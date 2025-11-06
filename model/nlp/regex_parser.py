import re

def regex_parse(text: str) -> dict:
    """
    Quick deterministic slot extraction.
    Returns dict with any of: intent, room, date, start, end, booking_id.
    """

    out = {}

    # Intent — simple keyword map
    intents = {
        "book": ["book", "reserve", "schedule"],
        "cancel": ["cancel", "delete"],
        "check_availability": ["available", "free", "vacant"],
    }
    lower = text.lower()
    for intent, words in intents.items():
        if any(w in lower for w in words):
            out["intent"] = intent
            break

    # Room patterns — e.g. SJT 315, TT 101, LH-204
    m = re.search(r"\b([A-Z]{2,}-?\s?\d{2,3})\b", text)
    if m:
        out["room"] = m.group(1).strip()

    # Date — 11 Sept / 11/09 / tomorrow / next Friday
    m = re.search(r"\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec))\b", text, re.I)
    if not m:
        m = re.search(r"\b(\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)\b", text)
    if not m:
        m = re.search(r"\b(today|tomorrow|next\s+\w+)\b", text, re.I)
    if m:
        out["date"] = m.group(1).strip()

    # Time range — 14:00 to 16:00 / 2 pm - 4 pm
    m = re.search(r"\b((?:[01]?\d|2[0-3])(?::[0-5]\d)?\s?(?:am|pm)?)\s*(?:-|–|to)\s*((?:[01]?\d|2[0-3])(?::[0-5]\d)?\s?(?:am|pm)?)\b", text, re.I)
    if m:
        out["start"], out["end"] = m.group(1).strip(), m.group(2).strip()

    # Booking ID — BK-####
    m = re.search(r"\b(BK-\d+)\b", text, re.I)
    if m:
        out["booking_id"] = m.group(1).upper()

    return out
