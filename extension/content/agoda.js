/**
 * TrueStars VN — Agoda Content Script
 * Detects hotel cards on search pages and single property pages.
 */

(function () {
  if (!window.location.hostname.includes('agoda.com')) return;

  function checkVn(url = '', text = '') {
    if (typeof isVietnamContext === 'function') return isVietnamContext(url, text);
    if (window.TrueStarsIsVietnam) return window.TrueStarsIsVietnam(url, text);
    const combined = `${url} ${text}`.toLowerCase();
    return combined.includes('-vn.html') || combined.includes('/hotel/vn/') || combined.includes('countryid=38') || combined.includes('vietnam');
  }

  function isVietnamAgodaPage() {
    if (checkVn(window.location.href)) return true;
    const breadcrumb = document.querySelector('[data-selenium="breadcrumb"], .Breadcrumbs, nav[aria-label="breadcrumb"]');
    if (breadcrumb && checkVn('', breadcrumb.textContent)) return true;
    const searchInput = document.querySelector('[data-selenium="textInput"], input[name="ss"], input[type="search"]');
    if (searchInput && checkVn('', searchInput.value)) return true;
    if (checkVn('', document.title)) return true;
    const addressEl = document.querySelector('[data-selenium="hotel-address"], .HeaderCms__address');
    if (addressEl && checkVn('', addressEl.textContent)) return true;
    return false;
  }

  function parseAgodaCard(card) {
    if (card.dataset.truestarsScanned) return;
    card.dataset.truestarsScanned = 'true';

    // Verify card is in Vietnam
    const cardLink = card.querySelector('a')?.href || '';
    const isPageVn = isVietnamAgodaPage();
    if (!isPageVn && !checkVn(cardLink, card.textContent)) {
      return; // Skip non-Vietnam hotel cards
    }

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
      else if (/\b(residence|residences|apartment|apartments|condo|condotel|aparthotel|suite|suites|boutique|villa|villas)\b/i.test(name)) stars = 4;
    }

    // 3. Dorm / Bunk Bed detection
    const cardText = card.textContent.toLowerCase();
    const hasDorm = /\b(bunk|dorm|dormitory|shared bathroom|capsule|hostel)\b/i.test(cardText);

    const defaultStars = /\b(residence|residences|apartment|apartments|condo|condotel|aparthotel|suite|suites|boutique|villa|villas)\b/i.test(name) ? 4 : 5;

    // Target injection container
    const target = card.querySelector('[data-selenium="hotel-name"]') || titleEl;
    if (target && window.TrueStarsBadge) {
      window.TrueStarsBadge.auditAndInject(target.parentElement || target, {
        name,
        claimedStars: stars || defaultStars,
        hasDorm
      });
    }
  }

  function parseAgodaPropertyHeader() {
    if (!isVietnamAgodaPage()) return; // Skip non-Vietnam single property pages
    const headerTitle = document.querySelector('[data-selenium="hotel-header-name"]') ||
                        document.querySelector('h1.HeaderCms__hotel-name') ||
                        document.querySelector('h1[data-selenium="hotel-header-name"]');
    if (!headerTitle || headerTitle.dataset.truestarsScanned) return;
    headerTitle.dataset.truestarsScanned = 'true';

    const name = headerTitle.textContent.trim();
    let stars = 0;
    const starEl = document.querySelector('[data-selenium="hotel-star-rating"]') || document.querySelector('.HeaderCms__stars');
    if (starEl) {
      const match = (starEl.getAttribute('aria-label') || starEl.textContent || '').match(/(\d(\.\d)?)/);
      if (match) stars = Math.round(parseFloat(match[1]));
    }

    if (stars === 0) {
      const pageText = document.body.textContent.toLowerCase();
      if (pageText.includes('5-star') || pageText.includes('5 star')) stars = 5;
      else if (pageText.includes('4-star') || pageText.includes('4 star')) stars = 4;
      else if (/\b(residence|residences|apartment|apartments|condo|condotel|aparthotel|suite|suites|boutique|villa|villas)\b/i.test(name)) stars = 4;
      else stars = 5;
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
