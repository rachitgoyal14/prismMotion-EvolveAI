# Creator Mode Usage for /create Endpoint

The Creator Mode WebSocket is **already working** for the `/create` endpoint (product_ad videos). No code changes needed!

## WebSocket Endpoint
```
ws://localhost:8000/ws/creator
```

## How to Use

### 1. Connect to WebSocket
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/creator');
```

### 2. Start a Product Ad Video (same as /create endpoint)
```javascript
ws.send(JSON.stringify({
  action: "start",
  video_type: "product_ad",
  payload: {
    topic: "New diabetes medication",
    brand_name: "MediCare",
    persona: "professional narrator",
    tone: "clear and reassuring",
    region: "india",
    language: "english",
    reference_docs: "optional reference text...",
    assets: {
      logos: [],
      images: []
    }
  }
}));
```

### 3. Receive Stage Completion
The server will execute stages one by one and wait for your response after each:

```javascript
ws.onmessage = (event) => {
  const response = JSON.parse(event.data);
  
  if (response.status === "completed") {
    console.log(`Stage ${response.stage} completed!`);
    console.log('Data:', response.data);
    
    // You can now:
    // - Accept and move to next stage
    // - Regenerate with feedback
  }
};
```

### 4. Accept Current Stage (Move to Next)
```javascript
ws.send(JSON.stringify({
  action: "accept"
}));
```

### 5. Regenerate Current Stage (with optional feedback)
```javascript
ws.send(JSON.stringify({
  action: "regenerate",
  feedback: "Make the scenes more engaging"  // optional
}));
```

### 6. Stop the Pipeline
```javascript
ws.send(JSON.stringify({
  action: "stop"
}));
```

## Stage Order for Product Ads

The pipeline executes these stages in order:

1. **scenes** - Generate scene structure
2. **script** - Generate narration script  
3. **visuals** - Fetch Pexels media and generate Remotion compositions
4. **animations** - Generate animation metadata
5. **tts** - Generate audio with Azure TTS (supports multiple languages)
6. **render** - Produce final video

## Example Flow

```javascript
// 1. Start
ws.send(JSON.stringify({
  action: "start",
  video_type: "product_ad",
  payload: {
    topic: "Innovative heart medication",
    brand_name: "CardioHealth",
    language: "spanish"  // NEW: Multilingual support!
  }
}));

// Server responds: Stage 1 (scenes) completed

// 2. Accept scenes
ws.send(JSON.stringify({ action: "accept" }));

// Server responds: Stage 2 (script) completed

// 3. Regenerate script with feedback
ws.send(JSON.stringify({
  action: "regenerate",
  feedback: "Make it more patient-friendly"
}));

// Server responds: Stage 2 (script) completed again

// 4. Accept script
ws.send(JSON.stringify({ action: "accept" }));

// ... continue through all stages
// Server responds: Pipeline complete with video_path
```

## Response Format

### Stage Completed
```json
{
  "stage": "scenes",
  "version": 1,
  "status": "completed",
  "data": {
    "scenes_data": { ... },
    "scene_count": 5
  },
  "next_actions": ["accept", "regenerate"],
  "progress": {
    "current": 1,
    "total": 6
  }
}
```

### Pipeline Complete
```json
{
  "status": "pipeline_complete",
  "video_id": "abc123",
  "video_path": "/path/to/final.mp4",
  "message": "Video generation complete!"
}
```

### Error
```json
{
  "stage": "tts",
  "version": 2,
  "status": "error",
  "error": "Azure TTS API key not configured",
  "next_actions": ["regenerate", "stop"]
}
```

## Testing with Python

```python
import asyncio
import websockets
import json

async def test_creator_mode():
    uri = "ws://localhost:8000/ws/creator"
    
    async with websockets.connect(uri) as ws:
        # Start product ad
        await ws.send(json.dumps({
            "action": "start",
            "video_type": "product_ad",
            "payload": {
                "topic": "Arthritis relief medication",
                "brand_name": "JointCare",
                "language": "hindi"
            }
        }))
        
        # Auto-accept all stages
        while True:
            response = json.loads(await ws.recv())
            print(f"Received: {response.get('status')} - Stage: {response.get('stage')}")
            
            if response.get("status") == "pipeline_complete":
                print(f"Video ready: {response.get('video_path')}")
                break
            
            elif response.get("status") == "completed":
                # Auto-accept
                await ws.send(json.dumps({"action": "accept"}))
            
            elif response.get("status") == "error":
                print(f"Error: {response.get('error')}")
                break

asyncio.run(test_creator_mode())
```

## Key Features

✅ **Already Working** - No code changes needed
✅ **Step-by-Step Control** - Review each stage before proceeding  
✅ **Regeneration** - Regenerate any stage with optional feedback
✅ **Multilingual Support** - Works with new language parameter
✅ **Regional Support** - Works with region parameter for demographics
✅ **Version Tracking** - Tracks how many times each stage was regenerated
✅ **Error Handling** - Graceful error responses with recovery options

## Notes

- Session state is **in-memory only** - lost on disconnect
- Each WebSocket connection = one video generation session
- Frontend can show stage-by-stage progress with preview
- Perfect for building an interactive video editor UI
