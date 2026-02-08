from fastapi import APIRouter, UploadFile, File, Form
import os
import shutil

router = APIRouter(prefix="/onboarding", tags=["onboarding"])

UPLOAD_DIR = "uploads"


@router.post("/")
async def save_onboarding_assets(
    user_id: str = Form(...),
    logo: UploadFile | None = File(None),
    assets: list[UploadFile] | None = File(None)
):
    # create base uploads folder
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # create user folder
    user_folder = os.path.join(UPLOAD_DIR, user_id)
    os.makedirs(user_folder, exist_ok=True)

    # ---------- SAVE LOGO ----------
    if logo:
        logo_path = os.path.join(user_folder, "logo.png")
        with open(logo_path, "wb") as buffer:
            shutil.copyfileobj(logo.file, buffer)

    # ---------- SAVE ASSETS ----------
    if assets:
        for i, asset in enumerate(assets):
            asset_path = os.path.join(
                user_folder,
                f"asset_{i}.png"
            )

            with open(asset_path, "wb") as buffer:
                shutil.copyfileobj(asset.file, buffer)

    return {
        "status": "success",
        "user_id": user_id
    }
