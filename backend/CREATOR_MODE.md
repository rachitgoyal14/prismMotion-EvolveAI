# Creator Mode Documentation

## Overview

Creator Mode is a **step-by-step video generation feature** that gives users full control over the video creation pipeline. Unlike the automated endpoints (`/create`, `/create-moa`, etc.), Creator Mode pauses after each stage and waits for explicit user approval before continuing.

## Key Features

✅ **Manual Stage Progression** - Pipeline advances only on user command  
✅ **Accept/Regenerate** - Approve output or request regeneration  
✅ **Feedback Loop** - Optionally provide natural language feedback for regeneration  
✅ **Real-time Updates** - WebSocket-based bidirectional communication  
✅ **In-Memory State** - No database persistence required  
✅ **All Video Types Supported** - Works with all existing pipelines

## Architecture

### Connection Model
- One WebSocket connection = One session
- State kept in memory per connection
- Session lost on disconnect (acceptable for Creator Mode use case)

### Pipeline Stages

All video types follow this general flow:

1. **scenes** - Generate scene structure and planning
2. **script** - Generate narration text for each scene  
3. **visuals** - Generate animations (Manim) or compositions (Remotion)
4. **animations** - Additional animations (Remotion only, optional)
5. **tts** - Generate text-to-speech audio
6. **render** - Produce final video file

### Reused Components

Creator Mode **does not duplicate any logic**. It calls the exact same functions used by existing endpoints:

- `generate_scenes()` / `generate_moa_scenes()` / `generate_doctor_scenes()` / `generate_sm_scenes()`
- `generate_script()`
- `run_stage2()` / `run_stage2_moa()` / `run_stage2_doctor()` / `run_stage2_sm()`
- `generate_animations()`
- `tts_generate()`
- `render_remotion()` / `render_moa_video()` / `render_doctor_video()` / `render_sm_video()`

## WebSocket Protocol

### Endpoint

```
ws://localhost:8000/ws/creator
```

### Message Format

All messages are JSON objects.

#### Client → Server

**Start Session**
```json
{
  "action": "start",
  "video_type": "product_ad",
  "payload": {
    "topic": "New diabetes medication",
    "brand_name": "DiabetEase",
    "persona": "professional narrator",
    "tone": "clear and reassuring",
    "region": "global"
  }
}
```

**Accept Stage**
```json
{
  "action": "accept"
}
```

**Regenerate Without Feedback**
```json
{
  "action": "regenerate"
}
```

**Regenerate With Feedback**
```json
{
  "action": "regenerate",
  "feedback": "Make the script more concise and patient-friendly"
}
```

**Stop Session**
```json
{
  "action": "stop"
}
```

#### Server → Client

**Session Started**
```json
{
  "status": "session_started",
  "video_id": "vid_abc123",
  "video_type": "product_ad",
  "stage_order": ["scenes", "script", "visuals", "animations", "tts", "render"],
  "current_stage": "scenes"
}
```

**Stage Running**
```json
{
  "status": "stage_running",
  "stage": "scenes",
  "version": 1,
  "message": "Executing scenes..."
}
```

**Stage Completed**
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

**Stage Error**
```json
{
  "stage": "script",
  "version": 2,
  "status": "error",
  "error": "OpenAI API timeout",
  "next_actions": ["regenerate", "stop"]
}
```

**Pipeline Complete**
```json
{
  "status": "pipeline_complete",
  "video_id": "vid_abc123",
  "video_path": "/path/to/final.mp4",
  "message": "All stages complete! Video is ready."
}
```

## Supported Video Types

### 1. Product Ad (`product_ad`)

**Required Payload:**
```json
{
  "topic": "string",
  "brand_name": "string",
  "persona": "string",
  "tone": "string",
  "region": "string (optional)"
}
```

**Pipeline:** Remotion-based with Pexels media

### 2. Compliance Video (`compliance_video`)

**Required Payload:**
```json
{
  "prompt": "string",
  "brand_name": "string",
  "persona": "compliance officer",
  "tone": "formal and precise",
  "reference_docs": "string (optional)"
}
```

**Pipeline:** Remotion with strict validation

### 3. MoA Video (`moa`)

**Required Payload:**
```json
{
  "drug_name": "string",
  "condition": "string",
  "target_audience": "healthcare professionals",
  "persona": "professional medical narrator",
  "tone": "clear and educational",
  "quality": "low/high"
}
```

**Pipeline:** Manim animations

### 4. Doctor Ad (`doctor_ad`)

**Required Payload:**
```json
{
  "drug_name": "string",
  "indication": "string",
  "moa_summary": "string (optional)",
  "clinical_data": "string (optional)",
  "persona": "professional medical narrator",
  "tone": "scientific and professional",
  "quality": "low/high"
}
```

**Pipeline:** Manim + Pexels + Logo support

### 5. Social Media (`social_media`)

**Required Payload:**
```json
{
  "drug_name": "string",
  "indication": "string",
  "key_benefit": "string (optional)",
  "target_audience": "patients",
  "persona": "friendly health narrator",
  "tone": "engaging and conversational",
  "quality": "low/high"
}
```

**Pipeline:** Manim + Pexels for short-form content

## Usage Examples

### Python Client (websockets)

```python
import asyncio
import websockets
import json

async def create_video_with_control():
    uri = "ws://localhost:8000/ws/creator"
    
    async with websockets.connect(uri) as ws:
        # Start session
        await ws.send(json.dumps({
            "action": "start",
            "video_type": "moa",
            "payload": {
                "drug_name": "Aspirin",
                "condition": "cardiovascular disease",
                "target_audience": "healthcare professionals"
            }
        }))
        
        # Receive session started
        response = await ws.recv()
        data = json.loads(response)
        print(f"Video ID: {data['video_id']}")
        
        # Pipeline loop
        while True:
            response = await ws.recv()
            data = json.loads(response)
            
            if data['status'] == 'completed':
                stage = data['stage']
                print(f"Stage {stage} done")
                
                # Review output
                print(json.dumps(data['data'], indent=2))
                
                # Decide what to do
                user_input = input("Accept? (y/n): ")
                
                if user_input.lower() == 'y':
                    await ws.send(json.dumps({"action": "accept"}))
                else:
                    feedback = input("Feedback (optional): ")
                    await ws.send(json.dumps({
                        "action": "regenerate",
                        "feedback": feedback
                    }))
            
            elif data['status'] == 'pipeline_complete':
                print(f"Done! Video: {data['video_path']}")
                break

asyncio.run(create_video_with_control())
```

### JavaScript Client (browser)

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/creator');

ws.onopen = () => {
  // Start session
  ws.send(JSON.stringify({
    action: 'start',
    video_type: 'product_ad',
    payload: {
      topic: 'New medication for anxiety',
      brand_name: 'CalmMed',
      persona: 'empathetic narrator',
      tone: 'warm and reassuring'
    }
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.status === 'session_started') {
    console.log(`Session started: ${data.video_id}`);
  }
  
  else if (data.status === 'completed') {
    console.log(`Stage ${data.stage} complete:`, data.data);
    
    // Show UI for accept/regenerate
    showStageReviewUI(data);
  }
  
  else if (data.status === 'pipeline_complete') {
    console.log(`Video ready: ${data.video_path}`);
    showVideoPlayer(data.video_path);
  }
};

function acceptStage() {
  ws.send(JSON.stringify({ action: 'accept' }));
}

function regenerateStage(feedback = '') {
  ws.send(JSON.stringify({
    action: 'regenerate',
    feedback: feedback
  }));
}
```

## State Management

### Session State Structure

```python
class CreatorSession:
    video_id: str              # Unique video identifier
    video_type: str            # Type of video being generated
    payload: Dict[str, Any]    # Initial configuration
    
    current_stage: str         # Current stage name
    stage_outputs: Dict        # stage_name -> output data
    stage_versions: Dict       # stage_name -> attempt count
    user_feedback: str         # Optional feedback for regeneration
    
    stage_order: List[str]     # Ordered list of stages
    stage_index: int           # Current position in stage_order
    is_active: bool            # Session active flag
```

### State Lifecycle

1. **Session Created** - When client sends "start"
2. **Stage Execution** - Function runs, output stored in `stage_outputs`
3. **User Review** - Client decides to accept or regenerate
4. **Stage Accepted** - `stage_index` increments, move to next stage
5. **Stage Regenerated** - `stage_versions` increments, re-run same stage
6. **Pipeline Complete** - All stages done, final video available
7. **Session Ends** - WebSocket closes, state discarded

## Error Handling

### Stage Failures

When a stage fails:
1. Server sends error message with stage name and error text
2. Client can choose to:
   - Regenerate (retry the stage)
   - Regenerate with feedback (provide guidance)
   - Stop (terminate session)

### Network Interruptions

- If WebSocket disconnects, session state is lost
- Client must restart from beginning
- This is acceptable for Creator Mode (not production-critical)

### Timeout Handling

- Heavy stages (Manim rendering) run in thread pools
- No hard timeout on stage execution
- Client can close connection to abort

## Performance Considerations

### Non-Blocking Execution

All heavy operations use `asyncio.run_in_executor()`:
- Scene generation (OpenAI API calls)
- Script generation (OpenAI API calls)
- Manim rendering (CPU-intensive)
- Remotion rendering (subprocess calls)
- TTS generation (API calls)

This prevents blocking the WebSocket event loop.

### Concurrent Clients

Each WebSocket connection:
- Has its own in-memory session
- Runs independently
- No shared state between sessions

Multiple users can use Creator Mode simultaneously without conflicts.

## Testing

### Manual Testing

```bash
# Terminal 1: Start backend
cd backend
uvicorn app.main:app --reload

# Terminal 2: Run test client
python test_creator_mode.py
```

### Automated Testing

```bash
# Run automated acceptance test
python test_creator_mode.py 2
```

This will:
1. Connect to WebSocket
2. Start a social media video
3. Auto-accept all stages
4. Verify pipeline completion

## Comparison: Creator Mode vs Regular Endpoints

| Feature | Regular Endpoints | Creator Mode |
|---------|------------------|--------------|
| Control | Automated | Manual |
| Progression | Auto-advance | Wait for user |
| Regeneration | Not available | Available |
| Feedback | Not available | Available |
| Use Case | Production | Content review |
| State | Database | In-memory |
| Connection | HTTP | WebSocket |

## Limitations

1. **No Persistence** - Session lost on disconnect
2. **No Reconnection** - Cannot resume interrupted session
3. **No Multi-User Collaboration** - One user per session
4. **No Stage Skipping** - Must go through all stages in order
5. **No Branch/Merge** - Cannot try multiple variations in parallel

These are acceptable trade-offs for the Creator Mode use case.

## Future Enhancements (Not Implemented)

Possible improvements:
- Session persistence (Redis/DB)
- Reconnection support (session ID)
- Parallel variation testing
- Stage skipping
- Custom stage order
- Webhooks for stage completion
- Retry limits
- Stage timeout configuration

## Troubleshooting

**Problem:** WebSocket closes immediately

**Solution:** Check server logs, ensure backend is running, verify WebSocket URL

---

**Problem:** Stage hangs indefinitely

**Solution:** Close connection and restart. Check backend logs for errors.

---

**Problem:** Regeneration doesn't change output

**Solution:** Feedback is used as context but doesn't guarantee different output. Try more specific feedback.

---

**Problem:** Session lost after disconnect

**Solution:** This is expected behavior. Creator Mode doesn't persist state.

## Security Considerations

1. **No Authentication** - WebSocket endpoint is open (add auth for production)
2. **Resource Limits** - No limits on regeneration attempts (add throttling)
3. **Input Validation** - Minimal validation on payload (add stricter checks)
4. **Rate Limiting** - Not implemented (add for production)

## Integration with Existing Code

Creator Mode integrates seamlessly:

- ✅ **No changes to existing endpoints**
- ✅ **No changes to pipeline functions**
- ✅ **No changes to database schema**
- ✅ **No new dependencies**
- ✅ **Fully isolated implementation**

All existing features continue to work exactly as before.
