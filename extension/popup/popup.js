/**
 * TrueStars VN — Popup Controller
 */

let matcher = null;
let whitelist = [];

async function loadData() {
  try {
    const res = await fetch(chrome.runtime.getURL('data/vnat_whitelist.json'));
    whitelist = await res.json();
    matcher = new TrueStarsMatcher(whitelist);
    setupSearch();
    auditActiveTab();
  } catch (err) {
    console.error('Failed to load whitelist in popup:', err);
  }
}

async function auditActiveTab() {
  const hotelNameEl = document.getElementById('tab-hotel-name');
  const verdictEl = document.getElementById('tab-audit-result');

  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab || !tab.url) {
      hotelNameEl.textContent = 'No active tab detected';
      return;
    }

    const url = tab.url;
    let propName = '';
    let isOTA = false;

    if (url.includes('agoda.com')) {
      isOTA = true;
      // Extract from page title: "Hotel Name, Hanoi | Deals..."
      const title = tab.title || '';
      propName = title.split(',')[0].replace(/booking/i, '').trim();
    } else if (url.includes('booking.com')) {
      isOTA = true;
      const title = tab.title || '';
      propName = title.split('(')[0].replace(/hotel/i, 'Hotel').trim();
    } else if (url.includes('trip.com')) {
      isOTA = true;
      const title = tab.title || '';
      propName = title.split('-')[0].trim();
    }

    if (!isOTA || !propName) {
      hotelNameEl.textContent = 'Not an OTA Listing';
      verdictEl.innerHTML = '<span class="placeholder-text">Open an Agoda, Booking.com, or Trip.com hotel page to inspect.</span>';
      return;
    }

    const checkVn = typeof isVietnamContext === 'function' ? isVietnamContext : (window.TrueStarsIsVietnam || (() => false));
    if (!checkVn(url, tab.title)) {
      hotelNameEl.textContent = propName;
      verdictEl.innerHTML = `
        <div class="verdict-tag" style="background: #334155; color: #94a3b8; border: 1px solid #475569;">🌍 NON-VIETNAM PROPERTY</div>
        <div style="color: #94a3b8; font-size: 11px; margin-top: 6px;">
          TrueStars Watchdog operates exclusively within Vietnam. This listing is located outside Vietnam and is not subject to VNAT accreditation (Luật Du lịch 2017).
        </div>
      `;
      return;
    }

    hotelNameEl.textContent = propName;

    if (!matcher) return;
    const audit = matcher.classify({
      name: propName,
      claimedStars: 5 // default inspect high
    });

    let tagClass = 'tag-unaccredited';
    let tagLabel = '🔴 UNACCREDITED STAR CLAIM';
    if (audit.verdict === 'VERIFIED_LEGITIMATE') {
      tagClass = 'tag-legit';
      tagLabel = `🟢 OFFICIAL VNAT ${audit.official_stars}★`;
    } else if (audit.verdict === 'STAR_INFLATION') {
      tagClass = 'tag-inflation';
      tagLabel = `🟡 INFLATED (+${audit.claimed_stars - audit.official_stars}★)`;
    }

    let refundCallout = '';
    if (audit.is_violation) {
      if (audit.verdict === 'STAR_INFLATION') {
        refundCallout = `
          <div style="background: rgba(217, 119, 6, 0.2); border: 1px solid #f59e0b; border-radius: 6px; padding: 8px; margin-top: 8px; font-size: 11px; color: #fde68a;">
            <strong>⚖️ STATUTORY REFUND ENTITLEMENT:</strong> Eligible for price adjustment refund or penalty-free cancellation under Decree 85/2021/NĐ-CP.
          </div>
        `;
      } else {
        refundCallout = `
          <div style="background: rgba(225, 29, 72, 0.2); border: 1px solid #f43f5e; border-radius: 6px; padding: 8px; margin-top: 8px; font-size: 11px; color: #fecdd3;">
            <strong>🚨 ELIGIBLE FOR 100% FULL REFUND:</strong> 0★ unaccredited listing. Strict liability under Decree 85/2021/NĐ-CP & Consumer Protection Law 2023.
          </div>
        `;
      }
    }

    verdictEl.innerHTML = `
      <div class="verdict-tag ${tagClass}">${tagLabel}</div>
      <div style="color: #cbd5e1; font-size: 11px; margin-top: 4px;">${audit.summary}</div>
      ${refundCallout}
      ${audit.matched_hotel ? `<div style="color: #60a5fa; font-size: 10px; margin-top: 4px;">Matched: ${audit.matched_hotel.name} (${audit.matched_hotel.address})</div>` : ''}
    `;
  } catch (err) {
    console.error('Error auditing active tab:', err);
  }
}

function setupSearch() {
  const input = document.getElementById('popup-search-input');
  const resultsEl = document.getElementById('popup-search-results');

  input.addEventListener('input', () => {
    const q = input.value.trim().toLowerCase();
    if (!q || !matcher) {
      resultsEl.innerHTML = '';
      return;
    }

    const matches = matcher.findMatches(q, '', 0.40).slice(0, 8);
    if (matches.length === 0) {
      resultsEl.innerHTML = '<div style="color: #64748b; font-size: 11px; padding: 4px;">No accredited hotels found.</div>';
      return;
    }

    resultsEl.innerHTML = matches.map(m => `
      <div class="search-item">
        <div class="search-item-title">
          <span>${m.hotel.name}</span>
          <span style="color: #fbbf24;">${'★'.repeat(m.hotel.stars)}</span>
        </div>
        <div class="search-item-addr">${m.hotel.address}</div>
      </div>
    `).join('');
  });
}

document.addEventListener('DOMContentLoaded', loadData);
