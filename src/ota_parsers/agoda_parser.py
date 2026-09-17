#!/usr/bin/env python3
"""
Agoda Listing Parser: Extracts property name, displayed star rating,
room types, and indicators of dorms/bunks from Agoda URLs and HTML.
"""

import re
import json
import html
import urllib.request
from typing import Dict, Optional

DORM_INDICATORS = [
    r'\bdorm\b', r'\bdormitory\b', r'\bbunk\b', r'bunk bed',
    r'giuong tang', r'giường tầng', r'tap the', r'tập thể',
    r'phong tap the', r'phòng tập thể', r'shared room', r'shared dorm',
    r'capsule', r'hostel', r'backpacker'
]

class AgodaParser:
    @staticmethod
    def parse_html(html_content: str, url: str = "") -> Dict:
        """Parse raw HTML or JSON-LD from an Agoda hotel page."""
        name = ""
        claimed_stars = 0
        room_count = None
        has_dorm = False
        address = ""
        province = ""

        # 1. Search for JSON-LD schema (schema.org/Hotel)
        json_ld_matches = re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html_content, re.S)
        for jld in json_ld_matches:
            try:
                data = json.loads(jld)
                if isinstance(data, dict):
                    if data.get("@type") in ["Hotel", "LodgingBusiness", "Hostel"]:
                        name = data.get("name", name)
                        if "starRating" in data and isinstance(data["starRating"], dict):
                            claimed_stars = int(float(data["starRating"].get("ratingValue", 0)))
                        if "address" in data:
                            addr = data["address"]
                            if isinstance(addr, dict):
                                address = f"{addr.get('streetAddress', '')}, {addr.get('addressLocality', '')}, {addr.get('addressCountry', '')}"
                                province = addr.get("addressRegion", addr.get("addressLocality", ""))
            except Exception:
                pass

        # 2. Fallback regex on HTML meta tags & headers
        if not name:
            title_match = re.search(r'<h1[^>]*property-name[^>]*>([^<]+)</h1>', html_content, re.I)
            if not title_match:
                title_match = re.search(r'<title>([^<]+)</title>', html_content, re.I)
            if title_match:
                name = html.unescape(title_match.group(1)).split('|')[0].split('-')[0].strip()

        # 3. Fallback star rating extraction
        if claimed_stars == 0:
            star_match = re.search(r'(?:star-rating|starRating|hotel-stars|rating-star)[^>]*?([1-5])(?:\.0)?\s*star', html_content, re.I)
            if not star_match:
                star_match = re.search(r'data-selenium="star-rating"[^>]*?aria-label="([1-5])(?:\.0)?', html_content, re.I)
            if not star_match:
                star_match = re.search(r'([1-5])-star-hotel', url, re.I)
            if star_match:
                claimed_stars = int(float(star_match.group(1)))

        # 4. Check for room count
        room_match = re.search(r'(?:Number of rooms|Số phòng)[:\s]*(\d+)', html_content, re.I)
        if room_match:
            room_count = int(room_match.group(1))

        # 5. Check for dormitory / bunk bed / hostel flags
        text_lower = (html_content + " " + name + " " + url).lower()
        for pattern in DORM_INDICATORS:
            if re.search(pattern, text_lower, re.I):
                has_dorm = True
                break

        return {
            "ota_source": "Agoda",
            "ota_url": url,
            "name": name,
            "claimed_stars": claimed_stars,
            "room_count": room_count,
            "has_dorm": has_dorm,
            "address": address,
            "province": province
        }

    @classmethod
    def fetch_and_parse(cls, url: str) -> Dict:
        """Fetch live Agoda page with browser headers and parse."""
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9,vi;q=0.8"
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                content = resp.read().decode("utf-8", errors="ignore")
                return cls.parse_html(content, url=url)
        except Exception as e:
            # If blocked by Cloudflare/WAF, attempt URL heuristic fallback
            return cls.parse_url_fallback(url, error=str(e))

    @staticmethod
    def parse_url_fallback(url: str, error: str = "") -> Dict:
        """Infer basic parameters from Agoda URL slug if direct fetch is blocked."""
        # Example URL: https://www.agoda.com/hanoi-old-quarter-backpacker-hostel/hotel/hanoi-vn.html
        slug_match = re.search(r'agoda\.com/(?:[a-z]{2}-[a-z]{2}/)?([^/]+)/hotel/([^/]+)', url)
        name = "Unknown Agoda Hotel"
        province = ""
        if slug_match:
            slug = slug_match.group(1).replace("-", " ").title()
            name = slug
            location_slug = slug_match.group(2)
            if "hanoi" in location_slug:
                province = "Hà Nội"
            elif "danang" in location_slug:
                province = "Đà Nẵng"
            elif "ho-chi-minh" in location_slug or "saigon" in location_slug:
                province = "Hồ Chí Minh"

        has_dorm = any(re.search(p, url.lower()) for p in DORM_INDICATORS)
        return {
            "ota_source": "Agoda",
            "ota_url": url,
            "name": name,
            "claimed_stars": 4, # Default presumption for audit if not provided
            "room_count": 15 if has_dorm else None,
            "has_dorm": has_dorm,
            "address": "",
            "province": province,
            "note": f"Parsed via URL slug heuristic (direct fetch: {error})"
        }
