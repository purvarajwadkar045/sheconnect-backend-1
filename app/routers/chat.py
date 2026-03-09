from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import List, Dict
import time

from jose import jwt, JWTError

from app.core.database import get_db
from app.core.security import get_current_user, SECRET_KEY, ALGORITHM
from app.models import User, Request
from app.models.chat import Chat
from app.schemas.schemas import ChatMessageCreate, ChatMessageResponse, ChatMessageRead

router = APIRouter(prefix="/chat", tags=["Chat"])

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: int):
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    async def send_personal_message(self, message: dict, receiver_id: int):
        if receiver_id in self.active_connections:
            websocket = self.active_connections[receiver_id]
            await websocket.send_json(message)

manager = ConnectionManager()


def get_user_from_token(token: str, db: Session) -> User:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        if user_id is None:
            return None
    except JWTError:
        return None
    
    user = db.query(User).filter(
        User.user_id == user_id,
        User.is_active == True,
        User.is_verified == True
    ).first()
    return user


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str,
    db: Session = Depends(get_db)
):
    user = get_user_from_token(token, db)
    if not user:
        await websocket.close(code=1008)
        return

    await manager.connect(websocket, user.user_id)
    last_location_time = 0

    try:
        while True:
            data = await websocket.receive_json()
            
            event_type = data.get("type", "message")
            receiver_id = data.get("receiverId")

            # Handle typing event
            if event_type == "typing":
                is_typing = data.get("isTyping", True)
                if receiver_id and receiver_id != user.user_id:
                    await manager.send_personal_message(
                        {"type": "typing", "senderId": user.user_id, "isTyping": is_typing},
                        receiver_id
                    )
                continue

            # Handle location sharing event
            if event_type == "location":
                lat = data.get("lat")
                lng = data.get("lng")
                if receiver_id and receiver_id != user.user_id and lat is not None and lng is not None:
                    # Validate coordinate ranges
                    try:
                        lat = float(lat)
                        lng = float(lng)
                        if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lng <= 180.0):
                            raise ValueError()
                    except (ValueError, TypeError):
                        await websocket.send_json({"error": "Invalid coordinates provided"})
                        continue
                    
                    # Rate limiting: max 1 update per 2 seconds
                    current_time = time.time()
                    if current_time - last_location_time < 2.0:
                        continue
                    last_location_time = current_time

                    await manager.send_personal_message(
                        {
                            "type": "location", 
                            "senderId": user.user_id, 
                            "lat": lat, 
                            "lng": lng,
                            "timestamp": data.get("timestamp")
                        },
                        receiver_id
                    )
                continue

            # Handle read receipt event
            if event_type == "read":
                chat_ids = data.get("chat_ids", [])
                if chat_ids:
                    db.query(Chat).filter(
                        Chat.chat_id.in_(chat_ids),
                        Chat.receiver_id == user.user_id
                    ).update({"is_read": True}, synchronize_session=False)
                    db.commit()
                    
                    if receiver_id and receiver_id != user.user_id:
                        await manager.send_personal_message(
                            {"type": "receipt", "chat_ids": chat_ids},
                            receiver_id
                        )
                continue

            # Default: Handle standard message event
            message_text = data.get("message")

            if not receiver_id or message_text is None:
                await websocket.send_json({"error": "Missing receiverId or message text"})
                continue
                
            message_text = str(message_text).strip()
            
            if len(message_text) == 0:
                await websocket.send_json({"error": "Message cannot be empty."})
                continue
                
            if len(message_text) > 2000:
                await websocket.send_json({"error": "Message is too long (max 2000 characters)."})
                continue
                
            if user.user_id == receiver_id:
                await websocket.send_json({"error": "Cannot send message to yourself"})
                continue

            target_user = db.query(User).filter(User.user_id == receiver_id, User.is_active == True).first()
            if not target_user:
                await websocket.send_json({"error": "Receiver not found"})
                continue

            # Need to get request ID from an accepted request
            accepted_request = db.query(Request).filter(
                Request.status == "accepted",
                or_(
                    and_(Request.sent_by == user.user_id, Request.sent_to == receiver_id),
                    and_(Request.sent_by == receiver_id, Request.sent_to == user.user_id)
                ),
                Request.is_active == True
            ).first()

            if not accepted_request:
                await websocket.send_json({"error": "No accepted travel request with this user."})
                continue
            
            new_chat = Chat(
                request_id=accepted_request.request_id,
                sender_id=user.user_id,
                receiver_id=receiver_id,
                message=message_text
            )
            
            try:
                db.add(new_chat)
                db.commit()
                db.refresh(new_chat)
                chat_id = new_chat.chat_id
                created_at = new_chat.created_at.isoformat() if new_chat.created_at else None
            except Exception as e:
                db.rollback()
                await websocket.send_json({"error": f"Failed to save message: {str(e)}"})
                continue

            # Push to receiver
            await manager.send_personal_message(
                {
                    "type": "message",
                    "chat_id": chat_id,
                    "senderId": user.user_id, 
                    "message": message_text,
                    "created_at": created_at
                },
                receiver_id
            )

            # Send confirmation back to sender
            await websocket.send_json(
                {
                    "type": "message_sent",
                    "chat_id": chat_id,
                    "receiverId": receiver_id,
                    "message": message_text,
                    "created_at": created_at
                }
            )

    except WebSocketDisconnect:
        manager.disconnect(user.user_id)


# @router.post("/send", response_model=dict)
# def send_message(
#     payload: ChatMessageCreate,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     receiver_id = payload.receiverId
#     message_text = payload.message
# 
#     if current_user.user_id == receiver_id:
#         raise HTTPException(status_code=400, detail="Cannot send message to yourself")
# 
#     target_user = db.query(User).filter(User.user_id == receiver_id, User.is_active == True).first()
#     if not target_user:
#         raise HTTPException(status_code=404, detail="Receiver not found")
# 
#     accepted_request = db.query(Request).filter(
#         Request.status == "accepted",
#         or_(
#             and_(Request.sent_by == current_user.user_id, Request.sent_to == receiver_id),
#             and_(Request.sent_by == receiver_id, Request.sent_to == current_user.user_id)
#         ),
#         Request.is_active == True
#     ).first()
# 
#     if not accepted_request:
#         raise HTTPException(
#             status_code=403,
#             detail="You can only chat with users whom you have an accepted travel request with."
#         )
# 
#     new_chat = Chat(
#         request_id=accepted_request.request_id,
#         sender_id=current_user.user_id,
#         receiver_id=receiver_id,
#         message=message_text
#     )
# 
#     db.add(new_chat)
#     db.commit()
# 
#     return {"message": "Message sent successfully"}
# 
# 
# @router.post("/read", response_model=dict)
# def mark_messages_as_read(
#     payload: ChatMessageRead,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     chat_ids = payload.chat_ids
#     if not chat_ids:
#         return {"message": "No chat IDs provided"}
# 
#     db.query(Chat).filter(
#         Chat.chat_id.in_(chat_ids),
#         Chat.receiver_id == current_user.user_id
#     ).update({"is_read": True}, synchronize_session=False)
#     db.commit()
# 
#     return {"message": "Messages marked as read"}
# 
@router.get("/{userId}", response_model=dict)
def get_chat_messages(
    userId: int,
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Guard: only allow reading chats with users you have an accepted request with
    accepted_request = db.query(Request).filter(
        Request.status == "accepted",
        or_(
            and_(Request.sent_by == current_user.user_id, Request.sent_to == userId),
            and_(Request.sent_by == userId, Request.sent_to == current_user.user_id)
        ),
        Request.is_active == True
    ).first()

    if not accepted_request:
        raise HTTPException(
            status_code=403,
            detail="You can only view chats with users you have an accepted travel request with."
        )

    chats = db.query(Chat).filter(
        or_(
            and_(Chat.sender_id == current_user.user_id, Chat.receiver_id == userId),
            and_(Chat.sender_id == userId, Chat.receiver_id == current_user.user_id)
        ),
        Chat.is_active == True
    ).order_by(Chat.created_at.asc()).offset(offset).limit(limit).all()

    messages_response = [
        {
            "chat_id": chat.chat_id,
            "senderId": chat.sender_id, 
            "message": chat.message,
            "is_read": chat.is_read,
            "created_at": chat.created_at
        }
        for chat in chats
    ]

    return {
        "messages": messages_response,
        "limit": limit,
        "offset": offset,
        "total_returned": len(chats)
    }
