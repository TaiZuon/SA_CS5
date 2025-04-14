from fastapi import APIRouter, HTTPException
from app.services.github import fetch_and_store_data

# Create an APIRouter instance to define the routes
router = APIRouter()

# Define a POST endpoint for fetching data from GitHub and saving to database
@router.post("/fetch-github")
async def fetch_github(per_page: int = 1):
  try:
    await fetch_and_store_data(per_page)
    return {"message": "✅ Dữ liệu đã được lấy và lưu!"}
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))