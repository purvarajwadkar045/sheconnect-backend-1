from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from app.core.database import Base, engine
from app.routers.auth import router as auth_router
from app.routers.travel import router as travel_router
from fastapi.middleware.cors import CORSMiddleware
from app.scripts.import_emails import import_emails
from app.routers.geo import router as geo_router
from sqlalchemy import text

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

# This block ensures the PostGIS extension is enabled in the database.
# It must run before `Base.metadata.create_all()` to prevent errors.
with engine.connect() as connection:
    connection.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
    connection.commit()

Base.metadata.create_all(bind=engine)
import_emails("app/scripts/female_emails.csv")

app.include_router(auth_router)
app.include_router(travel_router)
app.include_router(geo_router)

@app.get("/")
def home():
    return {"message": "Backend is running"}
