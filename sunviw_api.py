# -*- coding: utf-8 -*-
"""
SUNVIW 24 LOGICS (mặc định chạy 13 logic) - API JSON  (bản Python của SUNVIW_21logics.html + thêm L3N, L4N, L5N)

Chạy:
    pip install flask
    python sunviw_api.py                      # mặc định http://0.0.0.0:5000
    python sunviw_api.py --port 8080 --upstream https://xxx.trycloudflare.com/api/tx
    python sunviw_api.py --flip               # BẬT bẻ final (mặc định TẮT; hoặc SUNVIW_FLIP=1, hoặc sửa FLIP_FINAL_DEFAULT)
    python sunviw_api.py --no-auto-flip       # TẮT cơ chế tự đổi bẻ/theo khi sai (hoặc SUNVIW_FLIP_AUTO=0, hoặc sửa FLIP_AUTO_DEFAULT)

Endpoint:
    GET /api/predict             -> JSON dự đoán (đọc từ cache, trả về ngay)
    GET /api/predict?detail=1    -> thêm chi_tiet: vote từng logic + WR từng logic
    GET /health                  -> trạng thái nền (lần quét gần nhất, lỗi nếu có)

JSON /api/predict:
    {
      "ok": true,
      "phien": 12346,            # phiên được dự đoán (n)
      "du_doan": "TÀI",          # TÀI | XỈU  (mặc định = final của các logic đang dùng; nếu BẬT bẻ final thì = đảo ngược final)
      "be_final": false,         # cơ chế ĐANG ÁP DỤNG cho ván này (true = bẻ final, false = theo final) - có thể khác mặc định khi vừa sai
      "be_mac_dinh": false,      # cơ chế mặc định (FLIP_FINAL_DEFAULT / --flip)
      "doi_co_che": false,       # true = ván này đang chạy cơ chế ĐỔI (ván trước sai ở cơ chế mặc định)
      "do_tin_cay": 58.4,        # % = trung bình WR CÓ TRỌNG SỐ của các logic đang dùng trong WR_WINDOW ván gần nhất (null nếu chưa chấm ván nào)
                                 #     trọng số: ván mới nhất cao nhất (1.00), ván cũ giảm dần nhưng có sàn WR_FLOOR (xem "CONFIG WR CÓ TRỌNG SỐ")
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

🔁 TỰ ĐỔI CƠ CHẾ KHI SAI (FLIP_AUTO_DEFAULT = True):
    Cơ chế mặc định = bẻ final (FLIP_FINAL=True) hoặc theo final (FLIP_FINAL=False).
    - Đang chạy cơ chế MẶC ĐỊNH mà SAI 1 ván  -> ván kế tiếp tự ĐỔI sang cơ chế ngược lại
        (mặc định bẻ -> ván sau THEO final · mặc định theo -> ván sau BẺ final)
    - Ván ĐỔI chạy xong (đúng hay sai đều vậy) -> ván kế tiếp VỀ LẠI cơ chế mặc định
    - Ván trước bị đứt phiên (thiếu dữ liệu) -> chạy cơ chế mặc định
    Đúng/sai tính trên du_doan thực tế đã đưa ra của từng ván (chuoi ✅/❌ cũng theo cơ chế từng ván).
    Cơ chế từng ván được lưu trong file persist nên không bị lệch sau khi restart.

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
UPSTREAM_TIMEOUT = 15      # giây
HIST_PATH = os.environ.get("SUNVIW_HIST", "/tmp/sunviw_hist.json")   # lịch sử các phiên đã quét (tool tự tích lũy)
HIST_KEEP = 300            # giữ tối đa N phiên gần nhất trong lịch sử (>= WR_WINDOW + EVAL_WINDOW là đủ)
POLL_SEC = 3.0             # chu kỳ quét upstream (giống AUTO_INTERVAL_MS của HTML)
WR_MIN_GAMES = 1           # số ván đã chấm tối thiểu để dùng WR (dưới mức này -> đa số 21 logic)

# ═══════════════════════════════════════════════════════════════════════════
#  ⚙  CONFIG WR CÓ TRỌNG SỐ (KIỂU "PHẢN ỨNG NHANH + SÀN NHỚ CẦU CŨ")  —  CHỈNH Ở ĐÂY
# ═══════════════════════════════════════════════════════════════════════════
#   Ván MỚI NHẤT có trọng số = 1.00 (cao nhất). Ván càng cũ trọng số càng giảm theo hàm mũ NHƯNG không bao giờ
#   thấp hơn WR_FLOOR  ->  cầu mới đổi thì phản ứng nhanh (các ván mới chiếm phần lớn quyền), còn cầu cũ vẫn giữ
#   một phần quyền (không bị quên hẳn).
#
#       trọng số(ván tuổi a) = WR_FLOOR + (1 - WR_FLOOR) * WR_DECAY ** a        (a = 0 là ván mới nhất)
#
#   WR_WINDOW = số ván gần nhất được xét để tính WR
#   WR_DECAY  = tốc độ quên (0.75 = mỗi ván cũ hơn, phần "thưởng mới" giảm còn 75%). Nhỏ hơn -> phản ứng nhanh hơn.
#   WR_FLOOR  = sàn trọng số của ván cũ (0.35 = ván cũ nhất vẫn nặng bằng 35% ván mới nhất). Lớn hơn -> nhớ cầu cũ nhiều hơn.
#               (đặt WR_FLOOR = 1 -> mọi ván bằng nhau · đặt WR_FLOOR = 0 -> quên cầu cũ rất nhanh)
#
#   Với WINDOW=11 / DECAY=0.75 / FLOOR=0.35, trọng số (cũ nhất -> mới nhất):
#       0.39 · 0.40 · 0.42 · 0.44 · 0.47 · 0.50 · 0.56 · 0.62 · 0.72 · 0.84 · 1.00
#   -> 3 ván mới nhất nắm ~40% quyền quyết định, 8 ván còn lại nắm ~60% (cũ nhất vẫn còn ~39% sức của ván mới nhất).
#   WR của 1 logic = tổng trọng số các ván logic đó đoán đúng / tổng trọng số các ván đang xét.
#   Cách chia nhóm giữ nguyên: WR < 50% -> nhóm THẤP · WR ≥ 50% -> nhóm CAO, nhóm THẤP đông hơn thì theo nhóm THẤP,
#   còn lại theo nhóm CAO; nhóm được chọn hoà phiếu -> theo đa số tất cả logic.
WR_WINDOW = 13             # số ván gần nhất dùng để tính WR
WR_DECAY = 0.75            # tốc độ giảm trọng số khi ván cũ dần (nhỏ = phản ứng nhanh)
WR_FLOOR = 0.95            # sàn trọng số của ván cũ so với ván mới nhất (lớn = nhớ cầu cũ nhiều)
WR_WEIGHT_NEWEST = 1.42     # trọng số ván mới nhất (giữ cố định 1.00, chỉ để hiển thị)
# dạng Fraction để tính/so sánh chính xác (dùng trong wr_weights)
_W_DECAY = Fraction(str(WR_DECAY))
_W_FLOOR = Fraction(str(WR_FLOOR))
# Bảng trọng số đầy đủ (cũ nhất -> mới nhất) - chỉ để hiển thị ở /health và khi khởi động
WR_WEIGHTS_FULL = [round(float(_W_FLOOR + (1 - _W_FLOOR) * _W_DECAY ** (WR_WINDOW - 1 - k)), 4) for k in range(WR_WINDOW)]

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

# ─── TỰ ĐỔI CƠ CHẾ KHI SAI 1 VÁN ─────────────────────────────────────────
#   FLIP_AUTO_DEFAULT = True  : đang ở cơ chế mặc định (bẻ hoặc theo final) mà sai 1 ván -> ván sau đổi sang cơ chế ngược lại,
#                               chạy xong 1 ván đổi thì về lại mặc định.
#   FLIP_AUTO_DEFAULT = False : tắt, luôn chạy đúng cơ chế mặc định (như bản cũ)
#   Đổi không cần sửa file:  SUNVIW_FLIP_AUTO=1|0  hoặc cờ  --no-auto-flip
FLIP_AUTO_DEFAULT = True
FLIP_AUTO = _env_bool("SUNVIW_FLIP_AUTO", FLIP_AUTO_DEFAULT)

# ─── ĐÁNH GIÁ ĐÚNG/SAI ───────────────────────────────────────────────────
EVAL_WINDOW = 100           # số phiên gần nhất để đánh giá đúng/sai (hiện thẳng trong /api/predict)
ICON_DUNG = "✅"            # icon hiện cho ván ĐOÁN ĐÚNG trong chuỗi "chuoi" của /api/predict
ICON_SAI = "❌"             # icon hiện cho ván ĐOÁN SAI

# ─── PERSISTENCE (lưu graded để Railway không mất sau restart) ───────────
PERSIST_PATH = os.environ.get("SUNVIW_PERSIST", "/tmp/sunviw_graded.json")
PERSIST_KEEP = max(EVAL_WINDOW, WR_WINDOW) + 20   # giữ tối đa N graded entry trong file (>= EVAL_WINDOW để cơ chế bẻ từng ván không bị tính lại)

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


def out_final(final, be=None):
    """Final đã đưa ra API: `be` = True -> bẻ (đảo) · False -> theo final · None -> dùng cơ chế mặc định FLIP_FINAL."""
    be = FLIP_FINAL if be is None else be
    return flip_pred(final) if be else final


def flip_cfg():
    """Dấu vân tay cấu hình bẻ (mặc định + tự đổi): đổi cấu hình thì `be` đã lưu của các ván cũ bị bỏ và tính lại."""
    return f"{int(FLIP_FINAL)}{int(FLIP_AUTO)}"


def next_flip(prev, session):
    """Cơ chế áp dụng cho ván `session`: True = BẺ final (đảo) · False = THEO final.
    `prev` = graded entry của ván liền trước (cần có be / pred / actual), None nếu chưa có.
      - tắt FLIP_AUTO, chưa có ván trước, hoặc ván trước không liền phiên -> mặc định
      - ván trước là ván ĐỔI (be khác mặc định)                        -> xong 1 ván đổi, VỀ mặc định
      - ván trước chạy mặc định mà SAI                                 -> ĐỔI sang cơ chế ngược lại
      - còn lại (ván trước chạy mặc định và ĐÚNG)                      -> giữ mặc định"""
    d = FLIP_FINAL
    if not FLIP_AUTO or prev is None or prev["session"] != session - 1:
        return d
    if prev["be"] != d:
        return d
    return (not d) if prev["pred"] != prev["actual"] else d


def assign_flip(graded, kept=None):
    """Gán cơ chế từng ván: g["be"] (True = bẻ), g["pred"] (du_doan thực tế đã đưa ra), g["cfg"].
    `kept` = {session: entry đã lưu} -> ván đã có `be` (cùng cấu hình) thì GIỮ NGUYÊN, không tính lại
    (tránh lệch pha khi lịch sử trượt hoặc sau restart). Ván mới -> tính từ ván liền trước theo next_flip()."""
    cfg = flip_cfg()
    prev = None
    for g in graded:
        k = kept.get(g["session"]) if kept else None
        if k is not None:
            g["be"], g["cfg"] = k["be"], cfg
        elif "be" not in g or g.get("cfg") != cfg:
            g["be"], g["cfg"] = next_flip(prev, g["session"]), cfg
        g["pred"] = out_final(g["final"], g["be"])
        prev = g
    return graded


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
def wr_weights(n):
    """Trọng số của n ván gần nhất, thứ tự cũ nhất -> mới nhất (kiểu Fraction = chính xác tuyệt đối khi so với 50%).
    trọng số(tuổi a) = WR_FLOOR + (1 - WR_FLOOR) * WR_DECAY ** a, a = 0 là ván mới nhất (= 1.00).
    Vd n=11, DECAY=0.75, FLOOR=0.35 -> [0.39, 0.40, 0.42, 0.44, 0.47, 0.50, 0.56, 0.62, 0.72, 0.84, 1.00]."""
    return [_W_FLOOR + (1 - _W_FLOOR) * _W_DECAY ** (n - 1 - k) for k in range(n)]


def wr_decision(votes, graded):
    """Giống wrDecision() trong HTML + thêm avg (độ tin cậy = TB WR của các logic đang dùng, 0-100).
    CHỈ KHÁC bản gốc ở chỗ WR có TRỌNG SỐ: ván mới nhất = 1.00, ván cũ giảm theo hàm mũ nhưng không thấp hơn
    WR_FLOOR (xem CONFIG WR CÓ TRỌNG SỐ). Cách chia nhóm / chọn nhóm / hoà phiếu giữ NGUYÊN như bản gốc."""
    all_vote = vote_result(votes)
    win = graded[-WR_WINDOW:]                         # cũ -> mới
    n = len(win)
    if n < WR_MIN_GAMES:
        return {"mode": "ALL", "n": n, "final": all_vote, "wins": [], "low": [], "high": [],
                "gT": 0, "gX": 0, "tie": False, "avg": None, "wsum": 0.0, "weights": []}
    weights = wr_weights(n)
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
    merged = merge_graded(seed, fresh)
    cfg = flip_cfg()
    kept = {g["session"]: g for g in seed if "be" in g and g.get("cfg") == cfg}   # cơ chế đã lưu của các ván cũ (cùng cấu hình)
    return assign_flip(merged, kept)


def build_result(hist):
    """Từ lịch sử (cũ -> mới) -> dict kết quả dự đoán cho phiên kế tiếp."""
    latest = hist[-1]
    saved = persist_load()
    graded = rebuild_graded(hist, saved_graded=saved)
    persist_save(graded)
    votes = compute_all(latest["phien"] + 1, latest["d1"], latest["d2"], latest["d3"])
    dec = wr_decision(votes, graded)
    be_next = next_flip(graded[-1] if graded else None, latest["phien"] + 1)   # cơ chế của ván sắp dự đoán
    base = {
        "ok": True,
        "phien": latest["phien"] + 1,
        "du_doan": out_final(dec["final"], be_next),
        "be_final": be_next,
        "be_mac_dinh": FLIP_FINAL,
        "doi_co_che": be_next != FLIP_FINAL,
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
            "van_moi_nhat": WR_WEIGHT_NEWEST,                     # trọng số ván mới nhất (x1.00)
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
    return {"base": base, "detail": detail}


def _recent_accuracy(graded, size, with_chuoi=False):
    """Đúng/sai của du_doan ĐÃ ĐƯA RA API (theo cơ chế bẻ/theo của TỪNG ván) ở `size` ván gần nhất."""
    win = graded[-size:]
    oks = [g["pred"] == g["actual"] for g in win]
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
             poll_sec=POLL_SEC, wr_window=WR_WINDOW, be_final=FLIP_FINAL, tu_doi_co_che=FLIP_AUTO,
             wr_weights=WR_WEIGHTS_FULL, wr_decay=WR_DECAY, wr_floor=WR_FLOOR)       # trọng số cũ nhất -> mới nhất
    return _json(s)


@app.route("/")
def index():
    return _json({"api": f"SUNVIW {len(LOGIC_NAMES)} logics (dedup={DEDUP_MODE})", "endpoints": ["/api/predict", "/api/predict?detail=1", "/health"]})


# Chạy dưới gunicorn (Railway) thì main() không được gọi -> bật poller ngay khi import.
if __name__ != "__main__":
    ensure_poller()


def main():
    global UPSTREAM_URL, POLL_SEC, FLIP_FINAL, FLIP_AUTO
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(description="SUNVIW 24 logics (mặc định 13) - API JSON")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=int(os.environ.get("PORT", 5000)))
    ap.add_argument("--upstream", default=UPSTREAM_URL, help="URL API phien moi nhat (…/api/tx)")
    ap.add_argument("--poll", type=float, default=POLL_SEC, help="chu ky quet upstream (giay)")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--flip", action="store_true", help="BẬT bẻ final (đảo TÀI<->XỈU)")
    g.add_argument("--no-flip", action="store_true", help="TẮT bẻ final (giữ nguyên final của các logic đang dùng)")
    ap.add_argument("--no-auto-flip", action="store_true", help="TẮT tự đổi bẻ/theo final khi sai 1 ván")
    a = ap.parse_args()
    UPSTREAM_URL, POLL_SEC = a.upstream, a.poll
    if a.flip:
        FLIP_FINAL = True
    elif a.no_flip:
        FLIP_FINAL = False
    if a.no_auto_flip:
        FLIP_AUTO = False
    ensure_poller()
    print(f"SUNVIW API  ->  http://{a.host}:{a.port}/api/predict")
    print(f"upstream    ->  {UPSTREAM_URL}")
    print(f"be final    ->  mac dinh {'BE' if FLIP_FINAL else 'THEO'} · tu doi co che khi sai: {'BAT' if FLIP_AUTO else 'TAT'}")
    print(f"WR          ->  xet {WR_WINDOW} van gan nhat, trong so (cu -> moi): "
          + " · ".join(f"{w:.2f}" for w in WR_WEIGHTS_FULL))
    app.run(host=a.host, port=a.port, threaded=True)


if __name__ == "__main__":
    main()
