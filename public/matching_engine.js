/**
 * TrueStars VN — High-Speed Client-Side Entity Resolution & Statutory Audit Engine
 * 100% Client-Side Matching Parity with Python MatchingEngine & LegalEngine.
 */

const GEO_REPLACEMENTS = [
  [/\bhanoi\b/g, "ha noi"],
  [/\bsaigon\b/g, "sai gon"],
  [/\bdanang\b/g, "da nang"],
  [/\bnhatrang\b/g, "nha trang"],
  [/\bhalong\b/g, "ha long"],
  [/\bphuquoc\b/g, "phu quoc"],
  [/\bhochiminh\b/g, "ho chi minh"],
  [/\bdalat\b/g, "da lat"],
  [/\bhoian\b/g, "hoi an"],
  [/\bhue\b/g, "thua thien hue"],
  [/\bvungtau\b/g, "vung tau"],
];

const NOISE_WORDS = new Set([
  "khach", "san", "hotel", "resort", "spa", "boutique", "suites", "suite",
  "apartment", "apartments", "condo", "villa", "villas", "the", "and", "luxury",
  "international", "grand", "palace", "residence", "residences", "inn", "nghi", "duong",
  "co", "so", "luu", "tru", "ha", "noi", "saigon", "sai", "gon", "da", "nang",
  "ho", "chi", "minh", "hcm", "vietnam", "vn", "quoc", "te", "ha", "long",
  "nha", "trang", "phu", "quoc", "view", "central", "center", "city", "bay", "plaza"
]);

function removeAccents(str) {
  if (!str) return "";
  let norm = str.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  norm = norm.replace(/[đĐ]/g, "d");
  norm = norm.replace(/[^\w\s]/g, " ");
  norm = norm.replace(/\s+/g, " ").trim().toLowerCase();
  for (const [regex, rep] of GEO_REPLACEMENTS) {
    norm = norm.replace(regex, rep);
  }
  return norm;
}

function extractCoreTokens(str) {
  const norm = removeAccents(str);
  const tokens = norm.split(/\s+/).filter(t => t.length > 2 && !NOISE_WORDS.has(t));
  return new Set(tokens);
}

function sequenceRatio(s1, s2) {
  if (!s1 || !s2) return 0.0;
  if (s1 === s2) return 1.0;
  
  // Fast Dice coefficient on character bigrams for sequence matching
  const getBigrams = s => {
    const bg = new Map();
    for (let i = 0; i < s.length - 1; i++) {
      const pair = s.substr(i, 2);
      bg.set(pair, (bg.get(pair) || 0) + 1);
    }
    return bg;
  };

  const bg1 = getBigrams(s1);
  const bg2 = getBigrams(s2);
  let intersection = 0;
  for (const [pair, count] of bg1.entries()) {
    if (bg2.has(pair)) {
      intersection += Math.min(count, bg2.get(pair));
    }
  }

  const total = Math.max(1, (s1.length - 1) + (s2.length - 1));
  return (2.0 * intersection) / total;
}

class TrueStarsMatcher {
  constructor(hotelsList = []) {
    this.hotels = [];
    if (Array.isArray(hotelsList) && hotelsList.length > 0) {
      this.loadHotels(hotelsList);
    }
  }

  loadHotels(hotelsList) {
    this.hotels = hotelsList.map(h => ({
      ...h,
      name_norm: removeAccents(h.name),
      prov_norm: removeAccents(h.province),
      addr_norm: removeAccents(h.address),
      tokens: extractCoreTokens(h.name)
    }));
  }

  findMatches(hotelName, province = "", threshold = 0.50) {
    if (!hotelName) return [];
    const inputNorm = removeAccents(hotelName);
    const inputTokens = extractCoreTokens(hotelName);
    const normProv = removeAccents(province);

    const scored = [];

    for (const h of this.hotels) {
      if (normProv) {
        const provTokens = normProv.split(/\s+/);
        const combined = `${h.prov_norm} ${h.addr_norm}`;
        const hasOverlap = provTokens.some(pt => combined.includes(pt));
        if (!hasOverlap) continue;
      }

      const candNorm = h.name_norm;
      const candTokens = h.tokens;

      // 1. Substring match
      if (inputNorm && candNorm.includes(inputNorm)) {
        const score = Math.max(0.85, inputNorm.length / candNorm.length);
        scored.push({ hotel: h, score: Math.round(score * 1000) / 1000 });
        continue;
      }

      // 2. Sequence ratio
      const seqScore = sequenceRatio(inputNorm, candNorm);

      // 3. Token overlap
      let tokenScore = 0.0;
      if (inputTokens.size > 0 && candTokens.size > 0) {
        let intersection = 0;
        for (const t of inputTokens) {
          if (candTokens.has(t)) intersection++;
        }
        const union = new Set([...inputTokens, ...candTokens]).size;
        tokenScore = intersection / union;
      }

      const finalScore = (seqScore * 0.40) + (tokenScore * 0.60);
      if (finalScore >= threshold) {
        scored.push({ hotel: h, score: Math.round(finalScore * 1000) / 1000 });
      }
    }

    scored.sort((a, b) => b.score - a.score);
    return scored;
  }

  classify({ name, claimedStars = 5, hasDorm = false, roomCount = null, province = "" }) {
    const matches = this.findMatches(name, province, 0.45);
    const bestMatch = matches.length > 0 ? matches[0] : null;
    const matchScore = bestMatch ? bestMatch.score : 0.0;
    const matchedHotel = matchScore >= 0.70 ? bestMatch.hotel : null;
    const officialStars = matchedHotel ? matchedHotel.stars : 0;

    let verdict = "UNACCREDITED_HOTEL";
    let severity = "HIGH";
    let summary = "";
    const violations = [];

    const isHighRank = claimedStars >= 4;

    if (matchedHotel && officialStars === claimedStars && !hasDorm) {
      verdict = "VERIFIED_LEGITIMATE";
      severity = "NONE";
      summary = `Verified legitimate ${officialStars}-star hotel accredited by the Vietnam National Authority of Tourism (VNAT).`;
    } else if (hasDorm && isHighRank) {
      verdict = "BLATANT_HOSTEL_FRAUD";
      severity = "CRITICAL";
      summary = `Backpacker hostel or budget lodging falsely marketing as ${claimedStars} stars. Features dormitory/bunk beds. TCVN 4391:2015 strictly prohibits dorms and requires minimum 80-100 private rooms.`;
      violations.push({
        law: "Luật Du lịch 2017 - Điều 9, Khoản 8",
        statute_title: "Các hành vi bị nghiêm cấm trong hoạt động du lịch",
        application: `Property displays ${claimedStars} stars without VNAT statutory accreditation.`
      });
      violations.push({
        law: "TCVN 4391:2015 - Tiêu chuẩn Xếp hạng Khách sạn",
        statute_title: "Quy chuẩn cơ sở vật chất tối thiểu cho Khách sạn 4-5 sao",
        application: "Dormitory and bunk beds disqualify establishment from 4-star or 5-star hotel status."
      });
      violations.push({
        law: "Luật Bảo vệ quyền lợi người tiêu dùng 2023 - Điều 10 & 39",
        statute_title: "Lừa dối người tiêu dùng & Trách nhiệm nền tảng số trung gian",
        application: "Displaying gold star badges misleading guests on safety and luxury standards."
      });
    } else if (matchedHotel && officialStars < claimedStars) {
      verdict = "STAR_INFLATION";
      severity = "HIGH";
      summary = `Official VNAT certified rating is ${officialStars} stars, but marketed as ${claimedStars} stars (+${claimedStars - officialStars} star inflation).`;
      violations.push({
        law: "Luật Du lịch 2017 - Điều 9, Khoản 8 & Điều 50",
        statute_title: "Quảng cáo sai thứ hạng được cơ quan nhà nước công nhận",
        application: `Officially certified as ${officialStars} stars, but displayed on OTA as ${claimedStars} stars.`
      });
    } else if (isHighRank && (!matchedHotel || officialStars === 0)) {
      verdict = "UNACCREDITED_HOTEL";
      severity = "HIGH";
      summary = `Commercial property claims ${claimedStars} stars but is NOT in the official VNAT National Accreditation Registry.`;
      violations.push({
        law: "Luật Du lịch 2017 - Điều 9, Khoản 8",
        statute_title: "Quảng cáo cơ sở lưu trú du lịch khi chưa có văn bản công nhận",
        application: "Self-declaring or algorithmically displaying 4 or 5 stars violates statutory monopoly."
      });
      violations.push({
        law: "Nghị định 45/2019/NĐ-CP (sửa đổi NĐ 129/2021/NĐ-CP)",
        statute_title: "Xử phạt vi phạm hành chính trong lĩnh vực du lịch",
        application: "Mandates dismantling and ceasing publication of unauthorized star classifications."
      });
    }

    return {
      property_name: name,
      claimed_stars: claimedStars,
      official_stars: officialStars,
      has_dorm: hasDorm,
      verdict: verdict,
      severity: severity,
      summary: summary,
      matched_hotel: matchedHotel ? {
        name: matchedHotel.name,
        stars: matchedHotel.stars,
        address: matchedHotel.address,
        province: matchedHotel.province,
        room_count: matchedHotel.room_count,
        decision_code: matchedHotel.decision_code
      } : null,
      match_score: matchScore,
      violations: violations,
      legal_notice: `THÔNG BÁO VI PHẠM PHÁP LUẬT DU LỊCH:\nCơ sở lưu trú '${name}' đang hiển thị hoặc tự phong ${claimedStars} sao trên nền tảng đặt phòng trực tuyến. Hành vi này có dấu hiệu vi phạm Điều 9, Khoản 8 Luật Du lịch 2017 và Nghị định 45/2019/NĐ-CP.`
    };
  }
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { TrueStarsMatcher, removeAccents, extractCoreTokens, sequenceRatio };
}
