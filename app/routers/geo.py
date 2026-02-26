from fastapi import APIRouter, Query, HTTPException
import httpx

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
    headers = {"User-Agent": "SheConnect-Backend/1.0"}
    
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
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
