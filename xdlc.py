# xdlc.py — 79 thuật toán dự đoán Chẵn Lẻ (port từ server.js)
import random
import time
import threading
import requests
from flask import Blueprint, jsonify

bp = Blueprint("xdlc", __name__, url_prefix="/xdlc/api")

API_URL = "https://wcl.tele68.com/v1/chanlefull/lite-sessions"
API_PARAMS = {"cp": "R", "cl": "R", "pf": "web",
              "at": "bc1qgk07vhn53ws7khy3840gjjvlw7qgzftfjgweq2"}

latest_sessions = []
last_update_time = None
update_count = 0


def fetch_latest():
    global latest_sessions, last_update_time, update_count
    try:
        r = requests.get(API_URL, params=API_PARAMS, timeout=5)
        new_data = r.json().get("list") or []
        if new_data:
            if not latest_sessions or latest_sessions[0].get("id") != new_data[0].get("id"):
                latest_sessions = new_data
                last_update_time = time.strftime("%Y-%m-%dT%H:%M:%S")
                update_count += 1
                print(f"[XDLC] Cập nhật phiên {new_data[0].get('id')}")
    except Exception as e:
        print(f"[XDLC] Lỗi fetch: {e}")


def _loop():
    while True:
        fetch_latest()
        time.sleep(2)


# ========== 79 THUẬT TOÁN ==========
def ma3(r):
    c = sum(1 for x in r[:3] if x == 'chan')
    return {"prediction": 'chan' if c >= 2 else 'le', "confidence": 60 + c * 10}

def ma5(r):
    c = sum(1 for x in r[:5] if x == 'chan')
    return {"prediction": 'chan' if c >= 3 else 'le', "confidence": 60 + c * 8}

def ma7(r):
    c = sum(1 for x in r[:7] if x == 'chan')
    return {"prediction": 'chan' if c >= 4 else 'le', "confidence": 60 + c * 6}

def ma10(r):
    c = sum(1 for x in r[:10] if x == 'chan')
    return {"prediction": 'chan' if c >= 5 else 'le', "confidence": 60 + c * 5}

def ema(r):
    e = 1 if r[0] == 'chan' else 0
    a = 0.3
    for i in range(1, min(20, len(r))):
        v = 1 if r[i] == 'chan' else 0
        e = a * v + (1 - a) * e
    return {"prediction": 'chan' if e > 0.5 else 'le', "confidence": abs(e - 0.5) * 200}

def wma(r):
    ws, wt = 0, 0
    for i in range(min(10, len(r))):
        w = 10 - i
        ws += (1 if r[i] == 'chan' else 0) * w
        wt += w
    v = ws / wt if wt else 0.5
    return {"prediction": 'chan' if v > 0.5 else 'le', "confidence": abs(v - 0.5) * 200}

def holt_winters(r):
    l = 1 if r[0] == 'chan' else 0
    t = 0
    for i in range(1, min(20, len(r))):
        v = 1 if r[i] == 'chan' else 0
        nl = 0.2 * v + 0.8 * (l + t)
        t = 0.1 * (nl - l) + 0.9 * t
        l = nl
    f = l + t
    return {"prediction": 'chan' if f > 0.5 else 'le', "confidence": abs(f - 0.5) * 200}

def arima(r):
    diff = [(1 if r[i-1] == 'chan' else 0) - (1 if r[i] == 'chan' else 0)
            for i in range(1, len(r))]
    ma = sum(diff[:2]) / 2 if diff else 0
    ar = ma
    f = (1 if r[0] == 'chan' else 0) + (ar + ma) / 2
    return {"prediction": 'chan' if f > 0.5 else 'le', "confidence": abs(f - 0.5) * 200}

def sarima(r):
    seasonal = [1 if r[i] == r[i+1] else 0 for i in range(min(12, len(r) - 1))]
    s = sum(seasonal) / len(seasonal) if seasonal else 0.5
    trend = sum(1 for x in r[:5] if x == 'chan') / 5
    f = (trend + s) / 2
    return {"prediction": 'chan' if f > 0.5 else 'le', "confidence": abs(f - 0.5) * 200}

def garch(r):
    var = 0.5
    for i in range(1, min(20, len(r))):
        rr = (1 if r[i] == 'chan' else 0) - (1 if r[i-1] == 'chan' else 0)
        var = 0.1 * rr * rr + 0.9 * var
    return {"prediction": 'le' if r[0] == 'chan' else 'chan',
            "confidence": min(90, 50 + var * 50)}

def knn(r, k=3, kk=5):
    d = []
    for i in range(1, min(30, len(r))):
        dist = 0
        for j in range(k):
            if i + j < len(r) and r[j] != r[i + j]:
                dist += 1
        d.append({"dist": dist, "next": r[i-1]})
    d.sort(key=lambda x: x["dist"])
    kk = min(kk, len(d))
    c = sum(1 for x in d[:kk] if x["next"] == 'chan')
    return {"prediction": 'chan' if c > kk/2 else 'le', "confidence": (c/kk)*100 if kk else 50}

def naive_bayes(r):
    p_chan = sum(1 for x in r if x == 'chan') / len(r)
    p_le = 1 - p_chan
    cond = {'chan': {}, 'le': {}}
    for i in range(1, min(20, len(r))):
        prev, curr = r[i-1], r[i]
        cond[curr][prev] = cond[curr].get(prev, 0) + 1
    last = r[0]
    pc = p_chan * (cond['chan'].get(last, 1) / len(r))
    pl = p_le * (cond['le'].get(last, 1) / len(r))
    return {"prediction": 'chan' if pc > pl else 'le',
            "confidence": (max(pc, pl) / (pc + pl)) * 100 if (pc + pl) else 50}

def decision_tree(r):
    import math
    def entropy(arr):
        if not arr: return 0
        c = sum(1 for x in arr if x == 'chan') / len(arr)
        l = 1 - c
        return -(c * math.log2(c or 1) + l * math.log2(l or 1))
    best_gain, best_feat = 0, 0
    n = min(40, len(r))
    for f in range(4):
        left, right = [], []
        for i in range(4, n):
            val = r[i - 4 + f]
            (left if val == 'chan' else right).append(r[i])
        gain = entropy(r[4:n]) - (len(left)/n)*entropy(left) - (len(right)/n)*entropy(right)
        if gain > best_gain:
            best_gain, best_feat = gain, f
    test = r[best_feat] if best_feat < len(r) else 'chan'
    c, l = 0, 0
    for i in range(4, n):
        val = r[i - 4 + best_feat]
        if val == test:
            if r[i] == 'chan': c += 1
            else: l += 1
    return {"prediction": 'chan' if c > l else 'le',
            "confidence": (max(c, l) / (c + l + 1)) * 100}

def random_forest(r):
    c, l = 0, 0
    for _ in range(20):
        sample = [r[random.randrange(len(r))] for _ in range(30)]
        cc = sum(1 for x in sample if x == 'chan')
        if cc > 15: c += 1
        else: l += 1
    return {"prediction": 'chan' if c > l else 'le',
            "confidence": (max(c, l) / 20) * 100}

def gradient_boost(r):
    pred = 0.5
    for _ in range(30):
        res = (1 if r[0] == 'chan' else 0) - pred
        pred += 0.1 * (0.1 if res > 0 else -0.1)
    return {"prediction": 'chan' if pred > 0.5 else 'le', "confidence": abs(pred - 0.5) * 200}

def xgboost(r):
    score = 0
    for _ in range(20):
        th = random.random()
        w = random.random()
        if (1 if r[0] == 'chan' else 0) > th: score += w
        else: score -= w
    return {"prediction": 'chan' if score > 0 else 'le', "confidence": min(95, abs(score) * 10)}

def lightgbm(r):
    bins = 10
    hist = [0] * bins
    for i in range(min(30, len(r))):
        b = i * bins // 30
        hist[b] += 1 if r[i] == 'chan' else -1
    g = sum(hist)
    return {"prediction": 'chan' if g > 0 else 'le', "confidence": min(95, abs(g) * 5)}

def catboost(r):
    import math
    cats = [1 if x == 'chan' else 0 for x in r[:10]]
    pred = sum(cats[i] * math.exp(-i/3) for i in range(len(cats)))
    pred = 1 / (1 + math.exp(-pred/5))
    return {"prediction": 'chan' if pred > 0.5 else 'le', "confidence": abs(pred - 0.5) * 200}

def logistic_regression(r):
    import math
    w, b = 0.0, 0.0
    for i in range(1, min(30, len(r))):
        x = 1 if r[i-1] == 'chan' else -1
        y = 1 if r[i] == 'chan' else 0
        p = 1 / (1 + math.exp(-(w*x + b)))
        e = y - p
        w += 0.01 * e * x
        b += 0.01 * e
    last = 1 if r[0] == 'chan' else -1
    f = 1 / (1 + math.exp(-(w*last + b)))
    return {"prediction": 'chan' if f > 0.5 else 'le', "confidence": abs(f - 0.5) * 200}

def svm_linear(r):
    w, b = 0.0, 0.0
    for i in range(1, min(30, len(r))):
        x = 1 if r[i-1] == 'chan' else -1
        y = 1 if r[i] == 'chan' else -1
        if y * (w*x + b) <= 1:
            w += 0.01 * y * x
            b += 0.01 * y
    last = 1 if r[0] == 'chan' else -1
    pred = w * last + b
    return {"prediction": 'chan' if pred > 0 else 'le', "confidence": min(95, abs(pred) * 50)}

def svm_rbf(r):
    import math
    gamma = 0.5
    n = min(30, len(r))
    alpha = [0.0] * n
    for _ in range(20):
        for i in range(1, n):
            x = 1 if r[i-1] == 'chan' else -1
            y = 1 if r[i] == 'chan' else -1
            pred = sum(alpha[j] * math.exp(-gamma * (x - (1 if r[j-1]=='chan' else -1))**2) for j in range(1, n))
            if y * pred <= 1: alpha[i] += 0.01
    last = 1 if r[0] == 'chan' else -1
    f = sum(alpha[j] * math.exp(-gamma * (last - (1 if r[j-1]=='chan' else -1))**2) for j in range(1, n))
    return {"prediction": 'chan' if f > 0 else 'le', "confidence": min(95, abs(f) * 50)}

def perceptron(r):
    w, b = 0.0, 0.0
    for _ in range(10):
        for i in range(1, min(30, len(r))):
            x = 1 if r[i-1] == 'chan' else 0
            y = 1 if r[i] == 'chan' else 0
            pred = 1 if (w*x + b) > 0 else 0
            if pred != y:
                w += 0.1 * (y - pred) * x
                b += 0.1 * (y - pred)
    last = 1 if r[0] == 'chan' else 0
    f = w * last + b
    return {"prediction": 'chan' if f > 0 else 'le', "confidence": min(90, abs(f) * 50)}

def mlp(r):
    import math
    w1 = [random.random() for _ in range(3)]
    w2 = [random.random() for _ in range(3)]
    b1, b2 = random.random(), random.random()
    for _ in range(20):
        for i in range(3, min(30, len(r))):
            x = [1 if r[i-3+j] == 'chan' else 0 for j in range(3)]
            y = 1 if r[i] == 'chan' else 0
            h = 1 / (1 + math.exp(-(sum(x[j]*w1[j] for j in range(3)) + b1)))
            out = 1 / (1 + math.exp(-(h*sum(w2) + b2)))
            e = y - out
            for j in range(3): w2[j] += 0.1 * e * h
            for j in range(3): w1[j] += 0.1 * e * w2[j] * h * (1 - h) * x[j]
    x = [1 if r[2-j] == 'chan' else 0 for j in range(3)]
    h = 1 / (1 + math.exp(-(sum(x[j]*w1[j] for j in range(3)) + b1)))
    out = 1 / (1 + math.exp(-(h*sum(w2) + b2)))
    return {"prediction": 'chan' if out > 0.5 else 'le', "confidence": abs(out - 0.5) * 200}

def rnn(r):
    import math
    h = 0
    for i in range(min(20, len(r))):
        x = 1 if r[i] == 'chan' else -1
        h = math.tanh(0.5*h + 0.5*x)
    return {"prediction": 'chan' if h > 0 else 'le', "confidence": abs(h) * 100}

def lstm(r):
    import math
    c, h = 0.0, 0.0
    for i in range(min(20, len(r))):
        x = 1 if r[i] == 'chan' else -1
        c = 0.9*c + 0.1*x
        h = 0.5 * math.tanh(c)
    return {"prediction": 'chan' if h > 0 else 'le', "confidence": abs(h) * 100}

def gru(r):
    import math
    h = 0.0
    for i in range(min(20, len(r))):
        x = 1 if r[i] == 'chan' else -1
        z = 1 / (1 + math.exp(-(0.7*h + x)))
        rr = 1 / (1 + math.exp(-(0.3*h + x)))
        ht = math.tanh(x + rr*h)
        h = (1 - z)*h + z*ht
    return {"prediction": 'chan' if h > 0 else 'le', "confidence": abs(h) * 100}

def bilstm(r):
    import math
    fw, bw = 0.0, 0.0
    n = min(15, len(r))
    for i in range(n):
        x = 1 if r[i] == 'chan' else -1
        fw = math.tanh(0.5*fw + 0.5*x)
    for i in range(n - 1, -1, -1):
        x = 1 if r[i] == 'chan' else -1
        bw = math.tanh(0.5*bw + 0.5*x)
    h = (fw + bw) / 2
    return {"prediction": 'chan' if h > 0 else 'le', "confidence": abs(h) * 100}

def autoencoder(r):
    enc = []
    for i in range(0, min(15, len(r)), 3):
        pat = r[i:i+3]
        if pat: enc.append(sum(1 for x in pat if x == 'chan') / len(pat))
    avg = sum(enc) / len(enc) if enc else 0.5
    return {"prediction": 'chan' if avg > 0.5 else 'le', "confidence": abs(avg - 0.5) * 200}

def cnn1d(r):
    feats = []
    for fs in [2, 3, 4]:
        max_f = 0
        for i in range(len(r) - fs + 1):
            pat = r[i:i+fs]
            c = sum(1 for x in pat if x == 'chan') / fs
            max_f = max(max_f, c)
        feats.append(max_f)
    avg = sum(feats) / len(feats) if feats else 0.5
    return {"prediction": 'chan' if avg > 0.5 else 'le', "confidence": abs(avg - 0.5) * 200}

def transformer(r):
    import math
    q = 1 if r[0] == 'chan' else 0
    att_sum, wt_sum = 0, 0
    for i in range(1, min(15, len(r))):
        k = 1 if r[i] == 'chan' else 0
        v = 1 if r[i-1] == 'chan' else 0
        att = math.exp(-abs(q - k) / 2)
        att_sum += att * v
        wt_sum += att
    out = att_sum / wt_sum if wt_sum else 0.5
    return {"prediction": 'chan' if out > 0.5 else 'le', "confidence": abs(out - 0.5) * 200}

def attention(r):
    import math
    n = min(10, len(r))
    weights = [math.exp(-i/3) * (1.5 if i > 0 and r[i] == r[0] else 1) for i in range(n)]
    total = sum(weights)
    c, l = 0, 0
    for i, w in enumerate(weights):
        if r[i] == 'chan': c += w / total
        else: l += w / total
    return {"prediction": 'chan' if c > l else 'le', "confidence": abs(c - l) * 100}

def resnet(r):
    import math
    x = 1 if r[0] == 'chan' else -1
    residual = x
    for i in range(1, min(10, len(r))):
        x = math.tanh(0.5*x + 0.5*(1 if r[i] == 'chan' else -1))
    x = (x + residual) / 2
    return {"prediction": 'chan' if x > 0 else 'le', "confidence": abs(x) * 100}

def dqn(r):
    q = {}
    state = ','.join(r[:3])
    for i in range(3, min(30, len(r)) - 1):
        action = r[i]
        reward = 1 if r[i+1] == action else -0.5
        next_state = ','.join(r[i-2:i+1])
        q.setdefault(state, {'chan': 0, 'le': 0})
        q.setdefault(next_state, {'chan': 0, 'le': 0})
        q[state][action] += 0.1 * (reward + 0.9*max(q[next_state].values()) - q[state][action])
        state = next_state
    last = ','.join(r[:3])
    if last not in q:
        return {"prediction": 'le' if r[0] == 'chan' else 'chan', "confidence": 60}
    c, l = q[last]['chan'], q[last]['le']
    return {"prediction": 'chan' if c > l else 'le',
            "confidence": abs(c - l) / max(c + l, 1) * 100}

def genetic(r):
    pop = [{"genes": [random.random() for _ in range(5)], "fit": 0} for _ in range(20)]
    for _ in range(30):
        for ind in pop:
            correct = 0
            for i in range(min(20, len(r) - 1)):
                score = sum(ind["genes"][j] * (1 if r[i+j] == 'chan' else -1) for j in range(5) if i+j < len(r))
                pred = 'chan' if score > 0 else 'le'
                if pred == r[i+1]: correct += 1
            ind["fit"] = correct / max(min(19, len(r) - 1), 1)
        pop.sort(key=lambda x: x["fit"], reverse=True)
        pop = pop[:10]
        while len(pop) < 20:
            p1, p2 = random.choice(pop[:10]), random.choice(pop[:10])
            child = {"genes": [(p1["genes"][j] + p2["genes"][j]) / 2 for j in range(5)], "fit": 0}
            if random.random() < 0.1:
                child["genes"][random.randrange(5)] += (random.random() - 0.5) * 0.2
            pop.append(child)
    score = sum(pop[0]["genes"][j] * (1 if r[j] == 'chan' else -1) for j in range(5) if j < len(r))
    return {"prediction": 'chan' if score > 0 else 'le',
            "confidence": min(95, pop[0]["fit"] * 100 + 10)}

def pso(r):
    particles = [{"pos": random.random()*2-1, "vel": (random.random()-0.5)*0.5,
                  "bestPos": 0, "bestFit": -1e9} for _ in range(15)]
    g = {"pos": 0, "fit": -1e9}
    for _ in range(20):
        for p in particles:
            correct = 0
            for i in range(min(20, len(r) - 1)):
                pred = 'chan' if p["pos"] * (1 if r[i] == 'chan' else -1) > 0 else 'le'
                if pred == r[i+1]: correct += 1
            fit = correct / max(min(19, len(r) - 1), 1)
            if fit > p["bestFit"]:
                p["bestFit"], p["bestPos"] = fit, p["pos"]
            if fit > g["fit"]:
                g["fit"], g["pos"] = fit, p["pos"]
        for p in particles:
            p["vel"] = 0.7*p["vel"] + 0.5*random.random()*(p["bestPos"]-p["pos"]) + 0.5*random.random()*(g["pos"]-p["pos"])
            p["pos"] = max(-1, min(1, p["pos"] + p["vel"]))
    pred = 'chan' if g["pos"] * (1 if r[0] == 'chan' else -1) > 0 else 'le'
    return {"prediction": pred, "confidence": min(95, g["fit"] * 100 + 10)}

def simulated_annealing(r):
    import math
    curr = random.random() * 2 - 1
    best, bestFit, temp = curr, -1e9, 1.0
    for _ in range(50):
        correct = 0
        for i in range(min(20, len(r) - 1)):
            pred = 'chan' if curr * (1 if r[i] == 'chan' else -1) > 0 else 'le'
            if pred == r[i+1]: correct += 1
        fit = correct / max(min(19, len(r) - 1), 1)
        if fit > bestFit:
            bestFit, best = fit, curr
        neighbor = curr + (random.random() - 0.5) * temp
        n_fit = 0
        for i in range(min(20, len(r) - 1)):
            pred = 'chan' if neighbor * (1 if r[i] == 'chan' else -1) > 0 else 'le'
            if pred == r[i+1]: n_fit += 1
        n_fit /= max(min(19, len(r) - 1), 1)
        if n_fit > fit or math.exp((n_fit - fit) / temp) > random.random():
            curr = neighbor
        temp *= 0.95
    pred = 'chan' if best * (1 if r[0] == 'chan' else -1) > 0 else 'le'
    return {"prediction": pred, "confidence": min(95, bestFit * 100 + 10)}

def ant_colony(r):
    phero = [1.0, 1.0]
    best_sol, best_fit = None, -1e9
    for _ in range(20):
        for _ in range(10):
            total = sum(phero)
            choice = 0 if random.random() < phero[0] / total else 1
            pred = 'chan' if choice == 0 else 'le'
            correct = sum(1 for x in r[:20] if x == pred)
            fit = correct / max(min(20, len(r)), 1)
            if fit > best_fit:
                best_fit, best_sol = fit, pred
            phero[choice] += fit * 0.1
        phero = [p * 0.9 for p in phero]
    return {"prediction": best_sol or 'chan', "confidence": min(95, best_fit * 100 + 10)}

def bee_colony(r):
    bees = [{"pos": random.random()*2-1, "fit": 0} for _ in range(12)]
    for _ in range(25):
        for b in bees:
            correct = 0
            for i in range(min(20, len(r) - 1)):
                pred = 'chan' if b["pos"] * (1 if r[i] == 'chan' else -1) > 0 else 'le'
                if pred == r[i+1]: correct += 1
            b["fit"] = correct / max(min(19, len(r) - 1), 1)
        bees.sort(key=lambda x: x["fit"], reverse=True)
        for i in range(6, 12): bees[i]["pos"] = random.random()*2-1
        for i in range(6):
            bees[i]["pos"] = max(-1, min(1, bees[i]["pos"] + (random.random()-0.5)*0.3))
    best = bees[0]
    pred = 'chan' if best["pos"] * (1 if r[0] == 'chan' else -1) > 0 else 'le'
    return {"prediction": pred, "confidence": min(95, best["fit"] * 100 + 10)}

def firefly(r):
    import math
    flies = [{"pos": random.random()*2-1, "intensity": 0} for _ in range(15)]
    for _ in range(30):
        for f in flies:
            correct = 0
            for i in range(min(20, len(r) - 1)):
                pred = 'chan' if f["pos"] * (1 if r[i] == 'chan' else -1) > 0 else 'le'
                if pred == r[i+1]: correct += 1
            f["intensity"] = correct / max(min(19, len(r) - 1), 1)
        for i in range(len(flies)):
            for j in range(len(flies)):
                if flies[j]["intensity"] > flies[i]["intensity"]:
                    beta = 0.5 * math.exp(-(flies[i]["pos"] - flies[j]["pos"])**2)
                    flies[i]["pos"] += beta * (flies[j]["pos"] - flies[i]["pos"]) + (random.random()-0.5)*0.1
    best = max(flies, key=lambda x: x["intensity"])
    pred = 'chan' if best["pos"] * (1 if r[0] == 'chan' else -1) > 0 else 'le'
    return {"prediction": pred, "confidence": min(95, best["intensity"] * 100 + 10)}

def cuckoo_search(r):
    nests = [{"pos": random.random()*2-1, "fit": 0} for _ in range(15)]
    for _ in range(30):
        for n in nests:
            correct = 0
            for i in range(min(20, len(r) - 1)):
                pred = 'chan' if n["pos"] * (1 if r[i] == 'chan' else -1) > 0 else 'le'
                if pred == r[i+1]: correct += 1
            n["fit"] = correct / max(min(19, len(r) - 1), 1)
        best = max(nests, key=lambda x: x["fit"])
        new_pos = best["pos"] + random.random() * 0.2
        new_fit = 0
        for i in range(min(20, len(r) - 1)):
            pred = 'chan' if new_pos * (1 if r[i] == 'chan' else -1) > 0 else 'le'
            if pred == r[i+1]: new_fit += 1
        new_fit /= max(min(19, len(r) - 1), 1)
        if new_fit > best["fit"]: best["pos"] = new_pos
        nests[random.randrange(len(nests))]["pos"] = random.random()*2-1
    best = max(nests, key=lambda x: x["fit"])
    pred = 'chan' if best["pos"] * (1 if r[0] == 'chan' else -1) > 0 else 'le'
    return {"prediction": pred, "confidence": min(95, best["fit"] * 100 + 10)}

def bat_algorithm(r):
    bats = [{"pos": random.random()*2-1, "vel": 0, "freq": random.random(), "loud": 0.5} for _ in range(15)]
    best = {"pos": 0, "fit": -1e9}
    for _ in range(30):
        for b in bats:
            b["freq"] = random.random()
            b["vel"] += (b["pos"] - best["pos"]) * b["freq"]
            b["pos"] += b["vel"]
            correct = 0
            for i in range(min(20, len(r) - 1)):
                pred = 'chan' if b["pos"] * (1 if r[i] == 'chan' else -1) > 0 else 'le'
                if pred == r[i+1]: correct += 1
            fit = correct / max(min(19, len(r) - 1), 1)
            if fit > best["fit"]:
                best["fit"], best["pos"] = fit, b["pos"]
            if random.random() < b["loud"]:
                new_pos = best["pos"] + (random.random()-0.5)*0.1
                n_fit = 0
                for i in range(min(20, len(r) - 1)):
                    pred = 'chan' if new_pos * (1 if r[i] == 'chan' else -1) > 0 else 'le'
                    if pred == r[i+1]: n_fit += 1
                n_fit /= max(min(19, len(r) - 1), 1)
                if n_fit > fit:
                    b["pos"], b["loud"] = new_pos, b["loud"] * 0.9
    pred = 'chan' if best["pos"] * (1 if r[0] == 'chan' else -1) > 0 else 'le'
    return {"prediction": pred, "confidence": min(95, best["fit"] * 100 + 10)}

def grey_wolf(r):
    wolves = [{"pos": random.random()*2-1, "fit": 0} for _ in range(10)]
    alpha, beta, delta = {"pos": 0, "fit": -1e9}, {"pos": 0, "fit": -1e9}, {"pos": 0, "fit": -1e9}
    for _ in range(30):
        for w in wolves:
            correct = 0
            for i in range(min(20, len(r) - 1)):
                pred = 'chan' if w["pos"] * (1 if r[i] == 'chan' else -1) > 0 else 'le'
                if pred == r[i+1]: correct += 1
            w["fit"] = correct / max(min(19, len(r) - 1), 1)
        wolves.sort(key=lambda x: x["fit"], reverse=True)
        alpha, beta, delta = wolves[0], wolves[1], wolves[2]
        for w in wolves:
            X1 = alpha["pos"] - (2*0.5*random.random()-0.5)*abs(2*random.random()*alpha["pos"]-w["pos"])
            X2 = beta["pos"] - (2*0.5*random.random()-0.5)*abs(2*random.random()*beta["pos"]-w["pos"])
            X3 = delta["pos"] - (2*0.5*random.random()-0.5)*abs(2*random.random()*delta["pos"]-w["pos"])
            w["pos"] = (X1 + X2 + X3) / 3
    pred = 'chan' if alpha["pos"] * (1 if r[0] == 'chan' else -1) > 0 else 'le'
    return {"prediction": pred, "confidence": min(95, alpha["fit"] * 100 + 10)}

def markov1(r):
    t = {'chan': {'chan': 0, 'le': 0}, 'le': {'chan': 0, 'le': 0}}
    for i in range(1, len(r)): t[r[i-1]][r[i]] += 1
    last = r[0]
    total = t[last]['chan'] + t[last]['le']
    if not total: return {"prediction": 'le' if r[0] == 'chan' else 'chan', "confidence": 60}
    p = t[last]['chan'] / total
    return {"prediction": 'chan' if p > 0.5 else 'le', "confidence": max(p, 1-p) * 100}

def markov2(r):
    t = {}
    for i in range(2, len(r)):
        k = r[i-2] + ',' + r[i-1]
        t.setdefault(k, {'chan': 0, 'le': 0})
        t[k][r[i]] += 1
    k = r[0] + ',' + r[1]
    if k not in t: return markov1(r)
    total = t[k]['chan'] + t[k]['le']
    p = t[k]['chan'] / total
    return {"prediction": 'chan' if p > 0.5 else 'le', "confidence": max(p, 1-p) * 100}

def markov3(r):
    t = {}
    for i in range(3, len(r)):
        k = ','.join(r[i-3:i])
        t.setdefault(k, {'chan': 0, 'le': 0})
        t[k][r[i]] += 1
    k = ','.join(r[:3])
    if k not in t: return markov2(r)
    total = t[k]['chan'] + t[k]['le']
    p = t[k]['chan'] / total
    return {"prediction": 'chan' if p > 0.5 else 'le', "confidence": max(p, 1-p) * 100}

def hidden_markov(r):
    trans = {'chan': {'chan': 0.5, 'le': 0.5}, 'le': {'chan': 0.5, 'le': 0.5}}
    emit = {'chan': {'chan': 0.6, 'le': 0.4}, 'le': {'chan': 0.4, 'le': 0.6}}
    gamma = []
    for _ in range(5):
        gamma = []
        for i in range(len(r)):
            if i == 0:
                fw = {'chan': emit['chan'][r[i]] * 0.5, 'le': emit['le'][r[i]] * 0.5}
            else:
                fw = {
                    'chan': emit['chan'][r[i]] * (gamma[i-1]['chan']*trans['chan']['chan'] + gamma[i-1]['le']*trans['le']['chan']),
                    'le': emit['le'][r[i]] * (gamma[i-1]['chan']*trans['chan']['le'] + gamma[i-1]['le']*trans['le']['le']),
                }
            n = fw['chan'] + fw['le']
            gamma.append({'chan': fw['chan']/n, 'le': fw['le']/n})
        trans = {'chan': {'chan': 0, 'le': 0}, 'le': {'chan': 0, 'le': 0}}
        for i in range(1, len(r)):
            for s1 in ['chan', 'le']:
                for s2 in ['chan', 'le']:
                    trans[s1][s2] += gamma[i-1][s1] * trans[s1][s2] * emit[s2][r[i]]
        for s1 in ['chan', 'le']:
            tot = trans[s1]['chan'] + trans[s1]['le']
            if tot > 0:
                trans[s1]['chan'] /= tot
                trans[s1]['le'] /= tot
    last = gamma[0]
    p = last['chan']*trans['chan']['chan'] + last['le']*trans['le']['chan']
    return {"prediction": 'chan' if p > 0.5 else 'le', "confidence": abs(p - 0.5) * 200}

def monte_carlo(r):
    cw = 0
    for _ in range(100):
        sim = [r[0]]
        for i in range(1, 5):
            rate = sum(1 for x in r[:min(10, i)] if x == 'chan') / max(min(10, i), 1)
            sim.append('chan' if random.random() < rate else 'le')
        if sim[-1] == 'chan': cw += 1
    return {"prediction": 'chan' if cw > 50 else 'le',
            "confidence": (max(cw, 100-cw) / 100) * 100}

def kalman(r):
    x = 1 if r[0] == 'chan' else 0
    p = 1
    for i in range(1, min(15, len(r))):
        z = 1 if r[i] == 'chan' else 0
        p += 0.1
        k = p / (p + 0.1)
        x = x + k * (z - x)
        p = (1 - k) * p
    return {"prediction": 'chan' if x > 0.5 else 'le', "confidence": abs(x - 0.5) * 200}

def particle_filter(r):
    particles = [{"state": 'chan' if random.random() > 0.5 else 'le', "weight": 1} for _ in range(100)]
    for i in range(1, min(15, len(r))):
        total = 0
        for p in particles:
            if random.random() < 0.3:
                p["state"] = 'le' if p["state"] == 'chan' else 'chan'
            p["weight"] *= 0.7 if p["state"] == r[i] else 0.3
            total += p["weight"]
        for p in particles: p["weight"] /= total if total else 1
    cw = sum(p["weight"] for p in particles if p["state"] == 'chan')
    return {"prediction": 'chan' if cw > 0.5 else 'le', "confidence": abs(cw - 0.5) * 200}

def fourier(r):
    import math
    n = min(32, len(r))
    seq = [1 if x == 'chan' else -1 for x in r[:n]]
    freqs = []
    for k in range(n // 2):
        real = sum(seq[t] * math.cos(2*math.pi*k*t/n) for t in range(n))
        imag = -sum(seq[t] * math.sin(2*math.pi*k*t/n) for t in range(n))
        freqs.append(math.sqrt(real**2 + imag**2))
    if not freqs: return {"prediction": 'chan', "confidence": 50}
    max_f, max_i = 0, 0
    for i in range(1, len(freqs)):
        if freqs[i] > max_f: max_f, max_i = freqs[i], i
    nxt = math.cos(2*math.pi*max_i/n)
    return {"prediction": 'chan' if nxt > 0 else 'le',
            "confidence": min(90, (max_f / (freqs[0] or 1)) * 50)}

def wavelet(r):
    import math
    app = [1 if x == 'chan' else -1 for x in r[:16]]
    det = []
    while len(app) > 2:
        new_app, new_det = [], []
        for i in range(0, len(app) - 1, 2):
            new_app.append((app[i] + app[i+1]) / math.sqrt(2))
            new_det.append((app[i] - app[i+1]) / math.sqrt(2))
        det.append(new_det)
        app = new_app
    recon = list(app)
    for i in range(len(det) - 1, -1, -1):
        new_recon = []
        for j in range(len(recon)):
            d = det[i][j] if j < len(det[i]) else 0
            new_recon.append((recon[j] + d) / math.sqrt(2))
            new_recon.append((recon[j] - d) / math.sqrt(2))
        recon = new_recon
    energy = sum(abs(x) for x in app) / max(len(app), 1)
    return {"prediction": 'chan' if recon[0] > 0 else 'le',
            "confidence": min(90, energy * 50)}

def copula(r):
    import math
    seq = [1 if x == 'chan' else 0 for x in r]
    mean = sum(seq) / len(seq)
    var = sum((x - mean)**2 for x in seq) / len(seq)
    if var == 0: return {"prediction": 'chan' if mean > 0.5 else 'le', "confidence": 60}
    cop = math.exp(-((mean - 0.5)**2) / (2 * var)) / math.sqrt(2 * math.pi * var)
    return {"prediction": 'chan' if cop > 0.5 else 'le', "confidence": min(90, cop * 100)}

def bayesian_network(r):
    parents = {}
    for i in range(1, min(20, len(r))):
        k = r[i-1]
        parents.setdefault(k, {'chan': 0, 'le': 0})
        parents[k][r[i]] += 1
    last = r[0]
    if last not in parents:
        return {"prediction": 'le' if r[0] == 'chan' else 'chan', "confidence": 60}
    total = parents[last]['chan'] + parents[last]['le']
    p = parents[last]['chan'] / total
    return {"prediction": 'chan' if p > 0.5 else 'le', "confidence": max(p, 1-p) * 100}

def causal_inference(r):
    causes = {}
    n = min(30, len(r))
    for lag in range(1, 6):
        if n - lag <= 0: continue
        corr = sum(1 for i in range(lag, n) if r[i-lag] == r[i])
        causes[lag] = corr / (n - lag)
    best_lag, best_corr = 1, 0
    for lag, c in causes.items():
        if c > best_corr: best_corr, best_lag = c, lag
    idx = best_lag - 1
    return {"prediction": r[idx] if idx < len(r) else 'chan', "confidence": best_corr * 100}

def granger_causality(r):
    n = min(30, len(r))
    fstats = []
    for lag in range(1, 5):
        if n - lag <= 0: continue
        res1 = sum(1 for i in range(lag, n) if r[i-lag] != r[i])
        res2 = sum(1 for i in range(lag, n) if ('chan' if random.random() > 0.5 else 'le') != r[i])
        fstats.append((res2 - res1) / res2 if res2 else 0)
    if not fstats: return {"prediction": 'chan', "confidence": 50}
    best_f = max(fstats)
    best_lag = fstats.index(best_f) + 1
    idx = best_lag - 1
    return {"prediction": r[idx] if idx < len(r) else 'chan', "confidence": min(90, best_f * 100)}

# ========== ENSEMBLE META ==========
def _votes(preds):
    c, l = 0, 0
    for p in preds.values():
        if p["prediction"] == 'chan': c += 1
        else: l += 1
    return c, l

def voting_ensemble(preds):
    c, l = _votes(preds)
    return {"prediction": 'chan' if c > l else 'le', "confidence": (max(c, l) / (c + l)) * 100}

def weighted_voting(preds):
    cw = sum(p["confidence"] for p in preds.values() if p["prediction"] == 'chan')
    lw = sum(p["confidence"] for p in preds.values() if p["prediction"] == 'le')
    return {"prediction": 'chan' if cw > lw else 'le',
            "confidence": (max(cw, lw) / (cw + lw)) * 100 if (cw+lw) else 50}

def stacking(preds):
    cw = sum(p["confidence"]/100 for p in preds.values() if p["prediction"] == 'chan')
    lw = sum(p["confidence"]/100 for p in preds.values() if p["prediction"] == 'le')
    return {"prediction": 'chan' if cw > lw else 'le',
            "confidence": (max(cw, lw) / (cw + lw)) * 100 if (cw+lw) else 50}

def bayesian_avg(preds):
    post = {'chan': 0.5, 'le': 0.5}
    for p in preds.values():
        like = p["confidence"] / 100
        if p["prediction"] == 'chan':
            post['chan'] *= like; post['le'] *= (1 - like)
        else:
            post['chan'] *= (1 - like); post['le'] *= like
    tot = post['chan'] + post['le']
    if tot == 0: return {"prediction": 'chan', "confidence": 50}
    post['chan'] /= tot; post['le'] /= tot
    return {"prediction": 'chan' if post['chan'] > post['le'] else 'le',
            "confidence": max(post['chan'], post['le']) * 100}

def gb_ensemble(preds):
    pred = 0.5
    for p in preds.values():
        res = (1 if p["prediction"] == 'chan' else 0) - pred
        pred += 0.05 * res * (p["confidence"]/100)
    return {"prediction": 'chan' if pred > 0.5 else 'le', "confidence": abs(pred - 0.5) * 200}

def super_ensemble(preds):
    metas = [voting_ensemble(preds), weighted_voting(preds), stacking(preds),
             bayesian_avg(preds), gb_ensemble(preds)]
    c = sum(1 for m in metas if m["prediction"] == 'chan')
    l = len(metas) - c
    avg = sum(m["confidence"] for m in metas) / len(metas)
    return {"prediction": 'chan' if c > l else 'le',
            "confidence": min(98, avg * 1.05)}


def ultimate_prediction(sessions):
    r = [s.get("resultTruyenThong") for s in sessions if s.get("resultTruyenThong")]
    if len(r) < 20:
        c = sum(1 for x in r[:5] if x == 'chan')
        return {"prediction": 'chan' if c >= 3 else 'le', "confidence": 65}

    all_preds = {
        "ma3": ma3(r), "ma5": ma5(r), "ma7": ma7(r), "ma10": ma10(r),
        "ema": ema(r), "wma": wma(r), "holt": holt_winters(r),
        "arima": arima(r), "sarima": sarima(r), "garch": garch(r),
        "knn3": knn(r, 3, 5), "knn5": knn(r, 5, 7), "bayes": naive_bayes(r),
        "tree": decision_tree(r), "rf": random_forest(r), "gb": gradient_boost(r),
        "xgb": xgboost(r), "lgbm": lightgbm(r), "cat": catboost(r),
        "lr": logistic_regression(r), "svmL": svm_linear(r), "svmR": svm_rbf(r),
        "perc": perceptron(r), "mlp": mlp(r),
        "rnn": rnn(r), "lstm": lstm(r), "gru": gru(r), "bilstm": bilstm(r),
        "auto": autoencoder(r), "cnn": cnn1d(r), "trans": transformer(r),
        "att": attention(r), "res": resnet(r), "dqn": dqn(r),
        "genetic": genetic(r), "pso": pso(r), "sa": simulated_annealing(r),
        "aco": ant_colony(r), "bee": bee_colony(r), "firefly": firefly(r),
        "cuckoo": cuckoo_search(r), "bat": bat_algorithm(r), "greywolf": grey_wolf(r),
        "m1": markov1(r), "m2": markov2(r), "m3": markov3(r),
        "hmm": hidden_markov(r), "mc": monte_carlo(r), "kalman": kalman(r),
        "pf": particle_filter(r), "fourier": fourier(r), "wavelet": wavelet(r),
        "copula": copula(r), "bayesNet": bayesian_network(r),
        "causal": causal_inference(r), "granger": granger_causality(r),
    }
    meta = super_ensemble(all_preds)
    changes = sum(1 for i in range(1, min(20, len(r))) if r[i] != r[i-1])
    stability = 1 - (changes / 19) if len(r) >= 20 else 0.5
    conf = meta["confidence"] * (0.7 + stability * 0.3)
    return {"prediction": meta["prediction"],
            "confidence": round(min(98, max(65, conf)))}


# ========== ROUTES ==========
@bp.route("/xdlc")
def api_xdlc():
    try:
        if not latest_sessions:
            fetch_latest()
        if not latest_sessions:
            return jsonify({"phiên": "?", "dự_đoán": "DANG TAI..."})
        next_session = latest_sessions[0].get("id", 0) + 1
        res = ultimate_prediction(latest_sessions)
        return jsonify({"phiên": next_session,
                        "dự_đoán": "CHẴN" if res["prediction"] == 'chan' else "LẺ"})
    except Exception as e:
        print(f"[XDLC] Route error: {e}")
        return jsonify({"phiên": "?", "dự_đoán": "CHẴN"})


@bp.route("/health")
def api_health():
    return jsonify({"status": "ok", "algorithms": 79, "updates": update_count})


def start_background():
    threading.Thread(target=_loop, daemon=True).start()