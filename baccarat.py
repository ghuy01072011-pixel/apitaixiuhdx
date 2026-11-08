# baccarat.py — Port từ Node.js sang Python/Flask
import re
import time
import threading
import urllib3
import requests
from flask import Blueprint, jsonify

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ======================
# CẤU HÌNH TÀI KHOẢN
# ======================
USERNAME = "6tyghujkm"
PASSWORD = "6tyghujkm"
BASE = "https://aibcr.me"
LOGIN_URL = f"{BASE}/login"
LOBBY_URL = f"{BASE}/ae/lobby"
GET_RESULT_URL = f"{BASE}/baccarat/getnewresult"

bp = Blueprint("baccarat", __name__, url_prefix="/baccarat/api")

baccarat_data = []
last_update = None

_session = requests.Session()
_session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
})
_session.verify = False


def _get_csrf_token(html: str):
    m = re.search(r'<input[^>]*name="_token"[^>]*value="([^"]+)"', html)
    if m:
        return m.group(1)
    m = re.search(r'<meta\s+name="csrf-token"\s+content="([^"]+)"', html)
    return m.group(1) if m else None


def _login() -> bool:
    try:
        r = _session.get(LOGIN_URL, timeout=30)
        token = _get_csrf_token(r.text)
        if not token:
            print("[Baccarat] Không tìm thấy CSRF token")
            return False
        data = {
            "username": USERNAME,
            "password": PASSWORD,
            "_token": token,
            "action": "Login",
        }
        headers = {"Referer": LOGIN_URL, "Origin": BASE}
        r = _session.post(LOGIN_URL, data=data, headers=headers,
                          timeout=30, allow_redirects=True)
        if r.status_code in (200, 302):
            print("[Baccarat] ✅ Login OK")
            return True
        print(f"[Baccarat] ❌ Login fail: {r.status_code}")
        return False
    except Exception as e:
        print(f"[Baccarat] Login error: {e}")
        return False


def _go_lobby() -> bool:
    try:
        _session.get(LOBBY_URL, timeout=30)
        return True
    except Exception as e:
        print(f"[Baccarat] Lobby error: {e}")
        return False


def _fetch_data():
    global baccarat_data, last_update
    try:
        xsrf = ""
        for c in _session.cookies:
            if c.name == "XSRF-TOKEN":
                xsrf = c.value
                break
        headers = {
            "Referer": LOBBY_URL,
            "Origin": BASE,
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }
        if xsrf:
            headers["X-XSRF-TOKEN"] = xsrf
        r = _session.post(GET_RESULT_URL, data={"gameCode": "ae"},
                          headers=headers, timeout=30)
        j = r.json()
        if j.get("code") == 200 and isinstance(j.get("data"), list):
            baccarat_data = [{
                "table": it.get("table_name"),
                "table_id": it.get("table_id"),
                "result": it.get("result"),
                "goodRoad": it.get("goodRoad", ""),
                "cards": it.get("cards", ""),
                "game_code": it.get("game_code"),
            } for it in j["data"]]
            last_update = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    except Exception as e:
        print(f"[Baccarat] Fetch error: {e}")


# ======================
# ROUTES
# ======================
@bp.route("/baccarat")
def all_tables():
    return jsonify({
        "success": True,
        "data": baccarat_data,
        "lastUpdate": last_update,
        "total": len(baccarat_data),
    })


@bp.route("/baccarat/<table>")
def one_table(table):
    for it in baccarat_data:
        if str(it.get("table")) == table:
            return jsonify({"success": True, "data": it})
    return jsonify({"success": False, "message": f"Không tìm thấy bàn {table}"})


@bp.route("/latest")
def latest():
    def num(x):
        try:
            return int(x["table"])
        except (TypeError, ValueError):
            return 0
    sorted_data = sorted(baccarat_data, key=num, reverse=True)
    return jsonify({
        "success": True,
        "data": sorted_data[:10],
        "lastUpdate": last_update,
    })


# ======================
# WORKER
# ======================
def _worker():
    if not _login():
        print("[Baccarat] Không đăng nhập được, worker dừng")
        return
    _go_lobby()
    _fetch_data()
    print(f"[Baccarat] Bắt đầu loop — {len(baccarat_data)} bàn")
    while True:
        try:
            _fetch_data()
        except Exception as e:
            print(f"[Baccarat] Loop error: {e}")
        time.sleep(2)


def start_background():
    threading.Thread(target=_worker, daemon=True).start()