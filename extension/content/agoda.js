/**
 * TrueStars VN — Agoda Content Script
 * Detects hotel cards on search pages and single property pages.
 */

(function () {
  if (!window.location.hostname.includes('agoda.com')) return;

  function parseAgodaCard(card) {
    if (card.dataset.truestarsScanned) return;
    card.dataset.truestarsScanned = 'true';

    // 1. Hotel Name
    const titleEl = card.querySelector('[data-selenium="hotel-name"]') ||
                    card.querySelector('h3') ||
                    card.querySelector('[data-testid="property-card-title"]');
    if (!titleEl) return;
    const name = titleEl.textContent.trim();

    // 2. Stars
    let stars = 0;
    // Check ficon stars
    const starIcons = card.querySelectorAll('.ficon-star-10, .ficon-star-5, svg[data-selenium="star-rating"]');
    if (starIcons && starIcons.length > 0) {
      stars = starIcons.length;
    } else {
      // Check aria-labels or text
      const starWrapper = card.querySelector('[data-selenium="star-rating"], [aria-label*="star" i]');
      if (starWrapper) {
        const match = (starWrapper.getAttribute('aria-label') || starWrapper.textContent || '').match(/(\d(\.\d)?)/);
        if (match) stars = Math.round(parseFloat(match[1]));
      }
    }

    // Default assume 4/5 if prominent or luxury claimed, otherwise detect
    if (stars === 0) {
      const txt = card.textContent.toLowerCase();
      if (txt.includes('5-star') || txt.includes('5 star')) stars = 5;
      else if (txt.includes('4-star') || txt.includes('4 star')) stars = 4;
    }

    // 3. Dorm / Bunk Bed detection
    const cardText = card.textContent.toLowerCase();
    const hasDorm = /\b(bunk|dorm|dormitory|shared bathroom|capsule|hostel)\b/i.test(cardText);

    // Target injection container
    const target = card.querySelector('[data-selenium="hotel-name"]') || titleEl;
    if (target && window.TrueStarsBadge) {
      window.TrueStarsBadge.auditAndInject(target.parentElement || target, {
        name,
        claimedStars: stars || 5, // audit if high-claim or hostel
        hasDorm
      });
    }
  }

  function parseAgodaPropertyHeader() {
    const headerTitle = document.querySelector('[data-selenium="hotel-header-name"]') ||
                        document.querySelector('h1.HeaderCms__hotel-name') ||
                        document.querySelector('h1[data-selenium="hotel-header-name"]');
    if (!headerTitle || headerTitle.dataset.truestarsScanned) return;
    headerTitle.dataset.truestarsScanned = 'true';

    const name = headerTitle.textContent.trim();
    let stars = 5;
    const starEl = document.querySelector('[data-selenium="hotel-star-rating"]') || document.querySelector('.HeaderCms__stars');
    if (starEl) {
      const match = (starEl.getAttribute('aria-label') || starEl.textContent || '').match(/(\d(\.\d)?)/);
      if (match) stars = Math.round(parseFloat(match[1]));
    }

    const pageText = document.body.textContent.toLowerCase();
    const hasDorm = /\b(bunk bed|dormitory|female dorm|mixed dorm|shared dormitory)\b/i.test(pageText);

    if (window.TrueStarsBadge) {
      window.TrueStarsBadge.auditAndInject(headerTitle.parentElement || headerTitle, {
        name,
        claimedStars: stars,
        hasDorm
      });
    }
  }

  function scanAll() {
    // Search result items
    const cards = document.querySelectorAll(
      '[data-selenium="hotel-item"], .PropertyCard, [data-element-name="property-card-content"], li.hotel-item-box'
    );
    cards.forEach(parseAgodaCard);

    // Single hotel header
    parseAgodaPropertyHeader();
  }

  // Observe DOM for infinite scrolling / dynamic pagination
  const observer = new MutationObserver((mutations) => {
    let shouldScan = false;
    for (const m of mutations) {
      if (m.addedNodes && m.addedNodes.length > 0) {
        shouldScan = true;
        break;
      }
    }
    if (shouldScan) {
      requestAnimationFrame(scanAll);
    }
  });

  observer.observe(document.body, { childList: true, subtree: true });
  scanAll();
})();
