# Pharma Video Generator - Complete Architecture

## Two Pipelines, Shared Infrastructure

```
┌─────────────────────────────────────────────────────────────────────┐
│                         SHARED COMPONENTS                           │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌──────────────┐ │
│  │ LLM Client │  │ TTS Engine │  │ JSON Utils │  │  Video ID    │ │
│  │  (OpenAI)  │  │  (Stage 4) │  │            │  │  Generator   │ │
│  └────────────┘  └────────────┘  └────────────┘  └──────────────┘ │
│  ┌────────────┐  ┌────────────┐                                    │
│  │   Script   │  │   Paths    │                                    │
│  │ Generator  │  │   Config   │                                    │
│  │ (Stage 3)  │  │            │                                    │
│  └────────────┘  └────────────┘                                    │
└─────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────┬──────────────────────────────────┐
│   PIPELINE 1: PEXELS + REMOTION  │   PIPELINE 2: MANIM (MoA)        │
│   (Product Ads, Patient Videos)  │   (Educational, MoA Videos)      │
├──────────────────────────────────┼──────────────────────────────────┤
│                                  │                                  │
│  POST /create                    │  POST /create-moa                │
│  {                               │  {                               │
│    "topic": "...",               │    "drug_name": "...",           │
│    "video_type": "product_ad",   │    "condition": "...",           │
│    "brand_name": "..."           │    "target_audience": "...",     │
│  }                               │    "quality": "high"             │
│                                  │  }                               │
│  ↓                               │  ↓                               │
│  ┌──────────────────────────┐   │  ┌──────────────────────────┐   │
│  │ Stage 1: Scene Planning  │   │  │ Stage 1: MoA Scenes      │   │
│  │ (Pexels-focused scenes)  │   │  │ (Animation-focused)      │   │
│  └──────────────────────────┘   │  └──────────────────────────┘   │
│  ↓                               │  ↓                               │
│  ┌──────────────────────────┐   │  ┌──────────────────────────┐   │
│  │ Stage 3: Script (SHARED) │   │  │ Stage 3: Script (SHARED) │   │
│  │ Generate narration       │   │  │ Generate narration       │   │
│  └──────────────────────────┘   │  └──────────────────────────┘   │
│  ↓                               │  ↓                               │
│  ┌──────────────────────────┐   │  ┌──────────────────────────┐   │
│  │ Stage 2: Pexels + TSX    │   │  │ Stage 2: Manim Code Gen  │   │
│  │ - Download media         │   │  │ - Generate Python code   │   │
│  │ - Save to public/media/  │   │  │ - Save to manim/scenes/  │   │
│  └──────────────────────────┘   │  └──────────────────────────┘   │
│  ↓                               │  ↓                               │
│  ┌──────────────────────────┐   │  ┌──────────────────────────┐   │
│  │ Stage 4: TTS (SHARED)    │   │  │ Stage 4: TTS (SHARED)    │   │
│  │ Generate audio/scene_X   │   │  │ Generate audio/scene_X   │   │
│  └──────────────────────────┘   │  └──────────────────────────┘   │
│  ↓                               │  ↓                               │
│  ┌──────────────────────────┐   │  ┌──────────────────────────┐   │
│  │ Stage 5: Remotion Render │   │  │ Stage 5: Manim Render    │   │
│  │ - npx remotion render    │   │  │ - manim render scenes    │   │
│  │ - Outputs final.mp4      │   │  │ - Combine with audio     │   │
│  │                          │   │  │ - Concatenate scenes     │   │
│  │                          │   │  │ - Output final_moa.mp4   │   │
│  └──────────────────────────┘   │  └──────────────────────────┘   │
│  ↓                               │  ↓                               │
│  videos/{id}/final.mp4           │  videos/{id}/final_moa.mp4       │
└──────────────────────────────────┴──────────────────────────────────┘
                                   │
                                   ↓
                        ┌──────────────────────┐
                        │  GET /video/{id}     │
                        │  (Serves both types) │
                        └──────────────────────┘
```

## File Structure

```
backend/app/
├── main.py                         # FastAPI app with both pipelines
├── paths.py                        # Directory configuration
├── prompts/
│   ├── scene_planner_pharma.txt    # Pipeline 1 scenes
│   ├── scene_planner_moa.txt       # Pipeline 2 scenes (NEW)
│   ├── script_writer_pharma.txt    # SHARED by both
│   └── manim_generator.txt         # Pipeline 2 Manim (NEW)
├── stages/
│   ├── stage1_scenes.py            # Pipeline 1
│   ├── stage1_moa_scenes.py        # Pipeline 2 (NEW)
│   ├── stage2_remotion.py          # Pipeline 1
│   ├── stage2_moa_manim.py         # Pipeline 2 (NEW)
│   ├── stage3_script.py            # SHARED
│   ├── stage4_tts.py               # SHARED
│   ├── stage5_render.py            # Pipeline 1
│   └── stage5_moa_render.py        # Pipeline 2 (NEW)
├── utils/
│   ├── llm.py                      # SHARED
│   ├── json_safe.py                # SHARED
│   ├── generate_uid.py             # SHARED
│   └── pexels_client.py            # Pipeline 1 only
└── outputs/
    ├── scenes.json                 # Generated
    ├── script.json                 # Generated
    ├── scenes_with_media.json      # Generated
    ├── audio/{video_id}/           # SHARED (TTS output)
    ├── manim/{video_id}/           # Pipeline 2
    │   ├── scenes/
    │   │   ├── scene_1.py
    │   │   └── scenes_data.json
    │   └── videos/                 # Manim renders
    └── videos/{video_id}/          # Final outputs
        ├── final.mp4               # Pipeline 1
        └── final_moa.mp4           # Pipeline 2

remotion/
├── public/
│   ├── media/{video_id}/           # Downloaded Pexels content
│   └── audio/{video_id}/           # Symlink or copy of audio
└── src/
    └── PharmaVideo.tsx             # Pipeline 1 component
```

## API Endpoints

### Pipeline 1: Pexels + Remotion
```http
POST /create
Content-Type: application/json

{
  "topic": "New diabetes medication",
  "video_type": "product_ad",
  "brand_name": "GlucoFix"
}
```

### Pipeline 2: Manim MoA
```http
POST /create-moa
Content-Type: application/json

{
  "drug_name": "Metformin",
  "condition": "Type 2 Diabetes",
  "target_audience": "patients",
  "quality": "high"
}
```

### Video Retrieval (Both)
```http
GET /video/{video_id}
```

## Component Reuse

| Component | Pipeline 1 | Pipeline 2 | Notes |
|-----------|------------|------------|-------|
| LLM Client | ✅ | ✅ | Same OpenAI calls |
| Script Gen | ✅ | ✅ | stage3_script.py |
| TTS | ✅ | ✅ | stage4_tts.py |
| Video ID | ✅ | ✅ | generate_uid.py |
| JSON Utils | ✅ | ✅ | json_safe.py |
| Scene Planning | Different | Different | Separate prompts |
| Media/Animation | Pexels API | Manim | Different stage 2 |
| Rendering | Remotion | Manim+FFmpeg | Different stage 5 |
| Video Serving | ✅ | ✅ | Same endpoint |

## Key Differences

### Pipeline 1 (Pexels + Remotion)
- **Use case**: Marketing, patient awareness, brand videos
- **Media**: Real photos/videos from Pexels
- **Rendering**: Remotion (React-based)
- **Style**: Photorealistic, stock footage
- **Speed**: Fast (2-5 min total)

### Pipeline 2 (Manim MoA)
- **Use case**: Medical education, MoA explanations
- **Media**: Programmatic animations
- **Rendering**: Manim (Python-based)
- **Style**: Clean diagrams, white background
- **Speed**: Slower (5-15 min depending on quality)