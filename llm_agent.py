import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
_MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
_MODEL = None
if _API_KEY:
    try:
        genai.configure(api_key=_API_KEY)
        _MODEL = genai.GenerativeModel(_MODEL_NAME)
    except Exception:
        _MODEL = None

def analyze_sales_data(query, intent, facts, start_date=None, end_date=None):
    date_info = ""
    if start_date and end_date:
        if start_date == end_date:
            date_info = f"for {start_date.strftime('%B %d, %Y')}"
        else:
            date_info = f"from {start_date.strftime('%B %d, %Y')} to {end_date.strftime('%B %d, %Y')}"

    prompt = f"""
You are a sales insights assistant.
Question: "{query}"
Intent: {intent}
Date range: {date_info if date_info else "unspecified"}

Facts computed from real sales data:
{json.dumps(facts, indent=2)}

Summarize these results clearly in natural language. 
Keep it factual and formatted in bullet or numbered lists.
    """

    if not _MODEL:
        return _fallback_summary(intent, facts, date_info, reason="LLM unavailable")
    try:
        response = _MODEL.generate_content(prompt)
        if response and getattr(response, "text", None):
            return response.text.strip()
        return _fallback_summary(intent, facts, date_info, reason="Empty LLM response")
    except Exception:
        return _fallback_summary(intent, facts, date_info, reason="LLM error")


def _fallback_summary(intent, facts, date_info, reason="fallback"):
    header = f"Insight ({reason})"
    lines = [header, f"Intent: {intent}", f"Date: {date_info or 'unspecified'}"]
    if not facts:
        lines.append("No facts available.")
    else:
        for k, v in facts.items():
            lines.append(f"- {k}: {v}")
    return "\n".join(lines)

