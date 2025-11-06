from flask import Flask, request, jsonify
from nlp.ollama_runner import run_tinyllama_json
from nlp.regex_parser import regex_parse


app = Flask(__name__)


@app.get("/healthz")
def health_check():
    """Simple health endpoint."""
    return jsonify({"status": "ok"}), 200


@app.post("/parse")
def parse_text():
    """
    POST /parse
    {
      "utterance": "Reserve SJT 315 11 Sept 14:00 to 16:00 projector needed",
      "model": "room-nlu"  # optional, defaults to room-nlu
    }
    """
    data = request.get_json(silent=True) or {}
    utterance = (data.get("utterance") or "").strip()
    model = data.get("model", "room-nlu")

    if not utterance:
        return jsonify({"error": "utterance is required"}), 400

    try:
        result = run_tinyllama_json(utterance, model_name=model)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": f"{type(e).__name__}: {e}"}), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=False)
