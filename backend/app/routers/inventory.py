"""
Inventory router for vehicle search and details.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from app.models.schemas import (
    Vehicle, VehicleSearchResponse, BodyStyle, FuelType
)
from app.services.database import execute_query, execute_one

router = APIRouter()


@router.get("/search_inventory", response_model=VehicleSearchResponse)
async def search_inventory(
    make: Optional[str] = Query(None, description="Filter by make"),
    model: Optional[str] = Query(None, description="Filter by model"),
    min_year: Optional[int] = Query(None, description="Minimum year"),
    max_year: Optional[int] = Query(None, description="Maximum year"),
    min_price: Optional[float] = Query(None, description="Minimum price"),
    max_price: Optional[float] = Query(None, description="Maximum price"),
    body_style: Optional[str] = Query(None, description="Body style filter"),
    max_mileage: Optional[int] = Query(None, description="Maximum mileage"),
    fuel_type: Optional[str] = Query(None, description="Fuel type filter"),
    status: str = Query("available", description="Vehicle status"),
    limit: int = Query(10, le=50, description="Max results")
):
    """
    Search inventory with filters.
    Returns vehicles matching all specified criteria.
    """
    # Build dynamic query
    conditions = ["status = ?"]
    params: List = [status]
    
    if make:
        conditions.append("LOWER(make) LIKE LOWER(?)")
        params.append(f"%{make}%")
    
    if model:
        conditions.append("LOWER(model) LIKE LOWER(?)")
        params.append(f"%{model}%")
    
    if min_year:
        conditions.append("year >= ?")
        params.append(min_year)
    
    if max_year:
        conditions.append("year <= ?")
        params.append(max_year)
    
    if min_price:
        conditions.append("price >= ?")
        params.append(min_price)
    
    if max_price:
        conditions.append("price <= ?")
        params.append(max_price)
    
    if body_style:
        conditions.append("LOWER(body_style) = LOWER(?)")
        params.append(body_style)
    
    if max_mileage:
        conditions.append("mileage <= ?")
        params.append(max_mileage)
    
    if fuel_type:
        conditions.append("LOWER(fuel_type) = LOWER(?)")
        params.append(fuel_type)
    
    where_clause = " AND ".join(conditions)
    query = f"""
        SELECT * FROM inventory 
        WHERE {where_clause}
        ORDER BY price ASC
        LIMIT ?
    """
    params.append(limit)
    
    results = await execute_query(query, tuple(params))
    
    return VehicleSearchResponse(
        count=len(results),
        vehicles=results
    )


@router.get("/vehicle/{vehicle_id}")
async def get_vehicle(vehicle_id: int):
    """Get a single vehicle by ID."""
    vehicle = await execute_one(
        "SELECT * FROM inventory WHERE id = ?",
        (vehicle_id,)
    )
    
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    return vehicle


@router.get("/vehicle/vin/{vin}")
async def get_vehicle_by_vin(vin: str):
    """Get a vehicle by VIN."""
    vehicle = await execute_one(
        "SELECT * FROM inventory WHERE vin = ?",
        (vin.upper(),)
    )
    
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    return vehicle


@router.get("/inventory/stats")
async def get_inventory_stats():
    """Get inventory statistics."""
    stats = await execute_one("""
        SELECT 
            COUNT(*) as total_vehicles,
            COUNT(CASE WHEN status = 'available' THEN 1 END) as available,
            COUNT(CASE WHEN status = 'sold' THEN 1 END) as sold,
            ROUND(AVG(price), 2) as avg_price,
            MIN(price) as min_price,
            MAX(price) as max_price,
            ROUND(AVG(mileage), 0) as avg_mileage
        FROM inventory
    """)
    
    return stats
