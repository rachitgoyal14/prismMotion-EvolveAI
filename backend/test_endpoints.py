import requests
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000"

# Optional test assets
DOC_PATH = Path("sample.pdf")        # optional
LOGO_PATH = Path("logo.png")         # optional
IMAGE_PATH = Path("image.png")       # optional


def maybe_file(path: Path, field_name: str):
    if path.exists():
        return (field_name, (path.name, open(path, "rb")))
    return None


def test_create():
    print("\n▶ Testing /create")

    files = []
    if DOC_PATH.exists():
        files.append(("documents", (DOC_PATH.name, open(DOC_PATH, "rb"))))
    if LOGO_PATH.exists():
        files.append(("logo", (LOGO_PATH.name, open(LOGO_PATH, "rb"))))
    if IMAGE_PATH.exists():
        files.append(("image", (IMAGE_PATH.name, open(IMAGE_PATH, "rb"))))

    data = {
        "video_type": "product_ad",
        "topic": "Benefits of regular exercise",
        "brand_name": "HealthCorp",
        "persona": "professional narrator",
        "tone": "clear and reassuring",
    }

    r = requests.post(f"{BASE_URL}/create", data=data, files=files)
    print(r.status_code, r.json())


def test_create_compliance():
    print("\n▶ Testing /create-compliance")

    files = []
    if DOC_PATH.exists():
        files.append(("documents", (DOC_PATH.name, open(DOC_PATH, "rb"))))
    if LOGO_PATH.exists():
        files.append(("logo", (LOGO_PATH.name, open(LOGO_PATH, "rb"))))

    data = {
        "video_type": "compliance_video",
        "prompt": "Explain approved indication and safety information strictly based on documents.",
        "brand_name": "Acme Pharma",
        "persona": "compliance officer",
        "tone": "formal and precise",
    }

    r = requests.post(f"{BASE_URL}/create-compliance", data=data, files=files)
    print(r.status_code, r.json())


def test_create_moa():
    print("\n▶ Testing /create-moa")

    files = []
    if DOC_PATH.exists():
        files.append(("documents", (DOC_PATH.name, open(DOC_PATH, "rb"))))
    if IMAGE_PATH.exists():
        files.append(("images", (IMAGE_PATH.name, open(IMAGE_PATH, "rb"))))

    data = {
        "drug_name": "Drug X",
        "condition": "Hypertension",
        "target_audience": "healthcare professionals",
        "persona": "professional medical narrator",
        "tone": "clear and educational",
        "quality": "high",
    }

    r = requests.post(f"{BASE_URL}/create-moa", data=data, files=files)
    print(r.status_code, r.json())


def test_create_doctor():
    print("\n▶ Testing /create-doctor")

    files = []
    if DOC_PATH.exists():
        files.append(("documents", (DOC_PATH.name, open(DOC_PATH, "rb"))))
    if IMAGE_PATH.exists():
        files.append(("images", (IMAGE_PATH.name, open(IMAGE_PATH, "rb"))))

    data = {
        "drug_name": "Drug X",
        "indication": "Type 2 Diabetes",
        "moa_summary": "Improves insulin sensitivity",
        "clinical_data": "HbA1c reduction observed",
        "pexels_query": "doctor consultation",
        "persona": "professional medical narrator",
        "tone": "scientific and professional",
        "quality": "high",
    }

    r = requests.post(f"{BASE_URL}/create-doctor", data=data, files=files)
    print(r.status_code, r.json())


if __name__ == "__main__":
    test_create()
    # test_create_compliance()
    # test_create_moa()
    # test_create_doctor()
