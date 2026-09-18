#!/usr/bin/env python3
"""
Enriches vnat_whitelist.json with:
1. english_name: Clean international English commercial hotel name.
2. english_location: Normalized English destination/city name.
3. ota_links: Direct high-fidelity links to Agoda, Booking.com, Trip.com, and Google Maps with affiliate tags.
"""

import json
import re
import os
import urllib.parse

AFFILIATE_CONFIG = {
    "agoda_cid": "1924567",
    "booking_aid": "8092145",
    "trip_alliance_id": "489210",
    "trip_sid": "1983940"
}

DIACRITICS_MAP = {
    "à":"a","á":"a","ả":"a","ã":"a","ạ":"a","ă":"a","ằ":"a","ắ":"a","ẳ":"a","ẵ":"a","ặ":"a",
    "â":"a","ầ":"a","ấ":"a","ẩ":"a","ẫ":"a","ậ":"a","è":"e","é":"e","ẻ":"e","ẽ":"e","ẹ":"e",
    "ê":"e","ề":"e","ế":"e","ể":"e","ễ":"e","ệ":"e","ì":"i","í":"i","ỉ":"i","ĩ":"i","ị":"i",
    "ò":"o","ó":"o","ỏ":"o","õ":"o","ọ":"o","ô":"o","ồ":"o","ố":"o","ổ":"o","ỗ":"o","ộ":"o",
    "ơ":"o","ờ":"o","ớ":"o","ở":"o","ỡ":"o","ợ":"o","ù":"u","ú":"u","ủ":"u","ũ":"u","ụ":"u",
    "ư":"u","ừ":"u","ứ":"u","ử":"u","ữ":"u","ự":"u","ỳ":"y","ý":"y","ỷ":"y","ỹ":"y","ỵ":"y",
    "đ":"d","Đ":"D"
}

def remove_accents(text):
    if not text:
        return ""
    return "".join(DIACRITICS_MAP.get(c, c) for c in text)

KNOWN_NAMES = {
    494: "Sofitel Legend Metropole Hanoi",
    1981: "Furama Resort Danang",
    49: "Caravelle Saigon",
    2051: "Rex Hotel Saigon",
    3007: "Hotel Continental Saigon",
    2010: "Vinpearl Resort & Spa Da Nang",
    2048: "Sheraton Saigon Hotel & Towers",
    2032: "Park Hyatt Saigon",
    2018: "The Reverie Saigon",
    2019: "InterContinental Saigon",
    2052: "Hotel Majestic Saigon",
    2053: "Grand Hotel Saigon",
    2020: "Pullman Saigon Centre",
    2021: "Le Meridien Saigon",
    2022: "Mia Saigon Luxury Boutique Hotel",
    2023: "Nikko Saigon Hotel",
    2024: "Lotte Hotel Saigon",
    495: "JW Marriott Hotel Hanoi",
    496: "Lotte Hotel Hanoi",
    497: "InterContinental Hanoi Westlake",
    498: "InterContinental Hanoi Landmark72",
    499: "Hanoi Daewoo Hotel",
    500: "Hotel de l'Opera Hanoi - MGallery",
    501: "Pan Pacific Hanoi",
    502: "Melia Hanoi Hotel",
    503: "Grand Plaza Hanoi Hotel",
    504: "Apricot Hotel Hanoi",
    505: "Silk Path Boutique Hotel Hanoi",
    1982: "InterContinental Danang Sun Peninsula Resort",
    1983: "Hyatt Regency Danang Resort and Spa",
    1984: "Four Points by Sheraton Danang",
    1985: "Novotel Danang Premier Han River",
    1986: "Pullman Danang Beach Resort",
    1987: "Hilton Da Nang",
    1988: "Grand Mercure Danang",
    1989: "Naman Retreat Danang",
    1990: "TMS Hotel Da Nang Beach",
    1991: "Muong Thanh Luxury Da Nang Hotel",
    2000: "Four Seasons Resort The Nam Hai, Hoi An",
    2001: "Anantara Hoi An Resort",
    2002: "Allegro Hoi An - A Little Luxury Hotel & Spa",
    2003: "La Siesta Hoi An Resort & Spa",
    2004: "Vinpearl Resort & Golf Nam Hoi An",
    2005: "Almanity Hoi An Wellness Resort",
    2006: "Bel Marina Hoi An Resort",
    2100: "Six Senses Ninh Van Bay",
    2101: "Vinpearl Resort Nha Trang",
    2102: "Vinpearl Resort & Spa Nha Trang Bay",
    2103: "Amiana Resort Nha Trang",
    2104: "InterContinental Nha Trang",
    2105: "Sheraton Nha Trang Hotel & Spa",
    2106: "Mia Resort Nha Trang",
    2107: "Boma Resort Nha Trang",
    2200: "JW Marriott Phu Quoc Emerald Bay Resort & Spa",
    2201: "Regent Phu Quoc",
    2202: "InterContinental Phu Quoc Long Beach Resort",
    2203: "Premier Village Phu Quoc Resort",
    2204: "Salinda Resort Phu Quoc Island",
    2205: "La Veranda Resort Phu Quoc - MGallery",
    2206: "Vinpearl Resort & Spa Phu Quoc",
    2207: "Vinpearl Wonderworld Phu Quoc",
    2208: "Crowne Plaza Phu Quoc Starbay",
    2209: "Novotel Phu Quoc Resort",
    2210: "Pullman Phu Quoc Beach Resort",
    2211: "Best Western Premier Sonasea Phu Quoc",
    2300: "FLC Grand Hotel Halong",
    2301: "Vinpearl Resort & Spa Ha Long",
    2302: "Muong Thanh Luxury Ha Long Centre Hotel",
    2303: "Wyndham Legend Halong",
    2400: "The Grand Ho Tram Strip",
    2401: "Melia Ho Tram Beach Resort",
    2402: "Imperial Hotel Vung Tau",
    2403: "Pullman Vung Tau",
    2500: "Dalat Palace Heritage Hotel",
    2501: "Ana Mandara Villas Dalat Resort & Spa",
    2502: "Dalat Edensee Lake Resort & Spa",
    2503: "Swiss-Belresort Tuyen Lam Dalat",
    2600: "Azerai La Residence Hue",
    2601: "Silk Path Grand Hue Hotel",
    2602: "Melia Vinpearl Hue",
    2700: "Hotel de la Coupole - MGallery Sapa",
    2701: "Silk Path Grand Resort & Spa Sapa",
    2800: "Anantara Mui Ne Resort",
    2801: "The Cliff Resort & Residences Phan Thiet",
    2802: "Victoria Phan Thiet Beach Resort & Spa",
    2803: "Centara Mirage Resort Mui Ne",
    8088: "Meliá Vinpearl Danang Riverfront",
    7960: "Vinpearl Landmark 81, Autograph Collection"
}

def get_english_location(h):
    full = f"{h.get('province', '')} {h.get('address', '')}".lower()
    full_norm = remove_accents(full)

    if "ha noi" in full_norm or "hanoi" in full_norm:
        return "Hanoi"
    if "ho chi minh" in full_norm or "sai gon" in full_norm or "saigon" in full_norm:
        return "Ho Chi Minh City"
    if "da nang" in full_norm or "danang" in full_norm:
        return "Da Nang"
    if "nha trang" in full_norm or "khanh hoa" in full_norm:
        return "Nha Trang (Khanh Hoa)"
    if "phu quoc" in full_norm or "kien giang" in full_norm:
        return "Phu Quoc Island"
    if "hoi an" in full_norm or "quang nam" in full_norm:
        return "Hoi An (Quang Nam)"
    if "ha long" in full_norm or "quang ninh" in full_norm:
        return "Ha Long (Quang Ninh)"
    if "vung tau" in full_norm or "ba ria" in full_norm or "ho tram" in full_norm:
        return "Vung Tau / Ho Tram"
    if "da lat" in full_norm or "dalat" in full_norm or "lam dong" in full_norm:
        return "Da Lat"
    if "hue" in full_norm or "thua thien" in full_norm:
        return "Hue"
    if "phan thiet" in full_norm or "mui ne" in full_norm or "binh thuan" in full_norm:
        return "Phan Thiet / Mui Ne"
    if "hai phong" in full_norm or "cat ba" in full_norm:
        return "Hai Phong / Cat Ba"
    if "sa pa" in full_norm or "sapa" in full_norm or "lao cai" in full_norm:
        return "Sapa (Lao Cai)"
    if "quy nhon" in full_norm or "binh dinh" in full_norm:
        return "Quy Nhon"
    if "can tho" in full_norm:
        return "Can Tho"
    if "ninh binh" in full_norm:
        return "Ninh Binh"
    if "dong hoi" in full_norm or "quang binh" in full_norm:
        return "Quang Binh (Dong Hoi)"
    if "bac ninh" in full_norm:
        return "Bac Ninh"
    if "nghe an" in full_norm or "vinh" in full_norm:
        return "Nghe An (Vinh)"
    if "thanh hoa" in full_norm or "sam son" in full_norm:
        return "Thanh Hoa (Sam Son)"
    if "phu tho" in full_norm or "viet tri" in full_norm:
        return "Phu Tho (Viet Tri)"
    if "phu yen" in full_norm or "tuy hoa" in full_norm:
        return "Phu Yen (Tuy Hoa)"
    if "binh duong" in full_norm or "thu dau mot" in full_norm:
        return "Binh Duong"
    if "dong nai" in full_norm or "bien hoa" in full_norm:
        return "Dong Nai (Bien Hoa)"
    if "vinh phuc" in full_norm or "dai lai" in full_norm or "tam dao" in full_norm:
        return "Vinh Phuc (Tam Dao)"
    if "ha tinh" in full_norm:
        return "Ha Tinh"
    if "ben tre" in full_norm:
        return "Ben Tre"
    if "buon ma thuot" in full_norm or "dac lak" in full_norm:
        return "Dak Lak (Buon Ma Thuot)"
    if "ca mau" in full_norm:
        return "Ca Mau"
    if "lang son" in full_norm:
        return "Lang Son"
    if "ha giang" in full_norm:
        return "Ha Giang"
    if "son la" in full_norm or "moc chau" in full_norm:
        return "Son La (Moc Chau)"
    if "ninh thuan" in full_norm or "phan rang" in full_norm:
        return "Ninh Thuan (Phan Rang)"
    if "quang tri" in full_norm or "dong ha" in full_norm:
        return "Quang Tri"
    if "quang ngai" in full_norm:
        return "Quang Ngai"
    if "an giang" in full_norm or "rach gia" in full_norm or "chau doc" in full_norm:
        return "An Giang / Rach Gia"
    if "tay ninh" in full_norm:
        return "Tay Ninh"
    if "pleiku" in full_norm or "gia lai" in full_norm:
        return "Gia Lai (Pleiku)"
    if "hoa binh" in full_norm:
        return "Hoa Binh"
    if "hai duong" in full_norm:
        return "Hai Duong"
    if "cao bang" in full_norm:
        return "Cao Bang"
    if "lai chau" in full_norm:
        return "Lai Chau"
    if "ha nam" in full_norm or "phu ly" in full_norm:
        return "Ha Nam"

    prov = h.get("province", "")
    if prov:
        return re.sub(r"^(thành phố|tỉnh)\s+", "", prov, flags=re.I).strip()
    return "Vietnam"

def generate_english_name(h):
    raw_name = h.get("name", "").strip()
    prop_type = h.get("property_type", "").strip()

    is_resort = bool(re.search(r"nghỉ dưỡng|resort", raw_name, re.I) or re.search(r"resort", prop_type, re.I))
    is_villa = bool(re.search(r"biệt thự|villa", raw_name, re.I) or re.search(r"villa", prop_type, re.I))
    is_apt = bool(re.search(r"căn hộ|apartment|condotel|suites", raw_name, re.I))

    clean = re.sub(
        r"^(khách sạn nghỉ dưỡng|khu nghỉ dưỡng và giải trí quốc tế|khu du lịch nghỉ dưỡng|khách sạn du lịch nghỉ dưỡng|quần thể nghỉ dưỡng|khu nghỉ mát|khu nghỉ dưỡng|khách sạn|căn hộ du lịch|biệt thự du lịch|nhà nghỉ du lịch|khu căn hộ cao cấp)\s+",
        "",
        raw_name,
        flags=re.I
    ).strip()

    # Convert diacritics
    eng = remove_accents(clean)

    # Clean punctuation and spacing
    eng = re.sub(r"[-–—_]+", " ", eng)
    eng = re.sub(r"\s+", " ", eng).strip()

    # Brand fixes
    eng = re.sub(r"\bMuong Thanh\b", "Muong Thanh", eng, flags=re.I)
    eng = re.sub(r"\bVinpearl\b", "Vinpearl", eng, flags=re.I)
    eng = re.sub(r"\bMelia\b", "Melia", eng, flags=re.I)
    eng = re.sub(r"\bHa Noi\b", "Hanoi", eng, flags=re.I)
    eng = re.sub(r"\bDa Nang\b", "Danang", eng, flags=re.I)
    eng = re.sub(r"\bSai Gon\b", "Saigon", eng, flags=re.I)
    eng = re.sub(r"\bNha Trang\b", "Nha Trang", eng, flags=re.I)
    eng = re.sub(r"\bPhu Quoc\b", "Phu Quoc", eng, flags=re.I)
    eng = re.sub(r"\bHoi An\b", "Hoi An", eng, flags=re.I)
    eng = re.sub(r"\bHa Long\b", "Ha Long", eng, flags=re.I)
    eng = re.sub(r"\bVung Tau\b", "Vung Tau", eng, flags=re.I)
    eng = re.sub(r"\bDa Lat\b", "Dalat", eng, flags=re.I)
    eng = re.sub(r"\bLao Cai\b", "Lao Cai", eng, flags=re.I)
    eng = re.sub(r"\bHai Phong\b", "Hai Phong", eng, flags=re.I)

    # Title-case words
    words = eng.split()
    capitalized = []
    for w in words:
        if w.lower() in ["and", "&", "de", "l'", "the", "of", "in", "by"]:
            capitalized.append(w.lower())
        elif w.isupper() and len(w) <= 4:
            capitalized.append(w)
        else:
            capitalized.append(w.capitalize())
    eng = " ".join(capitalized)

    # Append category suffix if missing
    if is_resort and not re.search(r"resort|retreat|spa|village|palace|oasis", eng, re.I):
        eng += " Resort"
    elif is_villa and not re.search(r"villa", eng, re.I):
        eng += " Villas"
    elif is_apt and not re.search(r"apartment|suite|condo", eng, re.I):
        eng += " Suites & Apartments"
    elif not is_resort and not is_villa and not is_apt and not re.search(r"hotel|plaza|palace|residence|lodge|tower|suites", eng, re.I):
        eng += " Hotel"

    return eng

def pick_best_slug(slugs, name):
    if not slugs:
        return ""
    norm_name = remove_accents(name).lower()
    first_word = norm_name.split()[0] if norm_name else ""
    good = [s for s in slugs if not re.search(r"condotel|villas|suites|apartments|condo", s, re.I)]
    pool = good if good else slugs
    pool.sort(key=lambda s: (
        0 if s.startswith(first_word) else 1,
        0 if "resort" in s and "resort" in norm_name else 1,
        len(s)
    ))
    return pool[0]

def generate_ota_links_for_hotel(h, eng_name, eng_loc, is_curated=False, curated_entry=None):
    cid = AFFILIATE_CONFIG["agoda_cid"]
    aid = AFFILIATE_CONFIG["booking_aid"]
    trip_aid = AFFILIATE_CONFIG["trip_alliance_id"]
    trip_sid = AFFILIATE_CONFIG["trip_sid"]

    q = urllib.parse.quote_plus(f"{eng_name} {eng_loc}".strip())

    # Agoda URL
    if is_curated and curated_entry and curated_entry.get("direct_agoda_url"):
        agoda_url = curated_entry["direct_agoda_url"]
    elif is_curated and curated_entry and curated_entry.get("agoda_slugs"):
        best_slug = curated_entry["agoda_slugs"][0]
        agoda_url = f"https://www.agoda.com/{best_slug}/hotel/vietnam.html?cid={cid}"
    elif is_curated and curated_entry and curated_entry.get("agoda_ids"):
        agoda_url = f"https://www.agoda.com/partners/partnersearch.aspx?cid={cid}&hl=en-us&pcs=1&hid={curated_entry['agoda_ids'][0]}"
    else:
        agoda_url = f"https://www.google.com/search?q=site%3Aagoda.com+{q}"

    # Booking.com URL
    if is_curated and curated_entry and curated_entry.get("direct_booking_url"):
        booking_url = curated_entry["direct_booking_url"]
    elif is_curated and curated_entry and curated_entry.get("booking_slugs"):
        booking_url = f"https://www.booking.com/hotel/vn/{curated_entry['booking_slugs'][0]}.html?aid={aid}"
    else:
        booking_url = f"https://www.booking.com/searchresults.html?ss={q}&aid={aid}"

    # Trip.com URL
    if is_curated and curated_entry and curated_entry.get("direct_trip_url"):
        trip_url = curated_entry["direct_trip_url"]
    elif is_curated and curated_entry and curated_entry.get("trip_ids"):
        trip_url = f"https://www.trip.com/hotels/detail/?hotelId={curated_entry['trip_ids'][0]}&Allianceid={trip_aid}&SID={trip_sid}"
    else:
        trip_url = f"https://www.trip.com/hotels/list?keyword={q}&Allianceid={trip_aid}&SID={trip_sid}"

    # Google Maps URL - DIRECT PLACE CARD (Never generic search list)
    if is_curated and curated_entry and curated_entry.get("direct_maps_url"):
        maps_url = curated_entry["direct_maps_url"]
    else:
        maps_q = urllib.parse.quote_plus(f"{eng_name} {h.get('address', eng_loc)}".strip())
        maps_url = f"https://www.google.com/maps/place/{maps_q}/"

    return {
        "agoda": {
            "name": "Agoda",
            "url": agoda_url,
            "badge": "🟧 Agoda ↗"
        },
        "booking": {
            "name": "Booking.com",
            "url": booking_url,
            "badge": "🟦 Booking.com ↗"
        },
        "trip": {
            "name": "Trip.com",
            "url": trip_url,
            "badge": "🟨 Trip.com ↗"
        },
        "google_maps": {
            "name": "Google Maps",
            "url": maps_url,
            "badge": "🗺️ Maps ↗"
        }
    }

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    wl_path = os.path.join(base_dir, "public", "vnat_whitelist.json")
    data_wl_path = os.path.join(base_dir, "data", "vnat_whitelist.json")
    curated_path = os.path.join(base_dir, "data", "ota_curated_mappings.json")

    with open(wl_path, "r", encoding="utf-8") as f:
        whitelist = json.load(f)

    curated = {}
    if os.path.exists(curated_path):
        with open(curated_path, "r", encoding="utf-8") as f:
            curated = json.load(f)

    for h in whitelist:
        item_id = str(h.get("item_id", ""))
        is_curated = item_id in curated
        curated_entry = curated.get(item_id)
        if is_curated:
            c = curated_entry
            if "ota_identities" not in h or not h["ota_identities"]:
                h["ota_identities"] = {}
            for k, vals in c.items():
                if vals and isinstance(vals, list):
                    existing = h["ota_identities"].get(k, [])
                    h["ota_identities"][k] = list(set(existing + vals))

        eng_loc = get_english_location(h)
        eng_name = generate_english_name(h)
        if is_curated and curated_entry:
            if curated_entry.get("commercial_name"):
                eng_name = curated_entry["commercial_name"]
            if curated_entry.get("former_name"):
                h["former_name"] = curated_entry["former_name"]
            h["commercial_name"] = curated_entry.get("commercial_name", eng_name)

        ota_links = generate_ota_links_for_hotel(h, eng_name, eng_loc, is_curated=is_curated, curated_entry=curated_entry)

        h["english_name"] = eng_name
        h["english_location"] = eng_loc
        h["ota_links"] = ota_links
        h["direct_agoda_url"] = ota_links["agoda"]["url"]
        h["direct_booking_url"] = ota_links["booking"]["url"]
        h["direct_trip_url"] = ota_links["trip"]["url"]
        h["direct_maps_url"] = ota_links["google_maps"]["url"]

    # Write enriched list back to public, data, and extension
    with open(wl_path, "w", encoding="utf-8") as f:
        json.dump(whitelist, f, ensure_ascii=False, indent=2)

    if os.path.exists(os.path.dirname(data_wl_path)):
        with open(data_wl_path, "w", encoding="utf-8") as f:
            json.dump(whitelist, f, ensure_ascii=False, indent=2)

    ext_wl_path = os.path.join(base_dir, "extension", "data", "vnat_whitelist.json")
    if os.path.exists(os.path.dirname(ext_wl_path)):
        with open(ext_wl_path, "w", encoding="utf-8") as f:
            json.dump(whitelist, f, ensure_ascii=False, indent=2)

    print(f"Successfully enriched {len(whitelist)} hotels with English names, destinations, and OTA links!")
    print(f"Sample hotel 0: {whitelist[0]['name']} -> {whitelist[0]['english_name']} ({whitelist[0]['english_location']})")
    print(f"Sample hotel 0 Agoda: {whitelist[0]['ota_links']['agoda']['url']}")
    print(f"Sample hotel 1: {whitelist[1]['name']} -> {whitelist[1]['english_name']} ({whitelist[1]['english_location']})")
    print(f"Sample hotel 1 Agoda: {whitelist[1]['ota_links']['agoda']['url']}")

if __name__ == "__main__":
    main()
