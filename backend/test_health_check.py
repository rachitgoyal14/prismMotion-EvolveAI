#!/usr/bin/env python3
"""
Quick health check for Creator Mode endpoint.
Run this to verify the server is running and the WebSocket endpoint exists.
"""

import asyncio
import websockets
import json


async def health_check():
    """Check if server and WebSocket endpoint are accessible."""
    
    # First check HTTP endpoint
    print("🔍 Step 1: Checking if server is running...")
    try:
        import urllib.request
        response = urllib.request.urlopen("http://localhost:8000/")
        data = json.loads(response.read().decode())
        print("✅ Server is running!")
        print(f"   Service: {data.get('service', 'Unknown')}")
        
        # Check if creator_mode is documented
        if 'creator_mode' in data.get('endpoints', {}):
            print("✅ Creator Mode endpoint is registered!")
        else:
            print("⚠️  Creator Mode not found in endpoint list (but may still work)")
    
    except Exception as e:
        print(f"❌ Server is NOT running!")
        print(f"   Error: {e}")
        print("\n💡 Start the server first:")
        print("   uvicorn app.main:app --reload\n")
        return False
    
    # Now check WebSocket
    print("\n🔍 Step 2: Checking WebSocket endpoint...")
    try:
        uri = "ws://localhost:8000/ws/creator"
        async with websockets.connect(uri, open_timeout=5) as ws:
            print("✅ WebSocket connected successfully!")
            
            # Try a simple ping
            print("\n🔍 Step 3: Sending test message...")
            await ws.send(json.dumps({"action": "invalid_test"}))
            
            # Should get an error back (which is good - means it's working)
            response = await asyncio.wait_for(ws.recv(), timeout=5)
            msg = json.loads(response)
            
            if msg.get("status") == "error":
                print("✅ WebSocket is responding correctly!")
                print(f"   (Got expected error: {msg.get('error', 'Unknown')})")
            else:
                print("⚠️  Got unexpected response:")
                print(f"   {msg}")
            
            print("\n" + "=" * 60)
            print("🎉 ALL CHECKS PASSED!")
            print("=" * 60)
            print("\n✅ You're ready to test Creator Mode!")
            print("\nRun this command:")
            print("   python3 test_creator_mode.py")
            print()
            return True
    
    except asyncio.TimeoutError:
        print("❌ WebSocket connection timeout!")
        print("   The server is running but not responding to WebSocket")
        return False
    
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"❌ WebSocket connection failed with status: {e.status_code}")
        print("   The endpoint may not exist or is misconfigured")
        return False
    
    except Exception as e:
        print(f"❌ WebSocket connection failed!")
        print(f"   Error: {e}")
        print("\n💡 Make sure the server is running:")
        print("   uvicorn app.main:app --reload\n")
        return False


if __name__ == "__main__":
    print("🏥 Creator Mode Health Check")
    print("=" * 60)
    print()
    
    try:
        result = asyncio.run(health_check())
        exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Cancelled by user")
        exit(1)
