const fs = require('fs');
const path = require('path');
const { TrueStarsMatcher } = require('../public/matching_engine.js');

const data = JSON.parse(fs.readFileSync(path.join(__dirname, '../public/vnat_whitelist.json'), 'utf8'));
const matcher = new TrueStarsMatcher(data);

const testCases = [
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
  }
];

let allPassed = true;
console.log("==================================================");
console.log("CLIENT-SIDE MATCHING ENGINE PARITY SUITE");
console.log("==================================================");

for (const tc of testCases) {
  const res = matcher.classify({
    name: tc.name,
    claimedStars: tc.stars,
    hasDorm: tc.dorm
  });
  const pass = res.verdict === tc.expected;
  console.log(`[${pass ? 'PASS' : 'FAIL'}] "${tc.name}" -> ${res.verdict}`);
  if (!pass) {
    allPassed = false;
    console.error(`  Expected: ${tc.expected}, Got: ${res.verdict}`);
  }
}

console.log("==================================================");
if (!allPassed) {
  console.error("Parity test suite FAILED.");
  process.exit(1);
} else {
  console.log("Parity test suite PASSED (5/5).");
}
