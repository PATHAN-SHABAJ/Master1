import sys
import os

# Ensure flipcart root is in sys.path so 'core' and 'agents' are importable
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import asyncio
import json
import re
from datetime import datetime
from urllib.parse import urlparse, parse_qs

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

from core.config import FLIPKART_BASE_URL
from core.api import send_product


# ============================================================
# CATEGORY DETECTION
# ============================================================

ALLOWED_CATEGORIES = {
    "mobiles",
    "laptops",
    "earbuds",
    "tvs",
}


def detect_product_category(
    product_name,
    product_url
):

    text = (
        (product_name or "")
        + " "
        + (product_url or "")
    ).lower()

    blocked_words = [
        "shampoo", "beauty", "cream", "lotion", "wash", "face", "hair",
        "serum", "cleanser", "garnier", "nivea", "loreal", "soap",
        "shirt", "dress", "saree", "kurta", "jeans", "shoes", "clothing",
        "refrigerator", "fridge", "washing machine", "air conditioner",
        "camera"
    ]

    if any(b in text for b in blocked_words):
        return None

    # --------------------------------------------------------
    # MOBILES
    # --------------------------------------------------------

    mobile_words = [
        "iphone",
        "samsung galaxy",
        "oneplus",
        "google pixel",
        "redmi",
        "xiaomi",
        "realme",
        "vivo",
        "oppo",
        "motorola",
        "nothing phone",
        "iqoo",
        "poco",
        "smartphone",
        "mobile phone",
    ]

    if any(
        word in text
        for word in mobile_words
    ):
        return "mobiles"

    # --------------------------------------------------------
    # LAPTOPS
    # --------------------------------------------------------

    laptop_words = [
        "laptop",
        "macbook",
        "notebook computer",
    ]

    if any(
        word in text
        for word in laptop_words
    ):
        return "laptops"

    # --------------------------------------------------------
    # TVs
    # --------------------------------------------------------

    tv_words = [
        "tv",
        "television",
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

    if any(
        word in text
        for word in tv_words
    ):
        return "tvs"

    # --------------------------------------------------------
    # EARBUDS
    # --------------------------------------------------------

    earbuds_words = [
        "earbuds",
        "earbud",
        "airpods",
        "tws",
        "true wireless",
    ]

    if any(
        word in text
        for word in earbuds_words
    ):
        return "earbuds"

    return None


# ============================================================
# CONFIGURATION
# ============================================================

PRODUCT_DELAY = 2

PAGE_TIMEOUT = 50000

PAGE_WAIT = 4000

MAX_HIGHLIGHTS = 15

MAX_OFFERS = 15

MAX_IMAGES = 10


# ============================================================
# HELPERS
# ============================================================

def clean_text(value):

    if value is None:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(value)
    ).strip()


def clean_number(value):

    if value is None:
        return None

    value = clean_text(value)

    if not value:
        return None

    value = value.replace("₹", "")
    value = value.replace(",", "")
    value = value.replace("%", "")

    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def clean_url(url):

    if not url:
        return ""

    url = url.strip()

    if not url.startswith("http"):
        return ""

    parsed = urlparse(url)

    if "flipkart.com" not in parsed.netloc.lower():
        return ""

    # Keep Flipkart pid because it is the
    # actual product identifier.
    query = parse_qs(parsed.query)

    pid = query.get("pid", [""])[0].strip()

    clean_path = (
        f"{parsed.scheme}://"
        f"{parsed.netloc}"
        f"{parsed.path}"
    ).rstrip("/")

    if pid:
        return f"{clean_path}?pid={pid}"

    return clean_path


def find_product_id(product_url, body_text, json_ld):

    # --------------------------------------------------------
    # METHOD 1 — URL pid
    # --------------------------------------------------------

    try:

        parsed = urlparse(product_url)

        query = parse_qs(parsed.query)

        pid = query.get("pid", [""])[0].strip()

        if pid:
            return pid

    except Exception:
        pass


    # --------------------------------------------------------
    # METHOD 2 — JSON / page text
    # --------------------------------------------------------

    patterns = [
        r'"pid"\s*:\s*"([A-Z0-9]+)"',
        r'"productId"\s*:\s*"([A-Z0-9]+)"',
        r'"product_id"\s*:\s*"([A-Z0-9]+)"',
        r'[?&]pid=([A-Z0-9]+)',
    ]

    combined_text = (
        body_text
        + " "
        + json.dumps(json_ld, ensure_ascii=False)
    )

    for pattern in patterns:

        match = re.search(
            pattern,
            combined_text,
            re.IGNORECASE
        )

        if match:

            value = clean_text(
                match.group(1)
            )

            if value:
                return value


    # --------------------------------------------------------
    # METHOD 3 — Flipkart item ID from /p/
    # --------------------------------------------------------

    match = re.search(
        r"/p/([a-zA-Z0-9]+)",
        product_url
    )

    if match:

        return match.group(1)


    return ""


# ============================================================
# JSON-LD
# ============================================================

async def get_json_ld(page):

    results = []

    try:

        scripts = page.locator(
            'script[type="application/ld+json"]'
        )

        count = await scripts.count()

        for i in range(count):

            try:

                text = await scripts.nth(
                    i
                ).inner_text()

                data = json.loads(text)

                if isinstance(data, list):

                    results.extend(data)

                else:

                    results.append(data)

            except Exception:

                continue

    except Exception:

        pass

    return results


# ============================================================
# PRODUCT NAME
# ============================================================

def find_product_name(
    body_text,
    json_ld
):

    for item in json_ld:

        if not isinstance(
            item,
            dict
        ):
            continue

        name = item.get("name")

        if name:

            name = clean_text(name)

            if len(name) > 3:

                return name

    return ""


# ============================================================
# PRICE
# ============================================================

def find_price(
    body_text,
    json_ld
):

    for item in json_ld:

        if not isinstance(
            item,
            dict
        ):
            continue

        offers = item.get(
            "offers"
        )

        if isinstance(
            offers,
            dict
        ):

            price = offers.get(
                "price"
            )

            if price:

                return (
                    "₹" +
                    str(price)
                )

        elif isinstance(
            offers,
            list
        ):

            for offer in offers:

                if not isinstance(
                    offer,
                    dict
                ):
                    continue

                price = offer.get(
                    "price"
                )

                if price:

                    return (
                        "₹" +
                        str(price)
                    )

    matches = re.findall(
        r"₹\s*[\d,]+",
        body_text
    )

    if matches:

        return matches[0]

    return ""


# ============================================================
# RATING
# ============================================================

def find_rating(
    body_text,
    json_ld
):

    for item in json_ld:

        if not isinstance(
            item,
            dict
        ):
            continue

        rating = item.get(
            "aggregateRating"
        )

        if isinstance(
            rating,
            dict
        ):

            value = rating.get(
                "ratingValue"
            )

            if value:

                return str(value)

    match = re.search(
        r"\b([1-5](?:\.\d)?)\b",
        body_text
    )

    if match:

        value = match.group(1)

        try:

            number = float(value)

            if 1 <= number <= 5:

                return value

        except ValueError:

            pass

    return ""


# ============================================================
# RATING COUNT
# ============================================================

def find_rating_count(
    body_text,
    json_ld
):

    for item in json_ld:

        if not isinstance(
            item,
            dict
        ):
            continue

        rating = item.get(
            "aggregateRating"
        )

        if isinstance(
            rating,
            dict
        ):

            count = (
                rating.get(
                    "ratingCount"
                )
                or
                rating.get(
                    "reviewCount"
                )
            )

            if count:

                return str(count)

    match = re.search(
        r"([\d,]+)\s*(?:Ratings?|Reviews?)",
        body_text,
        re.IGNORECASE
    )

    if match:

        return match.group(1)

    return ""


# ============================================================
# IMAGE
# ============================================================

async def find_main_image(
    page,
    json_ld
):

    # ========================================================
    # METHOD 1 — JSON-LD
    # ========================================================

    for item in json_ld:

        if not isinstance(item, dict):
            continue

        image = item.get("image")

        if isinstance(image, str):
            if image.startswith("http"):
                return image

        if isinstance(image, list):

            for img in image:

                if isinstance(img, str) and img.startswith("http"):
                    return img

    # ========================================================
    # METHOD 2 — OG IMAGE
    # ========================================================

    try:

        og = page.locator(
            'meta[property="og:image"]'
        )

        if await og.count():

            image = await og.first.get_attribute(
                "content"
            )

            if image:
                return image

    except Exception:
        pass

    # ========================================================
    # METHOD 3 — PRODUCT IMAGES
    # ========================================================

    try:

        images = page.locator("img")

        count = await images.count()

        for i in range(min(count, 100)):

            img = images.nth(i)

            src = await img.get_attribute("src")

            if not src:
                continue

            if not src.startswith("http"):
                continue

            alt = (
                await img.get_attribute("alt")
                or ""
            )

            text = (
                src + " " + alt
            ).lower()

            if any(
                x in text
                for x in [
                    "logo",
                    "icon",
                    "banner",
                    "sprite"
                ]
            ):
                continue

            return src

    except Exception:
        pass

    return ""


async def find_image_urls(page, json_ld):

    images = []

    # JSON-LD images
    for item in json_ld:

        if not isinstance(item, dict):
            continue

        image = item.get("image")

        if isinstance(image, str):

            if image.startswith("http"):
                images.append(image)

        elif isinstance(image, list):

            for img in image:

                if isinstance(img, str) and img.startswith("http"):
                    images.append(img)

    # OG image
    try:

        og = page.locator(
            'meta[property="og:image"]'
        )

        if await og.count():

            image = await og.first.get_attribute(
                "content"
            )

            if image:
                images.append(image)

    except Exception:
        pass

    # Page images
    try:

        elements = page.locator("img")

        count = await elements.count()

        for i in range(min(count, 100)):

            src = await elements.nth(i).get_attribute("src")

            if not src or not src.startswith("http"):
                continue

            alt = (
                await elements.nth(i).get_attribute("alt")
                or ""
            )

            text = (
                src + " " + alt
            ).lower()

            if any(
                x in text
                for x in [
                    "logo",
                    "icon",
                    "banner",
                    "sprite"
                ]
            ):
                continue

            images.append(src)

    except Exception:
        pass

    # Remove duplicates
    unique_images = []

    for image in images:

        if image not in unique_images:
            unique_images.append(image)

        if len(unique_images) >= MAX_IMAGES:
            break

    return unique_images


def find_description(body_text, json_ld):

    # Try JSON-LD first
    for item in json_ld:

        if not isinstance(item, dict):
            continue

        description = item.get("description")

        if description:
            return clean_text(description)

    # Try page text
    lines = [
        clean_text(line)
        for line in body_text.splitlines()
        if clean_text(line)
    ]

    for i, line in enumerate(lines):

        if line.lower() in [
            "description",
            "product description"
        ]:

            collected = []

            for next_line in lines[i + 1:i + 15]:

                lower = next_line.lower()

                if lower in [
                    "specifications",
                    "highlights",
                    "offers",
                    "seller",
                    "ratings & reviews"
                ]:
                    break

                if len(next_line) > 20:
                    collected.append(next_line)

            if collected:
                return " ".join(collected[:5])

    return ""


def find_availability(body_text):

    text = body_text.lower()

    in_stock = None
    is_available = None
    cod_available = None
    emi_available = None

    # ========================================================
    # STOCK
    # ========================================================

    if any(
        phrase in text
        for phrase in [
            "out of stock",
            "currently unavailable",
            "not available"
        ]
    ):
        in_stock = False
        is_available = False

    elif any(
        phrase in text
        for phrase in [
            "in stock",
            "add to cart",
            "buy now"
        ]
    ):
        in_stock = True
        is_available = True

    # ========================================================
    # COD
    # ========================================================

    if any(
        phrase in text
        for phrase in [
            "cash on delivery",
            "cash on delivery available",
            "cod available"
        ]
    ):
        cod_available = True

    elif any(
        phrase in text
        for phrase in [
            "cod not available",
            "cash on delivery not available"
        ]
    ):
        cod_available = False

    # ========================================================
    # EMI
    # ========================================================

    if any(
        phrase in text
        for phrase in [
            "no cost emi",
            "emi available",
            "buy with emi",
            "easy emi"
        ]
    ):
        emi_available = True

    elif "emi not available" in text:
        emi_available = False

    return {
        "in_stock": in_stock,
        "is_available": is_available,
        "cod_available": cod_available,
        "emi_available": emi_available
    }


# ============================================================
# LABELED VALUES
# ============================================================

def find_labeled_value(
    body_text,
    labels
):

    lines = [

        clean_text(line)

        for line in body_text.splitlines()

        if clean_text(line)

    ]

    for i, line in enumerate(lines):

        lower = line.lower()

        for label in labels:

            label_lower = (
                label.lower()
            )

            if lower == label_lower:

                if i + 1 < len(lines):

                    value = clean_text(
                        lines[i + 1]
                    )

                    if value:

                        return value

            pattern = (
                r"^"
                + re.escape(label)
                + r"\s*[:\-]\s*(.+)$"
            )

            match = re.search(
                pattern,
                line,
                re.IGNORECASE
            )

            if match:

                value = clean_text(
                    match.group(1)
                )

                if value:

                    return value

    return ""


# ============================================================
# BASIC PRODUCT DETAILS
# ============================================================

async def extract_basic_details(
    page,
    body_text,
    json_ld,
    product_name
):

    brand = ""

    color = ""

    ram = ""

    storage = ""

    size = ""

    display_size = ""

    size_unit = ""

    style_code = ""

    product_family = ""

    seller = ""

    seller_average_rating = ""

    seller_no_of_ratings = ""

    seller_no_of_reviews = ""


    # --------------------------------------------------------
    # BRAND FROM JSON-LD
    # --------------------------------------------------------

    for item in json_ld:

        if not isinstance(
            item,
            dict
        ):
            continue

        brand_data = item.get(
            "brand"
        )

        if isinstance(
            brand_data,
            dict
        ):

            brand = clean_text(
                brand_data.get(
                    "name",
                    ""
                )
            )

        elif isinstance(
            brand_data,
            str
        ):

            brand = clean_text(
                brand_data
            )

        if brand:

            break


    # --------------------------------------------------------
    # BRAND FROM PAGE
    # --------------------------------------------------------

    if not brand:

        brand = find_labeled_value(
            body_text,
            ["Brand"]
        )


    # --------------------------------------------------------
    # BRAND FROM PRODUCT NAME
    # --------------------------------------------------------

    if not brand:

        common_brands = [

            "Apple",
            "Samsung",
            "Google",
            "OnePlus",
            "Xiaomi",
            "Redmi",
            "Realme",
            "Motorola",
            "Vivo",
            "Oppo",
            "Nothing",
            "Poco",
            "iQOO",
            "Sony",
            "Asus",
            "Lenovo",
            "Dell",
            "HP",
            "Acer"

        ]

        for candidate in common_brands:

            if product_name.lower().startswith(
                candidate.lower()
            ):

                brand = candidate

                break


    # --------------------------------------------------------
    # COLOR
    # --------------------------------------------------------

    color = find_labeled_value(
        body_text,
        [
            "Color",
            "Colour"
        ]
    )


    # --------------------------------------------------------
    # RAM
    # --------------------------------------------------------

    ram = find_labeled_value(
        body_text,
        ["RAM"]
    )


    # --------------------------------------------------------
    # STORAGE
    # --------------------------------------------------------

    storage = find_labeled_value(
        body_text,
        [
            "Internal Storage",
            "Storage",
            "Storage Capacity"
        ]
    )


    # --------------------------------------------------------
    # SELLER
    # --------------------------------------------------------

    seller = find_labeled_value(
        body_text,
        ["Seller"]
    )


    # --------------------------------------------------------
    # SELLER FALLBACK
    # --------------------------------------------------------

    if not seller:

        try:

            seller_elements = page.locator(
                "[id*='seller'], "
                "[class*='seller']"
            )

            count = await seller_elements.count()

            for i in range(
                min(count, 10)
            ):

                try:

                    candidate = clean_text(
                        await seller_elements.nth(
                            i
                        ).inner_text(
                            timeout=1000
                        )
                    )

                    if (
                        candidate
                        and len(candidate) < 100
                        and "seller" not in candidate.lower()
                    ):

                        seller = candidate

                        break

                except Exception:

                    continue

        except Exception:

            pass


    # --------------------------------------------------------
    # COLOR FALLBACK
    # --------------------------------------------------------

    if not color:

        match = re.search(
            r"\(([^,()]+),\s*[\d.]+\s*(?:GB|TB)",
            product_name,
            re.IGNORECASE
        )

        if match:

            color = clean_text(
                match.group(1)
            )


    if not color:
        match = re.search(r"\(([^,()]+)\)", product_name)
        if match:
            candidate = clean_text(match.group(1))
            if len(candidate) < 25 and not re.search(r"\b(GB|TB|Windows|Intel|AMD|Graphics)\b", candidate, re.IGNORECASE):
                color = candidate


    # --------------------------------------------------------
    # STORAGE FALLBACK
    # --------------------------------------------------------

    if not storage:
        # Look for explicit storage keywords first
        match = re.search(r"\b(\d+(?:\.\d+)?)\s*(GB|TB)\s*(?:SSD|HDD|ROM|Storage|eMMC|NVMe)\b", product_name, re.IGNORECASE)
        if match:
            storage = f"{match.group(1)} {match.group(2).upper()}"
        else:
            # Fallback to standard sizes if no keyword
            matches = re.findall(r"\b(128|256|512|1024)\s*GB\b|\b([1-4])\s*TB\b", product_name, re.IGNORECASE)
            if matches:
                # pick the first one matched
                for m in matches:
                    if m[0]: 
                        storage = f"{m[0]} GB"
                        break
                    if m[1]:
                        storage = f"{m[1]} TB"
                        break


    # --------------------------------------------------------
    # RAM FALLBACK
    # --------------------------------------------------------

    if not ram:

        match = re.search(
            r"(?:RAM|RAM Type)\s*[:\-]?\s*"
            r"(\d+(?:\.\d+)?)\s*(GB|MB)",
            body_text,
            re.IGNORECASE
        )

        if match:

            ram = (
                match.group(1)
                + " "
                + match.group(2).upper()
            )


    if not ram:
        match = re.search(r"\b(\d+(?:\.\d+)?)\s*GB\s*RAM\b", body_text, re.IGNORECASE)
        if not match:
            match = re.search(r"\b(\d+(?:\.\d+)?)\s*GB\s*(?:LPDDR|DDR)\b", body_text, re.IGNORECASE)
        if match:
            ram = f"{match.group(1)} GB"


    # --------------------------------------------------------
    # SIZE
    # --------------------------------------------------------

    size = find_labeled_value(
        body_text,
        [
            "Size",
            "Size Name",
            "Shoe Size",
            "Clothing Size"
        ]
    )

    if not size:

        match = re.search(
            r"\b(?:Size)\s*[:\-]?\s*([A-Za-z0-9 .]+)",
            body_text,
            re.IGNORECASE
        )

        if match:
            size = clean_text(
                match.group(1)
            )

    # --------------------------------------------------------
    # DISPLAY SIZE
    # --------------------------------------------------------

    display_size = find_labeled_value(
        body_text,
        [
            "Display Size",
            "Screen Size",
            "Screen Size (in)",
            "Display"
        ]
    )

    if not display_size:

        match = re.search(
            r"\b(\d+(?:\.\d+)?)\s*(inch|inches|cm)\b",
            product_name + " " + body_text,
            re.IGNORECASE
        )

        if match:
            display_size = (
                match.group(1)
                + " "
                + match.group(2)
            )

    # --------------------------------------------------------
    # SIZE UNIT
    # --------------------------------------------------------

    if display_size:

        if re.search(
            r"\binch|inches\b",
            display_size,
            re.IGNORECASE
        ):
            size_unit = "inch"

        elif re.search(
            r"\bcm\b",
            display_size,
            re.IGNORECASE
        ):
            size_unit = "cm"

    # --------------------------------------------------------
    # STYLE CODE
    # --------------------------------------------------------

    style_code = find_labeled_value(
        body_text,
        [
            "Model Number",
            "Model Name",
            "Style Code",
            "Model"
        ]
    )

    # --------------------------------------------------------
    # PRODUCT FAMILY
    # --------------------------------------------------------

    product_family = find_labeled_value(
        body_text,
        [
            "Product Family",
            "Series",
            "Series Name"
        ]
    )

    # --------------------------------------------------------
    # SELLER RATING
    # --------------------------------------------------------

    seller_average_rating = find_labeled_value(
        body_text,
        [
            "Seller Rating",
            "Seller Average Rating"
        ]
    )

    # --------------------------------------------------------
    # SELLER RATINGS COUNT
    # --------------------------------------------------------

    seller_no_of_ratings = find_labeled_value(
        body_text,
        [
            "Seller Ratings",
            "Seller Ratings Count"
        ]
    )

    # --------------------------------------------------------
    # SELLER REVIEWS COUNT
    # --------------------------------------------------------

    seller_no_of_reviews = find_labeled_value(
        body_text,
        [
            "Seller Reviews",
            "Seller Reviews Count"
        ]
    )

    # --------------------------------------------------------
    # SELLER RATING (regex fallback)
    # --------------------------------------------------------

    seller_rating_match = re.search(
        r"Seller.*?([1-5](?:\.\d)?)\s*★?",
        body_text,
        re.IGNORECASE | re.DOTALL
    )

    if seller_rating_match and not seller_average_rating:

        seller_average_rating = clean_text(
            seller_rating_match.group(1)
        )


    # --------------------------------------------------------
    # SELLER RATINGS / REVIEWS (regex fallback)
    # --------------------------------------------------------

    seller_section_match = re.search(
        r"Seller.*?(?=\n\s*\n|Highlights|Specifications|Description|Services|Warranty|$)",
        body_text,
        re.IGNORECASE | re.DOTALL
    )

    seller_section = (
        seller_section_match.group(0)
        if seller_section_match
        else body_text
    )


    if not seller_no_of_ratings:

        rating_matches = re.findall(
            r"([\d,]+)\s*(?:Ratings?|rating)",
            seller_section,
            re.IGNORECASE
        )

        if rating_matches:

            seller_no_of_ratings = clean_text(
                rating_matches[0]
            )


    if not seller_no_of_reviews:

        review_matches = re.findall(
            r"([\d,]+)\s*(?:Reviews?|reviews)",
            seller_section,
            re.IGNORECASE
        )

        if review_matches:

            seller_no_of_reviews = clean_text(
                review_matches[0]
            )

    return {

        "brand": brand,

        "color": color,

        "ram": ram,

        "storage": storage,

        "size": size,

        "display_size": display_size,

        "size_unit": size_unit,

        "style_code": style_code,

        "product_family": product_family,

        "seller": seller,

        "seller_average_rating": seller_average_rating,

        "seller_no_of_ratings": seller_no_of_ratings,

        "seller_no_of_reviews": seller_no_of_reviews

    }


# ============================================================
# HIGHLIGHTS
# ============================================================

async def extract_highlights(page):

    highlights = []

    # ========================================================
    # METHOD 1 — Normal Highlights section
    # ========================================================

    try:

        headings = page.get_by_text(
            "Highlights",
            exact=True
        )

        count = await headings.count()

        for i in range(count):

            heading = headings.nth(i)

            try:

                if not await heading.is_visible():
                    continue

                section = heading.locator(
                    "xpath=ancestor::*"
                    "[self::div or self::section]"
                    "[.//li][1]"
                )

                if await section.count() == 0:
                    continue

                items = section.locator("li")

                item_count = await items.count()

                for j in range(
                    min(item_count, MAX_HIGHLIGHTS)
                ):

                    text = clean_text(
                        await items.nth(j).inner_text()
                    )

                    if not text:
                        continue

                    if len(text) > 300:
                        continue

                    if text not in highlights:

                        highlights.append(text)

                if highlights:
                    break

            except Exception:
                continue

    except Exception:
        pass


    # ========================================================
    # METHOD 2 — Product Highlights text in body
    # ========================================================

    if not highlights:

        try:

            body_text = await page.locator(
                "body"
            ).inner_text()

            lines = [
                clean_text(x)
                for x in body_text.splitlines()
                if clean_text(x)
            ]

            for i, line in enumerate(lines):

                lower = line.lower()

                if (
                    "product highlights" not in lower
                    and lower != "highlights"
                ):
                    continue

                # Collect following lines
                for next_line in lines[i + 1:i + 20]:

                    text = clean_text(next_line)

                    if not text:
                        continue

                    # Stop at another major section
                    stop_words = [
                        "available offers",
                        "offers",
                        "seller",
                        "services",
                        "specifications",
                        "warranty",
                        "ratings & reviews",
                    ]

                    if any(
                        word in text.lower()
                        for word in stop_words
                    ):
                        break

                    # Ignore navigation / headings
                    if len(text) < 3:
                        continue

                    if len(text) > 300:
                        continue

                    if text not in highlights:

                        highlights.append(text)

                    if len(highlights) >= MAX_HIGHLIGHTS:
                        break

                if highlights:
                    break

        except Exception:
            pass


    # ========================================================
    # CLEAN HIGHLIGHTS
    # ========================================================

    cleaned = []

    for item in highlights:

        item = clean_text(item)

        if not item:
            continue

        # Remove duplicate entries
        if item.lower() in {
            x.lower()
            for x in cleaned
        }:
            continue

        # Ignore obvious headings
        if item.lower() in [
            "highlights",
            "product highlights",
        ]:
            continue

        cleaned.append(item)

    return cleaned[:MAX_HIGHLIGHTS]


# ============================================================
# OFFERS
# ============================================================

async def extract_offers(
    page,
    body_text
):

    offers = []

    # ========================================================
    # OFFER KEYWORDS
    # ========================================================

    keywords = [

        "bank offer",
        "bank discount",
        "special price",
        "special offer",

        "exchange offer",
        "exchange discount",

        "no cost emi",
        "no-cost emi",
        "emi",

        "cashback",
        "cash back",

        "instant discount",

        "credit card offer",
        "credit card discount",

        "debit card offer",
        "debit card discount",

        "upi offer",
        "upi discount",

        "additional offer",
        "additional discount",

        "partner offer",
        "partner discount",
    ]


    # ========================================================
    # COLLECT OFFER LINES FROM PAGE
    # ========================================================

    try:

        lines = [
            clean_text(line)
            for line in body_text.splitlines()
            if clean_text(line)
        ]

        for line in lines:

            text = clean_text(line)

            if not text:
                continue

            if len(text) > 500:
                continue

            lower = text.lower()

            matched = any(
                keyword in lower
                for keyword in keywords
            )

            if not matched:
                continue

            # Ignore navigation-only text
            if lower in [
                "offers",
                "available offers",
                "view all offers",
            ]:
                continue

            if text not in offers:
                offers.append(text)

            if len(offers) >= MAX_OFFERS:
                break

    except Exception:
        pass


    # ========================================================
    # TRY OFFER ELEMENTS FROM DOM
    # ========================================================

    if len(offers) < MAX_OFFERS:

        selectors = [

            "[class*='offer']",

            "[id*='offer']",

            "[class*='Offer']",

            "[id*='Offer']",

        ]

        for selector in selectors:

            try:

                elements = page.locator(
                    selector
                )

                count = await elements.count()

                for i in range(
                    min(count, 50)
                ):

                    try:

                        text = clean_text(
                            await elements.nth(i).inner_text(
                                timeout=1000
                            )
                        )

                        if not text:
                            continue

                        if len(text) > 500:
                            continue

                        lower = text.lower()

                        if not any(
                            keyword in lower
                            for keyword in keywords
                        ):
                            continue

                        if text not in offers:
                            offers.append(text)

                        if len(offers) >= MAX_OFFERS:
                            break

                    except Exception:
                        continue

                if len(offers) >= MAX_OFFERS:
                    break

            except Exception:
                continue


    return offers[:MAX_OFFERS]


# ============================================================
# MRP
# ============================================================

async def find_mrp(page, selling_price):

    candidates = []

    try:
        body_text = await page.locator("body").inner_text()
    except Exception:
        body_text = ""

    # ========================================================
    # METHOD 1 — Explicit MRP text
    # ========================================================

    lines = [
        clean_text(line)
        for line in body_text.splitlines()
        if clean_text(line)
    ]

    for i, line in enumerate(lines):

        if "mrp" not in line.lower():
            continue

        # Same line
        matches = re.findall(
            r"(?:₹|Rs\.?|INR)\s*[\d,]+(?:\.\d+)?",
            line,
            re.IGNORECASE
        )

        candidates.extend(matches)

        # Next few lines
        for next_line in lines[i + 1:i + 5]:

            matches = re.findall(
                r"(?:₹|Rs\.?|INR)\s*[\d,]+(?:\.\d+)?",
                next_line,
                re.IGNORECASE
            )

            candidates.extend(matches)

    # ========================================================
    # METHOD 2 — Strike / deleted price
    # ========================================================

    selectors = [
        "strike",
        "del",
        "s",
        "[class*='mrp']",
        "[class*='MRP']",
        "[class*='strike']",
        "[class*='Strike']",
        "[class*='original']",
        "[class*='Original']"
    ]

    for selector in selectors:

        try:

            elements = page.locator(selector)

            count = await elements.count()

            for i in range(min(count, 50)):

                try:

                    text = clean_text(
                        await elements.nth(i).inner_text(
                            timeout=1000
                        )
                    )

                    if not text:
                        continue

                    matches = re.findall(
                        r"(?:₹|Rs\.?|INR)\s*[\d,]+(?:\.\d+)?",
                        text,
                        re.IGNORECASE
                    )

                    candidates.extend(matches)

                except Exception:
                    continue

        except Exception:
            continue

    # ========================================================
    # METHOD 3 — Look for MRP number without ₹
    # ========================================================

    for i, line in enumerate(lines):

        if "mrp" not in line.lower():
            continue

        matches = re.findall(
            r"\b\d[\d,]*(?:\.\d+)?\b",
            line
        )

        candidates.extend(matches)

        for next_line in lines[i + 1:i + 4]:

            matches = re.findall(
                r"\b\d[\d,]*(?:\.\d+)?\b",
                next_line
            )

            candidates.extend(matches)

    # ========================================================
    # CLEAN CANDIDATES
    # ========================================================

    unique_candidates = []

    seen = set()

    for candidate in candidates:

        try:

            number_text = re.sub(
                r"[^\d.]",
                "",
                str(candidate)
            )

            if not number_text:
                continue

            number = float(number_text)

        except Exception:
            continue

        if number <= 0:
            continue

        if number in seen:
            continue

        seen.add(number)

        unique_candidates.append(number)

    # ========================================================
    # MRP MUST BE GREATER THAN SELLING PRICE
    # ========================================================

    if selling_price:

        try:
            selling_number = clean_number(
                selling_price
            )
        except Exception:
            selling_number = None

        if selling_number:

            valid = [
                number
                for number in unique_candidates
                if number > selling_number
            ]

            if valid:

                # Nearest value above selling price
                valid.sort()

                return f"₹{valid[0]:,.0f}"

    return ""


# ============================================================
# DISCOUNT
# ============================================================

def find_discount(body_text):

    patterns = [
        r"(\d+(?:\.\d+)?%\s*off)",
        r"(\d+(?:\.\d+)?\s*%\s*discount)"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            body_text,
            re.IGNORECASE
        )

        if match:
            return clean_text(
                match.group(1)
            )

    return ""


def find_discount_percentage(body_text):

    patterns = [
        r"(\d+(?:\.\d+)?)\s*%\s*off",
        r"(\d+(?:\.\d+)?)\s*%\s*discount"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            body_text,
            re.IGNORECASE
        )

        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None

    return None


# ============================================================
# SHIPPING CHARGES
# ============================================================

def find_shipping_charges(body_text):

    patterns = [
        r"delivery charges?\s*[:\-]?\s*₹?\s*([\d,]+(?:\.\d+)?)",
        r"shipping charges?\s*[:\-]?\s*₹?\s*([\d,]+(?:\.\d+)?)",
        r"shipping\s*[:\-]?\s*₹?\s*([\d,]+(?:\.\d+)?)",
        r"delivery\s*[:\-]?\s*₹?\s*([\d,]+(?:\.\d+)?)"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            body_text,
            re.IGNORECASE
        )

        if match:
            try:
                return float(
                    match.group(1).replace(",", "")
                )
            except ValueError:
                continue

    if re.search(
        r"free delivery|free shipping",
        body_text,
        re.IGNORECASE
    ):
        return 0.0

    return None


# ============================================================
# CASHBACK
# ============================================================

def find_cashback(body_text):

    patterns = [
        r"cashback\s*(?:of|up to)?\s*₹?\s*([\d,]+(?:\.\d+)?)",
        r"cash back\s*(?:of|up to)?\s*₹?\s*([\d,]+(?:\.\d+)?)"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            body_text,
            re.IGNORECASE
        )

        if match:
            return clean_text(
                match.group(0)
            )

    return ""


# ============================================================
# READ ONE PRODUCT
# ============================================================

async def read_product(
    page,
    product_url
):

    print("\n")

    print("=" * 70)

    print("🧠 PRODUCT AGENT")

    print("=" * 70)

    print(
        "🌐 Product:"
    )

    print(
        product_url
    )


    try:

        await page.goto(
            product_url,
            wait_until="domcontentloaded",
            timeout=PAGE_TIMEOUT
        )

    except PlaywrightTimeoutError:

        print(
            "⚠️ Page load timeout."
        )

    except Exception as error:

        print(
            "❌ Could not open product:"
        )

        print(error)

        return None


    # Give Flipkart time to render dynamic content
    await page.wait_for_timeout(PAGE_WAIT)

    # Scroll slightly to trigger lazy-loaded content
    try:

        await page.evaluate(
            "window.scrollTo(0, 500)"
        )

        await page.wait_for_timeout(1500)

        await page.evaluate(
            "window.scrollTo(0, 0)"
        )

    except Exception:
        pass


    try:

        body_text = await page.locator(
            "body"
        ).inner_text()

    except Exception:

        body_text = ""


    json_ld = await get_json_ld(
        page
    )


    product_name = find_product_name(
        body_text,
        json_ld
    )


    if not product_name:

        try:

            product_name = clean_text(
                await page.title()
            )

        except Exception:

            product_name = "Unknown Product"


    price = find_price(
        body_text,
        json_ld
    )


    mrp = await find_mrp(
        page,
        price
    )


    discount = find_discount(
        body_text
    )


    discount_percentage = find_discount_percentage(
        body_text
    )


    shipping_charges = find_shipping_charges(
        body_text
    )


    cashback = find_cashback(
        body_text
    )


    rating = find_rating(
        body_text,
        json_ld
    )


    rating_count = find_rating_count(
        body_text,
        json_ld
    )


    product_id = find_product_id(
        product_url,
        body_text,
        json_ld
    )


    image = await find_main_image(
        page,
        json_ld
    )

    image_urls = await find_image_urls(
        page,
        json_ld
    )


    highlights = await extract_highlights(
        page
    )


    offers = await extract_offers(
        page,
        body_text
    )

    description = find_description(
        body_text,
        json_ld
    )

    availability = find_availability(
        body_text
    )


    details = await extract_basic_details(
        page,
        body_text,
        json_ld,
        product_name
    )


    category = detect_product_category(
        product_name,
        product_url
    )

    if category not in ALLOWED_CATEGORIES:

        print(
            "⛔ Product rejected:"
            " outside allowed categories"
        )

        return None


    product = {

        "source": "Flipkart",

        "product_id": product_id,

        "category": category,

        "url": product_url,

        "product_url": product_url,

        "product_name": product_name,

        # Images
        "image": image,

        "image_urls": image_urls,

        # Price
        "price": price,

        "selling_price": price,

        "special_price": price,

        "mrp": mrp,

        "discount": discount,

        "discount_percentage": discount_percentage,

        "shipping_charges": shipping_charges,

        "cashback": cashback,

        # Rating
        "rating": rating,

        "rating_count": rating_count,

        # Basic details
        "brand": details["brand"],

        "color": details["color"],

        "ram": details["ram"],

        "storage": details["storage"],

        "size": details["size"],

        "display_size": details["display_size"],

        "size_unit": details["size_unit"],

        "style_code": details["style_code"],

        "product_family": details["product_family"],

        # Seller
        "seller": details["seller"],

        "seller_average_rating":
            details["seller_average_rating"],

        "seller_no_of_ratings":
            details["seller_no_of_ratings"],

        "seller_no_of_reviews":
            details["seller_no_of_reviews"],

        # Product information
        "description": description,

        "highlights": highlights,

        "offers": offers,

        # Availability
        "in_stock":
            availability["in_stock"],

        "is_available":
            availability["is_available"],

        "cod_available":
            availability["cod_available"],

        "emi_available":
            availability["emi_available"],

        # Generic category attributes
        "attributes": {
            "ram": details["ram"],
            "storage": details["storage"],
            "size": details["size"],
            "display_size": details["display_size"],
            "size_unit": details["size_unit"],
            "style_code": details["style_code"],
            "product_family": details["product_family"],
            "color": details["color"],
            "rating": rating,
            "rating_count": rating_count
        },

        "last_updated":
            datetime.now().isoformat()

    }


    # ========================================================
    # DISPLAY
    # ========================================================

    print("\n📦 PRODUCT UNDERSTOOD")

    print(
        f"   Product ID: {product['product_id']}"
    )

    print(
        f"   Name: {product['product_name']}"
    )

    print(
        f"   Price: {product['price']}"
    )

    print(
        f"   MRP: {product['mrp']}"
    )

    print(
        f"   Discount: {product['discount']}"
    )

    print(
        f"   Rating: {product['rating']}"
    )

    print(
        f"   Rating Count: {product['rating_count']}"
    )

    print(
        f"   Brand: {product['brand']}"
    )

    print(
        f"   Color: {product['color']}"
    )

    print(
        f"   RAM: {product['ram']}"
    )

    print(
        f"   Storage: {product['storage']}"
    )

    print(
        f"   Seller: {product['seller']}"
    )

    print(
        f"   Seller Rating: "
        f"{product['seller_average_rating']}"
    )

    print(
        f"   Seller Ratings: "
        f"{product['seller_no_of_ratings']}"
    )

    print(
        f"   Seller Reviews: "
        f"{product['seller_no_of_reviews']}"
    )

    print(
        f"   Image: "
        f"{'YES' if image else 'NO'}"
    )

    print(
        f"   Highlights: "
        f"{len(highlights)}"
    )

    print(
        f"   Offers: "
        f"{len(offers)}"
    )


    return product


# ============================================================
# PROCESS PRODUCT
# ============================================================

async def process_product(
    page,
    product_url
):

    product_url = clean_url(
        product_url
    )


    if not product_url:

        print(
            "❌ Invalid Flipkart URL"
        )

        return None


    if "/p/" not in product_url:

        print(
            "❌ Not a product URL:"
        )

        print(
            product_url
        )

        return None


    product = await read_product(
        page,
        product_url
    )


    if not product:

        return None


    print("\n📤 LIVE SYNC")

    success = send_product(
        product
    )


    if success:

        print(
            "✅ Product reflected "
            "on your website"
        )

    else:

        print(
            "⚠️ Product could not "
            "be sent to website"
        )


    return product


# ============================================================
# PROCESS MULTIPLE PRODUCTS
# ============================================================

async def process_products(
    product_urls
):

    #
    # Remove duplicates.
    #

    unique_urls = []

    seen = set()

    for url in product_urls:

        url = clean_url(
            url
        )

        if not url:

            continue

        if url in seen:

            continue

        seen.add(url)

        unique_urls.append(
            url
        )


    print("\n")

    print("#" * 70)

    print(
        "🤖 PRODUCT AGENT STARTING"
    )

    print("#" * 70)

    print(
        f"\n📦 Products received:"
        f" {len(unique_urls)}"
    )


    if not unique_urls:

        print(
            "❌ No product URLs."
        )

        return []


    results = []


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


        try:

            for number, url in enumerate(
                unique_urls,
                start=1
            ):

                print("\n")

                print(
                    f"📦 Product "
                    f"{number}/"
                    f"{len(unique_urls)}"
                )


                product = await process_product(
                    page,
                    url
                )


                if product:

                    results.append(
                        product
                    )


                if number < len(
                    unique_urls
                ):

                    await asyncio.sleep(
                        PRODUCT_DELAY
                    )


        finally:

            await context.close()

            await browser.close()


    print("\n")

    print("#" * 70)

    print(
        "📊 PRODUCT AGENT COMPLETE"
    )

    print("#" * 70)

    print(
        f"✅ Successfully processed:"
        f" {len(results)}"
    )

    print(
        f"❌ Failed:"
        f" {len(unique_urls) - len(results)}"
    )

    print("#" * 70)


    return results


# ============================================================
# TEST MODE
# ============================================================

async def test_product():

    #
    # Temporary test URL.
    #
    # Later this will come directly from
    # Discovery Agent.
    #

    test_url = (
        "https://www.flipkart.com/"
        "apple-iphone-15-black-128-gb/"
        "p/itm6ac6485515ae4"
    )


    await process_products(
        [test_url]
    )


# ============================================================
# RUN DIRECTLY
# ============================================================

if __name__ == "__main__":

    try:

        asyncio.run(
            test_product()
        )

    except KeyboardInterrupt:

        print(
            "\n🛑 Product Agent stopped."
        )