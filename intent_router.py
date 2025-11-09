import re
from typing import List, Set
import spacy

# Load the spaCy model (ensure 'en_core_web_sm' is installed). Fall back to heuristics if unavailable.
try:
    nlp = spacy.load("en_core_web_sm")
except Exception:
    nlp = None

def detect_intent(query: str) -> str:
    """
    Classify the user's query into a specific analytic intent.
    Uses both keyword-based heuristics and NLP for better accuracy.
    """
    q = (query or "").lower().strip()

    # --- NLP-based processing (optional) ---
    if nlp:
        doc = nlp(query)
        lemmas: List[str] = [t.lemma_.lower() for t in doc if t.lemma_]
        tokens_lower: List[str] = [t.text.lower() for t in doc]
    else:
        # heuristic token base if NLP unavailable
        tokens_lower = re.findall(r"[a-z0-9\-]+", q)
        lemmas = tokens_lower[:]

    L: Set[str] = set(lemmas)
    T: Set[str] = set(tokens_lower)

    # --- Item / product analytics ---
    # Recognize "best selling", "bestselling", "top selling", "most sold"
    if (
        re.search(r"\bbest[-\s]?selling\b", q)
        or "bestseller" in q or "bestsellers" in q
        or "top selling" in q or "top-selling" in q or "topselling" in q
        or "most sold" in q or "most-selling" in q
    ):
        return "top_items"

    if ("sell" in L or "sold" in L or "selling" in T) and ("best" in T or "top" in L or "most" in L):
        # If user mentions count wording, prefer 'most_frequent_items'
        if any(w in q for w in ["how many", "number", "count", "units", "quantity", "qty"]):
            return "most_frequent_items"
        return "top_items"

    if "frequent" in L or ("most" in L and ("common" in L or "frequent" in L)):
        return "most_frequent_items"
    if "average" in L and "item" in (L | T):
        return "average_items_per_order"
    
    # --- Revenue / Value related ---
    if "average" in L and ("order" in L or "purchase" in L or "aov" in (L | T)):
        return "average_order_value"

    # --- Order-level analytics ---
    if any(w in (L | T) for w in ["max", "highest", "largest", "maximum", "biggest", "top"]):
        return "max_order"
    if any(w in (L | T) for w in ["min", "lowest", "smallest", "minimum", "least"]):
        return "min_order"
    if ("how many" in q and "order" in q) or ("order" in (L | T) and ("count" in (L | T) or "number" in (L | T) or "total" in (L | T))):
        return "order_count"

    # --- Discount / employee / category / refund / hour analytics ---
    if "discount" in (L | T) or "promo" in (L | T) or "coupon" in (L | T):
        if any(w in (L | T) for w in ["max", "highest", "largest", "maximum", "biggest"]):
            return "max_discount"
        return "discount_impact"
    if any(w in (L | T) for w in ["employee", "employees", "staff", "cashier", "agent", "associate", "salesperson", "salesman", "saleswoman", "server", "waiter", "rep", "representative"]):
        return "sales_by_employee"
    if any(w in (L | T) for w in ["refund", "refunded", "refunds", "return", "returned", "chargeback", "chargebacks"]):
        return "refund_summary"
    if "category" in (L | T) or "categories" in (L | T) or "department" in (L | T) or "section" in (L | T):
        return "sales_by_category"
    if any(w in (L | T) for w in ["hour", "hourly", "busiest", "peak", "time"]):
        return "hourly_sales"

    # --- Trend / time-based ---
    if any(w in (L | T) for w in ["trend", "trends", "time", "last", "past", "daily", "weekly", "monthly"]) or "over time" in q or "by day" in q or "per day" in q:
        return "sales_trend"

    if any(w in (L | T) for w in ["revenue", "sales", "turnover", "takings", "collection", "collections", "earnings", "income", "total", "amount"]):
        return "total_revenue"

    # --- Fallback ---
    return "general"