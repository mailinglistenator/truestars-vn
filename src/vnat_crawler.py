#!/usr/bin/env python3
"""
VNAT Crawler: Extracts official 4-star and 5-star accredited hotel records
from the Vietnam National Authority of Tourism database (csdl.vietnamtourism.gov.vn).
"""

import sys
import os
import re
import html
import json
import time
import logging
import sqlite3
import unicodedata
import urllib.request
import urllib.parse
import http.cookiejar
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BASE_URL = "https://csdl.vietnamtourism.gov.vn/cslt/"
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "watchdog.db")
JSON_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "vnat_whitelist.json")

def remove_accents(input_str: str) -> str:
    """Normalize Vietnamese unicode string and remove accents/diacritics."""
    if not input_str:
        return ""
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    no_accents = ''.join([c for c in nfkd_form if not unicodedata.combining(c)])
    no_accents = no_accents.replace('đ', 'd').replace('Đ', 'D')
    cleaned = re.sub(r'\s+', ' ', no_accents).strip().lower()
    return cleaned

def extract_search_tokens(name: str) -> str:
    """Extract key business tokens for fuzzy matching, removing common generic prefixes."""
    normalized = remove_accents(name)
    prefixes = [
        r"^khach san nghi duong\s+",
        r"^khach san\s+",
        r"^khu nghi duong\s+",
        r"^khu can ho cao cap\s+",
        r"^can ho du lich\s+",
        r"^toa nha\s+",
        r"^hotel\s+",
        r"^resort & spa\s+",
        r"^resort\s+",
    ]
    for p in prefixes:
        normalized = re.sub(p, "", normalized)
    return normalized.strip()

class VNATCrawler:
    def __init__(self):
        self.cj = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cj))
        self.csrf_token = None

    def get_csrf_token(self) -> str:
        req = urllib.request.Request(
            BASE_URL,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )
        try:
            with self.opener.open(req, timeout=15) as resp:
                content = resp.read().decode("utf-8", errors="ignore")
                match = re.search(r'name="csrf_name"\s+value="([^"]+)"', content)
                if match:
                    self.csrf_token = match.group(1)
                    return self.csrf_token
        except Exception as e:
            logger.error(f"Failed to obtain CSRF token: {e}")
        raise RuntimeError("Could not retrieve CSRF token from VNAT CSDL portal.")

    def parse_card(self, block: str, default_stars: int) -> Optional[Dict]:
        """Extract a single hotel card from HTML block."""
        name_match = re.search(r'<h4><a href="/cslt/\?item=(\d+)">([^<]+)</a>', block)
        if not name_match:
            return None
        
        item_id = int(name_match.group(1))
        name = html.unescape(name_match.group(2)).strip()
        
        # Check stars
        stars = default_stars
        star_img_match = re.search(r'uploads/Icons/([0-9])star\.png', block)
        if star_img_match:
            stars = int(star_img_match.group(1))
            
        # Check property type
        type_match = re.search(r'<i class="fa fa-bed"[^>]*></i>&nbsp;([^<\n\r]+)', block)
        prop_type = html.unescape(type_match.group(1)).strip() if type_match else "Khách sạn"
        
        # Check address
        addr_match = re.search(r'Địa chỉ:\s*([^<\n\r]+)', block)
        address = html.unescape(addr_match.group(1)).strip() if addr_match else ""
        
        # Check room count
        room_match = re.search(r'Số phòng:\s*(\d+)', block)
        room_count = int(room_match.group(1)) if room_match else None
        
        # Check phone
        phone_match = re.search(r'Điện thoại[^:]*:\s*([0-9\s\.\-]+)', block)
        phone = phone_match.group(1).strip() if phone_match else ""

        # Extract province / municipality from address
        province = ""
        prov_match = re.search(r'(Thành phố [^,]+|Tỉnh [^,]+|TP\.?\s*[^,]+)$', address, re.IGNORECASE)
        if prov_match:
            province = prov_match.group(1).strip()
        else:
            for city in ["Hà Nội", "Hồ Chí Minh", "Đà Nẵng", "Khánh Hòa", "Quảng Nam", 
                         "Quảng Ninh", "Kiên Giang", "Lâm Đồng", "Bình Thuận", 
                         "Thừa Thiên Huế", "Vũng Tàu", "Cần Thơ", "Hải Phòng"]:
                if city.lower() in address.lower():
                    province = city
                    break

        return {
            "item_id": item_id,
            "name": name,
            "name_normalized": remove_accents(name),
            "search_tokens": extract_search_tokens(name),
            "stars": stars,
            "property_type": prop_type,
            "address": address,
            "province": province,
            "room_count": room_count,
            "phone": phone
        }

    def fetch_page(self, rate_code: int, page_num: int, default_stars: int) -> List[Dict]:
        """Fetch and parse one page for a given star tier."""
        url = BASE_URL if page_num == 1 else f"{BASE_URL}?page={page_num}"
        post_data = urllib.parse.urlencode({
            "csrf_name": self.csrf_token,
            "title": "",
            "province": "",
            "rate[]": str(rate_code)
        }).encode("utf-8")
        
        req = urllib.request.Request(
            url,
            data=post_data,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Content-Type": "application/x-www-form-urlencoded"
            }
        )

        try:
            with self.opener.open(req, timeout=20) as resp:
                content = resp.read().decode("utf-8", errors="ignore")
                
                csrf_match = re.search(r'name="csrf_name"\s+value="([^"]+)"', content)
                if csrf_match:
                    self.csrf_token = csrf_match.group(1)

                raw_items = re.findall(r'(<h4><a href="/cslt/\?item=\d+">.*?</div>\s*</div>)', content, re.S)
                items = []
                for block in raw_items:
                    card = self.parse_card(block, default_stars)
                    if card:
                        items.append(card)
                
                return items
        except Exception as e:
            logger.error(f"Error fetching rate_code={rate_code}, page={page_num}: {e}")
            return []

    def crawl_all(self) -> List[Dict]:
        """Crawl both 5-star (rate=1) and 4-star (rate=2) tiers nationwide."""
        self.get_csrf_token()
        all_hotels = {}

        # 1. Fetch 5-star hotels (rate=1)
        logger.info("Crawling 5-star hotels (rate[]=1)...")
        page = 1
        max_5star_pages = 22
        while page <= max_5star_pages:
            logger.info(f"Fetching 5-star page {page}...")
            items = self.fetch_page(rate_code=1, page_num=page, default_stars=5)
            if not items:
                logger.info(f"No items on 5-star page {page}, finished 5-star crawl.")
                break
            for it in items:
                all_hotels[it["item_id"]] = it
            page += 1
            time.sleep(0.2)

        # 2. Fetch 4-star hotels (rate=2)
        logger.info("Crawling 4-star hotels (rate[]=2)...")
        page = 1
        max_4star_pages = 28
        while page <= max_4star_pages:
            logger.info(f"Fetching 4-star page {page}...")
            items = self.fetch_page(rate_code=2, page_num=page, default_stars=4)
            if not items:
                logger.info(f"No items on 4-star page {page}, finished 4-star crawl.")
                break
            for it in items:
                all_hotels[it["item_id"]] = it
            page += 1
            time.sleep(0.2)

        hotel_list = list(all_hotels.values())
        logger.info(f"Completed crawl! Total unique accredited hotels extracted: {len(hotel_list)}")
        return hotel_list

def init_db(db_path: str):
    """Initialize SQLite database for VNAT hotels."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS vnat_hotels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER UNIQUE,
            name TEXT NOT NULL,
            name_normalized TEXT NOT NULL,
            search_tokens TEXT NOT NULL,
            stars INTEGER NOT NULL,
            property_type TEXT,
            address TEXT,
            province TEXT,
            room_count INTEGER,
            phone TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cur.execute("CREATE INDEX IF NOT EXISTS idx_vnat_name_normalized ON vnat_hotels(name_normalized)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_vnat_search_tokens ON vnat_hotels(search_tokens)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_vnat_stars ON vnat_hotels(stars)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_vnat_province ON vnat_hotels(province)")
    
    conn.commit()
    conn.close()

def save_to_db(hotels: List[Dict], db_path: str):
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    for h in hotels:
        cur.execute("""
            INSERT INTO vnat_hotels (
                item_id, name, name_normalized, search_tokens, stars,
                property_type, address, province, room_count, phone
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(item_id) DO UPDATE SET
                name = excluded.name,
                name_normalized = excluded.name_normalized,
                search_tokens = excluded.search_tokens,
                stars = excluded.stars,
                property_type = excluded.property_type,
                address = excluded.address,
                province = excluded.province,
                room_count = excluded.room_count,
                phone = excluded.phone,
                updated_at = CURRENT_TIMESTAMP
        """, (
            h["item_id"], h["name"], h["name_normalized"], h["search_tokens"],
            h["stars"], h["property_type"], h["address"], h["province"],
            h["room_count"], h["phone"]
        ))
    
    conn.commit()
    conn.close()
    logger.info(f"Saved {len(hotels)} records to database: {db_path}")

def save_to_json(hotels: List[Dict], json_path: str):
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(hotels, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved {len(hotels)} records to JSON: {json_path}")

def main():
    crawler = VNATCrawler()
    hotels = crawler.crawl_all()
    if hotels:
        save_to_json(hotels, JSON_PATH)
        save_to_db(hotels, DB_PATH)
        print(f"\n=======================================================")
        print(f"SUCCESS: Ingested {len(hotels)} legitimate 4★ and 5★ hotels from VNAT!")
        print(f"Database: {DB_PATH}")
        print(f"JSON: {JSON_PATH}")
        print(f"=======================================================\n")
    else:
        print("ERROR: No hotels were extracted.")
        sys.exit(1)

if __name__ == "__main__":
    main()
