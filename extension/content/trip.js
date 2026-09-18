/**
 * TrueStars VN — Trip.com Content Script
 */

(function () {
  if (!window.location.hostname.includes('trip.com')) return;

  function checkVn(url = '', text = '') {
    if (typeof isVietnamContext === 'function') return isVietnamContext(url, text);
    if (window.TrueStarsIsVietnam) return window.TrueStarsIsVietnam(url, text);
    const combined = `${url} ${text}`.toLowerCase();
    return combined.includes('countryid=31') || combined.includes('/vietnam-hotels') || combined.includes('-vn') || combined.includes('vietnam');
  }

  function isVietnamTripPage() {
    if (checkVn(window.location.href)) return true;
    const breadcrumb = document.querySelector('[class*="breadcrumb"], nav[aria-label="breadcrumb"]');
    if (breadcrumb && checkVn('', breadcrumb.textContent)) return true;
    const searchInput = document.querySelector('input[class*="search"], input[class*="destination"]');
    if (searchInput && checkVn('', searchInput.value)) return true;
    if (checkVn('', document.title)) return true;
    const addressEl = document.querySelector('[class*="address"], [class*="location"]');
    if (addressEl && checkVn('', addressEl.textContent)) return true;
    return false;
  }

  function parseTripCard(card) {
    if (card.dataset.truestarsScanned) return;
    card.dataset.truestarsScanned = 'true';

    // Verify card is in Vietnam
    const cardLink = card.querySelector('a')?.href || '';
    const isPageVn = isVietnamTripPage();
    if (!isPageVn && !checkVn(cardLink, card.textContent)) {
      return; // Skip non-Vietnam cards
    }

    const titleEl = card.querySelector('[class*="name"], [class*="hotelName"], h3');
    if (!titleEl) return;
    const name = titleEl.textContent.trim();

    let stars = 0;
    const starEl = card.querySelector('[class*="star"], [class*="diamond"], [aria-label*="star" i]');
    if (starEl) {
      const match = (starEl.getAttribute('aria-label') || starEl.className || starEl.textContent || '').match(/(\d)/);
      if (match) stars = parseInt(match[1], 10);
    }

    if (stars === 0) {
      const text = card.textContent.toLowerCase();
      if (text.includes('5 star') || text.includes('5 diamond')) stars = 5;
      else if (text.includes('4 star') || text.includes('4 diamond')) stars = 4;
      else if (/\b(residence|residences|apartment|apartments|condo|condotel|aparthotel|suite|suites|boutique|villa|villas)\b/i.test(name)) stars = 4;
    }

    const fullText = card.textContent.toLowerCase();
    const hasDorm = /\b(bunk bed|dormitory|dorm|hostel|shared bathroom)\b/i.test(fullText);

    const defaultStars = /\b(residence|residences|apartment|apartments|condo|condotel|aparthotel|suite|suites|boutique|villa|villas)\b/i.test(name) ? 4 : 5;

    if (titleEl && window.TrueStarsBadge) {
      window.TrueStarsBadge.auditAndInject(titleEl.parentElement || titleEl, {
        name,
        claimedStars: stars || defaultStars,
        hasDorm
      });
    }
  }

  function parseTripPropertyHeader() {
    if (!isVietnamTripPage()) return;
    const headerTitle = document.querySelector('h1[class*="hotelName"], h1[class*="detail-headline"], h1.name');
    if (!headerTitle || headerTitle.dataset.truestarsScanned) return;
    headerTitle.dataset.truestarsScanned = 'true';

    const name = headerTitle.textContent.trim();
    let stars = 0;
    const starEl = document.querySelector('[class*="star"], [class*="diamond"]');
    if (starEl) {
      const match = (starEl.getAttribute('aria-label') || starEl.className || starEl.textContent || '').match(/(\d)/);
      if (match) stars = parseInt(match[1], 10);
    }
    if (stars === 0) {
      const text = document.body.textContent.toLowerCase();
      if (text.includes('5 star') || text.includes('5 diamond')) stars = 5;
      else if (text.includes('4 star') || text.includes('4 diamond')) stars = 4;
      else stars = 5;
    }
    const hasDorm = /\b(bunk bed|dormitory|dorm|hostel)\b/i.test(document.body.textContent);

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
      '[class*="hotel-info"], [class*="list-card"], [class*="HotelCard"], [data-testid="hotel-card"]'
    );
    cards.forEach(parseTripCard);
    parseTripPropertyHeader();
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
