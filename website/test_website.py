import sys
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except AttributeError:
    pass
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from urllib.parse import urlparse
from datetime import datetime


HOST = "127.0.0.1"
PORT = 8000


# ============================================================
# LIVE PRODUCTS
# ============================================================

PRODUCTS = {}


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
# PRODUCT CLEANING
# ============================================================

def clean_product(product):
    allowed = [
        "source",
        "category",
        "url",
        "product_url",
        "product_name",
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
        "last_updated"
    ]

    cleaned = {}

    for field in allowed:
        cleaned[field] = product.get(field, "")

    if not isinstance(cleaned["highlights"], list):
        cleaned["highlights"] = []

    if not isinstance(cleaned["offers"], list):
        cleaned["offers"] = []

    return cleaned


def add_or_update_product(product):
    product = clean_product(product)

    category = str(product.get("category", "")).lower().strip()
    if category not in ALLOWED_CATEGORIES:
        print(f"[WEBSITE REJECTED] Unallowed category '{category}': {product.get('product_name')}")
        return False

    key = (
        product.get("url")
        or product.get("product_url")
        or product.get("product_name")
    )

    if not key:
        return False

    product["url"] = key

    PRODUCTS[key] = product

    return True


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

<title>Flipkart Live Clone</title>


<style>

* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}


body {

    font-family:
        Arial,
        Helvetica,
        sans-serif;

    background:
        #f1f3f6;

    color: #172337;

    min-height: 100vh;

}


/* ==========================================================
   3D BACKGROUND
   ========================================================== */

.scene {

    position: fixed;

    inset: 0;

    overflow: hidden;

    pointer-events: none;

    z-index: -1;

}


.orb {

    position: absolute;

    border-radius: 50%;

    filter: blur(2px);

    opacity: 0.25;

    animation:
        float 12s ease-in-out infinite;

}


.orb.one {

    width: 300px;

    height: 300px;

    background:
        radial-gradient(
            circle,
            #2874f0,
            transparent 70%
        );

    top: 120px;

    left: -100px;

}


.orb.two {

    width: 380px;

    height: 380px;

    background:
        radial-gradient(
            circle,
            #ff9f00,
            transparent 70%
        );

    right: -130px;

    top: 250px;

    animation-delay: 2s;

}


.orb.three {

    width: 250px;

    height: 250px;

    background:
        radial-gradient(
            circle,
            #00bfa5,
            transparent 70%
        );

    left: 45%;

    bottom: -100px;

    animation-delay: 4s;

}


.cube {

    position: absolute;

    width: 80px;

    height: 80px;

    border: 1px solid rgba(40,116,240,0.12);

    transform:
        rotateX(55deg)
        rotateZ(45deg);

    animation:
        cubeFloat 15s linear infinite;

}


.cube.c1 {

    left: 12%;

    top: 25%;

}


.cube.c2 {

    right: 15%;

    top: 18%;

    width: 120px;

    height: 120px;

    animation-delay: 3s;

}


.cube.c3 {

    left: 70%;

    bottom: 15%;

    width: 60px;

    height: 60px;

    animation-delay: 6s;

}


@keyframes float {

    0%, 100% {
        transform:
            translate3d(0,0,0)
            scale(1);
    }

    50% {
        transform:
            translate3d(40px,-30px,0)
            scale(1.08);
    }

}


@keyframes cubeFloat {

    0% {
        transform:
            translateY(0)
            rotateX(55deg)
            rotateZ(45deg);
    }

    50% {
        transform:
            translateY(-80px)
            rotateX(75deg)
            rotateZ(130deg);
    }

    100% {
        transform:
            translateY(0)
            rotateX(55deg)
            rotateZ(225deg);
    }

}


/* ==========================================================
   HEADER
   ========================================================== */

.header {

    background:
        linear-gradient(
            135deg,
            #2874f0,
            #1557c0
        );

    color: white;

    padding:
        12px 5%;

    display: flex;

    align-items: center;

    gap: 30px;

    position: sticky;

    top: 0;

    z-index: 100;

    box-shadow:
        0 3px 15px
        rgba(0,0,0,0.15);

}


.logo {

    font-size: 25px;

    font-weight: 800;

    letter-spacing: -1px;

    min-width: 140px;

}


.logo span {

    display: block;

    font-size: 11px;

    font-style: italic;

    color: #ffe500;

}


.search-box {

    flex: 1;

    max-width: 650px;

    position: relative;

}


.search-box input {

    width: 100%;

    height: 42px;

    border: none;

    outline: none;

    border-radius: 3px;

    padding:
        0 50px 0 18px;

    font-size: 15px;

}


.search-icon {

    position: absolute;

    right: 16px;

    top: 11px;

    color: #2874f0;

    font-size: 20px;

}


.live {

    display: flex;

    align-items: center;

    gap: 7px;

    font-size: 13px;

    white-space: nowrap;

}


.live-dot {

    width: 9px;

    height: 9px;

    border-radius: 50%;

    background: #00e676;

    box-shadow:
        0 0 10px #00e676;

}


/* ==========================================================
   CATEGORY BAR
   ========================================================== */

.categories {

    background: white;

    display: flex;

    justify-content: center;

    gap: 45px;

    padding: 17px 10px;

    box-shadow:
        0 2px 7px
        rgba(0,0,0,0.08);

    overflow-x: auto;

}


.category {

    font-weight: 600;

    font-size: 14px;

    white-space: nowrap;

    cursor: pointer;

    transition: 0.2s;

}


.category:hover {

    color: #2874f0;

    transform:
        translateY(-2px);

}


.category.active {

    color: #2874f0;

    border-bottom: 2px solid #2874f0;

    padding-bottom: 2px;

}


/* ==========================================================
   MAIN
   ========================================================== */

.container {

    width: 94%;

    max-width: 1500px;

    margin:
        25px auto;

}


.hero {

    background:
        linear-gradient(
            135deg,
            rgba(40,116,240,0.97),
            rgba(21,87,192,0.95)
        );

    border-radius: 12px;

    padding:
        35px 45px;

    color: white;

    display: flex;

    justify-content: space-between;

    align-items: center;

    margin-bottom: 25px;

    overflow: hidden;

    position: relative;

    box-shadow:
        0 12px 35px
        rgba(40,116,240,0.22);

}


.hero h1 {

    font-size: 32px;

    margin-bottom: 10px;

}


.hero p {

    opacity: 0.9;

    font-size: 15px;

}


.hero-3d {

    width: 170px;

    height: 120px;

    position: relative;

    perspective: 700px;

}


.phone {

    width: 75px;

    height: 130px;

    border-radius: 14px;

    background:
        linear-gradient(
            145deg,
            #1b1b1b,
            #555
        );

    border: 3px solid #111;

    position: absolute;

    right: 35px;

    top: -10px;

    transform:
        rotateY(-25deg)
        rotateX(8deg)
        rotateZ(8deg);

    box-shadow:
        0 25px 35px
        rgba(0,0,0,0.35);

    animation:
        phoneFloat 4s ease-in-out infinite;

}


.phone::after {

    content: "";

    position: absolute;

    inset: 5px;

    border-radius: 10px;

    background:
        linear-gradient(
            135deg,
            #2874f0,
            #7b2cff
        );

}


@keyframes phoneFloat {

    0%,100% {
        transform:
            translateY(0)
            rotateY(-25deg)
            rotateX(8deg)
            rotateZ(8deg);
    }

    50% {
        transform:
            translateY(-12px)
            rotateY(-10deg)
            rotateX(12deg)
            rotateZ(4deg);
    }

}


/* ==========================================================
   TOOLBAR
   ========================================================== */

.toolbar {

    background: white;

    padding:
        18px 20px;

    border-radius: 8px;

    display: flex;

    justify-content: space-between;

    align-items: center;

    margin-bottom: 15px;

    box-shadow:
        0 2px 8px
        rgba(0,0,0,0.06);

}


.toolbar-title {

    font-size: 20px;

    font-weight: 600;

}


.count {

    color: #777;

    font-size: 13px;

    margin-top: 4px;

}


/* ==========================================================
   PRODUCTS
   ========================================================== */

.products {

    display: grid;

    grid-template-columns:
        repeat(
            auto-fill,
            minmax(220px, 1fr)
        );

    gap: 16px;

}


.product-card {

    background: white;

    border-radius: 8px;

    overflow: hidden;

    cursor: pointer;

    transition:
        transform 0.25s,
        box-shadow 0.25s;

    box-shadow:
        0 2px 7px
        rgba(0,0,0,0.08);

}


.product-card:hover {

    transform:
        translateY(-7px);

    box-shadow:
        0 15px 35px
        rgba(0,0,0,0.15);

}


.product-image {

    height: 235px;

    display: flex;

    align-items: center;

    justify-content: center;

    background:
        linear-gradient(
            145deg,
            #f8f9fb,
            #edf1f7
        );

    position: relative;

}


.product-image img {

    max-width: 85%;

    max-height: 90%;

    object-fit: contain;

}


.placeholder-phone {

    width: 95px;

    height: 170px;

    border-radius: 17px;

    background:
        linear-gradient(
            145deg,
            #202020,
            #777
        );

    border:
        5px solid #111;

    transform:
        rotateY(-20deg)
        rotateZ(4deg);

    box-shadow:
        20px 20px 25px
        rgba(0,0,0,0.2);

}


.placeholder-phone::after {

    content: "";

    display: block;

    margin: 5px;

    height: 100%;

    border-radius: 10px;

    background:
        linear-gradient(
            145deg,
            #2874f0,
            #662cff
        );

}


.badge {

    position: absolute;

    top: 10px;

    left: 10px;

    background: #008c45;

    color: white;

    padding:
        5px 8px;

    border-radius: 3px;

    font-size: 11px;

    font-weight: bold;

}


.product-info {

    padding: 15px;

}


.product-name {

    font-size: 15px;

    font-weight: 600;

    line-height: 1.4;

    min-height: 43px;

}


.rating {

    margin-top: 9px;

    display: inline-flex;

    gap: 5px;

    background: #008c45;

    color: white;

    padding:
        4px 7px;

    border-radius: 4px;

    font-size: 12px;

}


.rating-count {

    color: #777;

    margin-left: 5px;

    font-size: 12px;

}


.price {

    margin-top: 12px;

    font-size: 20px;

    font-weight: 700;

}


.mrp {

    text-decoration: line-through;

    color: #777;

    margin-left: 7px;

    font-size: 13px;

    font-weight: normal;

}


.discount {

    color: #008c45;

    margin-left: 7px;

    font-size: 12px;

    font-weight: bold;

}


.meta {

    color: #666;

    font-size: 12px;

    margin-top: 8px;

}


.view-button {

    width: 100%;

    border: none;

    margin-top: 13px;

    padding: 10px;

    border-radius: 4px;

    background: #ff9f00;

    color: #111;

    font-weight: bold;

    cursor: pointer;

}


.view-button:hover {

    background: #ff8800;

}


/* ==========================================================
   DETAILS
   ========================================================== */

.details {

    background: white;

    border-radius: 10px;

    padding: 30px;

    box-shadow:
        0 4px 20px
        rgba(0,0,0,0.08);

}


.back-button {

    border: none;

    background: #2874f0;

    color: white;

    padding:
        10px 18px;

    border-radius: 4px;

    cursor: pointer;

    margin-bottom: 25px;

}


.detail-grid {

    display: grid;

    grid-template-columns:
        42% 58%;

    gap: 40px;

}


.detail-image {

    min-height: 500px;

    display: flex;

    align-items: center;

    justify-content: center;

    background:
        #f8f9fb;

    border-radius: 10px;

}


.detail-image img {

    max-width: 90%;

    max-height: 500px;

    object-fit: contain;

}


.detail-title {

    font-size: 28px;

    line-height: 1.3;

}


.detail-price {

    margin-top: 20px;

    font-size: 32px;

    font-weight: 700;

}


.detail-mrp {

    color: #777;

    text-decoration: line-through;

    margin-left: 10px;

    font-size: 16px;

}


.detail-discount {

    color: #008c45;

    margin-left: 10px;

    font-size: 15px;

    font-weight: bold;

}


.info-grid {

    display: grid;

    grid-template-columns:
        repeat(2, 1fr);

    margin-top: 25px;

    border-top:
        1px solid #eee;

    border-left:
        1px solid #eee;

}


.info-item {

    padding: 14px;

    border-right:
        1px solid #eee;

    border-bottom:
        1px solid #eee;

}


.info-label {

    color: #777;

    font-size: 12px;

}


.info-value {

    margin-top: 5px;

    font-weight: 600;

}


.section {

    margin-top: 28px;

}


.section h3 {

    font-size: 19px;

    margin-bottom: 13px;

}


.highlight {

    padding: 9px 0;

    font-size: 14px;

}


.highlight::before {

    content: "✓";

    color: #008c45;

    font-weight: bold;

    margin-right: 10px;

}


.offer {

    background:
        #f5fff8;

    border:
        1px solid #d8f1df;

    padding: 12px;

    margin-bottom: 8px;

    border-radius: 5px;

    font-size: 13px;

}


.buy-button {

    display: inline-block;

    margin-top: 25px;

    padding:
        15px 45px;

    background:
        #ff9f00;

    color: #111;

    text-decoration: none;

    border-radius: 5px;

    font-weight: bold;

}


.source {

    margin-top: 15px;

    color: #777;

    font-size: 12px;

}


.updated {

    margin-top: 8px;

    color: #999;

    font-size: 11px;

}


/* ==========================================================
   EMPTY
   ========================================================== */

.empty {

    background: white;

    padding: 70px 20px;

    text-align: center;

    border-radius: 8px;

}


.empty h2 {

    margin-bottom: 10px;

}


.empty p {

    color: #777;

}


/* ==========================================================
   FOOTER
   ========================================================== */

footer {

    margin-top: 50px;

    background: #172337;

    color: #aaa;

    padding:
        30px;

    text-align: center;

    font-size: 13px;

}


/* ==========================================================
   RESPONSIVE
   ========================================================== */

@media (max-width: 800px) {

    .header {

        flex-wrap: wrap;

        gap: 10px;

    }


    .logo {

        min-width: auto;

    }


    .search-box {

        order: 3;

        flex-basis: 100%;

    }


    .categories {

        justify-content: flex-start;

        gap: 25px;

    }


    .hero {

        padding: 25px;

    }


    .hero h1 {

        font-size: 24px;

    }


    .hero-3d {

        display: none;

    }


    .products {

        grid-template-columns:
            repeat(
                2,
                minmax(0, 1fr)
            );

        gap: 10px;

    }


    .product-image {

        height: 180px;

    }


    .detail-grid {

        grid-template-columns: 1fr;

    }


    .detail-image {

        min-height: 350px;

    }


    .details {

        padding: 18px;

    }


}


@media (max-width: 480px) {

    .products {

        grid-template-columns: 1fr;

    }


    .product-image {

        height: 250px;

    }


    .info-grid {

        grid-template-columns: 1fr;

    }

}

</style>

</head>


<body>


<!-- ========================================================
     3D BACKGROUND
     ======================================================== -->

<div class="scene">

    <div class="orb one"></div>

    <div class="orb two"></div>

    <div class="orb three"></div>

    <div class="cube c1"></div>

    <div class="cube c2"></div>

    <div class="cube c3"></div>

</div>


<!-- ========================================================
     HEADER
     ======================================================== -->

<header class="header">

    <div class="logo">

        Flipkart

        <span>Live Product Clone</span>

    </div>


    <div class="search-box">

        <input
            id="searchInput"
            type="text"
            placeholder="Search for products, brands and more"
            autocomplete="off"
        >

        <div class="search-icon">
            🔍
        </div>

    </div>


    <div class="live">

        <div class="live-dot"></div>

        LIVE

    </div>

</header>


<!-- ========================================================
     CATEGORIES
     ======================================================== -->

<nav class="categories">

    <div
        class="category active"
        data-category="all"
        onclick="setCategory('all')"
    >
        🏠 All
    </div>

    <div
        class="category"
        data-category="mobiles"
        onclick="setCategory('mobiles')"
    >
        📱 Mobiles
    </div>

    <div
        class="category"
        data-category="laptops"
        onclick="setCategory('laptops')"
    >
        💻 Laptops
    </div>

    <div
        class="category"
        data-category="earbuds"
        onclick="setCategory('earbuds')"
    >
        🎧 Earbuds
    </div>

    <div
        class="category"
        data-category="tvs"
        onclick="setCategory('tvs')"
    >
        📺 TVs
    </div>

</nav>


<!-- ========================================================
     MAIN
     ======================================================== -->

<main class="container">


    <section class="hero">

        <div>

            <h1>
                Discover Products
            </h1>

            <p>
                Live product information powered by
                your Flipkart monitoring agents.
            </p>

        </div>


        <div class="hero-3d">

            <div class="phone"></div>

        </div>

    </section>


    <section class="toolbar">

        <div>

            <div
                class="toolbar-title"
                id="resultTitle"
            >
                All Products
            </div>

            <div
                class="count"
                id="productCount"
            >
                Loading products...
            </div>

        </div>

    </section>


    <section
        class="products"
        id="products"
    >

    </section>


    <section
        class="details"
        id="details"
        style="display:none;"
    >

    </section>


</main>


<footer>

    Live Flipkart Clone •
    Continuously updated by agents

</footer>


<script>


let allProducts = [];
let products = [];
let currentFiltered = [];
let currentSearch = "";
let selectedCategory = "all";

function setCategory(category) {

    selectedCategory = category;

    document.querySelectorAll(".category").forEach(el => {
        el.classList.toggle("active", el.getAttribute("data-category") === category);
    });

    closeDetails();

    searchProducts();
}

function searchProducts() {

    const search =
        document
        .getElementById("searchInput")
        .value
        .toLowerCase()
        .trim();

    const filtered =
        allProducts.filter(product => {

            // =================================================
            // CATEGORY FILTER
            // =================================================

            if (
                selectedCategory !== "all" &&
                product.category !== selectedCategory
            ) {
                return false;
            }

            // =================================================
            // SEARCH FILTER
            // =================================================

            if (!search) {
                return true;
            }

            const searchableText = [

                product.product_name,

                product.brand,

                product.color,

                product.ram,

                product.storage,

                product.seller,

                product.source,

                product.category,

                ...(product.highlights || []),

                ...(product.offers || [])

            ]
            .join(" ")
            .toLowerCase();

            const words =
                search
                .split(/\s+/)
                .filter(Boolean);

            return words.every(
                word =>
                    searchableText.includes(word)
            );
        });

    displayProducts(filtered);
}

function displayProducts(filtered) {

    currentFiltered = filtered;

    const container =
        document.getElementById(
            "products"
        );

    const search =
        document
        .getElementById("searchInput")
        .value
        .trim();

    let titleText = "All Products";

    if (selectedCategory !== "all") {
        titleText =
            selectedCategory === "tvs" ? "TVs" :
            selectedCategory.charAt(0).toUpperCase() +
            selectedCategory.slice(1);
    }

    if (search) {
        titleText =
            `Results for "${search}"` +
            (selectedCategory !== "all" ? ` in ${titleText}` : "");
    }

    document.getElementById(
        "resultTitle"
    ).textContent = titleText;

    document.getElementById(
        "productCount"
    ).textContent =
        `${filtered.length} product(s) found`;

    if (!filtered.length) {

        container.innerHTML = `

            <div
                class="empty"
                style="grid-column:1/-1;"
            >

                <h2>
                    No products found
                </h2>

                <p>
                    Try another search or category.
                </p>

            </div>

        `;

        return;
    }

    container.innerHTML =
        filtered
            .map(
                (product, index) =>
                    createProductCard(
                        product,
                        index
                    )
            )
            .join("");
}

const renderProducts = searchProducts;


/* ==========================================================
   GET PRODUCTS
   ========================================================== */

async function loadProducts() {

    try {

        const response =
            await fetch("/api/products");

        products =
            await response.json();

        allProducts = products;

        searchProducts();

    } catch (error) {

        console.error(
            "Could not load products:",
            error
        );

        document.getElementById(
            "products"
        ).innerHTML = `

            <div class="empty">

                <h2>
                    Website API unavailable
                </h2>

                <p>
                    Start the Python website server.
                </p>

            </div>

        `;

    }

}


/* ==========================================================
   PRODUCT CARD
   ========================================================== */

function createProductCard(
    product,
    index
) {

    const image =
        product.image
            ? `
                <img
                    src="${escapeHtml(product.image)}"
                    alt="${escapeHtml(product.product_name)}"
                >
              `
            : `
                <div
                    class="placeholder-phone"
                ></div>
              `;


    return `

        <article
            class="product-card"
            onclick="showDetails(${index})"
        >

            <div class="product-image">

                ${image}

                ${
                    product.discount
                        ? `
                            <div class="badge">
                                ${escapeHtml(
                                    product.discount
                                )}
                            </div>
                          `
                        : ""
                }

            </div>


            <div class="product-info">

                <div class="product-name">

                    ${escapeHtml(
                        product.product_name ||
                        "Unknown Product"
                    )}

                </div>


                <div>

                    <span class="rating">

                        ⭐
                        ${escapeHtml(
                            product.rating || "-"
                        )}

                    </span>


                    <span class="rating-count">

                        ${
                            product.rating_count
                                ? escapeHtml(
                                    product.rating_count
                                ) + " Ratings"
                                : ""
                        }

                    </span>

                </div>


                <div class="price">

                    ${escapeHtml(
                        product.price || "Price unavailable"
                    )}

                    ${
                        product.mrp
                            ? `
                                <span class="mrp">
                                    ${escapeHtml(
                                        product.mrp
                                    )}
                                </span>
                              `
                            : ""
                    }


                    ${
                        product.discount
                            ? `
                                <span class="discount">
                                    ${escapeHtml(
                                        product.discount
                                    )}
                                </span>
                              `
                            : ""
                    }

                </div>


                <div class="meta">

                    ${
                        product.ram
                            ? escapeHtml(
                                product.ram
                            )
                            : ""
                    }

                    ${
                        product.storage
                            ? " • " +
                              escapeHtml(
                                product.storage
                              )
                            : ""
                    }

                    ${
                        product.color
                            ? " • " +
                              escapeHtml(
                                product.color
                              )
                            : ""
                    }

                </div>


                <button
                    class="view-button"
                    onclick="event.stopPropagation(); showDetails(${index})"
                >

                    VIEW COMPLETE DETAILS

                </button>

            </div>

        </article>

    `;

}


/* ==========================================================
   DETAILS
   ========================================================== */

function showDetails(index) {

    const product =
        currentFiltered[index] ||
        allProducts[index];

    if (!product) {
        return;
    }


    const details =
        document.getElementById(
            "details"
        );


    const image =
        product.image
            ? `
                <img
                    src="${escapeHtml(product.image)}"
                    alt="${escapeHtml(product.product_name)}"
                >
              `
            : `
                <div
                    class="placeholder-phone"
                    style="
                        width:150px;
                        height:270px;
                    "
                ></div>
              `;


    details.innerHTML = `

        <button
            class="back-button"
            onclick="closeDetails()"
        >
            ← BACK TO PRODUCTS
        </button>


        <div class="detail-grid">


            <div class="detail-image">

                ${image}

            </div>


            <div>

                <h1 class="detail-title">

                    ${escapeHtml(
                        product.product_name ||
                        "Unknown Product"
                    )}

                </h1>


                <div>

                    <span class="rating">

                        ⭐
                        ${escapeHtml(
                            product.rating || "-"
                        )}

                    </span>


                    <span class="rating-count">

                        ${
                            product.rating_count
                                ? escapeHtml(
                                    product.rating_count
                                ) +
                                " Ratings & Reviews"
                                : ""
                        }

                    </span>

                </div>


                <div class="detail-price">

                    ${escapeHtml(
                        product.price || "Price unavailable"
                    )}

                    ${
                        product.mrp
                            ? `
                                <span class="detail-mrp">
                                    ${escapeHtml(
                                        product.mrp
                                    )}
                                </span>
                              `
                            : ""
                    }

                    ${
                        product.discount
                            ? `
                                <span class="detail-discount">
                                    ${escapeHtml(
                                        product.discount
                                    )}
                                </span>
                              `
                            : ""
                    }

                </div>


                <div class="info-grid">

                    ${infoItem(
                        "Brand",
                        product.brand
                    )}

                    ${infoItem(
                        "Color",
                        product.color
                    )}

                    ${infoItem(
                        "RAM",
                        product.ram
                    )}

                    ${infoItem(
                        "Storage",
                        product.storage
                    )}

                    ${infoItem(
                        "Seller",
                        product.seller
                    )}

                    ${infoItem(
                        "Source",
                        product.source
                    )}

                </div>


                ${
                    product.highlights &&
                    product.highlights.length
                        ? `

                            <div class="section">

                                <h3>
                                    Product Highlights
                                </h3>

                                ${product.highlights
                                    .map(
                                        item =>
                                            `
                                                <div
                                                    class="highlight"
                                                >
                                                    ${escapeHtml(
                                                        item
                                                    )}
                                                </div>
                                            `
                                    )
                                    .join("")}

                            </div>

                          `
                        : ""
                }


                ${
                    product.offers &&
                    product.offers.length
                        ? `

                            <div class="section">

                                <h3>
                                    Available Offers
                                </h3>

                                ${product.offers
                                    .map(
                                        item =>
                                            `
                                                <div
                                                    class="offer"
                                                >
                                                    🎁
                                                    ${escapeHtml(
                                                        item
                                                    )}
                                                </div>
                                            `
                                    )
                                    .join("")}

                            </div>

                          `
                        : ""
                }


                ${
                    product.product_url &&
                    product.product_url.startsWith(
                        "http"
                    )
                        ? `
                            <a
                                class="buy-button"
                                href="${escapeHtml(
                                    product.product_url
                                )}"
                                target="_blank"
                                rel="noopener"
                            >
                                BUY ON FLIPKART
                            </a>
                          `
                        : ""
                }


                <div class="source">

                    Source:
                    ${escapeHtml(
                        product.source ||
                        "Flipkart"
                    )}

                </div>


                <div class="updated">

                    Last updated:
                    ${formatDate(
                        product.last_updated
                    )}

                </div>


            </div>

        </div>

    `;


    document.getElementById(
        "products"
    ).style.display = "none";


    document.querySelector(
        ".toolbar"
    ).style.display = "none";


    details.style.display =
        "block";


    window.scrollTo({
        top: 0,
        behavior: "smooth"
    });

}


/* ==========================================================
   CLOSE DETAILS
   ========================================================== */

function closeDetails() {

    document.getElementById(
        "details"
    ).style.display = "none";


    document.getElementById(
        "products"
    ).style.display = "grid";


    document.querySelector(
        ".toolbar"
    ).style.display = "flex";

}


/* ==========================================================
   CATEGORY SEARCH
   ========================================================== */

function categorySearch(value) {

    currentSearch = value;

    document.getElementById(
        "searchInput"
    ).value = value;

    closeDetails();

    renderProducts();

}


/* ==========================================================
   INFO ITEM
   ========================================================== */

function infoItem(
    label,
    value
) {

    if (!value) {
        return "";
    }


    return `

        <div class="info-item">

            <div class="info-label">

                ${escapeHtml(label)}

            </div>

            <div class="info-value">

                ${escapeHtml(value)}

            </div>

        </div>

    `;

}


/* ==========================================================
   ESCAPE HTML
   ========================================================== */

function escapeHtml(value) {

    if (value === null ||
        value === undefined) {

        return "";

    }


    return String(value)

        .replace(
            /&/g,
            "&amp;"
        )

        .replace(
            /</g,
            "&lt;"
        )

        .replace(
            />/g,
            "&gt;"
        )

        .replace(
            /"/g,
            "&quot;"
        )

        .replace(
            /'/g,
            "&#039;"
        );

}


/* ==========================================================
   DATE
   ========================================================== */

function formatDate(value) {

    if (!value) {
        return "Unknown";
    }


    try {

        return new Date(value)
            .toLocaleString();

    } catch {

        return value;

    }

}


/* ==========================================================
   SEARCH INPUT
   ========================================================== */

document.getElementById(
    "searchInput"
).addEventListener(
    "input",
    function () {

        currentSearch =
            this.value;

        closeDetails();

        renderProducts();

    }
);


/* ==========================================================
   LIVE REFRESH
   ========================================================== */

loadProducts();


setInterval(
    loadProducts,
    5000
);

</script>


</body>

</html>
"""


# ============================================================
# HTTP SERVER
# ============================================================

class RequestHandler(BaseHTTPRequestHandler):

    def send_json(self, data, status=200):

        payload = json.dumps(
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
            str(len(payload))
        )

        self.send_header(
            "Access-Control-Allow-Origin",
            "*"
        )

        self.end_headers()

        self.wfile.write(payload)

    def do_GET(self):

        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/":

            content = HTML.encode("utf-8")

            self.send_response(200)

            self.send_header(
                "Content-Type",
                "text/html; charset=utf-8"
            )

            self.send_header(
                "Content-Length",
                str(len(content))
            )

            self.end_headers()

            self.wfile.write(content)

            return

        if path == "/api/products":

            self.send_json(
                list(PRODUCTS.values())
            )

            return

        if path == "/api/product":

            self.send_json(
                list(PRODUCTS.values())
            )

            return

        if path == "/api/health":

            self.send_json({
                "status": "ok",
                "products": len(PRODUCTS),
                "live": True
            })

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

            raw = self.rfile.read(
                content_length
            )

            product = json.loads(
                raw.decode("utf-8")
            )

            if not isinstance(product, dict):

                raise ValueError(
                    "Product must be an object"
                )

            success = add_or_update_product(
                product
            )

            if not success:

                self.send_json(
                    {
                        "success": False,
                        "error": "Product has no URL"
                    },
                    400
                )

                return

            self.send_json(
                {
                    "success": True,
                    "message": "Product added/updated",
                    "products": len(PRODUCTS)
                }
            )

        except Exception as error:

            self.send_json(
                {
                    "success": False,
                    "error": str(error)
                },
                400
            )

    def do_OPTIONS(self):

        self.send_response(200)

        self.send_header(
            "Access-Control-Allow-Origin",
            "*"
        )

        self.send_header(
            "Access-Control-Allow-Methods",
            "GET, POST, OPTIONS"
        )

        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type"
        )

        self.end_headers()

    def log_message(self, format, *args):

        print(
            f"[WEBSITE] {format % args}"
        )


def start_server():

    server = HTTPServer(
        (HOST, PORT),
        RequestHandler
    )

    print("=" * 70)
    print("🛒 FLIPKART LIVE CLONE")
    print("=" * 70)

    print()

    print(
        f"🌐 Website: http://{HOST}:{PORT}"
    )

    print(
        f"📦 Products loaded: {len(PRODUCTS)}"
    )

    print(
        "🔄 Live API: /api/products"
    )

    print(
        "📡 Product API: /api/product"
    )

    print()

    print(
        "🤖 Waiting for agents..."
    )

    print(
        "Press CTRL+C to stop."
    )

    print("=" * 70)

    try:

        server.serve_forever()

    except KeyboardInterrupt:

        print(
            "\n🛑 Website stopped."
        )

    finally:

        server.server_close()


if __name__ == "__main__":

    start_server()