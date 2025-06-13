from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel
from typing import List
import joblib
import pandas as pd
import os
import re
import unicodedata

# دالة لتنظيف النص العربي والإنجليزي
def normalize_text(text):
    if not isinstance(text, str):
        return ""
    text = text.strip().lower()
    # إزالة التشكيل من العربي
    text = re.sub(r'[\u064B-\u0652]', '', text)
    # إزالة رموز زي النقاط والعلامات
    text = re.sub(r'[^\w\s]', '', text)
    # إزالة التنوين والتشكيل، وتوحيد الألف
    text = text.replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا').replace('ى', 'ي').replace('ئ', 'ي').replace('ة', 'ه')
    return text

# نموذج الرد
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

# نموذج الطلب
class CityRequest(BaseModel):
    city: str

# إنشاء التطبيق
app = FastAPI(title="نظام ترشيح الممرضين")

# مفتاح API اختياري (احذفه لو مش محتاجه)
API_KEY = os.getenv("API_KEY", "ak_2yRFbjP5NEgauepexZqPXkvNZ7E")
def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="🚫 مفتاح API غير صحيح")

@app.post("/nurses", response_model=List[NurseResponse])
async def get_nurses_by_city(request: CityRequest, _: str = Depends(verify_api_key)):
    try:
        # تحميل البيانات
        df = joblib.load("nurse_data.pkl")
        df = df[df['City'].notna()].copy()

        # تنظيف العمود من الطرف
        df["City_clean"] = df["City"].astype(str).apply(normalize_text)
        city_normalized = normalize_text(request.city)

        # الفلترة والترتيب
        filtered = df[df["City_clean"] == city_normalized].sort_values("AverageRating", ascending=False)

        if filtered.empty:
            raise HTTPException(status_code=404, detail=f"❌ لا يوجد ممرضين في المدينة: {request.city}")

        return filtered.drop(columns=["City_clean"]).to_dict("records")

    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="⚠️ لم يتم العثور على ملف البيانات.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"⚠️ خطأ داخلي في السيرفر: {str(e)}")
