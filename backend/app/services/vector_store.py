"""
Vector Store Service for semantic vehicle search.

Uses ChromaDB with sentence-transformers for local embeddings.
This enables "find similar vehicles" functionality.
"""

import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Any, Optional
from pathlib import Path

# Persistent storage path
CHROMA_PATH = Path(__file__).parent.parent.parent.parent / "data" / "chroma_db"

# Use sentence-transformers for local embeddings (works offline on M4)
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Singleton client
_client: Optional[chromadb.PersistentClient] = None
_collection = None


def get_client() -> chromadb.PersistentClient:
    """Get or create ChromaDB client."""
    global _client
    if _client is None:
        CHROMA_PATH.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    return _client


def get_collection():
    """Get or create the vehicle collection with embeddings."""
    global _collection
    if _collection is None:
        client = get_client()
        
        # Use sentence-transformers for embeddings
        embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=EMBEDDING_MODEL
        )
        
        _collection = client.get_or_create_collection(
            name="vehicles",
            embedding_function=embedding_fn,
            metadata={"hnsw:space": "cosine"}
        )
    return _collection


def vehicle_to_text(vehicle: Dict[str, Any]) -> str:
    """
    Convert a vehicle record to a text description for embedding.
    
    Creates a rich text representation that captures semantic meaning.
    """
    parts = [
        f"{vehicle.get('year', '')} {vehicle.get('make', '')} {vehicle.get('model', '')}",
        f"{vehicle.get('trim', '')} trim" if vehicle.get('trim') else "",
        f"{vehicle.get('body_style', '')}",
        f"${vehicle.get('price', 0):,.0f}" if vehicle.get('price') else "",
        f"{vehicle.get('mileage', 0):,} miles" if vehicle.get('mileage') else "",
        f"{vehicle.get('exterior_color', '')} exterior" if vehicle.get('exterior_color') else "",
        f"{vehicle.get('fuel_type', '')}" if vehicle.get('fuel_type') else "",
        f"{vehicle.get('drivetrain', '')}" if vehicle.get('drivetrain') else "",
        f"{vehicle.get('engine', '')}" if vehicle.get('engine') else "",
    ]
    return " ".join(filter(None, parts))


async def index_vehicles(vehicles: List[Dict[str, Any]]) -> int:
    """
    Index a list of vehicles into the vector store.
    
    Args:
        vehicles: List of vehicle dictionaries from the database
        
    Returns:
        Number of vehicles indexed
    """
    collection = get_collection()
    
    # Prepare documents, metadata, and IDs
    documents = []
    metadatas = []
    ids = []
    
    for v in vehicles:
        vehicle_id = str(v.get('id', v.get('vin', '')))
        text = vehicle_to_text(v)
        
        documents.append(text)
        metadatas.append({
            "id": v.get('id', 0),
            "vin": v.get('vin', ''),
            "make": v.get('make', ''),
            "model": v.get('model', ''),
            "year": v.get('year', 0),
            "price": v.get('price', 0),
            "body_style": v.get('body_style', ''),
            "status": v.get('status', 'available')
        })
        ids.append(f"vehicle_{vehicle_id}")
    
    # Upsert to handle updates
    if documents:
        collection.upsert(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
    
    return len(documents)


async def find_similar_vehicles(
    query_vehicle: Dict[str, Any],
    n_results: int = 5,
    exclude_id: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Find vehicles similar to the given vehicle.
    
    Args:
        query_vehicle: The vehicle to find similar matches for
        n_results: Number of results to return
        exclude_id: Vehicle ID to exclude (typically the query vehicle itself)
        
    Returns:
        List of similar vehicles with similarity scores
    """
    collection = get_collection()
    
    # Create text description for the query vehicle
    query_text = vehicle_to_text(query_vehicle)
    
    # Extract reference vehicle identifiers for exclusion
    ref_year = query_vehicle.get('year')
    ref_make = query_vehicle.get('make', '').lower()
    ref_model = query_vehicle.get('model', '').lower()
    
    # Query for similar vehicles (get extra to account for exclusions)
    results = collection.query(
        query_texts=[query_text],
        n_results=n_results + 5,  # Get extra to account for potential exclusions
        where={"status": "available"} if exclude_id else None
    )
    
    similar_vehicles = []
    
    if results and results['metadatas'] and results['metadatas'][0]:
        for i, metadata in enumerate(results['metadatas'][0]):
            # Skip the query vehicle by ID
            if exclude_id and metadata.get('id') == exclude_id:
                continue
            
            # Also skip vehicles with same year/make/model (prevents self-matching)
            if (metadata.get('year') == ref_year and 
                metadata.get('make', '').lower() == ref_make and 
                metadata.get('model', '').lower() == ref_model):
                continue
            
            # Get similarity score (distance from ChromaDB)
            distance = results['distances'][0][i] if results.get('distances') else 0
            similarity = 1 - distance  # Convert distance to similarity
            
            similar_vehicles.append({
                **metadata,
                "similarity_score": round(similarity, 3),
                "document": results['documents'][0][i] if results.get('documents') else ""
            })
            
            if len(similar_vehicles) >= n_results:
                break
    
    return similar_vehicles


async def find_similar_by_text(
    query_text: str,
    n_results: int = 5
) -> List[Dict[str, Any]]:
    """
    Find vehicles similar to a text description.
    
    Useful for queries like "Find me something like a family SUV"
    
    Args:
        query_text: Text description to match
        n_results: Number of results to return
        
    Returns:
        List of matching vehicles
    """
    collection = get_collection()
    
    results = collection.query(
        query_texts=[query_text],
        n_results=n_results,
        where={"status": "available"}
    )
    
    vehicles = []
    
    if results and results['metadatas'] and results['metadatas'][0]:
        for i, metadata in enumerate(results['metadatas'][0]):
            distance = results['distances'][0][i] if results.get('distances') else 0
            similarity = 1 - distance
            
            vehicles.append({
                **metadata,
                "similarity_score": round(similarity, 3)
            })
    
    return vehicles


async def get_index_count() -> int:
    """Get the number of vehicles in the index."""
    try:
        collection = get_collection()
        return collection.count()
    except Exception:
        return 0


async def clear_index() -> None:
    """Clear the vector index (useful for re-indexing)."""
    global _collection
    client = get_client()
    try:
        client.delete_collection("vehicles")
    except Exception:
        pass
    _collection = None
