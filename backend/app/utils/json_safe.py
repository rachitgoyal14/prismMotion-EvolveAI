import json
import re


def extract_json(text: str) -> dict:
    """
    Extract the FIRST valid JSON object from LLM output.
    Handles:
    - Markdown ```json fences
    - Extra text before/after JSON
    - Partial hallucinated output
    """
    if not text or not isinstance(text, str):
        raise ValueError("LLM output is empty or invalid")

    # 1️⃣ Remove markdown fences if present
    cleaned = re.sub(r"```(?:json)?|```", "", text, flags=re.IGNORECASE).strip()

    # 2️⃣ Fast path: pure JSON
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 3️⃣ Extract first JSON object
    match = re.search(r"\{[\s\S]*\}", cleaned)
    if not match:
        raise ValueError(
            f"No JSON object found in LLM output:\n{cleaned[:300]}"
        )

    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Invalid JSON extracted from LLM output: {e}\n"
            f"Extracted snippet:\n{match.group(0)[:300]}"
        )