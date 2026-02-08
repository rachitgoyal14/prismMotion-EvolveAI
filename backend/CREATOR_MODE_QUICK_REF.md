# Creator Mode Quick Reference

## Connect
```javascript
ws://localhost:8000/ws/creator
```

## Start Session
```json
{
  "action": "start",
  "video_type": "product_ad",
  "payload": {
    "topic": "Your topic here",
    "brand_name": "Your brand",
    "persona": "professional narrator",
    "tone": "clear and reassuring"
  }
}
```

## Accept Stage
```json
{"action": "accept"}
```

## Regenerate
```json
{
  "action": "regenerate",
  "feedback": "Make it shorter"
}
```

## Stop
```json
{"action": "stop"}
```

## Video Types

| Type | Key Fields |
|------|-----------|
| `product_ad` | topic, brand_name |
| `moa` | drug_name, condition |
| `doctor_ad` | drug_name, indication |
| `social_media` | drug_name, indication, key_benefit |
| `compliance_video` | prompt, brand_name |

## Pipeline Stages

1. **scenes** - Structure and planning
2. **script** - Narration text
3. **visuals** - Animations/compositions
4. **animations** - Additional effects (optional)
5. **tts** - Audio generation
6. **render** - Final video

## Test It

```bash
# Start server
uvicorn app.main:app --reload

# Run test client
python test_creator_mode.py
```

## Quick Python Example

```python
import asyncio
import websockets
import json

async def main():
    async with websockets.connect('ws://localhost:8000/ws/creator') as ws:
        # Start
        await ws.send(json.dumps({
            "action": "start",
            "video_type": "moa",
            "payload": {"drug_name": "Aspirin", "condition": "CVD"}
        }))
        
        # Loop through stages
        while True:
            msg = json.loads(await ws.recv())
            
            if msg['status'] == 'completed':
                print(f"✓ {msg['stage']}")
                await ws.send(json.dumps({"action": "accept"}))
            
            elif msg['status'] == 'pipeline_complete':
                print(f"Done: {msg['video_path']}")
                break

asyncio.run(main())
```

## Key Points

✅ State is in-memory only  
✅ One WebSocket = One session  
✅ Pipeline pauses after each stage  
✅ Must explicitly accept or regenerate  
✅ Session lost on disconnect  
✅ No database persistence  
✅ Reuses all existing pipeline functions  

## Error Handling

**Stage Error:**
```json
{
  "stage": "script",
  "status": "error",
  "error": "API timeout",
  "next_actions": ["regenerate", "stop"]
}
```

**Action:** Send `regenerate` or `stop`

## Status Messages

| Status | Meaning |
|--------|---------|
| `session_started` | Session initialized |
| `stage_running` | Stage executing |
| `completed` | Stage done, awaiting user |
| `error` | Stage failed |
| `pipeline_complete` | All done |
| `stopped` | User terminated |
