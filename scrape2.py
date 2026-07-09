# scrape2.py
import time
from flask import Flask, jsonify, request
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc
import random

app = Flask(__name__)

def scrape_deep_details(urls):
    enriched_data = []
    
    options = uc.ChromeOptions()
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--blink-settings=imagesEnabled=true")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    options.add_argument("--disable-blink-features=AutomationControlled") # ปิดการตรวจจับว่าเป็น Automation
    
    try:
        driver = uc.Chrome(options=options, version_main=149) # ปรับให้ตรงกับ Chrome ของคุณ
        
        for url in urls:
            try:
                print(f"🔍 [Scrape2] กำลังดึงข้อมูลดิบ: {url}")
                driver.get(url)
                
                # เลื่อนจอลงมาเพื่อให้เว็บโหลด Text ออกมาให้ครบ
                print("   ⬇️ เลื่อนหน้าจอโหลดข้อมูล...")
                for i in range(1, 3):
                    driver.execute_script(f"window.scrollTo(0, {i * 1000});")
                    time.sleep(1.5)
                
                # 1. พยายามดึงรูปภาพความละเอียดสูง
                high_res_image = ""
                try:
                    meta_img = driver.find_element(By.CSS_SELECTOR, 'meta[property="og:image"]')
                    high_res_image = meta_img.get_attribute("content")
                except: pass
                
                if not high_res_image:
                    try:
                        img_element = driver.find_element(By.CSS_SELECTOR, "img.pdp-mod-common-image.gallery-preview-panel__image")
                        high_res_image = img_element.get_attribute("src")
                    except: pass
                
                if high_res_image and high_res_image.startswith('//'):
                    high_res_image = 'https:' + high_res_image
                    
                # 2. 🌟 กวาดตัวหนังสือ "ทั้งหมด" ในโซนรายละเอียดสินค้า 🌟
                raw_text = ""
                try:
                    # ดึงกล่องรายละเอียดสินค้า (คลุมทั้งไฮไลท์ สเปค และรายละเอียด)
                    detail_box = driver.find_element(By.ID, "module_product_detail")
                    raw_text = detail_box.text.strip()
                except:
                    try:
                        # แผนสำรอง: ถ้าหา ID ไม่เจอ ให้ดึงคลาสแทน
                        detail_box = driver.find_element(By.CSS_SELECTOR, ".pdp-product-detail-v2")
                        raw_text = detail_box.text.strip()
                    except:
                        try:
                            # แผนสำรองสุดท้าย: ดึงข้อความทั้งหน้า
                            raw_text = driver.find_element(By.TAG_NAME, "body").text.strip()
                        except:
                            raw_text = "ไม่พบข้อความ"
                
                # ตัดข้อความให้เหลือแค่ 2500 ตัวอักษร (เพื่อประหยัด Token ของ AI และเอาเฉพาะส่วนสเปคที่มักอยู่ด้านบน)
                raw_text = raw_text[:2500]

                enriched_data.append({
                    "url": url,
                    "high_res_image": high_res_image,
                    "raw_data": raw_text # ส่งกลับไปเป็นตัวแปร raw_data
                })
                print(f"✅ ดึงข้อมูลดิบสำเร็จ: ความยาว {len(raw_text)} ตัวอักษร")
                
            except Exception as e:
                print(f"⚠️ Error: {url} -> {e}")
                enriched_data.append({"url": url, "high_res_image": "", "raw_data": "Error"})
                
    except Exception as e:
        print(f"❌ Fatal Error in Scrape2: {e}")
    finally:
        try: driver.quit()
        except: pass
        
    return enriched_data

def random_sleep(min_sec=2, max_sec=5):
    time.sleep(random.uniform(min_sec, max_sec))

@app.route('/api/scrape_details', methods=['POST'])
def run_deep_scraper():
    data = request.get_json()
    urls = data.get('urls', [])
    if not urls:
        return jsonify({"error": "No URLs provided"}), 400
        
    results = scrape_deep_details(urls)
    return jsonify(results)

if __name__ == '__main__':
    app.run(port=5001, debug=True)