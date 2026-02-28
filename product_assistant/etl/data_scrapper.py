import csv
import time
import re
import os
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class FlipkartScraper:

    def __init__(self, output_dir="data"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def _make_driver(self):
        for attempt in range(3):
            try:
                time.sleep(2)
                options = uc.ChromeOptions()
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--disable-blink-features=AutomationControlled")
                options.add_argument("--window-size=1920,1080")
                options.add_argument("--disable-extensions")
                options.add_argument("--disable-gpu")
                driver = uc.Chrome(options=options, use_subprocess=True, version_main=145)
                time.sleep(1)
                return driver
            except Exception as e:
                print(f"⚠️ Driver launch attempt {attempt + 1} failed: {e}")
                time.sleep(3)
        raise RuntimeError("❌ Failed to launch Chrome after 3 attempts.")

    def _safe_get(self, driver, url, retries=2):
        for attempt in range(retries):
            try:
                driver.get(url)
                return True
            except Exception as e:
                print(f"⚠️ Navigation attempt {attempt + 1} failed: {e}")
                time.sleep(2)
        return False

    def _extract_price(self, card):
        for sel in ["div.Nx9bqj", "div._30jeq3", "div._1_WHN1", "div.hl05eU"]:
            tag = card.select_one(sel)
            if tag:
                match = re.search(r"₹[\d,]+", tag.get_text(strip=True))
                if match:
                    return match.group(0)
        for tag in card.find_all(True):
            match = re.search(r"₹[\d,]+", tag.get_text(strip=True))
            if match:
                return match.group(0)
        return "N/A"

    def _extract_rating(self, card):
        for sel in ["div.XQDdHH", "div._3LWZlK", "div.UkUFwK span", "span._2_R_DZ"]:
            tag = card.select_one(sel)
            if tag:
                text = tag.get_text(strip=True)
                if re.match(r"^\d\.\d$", text):
                    return text
        for tag in card.find_all(True):
            text = tag.get_text(strip=True)
            if re.match(r"^\d\.\d$", text):
                return text
        return "N/A"

    def _to_reviews_url(self, product_url):
        """Convert product page URL to reviews page URL."""
        return re.sub(r"/p/(itm[0-9A-Za-z]+)", r"/product-reviews/\1", product_url)

    # ------------------------------------------------------------------ #
    # REVIEWS
    # ------------------------------------------------------------------ #

    def _get_reviews_with_driver(self, driver, product_url, count=2):
        try:
            reviews_url = self._to_reviews_url(product_url)
            ok = self._safe_get(driver, reviews_url)
            if not ok:
                return ""

            time.sleep(5)

            try:
                driver.find_element(By.XPATH, "//button[contains(text(),'✕')]").click()
                time.sleep(1)
            except Exception:
                pass

            for _ in range(3):
                ActionChains(driver).send_keys(Keys.END).perform()
                time.sleep(1.5)

            soup = BeautifulSoup(driver.page_source, "html.parser")

            SKIP = ["warranty", "flipkart internet", "bengaluru", "face id",
                    "barometer", "hevc", "aac lc", "handset", "sar limit",
                    "contrast ratio", "true tone", "lightning connector"]

            reviews = []
            seen = set()

            # Strategy 1: known selectors
            for sel in ["div.ZmyHeo", "div.t-ZTKy", "div._27M-vq",
                        "div.col.EPCmJX", "div._6K-7Co", "div.row.gHabs0"]:
                for block in soup.select(sel):
                    text = block.get_text(separator=" ", strip=True)
                    if (text and text not in seen and 30 < len(text) < 600
                            and not any(k in text.lower() for k in SKIP)):
                        reviews.append(text)
                        seen.add(text)
                    if len(reviews) >= count:
                        break
                if len(reviews) >= count:
                    break

            # Strategy 2: scan all leaf divs as fallback
            if not reviews:
                for tag in soup.find_all("div"):
                    if tag.find("div"):
                        continue
                    text = tag.get_text(separator=" ", strip=True)
                    if (text and text not in seen and 40 < len(text) < 500
                            and not any(k in text.lower() for k in SKIP)):
                        reviews.append(text)
                        seen.add(text)
                    if len(reviews) >= count:
                        break

            print(f"    📝 Reviews fetched: {len(reviews)}")
            return " || ".join(reviews) if reviews else ""

        except Exception as e:
            print(f"    ❌ Review fetch error: {e}")
            return ""

    # ------------------------------------------------------------------ #
    # PRODUCTS
    # ------------------------------------------------------------------ #

    def scrape_flipkart_products(self, query, max_products=3, review_count=2):
        driver = None
        try:
            driver = self._make_driver()
            search_url = "https://www.flipkart.com/search?q=" + query.replace(" ", "+")

            ok = self._safe_get(driver, search_url)
            if not ok:
                print("❌ Could not load Flipkart search page.")
                return []

            try:
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-id]"))
                )
            except Exception:
                print("⚠️ Timed out waiting for products to load.")
                return []

            time.sleep(3)

            try:
                driver.find_element(By.XPATH, "//button[contains(text(),'✕')]").click()
                time.sleep(1)
            except Exception:
                pass

            soup = BeautifulSoup(driver.page_source, "html.parser")
            cards = soup.select("div[data-id]")[:max_products]
            print(f"=== FOUND {len(cards)} product cards ===")

            product_info = []
            for card in cards:
                try:
                    img = card.select_one("img.UCc1lI, img[alt]")
                    title = img["alt"].strip() if img and img.get("alt") else "Unknown Title"

                    link_tag = card.select_one("a[href*='/p/']")
                    if not link_tag:
                        continue
                    href = link_tag.get("href", "")
                    product_link = (
                        href if href.startswith("http")
                        else "https://www.flipkart.com" + href
                    )
                    match = re.findall(r"/p/(itm[0-9A-Za-z]+)", href)
                    product_id = match[0] if match else "N/A"

                    price = self._extract_price(card)
                    rating = self._extract_rating(card)

                    reviews_tag = card.select_one("span.Wphh3N, span._2_R_DZ, span._13vcmD")
                    total_reviews = "N/A"
                    if reviews_tag:
                        m = re.search(r"\d+(,\d+)?", reviews_tag.get_text(strip=True))
                        total_reviews = m.group(0) if m else "N/A"

                    print(f"  ✅ {title} | {price} | ⭐{rating} | {product_id}")
                    product_info.append((product_id, title, rating, total_reviews, price, product_link))

                except Exception as e:
                    print(f"  ❌ Card error: {e}")
                    continue

            products = []
            for product_id, title, rating, total_reviews, price, product_link in product_info:
                print(f"  🔍 Getting reviews: {title}")
                top_reviews = self._get_reviews_with_driver(driver, product_link, count=review_count)
                products.append([product_id, title, rating, total_reviews, price, top_reviews])

            return products

        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass

    # ------------------------------------------------------------------ #
    # CSV
    # ------------------------------------------------------------------ #

    def save_to_csv(self, data, filename="product_reviews.csv"):
        if os.path.isabs(filename) or os.path.dirname(filename):
            path = filename
            os.makedirs(os.path.dirname(path), exist_ok=True)
        else:
            path = os.path.join(self.output_dir, filename)

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["product_id", "product_title", "rating", "total_reviews", "price", "top_reviews"])
            writer.writerows(data)

        print(f"Saved CSV at -> {path}")
