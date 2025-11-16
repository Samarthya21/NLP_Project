# streamlit_app.py
import streamlit as st
import subprocess, json, re
from datetime import datetime
from typing import Optional, Dict, Tuple

st.set_page_config(page_title="Room NLU - Demo (Regex bypass)", layout="wide")

# -------------------
# Prompt builder
# -------------------
def build_prompt(utterance: str) -> str:
    return f"""Task: Extract fields VERBATIM from the input text.
Fields (lowercase): intent, room, building, date, start, end, booking_id.
Rules:
- COPY EXACT SUBSTRINGS from the text (do NOT normalize or paraphrase).
- If explicit date/time exists (e.g., '11 Sept', '14:00'), PREFER it over relative words.
- For 'X to Y' / 'X-Y' / 'X-Y' patterns, set X as "start" and Y as "end".
- Only set "booking_id" if an exact token like BK-1234 appears in the text.
- Omit any field that is absent.
- OUTPUT ONE JSON OBJECT ONLY (must start with '{' and end with '}'). No other text.

Text: Book SJT 315 tomorrow 4 to 6 pm
JSON: {{"intent":"book","room":"SJT 315","date":"tomorrow","start":"4 pm","end":"6 pm"}}

Text: Reserve TT 101 11 Sept 14:00 to 16:00
JSON: {{"intent":"book","room":"TT 101","date":"11 Sept","start":"14:00","end":"16:00"}}

Text: Cancel booking BK-2021
JSON: {{"intent":"cancel","booking_id":"BK-2021"}}

Text: Is LH-204 free next Friday 2pm to 3:30pm?
JSON: {{"intent":"check_availability","room":"LH-204","date":"next Friday","start":"2 pm","end":"3:30 pm"}}

Text: {utterance}
JSON:
"""

# -------------------
# Ollama runner (subprocess)
# -------------------
def extract_first_json(text: str) -> Optional[str]:
    # trim fenced codeblocks
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

def kv_fallback(text: str) -> Dict[str,str]:
    # parse "Intent: book" style lines
    known = {"intent","room","building","date","start","end","booking_id"}
    out = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        m = re.match(r"^\s*([A-Za-z_ ]+)\s*:\s*(.+?)\s*$", line.strip())
        if not m: continue
        key = m.group(1).strip().lower()
        val = m.group(2).strip()
        key = key.replace("booking id","booking_id")
        if key in known and val:
            out[key] = val
    return out

def run_ollama(utterance: str, model_name: str = "room-nlu") -> Tuple[Dict, str]:
    """
    Returns (parsed_dict_or_empty, raw_output_text)
    """
    prompt = build_prompt(utterance)
    try:
        res = subprocess.run(
            ["ollama", "run", model_name],
            input=prompt.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            timeout=30
        )
    except FileNotFoundError:
        raise RuntimeError("ollama not found on PATH. Install Ollama or put it on PATH.")
    except subprocess.CalledProcessError as e:
        raw = e.stdout.decode("utf-8","ignore") + "\n\nERR:\n" + e.stderr.decode("utf-8","ignore")
        raise RuntimeError(f"ollama run failed:\n{raw}")
    except Exception as e:
        raise RuntimeError(f"Error running ollama: {e}")

    raw = res.stdout.decode("utf-8", "ignore").strip()
    # try JSON
    blob = extract_first_json(raw)
    if blob:
        try:
            parsed = json.loads(blob)
            return parsed, raw
        except Exception:
            # fall through to kv fallback
            pass
    # kv fallback
    kv = kv_fallback(raw)
    return kv, raw

# -------------------
# Regex parser (deterministic first-pass)
# -------------------
ROOM_RE = re.compile(r"\b([A-Z]{2,}-?\s?\d{2,3})\b")
DATE_LONG_RE = re.compile(r"\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec))\b", re.I)
DATE_SLASH_RE = re.compile(r"\b(\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)\b")
RELATIVE_DATE_RE = re.compile(r"\b(today|tomorrow|day after tomorrow|next\s+\w+)\b", re.I)
TIME_RANGE_RE = re.compile(r"\b((?:[01]?\d|2[0-3])(?::[0-5]\d)?\s?(?:am|pm)?)\s*(?:-|–|to)\s*((?:[01]?\d|2[0-3])(?::[0-5]\d)?\s?(?:am|pm)?)\b", re.I)
BK_RE = re.compile(r"\b(BK-\d+)\b", re.I)

def regex_parse(text: str) -> Dict[str,str]:
    out = {}
    lower = text.lower()
    # intent keywords
    if any(w in lower for w in ["book", "reserve", "schedule"]):
        out["intent"] = "book"
    elif any(w in lower for w in ["cancel", "delete"]):
        out["intent"] = "cancel"
    elif any(w in lower for w in ["available", "free", "vacant"]):
        out["intent"] = "check_availability"

    m = ROOM_RE.search(text)
    if m:
        out["room"] = m.group(1).strip()

    m = DATE_LONG_RE.search(text) or DATE_SLASH_RE.search(text) or RELATIVE_DATE_RE.search(text)
    if m:
        out["date"] = m.group(1).strip()

    m = TIME_RANGE_RE.search(text)
    if m:
        out["start"] = m.group(1).strip()
        out["end"] = m.group(2).strip()

    m = BK_RE.search(text)
    if m:
        out["booking_id"] = m.group(1).upper()

    return out

# -------------------
# Sanitize / guardrails (explicit spans override; kill hallucinated booking ids)
# -------------------
def prefer_explicit(original: str, model_out: Dict[str,str]) -> Dict[str,str]:
    out = dict(model_out) if model_out else {}
    # booking id must literally appear
    bk = BK_RE.search(original)
    if bk:
        out["booking_id"] = bk.group(1).upper()
    else:
        out.pop("booking_id", None)
    # explicit date overrides
    m = DATE_LONG_RE.search(original) or DATE_SLASH_RE.search(original)
    if m:
        out["date"] = m.group(1).strip()
    # explicit time range overrides
    m = TIME_RANGE_RE.search(original)
    if m:
        out["start"], out["end"] = m.group(1).strip(), m.group(2).strip()
    # explicit room overrides
    m = ROOM_RE.search(original)
    if m:
        out["room"] = m.group(1).strip()
    else:
        # if model suggested a room not literally in original, drop it
        if "room" in out and out["room"] not in original:
            out.pop("room", None)
    return out

# -------------------
# Compile/normalize to Param-JSON (simple)
# -------------------
MONTHS = {m.lower(): i for i,m in enumerate(["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"], start=1)}

def parse_time(tok: Optional[str]) -> Optional[str]:
    if not tok: return None
    tok = tok.strip().lower()
    m = re.match(r"^(\d{1,2})(?::(\d{2}))?\s*(am|pm)?$", tok)
    if not m:
        return None
    hh = int(m.group(1)); mm = int(m.group(2) or 0); ap = m.group(3)
    if ap == "pm" and hh < 12: hh += 12
    if ap == "am" and hh == 12: hh = 0
    if 0 <= hh < 24 and 0 <= mm < 60:
        return f"{hh:02d}:{mm:02d}"
    return None

def parse_date(tok: Optional[str], now: datetime) -> Optional[str]:
    if not tok: return None
    s = tok.strip().lower()
    if s in ("today","tomorrow","day after tomorrow"):
        delta = {"today":0,"tomorrow":1,"day after tomorrow":2}[s]
        return (now.date() + timedelta(days=delta)).isoformat()
    m = re.match(r"^(\d{1,2})\s*([a-z]{3,})$", s, re.I)
    if m:
        d = int(m.group(1)); mon = m.group(2)[:3].lower()
        if mon in MONTHS:
            year = now.year
            try:
                return datetime(year, MONTHS[mon], d).date().isoformat()
            except:
                return None
    m = re.match(r"^(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?$", s)
    if m:
        d = int(m.group(1)); mon = int(m.group(2)); year = int(m.group(3) or now.year)
        try:
            return datetime(year, mon, d).date().isoformat()
        except:
            return None
    return None

def compile_param_json(chosen: Dict[str,str], now: datetime) -> Dict:
    room_id = None
    if chosen.get("room"):
        room_id = chosen["room"].strip().lower().replace(" ", "-")
    date_iso = parse_date(chosen.get("date"), now) if chosen.get("date") else None
    start_iso = parse_time(chosen.get("start")) if chosen.get("start") else None
    end_iso = parse_time(chosen.get("end")) if chosen.get("end") else None

    template_map = {"book":"book_v1","check_availability":"check_v1","cancel":"cancel_v1","modify":"modify_v1"}
    template = template_map.get(chosen.get("intent","").lower(), "noop")

    args = {
        "room_id": room_id,
        "date": date_iso,
        "start": start_iso,
        "end": end_iso,
        "purpose": None,
        "equip": [],
        "capacity": None,
        "recurrence": None
    }
    warnings = []
    if template == "book_v1":
        if not room_id: warnings.append("missing_room_id")
        if not date_iso: warnings.append("missing_date")
        if not start_iso or not end_iso: warnings.append("missing_time_range")
        if start_iso and end_iso and start_iso >= end_iso: warnings.append("invalid_time_range")

    return {"template": template, "args": args, "warnings": warnings}

# -------------------
# Streamlit UI
# -------------------
st.title("Room Booking NLU — Demo (Regex bypass)")

st.markdown("""
This demo runs a local TinyLlama (Ollama) extractor **and** a deterministic regex pre-parser.
Regex has priority (bypass) for explicit spans — useful when you want provable deterministic behavior.
""")

col1, col2 = st.columns([1,1])

with col1:
    utterance = st.text_area("Utterance", value="Reserve SJT 315 11 Sept 14:00 to 16:00 projector needed", height=120)
    model_name = st.text_input("Model name (ollama)", value="room-nlu")
    use_regex_first = st.checkbox("Regex-first (bypass) (recommended)", value=True)
    force_model = st.checkbox("Always call model (ignore bypass)", value=False)
    run = st.button("Parse")

with col2:
    st.write("Instructions")
    st.markdown("""
    - Ensure `ollama` is installed and available on PATH.
    - If you created a custom model with `Modelfile`, use `room-nlu`. Otherwise use `tinyllama`.
    - This demo shows: **Regex parse**, **Model parse**, **Sanitized/merged**, and **Compiled Param-JSON**.
    - Use this to demo a deterministic bypass to stakeholders.
    """)

if run:
    now = datetime.now()
    # 1) regex
    regex_out = regex_parse(utterance)
    # decide if regex is confident enough: at least intent+room+date or intent+room+start+end
    conf = 0
    for k in ("intent","room","date"): 
        if k in regex_out: conf += 1
    for k in ("start","end"):
        if k in regex_out: conf += 1
    regex_confident = conf >= 3

    st.subheader("Regex parse (pre-parser)")
    st.json(regex_out)

    model_out = {}
    raw_model_text = ""
    if (use_regex_first and regex_confident and not force_model):
        st.info("Regex is confident — skipping model call (bypass active).")
    else:
        st.info("Calling model (Ollama/TinyLlama)...")
        try:
            model_out, raw_model_text = run_ollama(utterance, model_name=model_name)
            # st.subheader("Raw model text (debug)")
            # st.code(raw_model_text[:2000] + ("..." if len(raw_model_text)>2000 else ""))
            st.subheader("Model parsed output")
            st.json(model_out)
        except Exception as e:
            st.error(f"Model call failed: {e}")
            model_out = {}

    # 3) merge: regex overrides model
    merged = dict(model_out or {})
    # overlay regex (regex wins)
    for k,v in regex_out.items():
        merged[k] = v

    # 4) sanitize deterministic overrides
    sanitized = prefer_explicit(utterance, merged)

    st.subheader("Sanitized / Final selection (regex wins)")
    st.json(sanitized)

    # 5) compiled param-json
    compiled = compile_param_json(sanitized, now)
    st.subheader("Compiled Param-JSON (normalized)")
    st.json(compiled)

    # st.markdown("**Notes:** Regex bypass ensures explicit tokens in the user's text always win. Model is used to help fill gaps when regex can't find fields.")
