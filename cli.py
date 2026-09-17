#!/usr/bin/env python3
"""
CLI Tool: Vietnam Hotel Star Rating Watchdog
Audit any Agoda, Booking.com, or Trip.com URL or search the VNAT statutory whitelist.
"""

import sys
import os
import argparse
import json

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from src.audit_service import AuditService

def print_result(audit: dict, verbose: bool = False):
    status = audit["status"]
    inp = audit["input"]
    legal = audit.get("legal_dossier", {})
    
    colors = {
        "VERIFIED_LEGITIMATE": "\033[92m", # Green
        "STAR_INFLATION": "\033[93m",      # Yellow
        "UNACCREDITED_HOTEL": "\033[91m",  # Red
        "BLATANT_HOSTEL_FRAUD": "\033[95m" # Magenta
    }
    reset = "\033[0m"
    bold = "\033[1m"
    color = colors.get(status, reset)

    print("\n" + "=" * 70)
    print(f"{bold}HOTEL AUDIT VERDICT: {color}{status}{reset}")
    print("=" * 70)
    print(f"{bold}Property Name:{reset}     {inp.get('name')}")
    print(f"{bold}Platform:{reset}          {inp.get('ota_source', 'OTA')}")
    print(f"{bold}Claimed Stars:{reset}     {'★' * inp.get('claimed_stars', 0)} ({inp.get('claimed_stars')} Stars)")
    
    if audit.get("official_record"):
        rec = audit["official_record"]
        print(f"{bold}Official VNAT:{reset}     {'★' * rec['stars']} ({rec['stars']} Stars) - {rec['name']}")
        print(f"{bold}Certified Address:{reset} {rec['address']}")
        print(f"{bold}Official Rooms:{reset}    {rec.get('room_count') or 'N/A'}")
    else:
        print(f"{bold}Official VNAT:{reset}     \033[91mNOT IN NATIONAL REGISTRY (0 Stars Certified)\033[0m")

    print(f"\n{bold}Audit Finding:{reset}     {audit['message']}")
    
    if legal.get("is_violation"):
        print(f"\n{bold}Statutory Violations:{reset}")
        for v in legal.get("statutory_violations", []):
            print(f"  • {bold}{v['law']}{reset}: {v['statute_title']}")
            print(f"    Application: {v['application']}")

        print(f"\n{bold}Statutory Penalties Applicable:{reset}")
        for p in legal.get("penalties", []):
            print(f"  ⚠ {p}")

    if verbose and legal.get("formal_notice_text"):
        print("\n" + "-" * 70)
        print(legal["formal_notice_text"])

    print("=" * 70 + "\n")

def main():
    parser = argparse.ArgumentParser(description="Vietnam Hotel Star Rating Watchdog CLI")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Command: check
    check_p = subparsers.add_parser("check", help="Audit an OTA URL or manual property details")
    check_p.add_argument("url_or_name", help="OTA URL (Agoda, Booking, Trip) or hotel name")
    check_p.add_argument("--stars", type=int, default=None, help="Override/specify claimed stars (e.g. 5)")
    check_p.add_argument("--dorm", action="store_true", help="Flag that property offers dorm/bunk beds")
    check_p.add_argument("--rooms", type=int, default=None, help="Total room count")
    check_p.add_argument("--province", type=str, default="", help="City/Province (e.g. Hanoi, Danang)")
    check_p.add_argument("--source", type=str, default="Agoda", help="OTA platform name")
    check_p.add_argument("--json", action="store_true", help="Output raw JSON")
    check_p.add_argument("-v", "--verbose", action="store_true", help="Print full statutory notice text")

    # Command: search
    search_p = subparsers.add_parser("search", help="Search the official VNAT 4★/5★ whitelist")
    search_p.add_argument("query", help="Hotel name keyword (e.g. Metropole, Vinpearl, InterContinental)")
    search_p.add_argument("--province", type=str, default="", help="Filter by province")

    # Command: stats
    subparsers.add_parser("stats", help="Display statutory database statistics")

    args = parser.parse_args()
    service = AuditService()

    if args.command == "check":
        target = args.url_or_name
        if target.startswith("http://") or target.startswith("https://"):
            audit = service.audit_url(target, override_stars=args.stars, override_dorms=args.dorm if args.dorm else None)
        else:
            prop = {
                "name": target,
                "claimed_stars": args.stars if args.stars is not None else 5,
                "has_dorm": args.dorm,
                "room_count": args.rooms,
                "province": args.province,
                "ota_source": args.source
            }
            audit = service.audit_property(prop)

        if args.json:
            print(json.dumps(audit, ensure_ascii=False, indent=2))
        else:
            print_result(audit, verbose=args.verbose)

    elif args.command == "search":
        matches = service.search_vnat(args.query, province=args.province)
        print(f"\nFound {len(matches)} matches in official VNAT database for '{args.query}':\n")
        for h, score in matches[:10]:
            print(f"[{score:.2f}] {'★' * h['stars']} {h['name']}")
            print(f"       Address: {h['address']}")
            print(f"       Rooms: {h['room_count'] or 'N/A'} | Phone: {h['phone'] or 'N/A'}\n")

    elif args.command == "stats":
        matches5 = service.matcher.find_matches("", threshold=0.0)
        c5 = sum(1 for h, _ in matches5 if h["stars"] == 5)
        c4 = sum(1 for h, _ in matches5 if h["stars"] == 4)
        print("\n" + "=" * 50)
        print("VIETNAM NATIONAL TOURISM AUTHORITY (VNAT) STATS")
        print("=" * 50)
        print(f"Total Certified 5-Star Hotels: {c5}")
        print(f"Total Certified 4-Star Hotels: {c4}")
        print(f"Total Legitimate Whitelist:   {len(matches5)}")
        print("=" * 50 + "\n")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
