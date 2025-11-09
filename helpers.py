from datetime import datetime, date
import re

__all__ = [
    "format_date",
    "filter_orders_by_date",
    "has_date_hint",
]

def format_date(d: date | None) -> str:
    """Format date object for readable display."""
    return d.strftime("%b %d, %Y") if d else "Unknown"


def filter_orders_by_date(orders, start_date: date, end_date: date):
    """Filter orders by createdTime within inclusive [start_date, end_date].

    Expects each order to have ISO8601 createdTime with 'Z'.
    Silently skips malformed timestamps.
    """
    filtered = []
    for order in orders:
        try:
            created = datetime.fromisoformat(order["createdTime"].replace("Z", "+00:00")).date()
            if start_date <= created <= end_date:
                filtered.append(order)
        except Exception:
            continue
    return filtered


_MONTH_PATTERN = r"jan(uary)?|feb(ruary)?|mar(ch)?|apr(il)?|may|jun(e)?|jul(y)?|aug(ust)?|sep(t|tember)?|oct(ober)?|nov(ember)?|dec(ember)?"

_DATE_HINT_PATTERNS = [
    rf"\b({_MONTH_PATTERN})\b",
    # Relative periods
    r"\b(today|yesterday|tomorrow)\b",
    r"\b(last|past|previous)\s+(day|week|month|year|\d+\s*(days?|weeks?|months?|years?))\b",
    r"\b(next)\s+(day|week|month|year)\b",
    r"\bthis\s+(week|month|year|quarter)\b",
    r"\bquarter\s*\d\b",
    # Numeric dates
    r"\b\d{4}-\d{2}-\d{2}\b",  # ISO
    r"\b\d{1,2}[/-]\d{1,2}([/-]\d{2,4})?\b",  # 06/11 or 6-11-24
    # Day with ordinal + month
    rf"\b\d{{1,2}}(st|nd|rd|th)?\b\s+(of\s+)?\b({_MONTH_PATTERN})\b",
    # Range indicators
    r"\b(from|between)\b.*\b(to|and|through|thru|till|until)\b",
    r"\b(on|by|before|after|since|during)\b\s+",
]

def has_date_hint(text: str) -> bool:
    """Return True if query text contains a date/time reference.

    Used to decide whether to auto-default the date range.
    """
    t = text.lower()
    for pattern in _DATE_HINT_PATTERNS:
        if re.search(pattern, t):
            return True
    return False
