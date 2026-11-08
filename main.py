"""
main.py — GameAPI Hub
=========================
Chạy: python main.py
Mở:  http://localhost:5000

- Không cần file index.html riêng (HTML nhúng sẵn)
- Không lưu JSON history (chỉ giữ RAM)
- Mỗi game chỉ giữ 10 phiên gần nhất
- Đã BỎ SumClub
- Sunwin: chỉ giữ sicbo (đã bỏ tx)
- Đã thêm: Baccarat (đa bàn C1..C21), Haywin, XDLC — JSON unified
"""

import os
import sys
import io
import builtins
import importlib

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ============================================================
# 1) KHÔNG LƯU FILE — CHỈ GIỮ TRONG RAM
# ============================================================
builtins.load   = lambda name: []
builtins.save   = lambda name, data: None
builtins._sload = lambda name: []
builtins._ssave = lambda name, data: None

# ============================================================
# 2) IMPORT CÁC MODULE GAME — thiếu file nào skip file đó
# ============================================================
MODULE_NAMES = [
    '789', 'b52', 'baccarat', 'betvip', 'haywin', 'hitclub',
    'lc79', 'luck8', 'max789', 'rikvip', 'sao789', 'son789',
    'sunwin', 'xdlc', 'xocdia88',
]

MODULES = []
MISSING = []

for name in MODULE_NAMES:
    try:
        m = importlib.import_module(name)
        if not hasattr(m, 'bp'):
            print(f"  ⚠️  {name}.py thiếu biến 'bp' — bỏ qua")
            MISSING.append(name)
            continue
        if not hasattr(m, 'start_background'):
            print(f"  ⚠️  {name}.py thiếu 'start_background()' — bỏ qua")
            MISSING.append(name)
            continue
        MODULES.append(m)
    except ModuleNotFoundError:
        print(f"  ❌ Thiếu file: {name}.py")
        MISSING.append(name)
    except Exception as e:
        print(f"  ❌ Lỗi import {name}.py: {e}")
        MISSING.append(name)

if MISSING:
    print(f"\n⚠️  Có {len(MISSING)} module thiếu/lỗi: {', '.join(MISSING)}")
    print("   Server vẫn chạy với các module còn lại.\n")
else:
    print(f"✅ Import OK: {len(MODULES)} module\n")

# ============================================================
# 3) CHỈ GIỮ 10 PHIÊN GẦN NHẤT
# ============================================================
MAX_MEMORY = 10

for m in MODULES:
    if hasattr(m, 'MAX_HISTORY'):
        m.MAX_HISTORY = MAX_MEMORY

# Patch sunwin (dùng slice cứng)
try:
    if 'sunwin' in [m.__name__ for m in MODULES]:
        _sw = importlib.import_module('sunwin')
        _orig_commit = _sw._commit_tx
        def _patched_commit(sid, d1, d2, d3, source):
            _orig_commit(sid, d1, d2, d3, source)
            if len(_sw.tx_history) > MAX_MEMORY:
                del _sw.tx_history[MAX_MEMORY:]
        _sw._commit_tx = _patched_commit
        print("[Patch] sunwin._commit_tx -> 10 phiên")
except Exception as e:
    print(f"[Patch] sunwin: {e}")

# Patch 789 (dùng slice cứng)
try:
    if '789' in [m.__name__ for m in MODULES]:
        _g789 = importlib.import_module('789')
        _orig_parse = _g789.parse_tx_data
        def _patched_parse(msg):
            _orig_parse(msg)
            if len(_g789.tx_data["lich_su_cuoc"]) > MAX_MEMORY:
                _g789.tx_data["lich_su_cuoc"] = _g789.tx_data["lich_su_cuoc"][:MAX_MEMORY]
        _g789.parse_tx_data = _patched_parse
        print("[Patch] 789.parse_tx_data -> 10 phiên")
except Exception as e:
    print(f"[Patch] 789: {e}")

# ============================================================
# 4) FLASK APP
# ============================================================
from flask import Flask, Response, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

for m in MODULES:
    app.register_blueprint(m.bp)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ============================================================
# 5) HTML NHÚNG SẴN
# ============================================================
HTML = r"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, minimum-scale=1.0, user-scalable=no, viewport-fit=cover">
<meta name="theme-color" content="#0a0b10">
<title>GameAPI Hub — Kho API Game Đổi Thưởng</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#0a0b10;--surface:#12141c;--surface-2:#171a24;--line:rgba(255,255,255,.075);--line-hi:rgba(255,255,255,.14);--txt:#f1f3f9;--muted:#8a91a8;--accent:#6366f1;--accent-2:#22d3ee;--green:#34d399;--red:#f87171;--r:16px;--header-h:64px}
html{-webkit-text-size-adjust:100%;text-size-adjust:100%;scroll-behavior:smooth;touch-action:pan-y}
body{font-family:'Inter',system-ui,-apple-system,'Segoe UI',sans-serif;background:var(--bg);color:var(--txt);min-height:100vh;overflow-x:hidden;overscroll-behavior-y:none;-webkit-font-smoothing:antialiased;-webkit-tap-highlight-color:transparent;line-height:1.5}
img,svg{display:block;max-width:100%}
button,input{font-family:inherit;font-size:inherit;color:inherit}
button{background:none;border:none;cursor:pointer}
a{text-decoration:none;color:inherit}
.bg{position:fixed;inset:0;z-index:-1;pointer-events:none;overflow:hidden}
.bg::before{content:"";position:absolute;top:-30%;left:50%;transform:translateX(-50%);width:min(900px,120vw);height:min(900px,120vw);border-radius:50%;background:radial-gradient(circle,rgba(99,102,241,.18),transparent 65%);filter:blur(40px)}
.bg::after{content:"";position:absolute;bottom:-40%;right:-20%;width:min(700px,110vw);height:min(700px,110vw);border-radius:50%;background:radial-gradient(circle,rgba(34,211,238,.10),transparent 65%);filter:blur(50px)}
.wrap{width:100%;max-width:1200px;margin:0 auto;padding-left:clamp(16px,4vw,28px);padding-right:clamp(16px,4vw,28px)}
header{position:sticky;top:0;z-index:100;height:var(--header-h);background:rgba(10,11,16,.75);backdrop-filter:blur(18px) saturate(180%);-webkit-backdrop-filter:blur(18px) saturate(180%);border-bottom:1px solid var(--line);transition:background .25s,border-color .25s}
header.scrolled{background:rgba(10,11,16,.92);border-bottom-color:var(--line-hi)}
.nav{height:100%;display:flex;align-items:center;gap:12px}
.logo{display:flex;align-items:center;gap:10px;flex-shrink:0;min-width:0}
.logo-mark{width:36px;height:36px;flex-shrink:0;border-radius:11px;background:linear-gradient(135deg,var(--accent),var(--accent-2));display:grid;place-items:center;box-shadow:0 6px 18px -6px rgba(99,102,241,.8)}
.logo-mark svg{width:18px;height:18px;stroke:#fff;fill:none;stroke-width:2.4;stroke-linecap:round;stroke-linejoin:round}
.logo-txt{font-weight:700;font-size:16px;letter-spacing:-.3px;white-space:nowrap}
.logo-txt span{background:linear-gradient(90deg,#a5b4fc,#22d3ee);-webkit-background-clip:text;background-clip:text;color:transparent}
.nav-links{display:flex;align-items:center;gap:2px;margin-left:auto}
.nav-links a{padding:8px 14px;border-radius:9px;font-size:14px;font-weight:500;color:var(--muted);transition:color .2s,background .2s;white-space:nowrap}
.nav-links a:hover{color:var(--txt);background:rgba(255,255,255,.05)}
.nav-links a.on{color:var(--txt);background:rgba(99,102,241,.16)}
.btn-key{margin-left:8px;display:inline-flex;align-items:center;gap:7px;padding:9px 16px;border-radius:10px;font-size:13.5px;font-weight:600;color:#fff;background:linear-gradient(135deg,var(--accent),#4f46e5);box-shadow:0 6px 18px -8px rgba(99,102,241,.9);transition:transform .2s,box-shadow .2s;white-space:nowrap}
.btn-key:hover{transform:translateY(-1px);box-shadow:0 10px 24px -8px rgba(99,102,241,1)}
.btn-key svg{width:14px;height:14px;stroke:currentColor;fill:none;stroke-width:2.2;stroke-linecap:round;stroke-linejoin:round}
.burger{display:none;width:38px;height:38px;border-radius:10px;margin-left:auto;place-items:center;border:1px solid var(--line);transition:background .2s}
.burger:hover{background:rgba(255,255,255,.05)}
.burger svg{width:18px;height:18px;stroke:var(--txt);fill:none;stroke-width:2.2;stroke-linecap:round}
.mobile-menu{position:fixed;top:var(--header-h);left:0;right:0;z-index:99;padding:12px clamp(16px,4vw,28px) 20px;background:rgba(10,11,16,.97);backdrop-filter:blur(18px);-webkit-backdrop-filter:blur(18px);border-bottom:1px solid var(--line-hi);display:flex;flex-direction:column;gap:4px;transform:translateY(-12px);opacity:0;visibility:hidden;transition:transform .25s,opacity .25s,visibility .25s}
.mobile-menu.open{transform:none;opacity:1;visibility:visible}
.mobile-menu a{padding:12px 14px;border-radius:10px;font-size:15px;font-weight:500;color:var(--muted);transition:background .2s,color .2s}
.mobile-menu a:hover,.mobile-menu a.on{background:rgba(255,255,255,.06);color:var(--txt)}
.mobile-menu .btn-key{margin:8px 0 0;justify-content:center;padding:13px}
.hero{padding:clamp(44px,7vw,76px) 0 clamp(28px,4vw,40px);text-align:center}
.pill{display:inline-flex;align-items:center;gap:8px;padding:6px 14px 6px 10px;border-radius:999px;background:rgba(255,255,255,.04);border:1px solid var(--line-hi);font-size:12.5px;color:var(--muted);margin-bottom:22px}
.pill i{width:7px;height:7px;border-radius:50%;background:var(--green);box-shadow:0 0 0 3px rgba(52,211,153,.16);animation:blink 2s ease-in-out infinite}
@keyframes blink{50%{opacity:.35}}
.hero h1{font-size:clamp(30px,6vw,54px);font-weight:800;line-height:1.12;letter-spacing:-1.6px;margin-bottom:16px}
.hero h1 em{font-style:normal;background:linear-gradient(100deg,#a5b4fc,#22d3ee);-webkit-background-clip:text;background-clip:text;color:transparent}
.hero p{max-width:540px;margin:0 auto 30px;font-size:clamp(14.5px,2vw,16px);line-height:1.7;color:var(--muted);font-weight:400}
.search{position:relative;max-width:480px;margin:0 auto}
.search svg{position:absolute;left:16px;top:50%;transform:translateY(-50%);width:18px;height:18px;stroke:var(--muted);fill:none;stroke-width:2;pointer-events:none;transition:stroke .2s}
.search input{width:100%;padding:14px 16px 14px 46px;border-radius:14px;font-size:16px;color:var(--txt);background:var(--surface);border:1px solid var(--line-hi);outline:none;transition:border-color .2s,box-shadow .2s,background .2s}
.search input::placeholder{color:#5c6382}
.search input:focus{border-color:rgba(99,102,241,.65);background:var(--surface-2);box-shadow:0 0 0 4px rgba(99,102,241,.12)}
.search:focus-within svg{stroke:#a5b4fc}
.stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;max-width:660px;margin:36px auto 0}
.stat{padding:14px 8px;border-radius:14px;text-align:center;background:var(--surface);border:1px solid var(--line);transition:border-color .2s,transform .2s}
.stat:hover{border-color:rgba(99,102,241,.4);transform:translateY(-2px)}
.stat b{display:block;font-size:clamp(17px,2.6vw,21px);font-weight:700;letter-spacing:-.5px;color:#fff;margin-bottom:2px}
.stat span{font-size:11px;color:var(--muted);letter-spacing:.4px;font-weight:500}
.section{padding:8px 0 64px}
.sec-head{display:flex;align-items:flex-end;justify-content:space-between;gap:16px;flex-wrap:wrap;margin-bottom:22px}
.sec-head h2{font-size:clamp(19px,3vw,24px);font-weight:700;letter-spacing:-.6px}
.sec-head p{font-size:13px;color:var(--muted);margin-top:4px}
.filters{display:flex;gap:7px;flex-wrap:wrap}
.chip{padding:7px 14px;border-radius:9px;font-size:12.5px;font-weight:600;color:var(--muted);background:var(--surface);border:1px solid var(--line);transition:color .2s,border-color .2s,background .2s;white-space:nowrap}
.chip:hover{color:var(--txt);border-color:var(--line-hi)}
.chip.on{color:#fff;background:linear-gradient(135deg,var(--accent),#4f46e5);border-color:transparent;box-shadow:0 6px 16px -8px rgba(99,102,241,1)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(300px,100%),1fr));gap:16px;align-items:stretch}
.card{display:flex;flex-direction:column;padding:18px;border-radius:var(--r);background:var(--surface);border:1px solid var(--line);min-width:0;transition:border-color .25s,transform .25s,box-shadow .25s,background .25s}
.card:hover{border-color:var(--line-hi);background:var(--surface-2);transform:translateY(-4px);box-shadow:0 18px 40px -22px rgba(0,0,0,.9)}
.c-head{display:flex;align-items:center;gap:12px;margin-bottom:14px;min-width:0}
.c-logo{position:relative;width:52px;height:52px;flex-shrink:0;border-radius:14px;overflow:hidden;background:var(--g);box-shadow:0 8px 20px -10px var(--glow)}
.c-logo .fb{position:absolute;inset:0;display:grid;place-items:center;font-size:13px;font-weight:800;color:#fff;letter-spacing:-.5px;text-shadow:0 1px 3px rgba(0,0,0,.35);z-index:0}
.c-logo img{position:relative;z-index:1;width:100%;height:100%;object-fit:cover;display:block}
.c-logo::after{content:"";position:absolute;inset:0;z-index:2;background:linear-gradient(160deg,rgba(255,255,255,.22),transparent 55%);pointer-events:none}
.c-info{flex:1;min-width:0}
.c-info h3{font-size:15.5px;font-weight:700;letter-spacing:-.3px;display:flex;align-items:center;gap:6px;margin-bottom:2px}
.c-info h3 .verif{width:14px;height:14px;flex-shrink:0;border-radius:50%;background:linear-gradient(135deg,#22d3ee,#3b82f6);display:grid;place-items:center}
.c-info h3 .verif svg{width:8px;height:8px;stroke:#fff;fill:none;stroke-width:3.5;stroke-linecap:round;stroke-linejoin:round}
.c-info .sub{font-size:12px;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tags{display:flex;gap:5px;flex-wrap:wrap;margin-bottom:12px}
.tag{font-size:10.5px;font-weight:600;letter-spacing:.3px;padding:3px 8px;border-radius:6px;background:rgba(255,255,255,.05);border:1px solid var(--line);color:#9aa1bb;white-space:nowrap}
.tag.hot{background:rgba(244,114,182,.13);border-color:rgba(244,114,182,.28);color:#f9a8d4}
.tag.new{background:rgba(52,211,153,.12);border-color:rgba(52,211,153,.26);color:#6ee7b7}
.tag.vip{background:rgba(251,191,36,.12);border-color:rgba(251,191,36,.28);color:#fcd34d}
.endpoints{border-radius:11px;background:rgba(0,0,0,.4);border:1px solid var(--line);overflow:hidden;margin-bottom:14px}
.ep-row{display:flex;align-items:center;gap:8px;padding:9px 11px;min-width:0;border-bottom:1px solid var(--line);cursor:pointer;transition:background .2s}
.ep-row:last-child{border-bottom:none}
.ep-row:hover{background:rgba(99,102,241,.08)}
.ep-mode{flex-shrink:0;font-size:10px;font-weight:800;letter-spacing:.3px;padding:4px 8px;border-radius:6px;white-space:nowrap;text-transform:uppercase;min-width:86px;text-align:center}
.ep-mode.tx{background:rgba(244,114,182,.16);color:#fbcfe8;border:1px solid rgba(244,114,182,.42)}
.ep-mode.txmd5{background:rgba(34,211,238,.15);color:#a5f3fc;border:1px solid rgba(34,211,238,.42)}
.ep-mode.txhu{background:rgba(244,114,182,.16);color:#fbcfe8;border:1px solid rgba(244,114,182,.42)}
.ep-mode.sicbo{background:rgba(99,102,241,.18);color:#c7d2fe;border:1px solid rgba(99,102,241,.42)}
.ep-mode.hu{background:rgba(251,191,36,.15);color:#fde68a;border:1px solid rgba(251,191,36,.42)}
.ep-mode.bac{background:rgba(20,184,166,.16);color:#99f6e4;border:1px solid rgba(20,184,166,.42)}
.ep-mode.xdlc{background:rgba(236,72,153,.16);color:#fbcfe8;border:1px solid rgba(236,72,153,.42)}
.ep-url{flex:1;min-width:0;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:10.5px;color:#a4acd0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;direction:rtl;text-align:left}
.ep-go{flex-shrink:0;width:24px;height:24px;display:grid;place-items:center;color:#6c7499;transition:color .2s,transform .15s}
.ep-row:hover .ep-go{color:#a5b4fc;transform:translateX(2px)}
.ep-go svg{width:12px;height:12px;stroke:currentColor;fill:none;stroke-width:2.4;stroke-linecap:round;stroke-linejoin:round}
.ep-copy{flex-shrink:0;width:26px;height:26px;border-radius:7px;display:grid;place-items:center;background:rgba(255,255,255,.05);color:var(--muted);transition:background .2s,color .2s,transform .15s}
.ep-copy:hover{background:rgba(255,255,255,.12);color:var(--txt)}
.ep-copy:active{transform:scale(.9)}
.ep-copy svg{width:12px;height:12px;stroke:currentColor;fill:none;stroke-width:2.2;stroke-linecap:round;stroke-linejoin:round}
.ep-copy.done{background:rgba(52,211,153,.2);color:#6ee7b7}
.c-actions{display:flex;gap:8px;margin-top:auto}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:6px;padding:11px 14px;border-radius:11px;font-size:13px;font-weight:600;transition:transform .2s,box-shadow .2s,background .2s,border-color .2s;white-space:nowrap;overflow:hidden}
.btn svg{width:14px;height:14px;flex-shrink:0;stroke:currentColor;fill:none;stroke-width:2.1;stroke-linecap:round;stroke-linejoin:round}
.btn-go{flex:1;min-width:0;color:#fff;background:var(--g);box-shadow:0 8px 20px -12px var(--glow)}
.btn-go:hover{transform:translateY(-2px);box-shadow:0 12px 26px -12px var(--glow)}
.btn-doc{flex-shrink:0;width:42px;background:rgba(255,255,255,.05);border:1px solid var(--line);color:var(--muted)}
.btn-doc:hover{background:rgba(255,255,255,.1);color:var(--txt);border-color:var(--line-hi)}
.empty{grid-column:1/-1;text-align:center;padding:56px 20px;border-radius:var(--r);border:1px dashed var(--line-hi);color:var(--muted);font-size:14px}
.empty b{display:block;font-size:16px;color:var(--txt);margin-bottom:6px;font-weight:600}
.cta{padding:0 0 64px}
.cta-in{position:relative;overflow:hidden;padding:clamp(34px,6vw,52px) clamp(20px,4vw,40px);border-radius:22px;text-align:center;background:linear-gradient(135deg,rgba(99,102,241,.16),rgba(34,211,238,.08));border:1px solid rgba(99,102,241,.25)}
.cta-in h3{font-size:clamp(19px,3.2vw,26px);font-weight:700;letter-spacing:-.8px;margin-bottom:10px}
.cta-in p{max-width:460px;margin:0 auto 24px;font-size:14.5px;line-height:1.7;color:var(--muted)}
.cta-in .btn{padding:13px 28px;font-size:14px;color:#fff;background:linear-gradient(135deg,var(--accent),var(--accent-2));box-shadow:0 10px 28px -12px rgba(34,211,238,.9)}
.cta-in .btn:hover{transform:translateY(-2px);box-shadow:0 16px 36px -12px rgba(34,211,238,1)}
footer{border-top:1px solid var(--line);background:rgba(8,9,14,.6)}
.f-in{display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap;padding:26px 0}
.f-in p{font-size:13px;color:var(--muted)}
.f-links{display:flex;gap:20px;flex-wrap:wrap}
.f-links a{font-size:13px;color:var(--muted);transition:color .2s}
.f-links a:hover{color:#a5b4fc}
.toast{position:fixed;left:50%;bottom:24px;z-index:999;display:flex;align-items:center;gap:9px;padding:12px 20px;border-radius:12px;background:rgba(18,20,28,.97);border:1px solid rgba(52,211,153,.35);color:#6ee7b7;font-size:13.5px;font-weight:600;box-shadow:0 16px 40px -14px rgba(0,0,0,.95);backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);transform:translate(-50%,140%);transition:transform .4s cubic-bezier(.2,.9,.3,1.2);pointer-events:none;max-width:calc(100vw - 32px)}
.toast.show{transform:translate(-50%,0)}
.toast svg{width:16px;height:16px;flex-shrink:0;stroke:currentColor;fill:none;stroke-width:2.4;stroke-linecap:round;stroke-linejoin:round}
.toast span{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.modal{position:fixed;inset:0;z-index:200;display:grid;place-items:center;padding:16px;opacity:0;visibility:hidden;transition:opacity .25s,visibility .25s}
.modal.open{opacity:1;visibility:visible}
.modal-backdrop{position:absolute;inset:0;background:rgba(4,5,10,.78);backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px)}
.modal-panel{position:relative;width:100%;max-width:760px;max-height:calc(100vh - 32px);display:flex;flex-direction:column;border-radius:18px;background:linear-gradient(180deg,#141722,#0e1018);border:1px solid var(--line-hi);box-shadow:0 40px 100px -20px rgba(0,0,0,.95);transform:translateY(16px) scale(.98);transition:transform .3s cubic-bezier(.2,.9,.3,1.1);overflow:hidden}
.modal.open .modal-panel{transform:none}
.modal-head{display:flex;align-items:center;gap:12px;padding:16px 18px;border-bottom:1px solid var(--line);background:rgba(0,0,0,.25)}
.modal-info{flex:1;min-width:0}
.modal-game{font-size:15px;font-weight:700;letter-spacing:-.3px;display:flex;align-items:center;gap:8px}
.modal-game .chip-mini{font-size:9.5px;font-weight:800;letter-spacing:.4px;text-transform:uppercase;padding:3px 7px;border-radius:5px;background:rgba(99,102,241,.18);color:#c7d2fe;border:1px solid rgba(99,102,241,.4)}
.modal-mode{font-size:11.5px;color:var(--muted);margin-top:2px;font-family:ui-monospace,monospace}
.modal-actions{display:flex;gap:6px;flex-shrink:0}
.modal-btn{width:34px;height:34px;border-radius:9px;display:grid;place-items:center;background:rgba(255,255,255,.05);border:1px solid var(--line);color:var(--muted);transition:background .2s,color .2s,border-color .2s,transform .15s}
.modal-btn:hover{background:rgba(255,255,255,.11);color:var(--txt);border-color:var(--line-hi)}
.modal-btn:active{transform:scale(.94)}
.modal-btn svg{width:15px;height:15px;stroke:currentColor;fill:none;stroke-width:2.1;stroke-linecap:round;stroke-linejoin:round}
.modal-btn.ok{background:rgba(52,211,153,.18);color:#6ee7b7;border-color:rgba(52,211,153,.35)}
.modal-url{padding:10px 18px;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:11.5px;color:#8a93b5;background:rgba(0,0,0,.35);border-bottom:1px solid var(--line);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;direction:rtl;text-align:left}
.modal-body{flex:1;min-height:0;overflow:auto;padding:16px 18px;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:12.5px;line-height:1.7;background:#0a0c14;color:#c4cce8}
.modal-body::-webkit-scrollbar{width:10px;height:10px}
.modal-body::-webkit-scrollbar-track{background:transparent}
.modal-body::-webkit-scrollbar-thumb{background:rgba(255,255,255,.09);border-radius:8px;border:2px solid #0a0c14}
.modal-body::-webkit-scrollbar-thumb:hover{background:rgba(255,255,255,.16)}
.modal-body pre{margin:0;white-space:pre;overflow-x:auto}
.j-key{color:#a5b4fc}.j-str{color:#6ee7b7}.j-num{color:#fcd34d}.j-bool{color:#f9a8d4}.j-null{color:#f9a8d4;font-style:italic}.j-punc{color:#6c7499}
.m-state{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:14px;padding:60px 20px;text-align:center;color:var(--muted);font-family:'Inter',sans-serif}
.m-state .spinner{width:36px;height:36px;border-radius:50%;border:3px solid rgba(99,102,241,.2);border-top-color:#818cf8;animation:spin .9s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.m-state.err svg{width:44px;height:44px;stroke:var(--red);fill:none;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}
.m-state.err .t{color:#fca5a5;font-weight:600;font-size:15px}
.m-state.err .d{font-size:12.5px;max-width:420px;line-height:1.7;font-family:ui-monospace,monospace}
@media(max-width:860px){.nav-links,.nav>.btn-key{display:none}.burger{display:grid}}
@media(max-width:560px){
  :root{--header-h:60px}
  .stats{grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
  .sec-head{flex-direction:column;align-items:stretch}
  .filters{overflow-x:auto;padding-bottom:2px;scrollbar-width:none}
  .filters::-webkit-scrollbar{display:none}
  .grid{grid-template-columns:1fr;gap:12px}
  .f-in{flex-direction:column;text-align:center}
  .cta-in .btn{width:100%}
  .modal{padding:8px}
  .modal-panel{max-height:calc(100vh - 16px);border-radius:14px}
  .modal-body{font-size:11.5px;padding:12px 14px}
  .ep-mode{min-width:auto;font-size:9px;padding:3px 6px}
  .ep-url{font-size:10px}
}
</style>
</head>
<body>

<div class="bg"></div>

<header id="hd">
  <div class="wrap nav">
    <a href="#" class="logo">
      <div class="logo-mark"><svg viewBox="0 0 24 24"><path d="M13 2 3 14h8l-1 8 10-12h-8l1-8z"/></svg></div>
      <div class="logo-txt">Game<span>API</span></div>
    </a>
    <nav class="nav-links">
      <a href="#" class="on">Trang chủ</a>
      <a href="#games">Danh sách Game</a>
      <a href="#">Tài liệu</a>
      <a href="#">Bảng giá</a>
      <a href="#">Hỗ trợ</a>
    </nav>
    <button class="btn-key">
      <svg viewBox="0 0 24 24"><path d="M15 3h6v6M10 14 21 3M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/></svg>
      Lấy API Key
    </button>
    <button class="burger" id="burger" aria-label="Menu">
      <svg viewBox="0 0 24 24"><path d="M3 6h18M3 12h18M3 18h18"/></svg>
    </button>
  </div>
</header>

<div class="mobile-menu" id="mobileMenu">
  <a href="#" class="on">Trang chủ</a>
  <a href="#games">Danh sách Game</a>
  <a href="#">Tài liệu API</a>
  <a href="#">Bảng giá</a>
  <a href="#">Hỗ trợ</a>
  <button class="btn-key">
    <svg viewBox="0 0 24 24"><path d="M15 3h6v6M10 14 21 3M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/></svg>
    Lấy API Key
  </button>
</div>

<section class="wrap hero">
  <div class="pill"><i></i> Hệ thống hoạt động · 99.99% uptime</div>
  <h1>Kho <em>API Game</em><br>Đổi Thưởng Siêu Tốc</h1>
  <p>Tích hợp 15 cổng game lớn nhất thị trường. Nhấn vào endpoint để xem JSON trực tiếp từ server.</p>
  <div class="search">
    <svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>
    <input type="search" id="search" placeholder="Tìm game... (Sunwin, 789Club, Haywin...)" autocomplete="off">
  </div>
  <div class="stats">
    <div class="stat"><b>15</b><span>GAME API</span></div>
    <div class="stat"><b>30</b><span>ENDPOINT</span></div>
    <div class="stat"><b>10</b><span>PHIÊN LƯU</span></div>
    <div class="stat"><b>24/7</b><span>HỖ TRỢ</span></div>
  </div>
</section>

<section class="wrap section" id="games">
  <div class="sec-head">
    <div>
      <h2>API Game Nổi Bật</h2>
      <p>Nhấn vào từng dòng endpoint để xem JSON trực tiếp</p>
    </div>
    <div class="filters">
      <button class="chip on" data-f="all">Tất cả</button>
      <button class="chip" data-f="hot">🔥 Hot</button>
      <button class="chip" data-f="new">✨ Mới</button>
      <button class="chip" data-f="vip">👑 VIP</button>
    </div>
  </div>
  <div class="grid" id="grid"></div>
</section>

<section class="wrap cta">
  <div class="cta-in reveal">
    <h3>Sẵn sàng tích hợp API?</h3>
    <p>Đăng ký miễn phí và nhận API Key ngay lập tức. Không cần thẻ tín dụng, hỗ trợ kỹ thuật 1-1.</p>
    <button class="btn">
      <svg viewBox="0 0 24 24"><path d="M13 2 3 14h8l-1 8 10-12h-8l1-8z"/></svg>
      Nhận API Key Miễn Phí
    </button>
  </div>
</section>

<footer>
  <div class="wrap f-in">
    <p>© 2025 GameAPI Hub — Cổng tích hợp API game đổi thưởng.</p>
    <div class="f-links">
      <a href="#">Điều khoản</a>
      <a href="#">Bảo mật</a>
      <a href="#">Tài liệu</a>
      <a href="#">Liên hệ</a>
    </div>
  </div>
</footer>

<div class="toast" id="toast">
  <svg viewBox="0 0 24 24"><path d="M20 6 9 17l-5-5"/></svg>
  <span id="toastMsg">Đã copy!</span>
</div>

<div class="modal" id="modal">
  <div class="modal-backdrop" data-close></div>
  <div class="modal-panel">
    <header class="modal-head">
      <div class="modal-info">
        <div class="modal-game">
          <span id="modalGameName">789Club</span>
          <span class="chip-mini" id="modalModeTag">Tài Xỉu</span>
        </div>
        <div class="modal-mode" id="modalMode">/789/api/tx</div>
      </div>
      <div class="modal-actions">
        <button class="modal-btn" id="modalRefresh" title="Tải lại" aria-label="Refresh">
          <svg viewBox="0 0 24 24"><path d="M21 12a9 9 0 1 1-2.64-6.36"/><path d="M21 4v5h-5"/></svg>
        </button>
        <button class="modal-btn" id="modalCopyUrl" title="Copy URL" aria-label="Copy URL">
          <svg viewBox="0 0 24 24"><rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
        </button>
        <button class="modal-btn" id="modalCopyJson" title="Copy JSON" aria-label="Copy JSON">
          <svg viewBox="0 0 24 24"><path d="M8 3H5a2 2 0 0 0-2 2v3"/><path d="M21 8V5a2 2 0 0 0-2-2h-3"/><path d="M3 16v3a2 2 0 0 0 2 2h3"/><path d="M16 21h3a2 2 0 0 0 2-2v-3"/></svg>
        </button>
        <button class="modal-btn" data-close title="Đóng" aria-label="Close">
          <svg viewBox="0 0 24 24"><path d="M18 6 6 18M6 6l12 12"/></svg>
        </button>
      </div>
    </header>
    <div class="modal-url" id="modalUrl">/789/api/tx</div>
    <div class="modal-body" id="modalBody"></div>
  </div>
</div>

<script>
document.addEventListener('gesturestart', e => e.preventDefault());
document.addEventListener('gesturechange', e => e.preventDefault());
document.addEventListener('gestureend', e => e.preventDefault());
document.addEventListener('touchmove', e => { if (e.touches.length > 1) e.preventDefault(); }, { passive: false });
let lastTouch = 0;
document.addEventListener('touchend', e => {
  const now = Date.now();
  if (now - lastTouch <= 300) e.preventDefault();
  lastTouch = now;
}, { passive: false });
window.addEventListener('wheel', e => { if (e.ctrlKey) e.preventDefault(); }, { passive: false });
window.addEventListener('keydown', e => { if ((e.ctrlKey || e.metaKey) && ['+','-','=','0'].includes(e.key)) e.preventDefault(); });

const MODE_LABELS = { tx:'Tài Xỉu', txmd5:'Tài Xỉu MD5', txhu:'Tài Xỉu Hũ', sicbo:'Sicbo', hu:'Hũ', bac:'Baccarat', xdlc:'Chẵn Lẻ' };
const API_BASE = location.origin;

const GAMES = [
  {
    name:'789Club', sub:'Đẳng cấp số 1 Châu Á', img:'789club.png', logo:'789',
    c1:'#3b82f6', c2:'#8b5cf6', tags:['hot','vip'], players:'96K',
    endpoints:[
      { mode:'tx',    path:'/789/api/tx' },
      { mode:'sicbo', path:'/789/api/sicbo' }
    ]
  },
  {
    name:'B52Club', sub:'Bắn cá & nổ hũ đỉnh cao', img:'b52club.png', logo:'B52',
    c1:'#ef4444', c2:'#f97316', tags:['hot'], players:'72K',
    endpoints:[
      { mode:'tx',    path:'/b52/api/tx' },
      { mode:'txmd5', path:'/b52/api/md5' },
      { mode:'sicbo', path:'/b52/api/sicbo' }
    ]
  },
  {
    name:'Baccarat', sub:'Vua bài cổ điển — tất cả bàn C1..C21', img:'baccarat.png', logo:'BC',
    c1:'#dc2626', c2:'#7c3aed', tags:['new','vip'], players:'53K',
    endpoints:[
      { mode:'bac', path:'/baccarat/api/baccarat' }
    ]
  },
  {
    name:'BetVip', sub:'Cá cược thể thao VIP', img:'betvip.png', logo:'BV',
    c1:'#f59e0b', c2:'#eab308', tags:['vip'], players:'45K',
    endpoints:[
      { mode:'tx',    path:'/betvip/api/tx' },
      { mode:'txmd5', path:'/betvip/api/md5' }
    ]
  },
  {
    name:'Haywin', sub:'Lịch sử Tài Xỉu / MD5', img:'haywin.png', logo:'HW',
    c1:'#0ea5e9', c2:'#06b6d4', tags:['new','hot'], players:'67K',
    endpoints:[
      { mode:'tx',    path:'/haywin/api/taixiu' },
      { mode:'txmd5', path:'/haywin/api/md5' }
    ]
  },
  {
    name:'HitClub', sub:'Nổ hũ triệu phú', img:'hitclub.png', logo:'HC',
    c1:'#f43f5e', c2:'#a855f7', tags:['hot','new'], players:'59K',
    endpoints:[
      { mode:'tx',    path:'/hitclub/api/tx' },
      { mode:'txmd5', path:'/hitclub/api/md5' },
      { mode:'sicbo', path:'/hitclub/api/sicbo' }
    ]
  },
  {
    name:'Lc79', sub:'Lộc phát tài lộc', img:'lc79.png', logo:'LC79',
    c1:'#22c55e', c2:'#10b981', tags:['new'], players:'38K',
    endpoints:[
      { mode:'tx',    path:'/lc79/api/tx' },
      { mode:'txmd5', path:'/lc79/api/md5' }
    ]
  },
  {
    name:'Luck8', sub:'Vận may gõ cửa', img:'luck8.png', logo:'L8',
    c1:'#8b5cf6', c2:'#6366f1', tags:['new','vip'], players:'52K',
    endpoints:[
      { mode:'tx',    path:'/luck8/api/taixiu' },
      { mode:'txmd5', path:'/luck8/api/taixiumd5' },
      { mode:'sicbo', path:'/luck8/api/sicbo20' }
    ]
  },
  {
    name:'Max789', sub:'Cực đại đổi thưởng', img:'max789.png', logo:'MX',
    c1:'#06b6d4', c2:'#3b82f6', tags:['hot'], players:'61K',
    endpoints:[
      { mode:'tx',    path:'/max789/api/tx' },
      { mode:'txmd5', path:'/max789/api/md5' }
    ]
  },
  {
    name:'RikVip', sub:'Huyền thoại game bài', img:'rikvip.png', logo:'RV',
    c1:'#a855f7', c2:'#ec4899', tags:['vip'], players:'88K',
    endpoints:[
      { mode:'tx',    path:'/rikvip/api/tx' },
      { mode:'txmd5', path:'/rikvip/api/md5' },
      { mode:'sicbo', path:'/rikvip/api/sicbo' }
    ]
  },
  {
    name:'Sao789', sub:'Ngôi sao may mắn', img:'sao789.png', logo:'S789',
    c1:'#fbbf24', c2:'#f59e0b', tags:['hot','new'], players:'43K',
    endpoints:[
      { mode:'tx',    path:'/sao789/api/tx' },
      { mode:'txmd5', path:'/sao789/api/md5' }
    ]
  },
  {
    name:'Son789', sub:'Sơn hà xã tắc', img:'son789.png', logo:'SN',
    c1:'#14b8a6', c2:'#06b6d4', tags:['new'], players:'34K',
    endpoints:[
      { mode:'txmd5', path:'/son789/api/tx' }
    ]
  },
  {
    name:'Sunwin', sub:'Cổng game quốc dân', img:'sunwin.png', logo:'SW',
    c1:'#f59e0b', c2:'#ef4444', tags:['hot','vip'], players:'128K',
    endpoints:[
      { mode:'sicbo', path:'/sunwin/api/sicbo' }
    ]
  },
  {
    name:'XocDia88', sub:'Xóc đĩa tài lộc', img:'xocdia88.png', logo:'XD88',
    c1:'#dc2626', c2:'#f59e0b', tags:['new','hot'], players:'49K',
    endpoints:[
      { mode:'tx',    path:'/xocdia88/api/tx' },
      { mode:'txmd5', path:'/xocdia88/api/md5' }
    ]
  },
  {
    name:'XDLC (Xóc Đĩa Chẵn Lẻ)', sub:'Lịch sử chẵn / lẻ theo phiên', img:'xdlc.png', logo:'XL',
    c1:'#ec4899', c2:'#8b5cf6', tags:['new','vip'], players:'41K',
    endpoints:[
      { mode:'xdlc', path:'/xdlc/api/xdlc' }
    ]
  }
];

const ICON_BOLT = '<svg viewBox="0 0 24 24"><path d="M13 2 3 14h8l-1 8 10-12h-8l1-8z"/></svg>';
const ICON_DOC  = '<svg viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/></svg>';
const ICON_COPY = '<svg viewBox="0 0 24 24"><rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>';
const ICON_GO   = '<svg viewBox="0 0 24 24"><path d="M5 12h14M13 5l7 7-7 7"/></svg>';

const grid = document.getElementById('grid');
let currentFilter = 'all';

function render(filter = 'all', keyword = '') {
  const kw = keyword.trim().toLowerCase();
  const list = GAMES.filter(g => {
    const okFilter = filter === 'all' || g.tags.includes(filter);
    const okSearch = !kw || g.name.toLowerCase().includes(kw) || g.sub.toLowerCase().includes(kw);
    return okFilter && okSearch;
  });

  if (!list.length) {
    grid.innerHTML = '<div class="empty"><b>Không tìm thấy game nào</b>Thử từ khoá khác hoặc bỏ bộ lọc nhé.</div>';
    return;
  }

  grid.innerHTML = list.map((g, i) => {
    const allUrls = g.endpoints.map(e => API_BASE + e.path).join('\n');
    return `
    <article class="card reveal" style="--g:linear-gradient(135deg,${g.c1},${g.c2});--glow:${g.c1}aa;transition-delay:${i*30}ms">
      <div class="c-head">
        <div class="c-logo">
          <span class="fb">${g.logo}</span>
          <img src="${g.img}" alt="${g.name}" loading="lazy" onerror="this.remove()">
        </div>
        <div class="c-info">
          <h3>${g.name}<span class="verif"><svg viewBox="0 0 24 24"><path d="M20 6 9 17l-5-5"/></svg></span></h3>
          <div class="sub">${g.sub}</div>
        </div>
      </div>
      <div class="tags">
        ${g.tags.includes('hot')?'<span class="tag hot">🔥 HOT</span>':''}
        ${g.tags.includes('new')?'<span class="tag new">✨ NEW</span>':''}
        ${g.tags.includes('vip')?'<span class="tag vip">👑 VIP</span>':''}
        <span class="tag">🔗 ${g.endpoints.length} link</span>
        <span class="tag">👥 ${g.players}</span>
      </div>
      <div class="endpoints">
        ${g.endpoints.map(ep => `
          <div class="ep-row" data-open="${ep.path}" data-game="${g.name}" data-mode="${ep.mode}">
            <span class="ep-mode ${ep.mode}">${MODE_LABELS[ep.mode]}</span>
            <span class="ep-url">${API_BASE}${ep.path}</span>
            <span class="ep-go">${ICON_GO}</span>
            <button class="ep-copy" data-copy="${API_BASE+ep.path}" data-mode="${MODE_LABELS[ep.mode]}" data-game="${g.name}" title="Copy">${ICON_COPY}</button>
          </div>
        `).join('')}
      </div>
      <div class="c-actions">
        <button class="btn btn-go" data-copy="${allUrls}" data-label="${g.name}">${ICON_BOLT} Lấy tất cả (${g.endpoints.length})</button>
        <button class="btn btn-doc" title="Tài liệu">${ICON_DOC}</button>
      </div>
    </article>`;
  }).join('');

  requestAnimationFrame(() => {
    grid.querySelectorAll('.reveal').forEach(el => observer.observe(el));
  });
}

grid.addEventListener('click', e => {
  const copyBtn = e.target.closest('.ep-copy, .btn-go');
  if (copyBtn) {
    e.stopPropagation();
    const text = copyBtn.dataset.copy;
    const label = copyBtn.dataset.label;
    const mode = copyBtn.dataset.mode;
    const game = copyBtn.dataset.game;
    let msg = label ? `Đã copy ${text.split('\n').length} endpoint của ${label}` : `Đã copy ${mode} — ${game}`;
    const done = () => {
      showToast(msg);
      if (copyBtn.classList.contains('ep-copy')) {
        copyBtn.classList.add('done');
        setTimeout(() => copyBtn.classList.remove('done'), 1200);
      }
    };
    copyText(text, done);
    return;
  }
  const row = e.target.closest('.ep-row');
  if (row && row.dataset.open) {
    openModal(row.dataset.game, row.dataset.mode, row.dataset.open);
  }
});

function copyText(text, done) {
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(text).then(done).catch(fallback);
  } else fallback();
  function fallback() {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.cssText = 'position:fixed;top:0;left:0;opacity:0;pointer-events:none';
    document.body.appendChild(ta);
    ta.focus(); ta.select();
    try { document.execCommand('copy'); done(); } catch(_){}
    ta.remove();
  }
}

const modal = document.getElementById('modal');
const modalBody = document.getElementById('modalBody');
const modalUrl = document.getElementById('modalUrl');
const modalGame = document.getElementById('modalGameName');
const modalModeEl = document.getElementById('modalMode');
const modalModeTag = document.getElementById('modalModeTag');
let currentPath = null;
let currentJsonText = '';

function openModal(game, mode, path) {
  currentPath = path;
  const fullUrl = API_BASE + path;
  modalGame.textContent = game;
  modalModeTag.textContent = MODE_LABELS[mode] || mode.toUpperCase();
  modalModeEl.textContent = path;
  modalUrl.textContent = fullUrl;
  modal.classList.add('open');
  document.body.style.overflow = 'hidden';
  loadJson(fullUrl);
}
function closeModal() {
  modal.classList.remove('open');
  document.body.style.overflow = '';
  currentPath = null;
  currentJsonText = '';
}
function setLoading() {
  modalBody.innerHTML = '<div class="m-state"><div class="spinner"></div><div>Đang tải dữ liệu từ server...</div></div>';
}
function setError(err, url) {
  modalBody.innerHTML = `
    <div class="m-state err">
      <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M12 8v5M12 16h.01"/></svg>
      <div class="t">Không thể tải dữ liệu</div>
      <div class="d">${escapeHtml(err.message || String(err))}</div>
      <div class="d" style="opacity:.7">URL: ${escapeHtml(url)}</div>
      <div class="d" style="opacity:.6;margin-top:6px">Kiểm tra server Flask đang chạy và endpoint đã được đăng ký chưa.</div>
    </div>`;
}
async function loadJson(url) {
  setLoading();
  currentJsonText = '';
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 12000);
    const res = await fetch(url, { signal: controller.signal, cache: 'no-store' });
    clearTimeout(timeout);
    if (!res.ok) throw new Error(`HTTP ${res.status} ${res.statusText}`);
    const data = await res.json();
    currentJsonText = JSON.stringify(data, null, 2);
    modalBody.innerHTML = `<pre>${syntaxHighlight(currentJsonText)}</pre>`;
  } catch (err) {
    let msg = err;
    if (err.name === 'AbortError') msg = new Error('Hết thời gian chờ (12s)');
    else if (err instanceof TypeError) msg = new Error('Không kết nối được server (CORS hoặc server offline)');
    setError(msg, url);
  }
}
function syntaxHighlight(json) {
  return escapeHtml(json).replace(
    /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g,
    match => {
      let cls = 'j-num';
      if (/^"/.test(match)) cls = /:$/.test(match) ? 'j-key' : 'j-str';
      else if (/true|false/.test(match)) cls = 'j-bool';
      else if (/null/.test(match)) cls = 'j-null';
      return `<span class="${cls}">${match}</span>`;
    }
  ).replace(/([{}[\],])/g, '<span class="j-punc">$1</span>');
}
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

modal.addEventListener('click', e => {
  if (e.target.closest('[data-close]')) closeModal();
});
document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && modal.classList.contains('open')) closeModal();
});
document.getElementById('modalRefresh').addEventListener('click', () => { if (currentPath) loadJson(API_BASE + currentPath); });
document.getElementById('modalCopyUrl').addEventListener('click', e => {
  if (!currentPath) return;
  copyText(API_BASE + currentPath, () => {
    showToast('Đã copy URL endpoint');
    const b = e.currentTarget; b.classList.add('ok');
    setTimeout(() => b.classList.remove('ok'), 1200);
  });
});
document.getElementById('modalCopyJson').addEventListener('click', e => {
  if (!currentJsonText) return;
  copyText(currentJsonText, () => {
    showToast('Đã copy JSON');
    const b = e.currentTarget; b.classList.add('ok');
    setTimeout(() => b.classList.remove('ok'), 1200);
  });
});

let toastTimer;
function showToast(msg) {
  const toast = document.getElementById('toast');
  document.getElementById('toastMsg').textContent = msg;
  toast.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove('show'), 2200);
}

document.querySelectorAll('.chip').forEach(chip => {
  chip.addEventListener('click', () => {
    document.querySelectorAll('.chip').forEach(c => c.classList.remove('on'));
    chip.classList.add('on');
    currentFilter = chip.dataset.f;
    render(currentFilter, document.getElementById('search').value);
  });
});

let searchTimer;
document.getElementById('search').addEventListener('input', e => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => render(currentFilter, e.target.value), 160);
});

window.addEventListener('scroll', () => {
  document.getElementById('hd').classList.toggle('scrolled', window.scrollY > 10);
}, { passive: true });

const burger = document.getElementById('burger');
const mobileMenu = document.getElementById('mobileMenu');
burger.addEventListener('click', () => mobileMenu.classList.toggle('open'));
mobileMenu.addEventListener('click', e => { if (e.target.tagName === 'A') mobileMenu.classList.remove('open'); });

const observer = new IntersectionObserver(entries => {
  entries.forEach(en => {
    if (en.isIntersecting) { en.target.classList.add('in'); observer.unobserve(en.target); }
  });
}, { threshold: 0.1, rootMargin: '0px 0px -30px 0px' });
document.querySelectorAll('.reveal').forEach(el => observer.observe(el));

render();
</script>
</body>
</html>"""

# ============================================================
# 6) ROUTES
# ============================================================
@app.route('/')
def index():
    return Response(HTML, mimetype='text/html; charset=utf-8')

@app.route('/<path:filename>')
def serve_static(filename):
    if filename.endswith('.py') or filename.startswith('.') or filename.endswith('.txt'):
        return "Not found", 404
    return send_from_directory(BASE_DIR, filename)

# ============================================================
# 7) KHỞI ĐỘNG WORKERS
# ============================================================
def start_all():
    ok, fail = 0, 0
    for m in MODULES:
        try:
            m.start_background()
            print(f"  ✅ {m.__name__}")
            ok += 1
        except Exception as e:
            print(f"  ❌ {m.__name__}: {e}")
            fail += 1
    print(f"\n📊 Workers: {ok} OK / {fail} lỗi / {len(MISSING)} thiếu file\n")

# ============================================================
# 8) MAIN
# ============================================================
if __name__ == '__main__':
    print("=" * 60)
    print(f"🎮 GameAPI Hub — {len(MODULES)}/{len(MODULE_NAMES)} game khả dụng")
    print("=" * 60)
    print("⏳ Đang khởi động các worker...\n")

    start_all()

    port = int(os.environ.get('PORT', 5000))
    print("=" * 60)
    print(f"🚀 Server sẵn sàng:  http://localhost:{port}")
    print("💡 Chỉ giữ 10 phiên gần nhất — không lưu file JSON")
    print("=" * 60)

    app.run(
        host='0.0.0.0',
        port=port,
        debug=False,
        threaded=True,
        use_reloader=False
    )