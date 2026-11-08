"""
sunwin.py — Đã gộp token trực tiếp (không cần token.txt)
=========================================================
- TOKEN_DATA hard-code trong file
- Nếu muốn đổi account: sửa dict TOKEN_DATA bên dưới
"""

import asyncio
import websockets
import json
import threading
import time
import sys
import io
import socket
import requests
import re
from datetime import datetime, timedelta
from flask import Blueprint, jsonify

# Fix UTF-8 console
if sys.platform == 'win32':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    except Exception:
        pass

CAU_LEN = 15


# ============================================================
# HELPERS — CHUẨN FORMAT 789
# ============================================================
def to_tx(ket_qua):
    if not ket_qua:
        return "?"
    k = str(ket_qua).strip().lower()
    if "tà" in k or "tai" in k:
        return "T"
    if "xỉ" in k or "xiu" in k or "bão" in k or "bao" in k:
        return "X"
    return "?"


def build_cau(history):
    seq = "".join(to_tx(e.get("ket_qua")) for e in (history or [])[:CAU_LEN])
    return seq[::-1]


def _st(v):
    return None if v is None else str(v)


def latest_payload(latest, cau):
    xuc = latest.get("xuc_xac") or []
    d1 = xuc[0] if len(xuc) > 0 else None
    d2 = xuc[1] if len(xuc) > 1 else None
    d3 = xuc[2] if len(xuc) > 2 else None
    dice = None if (d1 is None or d2 is None or d3 is None) else f"{d1}-{d2}-{d3}"
    return {
        "phien": latest.get("phien"),
        "dice1": _st(d1),
        "dice2": _st(d2),
        "dice3": _st(d3),
        "dice": dice,
        "tong": _st(latest.get("tong")),
        "ket_qua": latest.get("ket_qua"),
        "cau": cau,
        "last_update": latest.get("last_update"),
    }


def decorate_history(history, limit=None):
    target = (history or [])[:limit] if limit else (history or [])
    result = []
    for i, e in enumerate(target):
        window = "".join(to_tx(x.get("ket_qua")) for x in (history or [])[i:i + CAU_LEN])
        xuc = e.get("xuc_xac") or []
        d1 = xuc[0] if len(xuc) > 0 else None
        d2 = xuc[1] if len(xuc) > 1 else None
        d3 = xuc[2] if len(xuc) > 2 else None

        def st(v):
            return None if v is None else str(v)

        dice = None if (d1 is None or d2 is None or d3 is None) else f"{d1}-{d2}-{d3}"
        row = {
            "phien": e.get("phien"),
            "dice1": st(d1),
            "dice2": st(d2),
            "dice3": st(d3),
            "dice": dice,
            "tong": st(e.get("tong")),
            "ket_qua": e.get("ket_qua"),
            "cau": window[::-1],
        }
        if e.get("last_update") is not None:
            row["last_update"] = e.get("last_update")
        result.append(row)
    return result


# ============================================================
# TOKEN DATA — ĐÃ GỘP TỪ token.txt
# ============================================================
TOKEN_DATA = {
    "ipAddress": "1.55.124.245",
    "wsToken": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJhbW91bnQiOjAsInVzZXJuYW1lIjoiU0NfYXBpc3Vud2luMTIzIn0.hgrRbSV6vnBwJMg9ZFtbx3rRu9mX_hZMZ_m5gMNhkw0",
    "locale": "vi",
    "userId": "a28a0f06-e88f-44b7-a268-5f6dad949fbf",
    "username": "GM_quapotjz",
    "timestamp": 1780029354479,
    "refreshToken": "26b930ec6dc04d7db5c2b362a1baac87.7549ba6185d4467380ee447589380061",
}

# Signature + accessToken + password đăng nhập
WS_SIGNATURE = "05915B436159B8F4E4DFF537639BD014D54EBEFA18CF62A8EB205B4074010AD72AEA9A780D5A8A4E1BD59BBBAFE03902C594B5DA56FD60D099F1FDDCCD48385FCC2760B5B0B4B8E75D39B8E40DF8CB7C01EA58DBEDA32805927473AB71FA9B798B0C2EDC445C3E36E47EF0AAFAD45601D99AAD1EC642FD2B63573A0401D6EC69"
WS_ACCESS_TOKEN = "7e9a9ecbff1b4a6393b48346f6d8b709"
LOGIN_PASSWORD = "quapit"

# URL + Headers
WEBSOCKET_URL = f"wss://websocket.azhkthg1.net/websocket?token={TOKEN_DATA['wsToken']}"
TX_WS_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Origin": "https://play.sun.pw",
}

# Initial messages
TX_INITIAL_MESSAGES = [
    [
        1,
        "MiniGame",
        TOKEN_DATA['username'],
        LOGIN_PASSWORD,
        {
            "signature": WS_SIGNATURE,
            "expireIn": TOKEN_DATA['timestamp'],
            "wsToken": TOKEN_DATA['wsToken'],
            "accessToken": WS_ACCESS_TOKEN,
            "message": "Thành công",
            "refreshToken": TOKEN_DATA['refreshToken'],
            "info": TOKEN_DATA,
        }
    ],
    [6, "MiniGame", "taixiuPlugin", {"cmd": 1005}],
    [6, "MiniGame", "lobbyPlugin", {"cmd": 10001}],
]

TX_HEARTBEAT_MSG = [6, "MiniGame", "taixiuPlugin", {"cmd": 1005}]

print(f"[Sunwin] 👤 Account: {TOKEN_DATA['username']}")


# ============================================================
# SICBO
# ============================================================
SICBO_SOURCE_URL = "https://api.wsktnus8.net/v2/history/getLastResult"
SICBO_PARAMS = {
    "gameId": "ktrng_3979",
    "size": 1,
    "tableId": "39791215743193",
    "curPage": 1,
}
SICBO_POLL_INTERVAL = 5


# ============================================================
# BLUEPRINT
# ============================================================
bp = Blueprint('gamesunwin', __name__)

current_result = {
    "phien": None,
    "xuc_xac": [None, None, None],
    "tong": None,
    "ket_qua": "",
    "last_update": "",
}

current_session_id = None
_last_message_time = None
reconnect_delay = 2.5

TX_FILE = "sunwin-tx"
tx_history = []
_committed_tx = set()
_tx_lock = threading.Lock()

sicbo_result = {
    "phien": None,
    "xuc_xac": [None, None, None],
    "tong": None,
    "ket_qua": "",
    "last_update": "",
}
sicbo_history = []
MAX_HISTORY = 100
_last_joined_sid = None


def get_vietnam_time():
    utc7_time = datetime.utcnow() + timedelta(hours=7)
    return utc7_time.strftime("%d-%m-%Y %H:%M:%S") + " UTC+7"


def handle_error(context, error):
    print(f"[❌] Lỗi - {context}: {error}")


# ============================================================
# SICBO FETCH
# ============================================================
def fetch_sicbo():
    try:
        response = requests.get(SICBO_SOURCE_URL, params=SICBO_PARAMS, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        handle_error("Gọi API sicbo", e)
        return None


def transform_sicbo(raw_data):
    try:
        result_list = raw_data.get("data", {}).get("resultList", [])
        if not result_list:
            return None
        latest = result_list[0]
        faces = latest.get("facesList", [0, 0, 0])
        total = sum(faces)
        if len(faces) >= 3 and faces[0] == faces[1] == faces[2]:
            ket_qua = "Bão"
        else:
            ket_qua = "Tài" if total >= 11 else "Xỉu"
        return {
            "phien": latest.get("gameNum", ""),
            "xuc_xac": [faces[0] if len(faces) > 0 else None,
                        faces[1] if len(faces) > 1 else None,
                        faces[2] if len(faces) > 2 else None],
            "tong": total,
            "ket_qua": ket_qua,
            "last_update": get_vietnam_time(),
        }
    except Exception as e:
        handle_error("Transform sicbo", e)
        return None


def sicbo_poll_loop():
    global sicbo_result
    while True:
        raw_data = fetch_sicbo()
        if raw_data:
            transformed = transform_sicbo(raw_data)
            if transformed:
                sicbo_result = transformed
                if not sicbo_history or sicbo_history[0]["phien"] != transformed["phien"]:
                    sicbo_history.insert(0, transformed)
                    del sicbo_history[MAX_HISTORY:]
                print(f"[🎲] Sicbo phiên {transformed['phien']}: "
                      f"{'-'.join(str(x) for x in transformed['xuc_xac'])} "
                      f"= {transformed['tong']} ({transformed['ket_qua']}) | cau={build_cau(sicbo_history)}")
        time.sleep(SICBO_POLL_INTERVAL)


# ============================================================
# TX COMMIT
# ============================================================
def _commit_tx(sid, d1, d2, d3, source):
    global current_result
    if sid is None or sid in _committed_tx:
        return
    d1 = int(d1); d2 = int(d2); d3 = int(d3)
    total = d1 + d2 + d3
    result = "Tài" if total >= 11 else "Xỉu"

    _committed_tx.add(sid)

    now = get_vietnam_time()
    with _tx_lock:
        current_result = {
            "phien": str(sid),
            "xuc_xac": [d1, d2, d3],
            "tong": total,
            "ket_qua": result,
            "last_update": now,
        }
        entry = {
            "phien": str(sid),
            "xuc_xac": [d1, d2, d3],
            "tong": total,
            "ket_qua": result,
            "last_update": now,
        }
        tx_history.insert(0, entry)
        del tx_history[100:]

    print(f"[🎲 WIN] Phiên {sid} | {d1}-{d2}-{d3} = {total} ({result}) | Nguồn: {source} | cau={build_cau(tx_history)}")


def _extract_tx_from_payload(obj, source='auto-recovery'):
    if obj is None:
        return
    if isinstance(obj, dict):
        sid = obj.get('sid')
        if sid and obj.get('d1') is not None and obj.get('d2') is not None and obj.get('d3') is not None:
            _commit_tx(sid, obj['d1'], obj['d2'], obj['d3'], source)
        if sid and isinstance(obj.get('dices'), list) and len(obj['dices']) >= 3:
            if all(v is not None for v in obj['dices'][:3]):
                _commit_tx(sid, obj['dices'][0], obj['dices'][1], obj['dices'][2], source)
        for v in obj.values():
            if isinstance(v, (dict, list)):
                _extract_tx_from_payload(v, source)
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, (dict, list)):
                _extract_tx_from_payload(item, source)


# ============================================================
# WS CONNECT
# ============================================================
async def connect_websocket():
    global current_session_id, _last_joined_sid, _last_message_time

    async def _heartbeat(ws):
        try:
            while True:
                await asyncio.sleep(6)
                try:
                    if ws.state.name == 'OPEN':
                        await ws.send(json.dumps(TX_HEARTBEAT_MSG))
                except Exception:
                    pass
        except asyncio.CancelledError:
            pass

    async def _watchdog(ws):
        try:
            while True:
                await asyncio.sleep(5)
                if _last_message_time and (time.time() - _last_message_time > 25):
                    print("[🚨 WATCHDOG] 25s im lặng. Force reconnect!")
                    await ws.close()
                    return
        except asyncio.CancelledError:
            pass

    while True:
        try:
            print("[🔄] Đang kết nối WebSocket (tx)...")

            ws_connection = await websockets.connect(
                WEBSOCKET_URL,
                additional_headers=TX_WS_HEADERS,
                open_timeout=10,
                close_timeout=5,
                ping_interval=20,
                ping_timeout=10,
                max_size=2**20,
            )

            print("[✅] WebSocket (tx) connected to Sun.Win")

            _last_message_time = time.time()
            for msg in TX_INITIAL_MESSAGES:
                await ws_connection.send(json.dumps(msg))
                await asyncio.sleep(0.3)

            hb = asyncio.create_task(_heartbeat(ws_connection))
            wd = asyncio.create_task(_watchdog(ws_connection))

            try:
                async for message in ws_connection:
                    _last_message_time = time.time()
                    try:
                        if isinstance(message, bytes):
                            message = message.decode('utf-8', errors='ignore')
                        if not message:
                            continue
                        text = message if isinstance(message, str) else str(message)
                        if text and not text.startswith('[') and not text.startswith('{'):
                            m = re.search(r'[\[{]', text)
                            if m:
                                text = text[m.start():]
                            else:
                                continue
                        data = json.loads(text)

                        _extract_tx_from_payload(data)

                        if not isinstance(data, list) or len(data) < 2 or not isinstance(data[1], dict):
                            continue
                        payload = data[1]
                        sid = payload.get('sid')
                        if sid:
                            current_session_id = sid
                            if sid != _last_joined_sid:
                                join_msg = [6, "MiniGame", "taixiuPlugin", {"cmd": 1007, "sid": sid}]
                                await ws_connection.send(json.dumps(join_msg))
                                _last_joined_sid = sid
                    except json.JSONDecodeError:
                        continue
                    except Exception as e:
                        handle_error("Xử lý message", e)
            finally:
                hb.cancel()
                wd.cancel()

        except websockets.exceptions.ConnectionClosed as e:
            handle_error("WebSocket đóng", e)
            await asyncio.sleep(reconnect_delay)
        except Exception as e:
            handle_error("Kết nối WebSocket", e)
            await asyncio.sleep(reconnect_delay)


# ============================================================
# ROUTES
# ============================================================
@bp.route('/sunwin/api/tx', methods=['GET'])
def get_tx_result():
    return jsonify(latest_payload(current_result, build_cau(tx_history)))


@bp.route('/sunwin/api/tx/history', methods=['GET'])
def get_tx_history():
    return jsonify({"history": decorate_history(tx_history), "total": len(tx_history)})


@bp.route('/sunwin/api/tx/history/<int:n>', methods=['GET'])
def get_tx_history_n(n):
    if n <= 0:
        n = 1
    return jsonify({"history": decorate_history(tx_history, n), "total": len(tx_history)})


@bp.route('/sunwin/api/sicbo', methods=['GET'])
def get_sicbo_result():
    return jsonify(latest_payload(sicbo_result, build_cau(sicbo_history)))


@bp.route('/sunwin/api/sicbo/history', methods=['GET'])
def get_sicbo_history():
    return jsonify({"history": decorate_history(sicbo_history), "total": len(sicbo_history)})


@bp.route('/sunwin/api/sicbo/history/<int:n>', methods=['GET'])
def get_sicbo_history_n(n):
    if n <= 0:
        n = 1
    return jsonify({"history": decorate_history(sicbo_history, n), "total": len(sicbo_history)})


@bp.route('/sunwin/', methods=['GET'])
def index():
    return jsonify({
        "name": "Sun.Win Tài Xỉu Data Stream",
        "version": "1.0",
        "endpoints": {
            "/sunwin/api/tx": "Lấy kết quả tài xỉu mới nhất",
            "/sunwin/api/sicbo": "Lấy kết quả sicbo mới nhất",
            "/sunwin/api/sicbo/history[/n]": "Lấy lịch sử sicbo",
        },
        "thoi_gian": get_vietnam_time(),
        "current_user": TOKEN_DATA.get('username', 'Unknown'),
    })


def start_background():
    global tx_history, sicbo_history
    tx_history = []
    sicbo_history = []
    threading.Thread(target=sicbo_poll_loop, daemon=True).start()
    threading.Thread(target=lambda: asyncio.run(connect_websocket()), daemon=True).start()