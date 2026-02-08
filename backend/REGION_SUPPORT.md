# Region-Based Media Fetching Support

## Overview

The `/create` endpoint now supports region-based demographic filtering for Pexels media fetching. This allows you to generate videos with culturally appropriate imagery by specifying the target region.

## Supported Regions

| Region Code | Demographic Modifier | TTS Voice | Description |
|------------|---------------------|-----------|-------------|
| `india` | Indian, South Asian | en-IN-NeerjaNeural | Indian English accent |
| `africa` | African, Black | en-ZA-LeahNeural | South African English accent |
| `europe` | European, Caucasian | en-GB-SoniaNeural | British English accent |
| `east_asia` | East Asian, Asian | en-SG-LunaNeural | Singaporean English accent |
| `middle_east` | Middle Eastern | en-AE-FatimaNeural | UAE English accent |
| `latin_america` | Latin American, Hispanic | en-US-JennyNeural | US English accent |
| `north_america` | American, North American | en-US-JennyNeural | US English accent |
| `southeast_asia` | Southeast Asian | en-PH-RosaNeural | Philippine English accent |
| `global` | *(no filter)* | en-US-JennyNeural | US English accent (neutral) |

## How It Works

### 1. Search Term Enhancement

When a region is specified, the system automatically enhances Pexels search terms with demographic context:

**Example:**
```
Original: "doctor explaining to patient"
+ region: "india"
→ Enhanced: "Indian doctor explaining to patient"

Original: "person applying pain relief cream"
+ region: "africa"
→ Enhanced: "African person applying pain relief cream"
```

### 2. Pipeline Flow

1. **Scene Planning** (Stage 1)
   - LLM generates scenes with Pexels search terms
   - Region context is added to the prompt to guide term generation

2. **Media Fetching** (Stage 2)
   - Search terms are enhanced with regional modifiers
   - Pexels API is queried with enhanced terms
   - Media featuring people from the specified region is prioritized

3. **Script Generation** (Stage 3)
   - Narration script is generated for each scene

4. **Text-to-Speech** (Stage 4)
   - **Region-appropriate voice is selected** (e.g., Indian English for `india`)
   - Azure Neural TTS generates audio with culturally appropriate accent
   - All voices speak English, but with regional pronunciation

5. **Video Composition** (Stage 5)
   - Fetched media and audio are integrated into the final video
   - Result: culturally appropriate video content with matching voiceover

## API Usage

### Using the `/create` Endpoint

**Form Data Parameters:**
```
POST /create
Content-Type: multipart/form-data

Fields:
  - topic: "Pain relief medication"
  - video_type: "product_ad"
  - brand_name: "PainAway"
  - region: "india"        <-- NEW PARAMETER
  - persona: "professional narrator"
  - tone: "clear and reassuring"
  - logo: [file]
  - image: [file]
  - documents: [files]
```

### Example Request (Python)

```python
import requests

url = "http://localhost:8000/create"
files = {
    'logo': open('logo.png', 'rb'),
}
data = {
    'topic': 'Diabetes management medication',
    'video_type': 'patient_awareness',
    'brand_name': 'GlucoControl',
    'region': 'india',  # Fetch Indian-context media
    'persona': 'friendly health educator',
    'tone': 'warm and encouraging'
}

response = requests.post(url, files=files, data=data)
print(response.json())
```

### Example Request (cURL)

```bash
curl -X POST "http://localhost:8000/create" \
  -F "topic=Hypertension medication awareness" \
  -F "video_type=patient_awareness" \
  -F "brand_name=HeartCare" \
  -F "region=africa" \
  -F "persona=professional narrator" \
  -F "tone=clear and reassuring" \
  -F "logo=@logo.png"
```

### Getting Supported Regions

```bash
GET /supported-regions
```

**Response:**
```json
{
  "supported_regions": [
    "india",
    "africa",
    "europe",
    "east_asia",
    "middle_east",
    "latin_america",
    "north_america",
    "southeast_asia",
    "global"
  ],
  "region_details": {
    "india": {
      "modifiers": ["Indian", "South Asian", "from India"],
      "description": "Fetches media featuring people from India"
    },
    "africa": {
      "modifiers": ["African", "Black", "from Africa"],
      "description": "Fetches media featuring people from Africa"
    },
    // ... more regions
  },
  "usage": "Pass 'region' parameter to /create endpoint"
}
```

## Real-World Examples

### Example 1: Diabetes Campaign for India

```python
data = {
    'topic': 'Managing type 2 diabetes with diet and exercise',
    'video_type': 'patient_awareness',
    'brand_name': 'DiabeCare',
    'region': 'india',
    'persona': 'warm health educator',
    'tone': 'encouraging and supportive'
}
```

**Result:** Video features Indian patients, families, and healthcare professionals in culturally relevant settings.
**Voiceover:** Indian English accent (en-IN-NeerjaNeural)

### Example 2: Pain Relief Product for Africa

```python
data = {
    'topic': 'Fast-acting pain relief for joint pain',
    'video_type': 'product_ad',
    'brand_name': 'FlexRelief',
    'region': 'africa',
    'persona': 'professional narrator',
    'tone': 'clear and confident'
}
```

**Result:** Video shows African individuals using the product in authentic scenarios.
**Voiceover:** South African English accent (en-ZA-LeahNeural)

### Example 3: Global Campaign

```python
data = {
    'topic': 'Heart health awareness',
    'video_type': 'patient_awareness',
    'brand_name': 'CardioHealth',
    'region': 'global',  # or omit region parameter
    'persona': 'professional narrator',
    'tone': 'informative and caring'
}
```

**Result:** Video uses diverse, global imagery without specific demographic targeting.
**Voiceover:** Neutral US English accent (en-US-JennyNeural)

## Azure Neural TTS Voices

### Voice Selection by Region

The system automatically selects culturally appropriate Azure Neural TTS voices based on the region:

- **India** (`en-IN-NeerjaNeural`): Natural Indian English accent
- **Africa** (`en-ZA-LeahNeural`): South African English accent
- **Europe** (`en-GB-SoniaNeural`): British English accent
- **East Asia** (`en-SG-LunaNeural`): Singaporean English accent
- **Middle East** (`en-AE-FatimaNeural`): UAE/Middle Eastern English accent
- **Latin America** (`en-US-JennyNeural`): Neutral US English (widely understood)
- **North America** (`en-US-JennyNeural`): US English accent
- **Southeast Asia** (`en-PH-RosaNeural`): Philippine English accent
- **Global/Default** (`en-US-JennyNeural`): Neutral US English

### Voice Features

All voices:
- ✅ Speak **English** (no language barriers)
- ✅ Are **neural** (natural, human-like quality)
- ✅ Are **female voices** (professional, clear tone)
- ✅ Support **SSML** for advanced control (if needed)
- ✅ Have regionally appropriate **pronunciation and accent**

### Why Region-Appropriate Voices?

**Cultural Connection:** Hearing a familiar accent builds trust and relatability with the target audience.

**Example:**
- A diabetes awareness video for India with an Indian English narrator feels more authentic
- A pain relief ad for Africa with a South African English voice resonates better locally
- A global campaign with neutral US English maintains broad accessibility

## Technical Details

### Files Modified

1. **`app/utils/region_mapper.py`** (NEW)
   - Core region mapping logic
   - Search term enhancement functions
   - Demographic modifier mappings

2. **`app/stages/stage1_scenes.py`**
   - Accepts `region` parameter
   - Adds region context to LLM prompt

3. **`app/stages/stage2_remotion.py`**
   - `enrich_scenes_with_media()` accepts `region` parameter
   - Applies regional modifiers to Pexels search terms
   - `run_stage2()` passes region through pipeline

4. **`app/stages/stage4_tts.py`** (NEW FEATURE)
   - Region-to-voice mapping (`REGION_VOICE_MAP`)
   - `get_voice_for_region()` function selects appropriate Azure Neural TTS voice
   - `generate_tts_for_scene()` accepts `region` parameter
   - `tts_generate()` passes region to voice selection

5. **`app/main.py`**
   - `/create` endpoint accepts `region` form field
   - New `/supported-regions` endpoint
   - Updated `CreateRequest` model
   - Passes `region` to Stage 1, 2, and 4

### Implementation Notes

- **Optional Parameter:** Region is completely optional; omitting it uses default (global) behavior
- **Case Insensitive:** Region codes are case-insensitive (`"India"` = `"india"`)
- **Fallback Handling:** Unknown regions default to no demographic filtering
- **Logging:** Enhanced search terms are logged for transparency
- **Backward Compatible:** Existing API calls without `region` parameter work unchanged

## Testing

Run the test suite:

```bash
cd backend
python3 test_region_support.py
```

**Test Coverage:**
- Region modifier retrieval
- Search term enhancement (single and batch)
- Real-world pharmaceutical scenarios
- Edge cases (None, unknown regions, "global")

## Best Practices

### When to Use Regional Filtering

✅ **Use regional filtering when:**
- Creating market-specific campaigns
- Targeting specific geographic audiences
- Regulatory requirements for localized content
- Cultural relevance is critical

❌ **Don't use regional filtering when:**
- Creating globally distributed content
- Media availability is limited for specific regions
- Campaign is intentionally diverse/multicultural

### Choosing the Right Region

- **Match target market:** Use the region where the video will be distributed
- **Consider availability:** Some regions may have more Pexels media than others
- **Test results:** Preview generated videos to ensure cultural appropriateness
- **Use "global":** For intentionally diverse content

## Limitations

1. **Pexels Availability:** Media availability varies by region; some searches may return fewer results
2. **Search Term Quality:** Effectiveness depends on how well the LLM generates culturally-appropriate search terms
3. **Demographic Accuracy:** Pexels media may not always perfectly match demographic expectations
4. **No Video Editing:** System doesn't perform facial recognition or content analysis; relies on Pexels search accuracy

## Future Enhancements

- [ ] Add more granular region options (e.g., specific countries)
- [ ] Support for multiple regions in a single video
- [ ] Fallback strategies when region-specific media is unavailable
- [ ] Analytics on region-based media fetch success rates
- [ ] Integration with additional stock media providers

## Support

For issues or questions about region-based fetching:
- Check test results: `python3 test_region_support.py`
- Review logs for search term enhancement
- Verify region code using `/supported-regions` endpoint
- Ensure Pexels API key is configured

## Changelog

### Version 1.0.0 (February 2026)
- ✨ Initial release
- ✅ Support for 9 regions
- ✅ Search term enhancement
- ✅ `/supported-regions` API endpoint
- ✅ Comprehensive test suite
- ✅ Documentation
