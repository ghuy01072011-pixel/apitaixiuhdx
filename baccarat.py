# baccarat.py — Trả dict {tên_bàn: unified_json} cho tất cả bàn
import re
import time
import threading
import urllib3
import requests
from datetime import datetime
from flask import Blueprint, jsonify

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

USERNAME = "huydaixubcr"
PASSWORD = "huydaixubcr"
BASE = "https://aibcr.me"
LOGIN_URL = f"{BASE}/login"
LOBBY_URL = f"{BASE}/ae/lobby"
GET_RESULT_URL = f"{BASE}/baccarat/getnewresult"

MAX_HISTORY = 10

bp = Blueprint("baccarat", __name__, url_prefix="/baccarat/api")

tables = {}          # { "C1": unified_obj, "C2": unified_obj, ... }
last_update_global = ""

_session = requests.Session()
_session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
})
_session.verify = False

_KQ_MAP = {'P': 'Player', 'B': 'Banker', 'T': 'Tie'}


def _now():
    return datetime.now().isoformat()


def _get_csrf_token(html):
    m = re.search(r'<input[^>]*name="_token"[^>]*value="([^"]+)"', html)
    if m:
        return m.group(1)
    m = re.search(r'<meta\s+name="csrf-token"\s+content="([^"]+)"', html)
    return m.group(1) if m else None


def _login():
    try:
        r = _session.get(LOGIN_URL, timeout=30)
        token = _get_csrf_token(r.text)
        if not token:
            print("[Baccarat] Khong co CSRF token")
            return False
        data = {"username": USERNAME, "password": PASSWORD,
                "_token": token, "action": "Login"}
        r = _session.post(LOGIN_URL, data=data,
                          headers={"Referer": LOGIN_URL, "Origin": BASE},
                          timeout=30, allow_redirects=True)
        if r.status_code in (200, 302):
            print("[Baccarat] Login OK")
            return True
        print(f"[Baccarat] Login fail: {r.status_code}")
        return False
    except Exception as e:
        print(f"[Baccarat] Login error: {e}")
        return False


def _go_lobby():
    try:
        _session.get(LOBBY_URL, timeout=30)
    except Exception as e:
        print(f"[Baccarat] Lobby error: {e}")


def _build_unified(table_name, result_str):
    """result_str = 'PBPBPB...' → unified object."""
    if not result_str:
        return None
    latest = result_str[-1]
    cau = result_str[-MAX_HISTORY:] if len(result_str) > MAX_HISTORY else result_str
    return {
        "cau": cau,
        "dice": "",
        "dice1": "",
        "dice2": "",
        "dice3": "",
        "ket_qua": _KQ_MAP.get(latest, latest),
        "last_update": _now(),
        "phien": len(result_str),
        "tong": "",
    }


def _fetch():
    global last_update_global
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
            new_tables = {}
            for it in j["data"]:
                name = it.get("table_name")
                res = it.get("result")
                if not name or not res:
                    continue
                entry = _build_unified(name, res)
                if entry:
                    new_tables[name] = entry
            tables.clear()
            tables.update(new_tables)
            last_update_global = _now()
    except Exception as e:
        print(f"[Baccarat] Fetch error: {e}")


def _sort_key(name):
    num = "".join(c for c in name if c.isdigit())
    try:
        return (0, int(num), name)
    except ValueError:
        return (1, 0, name)


@bp.route("/baccarat")
def api_all_tables():
    ordered = {k: tables[k] for k in sorted(tables.keys(), key=_sort_key)}
    return jsonify(ordered)


@bp.route("/baccarat/<table>")
def api_one_table(table):
    if table in tables:
        return jsonify(tables[table])
    return jsonify({"error": f"Không tìm thấy bàn {table}"}), 404


def _worker():
    if not _login():
        print("[Baccarat] Không đăng nhập được, worker dừng")
        return
    _go_lobby()
    _fetch()
    print(f"[Baccarat] Bắt đầu loop — {len(tables)} bàn")
    while True:
        try:
            _fetch()
        except Exception as e:
            print(f"[Baccarat] Loop error: {e}")
        time.sleep(2)


def start_background():
    threading.Thread(target=_worker, daemon=True).start()