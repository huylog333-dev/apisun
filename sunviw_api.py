# -*- coding: utf-8 -*-
"""
SUNVIW 24 LOGICS (mặc định chạy 13 logic) - API JSON  (bản Python của SUNVIW_21logics.html + thêm L3N, L4N, L5N)

Chạy:
    pip install flask
    python sunviw_api.py                      # mặc định http://0.0.0.0:5000
    python sunviw_api.py --port 8080 --upstream https://xxx.trycloudflare.com/api/tx
    python sunviw_api.py --flip               # BẬT bẻ final của SUN (mặc định TẮT; hoặc SUNVIW_FLIP=1, hoặc sửa FLIP_FINAL_DEFAULT)
    python sunviw_api.py --lc-flip            # BẬT bẻ final của LC79 (RIÊNG, không liên quan Sun; --lc-no-flip = tắt; hoặc LC79_FLIP=1|0, hoặc sửa LC_FLIP_FINAL_DEFAULT)

Endpoint:
    GET /api/predictsun          -> [SUN] JSON dự đoán (đọc từ cache, trả về ngay). /api/predict = tên cũ, giữ để tool cũ không hỏng
    GET /api/predictsun?detail=1 -> thêm chi_tiet: vote từng logic + WR từng logic
    GET /api/predictlc79         -> [LC79] JSON dự đoán, config RIÊNG (xem "CONFIG LC79"); cũng có ?detail=1
    ...?hist=N                   -> (cả 2 game) thêm lich_su: N ván đúng/sai gần nhất, mới -> cũ
    GET /api/html                -> panel HTML theo dõi cả 2 game, đổi qua lại, chọn số ván lịch sử
    GET /health                  -> trạng thái nền của cả 2 game

JSON /api/predict:
    {
      "ok": true,
      "phien": 12346,            # phiên được dự đoán (n)
      "du_doan": "TÀI",          # TÀI | XỈU  (mặc định = final của các logic đang dùng; nếu BẬT bẻ final thì = đảo ngược final)
      "be_final": false,         # trạng thái bẻ final đang áp dụng (false = tắt, mặc định)
      "do_tin_cay": 58.4,        # % = trung bình WR CÓ TRỌNG SỐ của các logic đang dùng trong WR_WINDOW ván gần nhất (null nếu chưa chấm ván nào)
                                 #     trọng số: ván mới nhất = WR_WEIGHT_NEWEST (cao nhất), ván cũ giảm dần nhưng có sàn WR_FLOOR (xem "CONFIG WR CÓ TRỌNG SỐ")
      "phien_truoc": 12345,      # phiên mới nhất đã có kết quả (n-1)
      "xuc_xac": [3, 5, 4],      # xúc xắc của phien_truoc (dùng để tính dự đoán)
      "tong": 12,                # tổng xúc xắc của phien_truoc
      "ket_qua_truoc": "TÀI",
      "so_van_wr": 9,            # số ván thực tế đã dùng để tính WR / độ tin cậy
      "tool_dung_sai_10_van": {"dung": 6, "sai": 4, "tong": 10, "chuoi": "✅❌✅✅❌✅❌✅✅❌"},
                                 # đúng/sai của du_doan ở 10 phiên gần nhất (theo be_final hiện tại), chuoi: mới -> cũ, ✅ = đúng · ❌ = sai (đổi icon ở ICON_DUNG / ICON_SAI)
      "stale": false,            # true nếu lần quét upstream gần nhất bị lỗi (đang trả kết quả cũ)
      "cap_nhat": "2026-10-09 12:30:01"
    }

/api/predict?detail=1 -> chi_tiet có thêm:
      "final_goc": "XỈU"                                     # final trước khi bẻ (luôn là final gốc của các logic đang dùng)
      "tool_dung_sai_15_van": {"dung": 5, "tong": 9}         # đúng/sai ở WR_WINDOW ván gần nhất (tên khóa giữ nguyên cho tương thích)
      "trong_so_wr": {...}                                   # số ván xét + bảng trọng số (cũ nhất -> mới nhất) đang áp dụng

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
from fractions import Fraction

# ─── CẤU HÌNH ────────────────────────────────────────────────────────────
# Upstream MỚI: /api/tx chỉ trả 1 PHIÊN MỚI NHẤT dạng 1 object:
#   {"ket_qua":"Tài","phien":3284075,"thoi_gian":"11-10-2026 13:50:38 UTC+7","tong":15,"xuc_xac_1":6,"xuc_xac_2":3,"xuc_xac_3":6}
# -> tool quét 1 phiên gần nhất mỗi lần, tự tích lũy vào lịch sử (HIST_PATH) để phần WR vẫn có ván để chấm.
UPSTREAM_URL = os.environ.get(
    "SUNVIW_UPSTREAM",
    "https://interstate-competent-shortly-cigarette.trycloudflare.com/api/tx",
)
UPSTREAM_TIMEOUT = 9      # giây
HIST_PATH = os.environ.get("SUNVIW_HIST", "/tmp/sunviw_hist.json")   # lịch sử các phiên đã quét (tool tự tích lũy)
HIST_KEEP = 300            # giữ tối đa N phiên gần nhất trong lịch sử (>= WR_WINDOW + EVAL_WINDOW là đủ)
POLL_SEC = 3.0             # chu kỳ quét upstream (giống AUTO_INTERVAL_MS của HTML)
WR_MIN_GAMES = 1           # số ván đã chấm tối thiểu để dùng WR (dưới mức này -> đa số 21 logic)

# ═══════════════════════════════════════════════════════════════════════════
#  ⚙  CONFIG WR CÓ TRỌNG SỐ (KIỂU "PHẢN ỨNG NHANH + SÀN NHỚ CẦU CŨ")  —  CHỈNH Ở ĐÂY
# ═══════════════════════════════════════════════════════════════════════════
#   Ván MỚI NHẤT có trọng số = WR_WEIGHT_NEWEST (cao nhất). Ván càng cũ trọng số càng giảm theo hàm mũ NHƯNG không bao giờ
#   thấp hơn WR_FLOOR  ->  cầu mới đổi thì phản ứng nhanh (các ván mới chiếm phần lớn quyền), còn cầu cũ vẫn giữ
#   một phần quyền (không bị quên hẳn).
#
#       trọng số(ván tuổi a) = WR_FLOOR + (WR_WEIGHT_NEWEST - WR_FLOOR) * WR_DECAY ** a        (a = 0 là ván mới nhất -> đúng = WR_WEIGHT_NEWEST)
#
#   WR_WINDOW = số ván gần nhất được xét để tính WR
#   WR_DECAY  = tốc độ quên (0.75 = mỗi ván cũ hơn, phần "thưởng mới" giảm còn 75%). Nhỏ hơn -> phản ứng nhanh hơn.
#   WR_WEIGHT_NEWEST = trọng số của ván MỚI NHẤT (1.00 = bản gốc). Lớn hơn WR_FLOOR càng nhiều -> ván mới nhất càng nặng so với ván cũ.
#               Phải > WR_FLOOR (nếu <= thì ván mới không còn nặng hơn ván cũ). Đặt = WR_FLOOR -> mọi ván bằng nhau.
#   WR_FLOOR  = sàn trọng số của ván cũ (0.35 = ván cũ nhất vẫn nặng bằng 35% ván mới nhất khi NEWEST=1.00). Lớn hơn -> nhớ cầu cũ nhiều hơn.
#               (đặt WR_FLOOR = 1 -> mọi ván bằng nhau · đặt WR_FLOOR = 0 -> quên cầu cũ rất nhanh)
#
#   Với WINDOW=11 / DECAY=0.75 / FLOOR=0.35 / NEWEST=1.00, trọng số (cũ nhất -> mới nhất):
#       0.39 · 0.40 · 0.42 · 0.44 · 0.47 · 0.50 · 0.56 · 0.62 · 0.72 · 0.84 · 1.00
#   -> 3 ván mới nhất nắm ~40% quyền quyết định, 8 ván còn lại nắm ~60% (cũ nhất vẫn còn ~39% sức của ván mới nhất).
#   WR của 1 logic = tổng trọng số các ván logic đó đoán đúng / tổng trọng số các ván đang xét.
#   Cách chia nhóm giữ nguyên: WR < 50% -> nhóm THẤP · WR ≥ 50% -> nhóm CAO, nhóm THẤP đông hơn thì theo nhóm THẤP,
#   còn lại theo nhóm CAO; nhóm được chọn hoà phiếu -> theo đa số tất cả logic.
WR_WINDOW = 13             # số ván gần nhất dùng để tính WR
WR_DECAY = 0.75            # tốc độ giảm trọng số khi ván cũ dần (nhỏ = phản ứng nhanh)
WR_FLOOR = 0.95            # sàn trọng số của ván cũ so với ván mới nhất (lớn = nhớ cầu cũ nhiều)
WR_WEIGHT_NEWEST = 1.42    # trọng số ván mới nhất (ĐÃ ÁP DỤNG vào tính WR; 1.00 = hành vi bản gốc)
# dạng Fraction để tính/so sánh chính xác (dùng trong wr_weights)
_W_DECAY = Fraction(str(WR_DECAY))
_W_FLOOR = Fraction(str(WR_FLOOR))
_W_NEWEST = Fraction(str(WR_WEIGHT_NEWEST))
# Bảng trọng số đầy đủ (cũ nhất -> mới nhất) - chỉ để hiển thị ở /health và khi khởi động
WR_WEIGHTS_FULL = [round(float(_W_FLOOR + (_W_NEWEST - _W_FLOOR) * _W_DECAY ** (WR_WINDOW - 1 - k)), 4) for k in range(WR_WINDOW)]

# ═══════════════════════════════════════════════════════════════════════════
#  ⚙  CONFIG BẺ FINAL CỦA SUN  (bật / tắt)  —  CHỈNH Ở ĐÂY   (LC79 có công tắc bẻ final riêng: LC_FLIP_FINAL_DEFAULT ở khối CONFIG LC79)
# ═══════════════════════════════════════════════════════════════════════════
#   FLIP_FINAL_DEFAULT = False  ->  TẮT (mặc định): du_doan = final của 21 logic, KHÔNG bẻ
#   FLIP_FINAL_DEFAULT = True   ->  BẬT : du_doan = đảo ngược final (TÀI <-> XỈU)
#
#  Muốn đổi mà không sửa file (ưu tiên: cờ dòng lệnh > biến môi trường > FLIP_FINAL_DEFAULT):
#     biến môi trường :  SUNVIW_FLIP=1  (bật)  |  SUNVIW_FLIP=0  (tắt)
#     dòng lệnh       :  python sunviw_api.py --flip      (bật)
#                        python sunviw_api.py --no-flip   (tắt)
FLIP_FINAL_DEFAULT = True


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
ICON_DUNG = "✅"            # icon hiện cho ván ĐOÁN ĐÚNG trong chuỗi "chuoi" của /api/predict
ICON_SAI = "❌"             # icon hiện cho ván ĐOÁN SAI

# ─── PERSISTENCE (lưu graded để Railway không mất sau restart) ───────────
PERSIST_PATH = os.environ.get("SUNVIW_PERSIST", "/tmp/sunviw_graded.json")
PERSIST_KEEP = 50          # giữ tối đa N graded entry trong file (>= WR_WINDOW đủ dùng)

# ═══════════════════════════════════════════════════════════════════════════
#  ⚙  CONFIG LC79 (GAME 2)  —  RIÊNG HOÀN TOÀN, KHÔNG ẢNH HƯỞNG CONFIG SUN Ở TRÊN  —  CHỈNH Ở ĐÂY
# ═══════════════════════════════════════════════════════════════════════════
#   Upstream trả ~100 phiên gần nhất (phiên MỚI NHẤT ở đầu list, càng xuống càng cũ).
#   WR của LC xét ĐÚNG LC_WR_WINDOW ván gần nhất lấy thẳng từ API (vd 15 -> đúng 15 ván mới nhất của API).
#   Đúng/sai: dự đoán phiên +1 (kèm xúc xắc phiên gần nhất) -> LƯU dự đoán -> quét API mỗi LC_POLL_SEC giây
#   đến khi API trả kết quả phiên đó -> so đúng/sai -> lặp lại với phiên +1 kế tiếp.
LC_UPSTREAM_URL = os.environ.get(
    "LC79_UPSTREAM",
    "https://wtxmd52.tele68.com/v1/txmd5/sessions?cp=R&cl=R&pf=web&at=a379cb76ee3f564314afa7136c476a4b",
)
LC_POLL_SEC = 3.0          # chu kỳ quét API LC79 (giây)
LC_WR_WINDOW = 11          # số ván gần nhất dùng để tính WR (tối đa ~99 vì API chỉ có ~100 phiên)
LC_WR_DECAY = 0.75         # tốc độ giảm trọng số ván cũ (như WR_DECAY của Sun)
LC_WR_FLOOR = 1.3         # sàn trọng số ván cũ (như WR_FLOOR của Sun)
LC_WR_WEIGHT_NEWEST = 0.95  # trọng số ván mới nhất (như WR_WEIGHT_NEWEST của Sun; 1.00 = hành vi bản gốc)
LC_WR_MIN_GAMES = 1        # số ván tối thiểu để dùng WR
LC_FLIP_FINAL_DEFAULT = False                      # bẻ final của LC79 (RIÊNG, độc lập FLIP_FINAL của Sun): True = bẻ · False = theo final gốc
                                                   # ưu tiên: cờ dòng lệnh --lc-flip/--lc-no-flip > env LC79_FLIP=1|0 > giá trị này
LC_FLIP_FINAL = _env_bool("LC79_FLIP", LC_FLIP_FINAL_DEFAULT)
LC_PRED_PATH = os.environ.get("LC79_PRED", "/tmp/lc79_preds.json")   # file lưu các dự đoán LC đã chấm / đang chờ
LC_PRED_KEEP = 300         # giữ tối đa N dự đoán LC trong file

# ─── PANEL /api/html ─────────────────────────────────────────────────────
PANEL_DEFAULT_SHOW = 30    # số ván lịch sử panel hiện mặc định (đổi trực tiếp trên panel, trình duyệt nhớ lại)
HIST_MAX = 300             # trần số ván lịch sử cho ?hist=N và ô nhập trên panel

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
def wr_weights(n, decay=None, floor=None, newest=None):
    """Trọng số của n ván gần nhất, thứ tự cũ nhất -> mới nhất (kiểu Fraction = chính xác tuyệt đối khi so với 50%).
    trọng số(tuổi a) = WR_FLOOR + (WR_WEIGHT_NEWEST - WR_FLOOR) * WR_DECAY ** a, a = 0 là ván mới nhất (= WR_WEIGHT_NEWEST).
    Vd n=11, DECAY=0.75, FLOOR=0.35, NEWEST=1.00 -> [0.39, 0.40, 0.42, 0.44, 0.47, 0.50, 0.56, 0.62, 0.72, 0.84, 1.00]."""
    decay = _W_DECAY if decay is None else decay      # None -> config Sun; LC truyền config riêng
    floor = _W_FLOOR if floor is None else floor
    newest = _W_NEWEST if newest is None else newest
    return [floor + (newest - floor) * decay ** (n - 1 - k) for k in range(n)]


def wr_decision(votes, graded, window=None, decay=None, floor=None, min_games=None, newest=None):
    """Giống wrDecision() trong HTML + thêm avg (độ tin cậy = TB WR của các logic đang dùng, 0-100).
    CHỈ KHÁC bản gốc ở chỗ WR có TRỌNG SỐ: ván mới nhất = WR_WEIGHT_NEWEST, ván cũ giảm theo hàm mũ nhưng không thấp hơn
    WR_FLOOR (xem CONFIG WR CÓ TRỌNG SỐ). Cách chia nhóm / chọn nhóm / hoà phiếu giữ NGUYÊN như bản gốc."""
    all_vote = vote_result(votes)
    window = WR_WINDOW if window is None else window        # None -> config Sun; LC truyền config riêng
    min_games = WR_MIN_GAMES if min_games is None else min_games
    win = graded[-window:]                            # cũ -> mới
    n = len(win)
    if n < min_games:
        return {"mode": "ALL", "n": n, "final": all_vote, "wins": [], "low": [], "high": [],
                "gT": 0, "gX": 0, "tie": False, "avg": None, "wsum": 0.0, "weights": []}
    weights = wr_weights(n, decay, floor, newest)
    wsum = sum(weights)                               # tổng trọng số (mẫu số của WR)
    # wins[i] = tổng trọng số các ván logic i đoán đúng (Fraction -> so với 50% chính xác, không sai số float)
    wins = [sum((wt for wt, g in zip(weights, win) if g["votes"][i] == g["actual"]), Fraction(0))
            for i in range(len(votes))]
    low, high = [], []
    for i, w in enumerate(wins):
        (low if w * 2 < wsum else high).append(i)    # WR <50% -> thấp · WR ≥50% -> cao (WR có trọng số)
    use_low = len(low) > len(high)
    idx = low if use_low else high
    gv = [votes[i] for i in idx]
    gT = sum(1 for x in gv if x == TAI)
    gX = len(gv) - gT
    final, tie = vote_result(gv), False
    if final == 'SKIP':
        final, tie = all_vote, True
    avg = float(sum(wins) / (len(wins) * wsum) * 100)  # TB WR có trọng số của các logic đang dùng
    return {"mode": "LOW" if use_low else "HIGH", "n": n, "final": final, "wins": [float(w) for w in wins],
            "low": low, "high": high, "gT": gT, "gX": gX, "tie": tie, "avg": avg,
            "wsum": float(wsum), "weights": [float(w) for w in weights]}


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
    elif isinstance(data, dict) and "phien" in data:          # API /api/tx: 1 object = 1 phiên mới nhất
        arr = [data]
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


_hist_store = {}            # phien -> record (các phiên đã quét được, tool tự tích lũy vì upstream chỉ trả 1 phiên)
_hist_loaded = False


def hist_update(records):
    """Gộp các phiên vừa quét vào lịch sử (nạp từ HIST_PATH lần đầu, lưu lại sau mỗi lần), trả về list cũ -> mới.
    Chỉ gọi trong refresh() (đã có _refresh_lock)."""
    global _hist_loaded
    if not _hist_loaded:
        _hist_loaded = True
        try:
            with open(HIST_PATH, "r", encoding="utf-8") as f:
                for r in json.load(f):
                    if isinstance(r, dict) and all(k in r for k in ("phien", "d1", "d2", "d3", "total", "actual")):
                        _hist_store[r["phien"]] = r
        except Exception:  # noqa: BLE001
            pass
    for r in records:
        _hist_store[r["phien"]] = r
    for k in sorted(_hist_store)[:-HIST_KEEP]:
        del _hist_store[k]
    out = [_hist_store[k] for k in sorted(_hist_store)]
    try:
        tmp = HIST_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False)
        os.replace(tmp, HIST_PATH)
    except Exception:  # noqa: BLE001
        pass
    return out


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
        "trong_so_wr": {                                          # cơ chế WR có trọng số đang áp dụng
            "so_van": dec["n"],
            "trong_so": dec["weights"],                           # cũ nhất -> mới nhất
            "van_moi_nhat": WR_WEIGHT_NEWEST,                     # trọng số ván mới nhất (WR_WEIGHT_NEWEST)
            "he_so_giam": WR_DECAY,                               # WR_DECAY: tốc độ quên ván cũ
            "san_trong_so": WR_FLOOR,                             # WR_FLOOR: sàn trọng số ván cũ
        },
        "logic": [
            {"ten": LOGIC_NAMES[i], "du_doan": votes[i],
             "wr": (round(dec["wins"][i] / dec["wsum"] * 100, 1) if dec["wins"] else None),
             "nhom": (None if not dec["wins"] else ("THAP" if i in dec["low"] else "CAO"))}
            for i in range(len(votes))
        ],
        "final_goc": dec["final"],
        "tool_dung_sai_15_van": _recent_accuracy(graded, WR_WINDOW),
    }
    hist_rows = [{"phien": g["session"], "du_doan": out_final(g["final"]), "ket_qua": g["actual"], "tong": g.get("total"),
                  "dung": out_final(g["final"]) == g["actual"]} for g in reversed(graded[-HIST_MAX:])]   # mới -> cũ
    return {"base": base, "detail": detail, "hist": hist_rows}


def _recent_accuracy(graded, size, with_chuoi=False):
    """Đúng/sai của final ĐÃ ĐƯA RA API (sau bẻ nếu đang bật) ở `size` ván gần nhất."""
    win = graded[-size:]
    oks = [out_final(g["final"]) == g["actual"] for g in win]
    out = {"dung": sum(oks), "tong": len(win)}
    if with_chuoi:
        out = {"dung": out["dung"], "sai": len(win) - out["dung"], "tong": len(win),
               "chuoi": "".join(ICON_DUNG if ok else ICON_SAI for ok in reversed(oks))}     # mới -> cũ
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
        recs = parse_history(_fetch_json(UPSTREAM_URL))
        if not recs:
            raise ValueError("upstream khong co phien hop le (can phien + xuc_xac_1..3)")
        hist = hist_update(recs)                      # upstream chỉ trả 1 phiên mới nhất -> gộp vào lịch sử tích lũy
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
    threading.Thread(target=_lc_poll_loop, daemon=True, name="lc79-poller").start()


# ─── LC79 (GAME 2): QUÉT API HISTORY · LƯU DỰ ĐOÁN · CHẤM ĐÚNG/SAI ───────
# Dùng CHUNG bộ logic (compute_all) với Sun, nhưng config / WR / lịch sử đúng-sai hoàn toàn RIÊNG (xem CONFIG LC79).
_LC_DECAY, _LC_FLOOR = Fraction(str(LC_WR_DECAY)), Fraction(str(LC_WR_FLOOR))
_LC_NEWEST = Fraction(str(LC_WR_WEIGHT_NEWEST))
_lc_preds = {}              # phien -> dự đoán đã LƯU (dung=None: đang chờ API trả kết quả phiên đó)
_lc_loaded = False
_lc_state = {"target": None, "base": None, "detail": None, "error": None, "updated": None, "checked": None, "polls": 0}
_lc_lock = threading.Lock()            # bảo vệ _lc_state + _lc_preds (giữ ngắn)
_lc_refresh_lock = threading.Lock()    # mỗi lúc chỉ 1 lượt quét


def lc_out(final):
    """Final LC đã đưa ra API (sau bẻ nếu LC_FLIP_FINAL bật)."""
    return flip_pred(final) if LC_FLIP_FINAL else final


def parse_lc(data):
    """API LC79: {"list":[{"id":phiên,"resultTruyenThong":"TAI|XIU","dices":[a,b,c],"point":n}, ...]}
    Phiên MỚI NHẤT ở ĐẦU list, càng xuống càng cũ. Trả list cũ -> mới (sắp theo id nên không phụ thuộc thứ tự upstream)."""
    arr = data.get("list") if isinstance(data, dict) else data
    m = {}
    for r in arr if isinstance(arr, list) else []:
        if not isinstance(r, dict):
            continue
        phien, dices = _parse_int(r.get("id")), r.get("dices")
        if phien is None or not isinstance(dices, list) or len(dices) != 3:
            continue
        d = [_parse_int(x) for x in dices]
        if None in d or any(x < 1 or x > 6 for x in d):
            continue
        total = sum(d)
        m[phien] = {"phien": phien, "d1": d[0], "d2": d[1], "d3": d[2], "total": total,
                    "actual": norm_kq(r.get("resultTruyenThong")) or actual_of(total)}
    return [m[k] for k in sorted(m)]


def lc_graded(hist, n):
    """ĐÚNG n ván gần nhất (cũ -> mới) lấy thẳng từ API: vote của từng logic cho phiên k (dùng xúc xắc phiên k-1)
    so với kết quả thật phiên k. Đây là dữ liệu để tính WR của LC."""
    out = []
    for i in range(len(hist) - 1, 0, -1):
        p, c = hist[i - 1], hist[i]
        if c["phien"] != p["phien"] + 1:
            continue
        out.append({"session": c["phien"], "actual": c["actual"],
                    "votes": compute_all(c["phien"], p["d1"], p["d2"], p["d3"])})
        if len(out) >= n:
            break
    return out[::-1]


def _lc_load():
    """Nạp dự đoán đã lưu (lần quét đầu tiên). Gọi trong _lc_lock."""
    global _lc_loaded
    if _lc_loaded:
        return
    _lc_loaded = True
    try:
        with open(LC_PRED_PATH, "r", encoding="utf-8") as f:
            for r in json.load(f):
                if isinstance(r, dict) and "phien" in r and r.get("sig") == LOGIC_SIG:
                    _lc_preds[r["phien"]] = r
    except Exception:  # noqa: BLE001
        pass


def _lc_save():
    """Ghi dự đoán ra file (atomic). Gọi trong _lc_lock."""
    try:
        rows = [_lc_preds[k] for k in sorted(_lc_preds)][-LC_PRED_KEEP:]
        tmp = LC_PRED_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False)
        os.replace(tmp, LC_PRED_PATH)
    except Exception:  # noqa: BLE001
        pass


def lc_refresh():
    """Quét API LC79: (1) chấm dự đoán đang chờ nếu API đã trả kết quả phiên đó,
    (2) có phiên mới -> dự đoán phiên +1 (kèm xúc xắc phiên gần nhất) và LƯU lại. Ném exception nếu lỗi."""
    with _lc_refresh_lock:
        hist = parse_lc(_fetch_json(LC_UPSTREAM_URL))
        if not hist:
            raise ValueError("upstream LC79 khong co phien hop le (can list[].id + dices)")
        by_p = {r["phien"]: r for r in hist}
        latest = hist[-1]
        target = latest["phien"] + 1
        changed = False
        with _lc_lock:
            _lc_load()
            for ph in list(_lc_preds):
                p = _lc_preds[ph]
                if p.get("dung") is not None or ph > latest["phien"]:
                    continue
                r = by_p.get(ph)
                if r is None:                        # phiên đã trôi khỏi API mà chưa kịp chấm -> bỏ
                    del _lc_preds[ph]
                else:
                    p.update(ket_qua=r["actual"], tong=r["total"], xuc_xac=[r["d1"], r["d2"], r["d3"]],
                             dung=(p["du_doan"] == r["actual"]), cham=_now())
                changed = True
            need = _lc_state["target"] != target or _lc_state["base"] is None
        if need:
            votes = compute_all(target, latest["d1"], latest["d2"], latest["d3"])
            dec = wr_decision(votes, lc_graded(hist, LC_WR_WINDOW), LC_WR_WINDOW, _LC_DECAY, _LC_FLOOR, LC_WR_MIN_GAMES, _LC_NEWEST)
            tai = sum(1 for v in votes if v == TAI)
            base = {"ok": True, "game": "lc79", "phien": target, "du_doan": lc_out(dec["final"]), "be_final": LC_FLIP_FINAL,
                    "do_tin_cay": None if dec["avg"] is None else round(dec["avg"], 1),
                    "phien_truoc": latest["phien"], "xuc_xac": [latest["d1"], latest["d2"], latest["d3"]],
                    "tong": latest["total"], "ket_qua_truoc": latest["actual"],
                    "so_van_wr": dec["n"], "wr_window": LC_WR_WINDOW}
            detail = {
                "vote": {"TÀI": tai, "XỈU": len(votes) - tai}, "so_logic": len(votes),
                "nhom_theo": {"ALL": "da so", "LOW": "WR thap", "HIGH": "WR cao"}[dec["mode"]],
                "nhom_tai_xiu": {"TÀI": dec["gT"], "XỈU": dec["gX"]}, "hoa_dung_da_so": dec["tie"],
                "final_goc": dec["final"],
                "trong_so_wr": {"so_van": dec["n"], "trong_so": dec["weights"],
                                "van_moi_nhat": LC_WR_WEIGHT_NEWEST,
                                "he_so_giam": LC_WR_DECAY, "san_trong_so": LC_WR_FLOOR},
                "logic": [{"ten": LOGIC_NAMES[i], "du_doan": votes[i],
                           "wr": (round(dec["wins"][i] / dec["wsum"] * 100, 1) if dec["wins"] else None),
                           "nhom": (None if not dec["wins"] else ("THAP" if i in dec["low"] else "CAO"))}
                          for i in range(len(votes))],
            }
            with _lc_lock:
                if target not in _lc_preds:          # LƯU dự đoán đúng 1 lần cho phiên này (không tính lại dù config đổi)
                    _lc_preds[target] = {"phien": target, "du_doan": base["du_doan"], "final_goc": dec["final"],
                                         "be_final": LC_FLIP_FINAL, "so_van_wr": dec["n"], "dung": None,
                                         "sig": LOGIC_SIG, "luc": _now()}
                    changed = True
                base["du_doan"] = _lc_preds[target]["du_doan"]       # luôn theo dự đoán ĐÃ LƯU
                base["be_final"] = _lc_preds[target]["be_final"]
                _lc_state.update(target=target, base=base, detail=detail, updated=_now())
        with _lc_lock:
            for k in sorted(_lc_preds)[:-LC_PRED_KEEP]:
                del _lc_preds[k]
                changed = True
            if changed:
                _lc_save()
            _lc_state.update(error=None, checked=_now())


def _lc_poll_loop():
    while True:
        try:
            lc_refresh()
        except Exception as e:  # noqa: BLE001 - giữ poller sống dù upstream lỗi
            with _lc_lock:
                _lc_state["error"] = f"{type(e).__name__}: {e}"
                _lc_state["checked"] = _now()
        with _lc_lock:
            _lc_state["polls"] += 1
        time.sleep(LC_POLL_SEC)


def lc_history():
    """Các ván LC đã chấm đúng/sai, mới -> cũ."""
    with _lc_lock:
        rows = [p for _, p in sorted(_lc_preds.items(), reverse=True) if p.get("dung") is not None]
    return [{"phien": p["phien"], "du_doan": p["du_doan"], "ket_qua": p["ket_qua"], "tong": p["tong"], "dung": p["dung"]}
            for p in rows]


def _acc_rows(rows, n=10):
    w = rows[:n]
    dung = sum(1 for r in w if r["dung"])
    return {"dung": dung, "sai": len(w) - dung, "tong": len(w),
            "chuoi": "".join(ICON_DUNG if r["dung"] else ICON_SAI for r in w)}      # mới -> cũ


# ─── PANEL HTML (/api/html) ──────────────────────────────────────────────
PANEL_HTML = r"""<!doctype html>
<html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SUNVIW · Panel theo dõi</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;600;800&display=swap" rel="stylesheet">
<style>
:root{--bg:#0f1424;--pn:#171d33;--ln:#252d4a;--tx:#e8ebf5;--mu:#8a93b2;--tai:#f5b942;--xiu:#5cc8ff;--ok:#3ddc97;--no:#ff6b81}
*{box-sizing:border-box}
body{margin:0 auto;max-width:720px;padding:14px 14px 40px;background:var(--bg);color:var(--tx);font:15px/1.45 "Be Vietnam Pro",system-ui,sans-serif;font-variant-numeric:tabular-nums}
header{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px}
h1{font-size:17px;margin:0;font-weight:800}
#st{font-size:12px;color:var(--mu)}
#st i{display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--ok);margin-right:6px}
#st.bad i{background:var(--no)}
.tabs{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:12px}
.tab{background:var(--pn);border:1px solid var(--ln);color:var(--tx);border-radius:12px;padding:10px 14px;font:inherit;cursor:pointer;display:flex;justify-content:space-between;align-items:center}
.tab.on{border-color:var(--mu);box-shadow:inset 0 -3px 0 var(--tx)}
.tab small{color:var(--mu)}
.tai{color:var(--tai)}.xiu{color:var(--xiu)}.okc{color:var(--ok)}.noc{color:var(--no)}.mu{color:var(--mu);font-size:13px}
.hero{background:var(--pn);border:1px solid var(--ln);border-radius:16px;padding:18px;display:grid;grid-template-columns:1fr auto;gap:16px;align-items:center}
.big{font-size:clamp(52px,16vw,88px);font-weight:800;line-height:1;margin:4px 0}
.prev{text-align:right}
.dice{display:inline-flex;gap:6px;margin:8px 0}
.dice i{width:30px;height:30px;border-radius:7px;display:block}
.stats{display:flex;flex-wrap:wrap;gap:6px 20px;margin:14px 2px;align-items:baseline}
.stats b{font-size:22px}
.cfg{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:4px 2px 12px}
.cfg input{width:76px;background:var(--pn);border:1px solid var(--ln);color:var(--tx);border-radius:8px;padding:6px 8px;font:inherit}
.cfg button{background:none;border:1px solid var(--ln);color:var(--mu);border-radius:8px;padding:5px 10px;font:inherit;cursor:pointer}
.cfg button:hover{color:var(--tx)}
.strip{display:flex;flex-wrap:wrap;gap:4px;margin-bottom:12px}
.chip{width:20px;height:20px;border-radius:5px;font-size:12px;line-height:20px;text-align:center;color:#0f1424;font-weight:800}
.chip.ok{background:var(--ok)}.chip.no{background:var(--no)}
table{width:100%;border-collapse:collapse}
th{font-weight:600;color:var(--mu);font-size:12px;text-align:left;padding:6px 8px}
td{padding:7px 8px;border-top:1px solid var(--ln)}
.r{text-align:right}
@media(max-width:480px){.hero{grid-template-columns:1fr}.prev{text-align:left}}
</style></head><body>
<header><h1>SUNVIW · Tài Xỉu</h1><div id="st"></div></header>
<nav class="tabs" id="tabs"></nav>
<main id="main"></main>
<div class="cfg">
  <label for="n" class="mu">Số ván lịch sử hiển thị</label>
  <input id="n" type="number" min="1" max="__MAX__">
  <button data-n="10">10</button><button data-n="20">20</button><button data-n="50">50</button><button data-n="100">100</button>
</div>
<div id="hist"></div>
<script>
const G={sun:{n:'Sun',u:'/api/predictsun'},lc:{n:'LC79',u:'/api/predictlc79'}};
let cur=localStorage.getItem('g') in G?localStorage.getItem('g'):'sun',N=+localStorage.getItem('n')||__SHOW__;
const D={},$=s=>document.querySelector(s),cl=v=>v==='TÀI'?'tai':v==='XỈU'?'xiu':'';
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const P={1:[[50,50]],2:[[26,26],[74,74]],3:[[26,26],[50,50],[74,74]],4:[[26,26],[74,26],[26,74],[74,74]],5:[[26,26],[74,26],[50,50],[26,74],[74,74]],6:[[26,26],[74,26],[26,50],[74,50],[26,74],[74,74]]};
const dice=a=>`<span class="dice">${a.map(n=>`<i style="background:${P[n].map(([x,y])=>`radial-gradient(circle at ${x}% ${y}%,#1a1f36 0 3.2px,transparent 3.8px)`).join(',')},#f2efe6"></i>`).join('')}</span>`;
const acc=d=>{const h=d.lich_su||[],k=h.filter(x=>x.dung).length;return{k,t:h.length,p:h.length?Math.round(k*100/h.length):null}};
function render(){
  $('#tabs').innerHTML=Object.entries(G).map(([k,g])=>{const d=D[k]||{},a=acc(d);
    return `<button class="tab${k===cur?' on':''}" data-g="${k}"><span>${g.n} <b class="${cl(d.du_doan)}">${d.ok?d.du_doan:'…'}</b></span><small>${a.p===null?'–':a.p+'%'}</small></button>`}).join('');
  const d=D[cur]||{},a=acc(d);
  if(!d.ok){$('#main').innerHTML=`<div class="hero"><div class="mu">${esc(d.loi||'Đang tải…')}</div></div>`;$('#hist').innerHTML='';return}
  $('#main').innerHTML=`<section class="hero"><div><div class="mu">Dự đoán phiên ${d.phien}</div><div class="big ${cl(d.du_doan)}">${d.du_doan}</div><div class="mu">Độ tin cậy ${d.do_tin_cay==null?'–':d.do_tin_cay+'%'}${d.be_final?' · đã bẻ final':''} · xét ${d.so_van_wr} ván</div></div><div class="prev"><div class="mu">Phiên ${d.phien_truoc}</div>${dice(d.xuc_xac)}<div><b>${d.tong}</b> <span class="${cl(d.ket_qua_truoc)}">${d.ket_qua_truoc}</span></div></div></section><div class="stats"><span><b class="okc">${a.k}</b> <span class="mu">đúng</span></span><span><b class="noc">${a.t-a.k}</b> <span class="mu">sai</span></span><span><b>${a.p===null?'–':a.p+'%'}</b> <span class="mu">trên ${a.t} ván</span></span></div>`;
  const h=d.lich_su||[];
  $('#hist').innerHTML=h.length?`<div class="strip">${h.map(x=>`<span class="chip ${x.dung?'ok':'no'}" title="#${x.phien}">${x.dung?'✓':'✗'}</span>`).join('')}</div><table><tr><th>Phiên</th><th>Dự đoán</th><th>Kết quả</th><th class="r">Đúng/sai</th></tr>${h.map(x=>`<tr><td>#${x.phien}</td><td class="${cl(x.du_doan)}">${x.du_doan}</td><td class="${cl(x.ket_qua)}">${x.ket_qua} <span class="mu">(${x.tong})</span></td><td class="r ${x.dung?'okc':'noc'}">${x.dung?'Đúng':'Sai'}</td></tr>`).join('')}</table>`:`<p class="mu">Chưa có ván nào được chấm. Tool lưu dự đoán rồi chờ API trả kết quả phiên đó.</p>`;
  $('#st').className=Object.values(D).some(x=>x&&(!x.ok||x.stale))?'bad':'';
  $('#st').innerHTML=`<i></i>${esc(d.cap_nhat||'')}`;
}
$('#tabs').onclick=e=>{const b=e.target.closest('[data-g]');if(b){cur=b.dataset.g;localStorage.setItem('g',cur);render()}};
$('#n').value=N;
function setN(v){N=Math.max(1,Math.min(+v||1,__MAX__));$('#n').value=N;localStorage.setItem('n',N);load()}
$('#n').onchange=e=>setN(e.target.value);
document.querySelectorAll('[data-n]').forEach(b=>b.onclick=()=>setN(b.dataset.n));
async function load(){
  await Promise.all(Object.entries(G).map(async([k,g])=>{
    try{const r=await fetch(`${g.u}?hist=${N}`,{cache:'no-store'});D[k]=await r.json()}
    catch(e){D[k]={ok:false,loi:'Mất kết nối: '+e}}}));
  render();
}
load();setInterval(load,3000);
</script></body></html>
"""


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


def _hist_n():
    """?hist=N -> trả thêm lich_su (N ván đúng/sai gần nhất, mới -> cũ). 0 / không truyền = không trả."""
    try:
        return max(0, min(int(request.args.get("hist", 0)), HIST_MAX))
    except ValueError:
        return 0


@app.route("/api/predictlc79")
@app.route("/api/prdictlc79")                     # giữ cả tên gõ tắt cho khỏi lệch
def api_predict_lc79():
    ensure_poller()
    with _lc_lock:
        have = _lc_state["base"] is not None
    if not have:                                  # request đầu tiên, poller chưa kịp quét xong
        try:
            lc_refresh()
        except Exception as e:  # noqa: BLE001
            with _lc_lock:
                _lc_state["error"] = f"{type(e).__name__}: {e}"
    with _lc_lock:
        base, detail, err, upd = _lc_state["base"], _lc_state["detail"], _lc_state["error"], _lc_state["updated"]
    if base is None:
        return _json({"ok": False, "game": "lc79", "loi": err or "chua co du lieu"}, 503)
    rows = lc_history()
    out = dict(base)
    out["tool_dung_sai_10_van"] = _acc_rows(rows, 10)
    out["stale"] = bool(err)
    if err:
        out["loi"] = err
    out["cap_nhat"] = upd
    n = _hist_n()
    if n:
        out["lich_su"] = rows[:n]
    if request.args.get("detail") in ("1", "true", "yes"):
        out["chi_tiet"] = detail
    return _json(out)


@app.route("/api/html")
def api_html():
    page = PANEL_HTML.replace("__SHOW__", str(PANEL_DEFAULT_SHOW)).replace("__MAX__", str(HIST_MAX))
    return Response(page, content_type="text/html; charset=utf-8")


@app.route("/api/predictsun")
@app.route("/api/predict")                        # tên cũ, giữ để tool đang chạy không bị hỏng
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
    out["game"] = "sun"
    out["stale"] = bool(err)
    if err:
        out["loi"] = err
    out["cap_nhat"] = upd
    n = _hist_n()
    if n:
        out["lich_su"] = res["hist"][:n]
    if request.args.get("detail") in ("1", "true", "yes"):
        out["chi_tiet"] = res["detail"]
    return _json(out)


@app.route("/health")
def health():
    ensure_poller()
    with _state_lock:
        s = {k: _state[k] for k in ("latest", "error", "updated", "checked", "polls")}
    s.update(ok=s["error"] is None and s["latest"] is not None, upstream=UPSTREAM_URL,
             poll_sec=POLL_SEC, wr_window=WR_WINDOW, be_final=FLIP_FINAL,
             wr_weights=WR_WEIGHTS_FULL, wr_decay=WR_DECAY, wr_floor=WR_FLOOR, wr_newest=WR_WEIGHT_NEWEST)       # trọng số cũ nhất -> mới nhất
    with _lc_lock:
        lc = {k: _lc_state[k] for k in ("error", "updated", "checked", "polls")}
        lc["latest"] = (_lc_state["base"] or {}).get("phien_truoc")
    lc.update(ok=lc["error"] is None and lc["latest"] is not None, poll_sec=LC_POLL_SEC, wr_window=LC_WR_WINDOW,
              be_final=LC_FLIP_FINAL, wr_decay=LC_WR_DECAY, wr_floor=LC_WR_FLOOR, wr_newest=LC_WR_WEIGHT_NEWEST)
    s["lc79"] = lc
    return _json(s)


@app.route("/")
def index():
    return _json({"api": f"SUNVIW {len(LOGIC_NAMES)} logics (dedup={DEDUP_MODE})", "endpoints": ["/api/predictsun", "/api/predictlc79", "/api/predictsun?detail=1", "/api/predictlc79?detail=1", "/api/html", "/health"]})


# Chạy dưới gunicorn (Railway) thì main() không được gọi -> bật poller ngay khi import.
if __name__ != "__main__":
    ensure_poller()


def main():
    global UPSTREAM_URL, POLL_SEC, FLIP_FINAL, LC_UPSTREAM_URL, LC_POLL_SEC, LC_FLIP_FINAL
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(description="SUNVIW 24 logics (mặc định 13) - API JSON")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=int(os.environ.get("PORT", 5000)))
    ap.add_argument("--upstream", default=UPSTREAM_URL, help="URL API phien moi nhat (…/api/tx)")
    ap.add_argument("--poll", type=float, default=POLL_SEC, help="chu ky quet upstream (giay)")
    ap.add_argument("--lc-upstream", default=LC_UPSTREAM_URL, help="URL API history LC79")
    ap.add_argument("--lc-poll", type=float, default=LC_POLL_SEC, help="chu ky quet API LC79 (giay)")
    lg = ap.add_mutually_exclusive_group()
    lg.add_argument("--lc-flip", action="store_true", help="BẬT bẻ final của LC79 (riêng, không ảnh hưởng Sun)")
    lg.add_argument("--lc-no-flip", action="store_true", help="TẮT bẻ final của LC79 (theo final gốc)")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--flip", action="store_true", help="BẬT bẻ final (đảo TÀI<->XỈU)")
    g.add_argument("--no-flip", action="store_true", help="TẮT bẻ final (giữ nguyên final của các logic đang dùng)")
    a = ap.parse_args()
    UPSTREAM_URL, POLL_SEC = a.upstream, a.poll
    LC_UPSTREAM_URL, LC_POLL_SEC = a.lc_upstream, a.lc_poll
    if a.flip:
        FLIP_FINAL = True
    elif a.no_flip:
        FLIP_FINAL = False
    if a.lc_flip:
        LC_FLIP_FINAL = True
    elif a.lc_no_flip:
        LC_FLIP_FINAL = False
    ensure_poller()
    print(f"SUNVIW API  ->  http://{a.host}:{a.port}/api/predict")
    print(f"upstream    ->  {UPSTREAM_URL}")
    print(f"LC79        ->  http://{a.host}:{a.port}/api/predictlc79 · panel http://{a.host}:{a.port}/api/html")
    print(f"LC79 WR     ->  xet dung {LC_WR_WINDOW} van gan nhat tu API · van moi nhat x{LC_WR_WEIGHT_NEWEST} · be final {'BAT' if LC_FLIP_FINAL else 'TAT'}")
    print(f"be final SUN ->  {'BAT' if FLIP_FINAL else 'TAT'}")
    print(f"WR          ->  xet {WR_WINDOW} van gan nhat, van moi nhat x{WR_WEIGHT_NEWEST}, trong so (cu -> moi): "
          + " · ".join(f"{w:.2f}" for w in WR_WEIGHTS_FULL))
    app.run(host=a.host, port=a.port, threaded=True)


if __name__ == "__main__":
    main()
