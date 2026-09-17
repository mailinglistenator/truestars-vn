# Chrome Web Store Submission & Publishing Package
## TrueStars VN — Hotel Star Rating Watchdog

*Last Updated: 2026-09-17*  
*Version: 1.0.0*

---

## 1. Store Listing Metadata

* **Extension Name**: TrueStars VN — Hotel Star Rating Watchdog
* **Short Description** (Max 132 chars):  
  Exposes fake and unaccredited 4★ and 5★ hotels on Agoda, Booking.com, and Trip.com using official Vietnam government records.
* **Category**: Travel / Shopping
* **Primary Language**: English (also suitable for Vietnamese)

### Detailed Description (CWS Markdown Format)

```markdown
Never get misled by unaccredited hotel ratings again when booking accommodations in Vietnam.

TrueStars VN is an independent consumer protection watchdog that instantly verifies hotel star claims on Online Travel Agencies (Agoda, Booking.com, and Trip.com) against the official statutory accreditation registry of the Vietnam National Authority of Tourism (VNAT).

WHY DO YOU NEED TRUESTARS VN?
Under Vietnamese law (Law on Tourism 2017 & TCVN 4391:2015), only the Ministry of Tourism can award 4-star and 5-star hotel ratings. Nationwide, only 681 hotels hold genuine accreditation. Yet on popular booking aggregators, thousands of properties—including party hostels with bunk beds and narrow tube homestays—display 4 or 5 golden stars.

KEY FEATURES:
🛡️ Instant Verification Badges: As you browse search results on Agoda, Booking.com, or Trip.com, TrueStars VN displays a color-coded status right on the hotel card:
  • 🟢 VNAT Certified: Officially accredited 4★ or 5★ luxury hotel.
  • 🚨 Hostel / Dorm Alert: Flags budget dorms and backpacker lodgings claiming luxury stars.
  • 🟡 Star Inflation: Flags hotels officially certified for 4 stars but advertised as 5 stars.
  • 🔴 Unaccredited: Flags properties claiming 4 or 5 stars without any official government accreditation.

🔍 Complete Registry Search: Look up any hotel in Vietnam directly from the extension popup to check its accredited star level, verified room count, and official location.

⚖️ Statutory Dossier: Click any badge to view the applicable legal standards under Vietnam's Law on Tourism 2017 and national hospitality standards.

🔒 Complete Privacy: TrueStars VN contains the full official whitelist offline inside the extension. Your browsing history is never tracked, stored, or sent to external servers.
```

---

## 2. Permissions Justification

| Permission / Host | Plain-English Reason for Chrome Web Store Reviewers |
| :--- | :--- |
| **`storage`** | Used exclusively to save local user preferences, such as badge display toggles and alert dismissal states. No personal data is stored. |
| **`tabs`** | Required to identify the hotel name from the active tab's title when the user clicks the extension popup on a booking site to show instant audit results. |
| **`*://*.agoda.com/*`** | Required to display verification badges on hotel search cards and listing headers on Agoda. |
| **`*://*.booking.com/*`** | Required to display verification badges on hotel search cards and property pages on Booking.com. |
| **`*://*.trip.com/*`** | Required to display verification badges on hotel search cards and listing headers on Trip.com. |

---

## 3. Privacy Policy & Data Handling Disclosure

* **Single Purpose Statement**: TrueStars VN exists solely to protect consumers from misleading hotel star ratings in Vietnam by displaying official government accreditation badges on travel booking sites.
* **Data Collection**: **Zero data collected.** TrueStars VN does not collect, track, or transmit any user information, booking details, personal identity, search queries, or analytics.
* **Offline Verification**: All verification matching occurs 100% locally within the user's browser using the bundled official government registry snapshot.

---

## 4. Packaging & Publishing Instructions

To produce the production upload `.zip` file:

```bash
cd /home/redking/Projects/vn_hotel_star_watchdog
python3 scripts/package_extension.py
```

This validates all icons and files, and generates:
* `extension.zip` ready for upload to the [Chrome Developer Dashboard](https://chrome.google.com/webstore/devconsole).
* Also copies `truestars_extension.zip` into `public/` so web dashboard visitors can download and install it in Developer Mode.
