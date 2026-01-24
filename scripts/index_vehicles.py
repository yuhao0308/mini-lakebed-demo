"""
Index vehicles into ChromaDB for semantic similarity search.

Run this script after seeding the database to enable the
"find similar vehicles" feature.
"""

import asyncio
import sqlite3
from pathlib import Path
import sys

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.services.vector_store import index_vehicles, get_index_count, clear_index

# Database path
DB_PATH = Path(__file__).parent.parent / "data" / "mini_lakebed.db"


def get_all_vehicles():
    """Fetch all available vehicles from the database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, vin, make, model, year, trim, body_style,
               exterior_color, interior_color, mileage, price, msrp,
               fuel_type, transmission, drivetrain, engine, status
        FROM inventory
        WHERE status = 'available'
    """)
    
    vehicles = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return vehicles


async def main():
    print("=" * 60)
    print("Vehicle Similarity Index Builder")
    print("=" * 60)
    
    # Check database exists
    if not DB_PATH.exists():
        print(f"❌ Database not found at {DB_PATH}")
        print("   Run seed_data.py first to create the database.")
        return
    
    # Get vehicles
    vehicles = get_all_vehicles()
    print(f"\n📊 Found {len(vehicles)} available vehicles in database")
    
    if not vehicles:
        print("❌ No vehicles to index. Run seed_data.py first.")
        return
    
    # Check current index
    current_count = await get_index_count()
    print(f"📁 Current index contains {current_count} vehicles")
    
    # Ask to rebuild if already indexed
    if current_count > 0:
        print("\n🔄 Clearing existing index...")
        await clear_index()
    
    # Index vehicles
    print("\n⏳ Indexing vehicles (this may take a moment for embeddings)...")
    indexed = await index_vehicles(vehicles)
    
    # Verify
    final_count = await get_index_count()
    
    print(f"\n✅ Successfully indexed {indexed} vehicles!")
    print(f"📊 Index now contains {final_count} vehicles")
    print("\n" + "=" * 60)
    print("Similar vehicles feature is now ready to use!")
    print("Try: 'Show me vehicles similar to a Toyota Camry'")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
