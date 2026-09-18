const fs = require('fs');
const path = require('path');
const { TrueStarsMatcher, parseOtaUrl, isVietnamContext } = require('../public/matching_engine.js');

const data = JSON.parse(fs.readFileSync(path.join(__dirname, '../public/vnat_whitelist.json'), 'utf8'));
const matcher = new TrueStarsMatcher(data);

const testCases = [
  // 1. Exact Name Matching Tests
  {
    name: "Sofitel Legend Metropole Hanoi",
    stars: 5,
    expected: "VERIFIED_LEGITIMATE"
  },
  {
    name: "Furama Resort Danang",
    stars: 5,
    expected: "VERIFIED_LEGITIMATE"
  },
  {
    name: "Avani Hai Phong Harbour View",
    stars: 5,
    expected: "STAR_INFLATION"
  },
  {
    name: "Hanoi Central Backpacker Hostel",
    stars: 5,
    expected: "UNACCREDITED_HOTEL",
    expectViolation: true
  },
  {
    name: "Fake Luxury Penthouse Hanoi",
    stars: 5,
    expected: "UNACCREDITED_HOTEL"
  },

  // 2. Closed-World OTA Aggregator Identity Link Tests (Zero False Positives)
  {
    url: "https://www.trip.com/hotels/detail/?cityEnName=Hanoi&hotelId=678508",
    stars: 5,
    expected: "VERIFIED_LEGITIMATE"
  },
  {
    url: "https://www.agoda.com/furama-resort-danang/hotel/da-nang-vn.html",
    stars: 5,
    expected: "VERIFIED_LEGITIMATE"
  },
  {
    url: "https://www.booking.com/hotel/vn/caravelle.html",
    stars: 5,
    expected: "VERIFIED_LEGITIMATE"
  },
  {
    url: "https://www.agoda.com/avani-hai-phong-harbour-view-hotel/hotel/hai-phong-vn.html",
    stars: 5,
    expected: "STAR_INFLATION"
  },
  {
    url: "https://www.booking.com/hotel/vn/totally-fake-unregistered-villa.html",
    stars: 5,
    expected: "UNACCREDITED_HOTEL"
  },
  {
    name: "vinpearl",
    stars: 5,
    expected: "VERIFIED_LEGITIMATE",
    expectViolation: false
  },
  {
    name: "diamond beach hotel da nang",
    stars: 5,
    expected: "UNACCREDITED_HOTEL",
    expectViolation: true
  },
  {
    url: "https://www.booking.com/hotel/vn/melia-vinpearl-danang-riverfont.html",
    stars: 5,
    expected: "VERIFIED_LEGITIMATE",
    expectViolation: false
  },
  {
    name: "Melia Vinpearl Danang Riverfront",
    stars: 5,
    expected: "VERIFIED_LEGITIMATE",
    expectViolation: false
  },
  {
    url: "https://www.booking.com/hotel/vn/danang-marriott-resort-spa-non-nuoc-beach-villas.html?aid=8092145",
    stars: 5,
    expected: "VERIFIED_LEGITIMATE",
    expectViolation: false,
    checkTripUrl: "hotelId=7362595"
  },
  {
    url: "https://www.booking.com/hotel/vn/jame-bay-residence.html?dest_id=-3712125",
    stars: 0, // Auto-detect should identify 4 stars for residence
    expected: "UNACCREDITED_HOTEL",
    expectViolation: true,
    expectedClaimedStars: 4
  },
  {
    url: "https://www.booking.com/hotel/vn/lahome-villa-apartment.html?aid=2405612&label=brave_nonbrand_organic_trigger_f3f828ac-4c6a-4b54-8e46-e2779b841553",
    stars: 0, // Auto-detect should identify 4 stars for villa apartment
    expected: "UNACCREDITED_HOTEL",
    expectViolation: true,
    expectedClaimedStars: 4
  }
];

let allPassed = true;
console.log("==================================================");
console.log("CLIENT-SIDE MATCHING ENGINE PARITY SUITE");
console.log("==================================================");

for (const tc of testCases) {
  let parsed = { isUrl: false, name: tc.name || "" };
  if (tc.url) {
    parsed = parseOtaUrl(tc.url);
  }

  const res = matcher.classify({
    name: parsed.name,
    claimedStars: tc.stars,
    otaPlatform: parsed.platform || "Direct Input",
    originalUrl: tc.url || "",
    otaId: parsed.otaId || "",
    otaSlug: parsed.otaSlug || ""
  });

  let pass = res.verdict === tc.expected;
  if (tc.expectViolation !== undefined && res.is_violation !== tc.expectViolation) {
    pass = false;
    console.error(`  Expected is_violation=${tc.expectViolation}, got ${res.is_violation}`);
  }
  if (!res.ota_links || !res.ota_links.agoda || !res.ota_links.booking || !res.ota_links.trip) {
    pass = false;
    console.error(`  Missing OTA deep-links with affiliate tags`);
  }
  if (tc.checkTripUrl && (!res.ota_links || !res.ota_links.trip || !res.ota_links.trip.url.includes(tc.checkTripUrl))) {
    pass = false;
    console.error(`  Expected Trip.com URL to contain ${tc.checkTripUrl}, got ${res.ota_links ? res.ota_links.trip.url : 'null'}`);
  }
  if (tc.expectedClaimedStars !== undefined && res.claimed_stars !== tc.expectedClaimedStars) {
    pass = false;
    console.error(`  Expected claimed_stars=${tc.expectedClaimedStars}, got ${res.claimed_stars}`);
  }
  if (tc.name === "diamond beach hotel da nang" && (!res.verified_alternatives || res.verified_alternatives.length === 0)) {
    pass = false;
    console.error(`  Expected verified alternatives for unaccredited hotel in Da Nang`);
  }

  const label = tc.url ? `URL: ${tc.url.split('?')[0]}` : `"${tc.name}"`;
  console.log(`[${pass ? 'PASS' : 'FAIL'}] ${label} -> ${res.verdict} (is_violation=${res.is_violation})`);
  if (!pass) {
    allPassed = false;
    console.error(`  Expected: ${tc.expected}, Got: ${res.verdict}`);
    console.error(`  Details: matched=${res.matchedHotel ? res.matchedHotel.name : 'null'}, matchType=${res.matchType}`);
  }
}

console.log("==================================================");
console.log("VIETNAM GEOGRAPHY ISOLATION SUITE (STRICT VN SCOPE)");
console.log("==================================================");

const vnGeographyCases = [
  // Legitimate Vietnam URLs
  { url: "https://www.agoda.com/furama-resort-danang/hotel/da-nang-vn.html", text: "", expected: true, desc: "Agoda Danang URL" },
  { url: "https://www.agoda.com/alansea-hotel/hotel/da-nang-vn.html", text: "", expected: true, desc: "Agoda Alan Sea Danang URL" },
  { url: "https://www.booking.com/hotel/vn/caravelle.html", text: "", expected: true, desc: "Booking.com VN URL" },
  { url: "https://www.trip.com/hotels/detail/?cityEnName=Hanoi&hotelId=678508", text: "", expected: true, desc: "Trip.com Hanoi URL" },
  { url: "https://www.trip.com/hotels/da-nang-hotel-detail-6842851/alan-sea-hotel-danang/", text: "", expected: true, desc: "Trip.com Danang URL" },
  { url: "https://www.agoda.com/city/da-nang-vn.html", text: "", expected: true, desc: "Agoda Da Nang city search" },
  
  // Text with Vietnamese cities/provinces
  { url: "", text: "InterContinental Danang Sun Peninsula Resort", expected: true, desc: "Da Nang resort name" },
  { url: "", text: "Khách sạn Mường Thanh Luxury Nha Trang", expected: true, desc: "Nha Trang hotel text" },
  { url: "", text: "Phú Quốc Eco Beach Resort", expected: true, desc: "Phu Quoc resort text" },

  // Foreign properties & URLs (MUST BE REJECTED - STRICT VN ONLY)
  { url: "https://www.agoda.com/siam-kempinski-hotel-bangkok/hotel/bangkok-th.html", text: "", expected: false, desc: "Agoda Bangkok Thailand" },
  { url: "https://www.agoda.com/hotel-gracery-shinjuku/hotel/tokyo-jp.html", text: "", expected: false, desc: "Agoda Tokyo Japan" },
  { url: "https://www.agoda.com/marina-bay-sands/hotel/singapore-sg.html", text: "", expected: false, desc: "Agoda Singapore" },
  { url: "https://www.booking.com/hotel/fr/the-peninsula-paris.html", text: "", expected: false, desc: "Booking.com Paris France" },
  { url: "https://www.booking.com/hotel/gb/the-ritz-london.html", text: "", expected: false, desc: "Booking.com London UK" },
  { url: "https://www.booking.com/hotel/it/hotel-daniel-venice.html", text: "", expected: false, desc: "Booking.com Venice Italy" },
  { url: "https://www.trip.com/hotels/tokyo-hotel-detail-12345/imperial-hotel/", text: "", expected: false, desc: "Trip.com Tokyo Japan" },
  { url: "https://www.trip.com/hotels/rome-hotel-detail-998877/rome-cavalieri/", text: "", expected: false, desc: "Trip.com Rome Italy" },
  { url: "", text: "Hilton Tokyo Shinjuku Japan", expected: false, desc: "Tokyo text without VN" },
  { url: "", text: "The Ritz-Carlton New York Central Park", expected: false, desc: "New York text without VN" }
];

let geoPassed = true;
for (const tc of vnGeographyCases) {
  const actual = isVietnamContext(tc.url, tc.text);
  const match = actual === tc.expected;
  if (!match) geoPassed = false;
  console.log(`[${match ? 'PASS' : 'FAIL'}] [${tc.expected ? 'IN-VN' : 'FOREIGN'}] ${tc.desc}: expected=${tc.expected}, got=${actual}`);
}

console.log("==================================================");
if (!allPassed || !geoPassed) {
  console.error("Test suites FAILED.");
  process.exit(1);
} else {
  console.log(`All Parity & Geography Isolation Tests PASSED (${testCases.length + vnGeographyCases.length}/${testCases.length + vnGeographyCases.length}).`);
}
