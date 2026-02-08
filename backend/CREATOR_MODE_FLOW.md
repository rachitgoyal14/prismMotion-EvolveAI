# Creator Mode Message Flow

## Connection & Session Start

```
Client                                Server
  │                                     │
  │───── WebSocket Connect ────────────>│
  │                                     │
  │<──── WebSocket Accept ──────────────│
  │                                     │
  │                                     │
  │  {                                  │
  │    "action": "start",               │
  │    "video_type": "moa",             │
  │    "payload": {...}                 │
  │  }                                  │
  │─────────────────────────────────────>│
  │                                     │
  │                                     │ [Create Session]
  │                                     │ [Initialize State]
  │                                     │
  │  {                                  │
  │    "status": "session_started",     │
  │    "video_id": "vid_123",           │
  │    "stage_order": [...]             │
  │  }                                  │
  │<─────────────────────────────────────│
  │                                     │
```

## Stage Execution (Scenes)

```
Client                                Server
  │                                     │
  │                                     │ [Execute Scenes Stage]
  │  {                                  │
  │    "status": "stage_running",       │
  │    "stage": "scenes"                │
  │  }                                  │
  │<─────────────────────────────────────│
  │                                     │
  │                                     │ [Call generate_scenes()]
  │                                     │ [Store output]
  │                                     │
  │  {                                  │
  │    "stage": "scenes",               │
  │    "status": "completed",           │
  │    "data": {                        │
  │      "scenes_data": {...},          │
  │      "scene_count": 5               │
  │    },                               │
  │    "next_actions": [                │
  │      "accept",                      │
  │      "regenerate"                   │
  │    ],                               │
  │    "progress": {                    │
  │      "current": 1,                  │
  │      "total": 6                     │
  │    }                                │
  │  }                                  │
  │<─────────────────────────────────────│
  │                                     │
  │                                     │ [PAUSE - Wait for User]
  │                                     │
```

## User Accepts Stage

```
Client                                Server
  │                                     │
  │ [User reviews output]               │
  │ [User clicks "Accept"]              │
  │                                     │
  │  {                                  │
  │    "action": "accept"               │
  │  }                                  │
  │─────────────────────────────────────>│
  │                                     │
  │                                     │ [Advance to next stage]
  │                                     │ [Execute Script Stage]
  │                                     │
  │  {                                  │
  │    "status": "stage_running",       │
  │    "stage": "script"                │
  │  }                                  │
  │<─────────────────────────────────────│
  │                                     │
  │                                     │ [Call generate_script()]
  │                                     │ [Store output]
  │                                     │
  │  {                                  │
  │    "stage": "script",               │
  │    "status": "completed",           │
  │    "data": {...}                    │
  │  }                                  │
  │<─────────────────────────────────────│
  │                                     │
  │                                     │ [PAUSE - Wait for User]
```

## User Regenerates Stage

```
Client                                Server
  │                                     │
  │ [User reviews output]               │
  │ [User clicks "Regenerate"]          │
  │ [User provides feedback]            │
  │                                     │
  │  {                                  │
  │    "action": "regenerate",          │
  │    "feedback": "Make it shorter"    │
  │  }                                  │
  │─────────────────────────────────────>│
  │                                     │
  │                                     │ [Increment version counter]
  │                                     │ [Re-execute SAME stage]
  │                                     │ [Use feedback in prompt]
  │                                     │
  │  {                                  │
  │    "status": "stage_running",       │
  │    "stage": "script",               │
  │    "version": 2                     │
  │  }                                  │
  │<─────────────────────────────────────│
  │                                     │
  │                                     │ [Call generate_script()]
  │                                     │ [Store NEW output]
  │                                     │
  │  {                                  │
  │    "stage": "script",               │
  │    "version": 2,                    │
  │    "status": "completed",           │
  │    "data": {...}                    │
  │  }                                  │
  │<─────────────────────────────────────│
  │                                     │
  │                                     │ [PAUSE - Wait for User]
```

## Error During Stage

```
Client                                Server
  │                                     │
  │                                     │ [Execute TTS Stage]
  │  {                                  │
  │    "status": "stage_running",       │
  │    "stage": "tts"                   │
  │  }                                  │
  │<─────────────────────────────────────│
  │                                     │
  │                                     │ [Call tts_generate()]
  │                                     │ ❌ [ERROR: API timeout]
  │                                     │
  │  {                                  │
  │    "stage": "tts",                  │
  │    "status": "error",               │
  │    "error": "OpenAI API timeout",   │
  │    "next_actions": [                │
  │      "regenerate",                  │
  │      "stop"                         │
  │    ]                                │
  │  }                                  │
  │<─────────────────────────────────────│
  │                                     │
  │                                     │ [PAUSE - Wait for User]
  │                                     │
  │ [User decides to retry]             │
  │                                     │
  │  {                                  │
  │    "action": "regenerate"           │
  │  }                                  │
  │─────────────────────────────────────>│
  │                                     │
  │                                     │ [Retry stage]
```

## Pipeline Complete

```
Client                                Server
  │                                     │
  │ [User accepts "render" stage]       │
  │                                     │
  │  {                                  │
  │    "action": "accept"               │
  │  }                                  │
  │─────────────────────────────────────>│
  │                                     │
  │                                     │ [No more stages]
  │                                     │ [Pipeline complete!]
  │                                     │
  │  {                                  │
  │    "status": "pipeline_complete",   │
  │    "video_id": "vid_123",           │
  │    "video_path": "/path/to/video",  │
  │    "message": "All stages complete!"│
  │  }                                  │
  │<─────────────────────────────────────│
  │                                     │
  │                                     │ [Session ends]
  │                                     │ [State discarded]
  │                                     │
```

## User Stops Session

```
Client                                Server
  │                                     │
  │ [User clicks "Stop"]                │
  │                                     │
  │  {                                  │
  │    "action": "stop"                 │
  │  }                                  │
  │─────────────────────────────────────>│
  │                                     │
  │                                     │ [Mark session inactive]
  │                                     │
  │  {                                  │
  │    "status": "stopped",             │
  │    "message": "Session terminated"  │
  │  }                                  │
  │<─────────────────────────────────────│
  │                                     │
  │───── WebSocket Close ───────────────>│
  │                                     │
  │                                     │ [Cleanup state]
  │                                     │ [Session ends]
```

## State Transitions

```
                    ┌─────────────┐
                    │  Connected  │
                    └──────┬──────┘
                           │
                    [send "start"]
                           │
                           ▼
                    ┌─────────────┐
             ┌─────>│   Running   │
             │      │   Stage N   │
             │      └──────┬──────┘
             │             │
             │      [stage complete]
             │             │
             │             ▼
             │      ┌─────────────┐
             │      │   Waiting   │──┐
             │      │  for User   │  │
             │      └──────┬──────┘  │
             │             │         │
             │    [user "accept"]    │
             │             │         │
             │      N < total?       │
             │             │         │
             │         yes │         │ [user "regenerate"]
             └─────────────┘         │
                           │         │
                       no  │         │
                           ▼         │
                    ┌─────────────┐  │
                    │  Complete!  │  │
                    └─────────────┘  │
                                     │
                                     │
             ┌───────────────────────┘
             │
             │ [increment version]
             │ [store feedback]
             │
             └──> [re-run same stage]


[user "stop" at any point] ──> [Session Stopped]
```

## Concurrent Sessions

```
Client A                Server               Client B
   │                      │                     │
   │── Connect ──────────>│<────── Connect ────│
   │                      │                     │
   │                      │ ┌─────────────────┐ │
   │                      │ │  Session A      │ │
   │── start(moa) ───────>│ │  video_id: 123  │ │
   │                      │ │  stage: scenes  │ │
   │                      │ └─────────────────┘ │
   │                      │                     │
   │                      │ ┌─────────────────┐ │
   │                      │ │  Session B      │ │
   │                      │ │  video_id: 456  │<│── start(doctor_ad)
   │                      │ │  stage: scenes  │ │
   │                      │ └─────────────────┘ │
   │                      │                     │
   │                      │  [Independent       │
   │                      │   execution,        │
   │                      │   no conflicts]     │
   │                      │                     │
   │<── scenes done ──────│                     │
   │                      │                     │
   │                      │────── scenes done ──>│
   │                      │                     │
   │── accept ───────────>│                     │
   │                      │<────── accept ──────│
   │                      │                     │
```

## Key Message Types Summary

| Direction | Message Type | Purpose |
|-----------|-------------|---------|
| Client → Server | `start` | Initialize session |
| Client → Server | `accept` | Approve stage output |
| Client → Server | `regenerate` | Request stage re-execution |
| Client → Server | `stop` | Terminate session |
| Server → Client | `session_started` | Confirm initialization |
| Server → Client | `stage_running` | Stage execution began |
| Server → Client | `completed` | Stage finished successfully |
| Server → Client | `error` | Stage failed |
| Server → Client | `pipeline_complete` | All stages done |
| Server → Client | `stopped` | Session terminated |
