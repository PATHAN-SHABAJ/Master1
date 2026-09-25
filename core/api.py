import hashlib
import os
import requests

from core.config import WEBSITE_API


# ============================================================
# SUPABASE CONFIGURATION
# ============================================================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

SUPABASE_TABLE = "flipkart_products"


# ============================================================
# CREATE PRODUCT ID
# ============================================================

def generate_product_id(product):
    """
    Create a stable product ID if Flipkart product_id
    is not already available.
    """

    product_id = product.get("product_id")

    if product_id:
        return str(product_id)

    url = (
        product.get("product_url")
        or product.get("url")
        or product.get("product_name")
        or ""
    )

    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:32]


def clean_numeric(value):
    """
    Convert empty strings to None so PostgreSQL
    numeric columns do not receive "".
    """

    if value is None:
        return None

    if isinstance(value, str):
        value = value.strip()

        if value == "":
            return None

        # Remove common currency symbols/commas
        value = value.replace("₹", "").replace(",", "").strip()

    try:
        return float(value)
    except (ValueError, TypeError):
        return None


# ============================================================
# CONVERT PRODUCT DATA FOR SUPABASE
# ============================================================

def prepare_supabase_product(product):
    """
    Convert the existing Flipkart product structure
    into the flipkart_products table structure.
    """

    product_id = generate_product_id(product)

    selling_price = product.get("selling_price")

    if selling_price is None:
        selling_price = product.get("price")

    attributes = {
        "ram": product.get("ram"),
        "storage": product.get("storage"),
        "rating": product.get("rating"),
        "rating_count": product.get("rating_count"),
    }

    # Remove empty values from attributes
    attributes = {
        key: value
        for key, value in attributes.items()
        if value is not None
    }

    data = {
        "product_id": product_id,

        "product_name": product.get("product_name"),
        "product_url": (
            product.get("product_url")
            or product.get("url")
        ),

        # Images
        "image": product.get("image"),
        "image_urls": product.get("image_urls", []),

        # Category
        "category": product.get("category"),
        "category_path": product.get("category_path", []),

        # Brand
        "brand": product.get("brand"),

        # Price
        "mrp": clean_numeric(product.get("mrp")),
        "selling_price": clean_numeric(selling_price),
        "special_price": clean_numeric(product.get("special_price")),
        "discount": product.get("discount"),
        "discount_percentage": clean_numeric(
            product.get("discount_percentage")
        ),

        # Product details
        "description": product.get("description"),
        "color": product.get("color"),
        "size": product.get("size"),
        "storage": product.get("storage"),
        "display_size": product.get("display_size"),
        "size_unit": product.get("size_unit"),
        "style_code": product.get("style_code"),
        "product_family": product.get("product_family"),

        # Variants
        "size_variants": product.get("size_variants", []),
        "color_variants": product.get("color_variants", []),

        # Availability
        "in_stock": product.get("in_stock"),
        "is_available": product.get("is_available"),
        "cod_available": product.get("cod_available"),
        "emi_available": product.get("emi_available"),

        # Seller
        "seller_name": product.get("seller"),
        "seller_average_rating": clean_numeric(
            product.get("seller_average_rating")
        ),
        "seller_no_of_ratings": clean_numeric(
            product.get("seller_no_of_ratings")
        ),
        "seller_no_of_reviews": clean_numeric(
            product.get("seller_no_of_reviews")
        ),

        # Shipping
        "shipping_charges": clean_numeric(
            product.get("shipping_charges")
        ),

        # Offers
        "offers": product.get("offers", []),
        "cashback": product.get("cashback"),

        # Specifications
        "key_specs": product.get("key_specs", []),
        "detailed_specs": product.get("detailed_specs", []),
        "specification_list": product.get("specification_list", []),

        # Other data
        "lifestyle_info": product.get("lifestyle_info", {}),
        "books_info": product.get("books_info", {}),

        # Category-specific data
        "attributes": attributes,

        # Store original product data
        "raw_data": product,
    }

    return data


# ============================================================
# SEND PRODUCT TO SUPABASE
# ============================================================

def send_to_supabase(product):
    """
    Insert or update the product in Supabase.

    If product_id already exists:
        UPDATE existing product

    Otherwise:
        INSERT new product
    """

    if (
        not SUPABASE_URL
        or SUPABASE_URL == "YOUR_SUPABASE_PROJECT_URL"
        or not SUPABASE_KEY
        or SUPABASE_KEY == "YOUR_SUPABASE_SERVICE_ROLE_KEY"
    ):
        print("❌ Supabase configuration is missing")
        return False

    url = (
        f"{SUPABASE_URL.rstrip('/')}"
        f"/rest/v1/{SUPABASE_TABLE}"
        f"?on_conflict=product_id"
    )

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }

    data = prepare_supabase_product(product)

    try:
        response = requests.post(
            url,
            headers=headers,
            json=data,
            timeout=20,
        )

        if response.status_code in (200, 201, 204):
            print("✅ Product saved to Supabase")
            return True

        print("❌ Supabase error:", response.status_code)
        print(response.text)
        return False

    except requests.RequestException as error:
        print("❌ Could not connect to Supabase")
        print(error)
        return False


# ============================================================
# SEND PRODUCT TO WEBSITE
# ============================================================

def send_to_website(product):
    """
    Keep the existing website API functionality.
    """

    url = f"{WEBSITE_API}/api/product"
    
    # Create a copy to clean numeric fields for the website
    cleaned_product = dict(product)
    for field in ["price", "mrp", "rating", "rating_count", "seller_average_rating", "seller_no_of_ratings", "seller_no_of_reviews", "shipping_charges"]:
        if field in cleaned_product:
            cleaned_product[field] = clean_numeric(cleaned_product[field])

    try:
        response = requests.post(
            url,
            json=cleaned_product,
            timeout=15
        )

        if response.status_code == 200:
            print("✅ Product sent to website")
            return True

        print("❌ Website API error:", response.status_code)
        print(response.text)
        return False

    except requests.RequestException as error:
        print("❌ Could not connect to website")
        print(error)
        return False


# ============================================================
# MAIN FUNCTION
# ============================================================

def send_product(product):
    """
    Send every product to BOTH:

    1. Existing Website API
    2. Supabase PostgreSQL
    """

    print("\n" + "=" * 60)
    print("📦 Sending product:", product.get("product_name"))
    print("=" * 60)

    website_success = send_to_website(product)

    supabase_success = send_to_supabase(product)

    print("\n📊 Product sync result:")
    print(
        "   Website :",
        "✅ SUCCESS" if website_success else "❌ FAILED"
    )
    print(
        "   Supabase:",
        "✅ SUCCESS" if supabase_success else "❌ FAILED"
    )

    return website_success and supabase_success