from fastapi import FastAPI, HTTPException, Header, Depends, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator
from typing import List, Optional
import joblib
import pandas as pd
import os
import requests
from dotenv import load_dotenv
import arabic_reshaper
from bidi.algorithm import get_display
import re

# Load environment variables
load_dotenv()

API_KEY = os.getenv("API_KEY", "ak_2yRFbjP5NEgauepexZqPXkvNZ7E")
CITY_API_URL = os.getenv("CITY_API_URL", "https://api.example.com/cities")

def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="🚫 مفتاح API غير صحيح")

class NurseResponse(BaseModel):
    NurseID: int
    FName: str
    LName: str
    PhoneNumber: int
    Email: str
    Experience: int
    Specialty: str
    City: str
    Street: str
    AverageRating: float
    ReviewCount: float
    Comment: str
    Score: float

    @validator('FName', 'LName', 'Specialty', 'City', 'Street', 'Comment')
    def validate_arabic_text(cls, v):
        if not re.search(r'[\u0600-\u06FF]', v):
            raise ValueError('يجب أن يحتوي النص على حروف عربية')
        return v

class CityInfo(BaseModel):
    city_name: str
    population: Optional[int]
    region: Optional[str]
    country: Optional[str]

    @validator('city_name', 'region', 'country')
    def validate_arabic_text(cls, v):
        if v and not re.search(r'[\u0600-\u06FF]', v):
            raise ValueError('يجب أن يحتوي النص على حروف عربية')
        return v

app = FastAPI(
    title="نظام ترشيح الممرضين",
    description="API لتوصية الممرضين مع معلومات المدينة",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def format_arabic_text(text: str) -> str:
    """Format Arabic text for proper display"""
    reshaped_text = arabic_reshaper.reshape(text)
    return get_display(reshaped_text)

async def get_city_info(city: str) -> CityInfo:
    try:
        headers = {
            'Accept': 'application/json',
            'Accept-Language': 'ar',
            'Content-Type': 'application/json; charset=utf-8'
        }
        response = requests.get(f"{CITY_API_URL}/{city}", headers=headers)
        if response.status_code == 200:
            return CityInfo(**response.json())
        return CityInfo(city_name=city)
    except Exception as e:
        print(f"Error fetching city info: {str(e)}")
        return CityInfo(city_name=city)

@app.get("/nurses/{city}", response_model=List[NurseResponse])
async def get_nurses_by_city(
    city: str,
    response: Response,
    _: str = Depends(verify_api_key)
):
    try:
        # Set response headers for Arabic support
        response.headers["Content-Type"] = "application/json; charset=utf-8"
        response.headers["Content-Language"] = "ar"

        # Get city information
        city_info = await get_city_info(city)
        
        # Load and filter nurse data
        df = joblib.load("nurse_data.pkl")
        city_normalized = city.strip().lower()
        df = df[df['City'].notna()].copy()
        df["City_clean"] = df["City"].astype(str).str.strip().str.lower()
        filtered = df[df["City_clean"] == city_normalized].sort_values("AverageRating", ascending=False)

        if filtered.empty:
            raise HTTPException(
                status_code=404, 
                detail=format_arabic_text(f"❌ لا يوجد ممرضين في المدينة: {city_info.city_name}")
            )

        # Prepare response
        nurses = filtered.drop(columns=["City_clean"]).to_dict("records")
        
        # Add city information to response
        for nurse in nurses:
            nurse["city_info"] = city_info.dict()
            # Format Arabic text in response
            for key, value in nurse.items():
                if isinstance(value, str):
                    nurse[key] = format_arabic_text(value)

        return nurses

    except FileNotFoundError:
        raise HTTPException(
            status_code=500, 
            detail=format_arabic_text("⚠️ لم يتم العثور على ملف البيانات.")
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=format_arabic_text(f"⚠️ خطأ داخلي في السيرفر: {str(e)}")
        )

@app.get("/health")
async def health_check(response: Response):
    response.headers["Content-Type"] = "application/json; charset=utf-8"
    response.headers["Content-Language"] = "ar"
    return {
        "status": "healthy",
        "message": format_arabic_text("الخدمة تعمل بشكل جيد")
    }
