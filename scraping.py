import time
from datetime import datetime, timezone
from seleniumwire import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import requests
import os
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

# Use proxy to avoid blocking issues
USE_PROXY = True
PROXY = "http://brd-customer-hl_ccb2cea0-zone-candidate_laura:8h8qgf2r4tvu@brd.superproxy.io:33335"


def get_driver():
    """
    Function to create a new Chrome WebDriver instance with the necessary options and settings.
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--no-sandbox")  # Improve performance in cloud
    chrome_options.add_argument("--disable-dev-shm-usage")  # Reduce memory usage
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36")
    chrome_options.add_argument("accept-language=en-US,en;q=0.9,es;q=0.8")
    
    # Proxy settings for SeleniumWire
    if USE_PROXY:
        proxy_options = {
            'proxy': {
                'http': PROXY,
                'https': PROXY,
                'no_proxy': 'localhost,127.0.0.1'
            }
        }
        driver = webdriver.Chrome(seleniumwire_options=proxy_options, options=chrome_options)
    else:
        driver = webdriver.Chrome(options=chrome_options)
    
    return driver

def get_product_json(product_id):
    """
    Function to get the JSON data for a specific product ID from the Surtiapp API

    Args:
    - product_id: str, the unique identifier for the product
    """

    # Get the url for the product JSON data using the product ID
    url = f"https://www.surtiapp.com.co/api/ProductDetail/SelectedProduct/{product_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
        "Referer": f"https://www.surtiapp.com.co/WithoutLoginB2B/Store/ProductDetail/{product_id}",
        "sec-ch-ua": '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin"
    }

    try:
        # Proxy settings for requests
        proxies = {"http": PROXY, "https": PROXY} if USE_PROXY else None
        response = requests.get(url, headers=headers, proxies=proxies, timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"ERROR: Received status code {response.status_code} for product {product_id}")

    except Exception as e:
        print(f"Error al obtener JSON para producto {product_id}: {e}")
    return None

def product_details(product_id, product_link, url, current_date, timestamp):
    """
    Function to extract product details from the JSON data and return them as a dictionary. 

    Args:
    - product_id: str, the unique identifier for the product
    - product_link: str, the URL of the product page
    - url: str, the URL of the category page
    - current_date: str, the current date in the format "YYYY-MM-DD"
    - timestamp: str, the current timestamp in the format "YYYY-MM-DD HH:MM:SS.mmm UTC

    Returns:
    - dict: a dictionary containing the product details
    """

    json_data = get_product_json(product_id)
    if not json_data or not json_data.get("Value"):
        return None

    # Extract product details from the JSON data
    details = json_data["Value"]["ProductDetailInformation"]
    image = json_data["Value"].get("MediaInformation", [{}])[0].get("Url", "N/A")

    return {
        "product_URL": product_link,
        "category": details.get("CategoryName", "N/A"),
        "subcategory": details.get("ClassificationName", "N/A"),
        "sku": details.get("ReferenceCode", "N/A"),
        "price": details.get("Price", "N/A"),
        "discount_percentage": details.get("DiscountPercentage", "N/A"),
        "discount_price": details.get("NewPrice", "N/A"),
        "product_name": details.get("Name", "N/A"),
        "available_quantity": details.get("MaxQuantity", "N/A"),
        "primary_image": image,
        "stock_status": "In Stock" if details.get("MaxQuantity", 0) > 0 else "Out of Stock",
        "brand": details.get("ManufacturerName", "N/A"),
        "date_scrape": current_date,
        "country": "co",
        "Category_URL": url,
        "scraping_timestamp": timestamp
    }

def scrape_category(url: str):
    """
    Function to scrape a category page on the Surtiapp website and extract product details.

    Args:
    - url: str, the URL of the category page

    Returns:
    - list: a list of dictionaries containing the product details
    """

    print(f"Iniciando Scraping")
    start_time = time.time()

    driver = get_driver()
    wait = WebDriverWait(driver, 10) 
    products_data = []

    # Extract category name from the URL
    try:
        category_name = url.split("/SearchByCategoryResults/")[1].split("/")[0]
    except IndexError:
        category_name = "Unknown"
    print(f"Categoría detectada: {category_name}")

    try:
        print(f"Abriendo URL: {url}")
        driver.get(url)
        time.sleep(2)

        # Scroll to the bottom of the page to load all products
        while True:
            try:
                show_more_btn = wait.until(EC.element_to_be_clickable((By.ID, "buttonLoadId")))
                driver.execute_script("arguments[0].scrollIntoView();", show_more_btn)
                driver.execute_script("arguments[0].click();", show_more_btn)
                print("Cargando más productos...")
                time.sleep(2)
            except Exception:
                print("Todos los productos visibles cargados.")
                break

        # Wait for product cards to load
        product_cards = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "product-card")))
        print(f"Se encontraron {len(product_cards)} productos en la página.")

        # Extract and process each product sequentially
        current_date = datetime.now().strftime("%Y-%m-%d")
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f UTC")

        cards_data = []
        for card in product_cards:
            try:
                # Extract product ID and URL from the card
                product_link = card.find_element(By.CSS_SELECTOR, ".product-card__body--link").get_attribute("href")
                product_id = product_link.split("ProductDetail/")[-1]
                cards_data.append((product_id, product_link))
            except:
                continue
        
        # Use ThreadPoolExecutor to parallelize the extraction of product details
        with ThreadPoolExecutor(max_workers=8) as executor:  
            futures = [executor.submit(product_details, p_id, p_link, url, current_date, timestamp) for p_id, p_link in cards_data]
            for future in futures:
                result = future.result()
                if result:
                    products_data.append(result)

    except Exception as e:
        print(f"Error general durante el scraping de {category_name}: {e}")
        return []

    finally:
        driver.quit()
        print("Navegador cerrado")

    end_time = time.time()
    print("--------------------------------------------------")
    print(f"{len(products_data)} productos extraídos de {category_name} en {end_time - start_time:.2f} segundos")
    print("--------------------------------------------------\n")

    return products_data


def generate_new_dataset():
    """
    Function to scrape multiple categories from the Surtiapp website and generate a new dataset.
    """

    urls = {
        "Insecticidas": "https://tienda.surtiapp.com.co/WithoutLoginB2B/Store/SearchByCategoryResults/Insecticidas/98383dff-e904-ea11-add2-501ac5356f6d",
        "Cocina": "https://www.surtiapp.com.co/WithoutLoginB2B/Store/SearchByCategoryResults/Cocina/b1383dff-e904-ea11-add2-501ac5356f6d",
        "Baño": "https://tienda.surtiapp.com.co/WithoutLoginB2B/Store/SearchByCategoryResults/Ba%C3%B1o/7d383dff-e904-ea11-add2-501ac5356f6d",
        "Pisos y Muebles": "https://tienda.surtiapp.com.co/WithoutLoginB2B/Store/SearchByCategoryResults/Pisos%20y%20Muebles/5b383dff-e904-ea11-add2-501ac5356f6d",
        "Cuidado Corporal": "https://tienda.surtiapp.com.co/WithoutLoginB2B/Store/SearchByCategoryResults/Cuidado%20Corporal/734903dd-1420-ea11-a601-0004ffd345f9",
        "Hogar": "https://tienda.surtiapp.com.co/WithoutLoginB2B/Store/SearchByCategoryResults/Hogar/4a8541a7-1621-ea11-a601-0004ffd345f9",
        "Implementos para limpieza": "https://tienda.surtiapp.com.co/WithoutLoginB2B/Store/SearchByCategoryResults/Implementos%20para%20limpieza/f1b950d1-2597-eb11-85aa-000d3a914014",
        "Servilletas y Toallas de Cocina": "https://tienda.surtiapp.com.co/WithoutLoginB2B/Store/SearchByCategoryResults/Servilletas%20y%20Toallas%20de%20Cocina/b50dcfd7-6875-ed11-9d78-000d3a93fe17",
        "Ropa": "https://tienda.surtiapp.com.co/WithoutLoginB2B/Store/SearchByCategoryResults/Ropa/a5383dff-e904-ea11-add2-501ac5356f6d"
    }

    all_data = []

    for name, url in urls.items():
        try:
            data = scrape_category(url)
            all_data.extend(data)
        except Exception as e:
            print(f"Error en el scraping {name}: {e}")

    if all_data:
        df = pd.DataFrame(all_data)
        os.makedirs("data", exist_ok=True)
        filename = f"data/surtiapp_dataset_{datetime.now().date()}.csv"
        df.to_csv(filename, index=False)
        print(f"Total de productos extraídos: {len(all_data)}")
    else:
        print("No se encontró data.")


if __name__ == "__main__":
    # Run the scraping function to generate the new dataset with the extracted product information
    generate_new_dataset()
