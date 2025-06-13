from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel
from typing import List
import joblib
import pandas as pd
import os

API_KEY = os.getenv("API_KEY", "ak_2yRFbjP5NEgauepexZqPXkvNZ7E")

def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="🚫 مفتاح API غير صحيح")

class CityRequest(BaseModel):
    city: str

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

app = FastAPI(title="نظام ترشيح الممرضين")

@app.post("/nurses", response_model=List[NurseResponse])
async def get_nurses_by_city(req: CityRequest, _: str = Depends(verify_api_key)):
    try:
        df = joblib.load("nurse_data.pkl")
        city_normalized = req.city.strip().lower()
        df = df[df['City'].notna()].copy()
        df["City_clean"] = df["City"].astype(str).str.strip().str.lower()
        filtered = df[df["City_clean"] == city_normalized].sort_values("AverageRating", ascending=False)

        if filtered.empty:
            raise HTTPException(status_code=404, detail=f"❌ لا يوجد ممرضين في المدينة: {req.city}")

        return filtered.drop(columns=["City_clean"]).to_dict("records")

    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="⚠️ لم يتم العثور على ملف البيانات.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"⚠️ خطأ داخلي في السيرفر: {str(e)}")
