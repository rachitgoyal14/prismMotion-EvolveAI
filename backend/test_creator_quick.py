#!/usr/bin/env python3
"""
Quick test for Creator Mode - Customize this!
"""

import asyncio
import websockets
import json


async def quick_test():
    """Quick test with auto-accept for fast verification."""
    
    uri = "ws://localhost:8000/ws/creator"
    print(f"🔌 Connecting to {uri}...")
    
    try:
        async with websockets.connect(uri) as ws:
            print("✅ Connected!\n")
            
            # ====================================
            # CUSTOMIZE THIS SECTION:
            # ====================================
            
            # Change video_type to: "product_ad", "moa", "doctor_ad", "social_media", "compliance_video"
            video_type = "social_media"  # Changed from "moa" since it's having LLM issues
            
            # Customize payload based on video type:
            if video_type == "moa":
                payload = {
                    "drug_name": "Aspirin",
                    "condition": "cardiovascular disease",
                    "target_audience": "healthcare professionals",
                    "quality": "low"
                }
            elif video_type == "product_ad":
                payload = {
                    "topic": "New diabetes medication",
                    "brand_name": "DiabetEase",
                    "persona": "professional narrator",
                    "tone": "clear and reassuring"
                }
            elif video_type == "doctor_ad":
                payload = {
                    "drug_name": "Lisinopril",
                    "indication": "hypertension",
                    "quality": "low"
                }
            elif video_type == "social_media":
                payload = {
                    "drug_name": "VitaBoost",
                    "indication": "vitamin deficiency",
                    "key_benefit": "Daily energy boost",
                    "quality": "low"
                }
            else:  # compliance_video
                payload = {
                    "prompt": "Create compliance video about adverse event reporting",
                    "brand_name": "PharmaCorp"
                }
            
            # ====================================
            
            print(f"📤 Starting {video_type} video...\n")
            
            # Start session
            await ws.send(json.dumps({
                "action": "start",
                "video_type": video_type,
                "payload": payload
            }))
            
            # Get session started confirmation
            msg = json.loads(await ws.recv())
            video_id = msg.get("video_id", "unknown")
            print(f"🎬 Video ID: {video_id}")
            print(f"📋 Stages: {' → '.join(msg.get('stage_order', []))}\n")
            print("─" * 60)
            
            # Pipeline loop with auto-accept
            stage_count = 0
            retry_count = 0
            max_retries = 3
            
            while True:
                msg = json.loads(await ws.recv())
                status = msg.get("status")
                
                if status == "stage_running":
                    stage = msg.get("stage")
                    version = msg.get("version", 1)
                    print(f"⏳ Running {stage.upper()} (v{version})...", end="", flush=True)
                
                elif status == "completed":
                    stage = msg.get("stage")
                    version = msg.get("version", 1)
                    progress = msg.get("progress", {})
                    data = msg.get("data", {})
                    
                    print(f" ✅ Done!")
                    print(f"   Progress: {progress.get('current', '?')}/{progress.get('total', '?')}")
                    
                    # Show some output info
                    if "scene_count" in data:
                        print(f"   → Generated {data['scene_count']} scenes")
                    elif "script_count" in data:
                        print(f"   → Generated {data['script_count']} scripts")
                    elif "message" in data:
                        print(f"   → {data['message']}")
                    
                    stage_count += 1
                    retry_count = 0  # Reset retry count on success
                    
                    # Auto-accept
                    await ws.send(json.dumps({"action": "accept"}))
                    print(f"   ✔️  Accepted, continuing...\n")
                
                elif status == "error":
                    stage = msg.get("stage")
                    error = msg.get("error")
                    print(f" ❌ FAILED!")
                    print(f"   Error: {error}\n")
                    
                    retry_count += 1
                    
                    if retry_count >= max_retries:
                        print(f"   ❌ Max retries ({max_retries}) reached. Stopping.\n")
                        await ws.send(json.dumps({"action": "stop"}))
                        break
                    
                    # Auto-regenerate on error (with limit)
                    print(f"   🔄 Retrying {stage}...\n")
                    await ws.send(json.dumps({"action": "regenerate"}))
                
                elif status == "pipeline_complete":
                    video_path = msg.get("video_path")
                    print("─" * 60)
                    print("\n🎉 PIPELINE COMPLETE!")
                    print(f"✅ Video ID: {video_id}")
                    print(f"✅ Stages completed: {stage_count}")
                    print(f"📁 Video path: {video_path}\n")
                    break
                
                elif status == "stopped":
                    print("🛑 Session stopped")
                    break
    
    except websockets.exceptions.WebSocketException as e:
        print(f"\n❌ WebSocket error: {e}")
        print("\n💡 Make sure the server is running:")
        print("   uvicorn app.main:app --reload")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("🎬 Creator Mode Quick Test")
    print("=" * 60)
    print()
    asyncio.run(quick_test())
