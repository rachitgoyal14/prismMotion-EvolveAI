import json
import re


def extract_json(text: str):
    """Extract the first JSON object from a string."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError("No JSON object found in LLM output")
    return json.loads(match.group())
