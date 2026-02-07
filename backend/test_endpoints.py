"""
Comprehensive Test Suite for Pharma Video Generator API
Tests all endpoints with various combinations of file uploads and parameters.

Test Coverage:
- / (root): 1 test
- /generate-user-id: 1 test
- /create (Remotion): 9 tests
- /create-compliance: 9 tests  
- /create-moa: 9 tests
- /create-doctor: 9 tests
- /create-sm: 3 tests
- /create-sm-rm: 7 tests
- /video/{video_id}: 2 tests

Total: 50 test cases

Usage:
    python test_endpoints.py                    # Run all tests
    python test_endpoints.py create             # Run only /create tests
    python test_endpoints.py compliance         # Run only /create-compliance tests
    python test_endpoints.py moa                # Run only /create-moa tests
    python test_endpoints.py doctor             # Run only /create-doctor tests
    python test_endpoints.py sm                 # Run only /create-sm tests
    python test_endpoints.py sm-rm              # Run only /create-sm-rm tests
"""

import requests
import os
from pathlib import Path
import json
import time
from typing import Dict, Optional, List
import io
from PIL import Image

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_URL = "http://localhost:8000"
TEST_USER_ID = "e08d1d5f-7d32-4b0a-93e2-e057212437a6"
TEST_RESULTS_DIR = Path("test_results")
TEST_RESULTS_DIR.mkdir(exist_ok=True)

# Test file paths
TEST_FILES_DIR = Path("test_files")
TEST_FILES_DIR.mkdir(exist_ok=True)

LOGO_PATH = TEST_FILES_DIR / "test_logo.png"
IMAGE_PATH = TEST_FILES_DIR / "test_image.jpg"
IMAGE2_PATH = TEST_FILES_DIR / "test_image2.jpg"
PDF_DOC_PATH = TEST_FILES_DIR / "test_document.pdf"
DOCX_DOC_PATH = TEST_FILES_DIR / "test_document.docx"
TXT_DOC_PATH = TEST_FILES_DIR / "test_document.txt"
INVALID_FILE_PATH = TEST_FILES_DIR / "invalid.exe"

# ============================================================================
# TEST FILE CREATION
# ============================================================================

def create_test_image(path: Path, size=(800, 600), color="blue"):
    """Create a test image file."""
    img = Image.new('RGB', size, color=color)
    img.save(path)
    print(f"✓ Created: {path.name}")

def create_test_pdf(path: Path):
    """Create a test PDF with pharmaceutical content."""
    pdf_content = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/Resources 4 0 R/MediaBox[0 0 612 792]/Contents 5 0 R>>endobj
4 0 obj<</Font<</F1<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>>>>>endobj
5 0 obj<</Length 300>>stream
BT /F1 12 Tf
50 750 Td (Test Pharmaceutical Document) Tj
0 -20 Td (Drug Name: TestDrug) Tj
0 -20 Td (Indication: Type 2 Diabetes) Tj
0 -20 Td (Mechanism: Increases insulin sensitivity) Tj
0 -20 Td (Clinical Data: 2%% HbA1c reduction) Tj
0 -20 Td (Safety: Well tolerated in trials) Tj
ET endstream endobj
xref 0 6
0000000000 65535 f 0000000009 00000 n 0000000058 00000 n 0000000115 00000 n 0000000214 00000 n 0000000304 00000 n trailer<</Size 6/Root 1 0 R>>
startxref 652
%%EOF"""
    path.write_bytes(pdf_content)
    print(f"✓ Created: {path.name}")

def create_test_txt(path: Path):
    """Create a test TXT file."""
    content = """Test Pharmaceutical Document

Drug Name: TestDrug
Indication: Type 2 Diabetes
Target Audience: Healthcare Professionals

Mechanism of Action:
TestDrug increases insulin sensitivity by activating PPAR-gamma receptors.

Clinical Data:
- Phase 3 trial: 2.1% HbA1c reduction
- Weight loss: 3.5kg average
- Safety: Low hypoglycemia risk

Dosing: 10-30mg once daily
"""
    path.write_text(content)
    print(f"✓ Created: {path.name}")

def create_test_docx(path: Path):
    """Create a minimal DOCX file."""
    import zipfile
    with zipfile.ZipFile(path, 'w') as docx:
        docx.writestr('[Content_Types].xml', '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
    print(f"✓ Created: {path.name}")

def create_invalid_file(path: Path):
    """Create an invalid .exe file."""
    path.write_bytes(b"MZ\x90\x00")
    print(f"✓ Created: {path.name}")

def setup_test_files():
    """Create all test files."""
    print("\n" + "="*70)
    print("SETTING UP TEST FILES")
    print("="*70)
    
    if not LOGO_PATH.exists():
        create_test_image(LOGO_PATH, (200, 200), "red")
    if not IMAGE_PATH.exists():
        create_test_image(IMAGE_PATH, (1920, 1080), "blue")
    if not IMAGE2_PATH.exists():
        create_test_image(IMAGE2_PATH, (1280, 720), "green")
    if not PDF_DOC_PATH.exists():
        create_test_pdf(PDF_DOC_PATH)
    if not TXT_DOC_PATH.exists():
        create_test_txt(TXT_DOC_PATH)
    if not DOCX_DOC_PATH.exists():
        create_test_docx(DOCX_DOC_PATH)
    if not INVALID_FILE_PATH.exists():
        create_invalid_file(INVALID_FILE_PATH)
    
    print("✓ All test files ready\n")

# ============================================================================
# TEST TRACKING
# ============================================================================

class TestTracker:
    def __init__(self):
        self.results = []
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.start_time = time.time()
    
    def add_result(self, endpoint: str, test_name: str, status: str, 
                   response_data: Optional[Dict] = None, error: Optional[str] = None,
                   duration: Optional[float] = None):
        result = {
            "endpoint": endpoint,
            "test_name": test_name,
            "status": status,
            "timestamp": time.time(),
            "duration_seconds": duration,
            "response_data": response_data,
            "error": error
        }
        self.results.append(result)
        
        if status == "PASS":
            self.passed += 1
            duration_str = f" ({duration:.1f}s)" if duration else ""
            print(f"  ✓ PASS: {test_name}{duration_str}")
        elif status == "FAIL":
            self.failed += 1
            print(f"  ✗ FAIL: {test_name}")
            if error:
                print(f"    → {error}")
        elif status == "SKIP":
            self.skipped += 1
            print(f"  ⊘ SKIP: {test_name}")
    
    def print_summary(self):
        total = len(self.results)
        total_time = time.time() - self.start_time
        
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        print(f"Total:   {total}")
        print(f"Passed:  {self.passed} ({self.passed/total*100:.1f}%)" if total > 0 else "Passed: 0")
        print(f"Failed:  {self.failed} ({self.failed/total*100:.1f}%)" if total > 0 else "Failed: 0")
        print(f"Skipped: {self.skipped} ({self.skipped/total*100:.1f}%)" if total > 0 else "Skipped: 0")
        print(f"Time:    {total_time:.1f}s")
        print("="*70)
        
        # Save results
        results_file = TEST_RESULTS_DIR / f"results_{int(time.time())}.json"
        with open(results_file, 'w') as f:
            json.dump({
                "summary": {"total": total, "passed": self.passed, "failed": self.failed, "skipped": self.skipped, "time": total_time},
                "results": self.results
            }, f, indent=2)
        print(f"\n📄 Results saved: {results_file}")
        
        if self.failed > 0:
            print("\n" + "="*70)
            print("FAILED TESTS")
            print("="*70)
            for r in self.results:
                if r["status"] == "FAIL":
                    print(f"❌ {r['endpoint']}: {r['test_name']}")
                    if r.get("error"):
                        print(f"   {r['error']}")

tracker = TestTracker()

# ============================================================================
# TEST HELPER
# ============================================================================

def test_endpoint(endpoint: str, test_name: str, data: Dict, files: Optional[Dict] = None,
                  expected_status: int = 200, should_fail: bool = False, timeout: int = 300):
    """Generic test function."""
    url = f"{BASE_URL}{endpoint}"
    start_time = time.time()
    
    try:
        files_payload = {}
        if files:
            for key, file_path in files.items():
                if file_path and Path(file_path).exists():
                    files_payload[key] = open(file_path, 'rb')
        
        response = requests.post(url, data=data, files=files_payload, timeout=timeout)
        
        for f in files_payload.values():
            f.close()
        
        duration = time.time() - start_time
        
        if should_fail:
            if response.status_code != 200:
                tracker.add_result(endpoint, test_name, "PASS", 
                                 response_data={"status_code": response.status_code}, duration=duration)
            else:
                tracker.add_result(endpoint, test_name, "FAIL",
                                 error=f"Expected failure but got {response.status_code}", duration=duration)
        else:
            if response.status_code == expected_status:
                try:
                    response_json = response.json()
                    tracker.add_result(endpoint, test_name, "PASS", response_data=response_json, duration=duration)
                except:
                    tracker.add_result(endpoint, test_name, "PASS",
                                     response_data={"status_code": response.status_code}, duration=duration)
            else:
                error_msg = f"Status {response.status_code}"
                try:
                    error_detail = response.json()
                    error_msg += f": {error_detail.get('detail', '')[:100]}"
                except:
                    error_msg += f": {response.text[:100]}"
                tracker.add_result(endpoint, test_name, "FAIL", error=error_msg, duration=duration)
    
    except requests.Timeout:
        tracker.add_result(endpoint, test_name, "FAIL", error=f"Timeout ({timeout}s)")
    except Exception as e:
        tracker.add_result(endpoint, test_name, "FAIL", error=str(e))

# ============================================================================
# TEST SUITES
# ============================================================================

def test_root_endpoint():
    print("\n" + "="*70)
    print("Testing / (Root)")
    print("="*70)
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code == 200:
            tracker.add_result("/", "Root endpoint", "PASS", response_data=response.json())
        else:
            tracker.add_result("/", "Root endpoint", "FAIL", error=f"Status {response.status_code}")
    except Exception as e:
        tracker.add_result("/", "Root endpoint", "FAIL", error=str(e))

def test_generate_user_id():
    print("\n" + "="*70)
    print("Testing /generate-user-id")
    print("="*70)
    try:
        response = requests.get(f"{BASE_URL}/generate-user-id")
        if response.status_code == 200 and "user_id" in response.json():
            tracker.add_result("/generate-user-id", "Generate user ID", "PASS", response_data=response.json())
        else:
            tracker.add_result("/generate-user-id", "Generate user ID", "FAIL", error="Missing user_id")
    except Exception as e:
        tracker.add_result("/generate-user-id", "Generate user ID", "FAIL", error=str(e))

def test_create_endpoint():
    print("\n" + "="*70)
    print("Testing /create (Remotion)")
    print("="*70)
    
    base = {
        "video_type": "product_ad",
        "topic": "New diabetes medication for Type 2 Diabetes",
        "brand_name": "TestBrand",
        "persona": "professional narrator",
        "tone": "clear and reassuring",
        "user_id": TEST_USER_ID
    }
    
    test_endpoint("/create", "1. No files", base.copy())
    test_endpoint("/create", "2. Logo only", base.copy(), {"logo": LOGO_PATH})
    test_endpoint("/create", "3. Image only", base.copy(), {"image": IMAGE_PATH})
    test_endpoint("/create", "4. Document only", base.copy(), {"documents": PDF_DOC_PATH})
    test_endpoint("/create", "5. Logo + Image", base.copy(), {"logo": LOGO_PATH, "image": IMAGE_PATH})
    test_endpoint("/create", "6. Logo + Document", base.copy(), {"logo": LOGO_PATH, "documents": PDF_DOC_PATH})
    test_endpoint("/create", "7. Image + Document", base.copy(), {"image": IMAGE_PATH, "documents": TXT_DOC_PATH})
    test_endpoint("/create", "8. All files", base.copy(), {"logo": LOGO_PATH, "image": IMAGE_PATH, "documents": PDF_DOC_PATH})
    test_endpoint("/create", "9. Invalid file (should fail)", base.copy(), {"logo": INVALID_FILE_PATH}, should_fail=True)

def test_create_compliance_endpoint():
    print("\n" + "="*70)
    print("Testing /create-compliance")
    print("="*70)
    
    base = {
        "video_type": "compliance_video",
        "prompt": "Pharmaceutical data privacy training",
        "brand_name": "ComplianceCorp",
        "persona": "compliance officer",
        "tone": "formal and precise",
        "user_id": TEST_USER_ID
    }
    
    test_endpoint("/create-compliance", "1. No files", base.copy())
    test_endpoint("/create-compliance", "2. Logo only", base.copy(), {"logo": LOGO_PATH})
    test_endpoint("/create-compliance", "3. Images only", base.copy(), {"images": IMAGE_PATH})
    test_endpoint("/create-compliance", "4. Documents only", base.copy(), {"documents": PDF_DOC_PATH})
    test_endpoint("/create-compliance", "5. Logo + Images", base.copy(), {"logo": LOGO_PATH, "images": IMAGE_PATH})
    test_endpoint("/create-compliance", "6. Logo + Documents", base.copy(), {"logo": LOGO_PATH, "documents": PDF_DOC_PATH})
    test_endpoint("/create-compliance", "7. Images + Documents", base.copy(), {"images": IMAGE_PATH, "documents": DOCX_DOC_PATH})
    test_endpoint("/create-compliance", "8. All files", base.copy(), {"logo": LOGO_PATH, "images": IMAGE_PATH, "documents": PDF_DOC_PATH})
    test_endpoint("/create-compliance", "9. Missing prompt (should fail)", {"video_type": "compliance_video", "user_id": TEST_USER_ID}, expected_status=422, should_fail=True)

def test_create_moa_endpoint():
    print("\n" + "="*70)
    print("Testing /create-moa")
    print("="*70)
    
    base = {
        "drug_name": "TestDrug",
        "condition": "Type 2 Diabetes",
        "target_audience": "healthcare professionals",
        "persona": "professional medical narrator",
        "tone": "clear and educational",
        "quality": "low",
        "user_id": TEST_USER_ID
    }
    
    test_endpoint("/create-moa", "1. No files", base.copy())
    test_endpoint("/create-moa", "2. Logo only", base.copy(), {"logo": LOGO_PATH})
    test_endpoint("/create-moa", "3. Images only", base.copy(), {"images": IMAGE_PATH})
    test_endpoint("/create-moa", "4. Documents only", base.copy(), {"documents": TXT_DOC_PATH})
    test_endpoint("/create-moa", "5. Logo + Images", base.copy(), {"logo": LOGO_PATH, "images": IMAGE_PATH})
    test_endpoint("/create-moa", "6. Logo + Documents", base.copy(), {"logo": LOGO_PATH, "documents": PDF_DOC_PATH})
    test_endpoint("/create-moa", "7. Images + Documents", base.copy(), {"images": IMAGE_PATH, "documents": PDF_DOC_PATH})
    test_endpoint("/create-moa", "8. All files", base.copy(), {"logo": LOGO_PATH, "images": IMAGE_PATH, "documents": PDF_DOC_PATH})
    test_endpoint("/create-moa", "9. Missing drug_name (should fail)", {"condition": "Test", "user_id": TEST_USER_ID}, expected_status=422, should_fail=True)

def test_create_doctor_endpoint():
    print("\n" + "="*70)
    print("Testing /create-doctor")
    print("="*70)
    
    base = {
        "drug_name": "TestDrug",
        "indication": "Type 2 Diabetes",
        "moa_summary": "Increases insulin sensitivity",
        "clinical_data": "2% HbA1c reduction",
        "pexels_query": "doctor consultation",
        "persona": "professional medical narrator",
        "tone": "scientific and professional",
        "quality": "low",
        "user_id": TEST_USER_ID
    }
    
    test_endpoint("/create-doctor", "1. No files", base.copy())
    test_endpoint("/create-doctor", "2. Logo only", base.copy(), {"logo": LOGO_PATH})
    test_endpoint("/create-doctor", "3. Images only", base.copy(), {"images": IMAGE_PATH})
    test_endpoint("/create-doctor", "4. Documents only", base.copy(), {"documents": PDF_DOC_PATH})
    test_endpoint("/create-doctor", "5. Logo + Images", base.copy(), {"logo": LOGO_PATH, "images": IMAGE_PATH})
    test_endpoint("/create-doctor", "6. Logo + Documents", base.copy(), {"logo": LOGO_PATH, "documents": DOCX_DOC_PATH})
    test_endpoint("/create-doctor", "7. Images + Documents", base.copy(), {"images": IMAGE_PATH, "documents": PDF_DOC_PATH})
    test_endpoint("/create-doctor", "8. All files", base.copy(), {"logo": LOGO_PATH, "images": IMAGE_PATH, "documents": PDF_DOC_PATH})
    test_endpoint("/create-doctor", "9. Missing indication (should fail)", {"drug_name": "Test", "user_id": TEST_USER_ID}, expected_status=422, should_fail=True)

def test_create_sm_endpoint():
    print("\n" + "="*70)
    print("Testing /create-sm")
    print("="*70)
    
    base = {
        "drug_name": "TestDrug",
        "indication": "High Blood Pressure",
        "key_benefit": "Lowers BP by 20 points",
        "target_audience": "patients",
        "persona": "friendly health narrator",
        "tone": "engaging and conversational",
        "quality": "low",
        "user_id": TEST_USER_ID
    }
    
    test_endpoint("/create-sm", "1. Patients audience", base.copy())
    test_endpoint("/create-sm", "2. HCP audience", {**base, "target_audience": "healthcare professionals"})
    test_endpoint("/create-sm", "3. Missing drug_name (should fail)", {"indication": "Test", "user_id": TEST_USER_ID}, expected_status=422, should_fail=True)

def test_create_sm_rm_endpoint():
    print("\n" + "="*70)
    print("Testing /create-sm-rm")
    print("="*70)
    
    base = {
        "topic": "Heart health tips",
        "brand_name": "HealthBrand",
        "persona": "friendly brand narrator",
        "tone": "engaging and conversational",
        "integrate_sadtalker": "false",
        "user_id": TEST_USER_ID
    }
    
    test_endpoint("/create-sm-rm", "1. No files", base.copy())
    test_endpoint("/create-sm-rm", "2. Logo only", base.copy(), {"logo": LOGO_PATH})
    test_endpoint("/create-sm-rm", "3. Image only", base.copy(), {"image": IMAGE_PATH})
    test_endpoint("/create-sm-rm", "4. Logo + Image", base.copy(), {"logo": LOGO_PATH, "image": IMAGE_PATH})
    tracker.add_result("/create-sm-rm", "5. Sadtalker (SKIPPED)", "SKIP", error="Requires external service")
    tracker.add_result("/create-sm-rm", "6. Sadtalker + image (SKIPPED)", "SKIP", error="Requires external service")
    test_endpoint("/create-sm-rm", "7. Missing topic (should fail)", {"brand_name": "Test", "user_id": TEST_USER_ID}, expected_status=422, should_fail=True)

def test_video_retrieval():
    print("\n" + "="*70)
    print("Testing /video/{video_id}")
    print("="*70)
    
    try:
        response = requests.get(f"{BASE_URL}/video/nonexistent_id")
        if response.status_code == 404:
            tracker.add_result("/video/{video_id}", "1. Non-existent video", "PASS")
        else:
            tracker.add_result("/video/{video_id}", "1. Non-existent video", "FAIL", error=f"Expected 404, got {response.status_code}")
    except Exception as e:
        tracker.add_result("/video/{video_id}", "1. Non-existent video", "FAIL", error=str(e))
    
    tracker.add_result("/video/{video_id}", "2. Valid video (SKIPPED)", "SKIP", error="Requires actual video_id")

# ============================================================================
# MAIN
# ============================================================================

def run_all_tests():
    print("\n" + "="*70)
    print("PHARMA VIDEO GENERATOR API - TEST SUITE")
    print("="*70)
    print(f"URL:     {BASE_URL}")
    print(f"User ID: {TEST_USER_ID}")
    print(f"Tests:   50")
    print("="*70)
    
    setup_test_files()
    
    # Check server
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        if response.status_code != 200:
            print(f"\n⚠️  Server returned {response.status_code}\n")
    except requests.ConnectionError:
        print(f"\n❌ Cannot connect to {BASE_URL}")
        print("Start server: uvicorn app.main:app --reload\n")
        return
    
    # Run tests
    test_root_endpoint()
    test_generate_user_id()
    test_create_endpoint()
    test_create_compliance_endpoint()
    test_create_moa_endpoint()
    test_create_doctor_endpoint()
    test_create_sm_endpoint()
    test_create_sm_rm_endpoint()
    test_video_retrieval()
    
    tracker.print_summary()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        test_name = sys.argv[1].lower()
        setup_test_files()
        
        tests = {
            "root": test_root_endpoint,
            "user-id": test_generate_user_id,
            "create": test_create_endpoint,
            "compliance": test_create_compliance_endpoint,
            "moa": test_create_moa_endpoint,
            "doctor": test_create_doctor_endpoint,
            "sm": test_create_sm_endpoint,
            "sm-rm": test_create_sm_rm_endpoint,
            "video": test_video_retrieval
        }
        
        if test_name in tests:
            tests[test_name]()
            tracker.print_summary()
        else:
            print(f"Unknown: {test_name}")
            print(f"Available: {', '.join(tests.keys())}")
            sys.exit(1)
    else:
        run_all_tests()