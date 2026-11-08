# haywin.py — Trả JSON unified format (giống 789/b52)
import time
import threading
import requests
from datetime import datetime
from flask import Blueprint, jsonify

bp = Blueprint("haywin", __name__, url_prefix="/haywin/api")

POLL_INTERVAL = 5
RETRY_DELAY = 5
MAX_HISTORY = 10          # main.py sẽ override

URL_100 = ("https://jakpotgwab.geightdors.net/glms/v1/notify/taixiu"
           "?platform_id=rik&gid=vgmn_100")
URL_101 = ("https://jakpotgwab.geightdors.net/glms/v1/notify/taixiu"
           "?platform_id=rik&gid=vgmn_101")

_state_100 = {
    "cau": "", "dice": "", "dice1": "", "dice2": "", "dice3": "",
    "ket_qua": "Chưa có", "last_update": "", "phien": 0, "tong": "",
}
_state_101 = dict(_state_100)

_hist_100 = []   # list[str] 'T'/'X' mới nhất ở index 0
_hist_101 = []

_last_sid_100 = None
_last_sid_101 = None
_sid_for_tx = None


def _now():
    return datetime.now().isoformat()


def _commit_tx(store, history, sid, d1, d2, d3):
    tong = d1 + d2 + d3
    kq_short = 'T' if tong > 10 else 'X'
    kq_full = 'Tài' if tong > 10 else 'Xỉu'
    history.insert(0, kq_short)
    if len(history) > MAX_HISTORY:
        del history[MAX_HISTORY:]
    store["cau"] = "".join(history)
    store["dice"] = f"{d1}-{d2}-{d3}"
    store["dice1"] = str(d1)
    store["dice2"] = str(d2)
    store["dice3"] = str(d3)
    store["ket_qua"] = kq_full
    store["last_update"] = _now()
    store["phien"] = sid
    store["tong"] = str(tong)


def _poll_taixiu():
    global _last_sid_100, _sid_for_tx
    while True:
        try:
            r = requests.get(URL_100, headers={"User-Agent": "Py/1.0"}, timeout=10)
            data = r.json()
            if data.get("status") == "OK" and isinstance(data.get("data"), list):
                for g in data["data"]:
                    if g.get("cmd") == 1008:
                        _sid_for_tx = g.get("sid")
                for g in data["data"]:
                    if g.get("cmd") == 1003:
                        sid = _sid_for_tx
                        d1, d2, d3 = g.get("d1"), g.get("d2"), g.get("d3")
                        if sid and sid != _last_sid_100 and all(v is not None for v in (d1, d2, d3)):
                            _last_sid_100 = sid
                            _commit_tx(_state_100, _hist_100, sid, d1, d2, d3)
                            print(f"[Haywin-TX] Phien {sid} → {d1}-{d2}-{d3} = {d1+d2+d3}")
                            _sid_for_tx = None
        except Exception as e:
            print(f"[Haywin-TX] Loi: {e}")
            time.sleep(RETRY_DELAY)
        time.sleep(POLL_INTERVAL)


def _poll_md5():
    global _last_sid_101
    while True:
        try:
            r = requests.get(URL_101, headers={"User-Agent": "Py/1.0"}, timeout=10)
            data = r.json()
            if data.get("status") == "OK" and isinstance(data.get("data"), list):
                for g in data["data"]:
                    if g.get("cmd") == 7006 and g.get("d1") and g.get("d2") and g.get("d3"):
                        sid = g.get("sid")
                        if sid and sid != _last_sid_101:
                            _last_sid_101 = sid
                            _commit_tx(_state_101, _hist_101, sid,
                                       g["d1"], g["d2"], g["d3"])
                            print(f"[Haywin-MD5] Phien {sid}")
        except Exception as e:
            print(f"[Haywin-MD5] Loi: {e}")
            time.sleep(RETRY_DELAY)
        time.sleep(POLL_INTERVAL)


@bp.route("/taixiu")
def api_taixiu():
    return jsonify(_state_100)


@bp.route("/md5")
def api_md5():
    return jsonify(_state_101)


def start_background():
    threading.Thread(target=_poll_taixiu, daemon=True).start()
    threading.Thread(target=_poll_md5, daemon=True).start()