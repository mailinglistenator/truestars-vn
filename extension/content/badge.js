/**
 * TrueStars VN — Badge Injector & Modal Manager
 */

(function () {
  let globalMatcher = null;
  let isInitializing = false;
  const pendingQueue = [];

  // Load bundled VNAT Whitelist
  async function initMatcher() {
    if (globalMatcher) return globalMatcher;
    if (isInitializing) {
      return new Promise(resolve => pendingQueue.push(resolve));
    }
    isInitializing = true;

    try {
      const url = chrome.runtime.getURL('data/vnat_whitelist.json');
      const response = await fetch(url);
      const data = await response.json();
      globalMatcher = new TrueStarsMatcher(data);
      console.log(`[TrueStars VN] Initialized with ${data.length} official VNAT accredited hotels.`);
      pendingQueue.forEach(cb => cb(globalMatcher));
      pendingQueue.length = 0;
      return globalMatcher;
    } catch (err) {
      console.error('[TrueStars VN] Failed to load VNAT whitelist:', err);
      return null;
    }
  }

  function showAuditModal(audit) {
    // Remove existing modal if open
    const existing = document.getElementById('truestars-active-modal');
    if (existing) existing.remove();

    const backdrop = document.createElement('div');
    backdrop.id = 'truestars-active-modal';
    backdrop.className = 'truestars-modal-backdrop';

    const win = document.createElement('div');
    win.className = 'truestars-modal-window';

    const isFraud = audit.verdict === 'BLATANT_HOSTEL_FRAUD';
    const isLegit = audit.verdict === 'VERIFIED_LEGITIMATE';
    const isInflation = audit.verdict === 'STAR_INFLATION';

    let headerBadgeColor = '#e11d48';
    let headerBadgeText = '🔴 UNACCREDITED STAR CLAIM';
    if (isLegit) {
      headerBadgeColor = '#059669';
      headerBadgeText = '🟢 OFFICIAL VNAT CERTIFIED';
    } else if (isFraud) {
      headerBadgeColor = '#dc2626';
      headerBadgeText = '🚨 BLATANT HOSTEL FRAUD';
    } else if (isInflation) {
      headerBadgeColor = '#d97706';
      headerBadgeText = '🟡 STAR INFLATION';
    }

    let violationsHtml = '';
    if (audit.violations && audit.violations.length > 0) {
      violationsHtml = `
        <div style="margin-top: 14px;">
          <div style="font-size: 11px; font-weight: 700; color: #94a3b8; text-transform: uppercase;">Statutory Violations (Luật Du lịch 2017)</div>
          ${audit.violations.map(v => `
            <div class="truestars-statute-card">
              <div class="truestars-statute-title">⚠ ${v.law}</div>
              <div>${v.statute_title}</div>
              <div style="color: #94a3b8; margin-top: 4px;">${v.application}</div>
            </div>
          `).join('')}
        </div>
      `;
    }

    let matchedHtml = '';
    if (audit.matched_hotel) {
      matchedHtml = `
        <div style="background: #090d16; border: 1px solid #1e293b; padding: 12px; border-radius: 8px; margin-top: 12px;">
          <div style="font-size: 11px; color: #60a5fa; font-weight: 700; text-transform: uppercase;">Official VNAT Registry Match</div>
          <div style="font-weight: 700; margin-top: 2px;">${audit.matched_hotel.name} (${'★'.repeat(audit.matched_hotel.stars)})</div>
          <div style="font-size: 11px; color: #94a3b8; margin-top: 2px;">${audit.matched_hotel.address}</div>
          <div style="font-size: 11px; color: #34d399; margin-top: 4px;">Capacity: ${audit.matched_hotel.room_count || 'N/A'} certified rooms</div>
        </div>
      `;
    }

    win.innerHTML = `
      <button class="truestars-modal-close" id="truestars-close-btn">&times;</button>
      <div style="display: inline-block; background: ${headerBadgeColor}; color: #fff; padding: 3px 8px; border-radius: 4px; font-size: 10px; font-weight: 800; margin-bottom: 8px;">
        ${headerBadgeText}
      </div>
      <h3 class="truestars-modal-title">${audit.property_name}</h3>
      <div style="font-size: 13px; color: #94a3b8; margin-bottom: 12px;">
        OTA Displayed: <strong style="color: #fbbf24;">${'★'.repeat(audit.claimed_stars)} (${audit.claimed_stars} Stars)</strong> | 
        VNAT Official: <strong style="color: ${isLegit ? '#34d399' : '#f87171'};">${audit.official_stars > 0 ? '★'.repeat(audit.official_stars) : 'Unaccredited (0★)'}</strong>
      </div>
      <div style="background: rgba(0,0,0,0.25); padding: 12px; border-radius: 8px; font-size: 12px; line-height: 1.5;">
        ${audit.summary}
      </div>
      ${matchedHtml}
      ${violationsHtml}
      <div style="background: #070a12; border: 1px solid #334155; border-radius: 8px; padding: 10px 12px; margin-top: 12px; font-size: 11px;">
        <div style="font-weight: 800; color: #f87171; margin-bottom: 4px;">⚖️ DEMONSTRATION OF STATUTORY INFRACTION</div>
        <div style="color: #cbd5e1; line-height: 1.4;">
          <strong>Luật Du lịch 2017 (Điều 9, Khoản 8 & Điều 50):</strong> Only VNAT has statutory authority to award 4★/5★ ratings in Vietnam (only 681 exist nationwide). Displaying unauthorized stars is a strict statutory violation.
        </div>
      </div>
      <div style="display: flex; flex-direction: column; gap: 8px; margin-top: 16px;">
        <button id="truestars-copy-platform-notice" class="truestars-btn-action" style="background: #2563eb; width: 100%; text-align: center;">📝 Copy Platform Cease & Desist Notice</button>
        <button id="truestars-copy-refund-letter" class="truestars-btn-action" style="background: #059669; width: 100%; text-align: center;">💰 Copy Traveler Refund Demand Letter</button>
      </div>
    `;

    backdrop.appendChild(win);
    document.body.appendChild(backdrop);

    document.getElementById('truestars-close-btn').addEventListener('click', () => backdrop.remove());
    backdrop.addEventListener('click', (e) => {
      if (e.target === backdrop) backdrop.remove();
    });

    document.getElementById('truestars-copy-platform-notice').addEventListener('click', () => {
      navigator.clipboard.writeText(audit.platform_notice || audit.legal_notice || audit.summary);
      const btn = document.getElementById('truestars-copy-platform-notice');
      btn.textContent = '✓ Platform Notice Copied!';
      setTimeout(() => { btn.textContent = '📝 Copy Platform Cease & Desist Notice'; }, 2000);
    });

    document.getElementById('truestars-copy-refund-letter').addEventListener('click', () => {
      navigator.clipboard.writeText(audit.refund_demand_letter || audit.summary);
      const btn = document.getElementById('truestars-copy-refund-letter');
      btn.textContent = '✓ Refund Demand Letter Copied!';
      setTimeout(() => { btn.textContent = '💰 Copy Traveler Refund Demand Letter'; }, 2000);
    });
  }

  window.TrueStarsBadge = {
    async auditAndInject(targetElement, { name, claimedStars = 5, hasDorm = false, province = "" }) {
      if (!name || targetElement.querySelector('.truestars-badge-container')) return;

      const m = await initMatcher();
      if (!m) return;

      const audit = m.classify({
        name,
        claimedStars,
        hasDorm,
        province
      });

      // Don't badge low star ratings unless fraudulent
      if (claimedStars < 4 && !hasDorm) return;

      const container = document.createElement('div');
      container.className = 'truestars-badge-container';

      const badge = document.createElement('span');
      badge.className = 'truestars-badge';

      if (audit.verdict === 'VERIFIED_LEGITIMATE') {
        badge.classList.add('truestars-legit');
        badge.innerHTML = `🛡️ VNAT ${audit.official_stars}★`;
        badge.title = 'Officially certified by Vietnam National Authority of Tourism';
      } else if (audit.verdict === 'BLATANT_HOSTEL_FRAUD') {
        badge.classList.add('truestars-hostel-fraud');
        badge.innerHTML = `🚨 FAKE ${claimedStars}★ (HOSTEL)`;
        badge.title = 'Violation: Backpacker hostel with dorm beds claiming 4★/5★';
      } else if (audit.verdict === 'STAR_INFLATION') {
        badge.classList.add('truestars-inflation');
        badge.innerHTML = `⚠ INFLATED: VNAT ${audit.official_stars}★`;
        badge.title = `Certified as ${audit.official_stars}★, marketed as ${claimedStars}★`;
      } else {
        badge.classList.add('truestars-unaccredited');
        badge.innerHTML = `⚠ UNACCREDITED ${claimedStars}★`;
        badge.title = `Not found in official VNAT 4★/5★ accreditation registry`;
      }

      badge.addEventListener('click', (e) => {
        e.stopPropagation();
        e.preventDefault();
        showAuditModal(audit);
      });

      container.appendChild(badge);
      targetElement.prepend(container);
    }
  };
})();
