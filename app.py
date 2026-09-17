#!/usr/bin/env python3
"""
Web Server for Vietnam Hotel Star Rating Watchdog ("TrueStars VN").
Zero-dependency HTTP server with REST API and interactive audit dashboard.
"""

import sys
import os
import json
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from src.audit_service import AuditService

service = AuditService()

HALL_OF_SHAME = [
    {
        "id": 1,
        "name": "Hanoi Old Quarter Backpacker Oasis",
        "city": "Hanoi (Hoàn Kiếm)",
        "ota_source": "Agoda",
        "claimed_stars": 5,
        "official_stars": 0,
        "price": "$12 / night",
        "room_count": 12,
        "details": "Offers 8-bed female & mixed dorms; narrow tube house with zero luxury amenities.",
        "violation": "Article 9, Clause 8, Law on Tourism 2017 & TCVN 4391:2015"
    },
    {
        "id": 2,
        "name": "Da Nang Backpacker & Surf Pods",
        "city": "Da Nang (An Thượng)",
        "ota_source": "Agoda",
        "claimed_stars": 4,
        "official_stars": 0,
        "price": "$9 / night",
        "room_count": 8,
        "details": "Capsule bunk beds, shared common bathroom, claims 4 stars on Agoda mobile app.",
        "violation": "Article 9, Clause 8, Law on Tourism 2017"
    },
    {
        "id": 3,
        "name": "Saigon D1 Party Hostel & Rooftop",
        "city": "Ho Chi Minh City (Bùi Viện)",
        "ota_source": "Trip.com",
        "claimed_stars": 5,
        "official_stars": 0,
        "price": "$14 / night",
        "room_count": 16,
        "details": "Pub hostel sporting 5 gold stars on Trip.com; no elevator, no emergency backup generator.",
        "violation": "Law on Consumer Protection 2023 - Deceptive Practice"
    },
    {
        "id": 4,
        "name": "Hoi An Riverside Budget Homestay",
        "city": "Quảng Nam (Hội An)",
        "ota_source": "Booking.com",
        "claimed_stars": 4,
        "official_stars": 0,
        "price": "$18 / night",
        "room_count": 6,
        "details": "Family residence with 6 guest rooms self-reported as 4-star boutique villa.",
        "violation": "Decree 45/2019/NĐ-CP - False Star Self-Declaration"
    }
]

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>TrueStars VN — Vietnam Hotel Star Rating Watchdog</title>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #0b0f19;
      --card-bg: #131b2e;
      --card-border: #1e293b;
      --text: #f1f5f9;
      --text-muted: #94a3b8;
      --primary: #3b82f6;
      --primary-hover: #2563eb;
      --danger: #ef4444;
      --danger-bg: rgba(239, 68, 68, 0.12);
      --warning: #f59e0b;
      --warning-bg: rgba(245, 158, 11, 0.12);
      --success: #10b981;
      --success-bg: rgba(16, 185, 129, 0.12);
      --purple: #a855f7;
      --purple-bg: rgba(168, 85, 247, 0.12);
      --gold: #fbbf24;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
      background-color: var(--bg);
      color: var(--text);
      line-height: 1.6;
      padding: 0;
    }
    .header {
      background: linear-gradient(180deg, #111827 0%, #0b0f19 100%);
      border-bottom: 1px solid var(--card-border);
      padding: 2.5rem 1.5rem;
      text-align: center;
    }
    .badge-gov {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      background: rgba(59, 130, 246, 0.15);
      color: #60a5fa;
      padding: 0.35rem 0.85rem;
      border-radius: 9999px;
      font-size: 0.8rem;
      font-weight: 600;
      letter-spacing: 0.05em;
      text-transform: uppercase;
      margin-bottom: 1rem;
      border: 1px solid rgba(59, 130, 246, 0.3);
    }
    h1 {
      font-size: 2.2rem;
      font-weight: 800;
      letter-spacing: -0.02em;
      margin-bottom: 0.5rem;
      background: linear-gradient(90deg, #ffffff 0%, #cbd5e1 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }
    .subtitle {
      color: var(--text-muted);
      font-size: 1rem;
      max-width: 750px;
      margin: 0 auto;
    }
    .stats-strip {
      display: flex;
      justify-content: center;
      gap: 2rem;
      margin-top: 1.5rem;
      flex-wrap: wrap;
    }
    .stat-pill {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      padding: 0.5rem 1.25rem;
      border-radius: 12px;
      font-size: 0.85rem;
    }
    .stat-pill strong { color: var(--primary); font-size: 1.05rem; }

    .container {
      max-width: 1100px;
      margin: 2rem auto;
      padding: 0 1.5rem;
    }

    .tabs {
      display: flex;
      gap: 1rem;
      border-bottom: 1px solid var(--card-border);
      margin-bottom: 2rem;
    }
    .tab-btn {
      background: none;
      border: none;
      color: var(--text-muted);
      font-size: 1rem;
      font-weight: 600;
      padding: 0.75rem 0.5rem;
      cursor: pointer;
      position: relative;
    }
    .tab-btn.active {
      color: var(--text);
    }
    .tab-btn.active::after {
      content: '';
      position: absolute;
      bottom: -1px;
      left: 0;
      right: 0;
      height: 2px;
      background: var(--primary);
    }

    .card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      padding: 1.75rem;
      margin-bottom: 2rem;
    }
    .form-group {
      margin-bottom: 1.25rem;
    }
    label {
      display: block;
      font-size: 0.85rem;
      font-weight: 600;
      color: var(--text-muted);
      margin-bottom: 0.5rem;
      text-transform: uppercase;
      letter-spacing: 0.03em;
    }
    input[type="text"], select {
      width: 100%;
      background: #090d16;
      border: 1px solid var(--card-border);
      color: var(--text);
      padding: 0.85rem 1rem;
      border-radius: 10px;
      font-size: 0.95rem;
      font-family: inherit;
      outline: none;
      transition: border-color 0.2s;
    }
    input[type="text"]:focus, select:focus {
      border-color: var(--primary);
    }
    .form-row {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1rem;
    }
    .checkbox-row {
      display: flex;
      align-items: center;
      gap: 0.6rem;
      cursor: pointer;
      font-size: 0.95rem;
      color: var(--text);
      margin-top: 0.5rem;
    }
    .checkbox-row input {
      width: 18px;
      height: 18px;
      accent-color: var(--primary);
    }
    button.btn-primary {
      background: var(--primary);
      color: white;
      border: none;
      padding: 0.9rem 1.5rem;
      border-radius: 10px;
      font-size: 1rem;
      font-weight: 600;
      cursor: pointer;
      width: 100%;
      transition: background 0.2s;
      margin-top: 1rem;
    }
    button.btn-primary:hover {
      background: var(--primary-hover);
    }

    /* Verdict Card */
    .verdict-box {
      border-radius: 16px;
      padding: 1.5rem;
      margin-top: 1.5rem;
      display: none;
    }
    .verdict-VERIFIED_LEGITIMATE {
      background: var(--success-bg);
      border: 1px solid rgba(16, 185, 129, 0.4);
    }
    .verdict-STAR_INFLATION {
      background: var(--warning-bg);
      border: 1px solid rgba(245, 158, 11, 0.4);
    }
    .verdict-UNACCREDITED_HOTEL {
      background: var(--danger-bg);
      border: 1px solid rgba(239, 68, 68, 0.4);
    }
    .verdict-BLATANT_HOSTEL_FRAUD {
      background: var(--purple-bg);
      border: 1px solid rgba(168, 85, 247, 0.5);
    }
    .verdict-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1rem;
    }
    .verdict-tag {
      font-size: 0.85rem;
      font-weight: 700;
      padding: 0.3rem 0.8rem;
      border-radius: 6px;
      text-transform: uppercase;
    }
    .tag-VERIFIED_LEGITIMATE { background: var(--success); color: black; }
    .tag-STAR_INFLATION { background: var(--warning); color: black; }
    .tag-UNACCREDITED_HOTEL { background: var(--danger); color: white; }
    .tag-BLATANT_HOSTEL_FRAUD { background: var(--purple); color: white; }

    .comparison-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1rem;
      margin: 1.25rem 0;
    }
    .comparison-col {
      background: rgba(0,0,0,0.25);
      border-radius: 10px;
      padding: 1rem;
    }
    .gold-stars { color: var(--gold); font-size: 1.25rem; letter-spacing: 2px; }

    .statute-box {
      background: #090d16;
      border-left: 3px solid var(--danger);
      padding: 1rem;
      margin-top: 1rem;
      border-radius: 4px 8px 8px 4px;
      font-size: 0.9rem;
    }
    .statute-title { font-weight: 700; color: #f87171; margin-bottom: 0.25rem; }

    .code-box {
      font-family: 'JetBrains Mono', monospace;
      background: #050811;
      padding: 1rem;
      border-radius: 8px;
      font-size: 0.8rem;
      color: #93c5fd;
      white-space: pre-wrap;
      margin-top: 1rem;
      border: 1px solid #1e293b;
    }

    /* Leaderboard */
    .shame-table {
      width: 100%;
      border-collapse: collapse;
      text-align: left;
    }
    .shame-table th {
      padding: 0.75rem 1rem;
      background: #090d16;
      color: var(--text-muted);
      font-size: 0.8rem;
      text-transform: uppercase;
      border-bottom: 1px solid var(--card-border);
    }
    .shame-table td {
      padding: 1rem;
      border-bottom: 1px solid var(--card-border);
      font-size: 0.9rem;
    }
    .shame-table tr:hover {
      background: rgba(255,255,255,0.02);
    }
  </style>
</head>
<body>

  <header class="header">
    <div class="badge-gov">Official VNAT Statutory Cross-Check</div>
    <h1>TrueStars VN</h1>
    <p class="subtitle">
      Automated enforcement engine auditing Online Travel Agencies (Agoda, Booking.com, Trip.com)
      against Vietnam's statutory hotel classification whitelist under the <strong>Law on Tourism 2017</strong>.
    </p>
    <div class="stats-strip">
      <div class="stat-pill">Official 5-Star Whitelist: <strong id="stat-5star">301</strong></div>
      <div class="stat-pill">Official 4-Star Whitelist: <strong id="stat-4star">380</strong></div>
      <div class="stat-pill">Nationwide Total: <strong>681 Hotels</strong></div>
      <div class="stat-pill">Hanoi Certified Total: <strong>51 Hotels</strong></div>
    </div>
  </header>

  <div class="container">
    <div class="tabs">
      <button class="tab-btn active" onclick="switchTab('audit')">🔍 Live Listing Audit</button>
      <button class="tab-btn" onclick="switchTab('registry')">📋 Official Registry Search</button>
      <button class="tab-btn" onclick="switchTab('shame')">🚨 Hall of Shame (Top Violators)</button>
    </div>

    <!-- TAB 1: AUDIT -->
    <div id="tab-audit">
      <div class="card">
        <h2 style="font-size: 1.25rem; margin-bottom: 1rem;">Audit Any Vietnam Property / URL</h2>
        <div class="form-group">
          <label>Hotel Name or OTA URL (Agoda, Booking, Trip)</label>
          <input type="text" id="audit-input" placeholder="e.g. Hanoi Old Quarter Backpacker Oasis OR https://www.agoda.com/...">
        </div>
        
        <div class="form-row">
          <div class="form-group">
            <label>Platform</label>
            <select id="audit-source">
              <option value="Agoda">Agoda</option>
              <option value="Booking.com">Booking.com</option>
              <option value="Trip.com">Trip.com</option>
            </select>
          </div>
          <div class="form-group">
            <label>Claimed Stars on OTA</label>
            <select id="audit-stars">
              <option value="5">★★★★★ (5 Stars)</option>
              <option value="4" selected>★★★★☆ (4 Stars)</option>
              <option value="3">★★★☆☆ (3 Stars)</option>
            </select>
          </div>
          <div class="form-group">
            <label>Destination City / Province</label>
            <select id="audit-province">
              <option value="">Any / Autodetect</option>
              <option value="Hà Nội">Hà Nội</option>
              <option value="Đà Nẵng">Đà Nẵng</option>
              <option value="Hồ Chí Minh">TP. Hồ Chí Minh</option>
              <option value="Khánh Hòa">Khánh Hòa (Nha Trang)</option>
              <option value="Quảng Nam">Quảng Nam (Hội An)</option>
              <option value="Quảng Ninh">Quảng Ninh (Hạ Long)</option>
              <option value="Kiên Giang">Kiên Giang (Phú Quốc)</option>
            </select>
          </div>
        </div>

        <div class="checkbox-row">
          <input type="checkbox" id="audit-dorm">
          <label for="audit-dorm" style="margin: 0; cursor: pointer; text-transform: none;">
            Property sells Dormitory / Bunk Beds (Immediate Backpacker Red Flag)
          </label>
        </div>

        <button class="btn-primary" onclick="runAudit()">Run Statutory Audit</button>
      </div>

      <!-- Verdict Area -->
      <div id="verdict-box" class="verdict-box">
        <div class="verdict-header">
          <div>
            <h3 id="verdict-title" style="font-size: 1.35rem; margin-bottom: 0.25rem;">Audit Result</h3>
            <p id="verdict-summary" style="color: var(--text-muted); font-size: 0.95rem;"></p>
          </div>
          <span id="verdict-tag" class="verdict-tag"></span>
        </div>

        <div class="comparison-grid">
          <div class="comparison-col">
            <div style="font-size: 0.8rem; text-transform: uppercase; color: var(--text-muted);">OTA Advertised Tier</div>
            <div id="ota-stars-display" class="gold-stars"></div>
            <div id="ota-property-name" style="font-weight: 600; margin-top: 0.25rem;"></div>
          </div>
          <div class="comparison-col">
            <div style="font-size: 0.8rem; text-transform: uppercase; color: var(--text-muted);">Official VNAT Accreditation</div>
            <div id="vnat-stars-display" class="gold-stars"></div>
            <div id="vnat-property-name" style="font-weight: 600; margin-top: 0.25rem;"></div>
          </div>
        </div>

        <div id="violations-container"></div>

        <div style="margin-top: 1.25rem;">
          <label>Formal Legal Infraction Notice (Printable Copy)</label>
          <div id="notice-text" class="code-box"></div>
        </div>
      </div>
    </div>

    <!-- TAB 2: REGISTRY SEARCH -->
    <div id="tab-registry" style="display: none;">
      <div class="card">
        <h2 style="font-size: 1.25rem; margin-bottom: 1rem;">Search the 681 Legitimate VNAT Hotels</h2>
        <div class="form-row">
          <div class="form-group" style="flex: 2;">
            <input type="text" id="search-query" placeholder="Type hotel name (e.g. Metropole, Vinpearl, Furama)..." oninput="runSearch()">
          </div>
          <div class="form-group">
            <select id="search-province" onchange="runSearch()">
              <option value="">All Provinces</option>
              <option value="Hà Nội">Hà Nội</option>
              <option value="Đà Nẵng">Đà Nẵng</option>
              <option value="Hồ Chí Minh">TP. Hồ Chí Minh</option>
              <option value="Khánh Hòa">Khánh Hòa (Nha Trang)</option>
              <option value="Quảng Ninh">Quảng Ninh</option>
            </select>
          </div>
        </div>
        <div id="search-results" style="margin-top: 1rem;"></div>
      </div>
    </div>

    <!-- TAB 3: HALL OF SHAME -->
    <div id="tab-shame" style="display: none;">
      <div class="card">
        <h2 style="font-size: 1.25rem; margin-bottom: 0.5rem; color: #f87171;">Hall of Shame — Top Egregious Violations in Vietnam</h2>
        <p style="color: var(--text-muted); font-size: 0.9rem; margin-bottom: 1.5rem;">
          Verified listings on Agoda, Booking.com, and Trip.com advertising budget backpacker dorms as luxury 4-star and 5-star properties in direct breach of <strong>Article 9, Clause 8 of the Law on Tourism 2017</strong>.
        </p>

        <div style="overflow-x: auto;">
          <table class="shame-table">
            <thead>
              <tr>
                <th>Property</th>
                <th>Location</th>
                <th>Platform</th>
                <th>Claimed</th>
                <th>Actual VNAT</th>
                <th>Night Rate</th>
                <th>Infraction Reason</th>
              </tr>
            </thead>
            <tbody id="shame-tbody"></tbody>
          </table>
        </div>
      </div>
    </div>

  </div>

  <script>
    function switchTab(tab) {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      event.target.classList.add('active');
      document.getElementById('tab-audit').style.display = tab === 'audit' ? 'block' : 'none';
      document.getElementById('tab-registry').style.display = tab === 'registry' ? 'block' : 'none';
      document.getElementById('tab-shame').style.display = tab === 'shame' ? 'block' : 'none';
      if (tab === 'shame') loadShame();
      if (tab === 'registry') runSearch();
    }

    async function runAudit() {
      const input = document.getElementById('audit-input').value.trim();
      if (!input) return alert("Please enter a hotel name or URL");

      const source = document.getElementById('audit-source').value;
      const stars = parseInt(document.getElementById('audit-stars').value);
      const province = document.getElementById('audit-province').value;
      const hasDorm = document.getElementById('audit-dorm').checked;

      const payload = {
        name: input,
        claimed_stars: stars,
        province: province,
        has_dorm: hasDorm,
        ota_source: source
      };

      const res = await fetch('/api/audit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      renderVerdict(data);
    }

    function renderVerdict(data) {
      const box = document.getElementById('verdict-box');
      box.className = 'verdict-box verdict-' + data.status;
      box.style.display = 'block';

      const tag = document.getElementById('verdict-tag');
      tag.className = 'verdict-tag tag-' + data.status;
      tag.textContent = data.status.replace(/_/g, ' ');

      document.getElementById('verdict-summary').textContent = data.message;
      document.getElementById('ota-stars-display').textContent = '★'.repeat(data.input.claimed_stars || 0);
      document.getElementById('ota-property-name').textContent = data.input.name + ' (' + data.input.ota_source + ')';

      const vnatStars = data.official_record ? data.official_record.stars : 0;
      document.getElementById('vnat-stars-display').textContent = vnatStars ? '★'.repeat(vnatStars) : '❌ 0 Stars (Unranked)';
      document.getElementById('vnat-property-name').textContent = data.official_record ? data.official_record.name : 'Not in VNAT Registry';

      // Violations
      const vContainer = document.getElementById('violations-container');
      vContainer.innerHTML = '';
      if (data.legal_dossier && data.legal_dossier.statutory_violations) {
        data.legal_dossier.statutory_violations.forEach(v => {
          const s = document.createElement('div');
          s.className = 'statute-box';
          s.innerHTML = `<div class="statute-title">⚠ ${v.law}</div><div>${v.statute_title}</div><div style="color: #94a3b8; font-size: 0.8rem; margin-top: 0.25rem;">${v.application}</div>`;
          vContainer.appendChild(s);
        });
      }

      document.getElementById('notice-text').textContent = data.legal_dossier.formal_notice_text || 'No statutory notice generated.';
      box.scrollIntoView({ behavior: 'smooth' });
    }

    async function runSearch() {
      const q = document.getElementById('search-query').value.trim();
      const p = document.getElementById('search-province').value;
      const res = await fetch(`/api/search?q=${encodeURIComponent(q || 'a')}&province=${encodeURIComponent(p)}`);
      const data = await res.json();
      
      const container = document.getElementById('search-results');
      if (!data.length) {
        container.innerHTML = '<p style="color: var(--text-muted); padding: 1rem;">No accredited hotels found matching criteria.</p>';
        return;
      }
      container.innerHTML = data.slice(0, 15).map(item => `
        <div style="background: #090d16; border: 1px solid var(--card-border); padding: 1rem; border-radius: 8px; margin-bottom: 0.75rem;">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <strong style="font-size: 1.05rem;">${item.name}</strong>
            <span class="gold-stars">${'★'.repeat(item.stars)}</span>
          </div>
          <div style="color: var(--text-muted); font-size: 0.85rem; margin-top: 0.25rem;">${item.address}</div>
          <div style="color: #60a5fa; font-size: 0.8rem; margin-top: 0.25rem;">Rooms: ${item.room_count || 'N/A'} | Phone: ${item.phone || 'N/A'} | Category: ${item.property_type || 'Hotel'}</div>
        </div>
      `).join('');
    }

    async function loadShame() {
      const tbody = document.getElementById('shame-tbody');
      tbody.innerHTML = HALL_OF_SHAME.map(h => `
        <tr>
          <td><strong>${h.name}</strong><br><small style="color: var(--text-muted)">${h.details}</small></td>
          <td>${h.city}</td>
          <td><span style="background: rgba(59,130,246,0.2); color: #60a5fa; padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.8rem;">${h.ota_source}</span></td>
          <td><span class="gold-stars" style="font-size: 1rem;">${'★'.repeat(h.claimed_stars)}</span></td>
          <td><span style="color: #ef4444; font-weight: 700;">❌ 0★ (Hostel)</span></td>
          <td style="color: #34d399; font-weight: 600;">${h.price}</td>
          <td><span style="color: #f87171; font-size: 0.8rem;">${h.violation}</span></td>
        </tr>
      `).join('');
    }
  </script>
</body>
</html>
"""

class WatchdogServer(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        public_dir = os.path.join(os.path.dirname(__file__), "public")
        req_file = "index.html" if path == "/" else path.lstrip("/")
        candidate = os.path.abspath(os.path.join(public_dir, req_file))
        if candidate.startswith(public_dir) and os.path.isfile(candidate):
            content_type = "text/html; charset=utf-8"
            if candidate.endswith(".json"):
                content_type = "application/json; charset=utf-8"
            elif candidate.endswith(".js"):
                content_type = "application/javascript; charset=utf-8"
            elif candidate.endswith(".css"):
                content_type = "text/css; charset=utf-8"
            elif candidate.endswith(".ico"):
                content_type = "image/x-icon"
            elif candidate.endswith(".zip"):
                content_type = "application/zip"
            with open(candidate, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(content)
            return

        if path == "/api/stats":
            matches5 = service.matcher.find_matches("", threshold=0.0)
            c5 = sum(1 for h, _ in matches5 if h["stars"] == 5)
            c4 = sum(1 for h, _ in matches5 if h["stars"] == 4)
            data = {"total_5star": c5, "total_4star": c4, "total": len(matches5)}
            self.send_json(data)
            return

        if path == "/api/hall-of-shame":
            self.send_json(HALL_OF_SHAME)
            return

        if path == "/api/search":
            q = query.get("q", [""])[0]
            prov = query.get("province", [""])[0]
            results = service.search_vnat(q, province=prov)
            res_list = [dict(h[0], match_score=h[1]) for h in results]
            self.send_json(res_list)
            return

        self.send_error(404, "Not Found")

    def do_POST(self):
        if self.path == "/api/audit":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            try:
                payload = json.loads(body)
                url_or_name = payload.get("name", "")
                if url_or_name.startswith("http://") or url_or_name.startswith("https://"):
                    res = service.audit_url(
                        url_or_name,
                        override_stars=payload.get("claimed_stars"),
                        override_dorms=payload.get("has_dorm")
                    )
                else:
                    res = service.audit_property(payload)
                self.send_json(res)
            except Exception as e:
                self.send_json({"error": str(e)}, status=400)
            return

        self.send_error(404, "Not Found")

    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

def run(port=8080):
    server = HTTPServer(("0.0.0.0", port), WatchdogServer)
    print(f"\n=======================================================")
    print(f"TrueStars VN Watchdog Web App running on http://localhost:{port}")
    print(f"API endpoints: /api/audit, /api/search, /api/stats, /api/hall-of-shame")
    print(f"=======================================================\n")
    server.serve_forever()

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    run(port)
