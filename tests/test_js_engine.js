const fs = require('fs');
const path = require('path');
const { TrueStarsMatcher, parseOtaUrl } = require('../public/matching_engine.js');

const data = JSON.parse(fs.readFileSync(path.join(__dirname, '../public/vnat_whitelist.json'), 'utf8'));
const matcher = new TrueStarsMatcher(data);

const testCases = [
  // 1. Exact Name Matching Tests
  {
    name: "Sofitel Legend Metropole Hanoi",
    stars: 5,
    dorm: false,
    expected: "VERIFIED_LEGITIMATE"
  },
  {
    name: "Furama Resort Danang",
    stars: 5,
    dorm: false,
    expected: "VERIFIED_LEGITIMATE"
  },
  {
    name: "Avani Hai Phong Harbour View",
    stars: 5,
    dorm: false,
    expected: "STAR_INFLATION"
  },
  {
    name: "Hanoi Central Backpacker Hostel",
    stars: 5,
    dorm: true,
    expected: "BLATANT_HOSTEL_FRAUD"
  },
  {
    name: "Fake Luxury Penthouse Hanoi",
    stars: 5,
    dorm: false,
    expected: "UNACCREDITED_HOTEL"
  },

  // 2. Closed-World OTA Aggregator Identity Link Tests (Zero False Positives)
  {
    url: "https://www.trip.com/hotels/detail/?cityEnName=Hanoi&hotelId=678508",
    stars: 5,
    dorm: false,
    expected: "VERIFIED_LEGITIMATE"
  },
  {
    url: "https://www.agoda.com/furama-resort-danang/hotel/da-nang-vn.html",
    stars: 5,
    dorm: false,
    expected: "VERIFIED_LEGITIMATE"
  },
  {
    url: "https://www.booking.com/hotel/vn/caravelle.html",
    stars: 5,
    dorm: false,
    expected: "VERIFIED_LEGITIMATE"
  },
  {
    url: "https://www.agoda.com/avani-hai-phong-harbour-view-hotel/hotel/hai-phong-vn.html",
    stars: 5,
    dorm: false,
    expected: "STAR_INFLATION"
  },
  {
    url: "https://www.booking.com/hotel/vn/totally-fake-unregistered-villa.html",
    stars: 5,
    dorm: false,
    expected: "UNACCREDITED_HOTEL"
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
    hasDorm: tc.dorm,
    otaPlatform: parsed.platform || "Direct Input",
    originalUrl: tc.url || "",
    otaId: parsed.otaId || "",
    otaSlug: parsed.otaSlug || ""
  });

  const pass = res.verdict === tc.expected;
  const label = tc.url ? `URL: ${tc.url.split('?')[0]}` : `"${tc.name}"`;
  console.log(`[${pass ? 'PASS' : 'FAIL'}] ${label} -> ${res.verdict}`);
  if (!pass) {
    allPassed = false;
    console.error(`  Expected: ${tc.expected}, Got: ${res.verdict}`);
    console.error(`  Details: matched=${res.matchedHotel ? res.matchedHotel.name : 'null'}, matchType=${res.matchType}`);
  }
}

console.log("==================================================");
if (!allPassed) {
  console.error("Parity test suite FAILED.");
  process.exit(1);
} else {
  console.log(`Parity test suite PASSED (${testCases.length}/${testCases.length}).`);
}
