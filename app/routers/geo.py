from fastapi import APIRouter, Query, HTTPException
import httpx
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/geo", tags=["Geo"])

@router.get("/autocomplete")
async def autocomplete(q: str = Query(..., min_length=3)):
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": q,
        "format": "json",
        "limit": 5,
        "addressdetails": 1
    }
    # Nominatim usage policy requires a User-Agent with contact info
    headers = {"User-Agent": "SheConnect-Backend/1.0 (vedantgirjapure41@gmail.com)"}
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error(f"Nominatim geocoding error: {e}")
            raise HTTPException(status_code=503, detail="Geocoding service unavailable")

    if not isinstance(data, list):
        return {"results": []}

    results = []
    for item in data:
        results.append({
            "place_id": item.get("place_id"),
            "label": item.get("display_name"),
            "lat": float(item.get("lat")),
            "lng": float(item.get("lon")),
            "confidence": 0.9 
        })
        
    return {"results": results}
