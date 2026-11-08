# haywin.py — Advanced Markov Analyzer (educational/research only)
import math
import time
import threading
import requests
from flask import Blueprint, jsonify

bp = Blueprint("haywin", __name__, url_prefix="/haywin/api")

POLL_INTERVAL = 5
RETRY_DELAY = 5
MAX_HISTORY = 10   # main.py sẽ ghi đè
ID_TAG = "@tiendataox"


class AdvancedMarkovAnalyzer:
    def __init__(self, states=None, order=2, decay=0.98, laplace=1,
                 memories=None, max_history=1000):
        self.states = states or ['Tài', 'Xỉu']
        self.order = max(1, order)
        self.decay = decay
        self.laplace = laplace
        self.memories = memories or [3, 10, 50]
        self.max_history = max_history
        self.transition_counts = {}
        self.pattern_freq = {}
        self.raw_history = []
        self.prediction_history = {}

    def _apply_decay(self):
        for ctx in list(self.transition_counts.keys()):
            counts = self.transition_counts[ctx]
            new_c, total = {}, 0
            for s in self.states:
                v = counts.get(s, 0) * self.decay
                new_c[s] = v
                total += v
            if total < 1e-6:
                del self.transition_counts[ctx]
            else:
                self.transition_counts[ctx] = new_c
        for pat in list(self.pattern_freq.keys()):
            v = self.pattern_freq[pat] * self.decay
            if v < 1e-6:
                del self.pattern_freq[pat]
            else:
                self.pattern_freq[pat] = v

    def update(self, actual_state):
        if actual_state not in self.states:
            raise ValueError(f"Unknown state: {actual_state}")
        self.raw_history.append(actual_state)
        if len(self.raw_history) > self.max_history:
            self.raw_history.pop(0)
        L = len(self.raw_history)
        for pat_len in range(1, min(self.order, L) + 1):
            seq = '|'.join(self.raw_history[L - pat_len:])
            self.pattern_freq[seq] = self.pattern_freq.get(seq, 0) + 1
        for k in range(1, self.order + 1):
            ctx_start = L - 1 - k
            if ctx_start < 0:
                continue
            ctx = '|'.join(self.raw_history[ctx_start:ctx_start + k])
            counts = self.transition_counts.get(ctx, {})
            counts[actual_state] = counts.get(actual_state, 0) + 1
            self.transition_counts[ctx] = counts
        if L % 20 == 0:
            self._apply_decay()

    def _probs_for_ctx(self, ctx):
        counts = self.transition_counts.get(ctx, {})
        total = sum(counts.get(s, 0) for s in self.states)
        K = len(self.states)
        return {s: (counts.get(s, 0) + self.laplace) / (total + self.laplace * K)
                for s in self.states}

    def predict_ensemble(self):
        aggregate = {s: 0.0 for s in self.states}
        L = len(self.raw_history)
        if L == 0:
            u = 1.0 / len(self.states)
            return {"probs": {s: u for s in self.states},
                    "chosen": self.states[0], "confidence": 0}
        for mem in self.memories:
            mem_size = min(mem, L)
            order_for_mem = min(self.order, mem_size)
            ctx = '|'.join(self.raw_history[L - order_for_mem:])
            probs = self._probs_for_ctx(ctx)
            weight = 1.0 / (1 + math.log(1 + mem))
            for s in self.states:
                aggregate[s] += probs[s] * weight
        total = sum(aggregate.values())
        if total <= 0:
            u = 1.0 / len(self.states)
            aggregate = {s: u for s in self.states}
        else:
            aggregate = {s: v / total for s, v in aggregate.items()}
        chosen = max(self.states, key=lambda s: aggregate[s])
        conf = abs(aggregate[self.states[0]] - aggregate[self.states[1]]) \
            if len(self.states) >= 2 else 0
        return {"probs": aggregate, "chosen": chosen, "confidence": conf}

    def top_patterns(self, k=20, max_len=None):
        arr = []
        for pat, cnt in self.pattern_freq.items():
            parts = pat.split('|')
            if max_len and len(parts) > max_len:
                continue
            arr.append({"pattern": pat, "count": cnt, "length": len(parts)})
        arr.sort(key=lambda x: x["count"], reverse=True)
        return arr[:k]

    def save_prediction(self, phien, result):
        entry = dict(result)
        entry["timestamp"] = int(time.time() * 1000)
        self.prediction_history[phien] = entry
        if len(self.prediction_history) > 500:
            del self.prediction_history[next(iter(self.prediction_history))]

    def get_prediction(self, phien):
        return self.prediction_history.get(phien)

    def get_full_analysis(self):
        L = len(self.raw_history)
        mem_analyses = {}
        for mem in self.memories:
            mem_size = min(mem, L)
            order_for_mem = min(self.order, mem_size)
            ctx = '|'.join(self.raw_history[L - order_for_mem:])
            mem_analyses[f"m{mem}"] = {"context": ctx,
                                       "probs": self._probs_for_ctx(ctx)}
        return {
            "order": self.order,
            "decay": self.decay,
            "laplace": self.laplace,
            "memories": self.memories,
            "rawHistoryLength": L,
            "rawHistorySample": self.raw_history[-min(50, L):],
            "transitionContextsStored": len(self.transition_counts),
            "topPatterns": self.top_patterns(30, self.order),
            "memoryAnalyses": mem_analyses,
        }


advanced_tx = AdvancedMarkovAnalyzer(order=3, decay=0.985, laplace=1,
                                     memories=[3, 10, 50], max_history=2000)
advanced_md5 = AdvancedMarkovAnalyzer(order=3, decay=0.985, laplace=1,
                                      memories=[3, 10, 50], max_history=2000)

latest_100 = {"Phien": 0, "Xuc_xac_1": 0, "Xuc_xac_2": 0, "Xuc_xac_3": 0,
              "Tong_diem": 0, "Pattern": "Chưa có", "Phien_hien_tai": 0,
              "Du_doan": "Chưa có", "Tong_du_doan": 0,
              "Tong_thang": 0, "Tong_thua": 0, "Id": ID_TAG}
latest_101 = dict(latest_100)

history_100 = []
history_101 = []
last_sid_100 = None
last_sid_101 = None
sid_for_tx = None

stats = {
    "ban_tai_xiu": {"totalPredictions": 0, "totalWins": 0, "totalLosses": 0},
    "ban_md5": {"totalPredictions": 0, "totalWins": 0, "totalLosses": 0},
}


def _update_result(store, history, analyzer, stat, result, table_name):
    store.update(result)
    actual = 'Tài' if store["Tong_diem"] > 10 else 'Xỉu'
    store["Pattern"] = actual
    analyzer.update(actual)
    pred = analyzer.predict_ensemble()
    store["Phien_hien_tai"] = store["Phien"] + 1
    store["Du_doan"] = pred["chosen"]
    store["Du_doan_confidence"] = round(pred["confidence"], 3)
    store["Du_doan_probs"] = pred["probs"]
    analyzer.save_prediction(store["Phien_hien_tai"], {
        "prediction": pred["chosen"], "probs": pred["probs"],
        "confidence": pred["confidence"]
    })
    if history:
        prev = history[0]
        prev_pred = analyzer.get_prediction(prev["Phien"])
        if prev_pred and prev_pred.get("prediction"):
            stat["totalPredictions"] += 1
            was_correct = prev_pred["prediction"] == actual
            if was_correct:
                stat["totalWins"] += 1
            else:
                stat["totalLosses"] += 1
            prev["Tong_thang"] = stat["totalWins"]
            prev["Tong_thua"] = stat["totalLosses"]
            prev["Tong_du_doan"] = stat["totalPredictions"]
            prev["Du_doan"] = prev_pred["prediction"]
            prev["Danh_gia"] = "Đúng" if was_correct else "Sai"
    entry = dict(result)
    entry["Ket_qua"] = actual
    entry["Tong_thang"] = stat["totalWins"]
    entry["Tong_thua"] = stat["totalLosses"]
    entry["Tong_du_doan"] = stat["totalPredictions"]
    entry["Id"] = ID_TAG
    history.insert(0, entry)
    if len(history) > MAX_HISTORY:
        history.pop()
    store["Tong_du_doan"] = stat["totalPredictions"]
    store["Tong_thang"] = stat["totalWins"]
    store["Tong_thua"] = stat["totalLosses"]
    store["Id"] = ID_TAG


def _poll_taixiu():
    global last_sid_100, sid_for_tx
    url = ("https://jakpotgwab.geightdors.net/glms/v1/notify/taixiu"
           "?platform_id=rik&gid=vgmn_100")
    while True:
        try:
            r = requests.get(url, headers={"User-Agent": "Py-Proxy/1.0"},
                             timeout=10)
            data = r.json()
            if data.get("status") == "OK" and isinstance(data.get("data"), list):
                for g in data["data"]:
                    if g.get("cmd") == 1008:
                        sid_for_tx = g.get("sid")
                for g in data["data"]:
                    if g.get("cmd") == 1003:
                        sid = sid_for_tx
                        d1, d2, d3 = g.get("d1"), g.get("d2"), g.get("d3")
                        if sid and sid != last_sid_100 and all(v is not None for v in (d1, d2, d3)):
                            last_sid_100 = sid
                            res = {"Phien": sid, "Xuc_xac_1": d1, "Xuc_xac_2": d2,
                                   "Xuc_xac_3": d3, "Tong_diem": d1 + d2 + d3}
                            _update_result(latest_100, history_100, advanced_tx,
                                           stats["ban_tai_xiu"], res, "TÀI XỈU")
                            print(f"[Haywin-TX] Phiên {sid} | Tổng {res['Tong_diem']} | Next {latest_100['Du_doan']}")
                            sid_for_tx = None
        except Exception as e:
            print(f"[Haywin-TX] Lỗi: {e}")
            time.sleep(RETRY_DELAY)
        time.sleep(POLL_INTERVAL)


def _poll_md5():
    global last_sid_101
    url = ("https://jakpotgwab.geightdors.net/glms/v1/notify/taixiu"
           "?platform_id=rik&gid=vgmn_101")
    while True:
        try:
            r = requests.get(url, headers={"User-Agent": "Py-Proxy/1.0"},
                             timeout=10)
            data = r.json()
            if data.get("status") == "OK" and isinstance(data.get("data"), list):
                for g in data["data"]:
                    if g.get("cmd") == 7006 and g.get("d1") and g.get("d2") and g.get("d3"):
                        sid = g.get("sid")
                        if sid and sid != last_sid_101:
                            last_sid_101 = sid
                            res = {"Phien": sid, "Xuc_xac_1": g["d1"],
                                   "Xuc_xac_2": g["d2"], "Xuc_xac_3": g["d3"],
                                   "Tong_diem": g["d1"] + g["d2"] + g["d3"]}
                            _update_result(latest_101, history_101, advanced_md5,
                                           stats["ban_md5"], res, "MD5")
                            print(f"[Haywin-MD5] Phiên {sid} | Next {latest_101['Du_doan']}")
        except Exception as e:
            print(f"[Haywin-MD5] Lỗi: {e}")
            time.sleep(RETRY_DELAY)
        time.sleep(POLL_INTERVAL)


# ====================== ROUTES ======================
@bp.route("/taixiu")
def api_taixiu():
    return jsonify(latest_100)


@bp.route("/md5")
def api_md5():
    return jsonify(latest_101)


@bp.route("/history")
def api_history():
    ls = [{"Phien": i["Phien"], "Du_doan": i.get("Du_doan", "Chưa có"),
           "Ket_qua": i.get("Ket_qua"),
           "Danh_gia": i.get("Danh_gia", "Chưa đánh giá")} for i in history_100]
    return jsonify({
        "ban": "Tài Xỉu",
        "Tong_so_phien_du_doan": stats["ban_tai_xiu"]["totalPredictions"],
        "Tong_du_doan_dung": stats["ban_tai_xiu"]["totalWins"],
        "Tong_du_doan_sai": stats["ban_tai_xiu"]["totalLosses"],
        "lich_su": ls,
    })


@bp.route("/history/md5")
def api_history_md5():
    ls = [{"Phien": i["Phien"], "Du_doan": i.get("Du_doan", "Chưa có"),
           "Ket_qua": i.get("Ket_qua"),
           "Danh_gia": i.get("Danh_gia", "Chưa đánh giá")} for i in history_101]
    return jsonify({
        "ban": "MD5",
        "Tong_so_phien_du_doan": stats["ban_md5"]["totalPredictions"],
        "Tong_du_doan_dung": stats["ban_md5"]["totalWins"],
        "Tong_du_doan_sai": stats["ban_md5"]["totalLosses"],
        "lich_su": ls,
    })


@bp.route("/stats")
def api_stats():
    def s(k):
        st = stats[k]
        return {
            "accuracy": round(st["totalWins"] / st["totalPredictions"] * 100, 2)
                if st["totalPredictions"] else 0,
            "total_predictions": st["totalPredictions"],
            "correct_predictions": st["totalWins"],
            "incorrect_predictions": st["totalLosses"],
            "current_prediction": latest_100["Du_doan"] if k == "ban_tai_xiu"
                else latest_101["Du_doan"],
            "history_length": len(advanced_tx.raw_history) if k == "ban_tai_xiu"
                else len(advanced_md5.raw_history),
        }
    return jsonify({
        "ban_tai_xiu": s("ban_tai_xiu"),
        "ban_md5": s("ban_md5"),
        "markov_analysis": advanced_tx.get_full_analysis(),
    })


@bp.route("/markov")
def api_markov():
    return jsonify({
        "ban": "Tài Xỉu",
        "advanced_config": {"order": advanced_tx.order, "decay": advanced_tx.decay,
                            "laplace": advanced_tx.laplace,
                            "memories": advanced_tx.memories},
        "analysis": advanced_tx.get_full_analysis(),
        "latest_prediction": list(advanced_tx.prediction_history.items())[-5:]
            if advanced_tx.prediction_history else [],
    })


@bp.route("/markov/md5")
def api_markov_md5():
    return jsonify({
        "ban": "MD5",
        "advanced_config": {"order": advanced_md5.order, "decay": advanced_md5.decay,
                            "laplace": advanced_md5.laplace,
                            "memories": advanced_md5.memories},
        "analysis": advanced_md5.get_full_analysis(),
        "latest_prediction": list(advanced_md5.prediction_history.items())[-5:]
            if advanced_md5.prediction_history else [],
    })


def start_background():
    threading.Thread(target=_poll_taixiu, daemon=True).start()
    threading.Thread(target=_poll_md5, daemon=True).start()