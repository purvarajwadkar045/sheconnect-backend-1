from fastapi import APIRouter, Depends,HTTPException
from app.security import get_current_user
from app.models import User
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Travel, User
from app.schemas import TravelCreate
from sqlalchemy import func

router = APIRouter(prefix="/travel", tags=["Travel"])

@router.get("/")
def get_travel(current_user: User = Depends(get_current_user)):
    return {
        "message": "This is protected travel route",
        "user_id": current_user.user_id,
        "email": current_user.email_id
    }

router = APIRouter(prefix="/travel", tags=["Travel"])
@router.post("/intents")
def create_travel_intent(
    travel: TravelCreate,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.user_id == 1).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    new_travel = Travel(
        user_id=user.user_id,
        start_location=travel.start_location,
        end_location=travel.end_location,
        travel_date=travel.travel_date,
        mode_of_transport=travel.mode_of_transport,
        vehicle_no=travel.vehicle_no
    )

    db.add(new_travel)
    db.commit()

    return {"message": "Travel intent created"}


@router.get("/trips/{trip_id}/matches")
def get_trip_matches(trip_id: int, db: Session = Depends(get_db)):

    # 🔎 Step 1: Get current trip
    my_trip = db.query(Travel).filter(
        Travel.travel_id == trip_id,
        Travel.is_active == True
    ).first()

    if not my_trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    # 🔎 Step 2: Find matching trips
    matches = db.query(Travel).filter(
        Travel.start_location.ilike(my_trip.start_location),
        Travel.end_location.ilike(my_trip.end_location),
        func.date(Travel.travel_date) == func.date(my_trip.travel_date),  # match same date
        Travel.mode_of_transport.ilike(my_trip.mode_of_transport),
        Travel.user_id != my_trip.user_id,
        Travel.is_active == True
    ).all()

    return {
        "matches_found": len(matches),
        "matches": [
            {
                "travel_id": match.travel_id,
                "user_id": match.user_id,
                "start_location": match.start_location,
                "end_location": match.end_location,
                "travel_date": match.travel_date,
                "mode_of_transport": match.mode_of_transport,
                "vehicle_no": match.vehicle_no
            }
            for match in matches
        ]
    }