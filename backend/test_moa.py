#!/usr/bin/env python3
"""
Quick test script for MoA video generation.
Run this after setting up the MoA pipeline to verify everything works.
"""
import requests
import time
import json

API_URL = "http://localhost:8000"

def test_moa_video():
    """Test MoA video generation with a simple drug."""
    
    print("🧪 Testing MoA Video Generation Pipeline\n")
    print("=" * 60)
    
    # Simple test case: Aspirin for pain
    payload = {
        "drug_name": "Aspirin",
        "condition": "Pain and Inflammation",
        "target_audience": "patients",
        "quality": "low",  # Use low quality for faster testing
        "tone": "simple and clear"
    }
    
    print(f"\n📝 Request Payload:")
    print(json.dumps(payload, indent=2))
    
    print(f"\n🚀 Sending request to {API_URL}/create-moa...")
    start_time = time.time()
    
    try:
        response = requests.post(
            f"{API_URL}/create-moa",
            json=payload,
            timeout=600  # 10 minute timeout for rendering
        )
        
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ SUCCESS! Video generated in {elapsed:.1f} seconds")
            print(f"\n📹 Video Details:")
            print(json.dumps(result, indent=2))
            
            video_id = result.get("video_id")
            if video_id:
                print(f"\n🎬 Watch your video at:")
                print(f"   {API_URL}/video/{video_id}")
            
            return True
        else:
            print(f"\n❌ FAILED with status {response.status_code}")
            print(f"Error: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"\n⏱️  Request timed out (>10 minutes)")
        print("This might be normal for first run or high quality renders")
        return False
    except requests.exceptions.ConnectionError:
        print(f"\n❌ Cannot connect to {API_URL}")
        print("Make sure your FastAPI server is running:")
        print("   cd backend && uvicorn app.main:app --reload")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False


def check_dependencies():
    """Check if required dependencies are installed."""
    import subprocess
    
    print("\n🔍 Checking Dependencies...\n")
    
    # Check Manim
    try:
        result = subprocess.run(["manim", "--version"], capture_output=True, text=True)
        print(f"✅ Manim: {result.stdout.strip()}")
    except FileNotFoundError:
        print("❌ Manim: NOT FOUND")
        print("   Install: pip install manim")
        return False
    
    # Check FFmpeg
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
        version_line = result.stdout.split('\n')[0]
        print(f"✅ FFmpeg: {version_line}")
    except FileNotFoundError:
        print("❌ FFmpeg: NOT FOUND")
        print("   Install: brew install ffmpeg (macOS) or apt-get install ffmpeg (Linux)")
        return False
    
    print("\n✅ All dependencies found!\n")
    return True


if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║  MoA Video Pipeline - Quick Test                         ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    # Check dependencies first
    if not check_dependencies():
        print("\n❌ Please install missing dependencies first.\n")
        exit(1)
    
    # Run test
    success = test_moa_video()
    
    if success:
        print("\n" + "=" * 60)
        print("🎉 MoA pipeline is working correctly!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Try with different drugs and conditions")
        print("2. Increase quality to 'high' for better results")
        print("3. Review generated Manim code in outputs/manim/")
    else:
        print("\n" + "=" * 60)
        print("⚠️  Test failed - check error messages above")
        print("=" * 60)
        print("\nTroubleshooting:")
        print("1. Is your FastAPI server running?")
        print("2. Check logs in terminal running uvicorn")
        print("3. Review outputs/manim/ for generated files")