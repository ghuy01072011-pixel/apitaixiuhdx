# xdlc.py — JSON unified, không dice
import time
import threading
import requests
from datetime import datetime
from flask import Blueprint, jsonify

bp = Blueprint("xdlc", __name__, url_prefix="/xdlc/api")

API_URL = "https://wcl.tele68.com/v1/chanlefull/lite-sessions"
API_PARAMS = {
    "cp": "R", "cl": "R", "pf": "web",
    "at": "bc1qgk07vhn53ws7khy3840gjjvlw7qgzftfjgweq2",
}

MAX_HISTORY = 10

_state = {
    "cau": "", "dice": "", "dice1": "", "dice2": "", "dice3": "",
    "ket_qua": "Chưa có", "last_update": "", "phien": 0, "tong": "",
}

_history = []   # list[str] 'C'/'L' mới nhất ở index 0
_last_id = None


def _now():
    return datetime.now().isoformat()


def _commit(session_id, result_raw):
    if result_raw == 'chan':
        kq_short, kq_full = 'C', 'CHẴN'
    elif result_raw == 'le':
        kq_short, kq_full = 'L', 'LẺ'
    else:
        return
    _history.insert(0, kq_short)
    if len(_history) > MAX_HISTORY:
        del _history[MAX_HISTORY:]
    _state["cau"] = "".join(_history)
    _state["ket_qua"] = kq_full
    _state["last_update"] = _now()
    _state["phien"] = session_id


def _fetch():
    global _last_id
    try:
        r = requests.get(API_URL, params=API_PARAMS, timeout=5)
        data = r.json().get("list") or []
        if not data:
            return
        newest = data[0]
        new_id = newest.get("id")
        if new_id is None or new_id == _last_id:
            return
        _last_id = new_id
        _commit(new_id, newest.get("resultTruyenThong"))
        print(f"[XDLC] Phien {new_id} → {_state['ket_qua']}")
    except Exception as e:
        print(f"[XDLC] Loi: {e}")


def _loop():
    while True:
        _fetch()
        time.sleep(2)


@bp.route("/xdlc")
def api_xdlc():
    return jsonify(_state)


def start_background():
    threading.Thread(target=_loop, daemon=True).start()