from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel
from typing import List
import joblib
import pandas as pd
import os
from dotenv import load_dotenv

# تحميل المتغيرات البيئية
load_dotenv()
API_KEY = os.getenv("API_KEY")

# التحقق من مفتاح API
def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="🚫 مفتاح API غير صحيح")

# نموذج البيانات للممرض
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

# إنشاء التطبيق
app = FastAPI(title="نظام ترشيح الممرضين")

# نقطة فحص (للتأكد من أن السيرفر يعمل)
@app.get("/")
def root():
    return {"status": "✅ التطبيق يعمل بنجاح"}

# API رئيسي لاسترجاع الممرضين بناءً على المدينة
@app.get("/nurses/{city}", response_model=List[NurseResponse])
async def get_nurses_by_city(city: str, _: str = Depends(verify_api_key)):
    try:
        df = joblib.load("nurse_data.pkl")
        city_norm = city.strip().lower()
        df = df[df['City'].notna()].copy()
        df["City_clean"] = df["City"].str.strip().str.lower()
        filtered = df[df["City_clean"] == city_norm].sort_values("Score", ascending=False)
        if filtered.empty:
            raise HTTPException(status_code=404, detail=f"❌ لا يوجد ممرضين في المدينة: {city}")
        return filtered.drop(columns=["City_clean"]).to_dict("records")
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="⚠️ لم يتم العثور على ملف البيانات.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"⚠️ خطأ داخلي في السيرفر: {e}")

# تشغيل التطبيق محليًا أو في Railway
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
