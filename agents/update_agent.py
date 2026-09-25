import asyncio
import requests

from core.config import WEBSITE_API


# ============================================================
# CONFIGURATION
# ============================================================

SYNC_INTERVAL = 60

ALLOWED_CATEGORIES = {
    "mobiles",
    "laptops",
    "earbuds",
    "tvs",
}


# ============================================================
# UPDATE / SYNC AGENT
# ============================================================

print()
print("=" * 70)
print("🔄 FLIPKART UPDATE / SYNC AGENT")
print("=" * 70)

print()
print("🎯 Allowed categories:")
print("   📱 Mobiles")
print("   💻 Laptops")
print("   🎧 Earbuds")
print("   📺 TVs")

print()
print(f"⏱️ Sync interval: {SYNC_INTERVAL} seconds")
print()


# ============================================================
# GET PRODUCTS FROM WEBSITE
# ============================================================

def get_products():

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

        data = response.json()

        if not isinstance(data, list):

            return []

        return data

    except requests.RequestException as error:

        print(
            "❌ Could not connect to website"
        )

        print(error)

        return []


# ============================================================
# CHECK CATEGORY
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
# PRODUCT KEY
# ============================================================

def get_product_key(product):

    return (
        product.get("product_url")
        or product.get("url")
        or ""
    ).strip()


# ============================================================
# NORMALIZE PRODUCT
# ============================================================

def normalize_product(product):

    if not isinstance(product, dict):

        return {}

    normalized = {}

    for key, value in product.items():

        if isinstance(value, list):

            normalized[key] = [
                str(item).strip()
                for item in value
                if str(item).strip()
            ]

        elif value is None:

            normalized[key] = ""

        else:

            normalized[key] = str(
                value
            ).strip()

    return normalized


# ============================================================
# BUILD PRODUCT MAP
# ============================================================

def build_product_map(products):

    product_map = {}

    for product in products:

        if not is_allowed_product(
            product
        ):

            continue

        key = get_product_key(
            product
        )

        if not key:

            continue

        product_map[key] = product

    return product_map


# ============================================================
# FIND DUPLICATES
# ============================================================

def find_duplicates(products):

    seen = set()

    duplicates = []

    for product in products:

        if not is_allowed_product(
            product
        ):

            continue

        key = get_product_key(
            product
        )

        if not key:

            continue

        if key in seen:

            duplicates.append(key)

        else:

            seen.add(key)

    return duplicates


# ============================================================
# REMOVE UNWANTED CATEGORY
# ============================================================

def remove_unwanted_products(products):

    allowed = []

    removed = 0

    for product in products:

        if is_allowed_product(
            product
        ):

            allowed.append(
                product
            )

        else:

            removed += 1

    return allowed, removed


# ============================================================
# SYNC CHECK
# ============================================================

def sync_check():

    print()
    print("=" * 70)
    print("🔄 UPDATE / SYNC CHECK")
    print("=" * 70)

    products = get_products()

    if not products:

        print()
        print(
            "⏳ No products available."
        )

        print(
            "   Waiting for Product Agent..."
        )

        return


    # --------------------------------------------------------
    # Category filtering
    # --------------------------------------------------------

    allowed_products, removed = (
        remove_unwanted_products(
            products
        )
    )

    print()
    print(
        f"📦 Products received: "
        f"{len(products)}"
    )

    print(
        f"✅ Allowed products: "
        f"{len(allowed_products)}"
    )

    print(
        f"⛔ Unwanted products: "
        f"{removed}"
    )


    # --------------------------------------------------------
    # Build product map
    # --------------------------------------------------------

    product_map = build_product_map(
        allowed_products
    )


    # --------------------------------------------------------
    # Category statistics
    # --------------------------------------------------------

    category_counts = {

        "mobiles": 0,

        "laptops": 0,

        "earbuds": 0,

        "tvs": 0,
    }


    for product in allowed_products:

        category = (
            product.get("category")
            or ""
        ).lower().strip()

        if category in category_counts:

            category_counts[
                category
            ] += 1


    print()
    print("📊 CATEGORY SUMMARY")

    print(
        f"   📱 Mobiles: "
        f"{category_counts['mobiles']}"
    )

    print(
        f"   💻 Laptops: "
        f"{category_counts['laptops']}"
    )

    print(
        f"   🎧 Earbuds: "
        f"{category_counts['earbuds']}"
    )

    print(
        f"   📺 TVs: "
        f"{category_counts['tvs']}"
    )


    # --------------------------------------------------------
    # Duplicate check
    # --------------------------------------------------------

    duplicates = find_duplicates(
        products
    )

    print()

    if duplicates:

        print(
            f"⚠️ Duplicate products: "
            f"{len(duplicates)}"
        )

    else:

        print(
            "✅ No duplicate product URLs"
        )


    # --------------------------------------------------------
    # Sync status
    # --------------------------------------------------------

    print()
    print(
        "🔗 WEBSITE SYNC STATUS"
    )

    print(
        f"   Live products: "
        f"{len(product_map)}"
    )

    print(
        "   Website API: "
        f"{WEBSITE_API}"
    )

    print()
    print(
        "✅ Update / Sync check complete"
    )

    print("=" * 70)


# ============================================================
# CONTINUOUS LOOP
# ============================================================

async def run_update_agent():

    print()
    print(
        "🤖 Update / Sync Agent running..."
    )

    while True:

        try:

            sync_check()

        except Exception as error:

            print()
            print(
                "❌ Update / Sync error:"
            )

            print(error)


        print()

        print(
            f"⏳ Next sync check in "
            f"{SYNC_INTERVAL} seconds..."
        )

        await asyncio.sleep(
            SYNC_INTERVAL
        )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    try:

        asyncio.run(
            run_update_agent()
        )

    except KeyboardInterrupt:

        print()
        print(
            "🛑 Update / Sync Agent stopped."
        )