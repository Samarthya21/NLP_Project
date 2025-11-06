import json
import subprocess
import sys
from prompt import build_prompt

def extract_first_json(text: str) -> str:
    """Find the first balanced JSON object in the model's output."""
    if "```" in text:  
        text = text.replace("```json", "```").replace("```JSON", "```")
        parts = text.split("```")
        for part in parts:
            if "{" in part:
                text = part
                break

    start = text.find("{")
    if start == -1:
        raise ValueError(f"No JSON object found in output:\n{text[:200]}")

    depth = 0
    for i, ch in enumerate(text[start:], start=start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start:i+1]

    raise ValueError("Unbalanced braces in model output.")


def run_tinyllama(utterance: str, model: str = "room-nlu") -> dict:
    """
    Call the local Ollama model with the built prompt and return parsed JSON.
    """
    prompt = build_prompt(utterance)
    res = subprocess.run(
        ["ollama", "run", model],
        input=prompt.encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True
    )

    raw_output = res.stdout.decode("utf-8").strip()
    try:
        json_text = extract_first_json(raw_output)
        return json.loads(json_text)
    except Exception as e:
        print("\n--- RAW MODEL OUTPUT ---\n", raw_output, "\n-------------------------\n")
        raise e


if __name__ == "__main__":
    if len(sys.argv) > 1:
        utterance = " ".join(sys.argv[1:])
    else:
        utterance = "Reserve SJT 315 11 Sept 14:00 to 16:00 projector needed"

    try:
        result = run_tinyllama(utterance)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as ex:
        print(f"Error: {ex}")
