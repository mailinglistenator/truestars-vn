#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.audit_service import AuditService

class TestAuditService(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.service = AuditService()

    def test_verified_legitimate_metropole(self):
        result = self.service.audit_property({
            "name": "Sofitel Legend Metropole Hanoi Hotel",
            "claimed_stars": 5,
            "province": "Hanoi",
            "ota_source": "Agoda"
        })
        self.assertEqual(result["status"], "VERIFIED_LEGITIMATE")
        self.assertEqual(result["severity"], "NONE")
        self.assertEqual(result["official_record"]["stars"], 5)
        self.assertFalse(result["legal_dossier"]["is_violation"])

    def test_verified_legitimate_furama_danang(self):
        result = self.service.audit_property({
            "name": "Furama Resort Danang",
            "claimed_stars": 5,
            "province": "Danang",
            "ota_source": "Booking.com"
        })
        self.assertEqual(result["status"], "VERIFIED_LEGITIMATE")
        self.assertEqual(result["official_record"]["stars"], 5)

    def test_star_inflation_downgraded_match(self):
        matches = self.service.search_vnat("Continental Saigon")
        if matches:
            official = matches[0][0]
            result = self.service.audit_property({
                "name": "Continental Saigon Hotel",
                "claimed_stars": 5,
                "province": "Saigon",
                "ota_source": "Trip.com"
            })
            if official["stars"] == 4:
                self.assertEqual(result["status"], "STAR_INFLATION")
                self.assertEqual(result["severity"], "HIGH")
                self.assertTrue(result["legal_dossier"]["is_violation"])

    def test_blatant_hostel_fraud_with_dorm(self):
        result = self.service.audit_property({
            "name": "Hanoi Old Quarter Backpacker Haven",
            "claimed_stars": 5,
            "has_dorm": True,
            "room_count": 12,
            "province": "Hanoi",
            "ota_source": "Agoda"
        })
        self.assertEqual(result["status"], "BLATANT_HOSTEL_FRAUD")
        self.assertEqual(result["severity"], "CRITICAL")
        self.assertTrue(result["legal_dossier"]["is_violation"])
        self.assertIn("Luật Du lịch 2017", result["legal_dossier"]["statutory_violations"][0]["law"])
        self.assertIn("TCVN 4391:2015", result["legal_dossier"]["formal_notice_text"])

    def test_unaccredited_private_hotel(self):
        result = self.service.audit_property({
            "name": "Dragon Backpacker Guesthouse & Rooms",
            "claimed_stars": 5,
            "has_dorm": False,
            "room_count": 45,
            "ota_source": "Agoda"
        })
        self.assertEqual(result["status"], "UNACCREDITED_HOTEL")
        self.assertEqual(result["severity"], "HIGH")
        self.assertTrue(result["legal_dossier"]["is_violation"])

    def test_deterministic_ota_identity_links(self):
        # 1. Trip.com exact ID
        res_trip = self.service.audit_property({
            "name": "https://www.trip.com/hotels/detail/?cityEnName=Hanoi&hotelId=678508",
            "claimed_stars": 5
        })
        self.assertEqual(res_trip["status"], "VERIFIED_LEGITIMATE")
        self.assertEqual(res_trip["match_type"], "DETERMINISTIC_TRIP_ID_LINK")
        self.assertEqual(res_trip["official_record"]["stars"], 5)

        # 2. Agoda exact slug
        res_agoda = self.service.audit_property({
            "name": "https://www.agoda.com/furama-resort-danang/hotel/da-nang-vn.html",
            "claimed_stars": 5
        })
        self.assertEqual(res_agoda["status"], "VERIFIED_LEGITIMATE")
        self.assertEqual(res_agoda["match_type"], "DETERMINISTIC_AGODA_SLUG_LINK")

        # 3. Booking.com exact slug
        res_booking = self.service.audit_property({
            "name": "https://www.booking.com/hotel/vn/caravelle.html",
            "claimed_stars": 5
        })
        self.assertEqual(res_booking["status"], "VERIFIED_LEGITIMATE")
        self.assertEqual(res_booking["match_type"], "DETERMINISTIC_BOOKING_SLUG_LINK")

        # 4. Agoda star inflation
        res_inf = self.service.audit_property({
            "name": "https://www.agoda.com/avani-hai-phong-harbour-view-hotel/hotel/hai-phong-vn.html",
            "claimed_stars": 5
        })
        self.assertEqual(res_inf["status"], "STAR_INFLATION")
        self.assertEqual(res_inf["match_type"], "DETERMINISTIC_AGODA_SLUG_LINK")

        # 5. Unaccredited URL
        res_unacc = self.service.audit_property({
            "name": "https://www.booking.com/hotel/vn/unregistered-scam-hotel.html",
            "claimed_stars": 5
        })
        self.assertEqual(res_unacc["status"], "UNACCREDITED_HOTEL")

if __name__ == "__main__":
    unittest.main()

