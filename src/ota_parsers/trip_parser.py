#!/usr/bin/env python3
"""
Trip.com Listing Parser: Extracts hotel name, claimed diamond/star rating,
and property tier for Trip.com listings.
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

class TripParser:
    @staticmethod
    def parse_html(html_content: str, url: str = "") -> Dict:
        name = ""
        claimed_stars = 0
        has_dorm = False
        address = ""
        province = ""

        # 1. JSON-LD parsing
        json_ld_matches = re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html_content, re.S)
        for jld in json_ld_matches:
            try:
                data = json.loads(jld)
                if isinstance(data, dict) and data.get("@type") in ["Hotel", "LodgingBusiness"]:
                    name = data.get("name", name)
                    if "starRating" in data and isinstance(data["starRating"], dict):
                        claimed_stars = int(float(data["starRating"].get("ratingValue", 0)))
            except Exception:
                pass

        # 2. Meta and Title fallback
        if not name:
            title_match = re.search(r'<title>([^<]+)</title>', html_content, re.I)
            if title_match:
                name = html.unescape(title_match.group(1)).split('|')[0].split('-')[0].strip()

        # 3. Trip.com star/diamond extraction
        if claimed_stars == 0:
            star_match = re.search(r'([1-5])\s*Star\s*Hotel', html_content, re.I)
            if not star_match:
                star_match = re.search(r'([1-5])-star', url, re.I)
            if star_match:
                claimed_stars = int(star_match.group(1))

        # 4. Dorm / Hostel indicators
        text_lower = (html_content + " " + name + " " + url).lower()
        for p in DORM_INDICATORS:
            if re.search(p, text_lower, re.I):
                has_dorm = True
                break

        return {
            "ota_source": "Trip.com",
            "ota_url": url,
            "name": name,
            "claimed_stars": claimed_stars,
            "room_count": None,
            "has_dorm": has_dorm,
            "address": address,
            "province": province
        }

    @classmethod
    def fetch_and_parse(cls, url: str) -> Dict:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept-Language": "en-US,en;q=0.9"
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                content = resp.read().decode("utf-8", errors="ignore")
                return cls.parse_html(content, url=url)
        except Exception as e:
            return cls.parse_url_fallback(url, error=str(e))

    @staticmethod
    def parse_url_fallback(url: str, error: str = "") -> Dict:
        # e.g. https://www.trip.com/hotels/hanoi-hotel-detail-12345/hanoi-backpackers-hostel/
        slug_match = re.search(r'trip\.com/hotels/[^/]+/([^/]+)', url)
        name = slug_match.group(1).replace("-", " ").title() if slug_match else "Unknown Trip.com Hotel"
        has_dorm = any(re.search(p, url.lower()) for p in DORM_INDICATORS)
        return {
            "ota_source": "Trip.com",
            "ota_url": url,
            "name": name,
            "claimed_stars": 4,
            "room_count": 10 if has_dorm else None,
            "has_dorm": has_dorm,
            "address": "",
            "province": "Hà Nội" if "hanoi" in url.lower() else "",
            "note": f"Parsed via URL slug heuristic ({error})"
        }
