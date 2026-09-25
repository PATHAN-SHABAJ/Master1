import sys
import os

# Ensure flipcart root is in sys.path so 'core' and 'agents' are importable
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import asyncio
from copy import deepcopy

import requests

from playwright.async_api import async_playwright

from core.config import WEBSITE_API, CHECK_INTERVAL
from core.api import send_product

from agents.product_agent import read_product


# ============================================================
# CONFIGURATION
# ============================================================

CHANGE_CHECK_INTERVAL = CHECK_INTERVAL

ALLOWED_CATEGORIES = {
    "mobiles",
    "laptops",
    "earbuds",
    "tvs",
}


# ============================================================
# CHANGE AGENT
# ============================================================

print()
print("=" * 70)
print("🔄 FLIPKART CHANGE AGENT")
print("=" * 70)

print()
print("🎯 Monitoring:")
print("   📱 Mobiles")
print("   💻 Laptops")
print("   🎧 Earbuds")
print("   📺 TVs")

print()
print(
    f"⏱️ Check interval: "
    f"{CHANGE_CHECK_INTERVAL // 60} minutes"
)

print()


# ============================================================
# GET CURRENT PRODUCTS FROM WEBSITE
# ============================================================

def get_website_products():

    try:

        response = requests.get(
            f"{WEBSITE_API}/api/products",
            timeout=15
        )

        if response.status_code != 200:

            print(
                "❌ Website API error:",
                response.status_code
            )

            return []

        products = response.json()

        if not isinstance(products, list):
            return []

        return products

    except requests.RequestException as error:

        print()
        print("⚠️ Website is not available")
        print(error)

        return []


# ============================================================
# VALIDATE PRODUCT
# ============================================================

def is_allowed_product(product):

    if not isinstance(product, dict):
        return False

    category = (
        product.get("category")
        or ""
    ).lower().strip()

    return category in ALLOWED_CATEGORIES


# ============================================================
# NORMALIZE VALUE FOR COMPARISON
# ============================================================

def normalize_value(value):

    if value is None:
        return ""

    if isinstance(value, list):

        cleaned = []

        for item in value:

            if item is None:
                continue

            text = str(item).strip()

            if text:
                cleaned.append(
                    " ".join(text.lower().split())
                )

        return sorted(set(cleaned))

    if isinstance(value, dict):

        return {
            str(key): normalize_value(val)
            for key, val in value.items()
        }

    return " ".join(
        str(value)
        .lower()
        .split()
    )


# ============================================================
# FIELDS WE MONITOR
# ============================================================

MONITORED_FIELDS = [

    "product_name",

    "price",

    "discount",

    "rating",

    "rating_count",

    "brand",

    "color",

    "ram",

    "storage",

    "seller",

    "image",

    "highlights",

    "offers",
]


# ============================================================
# FIND CHANGES
# ============================================================

def find_changes(
    old_product,
    new_product
):

    changes = []

    for field in MONITORED_FIELDS:

        old_value = normalize_value(
            old_product.get(field)
        )

        new_value = normalize_value(
            new_product.get(field)
        )

        # ----------------------------------------------------
        # If new scraper didn't find a value,
        # don't treat that as a real change.
        # ----------------------------------------------------

        if (
            new_value == ""
            and old_value != ""
        ):
            continue

        if old_value != new_value:

            changes.append({
                "field": field,
                "old": old_product.get(field),
                "new": new_product.get(field),
            })

    return changes


# ============================================================
# PRINT CHANGES
# ============================================================

def print_changes(changes):

    print()

    print(
        "🔍 CHANGES DETECTED:"
    )

    for change in changes:

        field = change["field"]

        old_value = change["old"]

        new_value = change["new"]

        print()
        print(
            f"   🔄 {field}"
        )

        print(
            f"      OLD: {old_value}"
        )

        print(
            f"      NEW: {new_value}"
        )


# ============================================================
# CHECK ONE PRODUCT
# ============================================================

async def check_product(
    page,
    old_product
):

    product_url = (
        old_product.get("product_url")
        or old_product.get("url")
    )

    if not product_url:

        print(
            "⚠️ Product has no URL"
        )

        return False

    print()
    print("-" * 70)

    print(
        "🔎 Checking:"
    )

    print(
        product_url
    )

    # --------------------------------------------------------
    # Read current Flipkart data
    # --------------------------------------------------------

    try:

        new_product = await read_product(
            page,
            product_url
        )

    except Exception as error:

        print()
        print(
            "⚠️ Could not read product"
        )

        print(error)

        return False

    if not new_product:

        print(
            "⚠️ Product could not be read"
        )

        return False

    # --------------------------------------------------------
    # Safety check
    # --------------------------------------------------------

    if not is_allowed_product(
        new_product
    ):

        print(
            "⛔ Product rejected:"
            " outside allowed categories"
        )

        return False

    # --------------------------------------------------------
    # Compare
    # --------------------------------------------------------

    changes = find_changes(
        old_product,
        new_product
    )

    # --------------------------------------------------------
    # No changes
    # --------------------------------------------------------

    if not changes:

        print()
        print(
            "✓ No changes detected"
        )

        return False

    # --------------------------------------------------------
    # Changes found
    # --------------------------------------------------------

    print()
    print(
        "🔄 PRODUCT UPDATED"
    )

    print_changes(
        changes
    )

    # --------------------------------------------------------
    # Update website
    # --------------------------------------------------------

    print()
    print(
        "📤 Updating clone website..."
    )

    success = send_product(
        new_product
    )

    if success:

        print(
            "✅ Clone website updated"
        )

        return True

    print(
        "❌ Failed to update clone website"
    )

    return False


# ============================================================
# CHANGE AGENT LOOP
# ============================================================

async def run_change_agent():

    # --------------------------------------------------------
    # Start Playwright
    # --------------------------------------------------------

    async with async_playwright() as playwright:

        browser = await playwright.chromium.launch(
            headless=True
        )

        context = await browser.new_context(
            viewport={
                "width": 1366,
                "height": 900
            },
            locale="en-IN",
            timezone_id="Asia/Kolkata"
        )

        page = await context.new_page()

        page.set_default_timeout(
            10000
        )

        print()
        print(
            "🤖 Change Agent running..."
        )

        print(
            "🖥️ Browser: HEADLESS"
        )

        try:

            while True:

                print()
                print(
                    "=" * 70
                )

                print(
                    "🔄 CHANGE CHECK"
                )

                print(
                    "=" * 70
                )

                # ------------------------------------------------
                # Get products currently shown on clone
                # ------------------------------------------------

                products = (
                    get_website_products()
                )

                allowed_products = [

                    product

                    for product in products

                    if is_allowed_product(
                        product
                    )
                ]

                print()
                print(
                    f"📦 Products on clone: "
                    f"{len(products)}"
                )

                print(
                    f"✅ Products monitored: "
                    f"{len(allowed_products)}"
                )

                if not allowed_products:

                    print()
                    print(
                        "⏳ No products available yet."
                    )

                    print(
                        "   Waiting for Discovery Agent..."
                    )

                # ------------------------------------------------
                # Check every product
                # ------------------------------------------------

                changed_count = 0

                for number, product in enumerate(
                    allowed_products,
                    start=1
                ):

                    print()
                    print(
                        f"📦 Product "
                        f"{number}/"
                        f"{len(allowed_products)}"
                    )

                    changed = await check_product(
                        page,
                        product
                    )

                    if changed:

                        changed_count += 1

                    # Small delay between products
                    await asyncio.sleep(2)

                # ------------------------------------------------
                # Summary
                # ------------------------------------------------

                print()
                print(
                    "=" * 70
                )

                print(
                    "📊 CHANGE CHECK COMPLETE"
                )

                print(
                    f"   Checked: "
                    f"{len(allowed_products)}"
                )

                print(
                    f"   Updated: "
                    f"{changed_count}"
                )

                print(
                    "=" * 70
                )

                # ------------------------------------------------
                # Wait
                # ------------------------------------------------

                print()

                print(
                    f"⏳ Next change check in "
                    f"{CHANGE_CHECK_INTERVAL // 60} minutes..."
                )

                await asyncio.sleep(
                    CHANGE_CHECK_INTERVAL
                )

        finally:

            await context.close()

            await browser.close()


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    try:

        asyncio.run(
            run_change_agent()
        )

    except KeyboardInterrupt:

        print()
        print(
            "🛑 Change Agent stopped."
        )