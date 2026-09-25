import sys
import os

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

# Ensure flipcart root is in sys.path so 'core' and 'agents' are importable
# regardless of the working directory when this script is launched.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import asyncio
import re
from urllib.parse import quote, urljoin, urlparse

from playwright.async_api import (
    async_playwright,
    TimeoutError as PlaywrightTimeoutError
)

from core.config import FLIPKART_BASE_URL
from agents.product_agent import process_products
from agents.category_agent import (
    get_category,
    is_allowed_product,
)


# ============================================================
# CONFIGURATION
# ============================================================

DISCOVERY_INTERVAL = 60

MAX_SCROLLS_PER_PAGE = 3

SCROLL_DELAY = 1.2

MAX_CATEGORY_PAGES = 5

PRODUCT_BATCH_SIZE = 5

MAX_PRODUCTS_PER_SEARCH = 5

PRODUCT_DELAY = 2

HEADLESS = True


# ============================================================
# SEARCH SEEDS
# ============================================================

SEARCH_QUERIES = [

    # ========================================================
    # MOBILES
    # ========================================================

    "mobile",
    "smartphone",
    "iphone",
    "iphone 15",
    "iphone 16",
    "iphone 17",
    "samsung mobile",
    "samsung galaxy",
    "oneplus mobile",
    "google pixel",
    "xiaomi mobile",
    "redmi mobile",
    "realme mobile",
    "vivo mobile",
    "oppo mobile",
    "motorola mobile",
    "nothing phone",
    "iqoo mobile",
    "poco mobile",

    # ========================================================
    # LAPTOPS
    # ========================================================

    "laptop",
    "gaming laptop",
    "hp laptop",
    "dell laptop",
    "lenovo laptop",
    "asus laptop",
    "acer laptop",
    "msi laptop",
    "macbook",
    "apple macbook",
    "windows laptop",

    # ========================================================
    # EARBUDS
    # ========================================================

    "earbuds",
    "wireless earbuds",
    "bluetooth earbuds",
    "true wireless earbuds",
    "tws earbuds",
    "airpods",
    "oneplus earbuds",
    "boat earbuds",
    "realme earbuds",
    "noise earbuds",
    "samsung earbuds",
    "oppo earbuds",

    # ========================================================
    # TVs
    # ========================================================

    "tv",
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
]


# ============================================================
# MEMORY
# ============================================================

DISCOVERED_PRODUCT_URLS = set()

DISCOVERED_CATEGORY_URLS = set()

DISCOVERED_LISTING_URLS = set()


# ============================================================
# STATISTICS
# ============================================================

STATS = {

    "rounds": 0,

    "pages_opened": 0,

    "products_found": 0,

    "new_products": 0,

    "processed_products": 0,

    "failed_products": 0,

    "categories_found": 0,

    "errors": 0,

}


# ============================================================
# URL CLEANING
# ============================================================

def clean_url(url):

    if not url:

        return ""

    url = url.strip()

    if not url.startswith("http"):

        return ""

    try:

        parsed = urlparse(url)

    except Exception:

        return ""

    if "flipkart.com" not in parsed.netloc.lower():

        return ""

    return (
        f"{parsed.scheme}://"
        f"{parsed.netloc}"
        f"{parsed.path}"
    ).rstrip("/")


# ============================================================
# PRODUCT URL VALIDATION
# ============================================================

def is_product_url(url):

    url = clean_url(url)

    if not url:

        return False

    parsed = urlparse(url)

    path = parsed.path.lower()

    #
    # Product pages normally contain /p/
    #

    if "/p/" not in path:

        return False

    #
    # Reject generic /product/p/item type links.
    #

    if path in [
        "/product/p/item",
        "/product/p/item/"
    ]:

        return False

    #
    # Product ID must contain a reasonable
    # alphanumeric identifier.
    #

    match = re.search(
        r"/p/([a-z0-9]+)$",
        path,
        re.IGNORECASE
    )

    if not match:

        return False

    product_id = match.group(1)

    if len(product_id) < 8:

        return False

    #
    # Reject generic pages.
    #

    blocked_names = [

        "product",
        "item",
        "page",
        "test",
        "sample"

    ]

    product_name = (
        path.split("/p/")[0]
        .split("/")[-1]
    )

    if product_name.lower() in blocked_names:

        return False

    return True


# ============================================================
# IGNORE URL
# ============================================================

def should_ignore_url(url):

    if not url:

        return True

    lower = url.lower()

    ignored_parts = [

        "/login",
        "/account",
        "/cart",
        "/wishlist",
        "/notifications",
        "/orders",
        "/helpcentre",
        "/seller",
        "/sell-online",
        "/privacy",
        "/terms",
        "/returnpolicy",
        "/viewcart",
        "/checkout",
        "/plus",
        "/travel",
        "/stories",
        "/compare",

    ]

    return any(
        part in lower
        for part in ignored_parts
    )


# ============================================================
# EXTRACT LINKS
# ============================================================

async def extract_links(page):

    links = set()

    try:

        anchors = page.locator(
            "a[href]"
        )

        count = await anchors.count()

        for i in range(count):

            try:

                href = await anchors.nth(
                    i
                ).get_attribute(
                    "href"
                )

                if not href:

                    continue

                absolute = urljoin(
                    FLIPKART_BASE_URL,
                    href
                )

                absolute = clean_url(
                    absolute
                )

                if not absolute:

                    continue

                if should_ignore_url(
                    absolute
                ):

                    continue

                links.add(
                    absolute
                )

            except Exception:

                continue

    except Exception as error:

        print(
            "   ⚠️ Link extraction error:",
            error
        )

    return list(links)


# ============================================================
# SCROLL
# ============================================================

async def scroll_page(page):

    previous_height = 0

    stable_count = 0

    print(
        "   📜 Scrolling..."
    )

    for number in range(
        MAX_SCROLLS_PER_PAGE
    ):

        try:

            height = await page.evaluate(
                "() => document.body.scrollHeight"
            )

            await page.evaluate(
                """
                () => window.scrollTo(
                    0,
                    document.body.scrollHeight
                )
                """
            )

            await page.wait_for_timeout(
                int(
                    SCROLL_DELAY * 1000
                )
            )

            new_height = await page.evaluate(
                "() => document.body.scrollHeight"
            )

            print(
                f"      Scroll "
                f"{number + 1}/"
                f"{MAX_SCROLLS_PER_PAGE}"
            )

            if new_height == previous_height:

                stable_count += 1

            else:

                stable_count = 0

            previous_height = new_height

            if stable_count >= 3:

                break

        except Exception:

            break


# ============================================================
# COLLECT PRODUCTS
# ============================================================

async def collect_product_urls(
    page,
    source
):

    links = await extract_links(
        page
    )

    found = set()

    for url in links:

        if not is_product_url(url):
            continue

        # ========================================================
        # CATEGORY AGENT FILTER
        # ========================================================

        category = get_category(
            product_name="",
            url=url
        )

        if not is_allowed_product(
            product_name="",
            url=url
        ):
            continue

        found.add(url)

    STATS["products_found"] += len(
        found
    )

    new_products = []

    for url in found:

        if len(new_products) >= MAX_PRODUCTS_PER_SEARCH:
            break

        if url in DISCOVERED_PRODUCT_URLS:

            continue

        DISCOVERED_PRODUCT_URLS.add(
            url
        )

        new_products.append(
            url
        )

    STATS["new_products"] += len(
        new_products
    )

    print(
        f"\n   📦 Products found:"
        f" {len(found)}"
    )

    print(
        f"   🆕 New products:"
        f" {len(new_products)}"
    )

    if new_products:

        for url in new_products[:15]:

            print(
                f"      • {url}"
            )

        if len(new_products) > 15:

            print(
                f"      ... "
                f"{len(new_products) - 15} more"
            )

    #
    # IMPORTANT:
    #
    # Immediately pass new URLs to
    # Product Agent.
    #

    if new_products:

        await send_to_product_agent(
            new_products,
            source
        )

    return new_products


# ============================================================
# SEND TO PRODUCT AGENT
# ============================================================

async def send_to_product_agent(
    product_urls,
    source
):

    print("\n")

    print(
        "➡️ DISCOVERY → PRODUCT AGENT"
    )

    print(
        f"   Source: {source}"
    )

    print(
        f"   URLs received:"
        f" {len(product_urls)}"
    )

    #
    # Process in batches.
    #

    for start in range(
        0,
        len(product_urls),
        PRODUCT_BATCH_SIZE
    ):

        batch = product_urls[
            start:
            start + PRODUCT_BATCH_SIZE
        ]

        print("\n")

        print(
            f"🧠 Product batch "
            f"{start + 1}-"
            f"{start + len(batch)}"
        )

        try:

            results = await process_products(
                batch
            )

            successful = len(
                results
            )

            failed = (
                len(batch)
                - successful
            )

            STATS[
                "processed_products"
            ] += successful

            STATS[
                "failed_products"
            ] += failed

        except Exception as error:

            print(
                "\n❌ Product Agent error:"
            )

            print(error)

            STATS["errors"] += 1

            STATS[
                "failed_products"
            ] += len(batch)

        #
        # Small delay between batches.
        #

        if (
            start + PRODUCT_BATCH_SIZE
            < len(product_urls)
        ):

            await asyncio.sleep(
                PRODUCT_DELAY
            )


# ============================================================
# COLLECT CATEGORIES
# ============================================================

async def collect_navigation_links(
    page
):

    links = await extract_links(
        page
    )

    categories = set()

    listings = set()

    category_keywords = [
        "/mobiles",
        "/laptops",
        "/audio",
        "/earbuds",
        "/televisions",
        "/tv",
    ]

    for url in links:

        lower = url.lower()

        if is_product_url(url):

            continue

        if "/search" in lower:

            listings.add(url)

            continue

        if any(
            keyword in lower
            for keyword in category_keywords
        ):

            categories.add(url)

    new_categories = (
        categories
        - DISCOVERED_CATEGORY_URLS
    )

    new_listings = (
        listings
        - DISCOVERED_LISTING_URLS
    )

    DISCOVERED_CATEGORY_URLS.update(
        new_categories
    )

    DISCOVERED_LISTING_URLS.update(
        new_listings
    )

    STATS["categories_found"] = len(
        DISCOVERED_CATEGORY_URLS
    )

    return (
        new_categories,
        new_listings
    )


# ============================================================
# OPEN PAGE
# ============================================================

async def open_page(
    page,
    url
):

    try:

        print(
            "\n🌐 Opening:"
        )

        print(
            f"   {url}"
        )

        STATS["pages_opened"] += 1

        await page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=40000
        )

        await page.wait_for_timeout(
            2500
        )

        return True

    except PlaywrightTimeoutError:

        print(
            "   ⚠️ Page load timeout"
        )

        STATS["errors"] += 1

        return False

    except Exception as error:

        print(
            "   ❌ Page error:"
        )

        print(error)

        STATS["errors"] += 1

        return False


# ============================================================
# POPUP HANDLING
# ============================================================

async def close_popups(page):

    selectors = [

        "button:has-text('✕')",
        "button:has-text('Close')",
        "button:has-text('CLOSE')",
        "[aria-label='Close']",
        "[aria-label='close']",

    ]

    for selector in selectors:

        try:

            locator = page.locator(
                selector
            )

            count = await locator.count()

            for i in range(
                min(count, 3)
            ):

                try:

                    if await locator.nth(
                        i
                    ).is_visible():

                        await locator.nth(
                            i
                        ).click(
                            timeout=1000
                        )

                except Exception:

                    pass

        except Exception:

            pass


# ============================================================
# HOME PAGE
# ============================================================

async def discover_homepage(
    page
):

    print("\n")

    print("=" * 70)

    print(
        "🏠 HOME PAGE DISCOVERY"
    )

    print("=" * 70)

    if not await open_page(
        page,
        FLIPKART_BASE_URL
    ):

        return

    await close_popups(
        page
    )

    await collect_product_urls(
        page,
        "homepage"
    )

    await scroll_page(
        page
    )

    await collect_product_urls(
        page,
        "homepage-after-scroll"
    )

    categories, listings = (
        await collect_navigation_links(
            page
        )
    )

    print(
        f"\n   📂 New categories:"
        f" {len(categories)}"
    )

    print(
        f"   📋 New listings:"
        f" {len(listings)}"
    )


# ============================================================
# SEARCH
# ============================================================

async def discover_search(
    page,
    query
):

    print("\n")

    print("=" * 70)

    print(
        f"🔎 SEARCH: {query}"
    )

    print("=" * 70)

    search_url = (
        f"{FLIPKART_BASE_URL}/search"
        f"?q={quote(query)}"
    )

    if not await open_page(
        page,
        search_url
    ):

        return

    await close_popups(
        page
    )

    await collect_product_urls(
        page,
        f"search:{query}"
    )

    await scroll_page(
        page
    )

    await collect_product_urls(
        page,
        f"search:{query}-after-scroll"
    )


# ============================================================
# CATEGORY
# ============================================================

async def discover_category(
    page,
    url
):

    print("\n")

    print("=" * 70)

    print(
        "📂 CATEGORY"
    )

    print("=" * 70)

    if not await open_page(
        page,
        url
    ):

        return

    await close_popups(
        page
    )

    await collect_product_urls(
        page,
        "category"
    )

    await scroll_page(
        page
    )

    await collect_product_urls(
        page,
        "category-after-scroll"
    )


# ============================================================
# DISCOVERY ROUND
# ============================================================

async def discovery_round(
    page
):

    STATS["rounds"] += 1

    print("\n\n")

    print(
        "#" * 70
    )

    print(
        f"🤖 DISCOVERY ROUND "
        f"#{STATS['rounds']}"
    )

    print(
        "#" * 70
    )

    print(
        f"\n📦 Known products:"
        f" {len(DISCOVERED_PRODUCT_URLS)}"
    )

    # --------------------------------------------------------
    # HOME
    # --------------------------------------------------------

    # Homepage disabled.
    # We only discover Mobiles, Laptops, Earbuds and TVs.
    # await discover_homepage(page)

    # --------------------------------------------------------
    # SEARCHES (Round-robin across categories like Amazon approach)
    # --------------------------------------------------------

    from agents.category_agent import get_queries

    categories = ["mobiles", "tvs", "laptops", "earbuds"]
    queries_by_cat = {c: get_queries(c) for c in categories}
    max_len = max(len(q) for q in queries_by_cat.values()) if queries_by_cat else 0

    search_num = 1
    for i in range(max_len):
        for category in categories:
            if i < len(queries_by_cat[category]):
                query = queries_by_cat[category][i]

                print(
                    f"\n🔍 Search "
                    f"{search_num}:"
                    f" {query} ({category})"
                )

                await discover_search(
                    page,
                    query
                )

                await asyncio.sleep(
                    2
                )
                search_num += 1

    # --------------------------------------------------------
    # CATEGORIES
    # --------------------------------------------------------

    categories = list(
        DISCOVERED_CATEGORY_URLS
    )

    categories = categories[
        :MAX_CATEGORY_PAGES
    ]

    for number, url in enumerate(
        categories,
        start=1
    ):

        print(
            f"\n📂 Category "
            f"{number}/"
            f"{len(categories)}"
        )

        await discover_category(
            page,
            url
        )

        await asyncio.sleep(
            2
        )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    print("\n")

    print("=" * 70)

    print(
        "📊 DISCOVERY SUMMARY"
    )

    print("=" * 70)

    print(
        f"🔄 Rounds:"
        f" {STATS['rounds']}"
    )

    print(
        f"🌐 Pages opened:"
        f" {STATS['pages_opened']}"
    )

    print(
        f"📦 Unique products:"
        f" {len(DISCOVERED_PRODUCT_URLS)}"
    )

    print(
        f"🆕 New products:"
        f" {STATS['new_products']}"
    )

    print(
        f"🧠 Products processed:"
        f" {STATS['processed_products']}"
    )

    print(
        f"❌ Product failures:"
        f" {STATS['failed_products']}"
    )

    print(
        f"📂 Categories:"
        f" {len(DISCOVERED_CATEGORY_URLS)}"
    )

    print(
        f"⚠️ Errors:"
        f" {STATS['errors']}"
    )

    print("=" * 70)


# ============================================================
# MAIN AGENT
# ============================================================

async def discovery_agent():

    print("=" * 70)

    print(
        "🤖 FLIPKART DISCOVERY + PRODUCT PIPELINE"
    )

    print("=" * 70)

    print()

    print(
        "Discovery Agent"
        " → Product Agent"
        " → Website"
    )

    print()

    async with async_playwright() as playwright:

        browser = await playwright.chromium.launch(

            headless=HEADLESS,

            args=[

                "--disable-blink-features=AutomationControlled",

                "--disable-dev-shm-usage",

                "--no-sandbox",

            ]

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

            while True:

                try:

                    await discovery_round(
                        page
                    )

                except Exception as error:

                    print(
                        "\n❌ Discovery error:"
                    )

                    print(error)

                    STATS["errors"] += 1

                print("\n")

                print(
                    "🔄 Discovery cycle complete."
                )

                print(
                    f"⏳ Next cycle in "
                    f"{DISCOVERY_INTERVAL}"
                    f" seconds."
                )

                await asyncio.sleep(
                    DISCOVERY_INTERVAL
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
            discovery_agent()
        )

    except KeyboardInterrupt:

        print(
            "\n🛑 Discovery Agent stopped."
        )