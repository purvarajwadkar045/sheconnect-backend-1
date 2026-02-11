from fastapi import APIRouter, Depends,HTTPException
from app.security import get_current_user
from app.models import User
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Travel, User
from app.schemas import TravelCreate
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
