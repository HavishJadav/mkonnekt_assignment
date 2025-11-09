import re
from collections import defaultdict
from datetime import datetime
from typing import Any


# -------------------------------------------------------
# Utility helpers
# -------------------------------------------------------

def _safe_num(value):
    """Ensure numeric fields are safe to sum (None -> 0)."""
    try:
        return float(value or 0)
    except Exception:
        return 0.0


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        if isinstance(value, bool):
            return int(value)
        return int(float(value))
    except Exception:
        return default


def parse_order_count_from_query(query: str, default: int = 1) -> int:
    """
    Extract numeric count (e.g., 'top 3', '3 smallest', 'lowest 5', etc.)
    from a natural-language query. Returns default (1) if no number found.
    Supports both '3 smallest' and 'smallest 3' phrasing.
    """
    q = query.lower().strip()
    pattern = r"(?:top|max(?:imum)?|lowest|min(?:imum)?|smallest)\s+(\d+)|(\d+)\s+(?:top|max(?:imum)?|lowest|min(?:imum)?|smallest)"
    match = re.search(pattern, q)
    if match:
        try:
            return int(match.group(1) or match.group(2))
        except ValueError:
            return default
    return default


def _get_discount_map(order):
    """Map each lineItemId to its cumulative discount amount (safe for None)."""
    discount_map = defaultdict(int)
    for d in order.get("discounts", []):
        line_id = d.get("lineItemId")
        amount = _safe_num(d.get("amount"))
        if line_id:
            discount_map[line_id] += amount
    return discount_map


# -------------------------------------------------------
# Core order-level analytics
# -------------------------------------------------------

def compute_total_revenue(orders):
    """Compute total revenue (USD) across all valid orders."""
    valid_orders = [o for o in orders if _safe_num(o.get("total")) > 0]
    return round(sum(_safe_num(o.get("total")) for o in valid_orders) / 100, 2)


def compute_average_order_value(orders):
    """Compute average order value (USD)."""
    valid_orders = [o for o in orders if _safe_num(o.get("total")) > 0]
    if not valid_orders:
        return 0
    return round(sum(_safe_num(o.get("total")) for o in valid_orders) / len(valid_orders) / 100, 2)


def _compute_orders_sorted(orders, n=1, reverse=True):
    """
    Shared logic for top/bottom N orders (reverse=True for max, False for min).
    Returns a list of up to N orders with breakdowns.
    """
    valid_orders = [o for o in orders if _safe_num(o.get("total")) > 0]
    if not valid_orders:
        return []

    sorted_orders = sorted(valid_orders, key=lambda o: _safe_num(o.get("total")), reverse=reverse)[:n]
    results = []

    for order in sorted_orders:
        discount_map = _get_discount_map(order)
        items = []
        for item in order.get("lineItems", []):
            base = _safe_num(item.get("price"))
            discount = _safe_num(discount_map.get(item.get("lineItemId"), 0))
            effective = base + discount
            items.append({
                "name": item.get("name"),
                "base_price": base / 100,
                "discount": discount / 100,
                "final_price": effective / 100
            })

        item_sum = sum(i["final_price"] for i in items)
        order_total = _safe_num(order.get("total")) / 100
        tax_diff = round(order_total - item_sum, 2)

        results.append({
            "order_id": order.get("orderId"),
            "total_usd": round(order_total, 2),
            "item_sum_usd": round(item_sum, 2),
            "tax_or_fee_usd": tax_diff if abs(tax_diff) > 0.01 else 0.00,
            "items": items
        })

    return results


def compute_max_order(orders, n=1):
    """Return the top N highest-value orders (default N=1)."""
    return _compute_orders_sorted(orders, n=n, reverse=True)


def compute_min_order(orders, n=1):
    """Return the bottom N lowest-value orders (default N=1)."""
    return _compute_orders_sorted(orders, n=n, reverse=False)


def compute_order_count(orders):
    """Count all valid (non-null total) orders."""
    return len([o for o in orders if _safe_num(o.get("total")) > 0])


# -------------------------------------------------------
# Item & category analytics
# -------------------------------------------------------

def compute_top_items(orders, n=5):
    """Aggregate total revenue by item name (discounts included)."""
    item_sales = defaultdict(float)
    for o in orders:
        discount_map = _get_discount_map(o)
        for item in o.get("lineItems", []):
            line_id = item.get("lineItemId")
            base = _safe_num(item.get("price"))
            discount = _safe_num(discount_map.get(line_id, 0))
            effective = base + discount
            item_sales[item.get("name")] += effective

    top_items = sorted(item_sales.items(), key=lambda x: x[1], reverse=True)[:n]
    return [{"name": n, "revenue_usd": round(p / 100, 2)} for n, p in top_items]


def compute_sales_by_category(orders, category_map):
    """Aggregate sales revenue by item category."""
    category_sales = defaultdict(float)
    for o in orders:
        discount_map = _get_discount_map(o)
        for item in o.get("lineItems", []):
            line_id = item.get("lineItemId")
            category = category_map.get(item.get("itemCode"), "Uncategorized")
            base = _safe_num(item.get("price"))
            discount = _safe_num(discount_map.get(line_id, 0))
            category_sales[category] += base + discount

    return [{"category": k, "revenue_usd": round(v / 100, 2)} for k, v in sorted(category_sales.items(), key=lambda x: x[1], reverse=True)]


def compute_most_frequent_items(orders, n=5):
    """Count how often each item is sold (not by revenue)."""
    freq = defaultdict(int)
    for o in orders:
        for item in o.get("lineItems", []):
            freq[item.get("name")] += 1
    top = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:n]
    return [{"name": name, "count": count} for name, count in top]


def compute_average_items_per_order(orders):
    """Compute average number of items per order."""
    valid_orders = [o for o in orders if o.get("lineItems")]
    total_items = sum(len(o["lineItems"]) for o in valid_orders)
    return round(total_items / len(valid_orders), 2) if valid_orders else 0


def _get_item_quantity(item: dict) -> int:
    """Best-effort extraction of quantity from a line item.

    Tries common keys; defaults to 1 when unspecified.
    If a 'refundedQty' (or similar) exists, it will be subtracted.
    """
    qty_keys = ["quantity", "qty", "count", "units", "quantitySold", "qtySold"]
    refunded_keys = ["refundedQty", "qtyRefunded", "refunded_quantity"]

    qty = 1  # default to 1 line item
    for k in qty_keys:
        if k in item:
            qty = max(_safe_int(item.get(k), 1), 0)
            break

    for rk in refunded_keys:
        if rk in item:
            qty -= max(_safe_int(item.get(rk), 0), 0)
            break

    return max(qty, 0)


def compute_top_items_by_units(orders, n=10):
    """Top-N items by total units sold (not revenue)."""
    units = defaultdict(int)
    for o in orders:
        for item in o.get("lineItems", []):
            name = item.get("name")
            if not name:
                continue
            units[name] += _get_item_quantity(item)

    top = sorted(units.items(), key=lambda x: x[1], reverse=True)[:n]
    return [{"name": name, "units": count} for name, count in top]


# -------------------------------------------------------
# Discount, employee, and refund analytics
# -------------------------------------------------------

def compute_discount_impact(orders):
    """Total discounts applied (USD)."""
    total_discount = 0
    for o in orders:
        for d in o.get("discounts", []):
            total_discount += _safe_num(d.get("amount"))
    return round(total_discount / 100, 2)


def compute_max_discount(orders):
    """Find the maximum single discount amount (USD)."""
    max_discount = 0
    max_discount_order = None
    
    for o in orders:
        for d in o.get("discounts", []):
            discount_amount = _safe_num(d.get("amount"))
            if discount_amount > max_discount:
                max_discount = discount_amount
                max_discount_order = {
                    "order_id": o.get("orderId"),
                    "discount_amount_usd": round(discount_amount / 100, 2),
                    "discount_type": d.get("type", "Unknown"),
                    "line_item_id": d.get("lineItemId")
                }
    
    return max_discount_order if max_discount_order else {"message": "No discounts found"}


def compute_sales_by_employee(orders):
    """Aggregate revenue per employee."""
    emp_sales = defaultdict(float)
    for o in orders:
        emp_sales[o.get("employeeId")] += _safe_num(o.get("total"))
    return [{"employeeId": k, "revenue_usd": round(v / 100, 2)} for k, v in sorted(emp_sales.items(), key=lambda x: x[1], reverse=True)]


def compute_refund_summary(orders):
    """Compute total refunded items and amount."""
    refunded_total = 0
    refunded_items = 0
    for o in orders:
        for item in o.get("lineItems", []):
            if _safe_num(item.get("refunded", 0)) > 0:
                refunded_total += _safe_num(item.get("price"))
                refunded_items += 1
    return {
        "refunded_items": refunded_items,
        "refunded_amount_usd": round(refunded_total / 100, 2)
    }


# -------------------------------------------------------
# Trend and time-based analytics
# -------------------------------------------------------

def compute_sales_trend(orders):
    """Compute revenue trend by date."""
    trend = defaultdict(float)
    for o in orders:
        try:
            date = datetime.fromisoformat(o["createdTime"].replace("Z", "+00:00")).date()
            trend[date] += _safe_num(o.get("total"))
        except Exception:
            continue
    return [{"date": str(k), "revenue_usd": round(v / 100, 2)} for k, v in sorted(trend.items())]


def compute_hourly_sales(orders):
    """Compute revenue by hour of the day."""
    hourly = defaultdict(float)
    for o in orders:
        try:
            dt = datetime.fromisoformat(o["createdTime"].replace("Z", "+00:00"))
            hour = dt.strftime("%H:00")
            hourly[hour] += _safe_num(o.get("total"))
        except Exception:
            continue
    return [{"hour": k, "revenue_usd": round(v / 100, 2)} for k, v in sorted(hourly.items())]
