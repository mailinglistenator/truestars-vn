#!/usr/bin/env python3
"""
Matching Engine: Entity resolution matching between OTA listings and
the official VNAT 4-star and 5-star accreditation registry.
"""

import os
import re
import sqlite3
import unicodedata
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "watchdog.db")

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

class MatchingEngine:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._cached_hotels = None
        self._load_cache()

    def _load_cache(self):
        """Pre-cache all 681 VNAT hotels in memory with normalized fields."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM vnat_hotels")
        rows = cur.fetchall()
        conn.close()

        self._cached_hotels = []
        for r in rows:
            d = dict(r)
            d["name_norm"] = remove_accents(d["name"])
            d["prov_norm"] = remove_accents(d["province"])
            d["addr_norm"] = remove_accents(d["address"])
            d["tokens"] = extract_core_tokens(d["name"])
            self._cached_hotels.append(d)

    def find_matches(self, hotel_name: str, province: Optional[str] = None, threshold: float = 0.50) -> List[Tuple[Dict, float]]:
        """
        Find potential VNAT candidates for a given hotel name.
        Returns list of (hotel_dict, similarity_score) sorted by score descending.
        """
        if not self._cached_hotels:
            self._load_cache()

        input_norm = remove_accents(hotel_name)
        input_tokens = extract_core_tokens(hotel_name)
        norm_prov = remove_accents(province) if province else ""

        scored = []
        for h in self._cached_hotels:
            # Check province match if specified
            if norm_prov:
                prov_tokens = set(norm_prov.split())
                h_prov_tokens = set(h["prov_norm"].split()).union(set(h["addr_norm"].split()))
                if prov_tokens and not prov_tokens.intersection(h_prov_tokens):
                    continue

            cand_norm = h["name_norm"]
            cand_tokens = h["tokens"]

            # 1. Exact or partial substring match boost
            if input_norm and (input_norm in cand_norm):
                # Search keyword directly inside official name
                final_score = max(0.85, len(input_norm) / len(cand_norm))
                h_clean = {k: v for k, v in h.items() if not k.endswith("_norm") and k != "tokens"}
                scored.append((h_clean, round(final_score, 3)))
                continue

            # 2. Sequence similarity
            seq_score = SequenceMatcher(None, input_norm, cand_norm).ratio()

            # 3. Token overlap on brand tokens
            token_score = 0.0
            if input_tokens and cand_tokens:
                intersection = input_tokens.intersection(cand_tokens)
                union = input_tokens.union(cand_tokens)
                if intersection:
                    cand_coverage = len(intersection) / len(cand_tokens)
                    input_coverage = len(intersection) / len(input_tokens)
                    token_score = (cand_coverage * 0.7) + (input_coverage * 0.3)
                    
                    # If all query tokens match (e.g. searching "metropole" or "furama")
                    if input_tokens.issubset(cand_tokens):
                        token_score = max(token_score, 0.88)

            final_score = (token_score * 0.70) + (seq_score * 0.30)

            # Substring exact brand containment check
            if input_tokens and cand_tokens and cand_tokens.issubset(input_tokens) and seq_score >= 0.45:
                final_score = max(final_score, 0.90)

            if final_score >= threshold:
                h_clean = {k: v for k, v in h.items() if not k.endswith("_norm") and k != "tokens"}
                scored.append((h_clean, round(final_score, 3)))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def audit_property(self, property_data: Dict) -> Dict:
        hotel_name = property_data.get("name", "")
        claimed_stars = int(property_data.get("claimed_stars", 0))
        has_dorm = property_data.get("has_dorm", False)
        room_count = property_data.get("room_count")
        province = property_data.get("province", "")
        ota_source = property_data.get("ota_source", "OTA")
        ota_url = property_data.get("ota_url", "")

        matches = self.find_matches(hotel_name, province=province, threshold=0.70)

        if matches:
            best_match, score = matches[0]
            official_stars = best_match["stars"]

            if claimed_stars <= official_stars:
                status = "VERIFIED_LEGITIMATE"
                severity = "NONE"
                message = f"Legitimately accredited {official_stars}-star property under VNAT Decision."
            else:
                status = "STAR_INFLATION"
                severity = "HIGH"
                message = (f"Accredited as {official_stars}-star by VNAT, but {ota_source} "
                           f"advertises {claimed_stars}-star (+{claimed_stars - official_stars} star inflation).")

            return {
                "input": property_data,
                "status": status,
                "severity": severity,
                "message": message,
                "confidence_score": score,
                "official_record": best_match,
                "all_matches": matches[:3]
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
            
            message = (f"Backpacker hostel / budget lodging falsely sporting {claimed_stars} stars on {ota_source}. "
                       f"Evidence: {'; '.join(details)}.")
        else:
            status = "UNACCREDITED_HOTEL"
            severity = "HIGH"
            message = (f"Claims {claimed_stars} stars on {ota_source}, but does NOT exist in the "
                       f"official VNAT 4-star / 5-star national registry.")

        return {
            "input": property_data,
            "status": status,
            "severity": severity,
            "message": message,
            "confidence_score": 0.0,
            "official_record": None,
            "all_matches": []
        }
