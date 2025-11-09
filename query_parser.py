import re
import dateparser
from datetime import datetime, timedelta

def validate_date_range(start_date, end_date, available_start, available_end):
    """
    Check if the user-specified date range is within the available data range.

    Args:
        start_date (date): Start of the user-specified range.
        end_date (date): End of the user-specified range.
        available_start (date): Start of the available data range.
        available_end (date): End of the available data range.

    Returns:
        bool: True if the range is valid, False otherwise.
    """
    return available_start <= start_date <= available_end and available_start <= end_date <= available_end

def _int_or_one(text: str) -> int:
    """Convert numeric text to int, default to 1 when no number is found.

    Examples: '3' -> 3, 'one' -> 1 (dateparser will often handle words), '' -> 1
    """
    try:
        return int(text)
    except Exception:
        # fallback
        return 1


_NUMBER_WORDS = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
}


def get_days_from_query(query: str) -> int:
    """Return an integer number of days implied by the query.

    Examples:
    - 'past 3 days' -> 3
    - 'last 2 weeks' -> 14
    - 'in the past 10 days' -> 10
    - 'last week' -> 7
    - 'past month' -> 30 (approx)
    - If no span found, returns 0
    """

    q = (query or "").lower()

    # direct digits
    m = re.search(r"(\d+)\s*(day|days|week|weeks|month|months)\b", q)
    if m:
        n = int(m.group(1))
        unit = m.group(2)
        if unit.startswith("day"):
            return n
        if unit.startswith("week"):
            return n * 7
        if unit.startswith("month"):
            return n * 30

    # number words
    m2 = re.search(r"([a-z]+)\s*(day|days|week|weeks|month|months)\b", q)
    if m2:
        word = m2.group(1)
        unit = m2.group(2)
        n = _NUMBER_WORDS.get(word, None)
        if n is not None:
            if unit.startswith("day"):
                return n
            if unit.startswith("week"):
                return n * 7
            if unit.startswith("month"):
                return n * 30

    # shorthand keywords
    if re.search(r"\blast week\b", q):
        return 7
    if re.search(r"\bpast week\b", q):
        return 7
    if re.search(r"\blast month\b|\bpast month\b", q):
        return 30

    return 0


def parse_date_range(query: str):
    """
    Parse a natural-language date range and return (start_date, end_date).

    Supported patterns (examples):
    - "past 3 days", "in the past 10 days"
    - "last 2 weeks", "last week" (week(s) -> 7-day multiples)
    - "past month" (approximated as 30 days)
    - "yesterday", "today"
    - Single dates (delegated to dateparser.parse)

    Returns a tuple of date objects (start_date, end_date).
    """

    q = (query or "").lower()
    now = datetime.now()

    # direct keywords
    if "yesterday" in q:
        start = now - timedelta(days=1)
        end = start
        return start.date(), end.date()

    if "today" in q:
        return now.date(), now.date()

    # regex patterns for relative spans like 'past 3 days' or 'last 2 weeks'
    # supports optional 'in the' or 'the' prefixes
    patterns = [
        # past N days / in the past N days
        (r"(?:past|in the past|in past)\s+(\d+)\s+day", lambda n: timedelta(days=_int_or_one(n))),
        (r"(?:last|past)\s+(\d+)\s+week", lambda n: timedelta(weeks=_int_or_one(n))),
        (r"(?:last|past)\s+(\d+)\s+month", lambda n: timedelta(days=30 * _int_or_one(n))),
        (r"(?:past|in the past|in past)\s+(\d+)\s+day", lambda n: timedelta(days=_int_or_one(n))),
    ]

    for pat, factory in patterns:
        m = re.search(pat, q)
        if m:
            n = m.group(1)
            span = factory(n)
            end = now
            start = now - span
            return start.date(), end.date()

    # Handle 'last week' (no number) meaning last 7 days
    if re.search(r"\blast week\b", q):
        return (now - timedelta(days=7)).date(), now.date()

    # 'past N days' with words (e.g., 'past three days') - try to extract number words
    m_words = re.search(r"(?:past|last|in the past)\s+([a-z]+)\s+day", q)
    if m_words:
        # try to parse words via dateparser (it can parse "three days ago")
        try:
            parsed = dateparser.parse(m_words.group(0))
            if parsed:
                start = parsed
                end = now
                return start.date(), end.date()
        except Exception:
            pass

    # Fallback: try parsing a single date with dateparser
    parsed = dateparser.parse(query, settings={'PREFER_DATES_FROM': 'past'})
    if parsed:
        print(f"[DEBUG] dateparser.parse('{query}') returned: {parsed}")
        return parsed.date(), parsed.date()
    else:
        print(f"[DEBUG] dateparser.parse('{query}') could not parse the date. Returning today as fallback.")

    # As last-resort return today
    return now.date(), now.date()


if __name__ == "__main__":
    # small demo of common inputs
    examples = [
        "past 3 days",
        "last 2 weeks",
        "in the past 10 days",
        "yesterday",
        "today",
        "2025-01-01",
    ]

    for ex in examples:
        s, e = parse_date_range(ex)
        days = get_days_from_query(ex)
        print(f"{ex!r} -> {s} to {e} (days={days})")
