from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from urllib.parse import urlparse
from datetime import datetime


HOST = "127.0.0.1"
PORT = 8000


# ============================================================
# PRODUCT DATABASE
# ============================================================

PRODUCTS = {}


# Demo products so the website has data immediately.
# Your Flipkart agent can later send real products here.

DEMO_PRODUCTS = [
    {
        "product_name": "Apple iPhone 15",
        "url": "https://www.flipkart.com/apple-iphone-15-black-128-gb/p/itm6ac6485515ae4",
        "image": "https://rukminim2.flixcart.com/image/416/416/xif0q/mobile/0/0/x/-original-imah4ehx6d3qz4zq.jpeg",
        "price": 57900,
        "mrp": 69900,
        "discount": "17% off",
        "rating": 4.6,
        "rating_count": 9739,
        "brand": "APPLE",
        "color": "Black",
        "ram": "8 GB",
        "storage": "128 GB",
        "seller": "TrueComRetail",
        "highlights": [
            "8 GB RAM",
            "128 GB ROM",
            "6.1 inch Super Retina XDR Display",
            "48MP + 12MP Dual Rear Camera",
            "12MP Front Camera",
            "A16 Bionic Chip"
        ],
        "offers": [
            "Bank Offer available",
            "No Cost EMI available",
            "Exchange offer available"
        ],
        "source": "Flipkart",
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    },
    {
        "product_name": "Apple iPhone 15 Plus",
        "url": "https://example.com/iphone-15-plus",
        "image": "https://rukminim2.flixcart.com/image/416/416/xif0q/mobile/0/0/x/-original-imah4ehx6d3qz4zq.jpeg",
        "price": 67900,
        "mrp": 79900,
        "discount": "15% off",
        "rating": 4.5,
        "rating_count": 5321,
        "brand": "APPLE",
        "color": "Blue",
        "ram": "8 GB",
        "storage": "128 GB",
        "seller": "RetailNet",
        "highlights": [
            "8 GB RAM",
            "128 GB ROM",
            "6.7 inch Super Retina XDR Display",
            "48MP + 12MP Dual Rear Camera",
            "A16 Bionic Chip"
        ],
        "offers": [
            "Bank Offer available",
            "Exchange offer available"
        ],
        "source": "Flipkart",
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    },
    {
        "product_name": "Samsung Galaxy S24",
        "url": "https://example.com/samsung-galaxy-s24",
        "image": "https://rukminim2.flixcart.com/image/416/416/xif0q/mobile/6/8/1/-original-imahyv5k7xg8z7zq.jpeg",
        "price": 64999,
        "mrp": 79999,
        "discount": "18% off",
        "rating": 4.7,
        "rating_count": 8234,
        "brand": "SAMSUNG",
        "color": "Black",
        "ram": "8 GB",
        "storage": "128 GB",
        "seller": "SuperComNet",
        "highlights": [
            "8 GB RAM",
            "128 GB Storage",
            "6.2 inch Dynamic AMOLED Display",
            "50MP Triple Camera",
            "Snapdragon Processor",
            "5G Connectivity"
        ],
        "offers": [
            "Bank Offer available",
            "No Cost EMI available",
            "Exchange offer available"
        ],
        "source": "Flipkart",
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    },
    {
        "product_name": "OnePlus 12",
        "url": "https://example.com/oneplus-12",
        "image": "https://rukminim2.flixcart.com/image/416/416/xif0q/mobile/oneplus-original-imagwdy4zq5h8h8g.jpeg",
        "price": 59999,
        "mrp": 69999,
        "discount": "14% off",
        "rating": 4.6,
        "rating_count": 6127,
        "brand": "ONEPLUS",
        "color": "Black",
        "ram": "12 GB",
        "storage": "256 GB",
        "seller": "Flashstar Commerce",
        "highlights": [
            "12 GB RAM",
            "256 GB Storage",
            "6.82 inch AMOLED Display",
            "50MP Triple Camera",
            "Snapdragon 8 Gen 3",
            "5G Connectivity"
        ],
        "offers": [
            "Bank Offer available",
            "No Cost EMI available"
        ],
        "source": "Flipkart",
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
]


for product in DEMO_PRODUCTS:
    PRODUCTS[product["url"]] = product


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def clean_product(product):
    """
    Make sure the product has only the fields
    that we want to display/store.
    """

    allowed_fields = [
        "product_name",
        "url",
        "image",
        "price",
        "mrp",
        "discount",
        "rating",
        "rating_count",
        "brand",
        "color",
        "ram",
        "storage",
        "seller",
        "highlights",
        "offers",
        "source",
        "last_updated"
    ]

    cleaned = {
        key: product.get(key, "")
        for key in allowed_fields
    }

    if not cleaned.get("url") and product.get("product_url"):
        cleaned["url"] = product.get("product_url")

    return cleaned


def add_or_update_product(product):
    """
    Add a new product or update an existing product.
    URL is used as the unique product ID.
    """

    if not isinstance(product, dict):
        return False

    url = product.get("url") or product.get("product_url")

    if not url:
        return False

    product["url"] = url
    product = clean_product(product)

    product["last_updated"] = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    PRODUCTS[url] = product

    return True


def money(value):
    """
    Format price as Indian Rupees.
    """

    if value == "" or value is None:
        return "Price unavailable"

    try:
        return "₹" + f"{float(value):,.0f}"
    except:
        return str(value)


# ============================================================
# HTML
# ============================================================

HTML = r"""
<!DOCTYPE html>
<html lang="en">

<head>

<meta charset="UTF-8">

<meta name="viewport"
      content="width=device-width, initial-scale=1.0">

<title>Phone Finder</title>

<style>

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    font-family: Arial, Helvetica, sans-serif;
    background: #f5f7fb;
    color: #222;
}

.header {
    background: #2874f0;
    color: white;
    padding: 18px 20px;
    position: sticky;
    top: 0;
    z-index: 10;
}

.header-content {
    max-width: 1200px;
    margin: auto;
}

.logo {
    font-size: 25px;
    font-weight: bold;
    margin-bottom: 14px;
}

.search-box {
    display: flex;
    gap: 10px;
}

.search-box input {
    flex: 1;
    padding: 14px 16px;
    border: none;
    border-radius: 5px;
    font-size: 16px;
    outline: none;
}

.search-box button {
    padding: 14px 22px;
    border: none;
    border-radius: 5px;
    background: white;
    color: #2874f0;
    font-weight: bold;
    cursor: pointer;
}

.container {
    max-width: 1200px;
    margin: 25px auto;
    padding: 0 15px;
}

.top-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
}

.title {
    font-size: 23px;
    font-weight: bold;
}

.count {
    color: #666;
}

.products {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
    gap: 20px;
}

.card {
    background: white;
    border-radius: 10px;
    padding: 18px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.08);
    transition: 0.2s;
}

.card:hover {
    transform: translateY(-3px);
    box-shadow: 0 5px 18px rgba(0,0,0,0.12);
}

.product-image {
    width: 100%;
    height: 240px;
    object-fit: contain;
    margin-bottom: 12px;
}

.product-name {
    font-size: 18px;
    font-weight: bold;
    margin-bottom: 10px;
}

.price {
    font-size: 22px;
    font-weight: bold;
    margin-bottom: 5px;
}

.mrp {
    color: #777;
    text-decoration: line-through;
    margin-right: 8px;
}

.discount {
    color: #008000;
    font-weight: bold;
}

.rating {
    margin: 10px 0;
}

.rating-badge {
    background: #168a35;
    color: white;
    padding: 4px 7px;
    border-radius: 4px;
    font-weight: bold;
}

.details-button {
    width: 100%;
    padding: 12px;
    margin-top: 12px;
    border: none;
    border-radius: 5px;
    background: #2874f0;
    color: white;
    font-weight: bold;
    cursor: pointer;
}

.details-button:hover {
    background: #125bd1;
}

.source {
    color: #777;
    font-size: 13px;
    margin-top: 10px;
}

.empty {
    background: white;
    padding: 50px;
    text-align: center;
    border-radius: 10px;
    color: #777;
}

#detailsPage {
    display: none;
}

.back-button {
    border: none;
    background: white;
    padding: 10px 16px;
    border-radius: 5px;
    cursor: pointer;
    margin-bottom: 20px;
    font-weight: bold;
}

.details {
    background: white;
    border-radius: 10px;
    padding: 25px;
}

.details-top {
    display: grid;
    grid-template-columns: 40% 60%;
    gap: 30px;
}

.details-image {
    width: 100%;
    height: 450px;
    object-fit: contain;
}

.details-name {
    font-size: 28px;
    font-weight: bold;
    margin-bottom: 15px;
}

.details-price {
    font-size: 30px;
    font-weight: bold;
    margin: 15px 0;
}

.info-table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 20px;
}

.info-table td {
    padding: 12px;
    border-bottom: 1px solid #eee;
}

.info-label {
    width: 35%;
    color: #666;
}

.section {
    margin-top: 30px;
}

.section h2 {
    font-size: 22px;
    border-bottom: 1px solid #ddd;
    padding-bottom: 10px;
}

.highlight-list,
.offer-list {
    padding-left: 20px;
}

.highlight-list li,
.offer-list li {
    margin: 10px 0;
}

.buy-button {
    display: inline-block;
    margin-top: 20px;
    padding: 14px 25px;
    background: #ff9f00;
    color: white;
    text-decoration: none;
    border-radius: 5px;
    font-weight: bold;
}

.updated {
    color: #777;
    font-size: 13px;
    margin-top: 20px;
}

@media (max-width: 700px) {

    .search-box {
        flex-direction: column;
    }

    .search-box button {
        width: 100%;
    }

    .products {
        grid-template-columns: 1fr;
    }

    .details-top {
        grid-template-columns: 1fr;
    }

    .details-image {
        height: 300px;
    }

    .details-name {
        font-size: 23px;
    }

}

</style>

</head>


<body>


<!-- ======================================================
     HEADER
====================================================== -->

<div class="header">

    <div class="header-content">

        <div class="logo">
            🤖 Phone Finder
        </div>

        <div class="search-box">

            <input
                id="searchInput"
                type="text"
                placeholder="Search iPhone, Samsung, OnePlus, 128 GB..."
                oninput="searchProducts()"
            >

            <button onclick="clearSearch()">
                CLEAR
            </button>

        </div>

    </div>

</div>


<!-- ======================================================
     PRODUCT LIST PAGE
====================================================== -->

<div id="homePage">

    <div class="container">

        <div class="top-bar">

            <div class="title">
                Available Products
            </div>

            <div class="count" id="productCount">
                Loading...
            </div>

        </div>

        <div id="products"
             class="products">

        </div>

    </div>

</div>


<!-- ======================================================
     DETAILS PAGE
====================================================== -->

<div id="detailsPage">

    <div class="container">

        <button
            class="back-button"
            onclick="showHome()">

            ← Back to Products

        </button>

        <div
            id="detailsContent"
            class="details">

        </div>

    </div>

</div>


<script>

let allProducts = [];


// ============================================================
// LOAD PRODUCTS
// ============================================================

async function loadProducts() {

    try {

        const response = await fetch("/api/products");

        allProducts = await response.json();

        searchProducts();

    } catch (error) {

        console.error(error);

        document.getElementById("products").innerHTML =
            `<div class="empty">
                Unable to load products.
             </div>`;

    }

}


// ============================================================
// SEARCH
// ============================================================

function searchProducts() {

    const search =
        document
        .getElementById("searchInput")
        .value
        .toLowerCase()
        .trim();


    if (!search) {

        displayProducts(allProducts);

        return;

    }


    const words = search
        .split(/\s+/)
        .filter(Boolean);


    const filtered =
        allProducts.filter(product => {

            const searchableText = [

                product.product_name,
                product.brand,
                product.color,
                product.ram,
                product.storage,
                product.seller,
                product.source,

                ...(product.highlights || []),

                ...(product.offers || [])

            ]
            .join(" ")
            .toLowerCase();


            return words.every(
                word => searchableText.includes(word)
            );

        });


    displayProducts(filtered);

}


// ============================================================
// DISPLAY PRODUCT CARDS
// ============================================================

function displayProducts(products) {

    const container =
        document.getElementById("products");

    document.getElementById("productCount")
        .innerText =
        products.length + " product(s)";


    if (products.length === 0) {

        container.innerHTML = `
            <div class="empty">
                <h2>No products found</h2>
                <p>Try searching for iPhone, Samsung, OnePlus or 128 GB.</p>
            </div>
        `;

        return;

    }


    container.innerHTML =
        products.map((product, index) => {

            const image =
                product.image ||
                "https://via.placeholder.com/300x300?text=No+Image";


            return `

                <div class="card">

                    <img
                        class="product-image"
                        src="${escapeHtml(image)}"
                        onerror="this.src='https://via.placeholder.com/300x300?text=No+Image'"
                    >

                    <div class="product-name">
                        ${escapeHtml(product.product_name)}
                    </div>

                    <div class="price">
                        ${formatPrice(product.price)}
                    </div>

                    <div>

                        ${
                            product.mrp
                            ?
                            `<span class="mrp">
                                ${formatPrice(product.mrp)}
                            </span>`
                            :
                            ""
                        }

                        ${
                            product.discount
                            ?
                            `<span class="discount">
                                ${escapeHtml(product.discount)}
                            </span>`
                            :
                            ""
                        }

                    </div>


                    <div class="rating">

                        ${
                            product.rating
                            ?
                            `<span class="rating-badge">
                                ⭐ ${escapeHtml(product.rating)}
                            </span>`
                            :
                            "Rating unavailable"
                        }

                        ${
                            product.rating_count
                            ?
                            ` (${escapeHtml(product.rating_count)})`
                            :
                            ""
                        }

                    </div>


                    <div class="source">

                        Source:
                        ${escapeHtml(product.source || "Flipkart")}

                    </div>


                    <button
                        class="details-button"
                        onclick="showDetails(${indexOfProduct(product)})">

                        VIEW COMPLETE DETAILS

                    </button>

                </div>

            `;

        })
        .join("");

}


// ============================================================
// FIND PRODUCT INDEX
// ============================================================

function indexOfProduct(product) {

    return allProducts.findIndex(
        p => p.url === product.url
    );

}


// ============================================================
// SHOW DETAILS
// ============================================================

function showDetails(index) {

    const product = allProducts[index];

    if (!product) {
        return;
    }


    document.getElementById("homePage")
        .style.display = "none";

    document.getElementById("detailsPage")
        .style.display = "block";


    const image =
        product.image ||
        "https://via.placeholder.com/500x500?text=No+Image";


    const highlights =
        product.highlights || [];


    const offers =
        product.offers || [];


    document.getElementById("detailsContent")
        .innerHTML = `

        <div class="details-top">

            <div>

                <img
                    class="details-image"
                    src="${escapeHtml(image)}"
                    onerror="this.src='https://via.placeholder.com/500x500?text=No+Image'"
                >

            </div>


            <div>

                <div class="details-name">

                    ${escapeHtml(product.product_name)}

                </div>


                <div class="rating">

                    ${
                        product.rating
                        ?
                        `<span class="rating-badge">
                            ⭐ ${escapeHtml(product.rating)}
                        </span>`
                        :
                        "Rating unavailable"
                    }

                    ${
                        product.rating_count
                        ?
                        ` (${escapeHtml(product.rating_count)} ratings)`
                        :
                        ""
                    }

                </div>


                <div class="details-price">

                    ${formatPrice(product.price)}

                </div>


                <div>

                    ${
                        product.mrp
                        ?
                        `<span class="mrp">
                            ${formatPrice(product.mrp)}
                        </span>`
                        :
                        ""
                    }

                    ${
                        product.discount
                        ?
                        `<span class="discount">
                            ${escapeHtml(product.discount)}
                        </span>`
                        :
                        ""
                    }

                </div>


                <table class="info-table">

                    <tr>
                        <td class="info-label">Brand</td>
                        <td>${escapeHtml(product.brand)}</td>
                    </tr>

                    <tr>
                        <td class="info-label">Color</td>
                        <td>${escapeHtml(product.color)}</td>
                    </tr>

                    <tr>
                        <td class="info-label">RAM</td>
                        <td>${escapeHtml(product.ram)}</td>
                    </tr>

                    <tr>
                        <td class="info-label">Storage</td>
                        <td>${escapeHtml(product.storage)}</td>
                    </tr>

                    <tr>
                        <td class="info-label">Seller</td>
                        <td>${escapeHtml(product.seller)}</td>
                    </tr>

                </table>


                ${
                    product.url
                    ?
                    `<a
                        class="buy-button"
                        href="${escapeHtml(product.url)}"
                        target="_blank">

                        BUY ON FLIPKART

                    </a>`
                    :
                    ""
                }


            </div>

        </div>


        <!-- PRODUCT HIGHLIGHTS -->

        <div class="section">

            <h2>
                Product Highlights
            </h2>

            ${
                highlights.length
                ?
                `<ul class="highlight-list">

                    ${
                        highlights
                        .map(
                            item =>
                            `<li>${escapeHtml(item)}</li>`
                        )
                        .join("")
                    }

                </ul>`
                :
                "<p>No highlights available.</p>"
            }

        </div>


        <!-- OFFERS -->

        <div class="section">

            <h2>
                Offers
            </h2>

            ${
                offers.length
                ?
                `<ul class="offer-list">

                    ${
                        offers
                        .map(
                            item =>
                            `<li>${escapeHtml(item)}</li>`
                        )
                        .join("")
                    }

                </ul>`
                :
                "<p>No offers available.</p>"
            }

        </div>


        <div class="updated">

            Last updated:
            ${escapeHtml(product.last_updated || "Unknown")}

        </div>

    `;

}


// ============================================================
// BACK TO HOME
// ============================================================

function showHome() {

    document.getElementById("detailsPage")
        .style.display = "none";

    document.getElementById("homePage")
        .style.display = "block";

}


// ============================================================
// CLEAR SEARCH
// ============================================================

function clearSearch() {

    document.getElementById("searchInput")
        .value = "";

    searchProducts();

}


// ============================================================
// FORMAT PRICE
// ============================================================

function formatPrice(value) {

    if (
        value === null ||
        value === undefined ||
        value === ""
    ) {

        return "Price unavailable";

    }


    const number =
        Number(value);


    if (isNaN(number)) {

        return escapeHtml(String(value));

    }


    return "₹" +
        number.toLocaleString("en-IN");

}


// ============================================================
// HTML ESCAPE
// ============================================================

function escapeHtml(value) {

    if (
        value === null ||
        value === undefined
    ) {

        return "";

    }


    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");

}


// ============================================================
// AUTO REFRESH
// ============================================================

setInterval(() => {

    loadProducts();

}, 5000);


// Initial load

loadProducts();

</script>


</body>

</html>
"""


# ============================================================
# SERVER
# ============================================================

class Handler(BaseHTTPRequestHandler):


    def send_json(self, data, status=200):

        response = json.dumps(
            data,
            ensure_ascii=False
        ).encode("utf-8")

        self.send_response(status)

        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8"
        )

        self.send_header(
            "Content-Length",
            str(len(response))
        )

        self.send_header(
            "Access-Control-Allow-Origin",
            "*"
        )

        self.end_headers()

        self.wfile.write(response)


    def do_GET(self):

        parsed = urlparse(self.path)
        path = parsed.path

        # Website
        if path == "/":

            response = HTML.encode("utf-8")

            self.send_response(200)

            self.send_header(
                "Content-Type",
                "text/html; charset=utf-8"
            )

            self.send_header(
                "Content-Length",
                str(len(response))
            )

            self.end_headers()

            self.wfile.write(response)

            return

        # Get all products
        if path == "/api/products":

            self.send_json(
                list(PRODUCTS.values())
            )

            return

        # Get one product
        if path == "/api/product":

            self.send_json(
                list(PRODUCTS.values())
            )

            return

        self.send_json(
            {
                "error": "Not found"
            },
            404
        )


    def do_POST(self):

        parsed = urlparse(self.path)
        path = parsed.path

        if path not in [
            "/api/product",
            "/api/products"
        ]:

            self.send_json(
                {
                    "error": "Not found"
                },
                404
            )

            return

        try:

            content_length = int(
                self.headers.get(
                    "Content-Length",
                    0
                )
            )

            body = self.rfile.read(content_length)

            product = json.loads(
                body.decode("utf-8")
            )

            success = add_or_update_product(product)

            if not success:

                self.send_json(
                    {
                        "success": False,
                        "error":
                            "Product must contain a URL"
                    },
                    400
                )

                return

            self.send_json(
                {
                    "success": True,
                    "message":
                        "Product added/updated successfully",
                    "product":
                        PRODUCTS[
                            product.get("url") or product.get("product_url")
                        ]
                }
            )

        except Exception as error:

            self.send_json(
                {
                    "success": False,
                    "error": str(error)
                },
                500
            )


    def log_message(
        self,
        format,
        *args
    ):

        print(
            "[SERVER]",
            format % args
        )


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("PHONE FINDER TEST WEBSITE")
    print("=" * 60)
    print()
    print(
        f"Website running at:"
        f" http://{HOST}:{PORT}"
    )
    print()
    print(
        f"Products available:"
        f" {len(PRODUCTS)}"
    )
    print()
    print("Search examples:")
    print("  iphone")
    print("  iphone 15")
    print("  samsung")
    print("  oneplus")
    print("  128 gb")
    print()
    print("Press CTRL+C to stop.")
    print("=" * 60)

    server = HTTPServer(
        (HOST, PORT),
        Handler
    )

    try:

        server.serve_forever()

    except KeyboardInterrupt:

        print("\nServer stopped.")

        server.server_close()