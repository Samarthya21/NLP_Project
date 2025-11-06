def build_prompt(utterance: str) -> str:

    return f"""Task: Extract fields VERBATIM from the input text.
Fields: intent, room, building, date, start, end, booking_id.
Rules:
- COPY EXACT SUBSTRINGS from the text (verbatim). Do NOT normalize or paraphrase.
- If an explicit date/time is present (e.g., '11 Sept', '14:00'), PREFER it over relative terms.
- If multiple times appear in a 'X to Y' or 'X–Y' pattern, map X→start and Y→end.
- If a field is absent, omit it (do not invent).
- Output STRICT JSON only (one object).

Text: Book SJT 315 tomorrow 4 to 6 pm
JSON: {{"intent":"book","room":"SJT 315","date":"tomorrow","start":"4 pm","end":"6 pm"}}

Text: Reserve TT 101 11 Sept 14:00 to 16:00
JSON: {{"intent":"book","room":"TT 101","date":"11 Sept","start":"14:00","end":"16:00"}}

Text: Cancel booking BK-2021
JSON: {{"intent":"cancel","booking_id":"BK-2021"}}

Text: Is LH-204 free next Friday 2pm to 3:30pm?
JSON: {{"intent":"check_availability","room":"LH-204","date":"next Friday","start":"2 pm","end":"3:30 pm"}}

Text: Reserve SJT 315 11 Sept 14:00 to 16:00 projector needed
JSON:
"""
