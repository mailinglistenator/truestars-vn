/**
 * TrueStars VN — Trip.com Content Script
 */

(function () {
  if (!window.location.hostname.includes('trip.com')) return;

  function parseTripCard(card) {
    if (card.dataset.truestarsScanned) return;
    card.dataset.truestarsScanned = 'true';

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
    }

    const fullText = card.textContent.toLowerCase();
    const hasDorm = /\b(bunk bed|dormitory|dorm|hostel|shared bathroom)\b/i.test(fullText);

    if (titleEl && window.TrueStarsBadge) {
      window.TrueStarsBadge.auditAndInject(titleEl.parentElement || titleEl, {
        name,
        claimedStars: stars || 5,
        hasDorm
      });
    }
  }

  function scanAll() {
    const cards = document.querySelectorAll(
      '[class*="hotel-info"], [class*="list-card"], [class*="HotelCard"], [data-testid="hotel-card"]'
    );
    cards.forEach(parseTripCard);
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
