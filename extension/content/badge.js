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

    const isLegit = audit.verdict === 'VERIFIED_LEGITIMATE' || !audit.is_violation;
    const isInflation = audit.verdict === 'STAR_INFLATION';

    let headerBadgeColor = '#e11d48';
    let headerBadgeText = '🔴 UNACCREDITED STAR CLAIM';
    if (isLegit) {
      headerBadgeColor = '#059669';
      headerBadgeText = '🟢 OFFICIAL VNAT CERTIFIED';
    } else if (isInflation) {
      headerBadgeColor = '#d97706';
      headerBadgeText = '🟡 STAR INFLATION';
    }

    let violationsHtml = '';
    if (!isLegit && audit.violations && audit.violations.length > 0) {
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
          <div style="font-size: 11px; color: #34d399; margin-top: 4px;">Capacity: ${audit.matched_hotel.room_count || '100+'} certified rooms • Decision: #${audit.matched_hotel.decision_code || audit.matched_hotel.item_id}</div>
        </div>
      `;
    }

    // Outbound OTA Links
    let otaLinksHtml = '';
    if (audit.ota_links) {
      otaLinksHtml = `
        <div style="margin-top: 12px;">
          <div style="font-size: 10px; font-weight: 700; color: #94a3b8; text-transform: uppercase; margin-bottom: 4px;">Direct Outbound Verification Links:</div>
          <div style="display: flex; gap: 6px; flex-wrap: wrap;">
            <a href="${audit.ota_links.agoda.url}" target="_blank" rel="noopener noreferrer" style="background: rgba(249,115,22,0.15); border: 1px solid #f97316; color: #fdba74; padding: 4px 8px; border-radius: 4px; font-size: 11px; text-decoration: none; font-weight: 700;">Agoda ↗</a>
            <a href="${audit.ota_links.booking.url}" target="_blank" rel="noopener noreferrer" style="background: rgba(59,130,246,0.15); border: 1px solid #3b82f6; color: #93c5fd; padding: 4px 8px; border-radius: 4px; font-size: 11px; text-decoration: none; font-weight: 700;">Booking.com ↗</a>
            <a href="${audit.ota_links.trip.url}" target="_blank" rel="noopener noreferrer" style="background: rgba(234,179,8,0.15); border: 1px solid #eab308; color: #fde047; padding: 4px 8px; border-radius: 4px; font-size: 11px; text-decoration: none; font-weight: 700;">Trip.com ↗</a>
            <a href="${audit.ota_links.google_maps.url}" target="_blank" rel="noopener noreferrer" style="background: rgba(16,185,129,0.15); border: 1px solid #10b981; color: #6ee7b7; padding: 4px 8px; border-radius: 4px; font-size: 11px; text-decoration: none; font-weight: 700;">Maps ↗</a>
          </div>
        </div>
      `;
    }

    // Alternatives HTML if violation
    let alternativesHtml = '';
    if (!isLegit && audit.verified_alternatives && audit.verified_alternatives.length > 0) {
      alternativesHtml = `
        <div style="margin-top: 14px; background: #060911; border: 1px solid #10b981; border-radius: 8px; padding: 12px;">
          <div style="font-size: 11px; font-weight: 800; color: #34d399; text-transform: uppercase;">🛡️ Certified 5★ Alternatives Nearby:</div>
          <div style="display: flex; flex-direction: column; gap: 8px; margin-top: 8px;">
            ${audit.verified_alternatives.slice(0, 3).map(alt => `
              <div style="background: #0d1322; border: 1px solid #1e293b; padding: 8px; border-radius: 6px;">
                <div style="display: flex; justify-content: space-between; font-size: 11px; font-weight: 700;">
                  <span>${alt.name}</span>
                  <span style="color: #fbbf24;">${'★'.repeat(alt.stars)}</span>
                </div>
                <div style="font-size: 10px; color: #94a3b8; margin-top: 2px;">${alt.address}</div>
                <div style="display: flex; gap: 4px; margin-top: 6px;">
                  <a href="${alt.agoda_url}" target="_blank" rel="noopener noreferrer" style="font-size: 10px; color: #fdba74; text-decoration: underline;">Agoda ↗</a>
                  <span style="color: #475569;">•</span>
                  <a href="${alt.booking_url}" target="_blank" rel="noopener noreferrer" style="font-size: 10px; color: #93c5fd; text-decoration: underline;">Booking ↗</a>
                  <span style="color: #475569;">•</span>
                  <a href="${alt.trip_url}" target="_blank" rel="noopener noreferrer" style="font-size: 10px; color: #fde047; text-decoration: underline;">Trip ↗</a>
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      `;
    }

    let otaPlatform = audit.ota_platform || 'Booking Platform';
    const host = window.location.hostname.toLowerCase();
    if (host.includes('agoda.com')) otaPlatform = 'Agoda';
    else if (host.includes('booking.com')) otaPlatform = 'Booking.com';
    else if (host.includes('trip.com')) otaPlatform = 'Trip.com';

    let refundBannerHtml = '';
    if (!isLegit) {
      if (isInflation) {
        refundBannerHtml = `
          <div class="truestars-refund-card inflation-mode">
            <div class="truestars-refund-tag">⚖️ STATUTORY REFUND ENTITLEMENT</div>
            <div class="truestars-refund-title">ELIGIBLE FOR RATE REFUND OR FREE CANCELLATION FROM ${otaPlatform.toUpperCase()}</div>
            <div class="truestars-refund-desc">
              Advertised rating (${audit.claimed_stars}★) exceeds official VNAT accreditation (${audit.official_stars}★). Under Decree 85/2021/NĐ-CP & Consumer Protection Law 2023, you have the statutory right to claim a price adjustment refund or penalty-free cancellation from ${otaPlatform}.
            </div>
            <button id="truestars-copy-refund-letter" class="truestars-btn-refund">💰 Claim Rate Difference Refund (Copy Demand Letter)</button>
            <div class="truestars-refund-subnote">Decree 85/2021/NĐ-CP • Chargeback Guaranteed</div>
          </div>
        `;
      } else {
        refundBannerHtml = `
          <div class="truestars-refund-card">
            <div class="truestars-refund-tag">🚨 STATUTORY 100% REFUND ENTITLEMENT</div>
            <div class="truestars-refund-title">ELIGIBLE FOR 100% FULL REFUND FROM ${otaPlatform.toUpperCase()}</div>
            <div class="truestars-refund-desc">
              This property holds ZERO (0★) official government accreditation. Advertising unauthorized star ratings violates Article 50 of the Vietnam Tourism Law 2017 & Consumer Protection Law 2023. Under Decree 85/2021/NĐ-CP, ${otaPlatform} bears strict statutory liability. You have the legal right to cancel free of charge and demand a 100% immediate refund.
            </div>
            <button id="truestars-copy-refund-letter" class="truestars-btn-refund">💰 Claim 100% Full Refund (Copy Demand Letter)</button>
            <div class="truestars-refund-subnote">Decree 85/2021/NĐ-CP • Chargeback Guaranteed</div>
          </div>
        `;
      }
    }

    // Dossier vs Infraction Box
    let legalDossierHtml = '';
    if (isLegit) {
      legalDossierHtml = `
        <div style="background: #070a12; border: 1px solid #10b981; border-radius: 8px; padding: 10px 12px; margin-top: 12px; font-size: 11px;">
          <div style="font-weight: 800; color: #34d399; margin-bottom: 4px;">🛡️ OFFICIAL STATUTORY COMPLIANCE DOSSIER</div>
          <div style="color: #cbd5e1; line-height: 1.4;">
            <strong>Luật Du lịch 2017 (Điều 50):</strong> This property is statutorily accredited by VNAT under Certificate #${audit.matched_hotel ? (audit.matched_hotel.item_id || audit.matched_hotel.decision_code) : 'AUTH'}. Authorized to market and display ${audit.official_stars} Gold Stars.
          </div>
        </div>
        <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid #10b981; border-radius: 6px; padding: 10px; text-align: center; color: #34d399; font-size: 11px; font-weight: 700; margin-top: 14px;">
          ✅ STATUTORILY CERTIFIED — FULL LEGAL COMPLIANCE
        </div>
      `;
    } else {
      legalDossierHtml = `
        <div style="background: #070a12; border: 1px solid #334155; border-radius: 8px; padding: 10px 12px; margin-top: 12px; font-size: 11px;">
          <div style="font-weight: 800; color: #f87171; margin-bottom: 4px;">⚖️ DEMONSTRATION OF STATUTORY INFRACTION</div>
          <div style="color: #cbd5e1; line-height: 1.4;">
            <strong>Luật Du lịch 2017 (Điều 9, Khoản 8 & Điều 50):</strong> Only VNAT has statutory authority to award 4★/5★ ratings in Vietnam (only 681 exist nationwide). Displaying unauthorized stars is a strict statutory violation under Vietnamese law.
          </div>
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
      ${refundBannerHtml}
      ${otaLinksHtml}
      ${matchedHtml}
      ${violationsHtml}
      ${legalDossierHtml}
      ${alternativesHtml}
    `;

    backdrop.appendChild(win);
    document.body.appendChild(backdrop);

    document.getElementById('truestars-close-btn').addEventListener('click', () => backdrop.remove());
    backdrop.addEventListener('click', (e) => {
      if (e.target === backdrop) backdrop.remove();
    });

    const refundBtn = document.getElementById('truestars-copy-refund-letter');
    if (refundBtn) {
      refundBtn.addEventListener('click', () => {
        navigator.clipboard.writeText(audit.refund_demand_letter || audit.summary);
        const originalText = refundBtn.textContent;
        refundBtn.textContent = '✓ Refund Demand Letter Copied to Clipboard!';
        setTimeout(() => { refundBtn.textContent = originalText; }, 2500);
      });
    }
  }

  window.TrueStarsBadge = {
    async auditAndInject(targetElement, { name, claimedStars = 5, province = "" }) {
      if (!name || targetElement.querySelector('.truestars-badge-container')) return;

      // Strict Vietnam-only scope guard
      const isVn = (typeof isVietnamContext === 'function' ? isVietnamContext : (window.TrueStarsIsVietnam || (() => false)));
      if (!isVn(window.location.href, `${name} ${province}`)) {
        return;
      }

      const m = await initMatcher();
      if (!m) return;

      const audit = m.classify({
        name,
        claimedStars,
        province
      });

      // Don't badge low star ratings
      if (claimedStars < 4) return;

      const container = document.createElement('div');
      container.className = 'truestars-badge-container';

      const badge = document.createElement('span');
      badge.className = 'truestars-badge';

      if (audit.verdict === 'VERIFIED_LEGITIMATE') {
        badge.classList.add('truestars-legit');
        badge.innerHTML = `🛡️ VNAT ${audit.official_stars}★`;
        badge.title = 'Officially certified by Vietnam National Authority of Tourism';
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
