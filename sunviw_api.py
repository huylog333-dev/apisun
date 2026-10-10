# -*- coding: utf-8 -*-
"""
SUNVIW 24 LOGICS (mặc định chạy 13 logic) - API JSON  (bản Python của SUNVIW_21logics.html + thêm L3N, L4N, L5N)

Chạy:
    pip install flask
    python sunviw_api.py                      # mặc định http://0.0.0.0:5000
    python sunviw_api.py --port 8080 --upstream https://xxx.trycloudflare.com/api/tx/history
    python sunviw_api.py --flip               # BẬT bẻ final (mặc định TẮT; hoặc SUNVIW_FLIP=1, hoặc sửa FLIP_FINAL_DEFAULT)

Endpoint:
    GET /api/predict             -> JSON dự đoán (đọc từ cache, trả về ngay)
    GET /api/predict?detail=1    -> thêm chi_tiet: vote từng logic + WR từng logic
    GET /health                  -> trạng thái nền (lần quét gần nhất, lỗi nếu có)

JSON /api/predict:
    {
      "ok": true,
      "phien": 12346,            # phiên được dự đoán (n)
      "du_doan": "TÀI",          # TÀI | XỈU  (mặc định = final của các logic đang dùng; nếu BẬT bẻ final thì = đảo ngược final)
      "be_final": false,         # trạng thái bẻ final đang áp dụng (false = tắt, mặc định)
      "do_tin_cay": 58.4,        # % = trung bình WR của các logic đang dùng trong WR_WINDOW ván gần nhất (null nếu chưa chấm ván nào)
      "phien_truoc": 12345,      # phiên mới nhất đã có kết quả (n-1)
      "xuc_xac": [3, 5, 4],      # xúc xắc của phien_truoc (dùng để tính dự đoán)
      "tong": 12,                # tổng xúc xắc của phien_truoc
      "ket_qua_truoc": "TÀI",
      "so_van_wr": 15,           # số ván thực tế đã dùng để tính WR / độ tin cậy
      "tool_dung_sai_10_van": {"dung": 6, "sai": 4, "tong": 10, "chuoi": "ĐSĐĐSĐSĐĐS"},
                                 # đúng/sai của du_doan ở 10 phiên gần nhất (theo be_final hiện tại), chuoi: mới -> cũ
      "stale": false,            # true nếu lần quét upstream gần nhất bị lỗi (đang trả kết quả cũ)
      "cap_nhat": "2026-10-09 12:30:01"
    }

/api/predict?detail=1 -> chi_tiet có thêm:
      "final_goc": "XỈU"                                     # final trước khi bẻ (luôn là final gốc của các logic đang dùng)
      "tool_dung_sai_15_van": {"dung": 9, "tong": 15}        # đúng/sai ở WR_WINDOW ván gần nhất

Logic giữ nguyên 100% so với file HTML (kể cả hành vi NaN của L1/L2/L3/LA/LB - xem ghi chú ở _hex_at).

⚙ LỌC LOGIC TRÙNG (kết quả backtest 300.000 ván: 4 dải số phiên x xúc xắc ngẫu nhiên):
    Có 5 nhóm logic dự đoán GIỐNG NHAU 100% (khớp 300.000/300.000 ván):
        L1 = L3                (do Z đọc ngoài chuỗi md5 -> NaN -> luôn TÀI)
        L2 = LA = LB           (do Z đọc ngoài chuỗi md5 -> NaN -> luôn XỈU)
        SUN1 = TX1 · SUN2 = TX2 · SUN3 = TX3   (SUN dùng đúng bộ công thức của TX)
    DEDUP_MODE = "all"       (mặc định): XÓA TOÀN BỘ logic nằm trong nhóm trùng -> còn 13 logic (10 logic cũ + L3N, L4N, L5N)
    DEDUP_MODE = "keep_one"  : mỗi nhóm trùng giữ lại 1 đại diện -> còn 18 logic
    DEDUP_MODE = "off"       : giữ nguyên toàn bộ 24 logic (21 logic cũ + L3N, L4N, L5N)
    Đổi bằng biến môi trường SUNVIW_DEDUP=all|keep_one|off hoặc sửa DEDUP_MODE_DEFAULT.
    Lưu ý: L7 và ANTI-L7 luôn NGƯỢC nhau 100% (không phải trùng) nên được giữ; hai logic này triệt tiêu nhau khi bỏ phiếu.

➕ L3N (logic mới thêm):  K = |(X + 1) ^ (Y + 1)| ÷ (Z × 5)  ·  chẵn→TÀI / lẻ→XỈU
    X = phiên % 20 · Y = MD5[6] % 20 · Z = MD5[30] % 20  (cùng kiểu LA/LB). Y, Z đọc ở ký tự hex 6 và 30 (như SUN/TX/S2)
    -> nằm TRONG chuỗi md5 32 ký tự nên KHÔNG bị NaN. Dấu ^ dùng _pow của file (cắt số mũ tối đa 8).
    Đặt tên L3N (không phải "L3") vì tên L3 đã dùng cho logic L3 cũ trong nhóm trùng, sẽ bị lọc mất.

➕ L4N (logic mới thêm):  K = |(X + 10) mod (Y ÷ 6)| ^ (Z ÷ 4)  ·  chẵn→XỈU / lẻ→TÀI
➕ L5N (logic mới thêm):  K = |(X + 3) × (Y ÷ 4)| − (Z ÷ 5)     ·  chẵn→XỈU / lẻ→TÀI
    Cùng quy ước với L3N: X = phiên % 20 · Y = MD5[6] % 20 · Z = MD5[30] % 20 (hex ký tự 6 và 30, không NaN).
    mod dùng _mod của file (chia cho 0 -> 0) · dấu ^ dùng _pow của file (cắt số mũ tối đa 8) · làm tròn kiểu Math.round của JS.
Server quét upstream nền mỗi POLL_SEC giây, chỉ tính lại khi có phiên mới -> request của HTML trả về tức thì.
"""
import argparse
import hashlib
import json
import math
import os
import re
import sys
import threading
import time
import unicodedata
import urllib.request

# ─── CẤU HÌNH ────────────────────────────────────────────────────────────
UPSTREAM_URL = os.environ.get(
    "SUNVIW_UPSTREAM",
    "https://reviewed-ssl-tradition-specialized.trycloudflare.com/api/tx/history",
)
UPSTREAM_TIMEOUT = 15      # giây
POLL_SEC = 3.0             # chu kỳ quét upstream (giống AUTO_INTERVAL_MS của HTML)
WR_WINDOW = 32             # số ván gần nhất dùng để tính WR
WR_MIN_GAMES = 1           # số ván đã chấm tối thiểu để dùng WR (dưới mức này -> đa số 21 logic)

# ═══════════════════════════════════════════════════════════════════════════
#  ⚙  CONFIG BẺ FINAL  (bật / tắt)  —  CHỈNH Ở ĐÂY
# ═══════════════════════════════════════════════════════════════════════════
#   FLIP_FINAL_DEFAULT = False  ->  TẮT (mặc định): du_doan = final của 21 logic, KHÔNG bẻ
#   FLIP_FINAL_DEFAULT = True   ->  BẬT : du_doan = đảo ngược final (TÀI <-> XỈU)
#
#  Muốn đổi mà không sửa file (ưu tiên: cờ dòng lệnh > biến môi trường > FLIP_FINAL_DEFAULT):
#     biến môi trường :  SUNVIW_FLIP=1  (bật)  |  SUNVIW_FLIP=0  (tắt)
#     dòng lệnh       :  python sunviw_api.py --flip      (bật)
#                        python sunviw_api.py --no-flip   (tắt)
FLIP_FINAL_DEFAULT = False


def _env_bool(name, default):
    """Đọc biến môi trường dạng bật/tắt; không đặt hoặc giá trị lạ -> dùng `default`."""
    v = os.environ.get(name, "").strip().lower()
    if v in ("1", "true", "yes", "on"):
        return True
    if v in ("0", "false", "no", "off"):
        return False
    return default


FLIP_FINAL = _env_bool("SUNVIW_FLIP", FLIP_FINAL_DEFAULT)

# ─── ĐÁNH GIÁ ĐÚNG/SAI ───────────────────────────────────────────────────
EVAL_WINDOW = 100           # số phiên gần nhất để đánh giá đúng/sai (hiện thẳng trong /api/predict)

# ─── PERSISTENCE (lưu graded để Railway không mất sau restart) ───────────
PERSIST_PATH = os.environ.get("SUNVIW_PERSIST", "/tmp/sunviw_graded.json")
PERSIST_KEEP = 50          # giữ tối đa N graded entry trong file (>= WR_WINDOW đủ dùng)

TAI, XIU = "TÀI", "XỈU"
NAN = float("nan")
ALL_LOGIC_NAMES = ['L1', 'L2', 'L3', 'TTA2', 'TTA4', 'TTA5', 'L7', 'LLOW1', 'LLOW2', 'ANTI-L7',
                   'SUN1', 'SUN2', 'SUN3', 'S2A', 'S2B', 'S2C', 'TX1', 'TX2', 'TX3', 'LA', 'LB', 'L3N', 'L4N', 'L5N']

# ─── LỌC LOGIC TRÙNG (từ backtest: khớp 100% trên mọi ván) ───────────────
DUP_GROUPS = [['L1', 'L3'], ['L2', 'LA', 'LB'], ['SUN1', 'TX1'], ['SUN2', 'TX2'], ['SUN3', 'TX3']]
DEDUP_MODE_DEFAULT = "all"     # "all" = xóa hết logic trong nhóm trùng · "keep_one" = giữ 1 đại diện/nhóm · "off" = giữ hết 24
DEDUP_MODE = os.environ.get("SUNVIW_DEDUP", DEDUP_MODE_DEFAULT).strip().lower()
if DEDUP_MODE not in ("all", "keep_one", "off"):
    DEDUP_MODE = DEDUP_MODE_DEFAULT


def _keep_indices(mode):
    """Chỉ số (trong ALL_LOGIC_NAMES) của các logic được giữ lại theo `mode`."""
    in_dup = {n for g in DUP_GROUPS for n in g}
    reps = {g[0] for g in DUP_GROUPS}
    out = []
    for i, n in enumerate(ALL_LOGIC_NAMES):
        if mode == "off" or n not in in_dup or (mode == "keep_one" and n in reps):
            out.append(i)
    return out


KEEP_IDX = _keep_indices(DEDUP_MODE)
LOGIC_NAMES = [ALL_LOGIC_NAMES[i] for i in KEEP_IDX]          # danh sách logic ĐANG DÙNG
LOGIC_SIG = ",".join(LOGIC_NAMES)                              # dấu vân tay bộ logic (để bỏ dữ liệu persist cũ lệch bộ)


# ─── HELPERS (mô phỏng đúng ngữ nghĩa JavaScript) ────────────────────────
def _js_round(x):
    """Math.round của JS (làm tròn .5 lên)."""
    if math.isnan(x) or math.isinf(x):
        return x
    r = math.floor(x)
    return r + 1 if x - r >= 0.5 else r


def _hex_at(md5, i):
    """parseInt(md5.substring(i, i+2), 16).
    LƯU Ý: md5 hex chỉ dài 32 ký tự. L1/L2/L3/LA/LB trong file HTML đọc Z ở vị trí 60 (ngoài chuỗi)
    -> substring rỗng -> parseInt = NaN. Giữ nguyên hành vi đó để kết quả khớp HTML."""
    s = md5[i:i + 2]
    try:
        return int(s, 16)
    except ValueError:
        return NAN


def _pow(a, b):
    a, b = abs(a), abs(b)
    if math.isnan(a) or math.isnan(b):
        return NAN
    b = min(b, 8)
    try:
        return math.pow(a, b)
    except OverflowError:
        return math.inf
    except ValueError:
        return NAN


def _mod(a, b):
    if b == 0:
        return 0
    try:
        return math.fmod(a, b)
    except ValueError:
        return NAN


OPS = {
    '+': lambda a, b: a + b,
    '-': lambda a, b: a - b,
    '*': lambda a, b: a * b,
    '/': lambda a, b: 0 if b == 0 else a / b,
    '%': _mod,
    '^': _pow,
    'diff': lambda a, b: abs(a - b),
    'min': lambda a, b: NAN if (math.isnan(a) or math.isnan(b)) else min(a, b),
}


def sum_digits(s):
    return sum(int(c) for c in str(s) if c.isdigit())


def last3_sum(s):
    d = [int(c) for c in str(s) if c.isdigit()]
    return sum(d[-3:])


def xor_digits(s):
    r = 0
    for c in str(s):
        if c.isdigit():
            r ^= int(c)
    return r


def last1_digit(s):
    d = [int(c) for c in str(s) if c.isdigit()]
    return d[-1] if d else 0


def actual_of(total):
    return TAI if total >= 11 else XIU


def flip_pred(p):
    """Bẻ: đảo TÀI <-> XỈU (giá trị khác giữ nguyên)."""
    return XIU if p == TAI else TAI if p == XIU else p


def out_final(final):
    """Final đã đưa ra API (sau bẻ nếu bật)."""
    return flip_pred(final) if FLIP_FINAL else final


def vote_result(preds):
    tai = sum(1 for x in preds if x == TAI)
    xiu = sum(1 for x in preds if x == XIU)
    if tai == xiu:
        return 'SKIP'
    return TAI if tai > xiu else XIU


# ─── CÔNG THỨC MD5: L1/L2/L3 · SUN · S2 · TX ─────────────────────────────
FORMULAS = [
    {"w1": 2, "w2": 8, "w3": 14, "inX": "/", "inY": "/", "inZ": "-", "op1": "diff", "op2": "-", "flip": True, "posY": 6, "posZ": 30},
    {"w1": 13, "w2": 4, "w3": 5, "inX": "-", "inY": "/", "inZ": "/", "op1": "*", "op2": "-", "flip": False, "posY": 6, "posZ": 30},
    {"w1": 15, "w2": 15, "w3": 15, "inX": "/", "inY": "/", "inZ": "/", "op1": "+", "op2": "+", "flip": True, "posY": 6, "posZ": 30},
]
S2_FORMULAS = [
    {"w1": 8, "w2": 13, "w3": 12, "inX": "-", "inY": "*", "inZ": "/", "op1": "+", "op2": "%", "flip": True, "posY": 6, "posZ": 30},
    {"w1": 6, "w2": 3, "w3": 8, "inX": "*", "inY": "/", "inZ": "+", "op1": "+", "op2": "%", "flip": True, "posY": 6, "posZ": 30},
    {"w1": 13, "w2": 6, "w3": 15, "inX": "+", "inY": "*", "inZ": "/", "op1": "-", "op2": "*", "flip": True, "posY": 6, "posZ": 30},
]
TX_FORMULAS = [
    {"w1": 11, "w2": 7, "w3": 12, "inX": "-", "inY": "/", "inZ": "-", "op1": "^", "op2": "/", "flip": True, "posY": 6, "posZ": 30},
    {"w1": 6, "w2": 3, "w3": 13, "inX": "*", "inY": "-", "inZ": "*", "op1": "^", "op2": "%", "flip": True, "posY": 6, "posZ": 30},
    {"w1": 9, "w2": 13, "w3": 12, "inX": "-", "inY": "*", "inZ": "/", "op1": "+", "op2": "%", "flip": False, "posY": 6, "posZ": 30},
]
SUN_FORMULAS = TX_FORMULAS  # SUN1-3 dùng đúng bộ công thức của TX1-3 (giống file HTML)


def md5_of(session, d1, d2, d3):
    raw = f"{session}-{d1}-{d2}-{d3}-{d1 + d2 + d3}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def _run_formulas(formulas, md5, X, pos_scale):
    out = []
    for F in formulas:
        Y = _hex_at(md5, F["posY"] * pos_scale)
        Z = _hex_at(md5, F["posZ"] * pos_scale)
        a = OPS[F["inX"]](X, F["w1"])
        b = OPS[F["inY"]](Y, F["w2"])
        c = OPS[F["inZ"]](Z, F["w3"])
        mid = OPS[F["op1"]](a, b)
        kraw = OPS[F["op2"]](mid, c)
        K = 0 if (math.isnan(kraw) or math.isinf(kraw)) else math.floor(abs(kraw))
        even = (K % 2 == 0)
        pred = (TAI if even else XIU) if F["flip"] else (XIU if even else TAI)
        out.append(pred)
    return out


# ─── CÁC LOGIC THEO PHIÊN ────────────────────────────────────────────────
def _tta(sess, m_sd, m_l3, m_xd, m_l1, mod, add=3):
    return (sum_digits(sess) * m_sd + last3_sum(sess) * m_l3 +
            xor_digits(sess) * m_xd + last1_digit(sess) * m_l1) % mod + add


def calc_la(md5, session):
    Xs = int(session) % 20
    Y = _hex_at(md5, 12) % 20
    Z = _hex_at(md5, 60) % 20 if not math.isnan(_hex_at(md5, 60)) else NAN
    step1 = min(Xs + 3, 0 if Y == 0 else Y / 3)
    step2 = abs(step1 - Xs)
    K = step2 * (0 if Z == 0 else Z / 2)
    return TAI if _js_round(abs(K)) % 2 == 0 else XIU


def calc_lb(md5, session):
    Xs = int(session) % 20
    Y = _hex_at(md5, 12) % 20
    Z = _hex_at(md5, 60) % 20 if not math.isnan(_hex_at(md5, 60)) else NAN
    denom = Y - 3
    step1 = 0 if denom == 0 else (Xs - 5) / denom
    K = abs(step1) * (0 if Z == 0 else Z / 3)
    return TAI if _js_round(abs(K)) % 2 == 0 else XIU


def calc_l3n(md5, session):
    """L3N: K = |(X + 1) ^ (Y + 1)| ÷ (Z × 5) · chẵn→TÀI / lẻ→XỈU.
    X = phiên % 20 · Y = MD5[6] % 20 · Z = MD5[30] % 20 (cùng kiểu LA/LB).
    Y, Z đọc ở ký tự hex 6 và 30 -> nằm trong chuỗi md5 32 ký tự nên không bị NaN như LA/LB."""
    Xs = int(session) % 20
    Y = _hex_at(md5, 6) % 20
    Z = _hex_at(md5, 30) % 20
    num = _pow(Xs + 1, Y + 1)
    den = Z * 5
    K = 0 if den == 0 else num / den
    return TAI if _js_round(abs(K)) % 2 == 0 else XIU


def calc_l4n(md5, session):
    """L4N: K = |(X + 10) mod (Y ÷ 6)| ^ (Z ÷ 4) · chẵn→XỈU / lẻ→TÀI.
    X = phiên % 20 · Y = MD5[6] % 20 · Z = MD5[30] % 20 (cùng quy ước L3N)."""
    Xs = int(session) % 20
    Y = _hex_at(md5, 6) % 20
    Z = _hex_at(md5, 30) % 20
    m = _mod(Xs + 10, Y / 6)
    K = _pow(abs(m), Z / 4)
    return XIU if _js_round(abs(K)) % 2 == 0 else TAI


def calc_l5n(md5, session):
    """L5N: K = |(X + 3) × (Y ÷ 4)| − (Z ÷ 5) · chẵn→XỈU / lẻ→TÀI.
    X = phiên % 20 · Y = MD5[6] % 20 · Z = MD5[30] % 20 (cùng quy ước L3N). K có thể âm -> chỉ xét chẵn/lẻ."""
    Xs = int(session) % 20
    Y = _hex_at(md5, 6) % 20
    Z = _hex_at(md5, 30) % 20
    K = abs((Xs + 3) * (Y / 4)) - (Z / 5)
    return XIU if _js_round(K) % 2 == 0 else TAI


def compute_all(session, d1, d2, d3):
    """Vote của các logic ĐANG DÙNG (đã lọc trùng) cho phiên `session`. Thứ tự = LOGIC_NAMES."""
    full = compute_all_full(session, d1, d2, d3)
    return [full[i] for i in KEEP_IDX]


def compute_all_full(session, d1, d2, d3):
    """Đủ 24 vote (21 logic cũ + L3N, L4N, L5N) cho phiên `session` từ xúc xắc (d1,d2,d3) của phiên liền trước. Thứ tự = ALL_LOGIC_NAMES."""
    md5 = md5_of(session, d1, d2, d3)
    X = sum_digits(session)
    l123 = _run_formulas(FORMULAS, md5, X, 2)          # L1 L2 L3 (vị trí hex ×2 như HTML)
    tta2 = TAI if _tta(session, 2, 13, 2, 3, 15) % 2 == 0 else XIU
    tta4 = TAI if _tta(session, 7, 11, 3, 4, 17) % 2 == 0 else XIU
    tta5 = XIU if _tta(session, 8, 13, 2, 3, 21) % 2 == 0 else TAI
    k7 = (sum_digits(session) * 18 + last3_sum(session) * 13) % 15
    l7 = TAI if k7 % 2 == 0 else XIU
    llow1 = TAI if _tta(session, 5, 5, 5, 4, 17) % 2 == 0 else XIU
    llow2 = TAI if _tta(session, 2, 11, 6, 4, 19) % 2 == 0 else XIU
    anti_l7 = XIU if k7 % 2 == 0 else TAI
    sun = _run_formulas(SUN_FORMULAS, md5, X, 1)
    s2 = _run_formulas(S2_FORMULAS, md5, X, 1)
    tx = _run_formulas(TX_FORMULAS, md5, X, 1)
    la = calc_la(md5, session)
    lb = calc_lb(md5, session)
    l3n = calc_l3n(md5, session)
    l4n = calc_l4n(md5, session)
    l5n = calc_l5n(md5, session)
    return l123 + [tta2, tta4, tta5, l7, llow1, llow2, anti_l7] + sun + s2 + tx + [la, lb, l3n, l4n, l5n]


# ─── WR · QUYẾT ĐỊNH CUỐI · ĐỘ TIN CẬY ───────────────────────────────────
def wr_decision(votes, graded):
    """Giống wrDecision() trong HTML + thêm avg (độ tin cậy = TB WR của các logic đang dùng, 0-100)."""
    all_vote = vote_result(votes)
    win = graded[-WR_WINDOW:]
    n = len(win)
    if n < WR_MIN_GAMES:
        return {"mode": "ALL", "n": n, "final": all_vote, "wins": [], "low": [], "high": [],
                "gT": 0, "gX": 0, "tie": False, "avg": None}
    wins = [sum(1 for g in win if g["votes"][i] == g["actual"]) for i in range(len(votes))]
    low, high = [], []
    for i, w in enumerate(wins):
        (low if w * 2 < n else high).append(i)       # WR <50% -> thấp · WR ≥50% -> cao
    use_low = len(low) > len(high)
    idx = low if use_low else high
    gv = [votes[i] for i in idx]
    gT = sum(1 for x in gv if x == TAI)
    gX = len(gv) - gT
    final, tie = vote_result(gv), False
    if final == 'SKIP':
        final, tie = all_vote, True
    avg = sum(wins) / (len(wins) * n) * 100
    return {"mode": "LOW" if use_low else "HIGH", "n": n, "final": final, "wins": wins,
            "low": low, "high": high, "gT": gT, "gX": gX, "tie": tie, "avg": avg}


# ─── LỊCH SỬ UPSTREAM ────────────────────────────────────────────────────
def _parse_int(v):
    m = re.match(r"\s*[+-]?\d+", str(v))
    return int(m.group()) if m else None


def norm_kq(s):
    t = unicodedata.normalize("NFD", str(s or ""))
    t = "".join(ch for ch in t if unicodedata.category(ch) != "Mn").lower()
    if "tai" in t:
        return TAI
    if "xiu" in t:
        return XIU
    return None


def parse_history(data):
    if isinstance(data, list):
        arr = data
    elif isinstance(data, dict) and isinstance(data.get("history"), list):
        arr = data["history"]
    else:
        arr = []
    m = {}
    for r in arr:
        if not isinstance(r, dict):
            continue
        phien = _parse_int(r.get("phien"))
        d1 = _parse_int(r.get("xuc_xac_1"))
        d2 = _parse_int(r.get("xuc_xac_2"))
        d3 = _parse_int(r.get("xuc_xac_3"))
        if None in (phien, d1, d2, d3):
            continue
        if any(d < 1 or d > 6 for d in (d1, d2, d3)):
            continue
        total = d1 + d2 + d3
        m[phien] = {"phien": phien, "d1": d1, "d2": d2, "d3": d3, "total": total,
                    "actual": norm_kq(r.get("ket_qua")) or actual_of(total),
                    "time": r.get("thoi_gian") or ""}
    return [m[k] for k in sorted(m)]            # cũ -> mới


def persist_load():
    """Load danh sách graded đã lưu từ file JSON. Trả về [] nếu không có / lỗi."""
    try:
        with open(PERSIST_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            # bỏ entry lưu từ bộ logic khác (vd. file cũ 21 logic) -> tránh lệch chỉ số vote
            return [g for g in data if isinstance(g, dict) and g.get("sig") == LOGIC_SIG]
    except Exception:  # noqa: BLE001
        pass
    return []


def persist_save(graded):
    """Ghi tối đa PERSIST_KEEP entry cuối vào file JSON (atomic write)."""
    try:
        chunk = graded[-PERSIST_KEEP:]
        tmp = PERSIST_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(chunk, f, ensure_ascii=False)
        os.replace(tmp, PERSIST_PATH)
    except Exception:  # noqa: BLE001
        pass


def merge_graded(saved, fresh):
    """Ghép saved (từ file) + fresh (rebuild từ hist hiện tại), dedup + sort theo session.
    fresh luôn được ưu tiên (overwrite saved nếu trùng session)."""
    by_sess = {g["session"]: g for g in saved}
    for g in fresh:
        by_sess[g["session"]] = g
    return [by_sess[k] for k in sorted(by_sess)]


def rebuild_graded(hist, saved_graded=None):
    """Chấm lại toàn bộ lịch sử (giống rebuildGraded): dự đoán phiên k+1 từ xúc xắc phiên k, chấm bằng kết quả thật.
    Nếu có saved_graded, merge vào để WR_WINDOW có đủ 15 ván dù upstream trả ít ván."""
    fresh = []
    # Dùng saved làm seed cho wr_decision trong quá trình rebuild
    seed = list(saved_graded) if saved_graded else []
    for i in range(len(hist) - 1):
        cur, nxt = hist[i], hist[i + 1]
        if nxt["phien"] != cur["phien"] + 1:
            continue
        votes = compute_all(cur["phien"] + 1, cur["d1"], cur["d2"], cur["d3"])
        # Chỉ dùng các ván đã chấm TRƯỚC phiên nxt (seed có thể chứa ván mới hơn -> nhìn trước đáp án, làm lệch đánh giá)
        combined = [g for g in merge_graded(seed, fresh) if g["session"] < nxt["phien"]]
        dec = wr_decision(votes, combined)
        fresh.append({"session": nxt["phien"], "total": nxt["total"], "actual": nxt["actual"],
                      "votes": votes, "final": dec["final"], "ok": dec["final"] == nxt["actual"],
                      "sig": LOGIC_SIG})
    return merge_graded(seed, fresh)


def build_result(hist):
    """Từ lịch sử (cũ -> mới) -> dict kết quả dự đoán cho phiên kế tiếp."""
    latest = hist[-1]
    saved = persist_load()
    graded = rebuild_graded(hist, saved_graded=saved)
    persist_save(graded)
    votes = compute_all(latest["phien"] + 1, latest["d1"], latest["d2"], latest["d3"])
    dec = wr_decision(votes, graded)
    base = {
        "ok": True,
        "phien": latest["phien"] + 1,
        "du_doan": out_final(dec["final"]),
        "be_final": FLIP_FINAL,
        "do_tin_cay": None if dec["avg"] is None else round(dec["avg"], 1),
        "phien_truoc": latest["phien"],
        "xuc_xac": [latest["d1"], latest["d2"], latest["d3"]],
        "tong": latest["total"],
        "ket_qua_truoc": latest["actual"],
        "so_van_wr": dec["n"],
        "tool_dung_sai_10_van": _recent_accuracy(graded, EVAL_WINDOW, with_chuoi=True),
    }
    tai = sum(1 for v in votes if v == TAI)
    detail = {
        "vote_21": {"TÀI": tai, "XỈU": len(votes) - tai},        # tên khóa giữ nguyên cho tương thích; giờ đếm trên các logic đang dùng
        "so_logic": len(votes),
        "che_do_loc_trung": DEDUP_MODE,
        "logic_bi_loai": [n for n in ALL_LOGIC_NAMES if n not in LOGIC_NAMES],
        "nhom_theo": {"ALL": "da so", "LOW": "WR thap", "HIGH": "WR cao"}[dec["mode"]],
        "nhom_tai_xiu": {"TÀI": dec["gT"], "XỈU": dec["gX"]},
        "hoa_dung_da_so_21": dec["tie"],
        "logic": [
            {"ten": LOGIC_NAMES[i], "du_doan": votes[i],
             "wr": (round(dec["wins"][i] / dec["n"] * 100, 1) if dec["wins"] else None),
             "nhom": (None if not dec["wins"] else ("THAP" if i in dec["low"] else "CAO"))}
            for i in range(len(votes))
        ],
        "final_goc": dec["final"],
        "tool_dung_sai_15_van": _recent_accuracy(graded, WR_WINDOW),
    }
    return {"base": base, "detail": detail}


def _recent_accuracy(graded, size, with_chuoi=False):
    """Đúng/sai của final ĐÃ ĐƯA RA API (sau bẻ nếu đang bật) ở `size` ván gần nhất."""
    win = graded[-size:]
    oks = [out_final(g["final"]) == g["actual"] for g in win]
    out = {"dung": sum(oks), "tong": len(win)}
    if with_chuoi:
        out = {"dung": out["dung"], "sai": len(win) - out["dung"], "tong": len(win),
               "chuoi": "".join("Đ" if ok else "S" for ok in reversed(oks))}     # mới -> cũ
    return out


# ─── TRẠNG THÁI NỀN + QUÉT UPSTREAM ──────────────────────────────────────
_state = {"result": None, "latest": None, "error": None, "updated": None, "checked": None, "polls": 0}
_state_lock = threading.Lock()
_refresh_lock = threading.Lock()
_poller_started = False


def _fetch_json(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; SUNVIW-API/1.0)",
        "Accept": "application/json",
        "Cache-Control": "no-cache",
    })
    with urllib.request.urlopen(req, timeout=UPSTREAM_TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))


def _now():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def refresh():
    """Lấy upstream; chỉ tính lại khi có phiên mới. Ném exception nếu lỗi (poller sẽ ghi lại)."""
    with _refresh_lock:
        hist = parse_history(_fetch_json(UPSTREAM_URL))
        if not hist:
            raise ValueError("upstream khong co phien hop le (can phien + xuc_xac_1..3)")
        latest = hist[-1]["phien"]
        with _state_lock:
            same = _state["result"] is not None and _state["latest"] == latest
        if same:
            with _state_lock:
                _state["error"] = None
                _state["checked"] = _now()
            return
        res = build_result(hist)
        with _state_lock:
            _state.update(result=res, latest=latest, error=None, updated=_now(), checked=_now())


def _poll_loop():
    while True:
        try:
            refresh()
        except Exception as e:  # noqa: BLE001 - giữ poller sống dù upstream lỗi
            with _state_lock:
                _state["error"] = f"{type(e).__name__}: {e}"
                _state["checked"] = _now()
        with _state_lock:
            _state["polls"] += 1
        time.sleep(POLL_SEC)


def ensure_poller():
    global _poller_started
    if _poller_started:
        return
    _poller_started = True
    threading.Thread(target=_poll_loop, daemon=True, name="sunviw-poller").start()


# ─── FLASK ────────────────────────────────────────────────────────────────
from flask import Flask, Response, request  # noqa: E402

app = Flask(__name__)


def _json(obj, status=200):
    return Response(json.dumps(obj, ensure_ascii=False), status=status,
                    content_type="application/json; charset=utf-8")


@app.after_request
def _cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "*"
    resp.headers["Access-Control-Allow-Private-Network"] = "true"
    resp.headers["Cache-Control"] = "no-store"
    return resp


@app.route("/api/predict")
def api_predict():
    ensure_poller()
    with _state_lock:
        have = _state["result"] is not None
    if not have:                                  # request đầu tiên, poller chưa kịp quét xong
        try:
            refresh()
        except Exception as e:  # noqa: BLE001
            with _state_lock:
                _state["error"] = f"{type(e).__name__}: {e}"
    with _state_lock:
        res, err, upd = _state["result"], _state["error"], _state["updated"]
    if res is None:
        return _json({"ok": False, "loi": err or "chua co du lieu"}, 503)
    out = dict(res["base"])
    out["stale"] = bool(err)
    if err:
        out["loi"] = err
    out["cap_nhat"] = upd
    if request.args.get("detail") in ("1", "true", "yes"):
        out["chi_tiet"] = res["detail"]
    return _json(out)


@app.route("/health")
def health():
    ensure_poller()
    with _state_lock:
        s = {k: _state[k] for k in ("latest", "error", "updated", "checked", "polls")}
    s.update(ok=s["error"] is None and s["latest"] is not None, upstream=UPSTREAM_URL,
             poll_sec=POLL_SEC, wr_window=WR_WINDOW, be_final=FLIP_FINAL)
    return _json(s)


@app.route("/")
def index():
    return _json({"api": f"SUNVIW {len(LOGIC_NAMES)} logics (dedup={DEDUP_MODE})", "endpoints": ["/api/predict", "/api/predict?detail=1", "/health"]})


# Chạy dưới gunicorn (Railway) thì main() không được gọi -> bật poller ngay khi import.
if __name__ != "__main__":
    ensure_poller()


def main():
    global UPSTREAM_URL, POLL_SEC, FLIP_FINAL
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(description="SUNVIW 24 logics (mặc định 13) - API JSON")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=int(os.environ.get("PORT", 5000)))
    ap.add_argument("--upstream", default=UPSTREAM_URL, help="URL API lich su (…/api/tx/history)")
    ap.add_argument("--poll", type=float, default=POLL_SEC, help="chu ky quet upstream (giay)")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--flip", action="store_true", help="BẬT bẻ final (đảo TÀI<->XỈU)")
    g.add_argument("--no-flip", action="store_true", help="TẮT bẻ final (giữ nguyên final của các logic đang dùng)")
    a = ap.parse_args()
    UPSTREAM_URL, POLL_SEC = a.upstream, a.poll
    if a.flip:
        FLIP_FINAL = True
    elif a.no_flip:
        FLIP_FINAL = False
    ensure_poller()
    print(f"SUNVIW API  ->  http://{a.host}:{a.port}/api/predict")
    print(f"upstream    ->  {UPSTREAM_URL}")
    print(f"be final    ->  {'BAT' if FLIP_FINAL else 'TAT'}")
    app.run(host=a.host, port=a.port, threaded=True)


if __name__ == "__main__":
    main()
