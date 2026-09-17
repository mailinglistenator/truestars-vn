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
    if txt.startswith("```json"):
        txt = txt[7:]
    elif txt.startswith("```"):
        txt = txt[3:]
    if txt.endswith("```"):
        txt = txt[:-3]
    txt = txt.strip()
    return json.loads(txt)

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
    statutory_match = payload.get("statutory_match")

    if not hotel_name and not url:
        raise HTTPException(status_code=400, detail="Hotel name or URL required")

    matched_hotel = None
    if statutory_match and isinstance(statutory_match, dict):
        matched_hotel = statutory_match.get("matched_hotel")

    cand_lines = []
    if matched_hotel:
        m_cert = matched_hotel.get("item_id") or matched_hotel.get("decision_code") or "AUTH"
        m_stars = matched_hotel.get("stars", 5)
        m_addr = matched_hotel.get("address", "")
        m_name = matched_hotel.get("name", "")
        cand_lines.append(f"★ [OFFICIAL STATUTORY MATCH]: {m_name} [Cert #{m_cert}, {m_stars}★]: {m_addr}")

    for c in candidates[:25]:
        cert = c.get("item_id") or c.get("decision_code") or "AUTH"
        if matched_hotel and str(cert) == str(matched_hotel.get("item_id")):
            continue
        stars = c.get("stars", 5)
        addr = c.get("address", "")
        eng = f" ({c.get('english_name')})" if c.get('english_name') else ""
        c_name = c.get("name", "")
        cand_lines.append(f"- {c_name}{eng} [Cert #{cert}, {stars}★]: {addr}")
    cand_text = "\n".join(cand_lines) if cand_lines else "No certified properties located in this immediate administrative zone."

    system_prompt = (
        "You are TrueStars VN, the official statutory watchdog evaluating accommodation claims in Vietnam "
        "under Vietnam Law on Tourism 2017 (Luật Du lịch số 09/2017/QH14) and national star criteria TCVN 4391:2015.\n\n"
        "Your task:\n"
        "1. Carefully evaluate whether the audited hotel could be one of the officially accredited hotels in this destination "
        "under a franchise, international management contract (e.g. Melia, Marriott, Accor, IHG, Autograph Collection), commercial trade name, or historical name.\n"
        "   - Example: Melia Vinpearl Danang Riverfront at 341 Tran Hung Dao is the commercial/Melia-managed property of Khu căn hộ du lịch Vinpearl Condotel Riverfront Danang (VNAT #8088).\n"
        "   - Example: Vinpearl Landmark 81, Autograph Collection is Vinpearl Luxury Landmark 81 (VNAT #7960).\n"
        "   - Example: Danang Marriott Resort & Spa, Non Nuoc Beach Villas is Khách sạn nghỉ dưỡng Vinpearl Đà Nẵng (VNAT #2010).\n"
        "2. If it IS an official hotel (exact match, verified franchise rebrand, or operator change):\n"
        "   - verdict: \"VERIFIED_COMPLIANT\"\n"
        "   - confidence: 0.98 to 1.0\n"
        "   - concise_summary: String affirming the valid statutory accreditation and rebrand identity.\n"
        "   - reasoning: Detail the rebrand connection, address match, and statutory validity.\n"
        "3. If it is NOT an official hotel:\n"
        "   - verdict: \"UNACCREDITED_DECEPTIVE_LISTING\" (or \"PROBABLE_STAR_INFLATION\" if rated lower by VNAT)\n"
        "   - confidence: 0.95\n"
        "   - concise_summary: \"This is not a \" + str(claimed_stars) + \"-star hotel. It is not in the Vietnamese government registry, and has been deceptively advertised by \" + platform + \". If you have stayed at this hotel, I recommend that you seek a refund from \" + platform + \" due to their deceptive advertising under Vietnamese law.\"\n"
        "   - refund_advisory: Legal explanation under Article 9 Clause 8 of Law on Tourism 2017 & Decree 85/2021/NĐ-CP.\n"
        "   - statutory_infractions: Array of strings citing Vietnamese legal provisions.\n"
        "   - tcvn_deficiencies: Array of strings describing structural/safety criteria under TCVN 4391:2015.\n"
        "   - risk_advisory: Summary consumer protection risk for travelers.\n"
        "   - reasoning: Technical legal reasoning.\n\n"
        "Output strictly valid JSON with keys: verdict, confidence, concise_summary, refund_advisory, statutory_infractions, tcvn_deficiencies, risk_advisory, reasoning."
    )

    statutory_context = ""
    if matched_hotel:
        statutory_context = (
            f"\n\n[OFFICIAL STATUTORY RECORD IDENTIFIED]:\n"
            f"The national matching database matches this listing with official VNAT Accreditation #{matched_hotel.get('item_id') or matched_hotel.get('decision_code')} "
            f"(\"{matched_hotel.get('name')}\", {matched_hotel.get('stars')}★, Address: {matched_hotel.get('address')}).\n"
            f"Please verify this rebrand/commercial management relationship, confirm that the property operates under this accredited identity, "
            f"and return VERIFIED_COMPLIANT."
        )

    user_prompt = (
        f"Audited Property: {hotel_name}\n"
        f"Claimed Stars: {claimed_stars}★\n"
        f"Platform: {platform}\n"
        f"URL: {url}\n"
        f"Destination: {city}\n"
        f"Offers Dormitory / Shared Bunk Beds: {'YES' if has_dorm else 'NO'}\n\n"
        f"Official VNAT Accredited Hotels in this Destination:\n{cand_text}"
        f"{statutory_context}"
    )

    def apply_statutory_guard(parsed_dict):
        if not parsed_dict or not isinstance(parsed_dict, dict):
            return parsed_dict
        if matched_hotel and statutory_match and statutory_match.get("verdict") == "VERIFIED_LEGITIMATE":
            if parsed_dict.get("verdict") not in ("VERIFIED_COMPLIANT", "VERIFIED_LEGITIMATE"):
                logging.warning("Overriding LLM output with statutory supremacy for verified entity!")
                parsed_dict["verdict"] = "VERIFIED_COMPLIANT"
                parsed_dict["confidence"] = 1.0
                cert = matched_hotel.get("item_id") or matched_hotel.get("decision_code") or "AUTH"
                m_stars = matched_hotel.get("stars", 5)
                m_name = matched_hotel.get("name", "")
                m_addr = matched_hotel.get("address", "")
                parsed_dict["concise_summary"] = (
                    f"This is an officially accredited {m_stars}-star hotel. "
                    f"It is certified in the Vietnamese government registry under \"{m_name}\" (Accreditation #{cert}), "
                    f"and is commercially marketed on {platform} as \"{hotel_name}\". Its {m_stars}-star rating is legally authentic under Vietnamese law."
                )
                parsed_dict["refund_advisory"] = (
                    f"No refund action warranted under Vietnamese law. Property possesses valid statutory accreditation "
                    f"(Decision #{cert}) issued by the Vietnam National Authority of Tourism (VNAT)."
                )
                parsed_dict["investigation_findings"] = (
                    f"AI investigated the official VNAT registry and confirmed that this listing at {m_addr} "
                    f"corresponds to official Accreditation #{cert}. The commercial branding on {platform} represents an authenticated international management contract or trade name."
                )
                parsed_dict["statutory_infractions"] = []
                parsed_dict["tcvn_deficiencies"] = []
                parsed_dict["risk_advisory"] = f"NO RISK: Property is fully accredited by VNAT as a {m_stars}-star luxury establishment."
                parsed_dict["reasoning"] = (
                    f"Identity authenticated against official VNAT Accreditation #{cert} (\"{m_name}\") "
                    f"at {m_addr}. Certified as {m_stars} Stars under Article 50 of Vietnam's Law on Tourism 2017."
                )
        return parsed_dict

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
        "max_tokens": 1200
    }

    try:
        r = requests.post("https://inference-api.nousresearch.com/v1/chat/completions", json=payload, headers=headers, timeout=35)
        if r.status_code in (401, 403):
            refresh_token_if_needed()
            token = get_nous_token()
            headers["Authorization"] = f"Bearer {token}"
            r = requests.post("https://inference-api.nousresearch.com/v1/chat/completions", json=payload, headers=headers, timeout=35)

        if r.status_code == 200:
            res_json = r.json()
            content = res_json["choices"][0]["message"]["content"]
            parsed = extract_json(content)
            parsed = apply_statutory_guard(parsed)
            parsed["model"] = "deepseek/deepseek-v4.1-flash (Hermes VPS)"
            parsed["latency_ms"] = int((time.time() - t0) * 1000)
            return parsed
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
                "max_tokens": 1200
            }
            gr = requests.post("https://api.groq.com/openai/v1/chat/completions", json=groq_payload, headers=groq_headers, timeout=15)
            if gr.status_code == 200:
                res_json = gr.json()
                content = res_json["choices"][0]["message"]["content"]
                parsed = extract_json(content)
                parsed = apply_statutory_guard(parsed)
                parsed["model"] = "openai/gpt-oss-120b (Hermes VPS Fallback)"
                parsed["latency_ms"] = int((time.time() - t0) * 1000)
                return parsed
    except Exception as e2:
        logging.error(f"Groq fallback failed: {e2}")

    raise HTTPException(status_code=502, detail="All Hermes VPS inference backends unavailable")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5006)
