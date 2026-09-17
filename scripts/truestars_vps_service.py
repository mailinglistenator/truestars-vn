import os
import sys
import json
import time
import logging
import requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

app = FastAPI(title="TrueStars VN Autonomous AI Statutory Verifier")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

AUTH_FILE = "/home/hermes/.hermes/auth.json"
ENV_FILE = "/home/hermes/.hermes/.env"

def get_env_vars():
    env = {}
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
    return env

def get_nous_token():
    try:
        with open(AUTH_FILE, "r", encoding="utf-8") as f:
            auth = json.load(f)
        nous = auth.get("providers", {}).get("nous", {})
        token = nous.get("access_token")
        return token
    except Exception as e:
        logging.error(f"Failed to read auth.json: {e}")
        return None

def refresh_token_if_needed():
    try:
        import subprocess
        subprocess.run(
            ["/home/hermes/.hermes/hermes-agent/venv/bin/python", "-m", "hermes_cli.main", "auth", "refresh", "nous"],
            capture_output=True, timeout=15
        )
    except Exception as e:
        logging.error(f"Error refreshing nous token: {e}")

def extract_json(raw_text):
    if not raw_text:
        return {}
    txt = raw_text.strip()
    if "<think>" in txt and "</think>" in txt:
        txt = txt.split("</think>", 1)[1].strip()
    if txt.startswith("```json"):
        txt = txt[7:]
    elif txt.startswith("```"):
        txt = txt[3:]
    if txt.endswith("```"):
        txt = txt[:-3]
    txt = txt.strip()
    try:
        return json.loads(txt)
    except Exception:
        start = txt.find("{")
        end = txt.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(txt[start:end+1])
            except Exception:
                pass
    return {}

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "TrueStars VN Statutory AI Verifier",
        "model": "deepseek/deepseek-v4.1-flash",
        "provider": "Nous Research (Hermes Agent Pool)",
        "fallback": "Groq / Hermes VPS",
        "timestamp": time.time()
    }

@app.post("/api/verify")
async def verify(request: Request):
    t0 = time.time()
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    hotel_name = payload.get("name", "").strip()
    claimed_stars = int(payload.get("claimed_stars", 5))
    platform = payload.get("platform", "Direct Input").strip()
    url = payload.get("url", "").strip()
    city = payload.get("city", "Vietnam").strip()
    has_dorm = bool(payload.get("has_dorm", False))
    candidates = payload.get("candidates", [])

    if not hotel_name and not url:
        raise HTTPException(status_code=400, detail="Hotel name or URL required")

    cand_lines = []
    for c in candidates[:30]:
        cert = c.get("item_id") or c.get("decision_code") or "AUTH"
        stars = c.get("stars", 5)
        addr = c.get("address", "")
        eng = f" ({c.get('english_name')})" if c.get('english_name') else ""
        former = f" [Formerly: {c.get('former_name')}]" if c.get('former_name') else ""
        c_name = c.get("name", "")
        cand_lines.append(f"- {c_name}{eng}{former} [VNAT Cert #{cert}, {stars}★]: {addr}")
    cand_text = "\n".join(cand_lines) if cand_lines else "No certified properties located in this immediate administrative zone."

    system_prompt = (
        "You are TrueStars VN, an autonomous statutory compliance auditor evaluating accommodation listings "
        "under Vietnam's Law on Tourism 2017 (Luật Du lịch số 09/2017/QH14) and national hotel classification standards TCVN 4391:2015.\n\n"
        "Your mission is to conduct an independent, rigorous statutory audit of the audited property against the official VNAT registry candidates provided for this destination.\n\n"
        "Audit Requirements:\n"
        "1. Independent Identity & Rebrand Investigation:\n"
        "   - Investigate whether the property corresponds to any officially accredited hotel in this destination under an international management contract, franchise rebrand, commercial trade name, or English translation.\n"
        "   - Examples in Vietnam: Vinpearl resorts operating under Marriott International management (e.g. Vinpearl Resort & Spa Da Nang -> Danang Marriott Resort & Spa), Vinpearl Condotels managed by Meliá, Landmark 81 Autograph Collection, or Accor/IHG management.\n"
        "   - Carefully cross-check the property location, street address, and geographical landmarks against the candidate registry.\n"
        "2. Statutory Star Rating Verification:\n"
        "   - If the property corresponds to an accredited hotel, verify whether the claimed star rating matches the official VNAT certificate.\n"
        "   - If an accredited hotel claims higher stars on the OTA than certified (e.g. certified 4★, claiming 5★), verdict is \"STAR_INFLATION\".\n"
        "3. Physical Facility Disqualifications:\n"
        "   - If the listing offers shared dormitory / bunk beds, it is structurally and legally disqualified from 4-star or 5-star hotel ranking under TCVN 4391:2015.\n"
        "4. Unaccredited Commercial Deception:\n"
        "   - If the property holds no statutory accreditation in the official registry and cannot be reconciled with any certified hotel, the use of star ratings violates Article 9 Clause 8 and Article 50 of the Law on Tourism 2017.\n\n"
        "Verdicts:\n"
        "- \"VERIFIED_COMPLIANT\": Property is authenticated as an accredited hotel (including genuine operator rebrands) with compliant star rating.\n"
        "- \"STAR_INFLATION\": Property is accredited, but advertised at a higher star level than certified.\n"
        "- \"UNACCREDITED_DECEPTIVE_LISTING\": Property is not in the statutory registry and falsely/deceptively markets star ratings.\n\n"
        "Output strictly valid JSON with keys:\n"
        "- verdict (string)\n"
        "- confidence (float 0.0-1.0)\n"
        "- concise_summary (string: clear factual summary of findings and legal standing)\n"
        "- refund_advisory (string: legal refund analysis under Law on Tourism 2017 & Decree 85/2021/NĐ-CP if deceptive/inflated, or confirmation of compliance if valid)\n"
        "- statutory_infractions (array of strings: legal citations if violated, empty if compliant)\n"
        "- tcvn_deficiencies (array of strings: physical/safety deficiencies under TCVN 4391:2015, empty if compliant)\n"
        "- risk_advisory (string: consumer protection assessment)\n"
        "- reasoning (string: detailed legal and factual rationale explaining your decision, address match, and rebrand analysis)"
    )

    user_prompt = (
        f"Audited Property: {hotel_name}\n"
        f"Claimed Stars: {claimed_stars}★\n"
        f"Platform: {platform}\n"
        f"URL: {url}\n"
        f"Destination: {city}\n"
        f"Offers Dormitory / Shared Bunk Beds: {'YES' if has_dorm else 'NO'}\n\n"
        f"Official VNAT Accredited Hotels in {city}:\n{cand_text}\n\n"
        f"Please conduct your independent statutory audit and return your findings in the required JSON format."
    )

    # 1. Try Nous DeepSeek Flash 4.1 first (timeout 35s)
    token = get_nous_token()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    payload = {
        "model": "deepseek/deepseek-v4.1-flash",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.1,
        "max_tokens": 1500
    }

    try:
        r = requests.post("https://inference-api.nousresearch.com/v1/chat/completions", json=payload, headers=headers, timeout=12)
        if r.status_code in (401, 403):
            refresh_token_if_needed()
            token = get_nous_token()
            headers["Authorization"] = f"Bearer {token}"
            r = requests.post("https://inference-api.nousresearch.com/v1/chat/completions", json=payload, headers=headers, timeout=12)

        if r.status_code == 200:
            res_json = r.json()
            content = res_json["choices"][0]["message"]["content"]
            parsed = extract_json(content)
            if parsed and parsed.get("verdict"):
                parsed["model"] = "deepseek/deepseek-v4.1-flash (Hermes VPS)"
                parsed["latency_ms"] = int((time.time() - t0) * 1000)
                return parsed
            else:
                logging.warning(f"Nous returned invalid/empty JSON, falling back to Groq...")
        else:
            logging.warning(f"Nous returned {r.status_code} ({r.text[:200]}), falling back to Groq...")
    except Exception as e:
        logging.warning(f"Nous request failed: {e}, falling back to Groq...")

    # 2. Fast Fallback: Groq on VPS
    try:
        env = get_env_vars()
        groq_key = env.get("GROQ_API_KEY")
        if groq_key:
            groq_headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {groq_key}"
            }
            groq_payload = {
                "model": "openai/gpt-oss-120b",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.1,
                "max_tokens": 1500
            }
            gr = requests.post("https://api.groq.com/openai/v1/chat/completions", json=groq_payload, headers=groq_headers, timeout=12)
            if gr.status_code == 200:
                res_json = gr.json()
                content = res_json["choices"][0]["message"]["content"]
                parsed = extract_json(content)
                if parsed and parsed.get("verdict"):
                    parsed["model"] = "openai/gpt-oss-120b (Hermes VPS Fallback)"
                    parsed["latency_ms"] = int((time.time() - t0) * 1000)
                    return parsed
    except Exception as e2:
        logging.error(f"Groq fallback failed: {e2}")

    raise HTTPException(status_code=502, detail="All Hermes VPS inference backends unavailable")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5006)
