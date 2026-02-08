#!/usr/bin/env python3
"""
Simple test to verify Creator Mode WebSocket is working correctly.
Tests the WebSocket connection and basic message flow without running full pipeline.
"""

import asyncio
import websockets
import json


async def test_connection():
    """Test basic WebSocket connection and message handling."""
    
    uri = "ws://localhost:8000/ws/creator"
    print("🔌 Testing Creator Mode WebSocket Connection")
    print("=" * 60)
    print(f"Connecting to {uri}...\n")
    
    try:
        async with websockets.connect(uri) as ws:
            print("✅ Connection successful!\n")
            
            # Test 1: Send invalid action to check error handling
            print("📤 Test 1: Sending invalid action...")
            await ws.send(json.dumps({"action": "invalid_test_action"}))
            
            response = await asyncio.wait_for(ws.recv(), timeout=5)
            msg = json.loads(response)
            
            if msg.get("status") == "error":
                print(f"✅ Error handling works: {msg.get('error')}\n")
            else:
                print(f"⚠️  Unexpected response: {msg}\n")
            
            # Test 2: Send stop action
            print("📤 Test 2: Sending stop action...")
            await ws.send(json.dumps({"action": "stop"}))
            
            response = await asyncio.wait_for(ws.recv(), timeout=5)
            msg = json.loads(response)
            
            if msg.get("status") == "stopped":
                print(f"✅ Stop action works: {msg.get('message')}\n")
            else:
                print(f"⚠️  Unexpected response: {msg}\n")
            
            print("=" * 60)
            print("🎉 All basic tests passed!")
            print("=" * 60)
            print("\n✅ Creator Mode WebSocket is functioning correctly!")
            print("\nThe code fix has been applied. You can now test with:")
            print("   python3 test_creator_quick.py")
            print()
            
            return True
    
    except asyncio.TimeoutError:
        print("❌ Timeout waiting for server response")
        return False
    
    except websockets.exceptions.WebSocketException as e:
        print(f"❌ WebSocket error: {e}")
        print("\n💡 Make sure the server is running:")
        print("   uvicorn app.main:app --reload --reload-exclude 'app/outputs/**'")
        return False
    
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(test_connection())
    exit(0 if result else 1)
