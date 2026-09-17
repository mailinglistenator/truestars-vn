import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
#!/usr/bin/env python3
"""
Audit Service: Orchestrates OTA fetching, fuzzy matching against VNAT whitelist,
and legal notice generation.
"""

import re
from typing import Dict
from src.matching_engine import MatchingEngine
from src.legal_engine import LegalEngine
from src.ota_parsers.agoda_parser import AgodaParser
from src.ota_parsers.booking_parser import BookingParser
from src.ota_parsers.trip_parser import TripParser

class AuditService:
    def __init__(self):
        self.matcher = MatchingEngine()

    def audit_url(self, url: str, override_stars: int = None, override_dorms: bool = None) -> Dict:
        """Fetch and audit an OTA URL (Agoda, Booking.com, Trip.com)."""
        url_lower = url.lower()
        if "agoda.com" in url_lower:
            parsed = AgodaParser.fetch_and_parse(url)
        elif "booking.com" in url_lower:
            parsed = BookingParser.fetch_and_parse(url)
        elif "trip.com" in url_lower:
            parsed = TripParser.fetch_and_parse(url)
        else:
            # Generic parser
            slug = url.split("?")[0].rstrip("/").split("/")[-1].replace("-", " ").title()
            parsed = {
                "ota_source": "Generic OTA",
                "ota_url": url,
                "name": slug,
                "claimed_stars": 4,
                "room_count": None,
                "has_dorm": False,
                "address": "",
                "province": ""
            }

        if override_stars is not None:
            parsed["claimed_stars"] = override_stars
        if override_dorms is not None:
            parsed["has_dorm"] = override_dorms

        return self.audit_property(parsed)

    def audit_property(self, property_data: Dict) -> Dict:
        """Run audit on structured property dictionary."""
        audit_res = self.matcher.audit_property(property_data)
        legal_notice = LegalEngine.generate_legal_notice(audit_res)
        
        audit_res["legal_dossier"] = legal_notice
        return audit_res

    def search_vnat(self, query: str, province: str = ""):
        """Search the official VNAT whitelist directly."""
        return self.matcher.find_matches(query, province=province, threshold=0.50)

if __name__ == "__main__":
    service = AuditService()
    # Test with a real legitimate hotel
    print("--- Test 1: Sofitel Metropole Hanoi (Legitimate 5-Star) ---")
    res1 = service.audit_property({
        "name": "Sofitel Legend Metropole Hanoi",
        "claimed_stars": 5,
        "province": "Hà Nội",
        "has_dorm": False,
        "ota_source": "Agoda"
    })
    print("Status:", res1["status"])
    print("Official Record:", res1["official_record"]["name"], f"({res1['official_record']['stars']}★)")
    
    print("\n--- Test 2: Backpacker Hostel claiming 5 stars ---")
    res2 = service.audit_property({
        "name": "Hanoi Old Quarter Backpacker Central Hostel",
        "claimed_stars": 5,
        "province": "Hà Nội",
        "has_dorm": True,
        "room_count": 14,
        "ota_source": "Agoda"
    })
    print("Status:", res2["status"])
    print("Severity:", res2["severity"])
    print("Message:", res2["message"])
    print("Legal breach:", res2["legal_dossier"]["statutory_violations"][0]["law"])
