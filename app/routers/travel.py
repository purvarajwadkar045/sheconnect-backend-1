from fastapi import APIRouter, Depends,HTTPException
from app.core.security import get_current_user
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import Travel, User, TravelRoute, Request
from app.schemas.schemas import TravelCreate, TravelResponse, TripRequestCreate, RequestUpdate, RequestResponse
from sqlalchemy import func, desc, text, or_
import httpx
from datetime import datetime, timezone, timedelta
import json
from typing import List

router = APIRouter(prefix="/travel", tags=["Travel"])

@router.get("/trips", response_model=List[TravelResponse])#Returns all trips created by the logged-in user.
def get_my_trips(
    limit: int = 50,
    offset: int = 0,
    active_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Travel).filter(Travel.user_id == current_user.user_id)
    if active_only:
        query = query.filter(Travel.is_active == True)
    trips = query.order_by(desc(Travel.created_at)).offset(offset).limit(limit).all()
    return trips

@router.post("/trips")#Creates a new trip.
async def create_trip(
    travel: TravelCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    
    start_time = travel.start_time
    # If the provided time is naive, assume it's in UTC for comparison.
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)

    if start_time < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Trip start time cannot be in the past.")
    
    if start_time > datetime.now(timezone.utc) + timedelta(days=60):
        raise HTTPException(status_code=400, detail="Trip cannot be scheduled more than 60 days in advance.")

    if not (0 <= travel.time_flex_minutes <= 120):
        raise HTTPException(status_code=400, detail="Time flexibility must be between 0 and 120 minutes.")

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

    osrm_url = f"http://router.project-osrm.org/route/v1/driving/{travel.start.lng},{travel.start.lat};{travel.end.lng},{travel.end.lat}?overview=full&geometries=geojson"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(osrm_url)
            response.raise_for_status()  # Raises HTTPStatusError for 4xx/5xx responses
            if response.status_code == 200:
                data = response.json()
                if not data.get("routes"):
                    raise ValueError("No route found between the specified points.")

                route_data = data["routes"][0]
                geometry_json = json.dumps(route_data["geometry"])
                
                new_route = TravelRoute(
                    travel_id=new_travel.travel_id,
                    route_geom=func.ST_SetSRID(func.ST_GeomFromGeoJSON(geometry_json), 4326),
                    distance_meters=route_data["distance"],
                    duration_seconds=route_data["duration"]
                )
                db.add(new_route)
                db.commit()  # Atomically commits both the trip and its route
                db.refresh(new_travel)
    except (httpx.RequestError, httpx.HTTPStatusError, ValueError) as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Could not generate a valid route for the given locations. Please check addresses. Error: {e}"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected server error occurred during trip creation."
        )

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

    # Calculate the current user's travel time window
    my_trip_earliest = my_trip.travel_date - timedelta(minutes=my_trip.time_flex_minutes)
    my_trip_latest = my_trip.travel_date + timedelta(minutes=my_trip.time_flex_minutes)

    overlap_ratio = (func.ST_Length(func.ST_Intersection(TravelRoute.route_geom, my_route.route_geom)) / func.ST_Length(my_route.route_geom)).label("overlap_score")
    
    start_distance = func.ST_Distance(Travel.start_point.cast(text("geography")), my_trip.start_point.cast(text("geography"))).label("start_dist")
    end_distance = func.ST_Distance(Travel.end_point.cast(text("geography")), my_trip.end_point.cast(text("geography"))).label("end_dist")

    results = db.query(Travel, User, overlap_ratio, start_distance, end_distance).join(
        TravelRoute, Travel.travel_id == TravelRoute.travel_id
    ).join(
        User, Travel.user_id == User.user_id
    ).filter(
        Travel.user_id != my_trip.user_id,
        Travel.status == "SEARCHING",
        Travel.is_active == True,
        # Spatial Filter: Start and End within 2km (2000 meters)
        func.ST_DWithin(Travel.start_point.cast(text("geography")), my_trip.start_point.cast(text("geography")), 2000),
        func.ST_DWithin(Travel.end_point.cast(text("geography")), my_trip.end_point.cast(text("geography")), 2000),
        # Time Window Overlap Filter: Check if the flexible time windows of the two trips overlap.
        # My earliest start must be before their latest start.
        my_trip_earliest <= (Travel.travel_date + func.make_interval(mins=Travel.time_flex_minutes)),
        # Their earliest start must be before my latest start.
        (Travel.travel_date - func.make_interval(mins=Travel.time_flex_minutes)) <= my_trip_latest
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
    # Validate sender's trip
    sender_trip = db.query(Travel).filter(
        Travel.travel_id == request_data.sender_trip_id,
        Travel.user_id == current_user.user_id
    ).first()
    if not sender_trip:
        raise HTTPException(status_code=404, detail="Your trip was not found or you are not the owner.")

    # Validate receiver's trip
    target_trip = db.query(Travel).filter(
        Travel.travel_id == request_data.receiver_trip_id,
        Travel.is_active == True,
        Travel.status == "SEARCHING"
    ).first()
    if not target_trip:
        raise HTTPException(status_code=404, detail="The requested trip is not available for matching.")

    if target_trip.user_id == current_user.user_id:
        raise HTTPException(status_code=400, detail="Cannot send request to yourself")

    # Check for existing pending requests between these two trips (in either direction)
    existing_request = db.query(Request).filter(
        or_(
            (Request.sender_travel_id == request_data.sender_trip_id and Request.receiver_travel_id == request_data.receiver_trip_id),
            (Request.sender_travel_id == request_data.receiver_trip_id and Request.receiver_travel_id == request_data.sender_trip_id)
        ),
        Request.status == "pending",
        Request.is_active == True
    ).first()

    if existing_request:
        raise HTTPException(status_code=400, detail="A request between these two trips is already pending.")

    # NOTE: This assumes the Request model has been updated to use sender_travel_id and receiver_travel_id
    new_request = Request(
        sender_travel_id=request_data.sender_trip_id,
        receiver_travel_id=request_data.receiver_trip_id,
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
    if update_data.status == "accepted":
        sender_trip = db.query(Travel).filter(Travel.travel_id == req.sender_travel_id).first()
        receiver_trip = db.query(Travel).filter(Travel.travel_id == req.receiver_travel_id).first()
        
        if sender_trip:
            sender_trip.status = "MATCHED"
        if receiver_trip:
            receiver_trip.status = "MATCHED"
    db.commit()
    
    return {"message": f"Request {update_data.status}"}

@router.post("/end")
def end_trip(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    trip = db.query(Travel).filter(
        Travel.user_id == current_user.user_id,
        Travel.status != "completed",
        Travel.is_active == True
    ).first()

    if not trip:
        raise HTTPException(status_code=404, detail="No active trip found to end")

    trip.status = "completed"
    trip.is_active = False

    accepted_requests = db.query(Request).filter(
        or_(
            Request.sent_by == current_user.user_id,
            Request.sent_to == current_user.user_id
        ),
        Request.status == "accepted",
        Request.is_active == True
    ).all()
    
    for req in accepted_requests:
        req.status = "completed"

    db.commit()

    return {"message": "Trip ended successfully", "redirectTo": "/dashboard"}
