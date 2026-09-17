#!/usr/bin/env python3
"""
Matching Engine: Entity resolution matching between OTA listings and
the official VNAT 4-star and 5-star accreditation registry.

Supports:
1. Closed-World Deterministic Aggregator Identity Lookup (Agoda, Booking, Trip.com)
2. Token Overlap & Fuzzy String Matching Fallback
"""

import os
import re
import json
import sqlite3
import unicodedata
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse, parse_qs, unquote

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "watchdog.db")
WHITELIST_PATH = os.path.join(DATA_DIR, "vnat_whitelist.json")
INDEX_PATH = os.path.join(DATA_DIR, "ota_identity_index.json")

GEO_REPLACEMENTS = {
    r"\bhanoi\b": "ha noi",
    r"\bsaigon\b": "sai gon",
    r"\bdanang\b": "da nang",
    r"\bnhatrang\b": "nha trang",
    r"\bhalong\b": "ha long",
    r"\bphuquoc\b": "phu quoc",
    r"\bhochiminh\b": "ho chi minh",
    r"\bdalat\b": "da lat",
    r"\bhoian\b": "hoi an",
    r"\bhue\b": "thua thien hue",
    r"\bvungtau\b": "vung tau",
}

def remove_accents(input_str: str) -> str:
    """Normalize Vietnamese unicode string and remove accents/diacritics."""
    if not input_str:
        return ""
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    no_accents = ''.join([c for c in nfkd_form if not unicodedata.combining(c)])
    no_accents = no_accents.replace('đ', 'd').replace('Đ', 'D')
    cleaned = re.sub(r'[^\w\s]', ' ', no_accents)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip().lower()
    for k, v in GEO_REPLACEMENTS.items():
        cleaned = re.sub(k, v, cleaned)
    return cleaned

NOISE_WORDS = {
    "khach", "san", "hotel", "resort", "spa", "boutique", "suites", "suite", 
    "apartment", "apartments", "condo", "villa", "villas", "the", "and", "luxury",
    "international", "grand", "palace", "residence", "residences", "inn", "nghi", "duong",
    "co", "so", "luu", "tru", "ha", "noi", "saigon", "sai", "gon", "da", "nang",
    "ho", "chi", "minh", "hcm", "vietnam", "vn", "quoc", "te", "ha", "long",
    "nha", "trang", "phu", "quoc", "view", "central", "center", "city", "bay", "plaza"
}

def extract_core_tokens(name: str) -> set:
    """Extract distinct core semantic brand words from a hotel name."""
    norm = remove_accents(name)
    tokens = [t for t in norm.split() if len(t) > 2 and t not in NOISE_WORDS]
    return set(tokens)

def parse_ota_url(raw_input: str) -> Dict:
    """Parse OTA URL into platform, slug, ID, and inferred name."""
    trimmed = raw_input.strip()
    if not (trimmed.startswith("http://") or trimmed.startswith("https://") or "agoda.com" in trimmed or "booking.com" in trimmed or "trip.com" in trimmed):
        return {"is_url": False, "name": trimmed, "platform": "Direct Input", "city": "", "original_url": "", "ota_id": "", "ota_slug": ""}

    try:
        url = urlparse(trimmed if "://" in trimmed else "https://" + trimmed)
        host = url.netloc.lower()
        qs = parse_qs(url.query)
        platform = "Online Travel Agency"
        extracted_name = ""
        city = ""
        ota_id = ""
        ota_slug = ""

        if "agoda.com" in host:
            platform = "Agoda"
            m = re.search(r"/([^/]+)/hotel/", url.path, re.IGNORECASE)
            if m:
                ota_slug = m.group(1).lower()
                extracted_name = re.sub(r"[-_]", " ", ota_slug)
            else:
                parts = [p for p in url.path.split("/") if p]
                for p in parts:
                    if p not in ["hotel", "hotels", "country", "city"]:
                        ota_slug = re.sub(r"\.html.*$", "", p).lower()
                        extracted_name = re.sub(r"[-_]", " ", ota_slug)
                        break
            if "hotel_id" in qs:
                ota_id = qs["hotel_id"][0]

        elif "booking.com" in host:
            platform = "Booking.com"
            m = re.search(r"/hotel/[a-z]{2}/([^/.]+)", url.path, re.IGNORECASE)
            if m:
                ota_slug = m.group(1).lower()
                extracted_name = re.sub(r"[-_]", " ", ota_slug)
            else:
                parts = [p for p in url.path.split("/") if p]
                for p in parts:
                    if ".html" in p:
                        ota_slug = re.sub(r"\.html.*$", "", p).lower()
                        extracted_name = re.sub(r"[-_]", " ", ota_slug)
                        break
            if "ss" in qs:
                extracted_name = qs["ss"][0]

        elif "trip.com" in host:
            platform = "Trip.com"
            city = qs.get("cityEnName", [""])[0]
            ota_id = qs.get("hotelId", [""])[0]

            parts = [p for p in url.path.split("/") if p]
            for seg in parts:
                if "-hotel-detail-" in seg:
                    m = re.search(r"-hotel-detail-(\d+)", seg)
                    if m:
                        ota_id = m.group(1)
                elif seg not in ["hotels", "detail", "hotel"] and len(seg) > 4:
                    ota_slug = seg.lower()
                    extracted_name = re.sub(r"[-_]", " ", seg).strip()

            if not extracted_name and ota_id:
                extracted_name = f"Trip.com Hotel Listing #{ota_id}"

        # Clean artifacts
        extracted_name = re.sub(r"\bhotel vn\b", "", extracted_name, flags=re.IGNORECASE)
        extracted_name = re.sub(r"\bvn\b", "", extracted_name, flags=re.IGNORECASE)
        extracted_name = re.sub(r"\s+", " ", extracted_name).strip()
        if extracted_name:
            extracted_name = " ".join([w.capitalize() for w in extracted_name.split()])

        return {
            "is_url": True,
            "name": extracted_name or trimmed[:50],
            "platform": platform,
            "city": unquote(city) if city else "",
            "original_url": trimmed,
            "ota_id": ota_id,
            "ota_slug": ota_slug
        }
    except Exception:
        return {"is_url": True, "name": trimmed[:50], "platform": "Online Travel Agency", "city": "", "original_url": trimmed, "ota_id": "", "ota_slug": ""}

class MatchingEngine:
    def __init__(self, db_path: str = DB_PATH, whitelist_path: str = WHITELIST_PATH):
        self.db_path = db_path
        self.whitelist_path = whitelist_path
        self._cached_hotels = None
        self._by_item_id = {}
        self._by_trip_id = {}
        self._by_trip_slug = {}
        self._by_agoda_slug = {}
        self._by_agoda_id = {}
        self._by_booking_slug = {}
        self._load_cache()

    def _load_cache(self):
        """Pre-cache all 681 VNAT hotels in memory with inverted aggregator indexes."""
        # Load enriched JSON whitelist if available
        if os.path.exists(self.whitelist_path):
            with open(self.whitelist_path, "r", encoding="utf-8") as f:
                hotels_data = json.load(f)
        else:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM vnat_hotels")
            hotels_data = [dict(r) for r in cur.fetchall()]
            conn.close()

        self._cached_hotels = []
        self._by_item_id.clear()
        self._by_trip_id.clear()
        self._by_trip_slug.clear()
        self._by_agoda_slug.clear()
        self._by_agoda_id.clear()
        self._by_booking_slug.clear()

        for h in hotels_data:
            d = dict(h)
            item_id = d.get("item_id")
            d["name_norm"] = remove_accents(d.get("name", ""))
            d["prov_norm"] = remove_accents(d.get("province", ""))
            d["addr_norm"] = remove_accents(d.get("address", ""))
            d["tokens"] = extract_core_tokens(d.get("name", ""))
            self._cached_hotels.append(d)
            if item_id:
                self._by_item_id[item_id] = d

            # Inverted OTA indexes
            ota = d.get("ota_identities", {})
            for tid in ota.get("trip_ids", []):
                self._by_trip_id[str(tid)] = d
            for tslug in ota.get("trip_slugs", []):
                self._by_trip_slug[tslug.lower()] = d
            for aslug in ota.get("agoda_slugs", []):
                self._by_agoda_slug[aslug.lower()] = d
            for aid in ota.get("agoda_ids", []):
                self._by_agoda_id[str(aid)] = d
            for bslug in ota.get("booking_slugs", []):
                self._by_booking_slug[bslug.lower()] = d

    def find_by_aggregator_identity(self, platform: str, ota_id: str = "", ota_slug: str = "") -> Optional[Tuple[Dict, str]]:
        """O(1) closed-world deterministic lookup for aggregators with zero false positives."""
        if not self._cached_hotels:
            self._load_cache()

        if platform == "Trip.com":
            if ota_id and str(ota_id) in self._by_trip_id:
                return self._by_trip_id[str(ota_id)], "DETERMINISTIC_TRIP_ID_LINK"
            if ota_slug and ota_slug.lower() in self._by_trip_slug:
                return self._by_trip_slug[ota_slug.lower()], "DETERMINISTIC_TRIP_SLUG_LINK"
        elif platform == "Agoda":
            if ota_slug and ota_slug.lower() in self._by_agoda_slug:
                return self._by_agoda_slug[ota_slug.lower()], "DETERMINISTIC_AGODA_SLUG_LINK"
            if ota_id and str(ota_id) in self._by_agoda_id:
                return self._by_agoda_id[str(ota_id)], "DETERMINISTIC_AGODA_ID_LINK"
        elif platform == "Booking.com":
            if ota_slug and ota_slug.lower() in self._by_booking_slug:
                return self._by_booking_slug[ota_slug.lower()], "DETERMINISTIC_BOOKING_SLUG_LINK"

        return None

    def find_matches(self, hotel_name: str, province: Optional[str] = None, threshold: float = 0.50) -> List[Tuple[Dict, float]]:
        """Find potential VNAT candidates for a given hotel name using string/token matching."""
        if not self._cached_hotels:
            self._load_cache()

        input_norm = remove_accents(hotel_name)
        input_tokens = extract_core_tokens(hotel_name)
        norm_prov = remove_accents(province) if province else ""

        scored = []
        for h in self._cached_hotels:
            if norm_prov:
                prov_tokens = set(norm_prov.split())
                h_prov_tokens = set(h["prov_norm"].split()).union(set(h["addr_norm"].split()))
                if prov_tokens and not prov_tokens.intersection(h_prov_tokens):
                    continue

            cand_norm = h["name_norm"]
            cand_tokens = h["tokens"]

            if input_norm and (input_norm in cand_norm):
                final_score = max(0.85, len(input_norm) / len(cand_norm))
                h_clean = {k: v for k, v in h.items() if not k.endswith("_norm") and k != "tokens"}
                scored.append((h_clean, round(final_score, 3)))
                continue

            seq_score = SequenceMatcher(None, input_norm, cand_norm).ratio()
            token_score = 0.0
            if input_tokens and cand_tokens:
                intersection = input_tokens.intersection(cand_tokens)
                if intersection:
                    cand_coverage = len(intersection) / len(cand_tokens)
                    input_coverage = len(intersection) / len(input_tokens)
                    token_score = (cand_coverage * 0.7) + (input_coverage * 0.3)
                    if input_tokens.issubset(cand_tokens):
                        token_score = max(token_score, 0.88)

            final_score = (token_score * 0.70) + (seq_score * 0.30)

            if input_tokens and cand_tokens and cand_tokens.issubset(input_tokens) and seq_score >= 0.45:
                final_score = max(final_score, 0.90)

            if final_score >= threshold:
                h_clean = {k: v for k, v in h.items() if not k.endswith("_norm") and k != "tokens"}
                scored.append((h_clean, round(final_score, 3)))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def audit_property(self, property_data: Dict) -> Dict:
        raw_input = property_data.get("name", "")
        claimed_stars = int(property_data.get("claimed_stars", 0))
        has_dorm = property_data.get("has_dorm", False)
        room_count = property_data.get("room_count")
        province = property_data.get("province", "")
        ota_source = property_data.get("ota_source", "OTA")
        ota_url = property_data.get("ota_url", "")

        # If user passed a URL in name or ota_url
        parsed = parse_ota_url(ota_url or raw_input)
        effective_name = parsed["name"] if parsed["is_url"] else raw_input
        effective_platform = parsed["platform"] if parsed["is_url"] else ota_source

        # 1. Closed-World Deterministic Aggregator Identity Lookup
        matched_hotel = None
        match_type = "NONE"
        match_score = 0.0

        if parsed["is_url"]:
            det = self.find_by_aggregator_identity(parsed["platform"], parsed["ota_id"], parsed["ota_slug"])
            if det:
                matched_hotel, match_type = det
                match_score = 1.0

        # 2. Text/Fuzzy Resolution Fallback
        if not matched_hotel:
            matches = self.find_matches(effective_name, province=province or parsed["city"], threshold=0.70)
            if matches:
                matched_hotel, match_score = matches[0]
                match_type = "TOKEN_FUZZY_MATCH"

        if matched_hotel:
            official_stars = matched_hotel["stars"]
            if claimed_stars <= official_stars:
                status = "VERIFIED_LEGITIMATE"
                severity = "NONE"
                message = f"Legitimately accredited {official_stars}-star property under VNAT Decision."
            else:
                status = "STAR_INFLATION"
                severity = "HIGH"
                message = (f"Accredited as {official_stars}-star by VNAT, but {effective_platform} "
                           f"advertises {claimed_stars}-star (+{claimed_stars - official_stars} star inflation).")

            return {
                "input": property_data,
                "status": status,
                "severity": severity,
                "message": message,
                "confidence_score": match_score,
                "match_type": match_type,
                "official_record": matched_hotel,
                "all_matches": [matched_hotel]
            }

        # No match found in official VNAT 4/5-star database
        if has_dorm or (room_count is not None and room_count < 30):
            status = "BLATANT_HOSTEL_FRAUD"
            severity = "CRITICAL"
            details = []
            if has_dorm:
                details.append("Offers bunk beds / shared dormitory rooms")
            if room_count is not None and room_count < 30:
                details.append(f"Only {room_count} rooms (TCVN 4391:2015 requires min 80 for 4★, 100 for 5★)")
            
            message = (f"Backpacker hostel / budget lodging falsely sporting {claimed_stars} stars on {effective_platform}. "
                       f"Evidence: {'; '.join(details)}.")
        else:
            status = "UNACCREDITED_HOTEL"
            severity = "HIGH"
            message = (f"Claims {claimed_stars} stars on {effective_platform}, but does NOT exist in the "
                       f"official VNAT 4-star / 5-star national registry.")

        return {
            "input": property_data,
            "status": status,
            "severity": severity,
            "message": message,
            "confidence_score": 0.0,
            "match_type": "NONE",
            "official_record": None,
            "all_matches": []
        }
