import asyncio
import json
import re
import requests
from datetime import datetime
from playwright.async_api import async_playwright


# ============================================================
# SETTINGS
# ============================================================

FLIPKART_URL = (
    "https://www.flipkart.com/apple-iphone-15-black-128-gb/"
    "p/itm6ac6485515ae4"
)

FAKE_WEBSITE_API = (
    "http://127.0.0.1:8000/api/product"
)

# For testing: 5 minutes
CHECK_INTERVAL = 5 * 60


# ============================================================
# CLEAN TEXT
# ============================================================

def clean_text(value):

    if not value:
        return ""

    return re.sub(
        r"\s+",
        " ",
        value
    ).strip()


# ============================================================
# EXTRACT JSON-LD
# ============================================================

async def get_json_ld(page):

    result = []

    try:

        scripts = page.locator(
            'script[type="application/ld+json"]'
        )

        count = await scripts.count()

        for i in range(count):

            try:

                text = await scripts.nth(i).inner_text()

                data = json.loads(text)

                if isinstance(data, list):

                    result.extend(data)

                else:

                    result.append(data)

            except Exception:

                pass

    except Exception:

        pass

    return result


# ============================================================
# FIND PRICE
# ============================================================

def find_price(body_text, json_ld):

    # First try structured data

    for item in json_ld:

        if not isinstance(item, dict):
            continue

        offers = item.get("offers")

        if isinstance(offers, dict):

            price = offers.get("price")

            if price:
                return "₹" + str(price)

        elif isinstance(offers, list):

            for offer in offers:

                if isinstance(offer, dict):

                    price = offer.get("price")

                    if price:
                        return "₹" + str(price)


    # Fallback: page text

    matches = re.findall(
        r"₹\s*[\d,]+",
        body_text
    )

    if matches:

        return matches[0]

    return ""


# ============================================================
# FIND RATING
# ============================================================

def find_rating(body_text, json_ld):

    for item in json_ld:

        if not isinstance(item, dict):
            continue

        rating = item.get(
            "aggregateRating"
        )

        if isinstance(rating, dict):

            value = rating.get(
                "ratingValue"
            )

            if value:
                return str(value)


    matches = re.findall(
        r"\b[1-5]\.\d\b",
        body_text
    )

    if matches:

        return matches[0]

    return ""


# ============================================================
# FIND RATING COUNT
# ============================================================

def find_rating_count(body_text, json_ld):

    for item in json_ld:

        if not isinstance(item, dict):
            continue

        rating = item.get(
            "aggregateRating"
        )

        if isinstance(rating, dict):

            count = (
                rating.get("reviewCount")
                or rating.get("ratingCount")
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
# FIND MAIN IMAGE
# ============================================================

async def find_main_image(page, json_ld):

    # JSON-LD first

    for item in json_ld:

        if not isinstance(item, dict):
            continue

        image = item.get("image")

        if isinstance(image, str):

            if image.startswith("http"):

                return image

        if isinstance(image, list):

            for img in image:

                if isinstance(img, str):

                    if img.startswith("http"):

                        return img


    # OpenGraph

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


    # Try images

    try:

        images = page.locator("img")

        count = await images.count()

        for i in range(count):

            img = images.nth(i)

            src = await img.get_attribute(
                "src"
            )

            alt = await img.get_attribute(
                "alt"
            )

            if not src:
                continue

            if not src.startswith("http"):
                continue

            # Ignore obvious logos

            text = (
                (alt or "") +
                " " +
                src
            ).lower()

            if "flipkart" in text:
                continue

            return src

    except Exception:

        pass

    return ""


# ============================================================
# EXTRACT PRODUCT HIGHLIGHTS
# ============================================================

async def extract_highlights(page):

    highlights = []

    print("   🔎 Watching Product Highlights...")

    # --------------------------------------------------------
    # Find the "Product Highlights" section
    # --------------------------------------------------------

    try:

        elements = page.locator("div, section")

        count = await elements.count()

        for i in range(min(count, 5000)):

            element = elements.nth(i)

            try:
                text = clean_text(
                    await element.inner_text(timeout=200)
                )
            except Exception:
                continue

            if not text:
                continue

            # We only want the actual Product Highlights section
            if not re.search(
                r"Product\s+Highlights",
                text,
                re.IGNORECASE
            ):
                continue

            # Find list items inside this section
            items = element.locator("li")

            item_count = await items.count()

            if item_count == 0:
                continue

            for j in range(min(item_count, 20)):

                item_text = clean_text(
                    await items.nth(j).inner_text()
                )

                if not item_text:
                    continue

                if len(item_text) > 300:
                    continue

                # Ignore unrelated website/menu items
                if item_text.lower() in [
                    "notification settings",
                    "my profile",
                    "orders",
                    "wishlist",
                    "login",
                    "logout",
                    "flipkart plus",
                    "customer care",
                    "become a seller",
                    "download app"
                ]:
                    continue

                if item_text not in highlights:

                    highlights.append(item_text)

            # Stop once we found the real section
            if highlights:
                break

    except Exception as error:

        print(
            "   ⚠️ Product Highlights error:",
            error
        )


    # --------------------------------------------------------
    # Result
    # --------------------------------------------------------

    print(
        f"   ✓ Product Highlights found: "
        f"{len(highlights)}"
    )

    for item in highlights:

        print(
            f"      • {item}"
        )

    return highlights[:15]


# ============================================================
# FIND SPECIFICATIONS
# ============================================================

async def find_specifications(page):

    specifications = {}

    # --------------------------------------------------------
    # Tables
    # --------------------------------------------------------

    try:

        rows = page.locator("tr")

        count = await rows.count()

        for i in range(count):

            row = rows.nth(i)

            cells = row.locator("td")

            cell_count = await cells.count()

            if cell_count >= 2:

                key = clean_text(
                    await cells.nth(0).inner_text()
                )

                value = clean_text(
                    await cells.nth(1).inner_text()
                )

                if key and value:

                    if len(key) < 150:

                        specifications[key] = value

    except Exception:

        pass


    # --------------------------------------------------------
    # Definition lists
    # --------------------------------------------------------

    try:

        dt_elements = page.locator("dt")

        count = await dt_elements.count()

        for i in range(count):

            key = clean_text(
                await dt_elements.nth(i).inner_text()
            )

            if not key:
                continue

            try:

                value = clean_text(
                    await dt_elements.nth(i)
                    .locator("xpath=following-sibling::dd[1]")
                    .inner_text()
                )

                if value:

                    specifications[key] = value

            except Exception:

                pass

    except Exception:

        pass


    return specifications


# ============================================================
# FIND BASIC PRODUCT DETAILS
# ============================================================

def find_labeled_value(body_text, labels):

    lines = [
        clean_text(line)
        for line in body_text.splitlines()
        if clean_text(line)
    ]

    for i, line in enumerate(lines):

        lower = line.lower()

        for label in labels:

            label_lower = label.lower()

            # Example:
            # Brand
            # Apple

            if lower == label_lower:

                if i + 1 < len(lines):

                    value = clean_text(
                        lines[i + 1]
                    )

                    if value:
                        return value


            # Example:
            # Brand: Apple

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
# FIND BASIC DETAILS FROM FLIPKART
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
    seller = ""


    # ========================================================
    # BRAND
    # ========================================================

    for item in json_ld:

        if not isinstance(item, dict):
            continue

        brand_data = item.get("brand")

        if isinstance(brand_data, dict):

            brand = clean_text(
                brand_data.get("name", "")
            )

        elif isinstance(brand_data, str):

            brand = clean_text(
                brand_data
            )

        if brand:
            break


    if not brand:

        brand = find_labeled_value(
            body_text,
            ["Brand"]
        )


    # Fallback brand from product name
    if not brand and product_name:

        first_word = product_name.split()[0] if product_name.split() else ""

        common_brands = [
            "Apple", "Samsung", "Google", "OnePlus", "Xiaomi", "Realme",
            "Motorola", "Vivo", "Oppo", "Nothing", "Poco", "iQOO",
            "Sony", "Asus", "Lenovo", "Dell", "HP", "Acer"
        ]

        for b in common_brands:
            if product_name.lower().startswith(b.lower()):
                brand = b
                break

        if not brand and first_word:
            brand = first_word


    # ========================================================
    # COLOR
    # ========================================================

    color = find_labeled_value(
        body_text,
        [
            "Color",
            "Colour"
        ]
    )


    # ========================================================
    # RAM
    # ========================================================

    ram = find_labeled_value(
        body_text,
        [
            "RAM"
        ]
    )


    # ========================================================
    # STORAGE
    # ========================================================

    storage = find_labeled_value(
        body_text,
        [
            "Internal Storage",
            "Storage",
            "Storage Capacity"
        ]
    )


    # ========================================================
    # SELLER
    # ========================================================

    seller = find_labeled_value(
        body_text,
        [
            "Seller"
        ]
    )

    if not seller:

        try:
            seller_elem = page.locator("#sellerName, div._1RLviY, [id*='seller']").first
            if await seller_elem.count():
                candidate_seller = clean_text(await seller_elem.inner_text())
                if candidate_seller and len(candidate_seller) < 100:
                    seller = candidate_seller
        except Exception:
            pass

    if not seller:

        lines = [
            clean_text(x)
            for x in body_text.splitlines()
            if clean_text(x)
        ]

        for i, line in enumerate(lines):

            if line.lower() == "seller" or "seller:" in line.lower():

                if i + 1 < len(lines):

                    candidate = clean_text(
                        lines[i + 1]
                    )

                    if (
                        candidate
                        and len(candidate) < 100
                        and not candidate.lower().startswith("rating")
                    ):

                        seller = candidate

                        break


    # ========================================================
    # COLOR FALLBACK
    # Example:
    # Apple iPhone 15 (Black, 128 GB)
    # ========================================================

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

        match = re.search(
            r"\(([^,()]+)\)",
            product_name,
            re.IGNORECASE
        )

        if match:

            candidate = clean_text(match.group(1))

            if not re.search(r"^\d+\s*(?:GB|TB)$", candidate, re.IGNORECASE):

                color = candidate


    # ========================================================
    # STORAGE FALLBACK
    # Example:
    # Apple iPhone 15 (Black, 128 GB)
    # ========================================================

    if not storage:

        match = re.search(
            r"(\d+(?:\.\d+)?)\s*(GB|TB)",
            product_name,
            re.IGNORECASE
        )

        if match:

            storage = (
                match.group(1)
                + " "
                + match.group(2).upper()
            )


    # ========================================================
    # RAM FALLBACK
    # ========================================================

    if not ram:

        # Look for RAM anywhere in page text

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


    # ========================================================
    # EXTRA RAM PATTERNS
    # ========================================================

    if not ram:

        match = re.search(
            r"(\d+(?:\.\d+)?)\s*GB\s*RAM",
            body_text,
            re.IGNORECASE
        )

        if match:

            ram = (
                match.group(1)
                + " GB"
            )


    return {
        "brand": brand,
        "color": color,
        "ram": ram,
        "storage": storage,
        "seller": seller
    }


# ============================================================
# FIND OFFERS
# ============================================================

async def find_offers(page, body_text):

    offers = []

    keywords = [
        "Bank Offer",
        "bank offer",
        "Special Price",
        "special price",
        "Exchange Offer",
        "exchange offer",
        "No Cost EMI",
        "no cost emi"
    ]


    lines = body_text.splitlines()

    for line in lines:

        text = clean_text(line)

        if not text:
            continue

        for keyword in keywords:

            if keyword.lower() in text.lower():

                if text not in offers:

                    offers.append(text)

                break


    return offers[:15]


# ============================================================
# EXTRACT PRODUCT
# ============================================================

async def read_flipkart_product(page):

    print("\n👀 Watching Flipkart...")

    await page.wait_for_timeout(3000)


    # Full visible page text

    body_text = await page.locator(
        "body"
    ).inner_text()


    # Structured data

    json_ld = await get_json_ld(page)


    # --------------------------------------------------------
    # NAME
    # --------------------------------------------------------

    product_name = ""


    for item in json_ld:

        if isinstance(item, dict):

            name = item.get("name")

            if name:

                product_name = clean_text(
                    str(name)
                )

                break


    if not product_name:

        try:

            product_name = clean_text(
                await page.title()
            )

        except Exception:

            product_name = "Unknown Product"


    # --------------------------------------------------------
    # PRICE
    # --------------------------------------------------------

    price = find_price(
        body_text,
        json_ld
    )


    # --------------------------------------------------------
    # MRP & DISCOUNT
    # --------------------------------------------------------

    mrp = ""
    discount = ""

    disc_match = re.search(r"(\d+%\s*off)", body_text, re.IGNORECASE)
    if disc_match:
        discount = clean_text(disc_match.group(1))

    try:
        strike_elem = page.locator("div._3I9_wc, div.yRaY8j, strike, [class*='strike']").first
        if await strike_elem.count():
            mrp_text = clean_text(await strike_elem.inner_text())
            if mrp_text.startswith("₹") or any(char.isdigit() for char in mrp_text):
                mrp = mrp_text
    except Exception:
        pass


    # --------------------------------------------------------
    # RATING
    # --------------------------------------------------------

    rating = find_rating(
        body_text,
        json_ld
    )


    # --------------------------------------------------------
    # RATING COUNT
    # --------------------------------------------------------

    rating_count = find_rating_count(
        body_text,
        json_ld
    )


    # --------------------------------------------------------
    # IMAGE
    # --------------------------------------------------------

    image = await find_main_image(
        page,
        json_ld
    )


    # --------------------------------------------------------
    # PRODUCT HIGHLIGHTS
    # --------------------------------------------------------

    highlights = await extract_highlights(page)


    # --------------------------------------------------------
    # OFFERS
    # --------------------------------------------------------

    offers = await find_offers(
        page,
        body_text
    )


    # ============================================================
    # BASIC PRODUCT DETAILS
    # ============================================================

    basic_details = await extract_basic_details(
        page,
        body_text,
        json_ld,
        product_name
    )

    brand = basic_details["brand"]

    color = basic_details["color"]

    ram = basic_details["ram"]

    storage = basic_details["storage"]

    seller = basic_details["seller"]


    # --------------------------------------------------------
    # PRODUCT OBJECT
    # --------------------------------------------------------

    product = {

        "source": "Flipkart",

        "product_url": FLIPKART_URL,

        "product_name": product_name,

        "image": image,

        "price": price,

        "mrp": mrp,

        "discount": discount,

        "rating": rating,

        "rating_count": rating_count,

        # ----------------------------------------
        # BASIC DETAILS WE ARE WATCHING
        # ----------------------------------------

        "brand": brand,

        "color": color,

        "ram": ram,

        "storage": storage,

        "seller": seller,

        # ----------------------------------------
        # OTHER DATA
        # ----------------------------------------

        "highlights": highlights,

        "offers": offers,

        "last_updated":
            datetime.now().isoformat()
    }


    return product


# ============================================================
# SEND DATA TO WEBSITE
# ============================================================

def send_to_website(product):

    print("\n📤 Sending product to fake website...")

    try:

        response = requests.post(

            FAKE_WEBSITE_API,

            json=product,

            timeout=15

        )


        if response.status_code == 200:

            print(
                "✅ Fake website updated"
            )

            return True


        print(
            "❌ Website returned:",
            response.status_code
        )

        return False


    except Exception as error:

        print(
            "❌ Could not connect to fake website"
        )

        print(error)

        return False


# ============================================================
# COMPARE DATA
# ============================================================

def product_changed(old_product, new_product):

    if old_product is None:
        return True

    fields = [
        "product_name",
        "image",
        "price",
        "mrp",
        "discount",
        "rating",
        "rating_count",
        "brand",
        "color",
        "storage",
        "ram",
        "seller",
        "highlights",
        "offers"
    ]

    for field in fields:

        old_value = old_product.get(field)
        new_value = new_product.get(field)

        if old_value != new_value:

            print(
                f"   Changed: {field}"
            )

            return True

    return False


# ============================================================
# MAIN AGENT
# ============================================================

async def flipkart_agent():

    print("=" * 70)
    print(
        "🤖 FLIPKART CONTINUOUS MONITORING AGENT"
    )
    print("=" * 70)


    previous_product = None


    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=False
        )


        page = await browser.new_page(

            viewport={
                "width": 1366,
                "height": 900
            }

        )


        print("\n🌐 Opening Flipkart...")


        try:

            await page.goto(

                FLIPKART_URL,

                wait_until="domcontentloaded",

                timeout=30000

            )


            print(
                "✅ Flipkart opened"
            )


        except Exception as error:

            print(
                "❌ Could not open Flipkart"
            )

            print(error)

            await browser.close()

            return


        # ====================================================
        # CONTINUOUS MONITORING
        # ====================================================

        while True:

            try:

                current_product = (

                    await read_flipkart_product(
                        page
                    )

                )


                print("\n" + "-" * 70)

                print(
                    "Product:",
                    current_product[
                        "product_name"
                    ]
                )

                print(
                    "Price:",
                    current_product[
                        "price"
                    ]
                )

                if current_product.get("mrp"):
                    print(
                        "🏷️ MRP:",
                        current_product["mrp"]
                    )

                if current_product.get("discount"):
                    print(
                        "📉 Discount:",
                        current_product["discount"]
                    )

                print(
                    "Rating:",
                    current_product[
                        "rating"
                    ]
                )

                print(
                    "Rating count:",
                    current_product[
                        "rating_count"
                    ]
                )

                print(
                    "Image:",
                    "YES"
                    if current_product["image"]
                    else "NO"
                )

                print(
                    "🏷️ Brand:",
                    current_product["brand"]
                )

                print(
                    "🎨 Color:",
                    current_product["color"]
                )

                print(
                    "💾 RAM:",
                    current_product["ram"]
                )

                print(
                    "💽 Storage:",
                    current_product["storage"]
                )

                print(
                    "🏪 Seller:",
                    current_product["seller"]
                )

                print(
                    "🎁 Product Highlights:",
                    len(
                        current_product["highlights"]
                    )
                )

                for highlight in current_product["highlights"]:

                    print(
                        "   •",
                        highlight
                    )

                print(
                    "💳 Offers:",
                    len(
                        current_product["offers"]
                    )
                )


                # --------------------------------------------
                # FIRST DATA / CHANGE
                # --------------------------------------------

                if product_changed(

                    previous_product,

                    current_product

                ):


                    if previous_product is None:

                        print(
                            "\n🆕 Product detected"
                        )

                    else:

                        print(
                            "\n🔄 PRODUCT UPDATED"
                        )


                    success = send_to_website(

                        current_product

                    )


                    if success:

                        previous_product = (
                            current_product
                        )


                else:

                    print(
                        "\n✓ No changes detected"
                    )


                # --------------------------------------------
                # WAIT
                # --------------------------------------------

                print(
                    f"\n⏳ Next check in "
                    f"{CHECK_INTERVAL // 60} minutes..."
                )


                await asyncio.sleep(
                    CHECK_INTERVAL
                )


                # --------------------------------------------
                # REFRESH FLIPKART
                # --------------------------------------------

                print(
                    "\n🔄 Refreshing Flipkart..."
                )


                await page.reload(

                    wait_until="domcontentloaded",

                    timeout=30000

                )


            except Exception as error:

                print(
                    "\n⚠️ Monitoring error:"
                )

                print(error)

                print(
                    "\nRetrying in 30 seconds..."
                )

                await asyncio.sleep(30)


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    try:

        asyncio.run(
            flipkart_agent()
        )

    except KeyboardInterrupt:

        print(
            "\n\n🛑 Flipkart Agent stopped."
        )