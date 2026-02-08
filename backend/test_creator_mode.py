"""
Test client for Creator Mode WebSocket endpoint.

Demonstrates step-by-step video generation with manual control.

Usage:
    python test_creator_mode.py

This will:
1. Connect to WebSocket at ws://localhost:8000/ws/creator
2. Start a video generation session
3. Execute each stage one at a time
4. Wait for your input to accept/regenerate
5. Continue until video is complete
"""

import asyncio
import websockets
import json
from typing import Dict, Any


async def test_creator_mode():
    """Interactive test client for Creator Mode."""
    
    # Connect to WebSocket
    uri = "ws://localhost:8000/ws/creator"
    
    print("🎬 Creator Mode Test Client")
    print("=" * 60)
    print(f"Connecting to {uri}...\n")
    
    async with websockets.connect(uri) as websocket:
        print("✅ Connected!\n")
        
        # ─────────────────────────────────────────────
        # STEP 1: Start session
        # ─────────────────────────────────────────────
        
        print("📤 Starting new video generation session...")
        
        start_message = {
            "action": "start",
            "video_type": "product_ad",  # or "moa", "doctor_ad", "social_media", "compliance_video"
            "payload": {
                "topic": "New diabetes medication with improved glucose control",
                "brand_name": "DiabetEase",
                "persona": "professional narrator",
                "tone": "clear and reassuring",
                "region": "global",
            }
        }
        
        await websocket.send(json.dumps(start_message))
        
        # Receive session start confirmation
        response = await websocket.recv()
        data = json.loads(response)
        print(f"📥 {json.dumps(data, indent=2)}\n")
        
        if data.get("status") != "session_started":
            print("❌ Failed to start session")
            return
        
        video_id = data.get("video_id")
        print(f"🎥 Video ID: {video_id}")
        print(f"📋 Stages: {' → '.join(data.get('stage_order', []))}\n")
        print("─" * 60)
        
        # ─────────────────────────────────────────────
        # STEP 2: Pipeline loop
        # ─────────────────────────────────────────────
        
        pipeline_active = True
        
        while pipeline_active:
            # Wait for stage completion or running status
            response = await websocket.recv()
            data = json.loads(response)
            
            status = data.get("status")
            
            # ─── Stage Running ───
            if status == "stage_running":
                stage = data.get("stage")
                version = data.get("version")
                print(f"\n⏳ Running {stage.upper()} (version {version})...")
                continue
            
            # ─── Stage Completed ───
            elif status == "completed":
                stage = data.get("stage")
                version = data.get("version")
                stage_data = data.get("data", {})
                progress = data.get("progress", {})
                
                print(f"\n✅ {stage.upper()} completed (version {version})")
                print(f"   Progress: {progress.get('current')}/{progress.get('total')}")
                print(f"   Output: {json.dumps(stage_data, indent=2)[:300]}...\n")
                
                # Ask user what to do next
                print("What would you like to do?")
                print("  [1] Accept and continue")
                print("  [2] Regenerate without feedback")
                print("  [3] Regenerate with feedback")
                print("  [4] Stop")
                
                choice = input("\nYour choice (1-4): ").strip()
                
                if choice == "1":
                    # Accept stage
                    await websocket.send(json.dumps({"action": "accept"}))
                    print("✔️  Stage accepted, moving to next...\n")
                    print("─" * 60)
                
                elif choice == "2":
                    # Regenerate without feedback
                    await websocket.send(json.dumps({"action": "regenerate"}))
                    print("🔄 Regenerating stage...\n")
                    print("─" * 60)
                
                elif choice == "3":
                    # Regenerate with feedback
                    feedback = input("Enter your feedback: ").strip()
                    await websocket.send(json.dumps({
                        "action": "regenerate",
                        "feedback": feedback
                    }))
                    print(f"🔄 Regenerating with feedback: {feedback}\n")
                    print("─" * 60)
                
                elif choice == "4":
                    # Stop
                    await websocket.send(json.dumps({"action": "stop"}))
                    print("🛑 Stopping session...")
                    pipeline_active = False
                
                else:
                    print("Invalid choice, defaulting to accept...")
                    await websocket.send(json.dumps({"action": "accept"}))
            
            # ─── Stage Error ───
            elif status == "error":
                stage = data.get("stage")
                error = data.get("error")
                
                print(f"\n❌ {stage.upper()} failed!")
                print(f"   Error: {error}\n")
                
                print("What would you like to do?")
                print("  [1] Regenerate")
                print("  [2] Regenerate with feedback")
                print("  [3] Stop")
                
                choice = input("\nYour choice (1-3): ").strip()
                
                if choice == "1":
                    await websocket.send(json.dumps({"action": "regenerate"}))
                    print("🔄 Retrying stage...\n")
                    print("─" * 60)
                
                elif choice == "2":
                    feedback = input("Enter your feedback: ").strip()
                    await websocket.send(json.dumps({
                        "action": "regenerate",
                        "feedback": feedback
                    }))
                    print(f"🔄 Retrying with feedback: {feedback}\n")
                    print("─" * 60)
                
                else:
                    await websocket.send(json.dumps({"action": "stop"}))
                    print("🛑 Stopping session...")
                    pipeline_active = False
            
            # ─── Pipeline Complete ───
            elif status == "pipeline_complete":
                video_path = data.get("video_path")
                print("\n" + "=" * 60)
                print("🎉 PIPELINE COMPLETE!")
                print("=" * 60)
                print(f"✅ Video ID: {data.get('video_id')}")
                print(f"📁 Video path: {video_path}")
                print(f"🎬 Your video is ready!\n")
                pipeline_active = False
            
            # ─── Session Stopped ───
            elif status == "stopped":
                print("\n🛑 Session stopped by request")
                pipeline_active = False
            
            # ─── Unknown Status ───
            else:
                print(f"\n⚠️  Unknown status: {json.dumps(data, indent=2)}")


async def test_automated_mode():
    """Automated test that accepts all stages without user input."""
    
    uri = "ws://localhost:8000/ws/creator"
    
    print("🤖 Automated Creator Mode Test")
    print("=" * 60)
    print(f"Connecting to {uri}...\n")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected!\n")
            
            # Start session
            start_message = {
                "action": "start",
                "video_type": "social_media",
                "payload": {
                    "drug_name": "TestDrug",
                    "indication": "hypertension",
                    "key_benefit": "24-hour blood pressure control",
                    "target_audience": "patients",
                    "persona": "friendly health narrator",
                    "tone": "engaging and conversational",
                    "quality": "low",
                }
            }
            
            await websocket.send(json.dumps(start_message))
            
            response = await websocket.recv()
            data = json.loads(response)
            print(f"📥 Session started: {data.get('video_id')}\n")
            
            # Auto-accept all stages
            pipeline_active = True
            
            while pipeline_active:
                try:
                    response = await websocket.recv()
                    data = json.loads(response)
                    status = data.get("status")
                    
                    if status == "stage_running":
                        print(f"⏳ {data.get('stage')}...")
                    
                    elif status == "completed":
                        stage = data.get("stage")
                        print(f"✅ {stage} done")
                        # Auto-accept
                        await websocket.send(json.dumps({"action": "accept"}))
                    
                    elif status == "error":
                        stage = data.get("stage")
                        error = data.get("error")
                        print(f"❌ {stage} error: {error}")
                        # Auto-regenerate once
                        await websocket.send(json.dumps({"action": "regenerate"}))
                    
                    elif status == "pipeline_complete":
                        print(f"\n🎉 Complete! Video: {data.get('video_path')}")
                        pipeline_active = False
                    
                    elif status == "stopped":
                        print("\n🛑 Stopped")
                        pipeline_active = False
                
                except websockets.exceptions.ConnectionClosed as e:
                    print(f"\n⚠️  Connection closed during pipeline: {e}")
                    print("    This usually means a stage failed on the server.")
                    print("    Check server logs for details.")
                    break
    
    except websockets.exceptions.WebSocketException as e:
        print(f"\n❌ WebSocket error: {e}")
        print("    Make sure server is running: uvicorn app.main:app --reload")
    
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import sys
    
    print("\nSelect mode:")
    print("  [1] Interactive mode (manual control)")
    print("  [2] Automated mode (auto-accept all)")
    
    choice = input("\nYour choice (1-2): ").strip() if len(sys.argv) < 2 else sys.argv[1]
    
    if choice == "2":
        asyncio.run(test_automated_mode())
    else:
        asyncio.run(test_creator_mode())
