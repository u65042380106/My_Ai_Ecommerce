import time
import re
from flask import Flask, jsonify, request
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc

app = Flask(__name__)

def make_serializable(obj):
    if isinstance(obj, set):
        return list(obj)
    if isinstance(obj, dict):
        return {k: make_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [make_serializable(i) for i in obj]
    return obj

def scrape_lazada_200_items(keyword, min_price, max_price, ship_from_filter):
    products_list = []
    seen_links = set()  # 🌟 สร้างตัวแปร Set สำหรับจดจำลิงก์สินค้าที่เคยดึงมาแล้ว
    
    try:
        options = uc.ChromeOptions()
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-popup-blocking")
        
        driver = uc.Chrome(options=options, version_main=149)
        current_page = 1
        max_safety_pages = 8  

        while len(products_list) < 30 and current_page <= max_safety_pages:
            
            base_url = f"https://www.lazada.co.th/catalog/?q={keyword}&page={current_page}"
            if min_price: base_url += f"&priceMin={min_price}"
            if max_price: base_url += f"&priceMax={max_price}"
            
            if ship_from_filter == "overseas":
                base_url += "&location=Overseas"
            elif ship_from_filter == "local":
                base_url += "&location=Local"
            
            print(f"\n[n8n Request] กำลังเปิดหน้าต่างที่ {current_page}...")
            driver.get(base_url)
            time.sleep(4) 

            for _ in range(12):
                driver.execute_script("window.scrollBy(0, 500);")
                time.sleep(0.5)

            items_found_in_this_page = 0
            
            # 🚀 วิธีที่ 1: เจาะ JSON
            try:
                page_data = driver.execute_script("return window.pageData;")
                if page_data and 'mods' in page_data and 'listItems' in page_data['mods']:
                    items = page_data['mods']['listItems']
                    
                    for item in items:
                        title = item.get('name', '')
                        alink = item.get('itemUrl', '')
                        if alink and alink.startswith('//'): alink = 'https:' + alink
                        
                        # 🌟 ระบบเช็กสินค้าซ้ำ (ตัด Tracking พารามิเตอร์ด้านหลัง ? ออกก่อนเทียบ)
                        clean_link = alink.split('?')[0] if alink else ""
                        if not clean_link or clean_link in seen_links:
                            continue  # ถ้าลิงก์นี้เคยดึงไปแล้ว ให้ข้ามทันที
                        seen_links.add(clean_link) # จดจำลิงก์นี้ไว้
                            
                        image_url = item.get('image') or item.get('itemImg') or item.get('picUrl') or item.get('thumbnail') or ""
                        if image_url and image_url.startswith('//'): 
                            image_url = 'https:' + image_url
                            
                        price = str(item.get('priceShow', item.get('price', '0')))
                        sales = str(item.get('itemSoldCntShow', item.get('sold', item.get('sales', '0')))).replace('ขายแล้ว', '').replace('ชิ้น', '').replace('sold', '').strip()
                        rating = str(item.get('ratingScore', item.get('rating', 'ไม่มีคะแนน')))
                        if rating == "None": rating = "ไม่มีคะแนน"
                        review_count = str(item.get('review', item.get('reviews', item.get('reviewCount', '0'))))
                        ship_from = str(item.get('location', item.get('sellerLocation', item.get('shipFrom', 'ไม่ระบุ'))))

                        products_list.append({
                            "id": len(products_list) + 1,
                            "title": title,
                            "price": float(price) if str(price).replace('.','',1).isdigit() else 0,
                            "sales": sales,
                            "rating": rating,
                            "review_count": review_count,
                            "link": alink,
                            "ship_from": ship_from,
                            "image_url": image_url
                        })
                        items_found_in_this_page += 1
                        if len(products_list) >= 30: break
            except: pass

            # 🚀 วิธีที่ 2: สแกนจาก HTML
            if items_found_in_this_page == 0:
                print("⚠️ สลับมาใช้ระบบสแกนหาจาก HTML...")
                cards = driver.find_elements(By.CSS_SELECTOR, 'div[data-qa-locator="product-item"]')
                if len(cards) == 0:
                    cards = driver.find_elements(By.CSS_SELECTOR, 'div[data-tracking="product-card"]')

                for card in cards:
                    try:
                        try:
                            a_tag = card.find_element(By.CSS_SELECTOR, "div.RfADt a")
                        except:
                            a_tag = card.find_element(By.TAG_NAME, "a")
                            
                        title = a_tag.get_attribute("title").strip() or a_tag.text.strip()
                        alink = a_tag.get_attribute("href")
                        if 'https:' not in alink: continue
                        
                        # 🌟 ระบบเช็กสินค้าซ้ำ สำหรับฝั่ง HTML
                        clean_link = alink.split('?')[0] if alink else ""
                        if not clean_link or clean_link in seen_links:
                            continue
                        seen_links.add(clean_link)
                        
                        image_url = ""
                        try:
                            card_html = card.get_attribute("outerHTML")
                            match = re.search(r'<img[^>]*?type="product"[^>]*?src=["\']([^"\']+)["\']', card_html)
                            if not match:
                                match = re.search(r'<img[^>]*?src=["\']([^"\']+)["\'][^>]*?type="product"', card_html)
                            if not match:
                                match = re.search(r'<img[^>]*?alt=["\'][^"\']*["\'][^>]*?src=["\']([^"\']+)["\']', card_html)
                            if not match:
                                match = re.search(r'class="picture-wrapper[^>]*>.*?<img[^>]*?src=["\']([^"\']+)["\']', card_html, re.DOTALL)
                            
                            if match:
                                raw_link = match.group(1)
                                if "data:image" not in raw_link:
                                    image_url = raw_link

                            if image_url:
                                if image_url.startswith('//'): 
                                    image_url = 'https:' + image_url
                                image_url = re.sub(r'_\d+x\d+q\d+\.[a-zA-Z0-9]+$', '_400x400q75.jpg', image_url)
                        except Exception as img_e:
                            pass
                            
                        price = "0"
                        try: 
                            price_elem = card.find_element(By.CSS_SELECTOR, "span.ooOxS")
                            price = price_elem.text.replace("฿", "").replace(",", "").strip()
                        except:
                            try:
                                price_elem = card.find_element(By.XPATH, ".//span[contains(text(), '฿')]")
                                price = price_elem.text.replace("฿", "").replace(",", "").strip()
                            except: pass
                        
                        sales = "0"
                        try: 
                            sales_elem = card.find_element(By.CSS_SELECTOR, "span._1cEkb")
                            sales = sales_elem.text.replace("ขายแล้ว", "").replace("ชิ้น", "").replace("sold", "").strip()
                        except:
                            try:
                                sales_elem = card.find_element(By.XPATH, ".//span[contains(text(), 'ชิ้น') or contains(text(), 'ขาย')]")
                                sales = sales_elem.text.replace("ขายแล้ว", "").replace("ชิ้น", "").strip()
                            except: pass
                        
                        review_count = "0"
                        try:
                            rev_elem = card.find_element(By.CSS_SELECTOR, "span.qzqFw")
                            review_count = rev_elem.text.replace("(", "").replace(")", "").replace(",", "").strip()
                        except: pass

                        rating = "0.0"
                        try:
                            star_box = card.find_element(By.CSS_SELECTOR, "div.mdmmT")
                            stars = star_box.find_elements(By.TAG_NAME, "i")
                            score = 0.0
                            for star in stars:
                                star_class = star.get_attribute("class") or ""
                                if "Dy1nx" in star_class: score += 1.0
                                elif "K8PID" in star_class: score += 0.0
                                elif star_class != "": score += 0.5
                            if score > 0: rating = str(score)
                        except: pass
                        
                        ship_from = "ไม่ระบุ"
                        try: 
                            loc_elem = card.find_element(By.CSS_SELECTOR, "span.oa6ri")
                            ship_from = loc_elem.get_attribute("title").strip() or loc_elem.text.strip()
                        except: pass

                        products_list.append({
                            "id": len(products_list) + 1,
                            "title": title,
                            "price": float(price) if price.replace('.','',1).isdigit() else 0,
                            "sales": sales if sales else "0",
                            "rating": rating if rating != "0.0" else "ไม่มีคะแนน", 
                            "review_count": review_count if review_count else "0",
                            "link": alink,
                            "ship_from": ship_from if ship_from else "ไม่ระบุ",
                            "image_url": image_url
                        })
                        items_found_in_this_page += 1
                        if len(products_list) >= 30: break
                    except Exception as e:
                        continue

            if items_found_in_this_page == 0: 
                print("⚠️ ไม่พบสินค้าใหม่เลย! (หยุดการค้นหา)")
                break
            current_page += 1
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        try: driver.quit()
        except: pass
        
    return products_list

@app.route('/api/scrape', methods=['POST'])
def run_scraper():
    data = request.get_json()
    
    print(f"\n[API] ได้รับคำสั่งค้นหา: {data.get('keyword', '')} (Filter จัดส่ง: {data.get('ship_from', 'all')})")
    
    results = scrape_lazada_200_items(
        data.get('keyword', ''),
        data.get('min_price', ''),
        data.get('max_price', ''),
        data.get('ship_from', 'all')
    )
    
    print(f"✅ ขูดข้อมูลสำเร็จทั้งหมด {len(results)} ชิ้น กำลังแพ็กส่งกลับไปยัง n8n...")
    return jsonify(make_serializable(results))

if __name__ == '__main__':
    print("🚀 สตาร์ท API ขูดข้อมูล Lazada เรียบร้อย! สแตนด์บายอยู่ที่พอร์ต 5000...")
    app.run(host='127.0.0.1', port=5000, debug=True)