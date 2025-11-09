from sales_api import get_recent_orders
from query_parser_old import parse_date_range, validate_date_range
from llm_agent import analyze_sales_data
from datetime import datetime, timedelta
import re
from helpers import format_date, filter_orders_by_date, has_date_hint

from intent_router import detect_intent
from analytics_engine import (
    parse_order_count_from_query,
    compute_total_revenue,
    compute_average_order_value,
    compute_max_order,
    compute_min_order,
    compute_order_count,
    compute_top_items,
    compute_top_items_by_units,
    compute_most_frequent_items,
    compute_average_items_per_order,
    compute_discount_impact,
    compute_max_discount,
    compute_sales_by_employee,
    compute_refund_summary,
    compute_sales_by_category,
    compute_sales_trend,
    compute_hourly_sales,
)


def _has_date_hint(text: str) -> bool:
    # Backward compatibility: call the shared helper
    return has_date_hint(text)


def main():
    print("\U0001F9E0 Sales Insight Agent (Gemini Edition)")
    print("Type 'quit' to exit.\n")

    while True:
        query = input("Ask your sales question: ").strip()
        if query.lower() in ["quit", "exit"]:
            break

        # Step 1: Parse date and number of orders (e.g., "top 3")
        start, end = parse_date_range(query)

        # If no explicit date hint, silently default to last 2 days; otherwise ask to clarify
        if start is None or end is None:
            if not _has_date_hint(query):
                start = datetime.now().date() - timedelta(days=2)
                end = datetime.now().date()
            else:
                print("⚠️ Sorry, I could not understand the date in your query. Please specify a valid date.")
                continue
            
        n = parse_order_count_from_query(query)

        # Step 2: Fetch recent sales data
        result = get_recent_orders()
        orders = result.get("orders", [])
        if not orders:
            print("⚠️ No data available from the sales API at the moment. Please check your connection or try again later.")
            continue
        available_start = datetime.now().date() - timedelta(days=2)  # Example: Last 2 days
        available_end = datetime.now().date()

        # Filter orders by the parsed date range
        filtered_orders = filter_orders_by_date(orders, start, end)

        if not validate_date_range(start, end, available_start, available_end):
            print("\U0001F6A8 The requested date range is outside the available data range.")
            print(f"Available data range: {available_start} to {available_end}")
            continue

        if not filtered_orders:
            print(f"⚠️ No orders found for {format_date(start)}. Please try another date within the available data range.")
            continue

        # Step 3: Detect intent
        intent = detect_intent(query)
        print(f"\U0001F50E Detected intent: {intent}")

        # Step 4: Compute based on intent
        facts = {}
        if intent == "total_revenue":
            facts["total_revenue"] = compute_total_revenue(filtered_orders)
        elif intent == "average_order_value":
            facts["average_order_value"] = compute_average_order_value(filtered_orders)
        elif intent == "max_order":
            facts["max_order"] = compute_max_order(filtered_orders, n)
        elif intent == "min_order":
            facts["min_order"] = compute_min_order(filtered_orders, n)
        elif intent == "order_count":
            facts["order_count"] = compute_order_count(filtered_orders)
        elif intent == "top_items":
            # Provide both revenue and units when possible
            facts["top_items_revenue"] = compute_top_items(filtered_orders, n)
            facts["top_items_units"] = compute_top_items_by_units(filtered_orders, n)
        elif intent == "most_frequent_items":
            facts["most_frequent_items"] = compute_top_items_by_units(filtered_orders, n)
        elif intent == "average_items_per_order":
            facts["average_items_per_order"] = compute_average_items_per_order(filtered_orders)
        elif intent == "discount_impact":
            facts["discount_impact"] = compute_discount_impact(filtered_orders)
        elif intent == "max_discount":
            facts["max_discount"] = compute_max_discount(filtered_orders)
        elif intent == "sales_by_employee":
            facts["sales_by_employee"] = compute_sales_by_employee(filtered_orders)
        elif intent == "refund_summary":
            facts["refund_summary"] = compute_refund_summary(filtered_orders)
        elif intent == "sales_by_category":
            facts["sales_by_category"] = compute_sales_by_category(filtered_orders, category_map={})
        elif intent == "sales_trend":
            facts["sales_trend"] = compute_sales_trend(filtered_orders)
        elif intent == "hourly_sales":
            facts["hourly_sales"] = compute_hourly_sales(filtered_orders)
        else:
            facts["summary"] = "Raw order data loaded, no structured metrics."

        # Step 5: Pass computed results to LLM for explanation
        answer = analyze_sales_data(query, intent, facts, start, end)
        print("\n\U0001F4FE Insight:")
        print(answer)
        print("-" * 80)


if __name__ == "__main__":
    main()
