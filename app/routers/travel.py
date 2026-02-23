from fastapi import APIRouter, Depends,HTTPException
from app.core.security import get_current_user
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import Travel, User, TravelRoute, Request
from app.schemas.schemas import TravelCreate, TravelResponse, TripRequestCreate, RequestUpdate, RequestResponse
from sqlalchemy import func, desc
import httpx
import json
from typing import List

router = APIRouter(prefix="/travel", tags=["Travel"])

@router.get("/trips", response_model=List[TravelResponse])#Returns all trips created by the logged-in user.
def get_my_trips(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    trips = db.query(Travel).filter(Travel.user_id == current_user.user_id).order_by(desc(Travel.created_at)).all()
    return trips

@router.post("/trips")#Creates a new trip.
async def create_trip(
    travel: TravelCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    
    if not (-90 <= travel.start.lat <= 90) or not (-180 <= travel.start.lng <= 180):
        raise HTTPException(status_code=400, detail="Invalid start coordinates")
    
    if not (-90 <= travel.end.lat <= 90) or not (-180 <= travel.end.lng <= 180):
        raise HTTPException(status_code=400, detail="Invalid end coordinates")

    if travel.start.lat == travel.end.lat and travel.start.lng == travel.end.lng:
        raise HTTPException(status_code=400, detail="Start and end points cannot be identical")

    new_travel = Travel(
        user_id=current_user.user_id,
        start_label=travel.start.label,
        end_label=travel.end.label,
        start_point=func.ST_SetSRID(func.ST_MakePoint(travel.start.lng, travel.start.lat), 4326),
        end_point=func.ST_SetSRID(func.ST_MakePoint(travel.end.lng, travel.end.lat), 4326),
        travel_date=travel.start_time,
        mode_of_transport=travel.transport_mode.value,
        time_flex_minutes=travel.time_flex_minutes,
        vehicle_no=travel.vehicle_no,
        status="SEARCHING"
    )

    db.add(new_travel)
    db.commit()
    db.refresh(new_travel)

    osrm_url = f"http://router.project-osrm.org/route/v1/driving/{travel.start.lng},{travel.start.lat};{travel.end.lng},{travel.end.lat}?overview=full&geometries=geojson"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(osrm_url)
            if response.status_code == 200:
                data = response.json()
                if data.get("routes"):
                    route_data = data["routes"][0]
                    geometry_json = json.dumps(route_data["geometry"])
                    
                    new_route = TravelRoute(
                        travel_id=new_travel.travel_id,
                        route_geom=func.ST_SetSRID(func.ST_GeomFromGeoJSON(geometry_json), 4326),
                        distance_meters=route_data["distance"],
                        duration_seconds=route_data["duration"]
                    )
                    db.add(new_route)
                    db.commit()
    except Exception as e:
        print(f"Error fetching/storing route: {e}")

    return {"message": "Trip created successfully"}

@router.get("/trips/{trip_id}/matches")#Finds matching trips for a given trip.
def get_trip_matches(trip_id: int, db: Session = Depends(get_db)):

    my_trip = db.query(Travel).filter(
        Travel.travel_id == trip_id,
        Travel.is_active == True
    ).first()

    if not my_trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    my_route = db.query(TravelRoute).filter(TravelRoute.travel_id == trip_id).first()
    
    if not my_route:
        return {"matches_found": 0, "matches": [], "message": "Route not generated for this trip yet"}

    overlap_ratio = (func.ST_Length(func.ST_Intersection(TravelRoute.route_geom, my_route.route_geom)) / func.ST_Length(my_route.route_geom)).label("overlap_score")
    
    start_distance = func.ST_Distance(Travel.start_point, my_trip.start_point).label("start_dist")
    end_distance = func.ST_Distance(Travel.end_point, my_trip.end_point).label("end_dist")

    results = db.query(Travel, User, overlap_ratio, start_distance, end_distance).join(
        TravelRoute, Travel.travel_id == TravelRoute.travel_id
    ).join(
        User, Travel.user_id == User.user_id
    ).filter(
        Travel.user_id != my_trip.user_id,
        Travel.status == "SEARCHING",
        Travel.is_active == True,
        # Spatial Filter: Start and End within 2km (2000 meters)
        func.ST_DWithin(Travel.start_point, my_trip.start_point, 2000),
        func.ST_DWithin(Travel.end_point, my_trip.end_point, 2000),
        # Time Filter: For simplicity, matching same day. Can be refined to time windows.
        func.date(Travel.travel_date) == func.date(my_trip.travel_date)
    ).order_by(desc("overlap_score")).limit(10).all()

    return {
        "matches_found": len(results),
        "matches": [
            {
                "match_id": str(travel.travel_id),
                "anonymous_id": user.anonymous_id,
                "start_location": travel.start_label,
                "end_location": travel.end_label,
                "mode_of_transport": travel.mode_of_transport,
                "route_overlap": round(overlap, 2) if overlap else 0,
                "start_distance_m": round(start_dist, 2) if start_dist else 0,
                "end_distance_m": round(end_dist, 2) if end_dist else 0
            }
            for travel, user, overlap, start_dist, end_dist in results
        ]
    }

@router.post("/request", response_model=RequestResponse)#Sends a travel request to another user.
def send_trip_request(
    request_data: TripRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
   
    target_trip = db.query(Travel).filter(Travel.travel_id == request_data.trip_id).first()
    if not target_trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    
    if target_trip.user_id == current_user.user_id:
        raise HTTPException(status_code=400, detail="Cannot send request to yourself")

    
    existing_request = db.query(Request).filter(
        Request.travel_id == request_data.trip_id,
        Request.sent_by == current_user.user_id,
        Request.status == "pending",
        Request.is_active == True
    ).first()

    if existing_request:
        raise HTTPException(status_code=400, detail="Request already pending")

    
    new_request = Request(
        travel_id=request_data.trip_id,
        sent_by=current_user.user_id,
        sent_to=target_trip.user_id,
        status="pending"
    )
    
    db.add(new_request)
    db.commit()
    db.refresh(new_request)
    return new_request

@router.get("/requests", response_model=dict[str, List[RequestResponse]])#Requests you received Requests you sent
def get_my_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    received = db.query(Request).filter(Request.sent_to == current_user.user_id, Request.is_active == True).all()
    sent = db.query(Request).filter(Request.sent_by == current_user.user_id, Request.is_active == True).all()
    
    return {
        "received": received,
        "sent": sent
    }

@router.put("/request/{request_id}")#Accepts or rejects a request.
def respond_to_request(
    request_id: int,
    update_data: RequestUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    req = db.query(Request).filter(Request.request_id == request_id, Request.is_active == True).first()
    
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
        
    if req.sent_to != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to respond to this request")
        
    if update_data.status not in ["accepted", "rejected"]:
        raise HTTPException(status_code=400, detail="Invalid status. Use 'accepted' or 'rejected'")
        
    req.status = update_data.status
    db.commit()
    
    return {"message": f"Request {update_data.status}"}
