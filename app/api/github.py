from fastapi import APIRouter, HTTPException
from app.services.github_service import fetch_and_store_data

router = APIRouter()

@router.post("/fetch-github")
async def fetch_github(per_page: int = 50):
  try:
    await fetch_and_store_data(per_page)
    return {"message": "✅ Dữ liệu đã được lấy và lưu!"}
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))