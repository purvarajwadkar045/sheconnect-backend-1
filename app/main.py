from fastapi import FastAPI
from app.database import Base, engine
from app.auth import router 
from app.travel import router as travel_router
import uuid
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()

origins = [
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
Base.metadata.create_all(bind=engine)

app.include_router(router)   


app.include_router(travel_router)

@app.get("/")
def home():
    return {"message": "Backend is running"}

