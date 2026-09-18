/**
 * TrueStars VN — Booking.com Content Script
 * Detects hotel cards on search pages and property pages on Booking.com.
 */

(function () {
  if (!window.location.hostname.includes('booking.com')) return;

  function checkVn(url = '', text = '') {
    if (typeof isVietnamContext === 'function') return isVietnamContext(url, text);
    if (window.TrueStarsIsVietnam) return window.TrueStarsIsVietnam(url, text);
    const combined = `${url} ${text}`.toLowerCase();
    return combined.includes('/hotel/vn/') || combined.includes('dest_id=233') || combined.includes('country=vn') || combined.includes('vietnam');
  }

  function isVietnamBookingPage() {
    if (checkVn(window.location.href)) return true;
    const breadcrumbs = document.querySelector('ol.bui-breadcrumb__list, nav[aria-label="breadcrumb"], [data-testid="breadcrumbs"]');
    if (breadcrumbs && checkVn('', breadcrumbs.textContent)) return true;
    const searchInput = document.querySelector('input[name="ss"], [data-testid="destination-container"] input');
    if (searchInput && checkVn('', searchInput.value)) return true;
    if (checkVn('', document.title)) return true;
    const addressEl = document.querySelector('.hp_address_subtitle, [data-node_tt_id="location_score_tooltip"]');
    if (addressEl && checkVn('', addressEl.textContent)) return true;
    return false;
  }

  function parseBookingCard(card) {
    if (card.dataset.truestarsScanned) return;
    card.dataset.truestarsScanned = 'true';

    // Verify card is in Vietnam
    const cardLink = card.querySelector('a')?.href || '';
    const isPageVn = isVietnamBookingPage();
    if (!isPageVn && !checkVn(cardLink, card.textContent)) {
      return; // Skip non-Vietnam cards
    }

    // 1. Hotel Name
    const titleEl = card.querySelector('[data-testid="title"]') || card.querySelector('h3');
    if (!titleEl) return;
    const name = titleEl.textContent.trim();

    // 2. Stars vs Quality Rating
    let stars = 0;
    const starsContainer = card.querySelector('[data-testid="rating-stars"]') ||
                           card.querySelector('[data-testid="quality-rating"]');
    if (starsContainer) {
      const svgs = starsContainer.querySelectorAll('svg');
      if (svgs && svgs.length > 0) {
        stars = svgs.length;
      } else {
        const aria = starsContainer.getAttribute('aria-label') || '';
        const match = aria.match(/(\d)/);
        if (match) stars = parseInt(match[1], 10);
      }
    }

    if (stars === 0) {
      const cardText = card.textContent.toLowerCase();
      if (cardText.includes('5-star') || cardText.includes('5 out of 5')) stars = 5;
      else if (cardText.includes('4-star') || cardText.includes('4 out of 5')) stars = 4;
      else if (/\b(residence|residences|apartment|apartments|condo|condotel|aparthotel|suite|suites|boutique|villa|villas)\b/i.test(name)) stars = 4;
    }

    // 3. Dorm bed detection
    const fullText = card.textContent.toLowerCase();
    const hasDorm = /\b(bunk bed|dormitory|dorm|bed in|shared bathroom|hostel)\b/i.test(fullText);

    const defaultStars = /\b(residence|residences|apartment|apartments|condo|condotel|aparthotel|suite|suites|boutique|villa|villas)\b/i.test(name) ? 4 : 5;

    if (titleEl && window.TrueStarsBadge) {
      window.TrueStarsBadge.auditAndInject(titleEl.parentElement || titleEl, {
        name,
        claimedStars: stars || defaultStars,
        hasDorm
      });
    }
  }

  function parseBookingHeader() {
    if (!isVietnamBookingPage()) return; // Skip non-Vietnam single hotel pages
    const headerTitle = document.querySelector('#hp_hotel_name') ||
                        document.querySelector('[data-testid="header-title"]') ||
                        document.querySelector('h2.pp-header__title');
    if (!headerTitle || headerTitle.dataset.truestarsScanned) return;
    headerTitle.dataset.truestarsScanned = 'true';

    const name = headerTitle.textContent.replace(/Hotel/i, ' Hotel').trim();
    let stars = 0;
    const starWrapper = document.querySelector('[data-testid="rating-stars"]') ||
                        document.querySelector('[data-testid="quality-rating"]') ||
                        document.querySelector('.bui-rating') ||
                        document.querySelector('[aria-label*="star" i]') ||
                        document.querySelector('[aria-label*="out of 5" i]');
    if (starWrapper) {
      const svgs = starWrapper.querySelectorAll('svg');
      if (svgs && svgs.length > 0) {
        stars = svgs.length;
      } else {
        const aria = (starWrapper.getAttribute('aria-label') || '').toLowerCase();
        const match = aria.match(/(\d)(\s*|\-)(star|out of 5|sao)/i) || aria.match(/(\d)/);
        if (match) stars = parseInt(match[1], 10);
      }
    }

    if (stars === 0) {
      const pageText = document.body.textContent.toLowerCase();
      if (pageText.includes('5-star') || pageText.includes('5 out of 5')) stars = 5;
      else if (pageText.includes('4-star') || pageText.includes('4 out of 5')) stars = 4;
      else if (/\b(residence|residences|apartment|apartments|condo|condotel|aparthotel|suite|suites|boutique|villa|villas)\b/i.test(name)) stars = 4;
      else stars = 5;
    }

    const pageText = document.body.textContent.toLowerCase();
    const hasDorm = /\b(bunk bed|dormitory|bed in 4-bed|bed in 6-bed|bed in 8-bed|shared dormitory)\b/i.test(pageText);

    if (window.TrueStarsBadge) {
      window.TrueStarsBadge.auditAndInject(headerTitle.parentElement || headerTitle, {
        name,
        claimedStars: stars,
        hasDorm
      });
    }
  }

  function scanAll() {
    const cards = document.querySelectorAll(
      '[data-testid="property-card"], [data-testid="property-card-container"]'
    );
    cards.forEach(parseBookingCard);
    parseBookingHeader();
  }

  const observer = new MutationObserver((mutations) => {
    let shouldScan = false;
    for (const m of mutations) {
      if (m.addedNodes && m.addedNodes.length > 0) {
        shouldScan = true;
        break;
      }
    }
    if (shouldScan) requestAnimationFrame(scanAll);
  });

  observer.observe(document.body, { childList: true, subtree: true });
  scanAll();
})();
