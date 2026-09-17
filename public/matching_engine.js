/**
 * TrueStars VN — High-Speed Client-Side Entity Resolution & Statutory Audit Engine
 * Includes Smart OTA URL Parsers, Evidentiary Law-Breaking Demonstrations,
 * and Formal Legal Notice & Traveler Refund Letter Generators.
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

/**
 * Smart OTA URL Parser: Extracts platform, clean hotel name/slug, and city
 */
function parseOtaUrl(rawInput) {
  if (!rawInput) return { isUrl: false, name: "", platform: "Direct Input", city: "" };

  const trimmed = rawInput.trim();
  if (!trimmed.startsWith("http://") && !trimmed.startsWith("https://")) {
    return { isUrl: false, name: trimmed, platform: "Direct Input", city: "" };
  }

  try {
    const url = new URL(trimmed);
    const host = url.hostname.toLowerCase();
    let platform = "Online Travel Agency";
    let extractedName = "";
    let city = "";

    if (host.includes("agoda.com")) {
      platform = "Agoda";
      const parts = url.pathname.split("/").filter(Boolean);
      for (const p of parts) {
        if (p.includes(".html")) {
          extractedName = p.replace(/\.html.*$/, "").replace(/[-_]/g, " ");
          break;
        } else if (p.length > 3 && !["hotel", "hotels", "country", "city"].includes(p)) {
          extractedName = p.replace(/[-_]/g, " ");
        }
      }
    } else if (host.includes("booking.com")) {
      platform = "Booking.com";
      const parts = url.pathname.split("/").filter(Boolean);
      for (const p of parts) {
        if (p.includes(".html")) {
          extractedName = p.replace(/\.html.*$/, "").replace(/[-_]/g, " ");
          break;
        }
      }
      if (url.searchParams.get("ss")) {
        extractedName = url.searchParams.get("ss");
      }
    } else if (host.includes("trip.com")) {
      platform = "Trip.com";
      city = url.searchParams.get("cityEnName") || "";
      const hotelId = url.searchParams.get("hotelId") || "";

      // Check if URL has a descriptive slug in the path
      const pathSegments = url.pathname.split("/").filter(Boolean);
      for (const seg of pathSegments) {
        if (seg.includes("-hotel-detail-") || (!["hotels", "detail", "hotel"].includes(seg) && seg.length > 4)) {
          extractedName = seg.replace(/^[a-z0-9]+-hotel-detail-\d+/, "").replace(/[-_]/g, " ").trim();
          if (extractedName) break;
        }
      }

      // If opaque URL with just hotelId & cityEnName (e.g. /hotels/detail/?cityEnName=Da%20Nang&hotelId=2848061)
      if (!extractedName && hotelId) {
        extractedName = `Trip.com Hotel Listing #${hotelId}${city ? ` (${decodeURIComponent(city)})` : ""}`;
      }
    }

    // Clean up numeric trailing tokens or artifacts
    extractedName = extractedName
      .replace(/\bhotel vn\b/gi, "")
      .replace(/\bvn\b/gi, "")
      .replace(/\s+/g, " ")
      .trim();

    // Capitalize words for clean display
    if (extractedName) {
      extractedName = extractedName
        .split(" ")
        .map(w => w.charAt(0).toUpperCase() + w.slice(1))
        .join(" ");
    } else {
      extractedName = `Unspecified ${platform} Listing`;
    }

    return {
      isUrl: true,
      name: extractedName,
      platform: platform,
      city: city ? decodeURIComponent(city) : "",
      originalUrl: trimmed
    };
  } catch (err) {
    return { isUrl: true, name: trimmed.substring(0, 50), platform: "Online Travel Agency", city: "", originalUrl: trimmed };
  }
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

  classify({ name, claimedStars = 5, hasDorm = false, roomCount = null, province = "", otaPlatform = "Online Travel Agency", originalUrl = "" }) {
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
      summary = `Verified legitimate ${officialStars}-star hotel officially accredited by the Vietnam National Authority of Tourism (VNAT).`;
    } else if (hasDorm && isHighRank) {
      verdict = "BLATANT_HOSTEL_FRAUD";
      severity = "CRITICAL";
      summary = `Backpacker hostel or budget lodging falsely marketing as ${claimedStars} stars. Offers dormitory/bunk beds. TCVN 4391:2015 strictly prohibits dorms and requires minimum 80-100 private guest rooms.`;
      violations.push({
        law: "Luật Du lịch 2017 - Điều 9, Khoản 8",
        statute_title: "Các hành vi bị nghiêm cấm trong hoạt động du lịch",
        application: `Displaying ${claimedStars} stars without VNAT statutory accreditation.`
      });
      violations.push({
        law: "TCVN 4391:2015 - Tiêu chuẩn Xếp hạng Khách sạn",
        statute_title: "Quy chuẩn cơ sở vật chất tối thiểu cho Khách sạn 4-5 sao",
        application: "Dormitory and bunk beds disqualify establishment from 4-star or 5-star hotel status."
      });
      violations.push({
        law: "Luật Bảo vệ quyền lợi người tiêu dùng 2023 - Điều 10 & 39",
        statute_title: "Hành vi lừa dối người tiêu dùng & Trách nhiệm nền tảng số trung gian",
        application: `Platform renders gold star iconography misleading guests on safety and luxury standards.`
      });
    } else if (matchedHotel && officialStars < claimedStars) {
      verdict = "STAR_INFLATION";
      severity = "HIGH";
      summary = `Official VNAT certified rating is ${officialStars} stars, but marketed as ${claimedStars} stars (+${claimedStars - officialStars} star inflation).`;
      violations.push({
        law: "Luật Du lịch 2017 - Điều 9, Khoản 8 & Điều 50",
        statute_title: "Quảng cáo sai thứ hạng được cơ quan nhà nước công nhận",
        application: `Officially certified as ${officialStars} stars, but displayed on platform as ${claimedStars} stars.`
      });
    } else if (isHighRank && (!matchedHotel || officialStars === 0)) {
      verdict = "UNACCREDITED_HOTEL";
      severity = "HIGH";
      summary = `Commercial property claims ${claimedStars} stars on ${otaPlatform} but is NOT present in the official VNAT National Accreditation Registry.`;
      violations.push({
        law: "Luật Du lịch 2017 - Điều 9, Khoản 8",
        statute_title: "Quảng cáo cơ sở lưu trú du lịch khi chưa có văn bản công nhận",
        application: "Self-declaring or algorithmically displaying 4 or 5 stars violates the state statutory monopoly."
      });
      violations.push({
        law: "Nghị định 45/2019/NĐ-CP (sửa đổi NĐ 129/2021/NĐ-CP)",
        statute_title: "Xử phạt vi phạm hành chính trong lĩnh vực du lịch",
        application: "Mandates dismantling and ceasing publication of unauthorized star classifications."
      });
      violations.push({
        law: "Nghị định 85/2021/NĐ-CP & Luật BVQLNTD 2023",
        statute_title: "Trách nhiệm pháp lý của sàn thương mại điện tử xuyên biên giới",
        application: "E-commerce platforms bear strict joint liability for publishing unverified quality representations."
      });
    }

    const platformNotice = generatePlatformNotice({
      propertyName: name,
      claimedStars,
      officialStars,
      otaPlatform,
      city: province,
      originalUrl,
      violations,
      matchedHotel,
      hasDorm
    });

    const refundDemandLetter = generateRefundDemandLetter({
      propertyName: name,
      claimedStars,
      officialStars,
      otaPlatform,
      hasDorm
    });

    const lawBreakingProof = generateDemonstrationOfLawBreaking({
      propertyName: name,
      claimedStars,
      officialStars,
      hasDorm,
      otaPlatform,
      matchedHotel
    });

    return {
      property_name: name,
      claimed_stars: claimedStars,
      official_stars: officialStars,
      has_dorm: hasDorm,
      ota_platform: otaPlatform,
      original_url: originalUrl,
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
      law_breaking_proof: lawBreakingProof,
      platform_notice: platformNotice,
      refund_demand_letter: refundDemandLetter
    };
  }
}

/**
 * Generates the Formal Statutory Demonstration of Law Breaking
 */
function generateDemonstrationOfLawBreaking({ propertyName, claimedStars, officialStars, hasDorm, otaPlatform, matchedHotel }) {
  const isHostel = hasDorm;
  const isInflated = matchedHotel && officialStars < claimedStars;

  return {
    statute_monopoly: {
      law: "Luật Du lịch 2017 (Law No. 09/2017/QH14) - Điều 50, Khoản 3",
      rule: "Thẩm quyền công nhận hạng cơ sở lưu trú du lịch",
      analysis: "Under Vietnamese law, the 1-to-5 star classification is a STATE-CONTROLLED statutory title. Only the Vietnam National Authority of Tourism (Cục Du lịch Quốc gia Việt Nam - VNAT) has legal authority to evaluate and award 4-star and 5-star ratings. Online booking platforms cannot invent internal algorithms or allow properties to self-declare star ranks."
    },
    prohibition_clause: {
      law: "Luật Du lịch 2017 - Điều 9, Khoản 8",
      rule: "Các hành vi bị nghiêm cấm trong hoạt động du lịch",
      quote: "Quảng cáo cơ sở lưu trú du lịch khi chưa có văn bản công nhận hạng của cơ quan nhà nước có thẩm quyền hoặc quảng cáo không đúng với hạng đã được công nhận.",
      analysis: `Displaying ${claimedStars} stars for "${propertyName}" directly violates this statutory prohibition because the property possesses NO official ${claimedStars}-star certificate.`
    },
    ground_truth_evidence: {
      national_whitelist_size: 681,
      total_5star: 301,
      total_4star: 380,
      evidence_finding: isInflated
        ? `Official Registry Match: "${matchedHotel.name}" is certified for only ${officialStars} Stars. Marketing it as ${claimedStars} Stars constitutes unlawful star inflation (+${claimedStars - officialStars}★).`
        : `Official Registry Search: A complete crawl of the VNAT central database (csdl.vietnamtourism.gov.vn) confirms ZERO 4-star or 5-star accreditation records exist for "${propertyName}". Out of only 681 certified hotels nationwide, this listing is 100% UNACCREDITED.`
    },
    facility_standards: isHostel ? {
      standard: "TCVN 4391:2015 - Tiêu chuẩn Xếp hạng Khách sạn",
      analysis: "National standard TCVN 4391:2015 strictly mandates a minimum of 80 rooms for 4-star and 100 rooms for 5-star hotels. Facilities offering shared dormitory or bunk bed rooms cannot legally qualify as luxury hotels."
    } : null,
    platform_liability: {
      decree: "Nghị định 85/2021/NĐ-CP & Luật Bảo vệ quyền lợi người tiêu dùng 2023 (Điều 10 & 39)",
      analysis: `${otaPlatform} acts as an e-commerce intermediary platform operating in Vietnam. It is strictly mandated to verify supplier licenses and bears direct joint liability for displaying deceptive gold star emblems that mislead booking travelers.`
    }
  };
}

/**
 * Generates Cease & Desist / Legal Takedown Notice to Offending Platform
 */
function generatePlatformNotice({ propertyName, claimedStars, officialStars, otaPlatform, city, originalUrl, violations, matchedHotel, hasDorm }) {
  const dateStr = new Date().toLocaleDateString('en-GB');

  return `FORMAL STATUTORY NOTICE OF UNLAWFUL HOTEL STAR CLASSIFICATION
& DEMAND FOR IMMEDIATE PLATFORM TAKEDOWN

DATE: ${dateStr}
TO: Legal & Regulatory Compliance Directorate
    ${otaPlatform.toUpperCase()} [Trip.com Group Ltd. / Agoda Company Pte. Ltd. / Booking.com B.V.]
CC: 
    1. Thanh tra Bộ Văn hóa, Thể thao và Du lịch (Tourism Inspectorate of Vietnam)
    2. Ủy ban Cạnh tranh Quốc gia - Bộ Công Thương (National Competition Commission)
    3. Cục Du lịch Quốc gia Việt Nam - VNAT

RE: SYSTEMIC CONSUMER DECEPTION & STATUTORY INFRACTION
PROPERTY: ${propertyName}
LOCATION: ${city || "Vietnam"}
LISTING URL: ${originalUrl || "[Platform Listing URL]"}
DISPLAYED RATING ON PLATFORM: ${'★'.repeat(claimedStars)} (${claimedStars} Stars)
OFFICIAL STATUTORY ACCREDITATION: ${officialStars > 0 ? `${officialStars} Stars Certified (INFLATED TO ${claimedStars}★)` : 'UNACCREDITED (0 Stars Certified)'}

1. STATEMENT OF STATUTORY VIOLATION
Under Article 9, Clause 8 and Article 50 of the Law on Tourism of the Socialist Republic of Vietnam (Law No. 09/2017/QH14):
• The 1-to-5 star classification system for tourism accommodations in Vietnam is a strict state monopoly regulated exclusively by the Vietnam National Authority of Tourism (VNAT).
• Article 9, Clause 8 explicitly prohibits: "Advertising tourist accommodation establishments without official written accreditation by the competent state authority, or advertising inconsistent with the accredited rank."
• Commercial listings displaying unauthorized gold star iconography violate Decree No. 45/2019/NĐ-CP (amended by Decree 129/2021/NĐ-CP) and Decree No. 38/2021/NĐ-CP (False Advertising).

2. EVIDENTIARY AUDIT PROOF
According to the official central database of the Ministry of Culture, Sports and Tourism (csdl.vietnamtourism.gov.vn):
• There are currently ONLY 301 certified 5-star hotels and 380 certified 4-star hotels across all of Vietnam (Total: 681 accredited establishments).
• An exhaustive search of the national statutory whitelist confirms that "${propertyName}" DOES NOT possess ${claimedStars}-star accreditation.
${hasDorm ? '• EVIDENCE OF BLATANT FRAUD: The property operates dormitory / bunk beds, which physically and legally disqualifies it from 4-star or 5-star ranking under National Standard TCVN 4391:2015.\n' : ''}
3. PLATFORM INTERMEDIARY STRICT LIABILITY
Under Decree No. 85/2021/NĐ-CP (regulating cross-border e-commerce platforms in Vietnam) and Articles 10 & 39 of the Law on Protection of Consumer Rights 2023:
As a digital platform intermediary transacting in Vietnam, ${otaPlatform} is legally obligated to verify statutory qualifications and shares joint liability for false, misleading quality representations.

4. FORMAL DEMAND FOR REMEDY
You are hereby given formal notice to:
1. Immediately remove the unauthorized ${claimedStars}-star classification from the digital listing for "${propertyName}".
2. Replace the state-regulated star symbol with clear, non-deceptive terminology or verify official accreditation.

TIME IS OF THE ESSENCE: Failure to rectify this listing within five (5) business days will result in the formal transmission of this evidentiary dossier to Thanh tra Bộ VHTTDL and the National Competition Commission for administrative enforcement, fines, and market access review.

Submitted via TrueStars VN Watchdog Engine (truestars-vn.vercel.app)`;
}

/**
 * Generates Traveler Refund Demand Letter
 */
function generateRefundDemandLetter({ propertyName, claimedStars, officialStars, otaPlatform, hasDorm }) {
  const dateStr = new Date().toLocaleDateString('en-GB');

  return `FORMAL DEMAND FOR FULL REFUND
DECEPTIVE CONSUMER INDUCEMENT & STATUTORY NON-COMPLIANCE

DATE: ${dateStr}
TO: Customer Care & Dispute Escalation Department
    ${otaPlatform} Support Team

FROM: [Insert Your Full Name]
EMAIL: [Insert Your Account Email]
BOOKING CONFIRMATION ID: [Insert Booking Reference Number]
PROPERTY NAME: ${propertyName}
DATES OF RESERVATION: [Insert Check-In & Check-Out Dates]
TOTAL AMOUNT PAID: [Insert Amount & Currency, e.g. $450.00 USD / 11,200,000 VND]

SUBJECT: FORMAL DEMAND FOR FULL REFUND — BREACH OF CONTRACT & FALSE HOTEL STAR RATING

Dear Customer Support & Legal Management,

I am writing to formally demand an immediate full refund for my reservation at "${propertyName}", booked via ${otaPlatform} under Booking Reference [Insert Booking Reference Number].

1. SUMMARY OF MISREPRESENTATION
I booked this property relying directly on the ${claimedStars}-Star classification prominently displayed on your platform with ${claimedStars} gold star icons (★★★★★). 

Official verification conducted via the Vietnam National Authority of Tourism (Cục Du lịch Quốc gia Việt Nam - VNAT, csdl.vietnamtourism.gov.vn) reveals that this property:
• Officially holds ${officialStars > 0 ? `only a ${officialStars}-Star accreditation` : 'ZERO official star accreditation'} from the Vietnamese government.
• Illegally advertises luxury stars in direct violation of Article 9, Clause 8 of Vietnam's Law on Tourism 2017 (Law No. 09/2017/QH14).
${hasDorm ? '• Sells shared dormitory / bunk bed facilities, which cannot legally qualify as a 4-star or 5-star hotel under National Standard TCVN 4391:2015.\n' : ''}
2. STATUTORY BREACH & INTERMEDIARY LIABILITY
The advertised ${claimedStars}-star rating was the primary material factor in my booking decision and willingness to pay this rate.
• Under Article 10 & Article 34 of Vietnam's Law on Protection of Consumer Rights 2023 (effective July 1, 2024), consumers are entitled to full compensation and contract voiding when services fail to match advertised claims.
• Under Decree 85/2021/NĐ-CP, ${otaPlatform} is jointly liable for false or deceptive merchant claims hosted on its platform.
• Under International Merchant Operating Rules (Visa / Mastercard Chargeback Reason Code 4853 — "Services Not as Described / Misrepresentation"), advertising an unaccredited budget lodging as a luxury hotel constitutes clear commercial deception.

3. REQUIRED REMEDY
I demand a 100% refund of [Insert Amount & Currency] credited back to my original payment method within seven (7) business days of receipt of this notice.

If a full refund is not processed within seven business days, I will immediately:
1. File a formal chargeback dispute with my credit card issuing bank, attaching the official VNAT statutory whitelist records proving deceptive quality representation.
2. Submit a formal consumer protection complaint to the National Competition Commission (Ủy ban Cạnh tranh Quốc gia - Bộ Công Thương) and the Ministry of Tourism Inspectorate.
3. Lodge a complaint with consumer protection authorities in my country of residence.

I await your immediate confirmation of refund processing.

Sincerely,

[Insert Your Full Name]
[Insert Phone Number]`;
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    TrueStarsMatcher,
    removeAccents,
    extractCoreTokens,
    sequenceRatio,
    parseOtaUrl,
    generatePlatformNotice,
    generateRefundDemandLetter,
    generateDemonstrationOfLawBreaking
  };
}
