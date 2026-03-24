from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import hashlib
import hmac
import secrets
import time
import json
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

# ========== KONSTANTA ==========
URL = "https://accountmtapi.mobilelegends.com"
CAPTCHA_API_URL = "http://149.104.77.174:1337/token"

BINDING_MAP = {
    "mt-and_": "Moonton",
    "fb-and_": "Facebook",
    "vk-and_": "VK",
    "google-and_": "Google Play",
    "apple-and_": "Apple",
    "twitter-and_": "Twitter",
    "tiktok-and_": "TikTok",
    "gamecenter-ios_": "Game Center",
    "googleplay-ios_": "Google Play",
    "gg_": "Google Play",
    "gg-and_": "Google Play",
    "gg-ios_": "Google Play",
    "fb-ios_": "Facebook",
    "vk-ios_": "VK",
    "twitter-ios_": "Twitter",
    "tiktok-ios_": "TikTok",
    "apple-ios_": "Apple",
    "mt-ios_": "Moonton",
    "line-and_": "LINE",
    "line-ios_": "LINE",
    "discord-and_": "Discord",
    "discord-ios_": "Discord"
}

RANK_RANGES = [
    {"min": 0, "max": 4, "rank": "Warrior III"},
    {"min": 5, "max": 9, "rank": "Warrior II"},
    {"min": 10, "max": 14, "rank": "Warrior I"},
    {"min": 15, "max": 19, "rank": "Elite IV"},
    {"min": 20, "max": 24, "rank": "Elite III"},
    {"min": 25, "max": 29, "rank": "Elite II"},
    {"min": 30, "max": 34, "rank": "Elite I"},
    {"min": 35, "max": 39, "rank": "Master IV"},
    {"min": 40, "max": 44, "rank": "Master III"},
    {"min": 45, "max": 49, "rank": "Master II"},
    {"min": 50, "max": 54, "rank": "Master I"},
    {"min": 55, "max": 59, "rank": "Grandmaster IV"},
    {"min": 60, "max": 64, "rank": "Grandmaster III"},
    {"min": 65, "max": 69, "rank": "Grandmaster II"},
    {"min": 70, "max": 74, "rank": "Grandmaster I"},
    {"min": 75, "max": 79, "rank": "Epic IV"},
    {"min": 80, "max": 84, "rank": "Epic III"},
    {"min": 85, "max": 89, "rank": "Epic II"},
    {"min": 90, "max": 94, "rank": "Epic I"},
    {"min": 95, "max": 99, "rank": "Legend IV"},
    {"min": 100, "max": 104, "rank": "Legend III"},
    {"min": 105, "max": 109, "rank": "Legend II"},
    {"min": 110, "max": 114, "rank": "Legend I"},
    {"min": 115, "max": 136, "rank": "Mythic Entry"},
    {"min": 137, "max": 160, "rank": "Mythic"},
    {"min": 161, "max": 185, "rank": "Mythic Honor"},
    {"min": 186, "max": 235, "rank": "Mythical Glory"},
    {"min": 236, "max": 9999, "rank": "Mythical Immortal"}
]

# ========== FUNGSI UTILITY ==========
def md5(text):
    return hashlib.md5(text.encode()).hexdigest()

def make_sign(data):
    so = "&".join(f"{k}={v}" for k, v in sorted(data.items())) + "&op=login"
    return md5(so)

def get_rank_name(rank_level):
    try:
        rank_level = int(rank_level)
        for rank in RANK_RANGES:
            if rank["min"] <= rank_level <= rank["max"]:
                if rank["rank"] == "Mythic":
                    star = rank_level - 136
                    return f"Mythic {star} Star"
                elif rank["rank"] == "Mythic Honor":
                    star = rank_level - 160
                    return f"Mythic Honor {star + 24} Star"
                elif rank["rank"] == "Mythical Glory":
                    star = rank_level - 185
                    return f"Mythical Glory {star + 49} Star"
                elif rank["rank"] == "Mythical Immortal":
                    star = rank_level - 235
                    return f"Mythical Immortal {star + 99} Star"
                return rank["rank"]
        return "Unranked"
    except:
        return "N/A"

def parse_binding(bind_json):
    try:
        data = bind_json.get("data", {})
        bindings = []
        
        if data.get("is_fb_bind", 0) == 1:
            bindings.append("Facebook")
        if data.get("is_vk_bind", 0) == 1:
            bindings.append("VK")
        if data.get("is_google_bind", 0) == 1:
            bindings.append("Google Play")
        if data.get("is_apple_bind", 0) == 1:
            bindings.append("Apple")
        if data.get("is_twitter_bind", 0) == 1:
            bindings.append("Twitter")
        if data.get("is_tiktok_bind", 0) == 1:
            bindings.append("TikTok")
        if data.get("is_mt_bind", 0) == 1:
            bindings.append("Moonton")
        if data.get("is_line_bind", 0) == 1:
            bindings.append("LINE")
        if data.get("is_discord_bind", 0) == 1:
            bindings.append("Discord")
        
        bind_email = data.get("bind_email", [])
        if not bind_email:
            bind_email = data.get("email", [])
        
        for b in bind_email:
            if isinstance(b, str):
                found = False
                for prefix, name in BINDING_MAP.items():
                    if b.startswith(prefix):
                        if name not in bindings:
                            bindings.append(name)
                        found = True
                        break
                
                if not found and b:
                    if "and_" in b:
                        platform = b.split("and_")[0]
                        bindings.append(f"{platform.capitalize()} (Android)")
                    elif "ios_" in b:
                        platform = b.split("ios_")[0]
                        bindings.append(f"{platform.capitalize()} (iOS)")
                    elif b:
                        bindings.append(f"Unknown: {b}")
        
        bindings = list(dict.fromkeys(bindings))
        
        if not bindings:
            if any(key.endswith('_bind') for key in data.keys()):
                return "Bound (Platform Unknown)"
            return "No Bindings"
        
        return " + ".join(bindings)
        
    except Exception as e:
        return "Binding Error"

def get_creation_date(role_id, zone_id):
    API_URL = "https://artixlucien.x10.mx/mlbb/creation"
    k = b"jarellisgod0"
    
    if not role_id or not zone_id:
        return "N/A"
    
    try:
        u = str(role_id)
        z = str(zone_id)
        
        if not u.isdigit() or not z.isdigit():
            return "N/A"
        
        ts = str(int(time.time()))
        nonce = secrets.token_hex(8)
        sig = hmac.new(k, f"{u}:{z}:{ts}:{nonce}".encode(), hashlib.sha256).digest()
        raw = b"|".join([u.encode(), z.encode(), ts.encode(), nonce.encode(), sig])
        payload = raw.hex()
        
        for attempt in range(2):
            try:
                r = requests.post(API_URL, data={"data": payload}, timeout=10)
                r.raise_for_status()
                result = r.json()
                
                if result.get("success"):
                    create_date = result.get("estimated_creation_date", "N/A")
                    return create_date
            except:
                if attempt < 1:
                    time.sleep(1)
                    continue
                return "N/A"
        
        return "N/A"
        
    except Exception:
        return "N/A"

def get_ban_info(jwt, lang="en"):
    url = "https://api.mobilelegends.com/tools/selfservice/punishList"
    
    try:
        headers = {
            "Authorization": f"Bearer {jwt}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        payload = {"lang": lang}
        
        for attempt in range(2):
            try:
                r = requests.post(url, headers=headers, data=payload, timeout=10)
                data = r.json()
                
                if data.get("code") == 0 and data.get("status") == "success":
                    ban_data = data.get("data", [])
                    
                    if not ban_data:
                        return {
                            "banned": False,
                            "reason": "Not Banned",
                            "until": "",
                            "status": "No"
                        }
                    
                    for ban_info in ban_data:
                        if ban_info.get("id"):
                            reason = ban_info.get("reason", "Unknown Reason")
                            until = ban_info.get("unlock_time", "N/A")
                            
                            ban_text = f"Yes (Reason: {reason}"
                            if until and until != "N/A":
                                ban_text += f", Until: {until}"
                            ban_text += ")"
                            
                            return {
                                "banned": True,
                                "reason": reason,
                                "until": until,
                                "status": ban_text
                            }
                    
                    return {
                        "banned": False,
                        "reason": "Not Banned",
                        "until": "",
                        "status": "No"
                    }
            except:
                if attempt < 1:
                    time.sleep(1)
                    continue
                return {
                    "banned": False,
                    "reason": "API Error",
                    "until": "",
                    "status": "No (API Error)"
                }
        
        return {
            "banned": False,
            "reason": "Max Retries Exceeded",
            "until": "",
            "status": "No (Max Retries)"
        }
            
    except Exception as e:
        return {
            "banned": False,
            "reason": str(e),
            "until": "",
            "status": f"No (Error: {str(e)[:50]})"
        }

# ========== API ENDPOINTS ==========

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})

@app.route('/api/captcha', methods=['GET'])
def get_captcha():
    for attempt in range(2):
        try:
            response = requests.get(CAPTCHA_API_URL, timeout=10)
            data = response.json()
            
            if data.get("success") and data.get("token"):
                return jsonify({"success": True, "token": data["token"]})
        except:
            if attempt < 1:
                time.sleep(1)
    
    return jsonify({"success": False, "message": "Failed to get captcha token"})

@app.route('/api/check', methods=['POST'])
def check_account():
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        abck_cookie = data.get('abck_cookie')
        captcha_token = data.get('captcha_token')
        
        if not email or not password:
            return jsonify({"success": False, "status": "error", "message": "Email and password required"})
        
        if not abck_cookie:
            return jsonify({"success": False, "status": "error", "message": "_abck cookie required"})
        
        if not captcha_token:
            return jsonify({"success": False, "status": "error", "message": "Captcha token required"})
        
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "origin": "https://mtacc.mobilelegends.com",
            "referer": "https://mtacc.mobilelegends.com/",
        })
        session.cookies.set("_abck", abck_cookie)
        
        p = md5(password)
        params = {
            "account": email,
            "md5pwd": p,
            "game_token": "",
            "recaptcha_token": "",
            "e_captcha": captcha_token,
            "country": ""
        }
        
        payload = {
            "op": "login",
            "sign": make_sign(params),
            "params": params,
            "lang": "en"
        }
        
        try:
            r = session.post(URL, json=payload, timeout=15)
            
            try:
                js = r.json()
            except:
                return jsonify({"success": False, "status": "error", "message": "Invalid response from MLBB server"})
            
            code = js.get("code")
            message = js.get("message", "Unknown error")
            
            if "Error_ECaptcha_VerifyFail" in str(message):
                return jsonify({"success": False, "status": "captcha_failed", "message": "Captcha verification failed"})
            
            if code == 0:
                login_data = js.get("data") or {}
                session_token = login_data.get("session", "")
                gui = login_data.get("guid", "")
                
                if not session_token:
                    return jsonify({"success": False, "status": "invalid", "message": "No session token"})
                
                jwt_payload = {"id": gui, "token": session_token, "type": "mt_And"}
                jwt_req = session.post(
                    "https://api.mobilelegends.com/tools/deleteaccount/getToken",
                    json=jwt_payload,
                    headers={"Authorization": session_token},
                    timeout=15
                )
                jwt_data = jwt_req.json()
                
                if "jwt" not in jwt_data.get("data", {}):
                    return jsonify({"success": False, "status": "invalid", "message": "No JWT token"})
                
                jwt = jwt_data["data"]["jwt"]
                ban_info = get_ban_info(jwt)
                ban_status = ban_info.get("status", "No")
                
                try:
                    bind_check = session.post(
                        "https://api.mobilelegends.com/tools/deleteaccount/getCancelAccountInfo",
                        headers={"Authorization": f"Bearer {jwt}"},
                        json={},
                        timeout=15
                    )
                    bind_json = bind_check.json()
                    bindings_text = parse_binding(bind_json)
                except:
                    bindings_text = "Binding Error"
                
                try:
                    info_req = session.post(
                        "https://sg-api.mobilelegends.com/base/getBaseInfo",
                        headers={"Authorization": f"Bearer {jwt}"},
                        data={},
                        timeout=15
                    )
                    info_json = info_req.json().get("data") or {}
                except:
                    info_json = {}
                
                name = info_json.get("name", "Unknown")
                level = info_json.get("level", "N/A")
                acc_country = info_json.get("reg_country", "N/A")
                role_id = info_json.get("roleId", "N/A")
                zone_id = info_json.get("zoneId", "N/A")
                
                current_rank_level = info_json.get("rank_level", 0)
                highest_rank_level = info_json.get("history_rank_level", 0)
                
                current_rank = get_rank_name(current_rank_level)
                highest_rank = get_rank_name(highest_rank_level)
                
                create_date = "N/A"
                try:
                    create_date = get_creation_date(role_id, zone_id)
                except:
                    pass
                
                status = "banned" if "Yes" in ban_status else "valid"
                
                return jsonify({
                    "success": True,
                    "status": status,
                    "data": {
                        "email": email,
                        "password": password,
                        "name": name,
                        "level": level,
                        "role_id": role_id,
                        "zone_id": zone_id,
                        "current_rank": current_rank,
                        "highest_rank": highest_rank,
                        "bindings": bindings_text,
                        "region": acc_country,
                        "create_date": create_date,
                        "ban_status": ban_status
                    }
                })
            else:
                return jsonify({"success": False, "status": "invalid", "message": message})
                
        except requests.exceptions.Timeout:
            return jsonify({"success": False, "status": "error", "message": "Request timeout"})
        except Exception as e:
            return jsonify({"success": False, "status": "error", "message": str(e)})
            
    except Exception as e:
        return jsonify({"success": False, "status": "error", "message": str(e)})

# Handler untuk Vercel
app.debug = False

# ========== UNTUK LOCAL DEVELOPMENT ==========
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)