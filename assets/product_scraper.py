from bs4 import BeautifulSoup
import time
from urllib3.util.retry import Retry
from urllib3 import PoolManager
import re
import sqlite3
import os

# Web scraping yöntemi ile bir e-ticaret sitesindeki ürün bilgilerini çekmemize
# ve bu bilgileri kendi veritabanımıza kaydetmemizi sağlar.

conn = sqlite3.connect(os.path.join(".", "assets", "products.db"))
c = conn.cursor()

c.execute('''
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        brand TEXT,
        price TEXT,
        brandhref TEXT,
        imageurl TEXT,
        url TEXT,
        description TEXT,
        content TEXT,
        category_id INTEGER,
        vote REAL NULL
    )
''')
c.execute('''
    CREATE TABLE IF NOT EXISTS product_url (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT,
        category_id INTEGER
    )
''')
c.execute('''
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT
    )
''')
conn.commit()

retries = Retry(total=5, backoff_factor=1, status_forcelist=[502, 503, 504])
http = PoolManager(retries=retries)

base_url = "https://www.lcw.com"

categories = [
    "/kadin-t-1", 
    "/mvc/kolej-stili-kadin-btc", 
    "/kadin-giyim-t-10",
    "/kadin-tisort-t-348",
    "/kadin-jean-t-196",
    "/elbise-t-149",
    "/kadin-sweatshirt-t-303",
    "/kadin-esofman-alti-t-3528",
    "/kadin-yelek-t-1925",
    "/kadin-ceket-t-133",
    "/kadin-tayt-t-334",
    "/hamile-giyim-t-211",
    "/kadin-kazak-t-202",
    "/kadin-canta-t-126",
    "/kadin-fular-ve-sal-t-142",
    "/kadin-sapka-t-309",
    "/kadin-kolsuz-tisort-t-5112",
    "/kadin-hirka-t-186",
    "/kadin-giyim-t-10?marka=lcw-active",
    "/kadin-sort-t-319",
    "/kadin-kapri-t-5200",
    "/kadin-trenckot-t-1929",
    "/kadin-bluz-t-105",
    "/kadin-gomlek-t-176",
    "/kadin-pantolon-t-263",
    "/kadin-tunik-t-360",
    "/kadin-spor-ayakkabi-t-292",
    "/kadin-babet-t-101",
    "/kadin-ev-ayakkabilari-t-169",
    "/kadin-bot-t-117",
    "/kadin-topuklu-ayakkabi-t-351",
    "/kadin-canta-t-126",
    "/kadin-fular-ve-sal-t-142",
    "/kadin-sapka-t-309",
    "/kadin-spor-ayakkabi-t-292",
    "/kadin-topuklu-ayakkabi-t-351",
    "/kadin-babet-t-101",
    "/kadin-ayakkabi-t-33",
    "/kadin-klasik-ayakkabi-t-212",
    "/kadin-gunluk-ayakkabi-t-5020",
    "/kadin-espadril-ayakkabi-t-5021",
    "/kadin-loafer-ayakkabi-t-5022",
    "/kadin-oxford-ayakkabi-t-5023",
    "/kadin-jean-t-196",
    "/kadin-sneaker-t-911"
]

for i, category in enumerate(categories):
    cur = conn.cursor()
    cur.execute("INSERT INTO categories (url) VALUES (?)", (category,))
    conn.commit()

#---------------------------------------------------------------

cursor = conn.cursor()
cursor.execute('SELECT * FROM categories')
categories = cursor.fetchall()

for i, category in enumerate(categories):
    response = http.request('GET', base_url + category[1])
    soup = BeautifulSoup(response.data, "html.parser")

    for product_card in soup.find_all('div', class_="product-card"):
        a_tag = product_card.find('a')
        if a_tag:
            product_url = a_tag.get('href')
            cur = conn.cursor()
            cur.execute("INSERT INTO product_url (url, category_id) VALUES (?, ?)", (product_url, category[0],))
            conn.commit()


#---------------------------------------------------------------

cursor = conn.cursor()
cursor.execute('SELECT * FROM product_url WHERE category_id IN (4, 5, 6, 7, 8, 23, 24, 25, 32, 35)')
product_links = cursor.fetchall()

for product in product_links:
    
    url = product[1]
    
    product_response = http.request('GET', base_url + url)
    product_soup = BeautifulSoup(product_response.data, "html.parser")

    product_section = product_soup.find('div', class_='title-info')
    
    alldescription = product_soup.find('div', class_="panel-body")
    
    description = None
    cleaned_text = None
    
    if alldescription != None:
        description_section = alldescription.find('h5')
        description = description_section.find_next('li').get_text().strip()
    
        cleaned_text = re.sub(r'\n\s*\n+', '\n', alldescription.get_text(separator="\n").strip())
        cleaned_text = re.sub(r'\s*:\s*', ': ', cleaned_text)
        cleaned_text = re.sub(r'\s{2,}', ' ', cleaned_text)
        cleaned_text = re.sub(r'(Göğüs|Bel|Basen|Boy|Ana Kumaş|Satıcı|Marka|Ürün Tip|Cinsiyet|Kalıp|Kumaş|Desen|Yaka|Kol Boyu):', r'\1:', cleaned_text)
    
    brand = None
    title = None
    
    if product_section != None:
        brand = product_section.find('a', class_='brand-link')
        brandHref = brand["href"]
        brand = brand.text.strip()
        title = product_section.find('h1', class_='product-title').text.strip()
    
    image_section = product_soup.find('div', class_='product-images-desktop hidden-xs')
    
    imageUrl = None

    if image_section:
        img_tags = image_section.find_all('img')
        if len(img_tags) >= 5:
            imageUrl = img_tags[4]['src']
        elif len(img_tags) >= 3:
            imageUrl = img_tags[2]['src']
        else:
            imageUrl = img_tags[0]['src']

    if brand and title:
        if brand in title:
            title = title.replace(brand, '').strip()
            
    price_section = product_soup.find('span', class_='advanced-price')
    price = None
    
    if price_section != None:
        price = price_section.text.strip()
    
    if title is not None and price is not None:
        cur = conn.cursor()
        cur.execute("INSERT INTO products (title, brand, price, brandhref, imageurl, url, description, content, category_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (title, brand, price, brandHref, imageUrl, url, description, cleaned_text, product[2]))
        conn.commit()

    time.sleep(0.5)
    

#-------------------------------------------------------


from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# WebDriver'ı başlat
driver = webdriver.Chrome()

# Veritabanından ürünleri al
c.execute('SELECT * FROM products')
products = c.fetchall()

# Ürün sayısını yazdır
print(f"Toplam Ürün Sayısı: {len(products)}")

for product in products:
    if product[10] != 0:
        continue
    print(product[0], product[10])
    driver.get(base_url + product[6])  # Ürün URL'sini aç

    try:
        # Yıldız elementi yüklenene kadar bekle
        rating_element = WebDriverWait(driver, 1).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'rating-stars__filled-stars-container'))
        )
        
        # Eğer element bulunduysa
        if rating_element:
            class_attr = rating_element.get_attribute('class')
            # Yüzde değerini al (örneğin pct-89 gibi)
            pct_class = [cls for cls in class_attr.split() if 'pct-' in cls]
            if pct_class:
                rating_percentage = pct_class[0].replace('pct-', '')
                rating = float(rating_percentage) / 20  # 5 üzerinden hesaplamak için
                print(f"Rating: {rating:.2f} yıldız")
                product_id = product[0]  # ID değerini al
                c.execute('UPDATE products SET vote = ? WHERE id = ?', (rating, product_id))
                conn.commit()  # Değişiklikleri kaydet
            else:
                print("Yıldız verisi bulunamadı.")
    except Exception as e:
        print(f"Hata: {str(e)}. Yıldız verisi bulunamadı.")

# Tarayıcıyı kapat
driver.quit()

