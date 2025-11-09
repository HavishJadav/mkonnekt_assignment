import requests

DEFAULT_TIMEOUT = 10

import os
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    # If python-dotenv isn't installed, environment variables can still be provided by the OS
    pass

DEFAULT_TIMEOUT = int(os.getenv("MKONNEKT_TIMEOUT", "10"))


def get_recent_orders():
    url = os.getenv("MKONNEKT_ORDERS_RECENT_URL")
    if not url:
        print("⚠️ Error: Missing MKONNEKT_ORDERS_RECENT_URL. Please set it in your environment or .env file.")
        return {"orders": [], "meta": {}}
    try:
        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        try:
            data = response.json()
        except ValueError:
            print("⚠️ Error: API response was not valid JSON.")
            return {"orders": [], "meta": {}}

        # Handle the correct API format
        total_orders = data.get("totalOrders", 0)
        max_limit = data.get("maxLimit", 500)
        date_range = data.get("dateRange", "Unknown")
        orders = data.get("orders", [])

        if total_orders >= max_limit:
            print(f"⚠️ Warning: API returned the max {max_limit} orders. Data may be truncated.")
        print(f"📅 Date range of data: {date_range}")

        return {
            "orders": orders,
            "meta": {
                "totalOrders": total_orders,
                "maxLimit": max_limit,
                "dateRange": date_range
            }
        }

    except requests.Timeout:
        print("⚠️ Error: The request to the sales API timed out. Please try again later.")
        return {"orders": [], "meta": {}}
    except requests.RequestException as e:
        print(f"⚠️ Network error fetching orders: {e}")
        return {"orders": [], "meta": {}}
    except Exception as e:
        print(f"⚠️ Unexpected error fetching orders: {e}")
        return {"orders": [], "meta": {}}
