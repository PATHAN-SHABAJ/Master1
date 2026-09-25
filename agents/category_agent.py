# ============================================================
# CATEGORY AGENT
# ============================================================

import re


# ============================================================
# ALLOWED CATEGORIES
# ============================================================

ALLOWED_CATEGORIES = {
    "mobiles",
    "laptops",
    "earbuds",
    "tvs",
}


# ============================================================
# SEARCH QUERIES
# ============================================================

MOBILE_QUERIES = [
    "mobile",
    "smartphone",
    "iphone",
    "iphone 15",
    "iphone 16",
    "iphone 17",
    "samsung galaxy",
    "oneplus",
    "google pixel",
    "xiaomi",
    "redmi",
    "realme",
    "vivo",
    "oppo",
    "motorola",
    "nothing phone",
    "iqoo",
    "poco",
]


LAPTOP_QUERIES = [
    "laptop",
    "gaming laptop",
    "hp laptop",
    "dell laptop",
    "lenovo laptop",
    "asus laptop",
    "acer laptop",
    "macbook",
]


EARBUD_QUERIES = [
    "earbuds",
    "bluetooth earbuds",
    "wireless earbuds",
    "true wireless earbuds",
    "tws earbuds",
    "airpods",
    "oneplus earbuds",
    "realme earbuds",
    "boat earbuds",
    "samsung earbuds",
    "noise earbuds",
]


TV_QUERIES = [
    "tv",
    "smart tv",
    "led tv",
    "4k tv",
    "5k tv",
    "android tv",
    "google tv",
    "sony tv",
    "samsung tv",
    "lg tv",
    "oneplus tv",
    "xiaomi tv",
    "mi tv",
    "tcl tv",
    "hisense tv",
]


CATEGORY_QUERIES = {

    "mobiles": MOBILE_QUERIES,

    "laptops": LAPTOP_QUERIES,

    "earbuds": EARBUD_QUERIES,

    "tvs": TV_QUERIES,

}


# ============================================================
# CATEGORY KEYWORDS
# ============================================================

CATEGORY_KEYWORDS = {

    "mobiles": [
        "mobile",
        "smartphone",
        "iphone",
        "galaxy",
        "oneplus",
        "pixel",
        "redmi",
        "xiaomi",
        "realme",
        "vivo",
        "oppo",
        "motorola",
        "nothing phone",
        "iqoo",
        "poco",
    ],

    "laptops": [
        "laptop",
        "notebook",
        "macbook",
        "chromebook",
        "vivobook",
        "ideapad",
        "thinkpad",
        "pavilion",
        "inspiron",
        "latitude",
        "aspire",
        "gaming laptop",
    ],

    "earbuds": [
        "earbuds",
        "earbud",
        "tws",
        "airpods",
        "true wireless",
        "wireless earbuds",
    ],

    "tvs": [
        "tv",
        "television",
        "smart tv",
        "led tv",
        "4k tv",
        "android tv",
        "google tv",
        "sony tv",
        "samsung tv",
        "lg tv",
        "oneplus tv",
        "xiaomi tv",
        "mi tv",
        "tcl tv",
        "hisense tv",
    ],
}


# ============================================================
# CATEGORY DETECTION
# ============================================================

def detect_category(
    product_name="",
    url=""
):

    text = (
        f"{product_name} {url}"
        .lower()
    )

    text = re.sub(
        r"[^a-z0-9\s-]",
        " ",
        text
    )

    # Reject accessories
    blocked = ["screen guard", "screen protector", "tempered glass", "case", "cover", "charger", "cable", "adapter"]
    for keyword in blocked:
        if keyword in text:
            return ""

    # --------------------------------------------------------
    # TV (Check TV first before Mobile to prevent 'Smart TV' matching 'Smart')
    # --------------------------------------------------------

    for keyword in CATEGORY_KEYWORDS["tvs"]:

        if keyword in text:

            return "tvs"

    # --------------------------------------------------------
    # Earbuds first
    # --------------------------------------------------------

    for keyword in CATEGORY_KEYWORDS["earbuds"]:

        if keyword in text:

            return "earbuds"

    # --------------------------------------------------------
    # Laptop
    # --------------------------------------------------------

    for keyword in CATEGORY_KEYWORDS["laptops"]:

        if keyword in text:

            return "laptops"

    # --------------------------------------------------------
    # Mobile
    # --------------------------------------------------------

    for keyword in CATEGORY_KEYWORDS["mobiles"]:

        if keyword in text:

            return "mobiles"

    return ""


# ============================================================
# CHECK ALLOWED CATEGORY
# ============================================================

def is_allowed_category(
    category
):

    if not category:
        return False

    return (
        category.lower().strip()
        in ALLOWED_CATEGORIES
    )


# ============================================================
# CHECK PRODUCT
# ============================================================

def is_allowed_product(
    product_name="",
    url="",
    category=""
):

    detected = detect_category(
        product_name,
        url
    )

    # --------------------------------------------------------
    # If category is explicitly supplied,
    # it must be one of our allowed categories.
    # --------------------------------------------------------

    if category:

        category = (
            category
            .lower()
            .strip()
        )

        if not is_allowed_category(
            category
        ):

            return False

        return True

    # --------------------------------------------------------
    # Otherwise detect automatically
    # --------------------------------------------------------

    return is_allowed_category(
        detected
    )


# ============================================================
# GET CATEGORY
# ============================================================

def get_category(
    product_name="",
    url=""
):

    return detect_category(
        product_name,
        url
    )


# ============================================================
# GET SEARCH QUERIES
# ============================================================

def get_all_queries():

    queries = []

    for category in [
        "mobiles",
        "laptops",
        "earbuds",
        "tvs",
    ]:

        queries.extend(
            CATEGORY_QUERIES[category]
        )

    return queries


# ============================================================
# GET QUERIES BY CATEGORY
# ============================================================

def get_queries(
    category
):

    category = (
        category
        .lower()
        .strip()
    )

    return CATEGORY_QUERIES.get(
        category,
        []
    )


# ============================================================
# DISPLAY CATEGORY SUMMARY
# ============================================================

def print_category_summary():

    print()
    print("=" * 70)
    print("🗂️ CATEGORY AGENT")
    print("=" * 70)

    print()
    print("✅ Allowed categories:")

    print("   📱 Mobiles")
    print("   💻 Laptops")
    print("   🎧 Earbuds")
    print("   📺 TVs")

    print()

    for category in [
        "mobiles",
        "laptops",
        "earbuds",
        "tvs",
    ]:

        print(
            f"   {category.title()}: "
            f"{len(CATEGORY_QUERIES[category])} searches"
        )

    print()
    print(
        f"🔎 Total searches: "
        f"{len(get_all_queries())}"
    )

    print("=" * 70)


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print_category_summary()

    tests = [

        (
            "Apple iPhone 17",
            "https://www.flipkart.com/apple-iphone-17/p/abc"
        ),

        (
            "ASUS Vivobook Laptop",
            "https://www.flipkart.com/asus-vivobook/p/abc"
        ),

        (
            "OnePlus Wireless Earbuds",
            "https://www.flipkart.com/oneplus-earbuds/p/abc"
        ),

        (
            "Samsung Smart TV",
            "https://www.flipkart.com/samsung-smart-tv/p/abc"
        ),

        (
            "Washing Machine",
            "https://www.flipkart.com/washing-machine/p/abc"
        ),

    ]

    print()

    print(
        "🧪 CATEGORY TESTS"
    )

    print()

    for name, url in tests:

        category = get_category(
            name,
            url
        )

        allowed = is_allowed_product(
            name,
            url
        )

        print(
            f"Product: {name}"
        )

        print(
            f"Category: "
            f"{category or 'UNKNOWN'}"
        )

        print(
            f"Allowed: "
            f"{'YES' if allowed else 'NO'}"
        )

        print("-" * 50)