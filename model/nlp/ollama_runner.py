import json
import re
import subprocess
from .prompt import build_prompt

KNOWN_KEYS = {
    "intent": "intent",
    "room": "room",
    "building": "building",
    "date": "date",
    "start": "start",
    "end": "end",
    "booking_id": "booking_id",
    # tolerate common variants in chatter
    "booking id": "booking_id",
}

def _extract_first_json(text: str) -> str | None:
    """Return the first balanced {...} JSON object, or None."""
    # strip fences if any
    if "```" in text:
        text = text.replace("```json", "```").replace("```JSON", "```")
        for part in text.split("```"):
            if "{" in part:
                text = part
                break
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    for i, ch in enumerate(text[start:], start=start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start:i+1]
    return None

def _kv_fallback(text: str) -> dict | None:
    """
    Parse lines like 'Intent: book' / 'Room: SJT 315' when model ignores JSON.
    Returns a dict with lowercase keys if anything useful is found.
    """
    lines = [l.strip() for l in text.splitlines() if ":" in l]
    out = {}
    for line in lines:
        # match 'Key: value' up to the end of the line
        m = re.match(r"^\s*([A-Za-z_ ]+)\s*:\s*(.+?)\s*$", line)
        if not m:
            continue
        k_raw, v = m.group(1).strip().lower(), m.group(2).strip()
        k = KNOWN_KEYS.get(k_raw)
        if k and v:
            out[k] = v
    return out or None

def run_tinyllama_json(utterance: str, model_name: str = "room-nlu") -> dict:
    """
    Calls TinyLlama locally via Ollama and returns a dict.
    Enforces JSON, but if the model still chats, falls back to parsing 'Key: Value' lines.
    """
    prompt = build_prompt(utterance)
    res = subprocess.run(
        ["ollama", "run", model_name],
        input=prompt.encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True
    )
    raw = res.stdout.decode("utf-8").strip()

    # 1) Try strict JSON
    blob = _extract_first_json(raw)
    if blob is not None:
        try:
            return json.loads(blob)
        except Exception:
            pass  # attempt fallback

    # 2) Fallback: parse 'Intent: ...' style chatter
    kv = _kv_fallback(raw)
    if kv:
        return kv

    # 3) If nothing worked, raise with raw for debugging
    raise ValueError(f"No JSON found and KV fallback failed. Output head:\n{raw[:300]}")
