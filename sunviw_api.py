# -*- coding: utf-8 -*-
"""
SUNVIW 24 LOGICS (mặc định chạy 13 logic) - API JSON  (bản Python của SUNVIW_21logics.html + thêm L3N, L4N, L5N)

Chạy:
    pip install flask websocket-client
    python sunviw_api.py                      # mặc định http://0.0.0.0:5000  (LC79: mở /api/html -> tab LC79 -> dán token -> Bật)
    python sunviw_api.py --port 8080 --upstream https://xxx.trycloudflare.com/api/tx
    python sunviw_api.py --flip               # BẬT bẻ final của SUN (mặc định TẮT; hoặc SUNVIW_FLIP=1, hoặc sửa FLIP_FINAL_DEFAULT)
    python sunviw_api.py --lc-flip            # BẬT bẻ final của LC79 (RIÊNG, không liên quan Sun; --lc-no-flip = tắt; hoặc LC79_FLIP=1|0, hoặc sửa LC_FLIP_FINAL_DEFAULT)
    python sunviw_api.py --wr-flip            # BẬT FLIP TRỌNG SỐ WR của SUN: ván CŨ nhất nặng nhất -> giảm dần tới ván MỚI nhất (--no-wr-flip = tắt; hoặc SUNVIW_WR_FLIP=1|0, hoặc sửa WR_FLIP_WEIGHT_DEFAULT)
    python sunviw_api.py --lc-wr-flip         # BẬT FLIP TRỌNG SỐ WR của LC79 (RIÊNG, độc lập Sun; --lc-no-wr-flip = tắt; hoặc LC79_WR_FLIP=1|0, hoặc sửa LC_WR_FLIP_WEIGHT_DEFAULT)
    python sunviw_api.py --zf-window 150      # ZF (SUN): SỐ VÁN gần nhất xét WR từng logic (--zf / --no-zf = bật/tắt ZF · --zf-z 2.0 = ngưỡng z · --zf-min 100 = số ván tối thiểu · --zf-flip / --zf-no-flip = bẻ riêng ZF)
                                              #           hoặc env SUNVIW_ZF / SUNVIW_ZF_WINDOW / SUNVIW_ZF_Z / SUNVIW_ZF_MIN / SUNVIW_ZF_FLIP / SUNVIW_ZF_EXCLUDE, hoặc sửa ZF_*_DEFAULT ở khối "CONFIG ZF"

Endpoint:
    GET /api/predictsun          -> [SUN] JSON dự đoán (đọc từ cache, trả về ngay). /api/predict = tên cũ, giữ để tool cũ không hỏng
    GET /api/predictsun?detail=1 -> thêm chi_tiet: vote từng logic + WR từng logic
    GET /api/predictlc79         -> [LC79] JSON dự đoán (nguồn = SOCKET), config RIÊNG (xem "CONFIG LC79"); cũng có ?detail=1
    GET /api/lc79/ws             -> trạng thái socket LC79 (không bao giờ trả token)
    POST /api/lc79/ws/start      -> gắn token + bật socket LC79: {"token":"...","url":"(tuỳ chọn)","auth":"(tuỳ chọn)"}; token rỗng = dùng token đã lưu
    POST /api/lc79/ws/stop       -> tắt socket LC79
    ...?hist=N                   -> (cả 2 game) thêm lich_su: N ván đúng/sai gần nhất, mới -> cũ
    GET /api/html                -> panel HTML theo dõi cả 2 game, đổi qua lại, chọn số ván lịch sử
    GET /health                  -> trạng thái nền của cả 2 game

JSON /api/predict:
    {
      "ok": true,
      "phien": 12346,            # phiên được dự đoán (n)
      "du_doan": "TÀI",          # TÀI | XỈU  (mặc định = final của các logic đang dùng; nếu BẬT bẻ final thì = đảo ngược final)
      "be_final": false,         # trạng thái bẻ final đang áp dụng (false = tắt, mặc định)
      "zf": true,                # true = final của ván này do ZF chốt · false = ZF chưa đủ điều kiện, đang dùng cách chốt cũ (be_final khi đó theo FLIP_FINAL)
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
🎯 ZF (Z-FILTER ĐỘNG) — cách chốt final MỚI của SUN (mặc định BẬT · chỉnh ở khối "CONFIG ZF" gần đầu file · LC79 giữ nguyên cách cũ):
    Mỗi ván lấy ZF_WINDOW ván gần nhất đã chấm (CHỈNH ĐƯỢC ở ZF_WINDOW_DEFAULT / env SUNVIW_ZF_WINDOW / cờ --zf-window), tính WR từng logic.
    Logic nào lệch khỏi 50% đủ mạnh (|z| >= ZF_Z) mới được bỏ phiếu:  WR > 50% -> THEO logic · WR < 50% -> ĐẢO logic.  Đa số phiếu = final.
    Không logic nào đủ mạnh / hoà phiếu / chưa đủ ZF_MIN_GAMES ván -> tự quay về cách chốt cũ (WR có trọng số + nhóm THẤP/CAO) và JSON có "zf": false.
    Ván do ZF chốt KHÔNG bị bẻ bởi FLIP_FINAL chung (ZF đã tự chọn hướng từng logic) — muốn bẻ riêng ZF dùng ZF_FLIP_FINAL. Ván quay về cách cũ vẫn bẻ theo FLIP_FINAL như trước.

Server quét upstream nền mỗi POLL_SEC giây, chỉ tính lại khi có phiên mới -> request của HTML trả về tức thì.
"""
import argparse
import collections
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
    "https://well-summary-oclc-invisible.trycloudflare.com/api/tx",
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
#
#   🔄 FLIP TRỌNG SỐ (WR_FLIP_WEIGHT_DEFAULT) — công tắc RIÊNG cho SUN (LC79 có công tắc riêng: LC_WR_FLIP_WEIGHT_DEFAULT):
#       False (mặc định) -> như trên: ván MỚI nhất nặng nhất, giảm dần về ván cũ nhất.
#       True             -> ĐẢO NGƯỢC bảng trọng số: ván CŨ nhất (trong WR_WINDOW) nặng nhất = WR_WEIGHT_NEWEST,
#                           giảm dần theo cùng công thức tới ván MỚI nhất (nhẹ nhất = tiến về WR_FLOOR).
#       Chỉ đảo thứ tự gán trọng số — DECAY / FLOOR / WEIGHT_NEWEST vẫn chỉnh như cũ (WEIGHT_NEWEST lúc này = trọng số CAO NHẤT).
#       Vd WINDOW=11 / DECAY=0.75 / FLOOR=0.35 / NEWEST=1.00, bật flip -> (cũ nhất -> mới nhất):
#           1.00 · 0.84 · 0.72 · 0.62 · 0.56 · 0.50 · 0.47 · 0.44 · 0.42 · 0.40 · 0.39
#       Muốn đổi mà không sửa file (ưu tiên: cờ dòng lệnh > biến môi trường > WR_FLIP_WEIGHT_DEFAULT):
#           biến môi trường :  SUNVIW_WR_FLIP=1 (bật) | SUNVIW_WR_FLIP=0 (tắt)
#           dòng lệnh       :  python sunviw_api.py --wr-flip  |  --no-wr-flip
#   Cách chia nhóm giữ nguyên: WR < 50% -> nhóm THẤP · WR ≥ 50% -> nhóm CAO, nhóm THẤP đông hơn thì theo nhóm THẤP,
#   còn lại theo nhóm CAO; nhóm được chọn hoà phiếu -> theo đa số tất cả logic.
WR_WINDOW = 13             # số ván gần nhất dùng để tính WR
WR_DECAY = 0.95           # tốc độ giảm trọng số khi ván cũ dần (nhỏ = phản ứng nhanh)
WR_FLOOR = 0.75            # sàn trọng số của ván cũ so với ván mới nhất (lớn = nhớ cầu cũ nhiều)
WR_WEIGHT_NEWEST = 1.4    # trọng số ván mới nhất (ĐÃ ÁP DỤNG vào tính WR; 1.00 = hành vi bản gốc)
# dạng Fraction để tính/so sánh chính xác (dùng trong wr_weights)
_W_DECAY = Fraction(str(WR_DECAY))
_W_FLOOR = Fraction(str(WR_FLOOR))
_W_NEWEST = Fraction(str(WR_WEIGHT_NEWEST))
WR_FLIP_WEIGHT_DEFAULT = False   # FLIP trọng số WR của SUN: True = ván CŨ nhất nặng nhất -> giảm dần tới ván MỚI nhất · False = ván mới nhất nặng nhất (mặc định)

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
WR_FLIP_WEIGHT = _env_bool("SUNVIW_WR_FLIP", WR_FLIP_WEIGHT_DEFAULT)      # flip trọng số WR của SUN (xem CONFIG WR CÓ TRỌNG SỐ)

# ─── ĐÁNH GIÁ ĐÚNG/SAI ───────────────────────────────────────────────────
EVAL_WINDOW = 100           # số phiên gần nhất để đánh giá đúng/sai (hiện thẳng trong /api/predict)
ICON_DUNG = "✅"            # icon hiện cho ván ĐOÁN ĐÚNG trong chuỗi "chuoi" của /api/predict
ICON_SAI = "❌"             # icon hiện cho ván ĐOÁN SAI

# ─── PERSISTENCE (lưu graded để Railway không mất sau restart) ───────────
PERSIST_PATH = os.environ.get("SUNVIW_PERSIST", "/tmp/sunviw_graded.json")
PERSIST_KEEP = 50          # giữ tối đa N graded entry trong file (>= WR_WINDOW đủ dùng)

# ═══════════════════════════════════════════════════════════════════════════
#  🎯  CONFIG ZF (Z-FILTER ĐỘNG) — CÁCH CHỐT FINAL CỦA SUN  —  CHỈNH Ở ĐÂY   (LC79 KHÔNG dùng ZF, giữ cách chốt cũ)
# ═══════════════════════════════════════════════════════════════════════════
#   Mỗi ván: lấy ZF_WINDOW ván GẦN NHẤT đã chấm, tính WR (đoán đúng / số ván) của TỪNG logic.
#   Logic nào lệch khỏi 50% đủ mạnh (|z| >= ZF_Z) mới được bỏ phiếu:
#       WR > 50%  -> THEO logic (logic đoán gì phiếu đó)          WR < 50% -> ĐẢO logic (logic đoán TÀI thì phiếu XỈU, và ngược lại)
#   z = (WR - 0.5) / (0.5 / sqrt(số ván xét)).  Vd 150 ván & ZF_Z = 2.0 -> chọn logic có WR >= 58.2% hoặc <= 41.8%.
#   Đa số phiếu của các logic được chọn = final.
#   Không logic nào được chọn / hoà phiếu / chưa đủ ZF_MIN_GAMES ván -> TỰ QUAY VỀ cách chốt cũ (WR có trọng số + nhóm THẤP/CAO),
#   JSON báo "zf": false để tool bên ngoài tự bỏ ván nếu muốn.
#
#   ZF_ENABLED_DEFAULT   True = dùng ZF · False = chỉ dùng cách chốt cũ
#   ZF_WINDOW_DEFAULT    SỐ VÁN gần nhất dùng để chấm WR từng logic (đã backtest 100 / 150 / 200; nhỏ = phản ứng nhanh nhưng nhiễu hơn)
#   ZF_Z_DEFAULT         ngưỡng z để logic được bỏ phiếu (1.5 = lỏng, nhiều logic hơn · 2.0 = mặc định · 2.5 = chặt, ít ván được chốt hơn)
#   ZF_MIN_GAMES_DEFAULT số ván đã chấm tối thiểu mới bật ZF (chưa đủ thì dùng cách cũ). Tự kẹp trong [10, ZF_WINDOW]. Chưa đủ ZF_WINDOW thì xét tất cả ván đang có.
#   ZF_FLIP_FINAL_DEFAULT bẻ riêng kết quả ZF (TÀI<->XỈU). Mặc định False: ZF đã tự chọn THEO/ĐẢO từng logic nên bẻ nữa là đảo ngược lại chính nó.
#                         FLIP_FINAL chung của SUN KHÔNG áp lên ván do ZF chốt (chỉ áp lên ván quay về cách cũ).
#   ZF_EXCLUDE_DEFAULT   logic KHÔNG cho bỏ phiếu trong ZF. ANTI-L7 luôn ngược L7 100% -> trong ZF cả hai cùng bỏ 1 phiếu giống nhau (L7 bị đếm đôi) nên loại ANTI-L7.
#   Lịch sử cần giữ >= cửa sổ ZF: HIST_KEEP / PERSIST_KEEP TỰ nới theo ZF_WINDOW (xem zf_apply_limits). Chạy trên Railway nên trỏ SUNVIW_HIST / SUNVIW_PERSIST vào ổ đĩa
#   bền, nếu không mỗi lần deploy /tmp bị xoá và ZF phải gom lại >= ZF_MIN_GAMES ván mới chạy.
#
#   Đổi mà không sửa file (ưu tiên: cờ dòng lệnh > biến môi trường > *_DEFAULT):
#       env  : SUNVIW_ZF=1|0 · SUNVIW_ZF_WINDOW=150 · SUNVIW_ZF_Z=2.0 · SUNVIW_ZF_MIN=100 · SUNVIW_ZF_FLIP=1|0 · SUNVIW_ZF_EXCLUDE="ANTI-L7,..." (rỗng = không loại)
#       lệnh : --zf / --no-zf · --zf-window N · --zf-z X · --zf-min N · --zf-flip / --zf-no-flip
ZF_ENABLED_DEFAULT = False
ZF_WINDOW_DEFAULT = 150
ZF_Z_DEFAULT = 2.0
ZF_MIN_GAMES_DEFAULT = 100
ZF_FLIP_FINAL_DEFAULT = False
ZF_EXCLUDE_DEFAULT = ("ANTI-L7",)


def _env_num(name, default, cast):
    v = os.environ.get(name, "").strip()
    if not v:
        return default
    try:
        return cast(v)
    except ValueError:
        return default


ZF_ENABLED = _env_bool("SUNVIW_ZF", ZF_ENABLED_DEFAULT)
ZF_WINDOW = _env_num("SUNVIW_ZF_WINDOW", ZF_WINDOW_DEFAULT, int)
ZF_Z = _env_num("SUNVIW_ZF_Z", ZF_Z_DEFAULT, float)
ZF_MIN_GAMES = _env_num("SUNVIW_ZF_MIN", ZF_MIN_GAMES_DEFAULT, int)
ZF_FLIP_FINAL = _env_bool("SUNVIW_ZF_FLIP", ZF_FLIP_FINAL_DEFAULT)
_zf_ex_env = os.environ.get("SUNVIW_ZF_EXCLUDE")
ZF_EXCLUDE = tuple(x.strip() for x in _zf_ex_env.split(",") if x.strip()) if _zf_ex_env is not None else tuple(ZF_EXCLUDE_DEFAULT)
_HIST_KEEP_BASE, _PERSIST_KEEP_BASE = HIST_KEEP, PERSIST_KEEP


def zf_apply_limits():
    """Chuẩn hoá tham số ZF + nới HIST_KEEP / PERSIST_KEEP đủ chứa cửa sổ ZF (gọi lúc import và sau khi đọc cờ dòng lệnh)."""
    global ZF_WINDOW, ZF_Z, ZF_MIN_GAMES, HIST_KEEP, PERSIST_KEEP
    ZF_WINDOW = max(10, int(ZF_WINDOW))
    ZF_Z = max(0.0, float(ZF_Z))
    ZF_MIN_GAMES = max(10, min(int(ZF_MIN_GAMES), ZF_WINDOW))
    HIST_KEEP = max(_HIST_KEEP_BASE, ZF_WINDOW * 2 + 10)
    PERSIST_KEEP = max(_PERSIST_KEEP_BASE, ZF_WINDOW + 10)


zf_apply_limits()


# ═══════════════════════════════════════════════════════════════════════════
#  ⚙  CONFIG LC79 (GAME 2)  —  RIÊNG HOÀN TOÀN, KHÔNG ẢNH HƯỞNG CONFIG SUN Ở TRÊN  —  CHỈNH Ở ĐÂY
# ═══════════════════════════════════════════════════════════════════════════
#   NGUỒN DỮ LIỆU LC79 = SOCKET (Engine.IO v4 / Socket.IO, namespace /txmd5) — thay cho API REST history cũ.
#   Token gắn ở panel /api/html (tab LC79) -> server tự kết nối, tự nối lại khi rớt, lần khởi động sau tự bật lại.
#   Bắt 2 event:
#       new-session    {id, md5}                                       -> vote NGAY phiên `id` bằng md5 của event (phiên KHÔNG +1) -> LƯU dự đoán
#       session-result {md5Raw:"<id>:...", dices:[a,b,c], resultTruyenThong} -> chấm đúng/sai phiên đó -> cập nhật WR
#   WR của LC xét LC_WR_WINDOW ván gần nhất ĐÃ CHẤM (dự đoán đã lưu + kết quả thật do socket trả).
#   Phiên mới đến mà kết quả phiên trước chưa về -> chờ tối đa LC_WAIT_RESULT_SEC giây để WR được cập nhật trước khi vote.
LC_WS_URL_DEFAULT = os.environ.get("LC79_WS_URL", "wss://wtxmd52.tele68.com/txmd5/?EIO=4&transport=websocket")
LC_WS_AUTH_DEFAULT = '40/txmd5,{"token":"{TOKEN}"}'   # mỗi dòng 1 khung · {TOKEN} = token · dòng 1 gửi ngay khi mở kết nối, các dòng sau gửi sau khi namespace connect
LC_WS_CFG_PATH = os.environ.get("LC79_WS_CFG", "/tmp/lc79_ws_cfg.json")   # file lưu token + URL + khung auth + cờ tự bật (quyền 600)
LC_WS_ORIGIN = os.environ.get("LC79_WS_ORIGIN", "")   # nếu server socket đòi Origin cụ thể thì đặt ở đây (mặc định để trống)
LC_WS_RETRY_BASE, LC_WS_RETRY_MAX = 2.0, 30.0         # nối lại: 2s, 4s, 8s ... tối đa 30s
LC_WAIT_RESULT_SEC = 4.0                              # chờ kết quả phiên trước tối đa N giây trước khi vote phiên mới
LC_WR_WINDOW = 17          # số ván gần nhất dùng để tính WR
LC_WR_DECAY = 0.95         # tốc độ giảm trọng số ván cũ (như WR_DECAY của Sun)
LC_WR_FLOOR = 0.35        # sàn trọng số ván cũ (như WR_FLOOR của Sun)
LC_WR_WEIGHT_NEWEST = 1.5  # trọng số ván mới nhất (như WR_WEIGHT_NEWEST của Sun; 1.00 = hành vi bản gốc)
LC_WR_MIN_GAMES = 1        # số ván tối thiểu để dùng WR
LC_WR_FLIP_WEIGHT_DEFAULT = True                 # FLIP trọng số WR của LC79 (RIÊNG, độc lập WR_FLIP_WEIGHT của Sun):
                                                   #   True  = ván CŨ nhất (trong LC_WR_WINDOW) nặng nhất = LC_WR_WEIGHT_NEWEST, giảm dần tới ván MỚI nhất
                                                   #   False = ván mới nhất nặng nhất, giảm dần về ván cũ nhất (mặc định)
                                                   # ưu tiên: cờ dòng lệnh --lc-wr-flip/--lc-no-wr-flip > env LC79_WR_FLIP=1|0 > giá trị này
LC_WR_FLIP_WEIGHT = _env_bool("LC79_WR_FLIP", LC_WR_FLIP_WEIGHT_DEFAULT)
LC_FLIP_FINAL_DEFAULT = False                      # bẻ final của LC79 (RIÊNG, độc lập FLIP_FINAL của Sun): True = bẻ · False = theo final gốc
                                                   # ưu tiên: cờ dòng lệnh --lc-flip/--lc-no-flip > env LC79_FLIP=1|0 > giá trị này
LC_FLIP_FINAL = _env_bool("LC79_FLIP", LC_FLIP_FINAL_DEFAULT)
LC_PRED_PATH = os.environ.get("LC79_PRED", "/tmp/lc79_preds.json")   # file lưu các dự đoán LC đã chấm / đang chờ (kèm vote từng logic để tính WR sau restart)
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


def compute_all_md5(session, md5):
    """Giống compute_all nhưng nhận THẲNG md5 (LC79: md5 lấy từ event new-session của socket, không tự dựng từ xúc xắc).
    Công thức y hệt compute_all — chỉ khác nguồn md5."""
    full = compute_all_full_md5(session, md5)
    return [full[i] for i in KEEP_IDX]


def compute_all_full(session, d1, d2, d3):
    """Đủ 24 vote (21 logic cũ + L3N, L4N, L5N) cho phiên `session` từ xúc xắc (d1,d2,d3) của phiên liền trước. Thứ tự = ALL_LOGIC_NAMES."""
    return compute_all_full_md5(session, md5_of(session, d1, d2, d3))


def compute_all_full_md5(session, md5):
    """Đủ 24 vote cho phiên `session` với md5 cho sẵn. Thứ tự = ALL_LOGIC_NAMES. (Công thức giữ nguyên 100% như bản gốc.)"""
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
def wr_weights(n, decay=None, floor=None, newest=None, flip=None):
    """Trọng số của n ván gần nhất, thứ tự cũ nhất -> mới nhất (kiểu Fraction = chính xác tuyệt đối khi so với 50%).
    Mặc định: trọng số(tuổi a) = WR_FLOOR + (WR_WEIGHT_NEWEST - WR_FLOOR) * WR_DECAY ** a, a = 0 là ván mới nhất (= WR_WEIGHT_NEWEST).
    Vd n=11, DECAY=0.75, FLOOR=0.35, NEWEST=1.00 -> [0.39, 0.40, 0.42, 0.44, 0.47, 0.50, 0.56, 0.62, 0.72, 0.84, 1.00].
    flip=True (WR_FLIP_WEIGHT) -> ĐẢO NGƯỢC bảng: ván CŨ nhất nặng nhất, giảm dần tới ván MỚI nhất
    -> [1.00, 0.84, 0.72, 0.62, 0.56, 0.50, 0.47, 0.44, 0.42, 0.40, 0.39]."""
    decay = _W_DECAY if decay is None else decay      # None -> config Sun; LC truyền config riêng
    floor = _W_FLOOR if floor is None else floor
    newest = _W_NEWEST if newest is None else newest
    flip = WR_FLIP_WEIGHT if flip is None else flip   # None -> công tắc flip của Sun; LC truyền công tắc riêng
    w = [floor + (newest - floor) * decay ** (n - 1 - k) for k in range(n)]
    return w[::-1] if flip else w


def wr_weights_full():
    """Bảng trọng số đầy đủ của SUN (cũ nhất -> mới nhất, đã tính flip nếu đang bật) - chỉ để hiển thị ở /health và khi khởi động."""
    return [round(float(w), 4) for w in wr_weights(WR_WINDOW)]


def wr_decision(votes, graded, window=None, decay=None, floor=None, min_games=None, newest=None, flip=None):
    """Giống wrDecision() trong HTML + thêm avg (độ tin cậy = TB WR của các logic đang dùng, 0-100).
    CHỈ KHÁC bản gốc ở chỗ WR có TRỌNG SỐ: ván mới nhất = WR_WEIGHT_NEWEST, ván cũ giảm theo hàm mũ nhưng không thấp hơn
    WR_FLOOR (xem CONFIG WR CÓ TRỌNG SỐ). Nếu flip bật thì đảo ngược: ván CŨ nhất nặng nhất -> giảm dần tới ván MỚI nhất.
    Cách chia nhóm / chọn nhóm / hoà phiếu giữ NGUYÊN như bản gốc."""
    all_vote = vote_result(votes)
    flip = WR_FLIP_WEIGHT if flip is None else flip        # None -> công tắc flip của Sun; LC truyền công tắc riêng
    window = WR_WINDOW if window is None else window        # None -> config Sun; LC truyền config riêng
    min_games = WR_MIN_GAMES if min_games is None else min_games
    win = graded[-window:]                            # cũ -> mới
    n = len(win)
    if n < min_games:
        return {"mode": "ALL", "n": n, "final": all_vote, "wins": [], "low": [], "high": [],
                "gT": 0, "gX": 0, "tie": False, "avg": None, "wsum": 0.0, "weights": [], "flip": flip}
    weights = wr_weights(n, decay, floor, newest, flip)
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
            "wsum": float(wsum), "weights": [float(w) for w in weights], "flip": flip}


def zf_decision(votes, graded, window=None, z_thr=None, min_games=None):
    """ZF (Z-filter động): chấm WR từng logic trên `window` ván đã chấm gần nhất, chỉ cho logic lệch 50% đủ mạnh (|z| >= z_thr) bỏ phiếu,
    WR > 50% -> THEO, WR < 50% -> ĐẢO, đa số phiếu = final. Trả dict luôn có khoá:
      active (True = ZF chốt được final) · reason (ok | chua_du_van | khong_logic_du_manh | hoa_phieu) · n (số ván đã xét) · final
      picks (chỉ số logic được chọn) · tai / xiu (số phiếu) · avg (TB WR theo hướng của các logic được chọn, 0-100) · per[i] = {wr, z, huong} hoặc None."""
    window = ZF_WINDOW if window is None else window
    z_thr = ZF_Z if z_thr is None else z_thr
    min_games = ZF_MIN_GAMES if min_games is None else min_games
    win = graded[-window:]
    n = len(win)
    need = max(1, min(min_games, window))
    out = {"active": False, "reason": "chua_du_van", "n": n, "final": None, "picks": [], "tai": 0, "xiu": 0,
           "avg": None, "per": [None] * len(votes), "need": need}
    if n < need:
        return out
    skip = {i for i, nm in enumerate(LOGIC_NAMES) if nm in ZF_EXCLUDE}
    half, root = n / 2.0, math.sqrt(n) / 2.0
    tai = xiu = 0
    picks, dir_wr = [], []
    for i, v in enumerate(votes):
        hit = sum(1 for g in win if g["votes"][i] == g["actual"])
        z = (hit - half) / root                      # = (WR - 0.5) / (0.5 / sqrt(n))
        huong = None
        if i not in skip and z != 0 and abs(z) + 1e-9 >= z_thr:
            huong = "THEO" if z > 0 else "ĐẢO"
            p = v if z > 0 else flip_pred(v)
            if p == TAI:
                tai += 1
            elif p == XIU:
                xiu += 1
            picks.append(i)
            dir_wr.append(hit / n if z > 0 else 1 - hit / n)
        out["per"][i] = {"wr": hit / n, "z": z, "huong": huong}
    out.update(picks=picks, tai=tai, xiu=xiu)
    if not picks:
        out["reason"] = "khong_logic_du_manh"
    elif tai == xiu:
        out["reason"] = "hoa_phieu"
    else:
        out.update(active=True, reason="ok", final=TAI if tai > xiu else XIU, avg=sum(dir_wr) / len(dir_wr) * 100)
    return out


def decide_final(votes, graded, dec_wr=None):
    """Chốt final của SUN: ZF nếu đủ điều kiện, không thì cách cũ (wr_decision). Trả (final, dùng_zf, zf, dec_wr).
    `dec_wr` truyền sẵn thì không tính lại wr_decision; chỉ tính khi thật sự cần quay về cách cũ."""
    zf = zf_decision(votes, graded) if ZF_ENABLED else None
    if zf is not None and zf["active"]:
        return zf["final"], True, zf, dec_wr
    if dec_wr is None:
        dec_wr = wr_decision(votes, graded)
    return dec_wr["final"], False, zf, dec_wr


def out_final_zf(final, used_zf):
    """Final SUN đã đưa ra API. Ván do ZF chốt: chỉ bẻ khi ZF_FLIP_FINAL bật (KHÔNG dính FLIP_FINAL chung — ZF đã tự chọn hướng từng logic).
    Ván quay về cách cũ: bẻ theo FLIP_FINAL như trước."""
    if used_zf:
        return flip_pred(final) if ZF_FLIP_FINAL else final
    return out_final(final)


def out_final_g(g):
    """Final đã đưa ra API của 1 ván đã chấm (entry cũ không có khoá 'zf' = ván chốt bằng cách cũ)."""
    return out_final_zf(g["final"], g.get("zf", False))


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
        final, used_zf, _zf, _wr = decide_final(votes, combined)          # ZF nếu đủ điều kiện, không thì cách cũ
        fresh.append({"session": nxt["phien"], "total": nxt["total"], "actual": nxt["actual"],
                      "votes": votes, "final": final, "ok": final == nxt["actual"], "zf": used_zf,
                      "sig": LOGIC_SIG})
    return merge_graded(seed, fresh)


def build_result(hist):
    """Từ lịch sử (cũ -> mới) -> dict kết quả dự đoán cho phiên kế tiếp."""
    latest = hist[-1]
    saved = persist_load()
    graded = rebuild_graded(hist, saved_graded=saved)
    persist_save(graded)
    votes = compute_all(latest["phien"] + 1, latest["d1"], latest["d2"], latest["d3"])
    dec = wr_decision(votes, graded)                                   # cách chốt cũ: luôn tính (phương án dự phòng + hiển thị WR cũ)
    final, used_zf, zf, _ = decide_final(votes, graded, dec)           # ZF nếu đủ điều kiện, không thì cách cũ
    avg = zf["avg"] if used_zf else dec["avg"]
    base = {
        "ok": True,
        "phien": latest["phien"] + 1,
        "du_doan": out_final_zf(final, used_zf),
        "be_final": ZF_FLIP_FINAL if used_zf else FLIP_FINAL,          # bẻ ĐANG ÁP DỤNG cho ván này (ZF chốt -> ZF_FLIP_FINAL · cách cũ -> FLIP_FINAL)
        "zf": used_zf,
        "do_tin_cay": None if avg is None else round(avg, 1),
        "phien_truoc": latest["phien"],
        "xuc_xac": [latest["d1"], latest["d2"], latest["d3"]],
        "tong": latest["total"],
        "ket_qua_truoc": latest["actual"],
        "so_van_wr": zf["n"] if used_zf else dec["n"],
        "tool_dung_sai_10_van": _recent_accuracy(graded, EVAL_WINDOW, with_chuoi=True),
    }
    tai = sum(1 for v in votes if v == TAI)
    detail = {
        "vote_21": {"TÀI": tai, "XỈU": len(votes) - tai},        # tên khóa giữ nguyên cho tương thích; giờ đếm trên các logic đang dùng
        "so_logic": len(votes),
        "che_do_loc_trung": DEDUP_MODE,
        "logic_bi_loai": [n for n in ALL_LOGIC_NAMES if n not in LOGIC_NAMES],
        "nhom_theo": "ZF (z-filter)" if used_zf else {"ALL": "da so", "LOW": "WR thap", "HIGH": "WR cao"}[dec["mode"]],
        "nhom_tai_xiu": {"TÀI": zf["tai"], "XỈU": zf["xiu"]} if used_zf else {"TÀI": dec["gT"], "XỈU": dec["gX"]},
        "hoa_dung_da_so_21": dec["tie"],
        "zf": {                                                    # ZF (z-filter động) — xem khối CONFIG ZF
            "bat": ZF_ENABLED,
            "dang_dung": used_zf,                                  # True = final ván này do ZF chốt · False = đang dùng cách cũ
            "ly_do": "tat" if zf is None else zf["reason"],        # ok | chua_du_van | khong_logic_du_manh | hoa_phieu | tat
            "cua_so": ZF_WINDOW,                                   # số ván cấu hình (ZF_WINDOW)
            "so_van_xet": 0 if zf is None else zf["n"],            # số ván thực tế đang xét (< cua_so khi lịch sử chưa đủ)
            "van_toi_thieu": ZF_MIN_GAMES,
            "nguong_z": ZF_Z,
            "logic_loai": [n for n in ZF_EXCLUDE if n in LOGIC_NAMES],
            "so_logic_chon": 0 if zf is None else len(zf["picks"]),
            "phieu": None if zf is None else {"TÀI": zf["tai"], "XỈU": zf["xiu"]},
            "be_final_zf": ZF_FLIP_FINAL,
        },
        "trong_so_wr": {                                          # cơ chế WR có trọng số (cách cũ / dự phòng)
            "so_van": dec["n"],
            "trong_so": dec["weights"],                           # cũ nhất -> mới nhất (đã tính flip nếu bật)
            "flip_trong_so": dec["flip"],                         # True = ván CŨ nhất nặng nhất -> giảm dần tới ván MỚI nhất
            "van_moi_nhat": WR_WEIGHT_NEWEST,                     # trọng số CAO NHẤT (WR_WEIGHT_NEWEST; gán cho ván mới nhất, hoặc ván cũ nhất nếu flip)
            "he_so_giam": WR_DECAY,                               # WR_DECAY: tốc độ quên ván cũ
            "san_trong_so": WR_FLOOR,                             # WR_FLOOR: sàn trọng số ván cũ
        },
        "logic": [
            {"ten": LOGIC_NAMES[i], "du_doan": votes[i],
             "wr": (round(dec["wins"][i] / dec["wsum"] * 100, 1) if dec["wins"] else None),       # WR có trọng số (cách cũ)
             "nhom": (None if not dec["wins"] else ("THAP" if i in dec["low"] else "CAO")),
             "zf_wr": (None if not zf or zf["per"][i] is None else round(zf["per"][i]["wr"] * 100, 1)),    # WR thường trên cửa sổ ZF
             "zf_z": (None if not zf or zf["per"][i] is None else round(zf["per"][i]["z"], 2)),
             "zf_huong": (None if not zf or zf["per"][i] is None else zf["per"][i]["huong"])}      # THEO | ĐẢO | None (không đủ mạnh / bị loại)
            for i in range(len(votes))
        ],
        "final_goc": final,                                       # final trước khi bẻ (của ZF nếu ZF chốt, không thì của cách cũ)
        "tool_dung_sai_15_van": _recent_accuracy(graded, WR_WINDOW),
    }
    hist_rows = [{"phien": g["session"], "du_doan": out_final_g(g), "ket_qua": g["actual"], "tong": g.get("total"),
                  "dung": out_final_g(g) == g["actual"], "zf": g.get("zf", False)} for g in reversed(graded[-HIST_MAX:])]   # mới -> cũ
    return {"base": base, "detail": detail, "hist": hist_rows}


def _recent_accuracy(graded, size, with_chuoi=False):
    """Đúng/sai của final ĐÃ ĐƯA RA API (sau bẻ nếu đang bật) ở `size` ván gần nhất."""
    win = graded[-size:]
    oks = [out_final_g(g) == g["actual"] for g in win]
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
    lc_ws_autostart()                             # LC79: nạp token đã lưu, lần trước đang bật thì tự bật lại socket


# ─── LC79 (GAME 2): SOCKET (new-session · session-result) · LƯU DỰ ĐOÁN · CHẤM ĐÚNG/SAI ───
# Dùng CHUNG công thức (compute_all_md5 = y hệt compute_all) với Sun, nhưng config / WR / lịch sử đúng-sai hoàn toàn RIÊNG (xem CONFIG LC79).
# Nguồn dữ liệu = WebSocket Engine.IO v4 / Socket.IO (namespace /txmd5) — port từ phần "TỰ ĐỘNG" của SUNVIW_11logics_wr13_auto_v12.html:
#   new-session    -> vote đúng phiên `id` bằng md5 của event (KHÔNG +1) rồi LƯU dự đoán
#   session-result -> chấm đúng/sai phiên đó, cập nhật WR + lịch sử
_LC_DECAY, _LC_FLOOR = Fraction(str(LC_WR_DECAY)), Fraction(str(LC_WR_FLOOR))
_LC_NEWEST = Fraction(str(LC_WR_WEIGHT_NEWEST))
_lc_preds = {}              # phien -> dự đoán đã LƯU (dung=None: đang chờ event session-result của phiên đó)
_lc_loaded = False
_lc_results = {}            # phien -> {"xuc_xac","tong","ket_qua"}: kết quả thật socket đã trả (chỉ giữ ~40 phiên gần nhất)
_lc_wait = {"p": None, "timer": None}   # phiên mới đang chờ kết quả phiên trước: p = (phien, md5)
_lc_state = {"target": None, "base": None, "detail": None, "error": None, "updated": None, "checked": None, "events": 0}
_lc_lock = threading.RLock()            # bảo vệ _lc_state + _lc_preds + _lc_results + _lc_wait + _ws (giữ ngắn)
_WS_UA = "Mozilla/5.0 (compatible; SUNVIW-API/1.0)"
_ws = {"wanted": False, "gen": 0, "sock": None, "status": "off", "text": "● Tắt", "retry": 0,
       "last_frame": 0.0, "ready_at": 0.0, "got_session": False, "warned": False, "ping_timeout": 50.0,
       "raw_budget": 0, "auth_queue": [], "auth_timer": None, "seen": set(),
       "token": "", "url": LC_WS_URL_DEFAULT, "auth": LC_WS_AUTH_DEFAULT, "booted": False}
_ws_log = collections.deque(maxlen=80)  # nhật ký socket (token luôn bị che thành {TOKEN})


def lc_out(final):
    """Final LC đã đưa ra API (sau bẻ nếu LC_FLIP_FINAL bật)."""
    return flip_pred(final) if LC_FLIP_FINAL else final


# ── tiện ích: log · trạng thái · lưu cấu hình token ─────────────────────
def _ws_say(msg):
    tok = _ws["token"]
    if tok:
        msg = str(msg).replace(tok, "{TOKEN}")
    _ws_log.append(f"{time.strftime('%H:%M:%S')} {msg}")


def _ws_set(kind, text):
    """kind: off | wait | ready | err (gọi trong _lc_lock)."""
    _ws["status"], _ws["text"] = kind, text


def _ws_cfg_save(auto):
    """Lưu token + URL + khung auth + cờ tự bật (quyền 600, ghi atomic). Gọi trong _lc_lock."""
    try:
        tmp = LC_WS_CFG_PATH + ".tmp"
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"token": _ws["token"], "url": _ws["url"], "auth": _ws["auth"], "auto": bool(auto)}, f, ensure_ascii=False)
        os.replace(tmp, LC_WS_CFG_PATH)
    except Exception:  # noqa: BLE001
        pass


def _ws_cfg_load():
    try:
        with open(LC_WS_CFG_PATH, "r", encoding="utf-8") as f:
            c = json.load(f)
        return c if isinstance(c, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


# ── lưu / nạp dự đoán ───────────────────────────────────────────────────
def _lc_load():
    """Nạp dự đoán đã lưu (1 lần). Gọi trong _lc_lock."""
    global _lc_loaded
    if _lc_loaded:
        return
    _lc_loaded = True
    try:
        with open(LC_PRED_PATH, "r", encoding="utf-8") as f:
            for r in json.load(f):
                if isinstance(r, dict) and "phien" in r and r.get("sig") == LOGIC_SIG:
                    _lc_preds[r["phien"]] = r
                    if r.get("ket_qua"):
                        _lc_results[r["phien"]] = {"xuc_xac": r.get("xuc_xac"), "tong": r.get("tong"), "ket_qua": r["ket_qua"]}
    except Exception:  # noqa: BLE001
        pass
    for k in sorted(_lc_results)[:-40]:
        del _lc_results[k]


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


def _lc_graded(before=None):
    """Các ván ĐÃ CHẤM (cũ -> mới) để tính WR: vote từng logic lúc dự đoán (đã lưu) + kết quả thật do socket trả.
    before = chỉ lấy các ván có phiên < before. Gọi trong _lc_lock."""
    n = len(LOGIC_NAMES)
    rows = [p for _, p in sorted(_lc_preds.items())
            if p.get("ket_qua") and isinstance(p.get("votes"), list) and len(p["votes"]) == n
            and (before is None or p["phien"] < before)]
    return [{"session": p["phien"], "actual": p["ket_qua"], "votes": p["votes"]} for p in rows][-LC_WR_WINDOW:]


def _lc_prev_fields(target):
    """Kết quả thật của phiên gần nhất TRƯỚC `target` (nếu socket đã trả) — để hiện ở phien_truoc / xuc_xac / tong / ket_qua_truoc."""
    ks = [k for k in _lc_results if k < target]
    if not ks:
        return {"phien_truoc": None, "xuc_xac": None, "tong": None, "ket_qua_truoc": None}
    k = max(ks)
    r = _lc_results[k]
    return {"phien_truoc": k, "xuc_xac": r.get("xuc_xac"), "tong": r.get("tong"), "ket_qua_truoc": r["ket_qua"]}


# ── EVENT 1: new-session -> vote + LƯU dự đoán ──────────────────────────
def _lc_vote(sid, md5):
    """Vote phiên `sid` (đúng id của event, không +1) bằng md5 của event, rồi LƯU dự đoán. Gọi trong _lc_lock.
    Phiên này đã có dự đoán LƯU sẵn (vd. server restart giữa ván, socket gửi lại phiên hiện tại) -> KHÔNG tính lại,
    chỉ dựng lại trạng thái API từ dự đoán đã lưu (du_doan luôn theo bản đã lưu)."""
    _lc_load()
    saved = _lc_preds.get(sid)
    if saved is not None and _lc_state["target"] == sid:
        return
    n_logic = len(LOGIC_NAMES)
    votes = saved["votes"] if saved is not None and isinstance(saved.get("votes"), list) and len(saved["votes"]) == n_logic \
        else compute_all_md5(sid, md5)
    dec = wr_decision(votes, _lc_graded(before=sid), LC_WR_WINDOW, _LC_DECAY, _LC_FLOOR, LC_WR_MIN_GAMES, _LC_NEWEST, LC_WR_FLIP_WEIGHT)
    tai = sum(1 for v in votes if v == TAI)
    base = {"ok": True, "game": "lc79", "phien": sid, "md5": md5, "du_doan": lc_out(dec["final"]), "be_final": LC_FLIP_FINAL,
            "do_tin_cay": None if dec["avg"] is None else round(dec["avg"], 1),
            "so_van_wr": dec["n"], "wr_window": LC_WR_WINDOW}
    detail = {
        "vote": {"TÀI": tai, "XỈU": len(votes) - tai}, "so_logic": len(votes),
        "nhom_theo": {"ALL": "da so", "LOW": "WR thap", "HIGH": "WR cao"}[dec["mode"]],
        "nhom_tai_xiu": {"TÀI": dec["gT"], "XỈU": dec["gX"]}, "hoa_dung_da_so": dec["tie"],
        "final_goc": dec["final"],
        "trong_so_wr": {"so_van": dec["n"], "trong_so": dec["weights"],
                        "flip_trong_so": dec["flip"],
                        "van_moi_nhat": LC_WR_WEIGHT_NEWEST,
                        "he_so_giam": LC_WR_DECAY, "san_trong_so": LC_WR_FLOOR},
        "logic": [{"ten": LOGIC_NAMES[i], "du_doan": votes[i],
                   "wr": (round(dec["wins"][i] / dec["wsum"] * 100, 1) if dec["wins"] else None),
                   "nhom": (None if not dec["wins"] else ("THAP" if i in dec["low"] else "CAO"))}
                  for i in range(len(votes))],
    }
    if saved is None:                                    # LƯU dự đoán đúng 1 lần cho phiên này (không tính lại dù config đổi)
        _lc_preds[sid] = {"phien": sid, "md5": md5, "du_doan": base["du_doan"], "final_goc": dec["final"],
                          "be_final": LC_FLIP_FINAL, "so_van_wr": dec["n"], "votes": votes, "dung": None,
                          "sig": LOGIC_SIG, "luc": _now()}
        for k in sorted(_lc_preds)[:-LC_PRED_KEEP]:
            del _lc_preds[k]
        _lc_save()
    base["du_doan"] = _lc_preds[sid]["du_doan"]          # luôn theo dự đoán ĐÃ LƯU
    base["be_final"] = _lc_preds[sid]["be_final"]
    _lc_state.update(target=sid, base=base, detail=detail, updated=_now(), error=None)
    _ws_say(f"✔ vote phiên {sid} → {base['du_doan']}" if saved is None else f"✔ nạp lại dự đoán đã lưu phiên {sid} → {base['du_doan']}")
    if _ws["wanted"]:                                   # đã tắt / bị từ chối thì giữ nguyên trạng thái
        _ws_set("ready", f"● Đang chạy · phiên {sid} → {base['du_doan']}")


def _lc_flush_pending():
    """Vote phiên đang chờ (nếu có): gọi khi kết quả phiên trước về, hết LC_WAIT_RESULT_SEC, hoặc có phiên mới hơn đến."""
    with _lc_lock:
        t = _lc_wait["timer"]
        _lc_wait["timer"] = None
        if t is not None:
            t.cancel()
        p = _lc_wait["p"]
        _lc_wait["p"] = None
        if p is not None:
            try:
                _lc_vote(p[0], p[1])
            except Exception as e:  # noqa: BLE001
                _ws_say(f"✖ lỗi vote phiên {p[0]}: {type(e).__name__}: {e}")


def _lc_on_new_session(d):
    sid = _parse_int(d.get("id"))
    md5 = str(d.get("md5") or "").strip().lower()
    if sid is None or not re.fullmatch(r"[0-9a-f]{32}", md5):
        _ws_say("? new-session thiếu id/md5")
        return
    with _lc_lock:
        _lc_load()
        _ws["got_session"] = True
        _lc_state["events"] += 1
        _lc_state["checked"] = _now()
        if _lc_wait["p"] is not None:                    # phiên cũ đang chờ thì vote nốt
            _lc_flush_pending()
        if sid in _lc_preds:
            if _lc_state["target"] == sid:
                _ws_say(f"bỏ qua phiên trùng {sid}")
            else:
                _lc_vote(sid, md5)                       # đã có dự đoán lưu (restart giữa ván) -> nạp lại, không chờ, không tính lại
            return
        last = _lc_preds[max(_lc_preds)] if _lc_preds else None
        if last is not None and last.get("dung") is None:
            # kết quả phiên trước có thể đến chậm hơn vài giây -> chờ để WR được cập nhật trước khi vote
            _lc_wait["p"] = (sid, md5)
            t = threading.Timer(LC_WAIT_RESULT_SEC, _lc_flush_pending)
            t.daemon = True
            _lc_wait["timer"] = t
            t.start()
            _ws_say(f"phiên {sid}: chờ kết quả phiên {last['phien']} (tối đa {LC_WAIT_RESULT_SEC:g}s)")
            return
        _lc_vote(sid, md5)


# ── EVENT 2: session-result -> chấm ĐÚNG/SAI ────────────────────────────
def _lc_on_result(d):
    m = re.match(r"^(\d+):", str(d.get("md5Raw") or ""))
    sid = int(m.group(1)) if m else None
    dices = None
    raw = d.get("dices")
    if isinstance(raw, list) and len(raw) == 3:
        dd = [_parse_int(x) for x in raw]
        if None not in dd and all(1 <= x <= 6 for x in dd):
            dices = dd
    res = norm_kq(d.get("resultTruyenThong"))
    if not res and dices:
        res = actual_of(sum(dices))
    if sid is None or not res:
        _ws_say("? session-result thiếu dữ liệu")
        return
    total = sum(dices) if dices else None
    with _lc_lock:
        _lc_load()
        _lc_state["events"] += 1
        _lc_state["checked"] = _now()
        _lc_results[sid] = {"xuc_xac": dices, "tong": total, "ket_qua": res}
        for k in sorted(_lc_results)[:-40]:
            del _lc_results[k]
        p = _lc_preds.get(sid)
        dtxt = f" ({'-'.join(map(str, dices))})" if dices else ""
        if p is None:
            _ws_say(f"kết quả phiên {sid}: {res}{dtxt} (tool chưa có dự đoán phiên này)")
        else:
            p.update(ket_qua=res, tong=total, xuc_xac=dices, dung=(p["du_doan"] == res), cham=_now())
            _lc_save()
            _ws_say(f"✔ kết quả phiên {sid}: {res}{dtxt} → {'ĐÚNG' if p['dung'] else 'SAI'}")
        if _lc_wait["p"] is not None:                    # đã có kết quả của ván mới nhất -> vote phiên đang chờ
            last = _lc_preds[max(_lc_preds)] if _lc_preds else None
            if last is None or last.get("dung") is not None:
                _lc_flush_pending()


def _lc_on_event(name, data):
    try:
        if name == "new-session" and isinstance(data, dict):
            _lc_on_new_session(data)
            return
        if name == "session-result" and isinstance(data, dict):
            _lc_on_result(data)
            return
    except Exception as e:  # noqa: BLE001 - 1 event lỗi không được làm sập luồng socket
        _ws_say(f"✖ lỗi xử lý event {name}: {type(e).__name__}: {e}")
        return
    with _lc_lock:
        if name not in _ws["seen"]:
            _ws["seen"].add(name)
            _ws_say(f"· event bỏ qua: {name}")


# ── SOCKET: Engine.IO v4 ('0' open · '1' close · '2' ping · '3' pong · '4' message) ───
def _ws_alive(gen):
    with _lc_lock:
        return _ws["wanted"] and _ws["gen"] == gen


def _ws_send(app, frame):
    try:
        app.send(frame)
        return True
    except Exception:  # noqa: BLE001
        return False


def _ws_send_auth(app):
    with _lc_lock:
        token = _ws["token"]
        lines = [x.strip() for x in _ws["auth"].split("\n") if x.strip()]
        first = lines[0] if lines else "40/txmd5,"
        _ws["auth_queue"] = lines[1:]
        old = _ws["auth_timer"]
        _ws["auth_timer"] = None
    if old is not None:
        old.cancel()
    _ws_send(app, first.replace("{TOKEN}", token))
    _ws_say("→ " + first)
    if lines[1:]:                                       # phòng khi không thấy ack connect của namespace
        t = threading.Timer(2.5, _ws_flush_auth, args=(app,))
        t.daemon = True
        with _lc_lock:
            _ws["auth_timer"] = t
        t.start()


def _ws_flush_auth(app):
    with _lc_lock:
        token = _ws["token"]
        queue, _ws["auth_queue"] = _ws["auth_queue"], []
    for line in queue:
        _ws_send(app, line.replace("{TOKEN}", token))
        _ws_say("→ " + line)


def _ws_frame(app, f):
    with _lc_lock:
        if _ws["raw_budget"] > 0:
            _ws["raw_budget"] -= 1
            _ws_say("← " + f[:140])
    if f == "2":                                        # server ping -> client pong
        _ws_send(app, "3")
        return
    if f == "3":
        return
    t = f[:1]
    if t == "0":
        try:
            o = json.loads(f[1:])
        except ValueError:
            o = {}
        if isinstance(o, dict) and o.get("pingInterval") and o.get("pingTimeout"):
            with _lc_lock:
                _ws["ping_timeout"] = (o["pingInterval"] + o["pingTimeout"]) / 1000.0 + 5
        _ws_send_auth(app)
        return
    if t == "1":
        _ws_say("Server gửi lệnh đóng")
        return
    if t == "4":
        _ws_sio(app, f[1:])


# Socket.IO: '0' CONNECT · '1' DISCONNECT · '2' EVENT · '4' CONNECT_ERROR
def _ws_sio(app, s):
    t = s[:1]
    rest, ns = s[1:], "/"
    if rest[:1] == "/":
        i = rest.find(",")
        if i < 0:
            ns, rest = rest, ""
        else:
            ns, rest = rest[:i], rest[i + 1:]
    if t == "0":
        with _lc_lock:
            tm = _ws["auth_timer"]
            _ws["auth_timer"] = None
        if tm is not None:
            tm.cancel()
        _ws_flush_auth(app)
        with _lc_lock:
            _ws["ready_at"] = time.time()
            _ws["retry"] = 0
            _lc_state["error"] = None
            _ws_set("ready", "● Đã kết nối — chờ phiên mới…")
        _ws_say("✔ Socket.IO connect " + ns)
        return
    if t == "4":
        _ws_say("✖ Server từ chối: " + rest[:160])
        with _lc_lock:
            _ws["wanted"] = False
            _ws["gen"] += 1
            _ws["auth_queue"] = []
            _ws["sock"] = None
            _lc_state["error"] = "socket bi server tu choi (token het han / sai khung auth?)"
            _ws_set("err", "● Server từ chối (token hết hạn / sai khung auth?)")
            _ws_cfg_save(False)
        try:
            app.close()
        except Exception:  # noqa: BLE001
            pass
        return
    if t == "1":
        _ws_say("Server ngắt namespace " + ns)
        return
    if t == "2":
        m = re.match(r"^(\d+)?(\[[\s\S]*\])$", rest)
        if not m:
            _ws_say("? event lạ: " + rest[:100])
            return
        try:
            arr = json.loads(m.group(2))
        except ValueError:
            _ws_say("? JSON lỗi")
            return
        if isinstance(arr, list) and arr:
            _lc_on_event(arr[0], arr[1] if len(arr) > 1 else None)


def _ws_watch(gen, app):
    """Giám sát kết nối: lâu không nhận khung nào -> đóng để nối lại · 25s sau connect mà chưa có phiên nào -> cảnh báo."""
    while True:
        for _ in range(10):
            time.sleep(0.5)
            if not _ws_alive(gen) or app is not _ws["sock"]:
                return
        now = time.time()
        with _lc_lock:
            idle_too_long = now - _ws["last_frame"] > _ws["ping_timeout"]
            warn = bool(_ws["ready_at"]) and not _ws["got_session"] and not _ws["warned"] and now - _ws["ready_at"] > 25
            if warn:
                _ws["warned"] = True
                _ws_set("err", "● Đã kết nối nhưng chưa có phiên — kiểm tra auth")
        if idle_too_long:
            _ws_say("✖ Quá lâu không nhận khung nào — kết nối lại")
            try:
                app.close()
            except Exception:  # noqa: BLE001
                pass
            return
        if warn:
            _ws_say("⚠ 25s chưa nhận phiên nào — kiểm tra token / khung auth")


def _ws_session(gen, websocket):
    """Mở 1 kết nối, chạy tới khi đóng (chặn luồng). Vòng nối lại nằm ở _ws_run."""
    with _lc_lock:
        url = _ws["url"]
        _ws.update(last_frame=time.time(), ready_at=0.0, got_session=False, warned=False,
                   raw_budget=15, ping_timeout=50.0, auth_queue=[])
        _ws_set("wait", "● Đang kết nối…")
    _ws_say("→ kết nối " + url)

    def on_open(app):
        if app is _ws["sock"]:
            _ws_say("✔ WebSocket đã mở")

    def on_message(app, msg):
        if app is not _ws["sock"] or not isinstance(msg, str):
            return
        _ws["last_frame"] = time.time()
        try:
            _ws_frame(app, msg)
        except Exception as e:  # noqa: BLE001
            _ws_say(f"✖ lỗi xử lý khung: {type(e).__name__}: {e}")

    def on_error(app, err):
        if app is _ws["sock"]:
            _ws_say(f"✖ WebSocket lỗi: {err} (server từ chối Origin / mạng / URL sai)")

    def on_close(app, code, reason):
        if app is _ws["sock"]:
            _ws_say(f"✖ WebSocket đóng (code {code}{': ' + str(reason) if reason else ''})")

    app = websocket.WebSocketApp(url, header=[f"User-Agent: {_WS_UA}"], on_open=on_open,
                                 on_message=on_message, on_error=on_error, on_close=on_close)
    with _lc_lock:
        if not (_ws["wanted"] and _ws["gen"] == gen):
            return
        _ws["sock"] = app
    threading.Thread(target=_ws_watch, args=(gen, app), daemon=True, name="lc79-socket-watch").start()
    try:
        app.run_forever(origin=LC_WS_ORIGIN or None)
    finally:
        with _lc_lock:
            same = app is _ws["sock"]
            if same:
                _ws["sock"] = None
                _ws["auth_queue"] = []
                if _ws["wanted"] and _ws["gen"] == gen:
                    _lc_state["error"] = "socket mat ket noi"
            tm = _ws["auth_timer"] if same else None
            if same:
                _ws["auth_timer"] = None
        if tm is not None:
            tm.cancel()


def _ws_run(gen):
    """Luồng quản lý socket: kết nối -> rớt thì chờ 2s, 4s, 8s ... (tối đa 30s) rồi nối lại, tới khi bị tắt / bị từ chối."""
    try:
        import websocket  # pip install websocket-client
    except ImportError:
        with _lc_lock:
            _ws["wanted"] = False
            _ws_set("err", "● Thiếu thư viện websocket-client")
            _lc_state["error"] = "thieu thu vien websocket-client (pip install websocket-client)"
        _ws_say("✖ Thiếu thư viện: pip install websocket-client")
        return
    while _ws_alive(gen):
        try:
            _ws_session(gen, websocket)
        except Exception as e:  # noqa: BLE001
            _ws_say(f"✖ lỗi socket: {type(e).__name__}: {e}")
        if not _ws_alive(gen):
            return
        with _lc_lock:
            d = min(LC_WS_RETRY_BASE * (2 ** min(_ws["retry"], 10)), LC_WS_RETRY_MAX)
            _ws["retry"] += 1
            _ws_set("wait", f"● Mất kết nối — thử lại sau {round(d)}s")
        waited = 0.0
        while waited < d and _ws_alive(gen):
            time.sleep(0.25)
            waited += 0.25


def _ws_close_sock():
    with _lc_lock:
        app, _ws["sock"] = _ws["sock"], None
        tm, _ws["auth_timer"] = _ws["auth_timer"], None
        _ws["auth_queue"] = []
    if tm is not None:
        tm.cancel()
    if app is not None:
        try:
            app.close()
        except Exception:  # noqa: BLE001
            pass


def lc_ws_start(token=None, url=None, auth=None):
    """Bật socket LC79. token rỗng -> dùng token đã lưu. Ném ValueError nếu chưa có token."""
    with _lc_lock:
        t = (token or "").strip() or _ws["token"]
        if not t:
            raise ValueError("chua co token — dan token vao o Token roi bam Bat")
        _ws["token"] = t
        if url and url.strip():
            _ws["url"] = url.strip()
        if auth and auth.strip():
            _ws["auth"] = auth
        _ws_cfg_save(True)
        _ws["wanted"] = True
        _ws["gen"] += 1
        _ws["retry"] = 0
        gen = _ws["gen"]
    _ws_close_sock()
    threading.Thread(target=_ws_run, args=(gen,), daemon=True, name="lc79-socket").start()


def lc_ws_stop():
    """Tắt socket LC79 (giữ token đã lưu, lần khởi động sau KHÔNG tự bật lại)."""
    with _lc_lock:
        _ws["wanted"] = False
        _ws["gen"] += 1
        tm, _lc_wait["timer"] = _lc_wait["timer"], None
        _lc_wait["p"] = None
        _lc_state["error"] = "socket da tat"
        _ws_set("off", "● Tắt")
        _ws_cfg_save(False)
    if tm is not None:
        tm.cancel()
    _ws_close_sock()
    _ws_say("■ Đã tắt tự động")


def lc_ws_autostart():
    """Khởi động server: nạp token đã lưu; lần trước đang bật tự động thì tự bật lại (chỉ chạy 1 lần)."""
    with _lc_lock:
        if _ws["booted"]:
            return
        _ws["booted"] = True
        c = _ws_cfg_load()
        _ws["token"] = str(c.get("token") or "")
        if c.get("url"):
            _ws["url"] = str(c["url"])
        if c.get("auth"):
            _ws["auth"] = str(c["auth"])
        auto = bool(c.get("auto")) and bool(_ws["token"])
        _lc_load()
    if auto:
        lc_ws_start()


def lc_ws_status():
    """Trạng thái socket cho panel / health. KHÔNG bao giờ trả token (url/khung auth cũng bị che nếu có chứa token)."""
    with _lc_lock:
        tok = _ws["token"]
        mask = (lambda x: x.replace(tok, "{TOKEN}")) if tok else (lambda x: x)
        return {"ok": True, "status": _ws["status"], "text": _ws["text"], "wanted": _ws["wanted"],
                "has_token": bool(tok), "url": mask(_ws["url"]), "auth": mask(_ws["auth"]),
                "events": _lc_state["events"], "log": list(_ws_log)}


def lc_history():
    """Các ván LC đã chấm đúng/sai, mới -> cũ."""
    with _lc_lock:
        _lc_load()
        rows = [p for _, p in sorted(_lc_preds.items(), reverse=True) if p.get("dung") is not None]
    return [{"phien": p["phien"], "du_doan": p["du_doan"], "ket_qua": p["ket_qua"], "tong": p.get("tong"), "dung": p["dung"]}
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
.ws{background:var(--pn);border:1px solid var(--ln);border-radius:12px;margin-bottom:12px}
.ws>summary{cursor:pointer;padding:10px 14px;list-style:none;display:flex;justify-content:space-between;align-items:center;gap:8px;font-weight:600}
.ws>summary::-webkit-details-marker{display:none}
.ws-b{padding:0 14px 14px}
.ws label{display:block;margin:10px 0 4px}
.ws input,.ws textarea{width:100%;background:#0f1424;border:1px solid var(--ln);color:var(--tx);border-radius:8px;padding:9px 10px;font:13px/1.4 ui-monospace,Consolas,monospace}
.ws textarea{height:56px;resize:vertical}
.ws .row{display:flex;gap:8px;margin-top:10px}
.ws .row button{flex:1;border-radius:8px;padding:9px 10px;font:inherit;font-weight:600;cursor:pointer;border:1px solid var(--ln);background:none;color:var(--tx)}
.ws .row .go{background:var(--ok);border-color:var(--ok);color:#0f1424}
.ws pre{margin:0;padding:8px;background:#0b0f1d;border:1px solid var(--ln);border-radius:6px;max-height:160px;overflow:auto;font-size:11.5px;white-space:pre-wrap;word-break:break-all;color:var(--mu)}
.st-off{color:var(--mu)}.st-wait{color:#ffb020}.st-ready{color:var(--ok)}.st-err{color:var(--no)}
[hidden]{display:none!important}
@media(max-width:480px){.hero{grid-template-columns:1fr}.prev{text-align:left}}
</style></head><body>
<header><h1>SUNVIW · Tài Xỉu</h1><div id="st"></div></header>
<nav class="tabs" id="tabs"></nav>
<details class="ws" id="ws" hidden>
  <summary><span>🔑 Socket LC79 · gắn token</span><span id="wsSt" class="st-off">● Tắt</span></summary>
  <div class="ws-b">
    <label class="mu" for="wsTok">Token đăng nhập</label>
    <input id="wsTok" type="password" autocomplete="off" spellcheck="false" placeholder="Dán token đăng nhập vào đây...">
    <div class="row"><button class="go" id="wsGo">▶ Bật tự động</button><button id="wsOff">■ Tắt</button></div>
    <div class="mu" id="wsHint" style="margin-top:8px"></div>
    <details style="margin-top:10px">
      <summary class="mu" style="cursor:pointer">⚙ Nâng cao (URL · khung auth · nhật ký)</summary>
      <label class="mu" for="wsUrl">URL WebSocket</label>
      <input id="wsUrl" type="text" spellcheck="false">
      <label class="mu" for="wsAuth">Khung gửi khi kết nối — mỗi dòng 1 khung, {TOKEN} = token. Dòng 1 gửi ngay khi mở kết nối, các dòng sau gửi sau khi namespace connect:</label>
      <textarea id="wsAuth" spellcheck="false"></textarea>
      <label class="mu">Nhật ký socket</label>
      <pre id="wsLog"></pre>
    </details>
  </div>
</details>
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
const prevHtml=d=>d.phien_truoc==null?'<div class="mu">Chưa có kết quả phiên trước</div>':`<div class="mu">Phiên ${d.phien_truoc}</div>${d.xuc_xac?dice(d.xuc_xac):''}<div>${d.tong==null?'':`<b>${d.tong}</b> `}<span class="${cl(d.ket_qua_truoc)}">${d.ket_qua_truoc}</span></div>`;
const acc=d=>{const h=d.lich_su||[],k=h.filter(x=>x.dung).length;return{k,t:h.length,p:h.length?Math.round(k*100/h.length):null}};
function render(){
  $('#ws').hidden=cur!=='lc';
  $('#tabs').innerHTML=Object.entries(G).map(([k,g])=>{const d=D[k]||{},a=acc(d);
    return `<button class="tab${k===cur?' on':''}" data-g="${k}"><span>${g.n} <b class="${cl(d.du_doan)}">${d.ok?d.du_doan:'…'}</b></span><small>${a.p===null?'–':a.p+'%'}</small></button>`}).join('');
  const d=D[cur]||{},a=acc(d);
  if(!d.ok){$('#main').innerHTML=`<div class="hero"><div class="mu">${esc(d.loi||'Đang tải…')}</div></div>`;$('#hist').innerHTML='';return}
  $('#main').innerHTML=`<section class="hero"><div><div class="mu">Dự đoán phiên ${d.phien}</div><div class="big ${cl(d.du_doan)}">${d.du_doan}</div><div class="mu">Độ tin cậy ${d.do_tin_cay==null?'–':d.do_tin_cay+'%'}${d.be_final?' · đã bẻ final':''} · xét ${d.so_van_wr} ván</div></div><div class="prev">${prevHtml(d)}</div></section><div class="stats"><span><b class="okc">${a.k}</b> <span class="mu">đúng</span></span><span><b class="noc">${a.t-a.k}</b> <span class="mu">sai</span></span><span><b>${a.p===null?'–':a.p+'%'}</b> <span class="mu">trên ${a.t} ván</span></span></div>`;
  const h=d.lich_su||[];
  $('#hist').innerHTML=h.length?`<div class="strip">${h.map(x=>`<span class="chip ${x.dung?'ok':'no'}" title="#${x.phien}">${x.dung?'✓':'✗'}</span>`).join('')}</div><table><tr><th>Phiên</th><th>Dự đoán</th><th>Kết quả</th><th class="r">Đúng/sai</th></tr>${h.map(x=>`<tr><td>#${x.phien}</td><td class="${cl(x.du_doan)}">${x.du_doan}</td><td class="${cl(x.ket_qua)}">${x.ket_qua}${x.tong==null?'':` <span class="mu">(${x.tong})</span>`}</td><td class="r ${x.dung?'okc':'noc'}">${x.dung?'Đúng':'Sai'}</td></tr>`).join('')}</table>`:`<p class="mu">Chưa có ván nào được chấm. Tool lưu dự đoán rồi chờ kết quả phiên đó (Sun: API · LC79: event session-result của socket).</p>`;
  $('#st').className=Object.values(D).some(x=>x&&(!x.ok||x.stale))?'bad':'';
  $('#st').innerHTML=`<i></i>${esc(d.cap_nhat||'')}`;
}
$('#tabs').onclick=e=>{const b=e.target.closest('[data-g]');if(b){cur=b.dataset.g;localStorage.setItem('g',cur);render()}};
$('#n').value=N;
function setN(v){N=Math.max(1,Math.min(+v||1,__MAX__));$('#n').value=N;localStorage.setItem('n',N);load()}
$('#n').onchange=e=>setN(e.target.value);
document.querySelectorAll('[data-n]').forEach(b=>b.onclick=()=>setN(b.dataset.n));
let W=null,wsInit=false;
const wsCls={off:'st-off',wait:'st-wait',ready:'st-ready',err:'st-err'};
function wsRender(){
  if(!W)return;
  const box=$('#ws');
  $('#wsSt').className=wsCls[W.status]||'st-off';$('#wsSt').textContent=W.text||'';
  if(!wsInit){wsInit=true;$('#wsUrl').value=W.url||'';$('#wsAuth').value=W.auth||'';box.open=!W.has_token||W.status==='err'}
  $('#wsTok').placeholder=W.has_token?'Đã lưu token trên server — để trống nếu muốn dùng lại':'Dán token đăng nhập vào đây...';
  $('#wsHint').textContent=W.has_token?'Token đã lưu trên server (không hiển thị lại).':'Chưa có token — dán token rồi bấm Bật tự động.';
  const lg=$('#wsLog'),end=lg.scrollTop+lg.clientHeight>=lg.scrollHeight-4;
  lg.textContent=(W.log||[]).join('\n');if(end)lg.scrollTop=lg.scrollHeight;
}
async function wsLoad(){
  try{const r=await fetch('/api/lc79/ws',{cache:'no-store'});W=await r.json()}catch(e){}
  wsRender();
}
$('#wsGo').onclick=async()=>{
  const t=$('#wsTok').value.trim();
  if(!t&&!(W&&W.has_token)){alert('Dán token đăng nhập vào ô Token trước!');return}
  try{
    const r=await fetch('/api/lc79/ws/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token:t,url:$('#wsUrl').value,auth:$('#wsAuth').value})});
    const j=await r.json().catch(()=>({}));
    if(!r.ok||j.ok===false){alert(j.loi||'Không bật được socket');return}
    $('#wsTok').value='';
  }catch(e){alert('Mất kết nối: '+e);return}
  wsLoad();load();
};
$('#wsOff').onclick=async()=>{try{await fetch('/api/lc79/ws/stop',{method:'POST'})}catch(e){}wsLoad()};
async function load(){
  await Promise.all([wsLoad(),...Object.entries(G).map(async([k,g])=>{
    try{const r=await fetch(`${g.u}?hist=${N}`,{cache:'no-store'});D[k]=await r.json()}
    catch(e){D[k]={ok:false,loi:'Mất kết nối: '+e}}})]);
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
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
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
        _lc_load()
        base, detail, err, upd = _lc_state["base"], _lc_state["detail"], _lc_state["error"], _lc_state["updated"]
        prev = _lc_prev_fields(base["phien"]) if base is not None else None
        ws_text = _ws["text"]
    if base is None:                              # chưa có event new-session nào (chưa gắn token / socket chưa nhận phiên)
        return _json({"ok": False, "game": "lc79",
                      "loi": "chua co du lieu — socket: " + ws_text + " (gan token o panel /api/html, tab LC79)"}, 503)
    rows = lc_history()
    out = dict(base)
    out.update(prev)                              # phien_truoc / xuc_xac / tong / ket_qua_truoc: kết quả thật socket đã trả (None nếu chưa có)
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


@app.route("/api/lc79/ws")
def api_lc_ws():
    """Trạng thái socket LC79 (không bao giờ trả token)."""
    ensure_poller()
    return _json(lc_ws_status())


@app.route("/api/lc79/ws/start", methods=["POST"])
def api_lc_ws_start():
    """Gắn token + bật socket. Body JSON: {"token": "...", "url": "... (tuỳ chọn)", "auth": "... (tuỳ chọn)"}. token rỗng = dùng token đã lưu."""
    ensure_poller()
    b = request.get_json(silent=True) or {}
    str_or_none = lambda v: None if v is None else str(v)  # noqa: E731
    try:
        lc_ws_start(str_or_none(b.get("token")), str_or_none(b.get("url")), str_or_none(b.get("auth")))
    except ValueError as e:
        return _json({"ok": False, "loi": str(e)}, 400)
    return _json(lc_ws_status())


@app.route("/api/lc79/ws/stop", methods=["POST"])
def api_lc_ws_stop():
    ensure_poller()
    lc_ws_stop()
    return _json(lc_ws_status())


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
             wr_weights=wr_weights_full(), wr_flip=WR_FLIP_WEIGHT, wr_decay=WR_DECAY, wr_floor=WR_FLOOR, wr_newest=WR_WEIGHT_NEWEST,       # trọng số cũ nhất -> mới nhất
             zf=dict(bat=ZF_ENABLED, window=ZF_WINDOW, z=ZF_Z, min_games=ZF_MIN_GAMES, be_final_zf=ZF_FLIP_FINAL,
                     loai=list(ZF_EXCLUDE), hist_keep=HIST_KEEP, persist_keep=PERSIST_KEEP))
    with _lc_lock:
        lc = {k: _lc_state[k] for k in ("error", "updated", "checked", "events")}
        lc["latest"] = _lc_state["target"]
        lc["socket"] = {"status": _ws["status"], "text": _ws["text"], "wanted": _ws["wanted"],
                        "has_token": bool(_ws["token"]), "url": _ws["url"]}      # KHÔNG trả token
    lc.update(ok=lc["error"] is None and lc["latest"] is not None, wr_window=LC_WR_WINDOW,
              be_final=LC_FLIP_FINAL, wr_flip=LC_WR_FLIP_WEIGHT, wr_decay=LC_WR_DECAY, wr_floor=LC_WR_FLOOR, wr_newest=LC_WR_WEIGHT_NEWEST)
    s["lc79"] = lc
    return _json(s)


@app.route("/")
def index():
    return _json({"api": f"SUNVIW {len(LOGIC_NAMES)} logics (dedup={DEDUP_MODE})", "endpoints": ["/api/predictsun", "/api/predictlc79", "/api/predictsun?detail=1", "/api/predictlc79?detail=1", "/api/lc79/ws", "POST /api/lc79/ws/start", "POST /api/lc79/ws/stop", "/api/html", "/health"]})


# Chạy dưới gunicorn (Railway) thì main() không được gọi -> bật poller ngay khi import.
if __name__ != "__main__":
    ensure_poller()


def main():
    global UPSTREAM_URL, POLL_SEC, FLIP_FINAL, LC_FLIP_FINAL, WR_FLIP_WEIGHT, LC_WR_FLIP_WEIGHT
    global ZF_ENABLED, ZF_WINDOW, ZF_Z, ZF_MIN_GAMES, ZF_FLIP_FINAL
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(description="SUNVIW 24 logics (mặc định 13) - API JSON")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=int(os.environ.get("PORT", 5000)))
    ap.add_argument("--upstream", default=UPSTREAM_URL, help="URL API phien moi nhat (…/api/tx)")
    ap.add_argument("--poll", type=float, default=POLL_SEC, help="chu ky quet upstream (giay)")
    lg = ap.add_mutually_exclusive_group()
    lg.add_argument("--lc-flip", action="store_true", help="BẬT bẻ final của LC79 (riêng, không ảnh hưởng Sun)")
    lg.add_argument("--lc-no-flip", action="store_true", help="TẮT bẻ final của LC79 (theo final gốc)")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--flip", action="store_true", help="BẬT bẻ final (đảo TÀI<->XỈU)")
    g.add_argument("--no-flip", action="store_true", help="TẮT bẻ final (giữ nguyên final của các logic đang dùng)")
    wg = ap.add_mutually_exclusive_group()
    wg.add_argument("--wr-flip", action="store_true", help="BẬT flip trọng số WR của SUN (ván CŨ nhất nặng nhất -> giảm dần tới ván MỚI nhất)")
    wg.add_argument("--no-wr-flip", action="store_true", help="TẮT flip trọng số WR của SUN (ván mới nhất nặng nhất)")
    lwg = ap.add_mutually_exclusive_group()
    lwg.add_argument("--lc-wr-flip", action="store_true", help="BẬT flip trọng số WR của LC79 (riêng, không ảnh hưởng Sun)")
    lwg.add_argument("--lc-no-wr-flip", action="store_true", help="TẮT flip trọng số WR của LC79")
    zg = ap.add_mutually_exclusive_group()
    zg.add_argument("--zf", action="store_true", help="BẬT ZF (z-filter động) cho SUN")
    zg.add_argument("--no-zf", action="store_true", help="TẮT ZF, chỉ dùng cách chốt cũ (WR có trọng số)")
    ap.add_argument("--zf-window", type=int, default=None, help="ZF: SỐ VÁN gần nhất xét WR từng logic (mặc định ZF_WINDOW_DEFAULT)")
    ap.add_argument("--zf-z", type=float, default=None, help="ZF: ngưỡng |z| để logic được bỏ phiếu (mặc định ZF_Z_DEFAULT)")
    ap.add_argument("--zf-min", type=int, default=None, help="ZF: số ván đã chấm tối thiểu mới bật ZF (mặc định ZF_MIN_GAMES_DEFAULT)")
    zfg = ap.add_mutually_exclusive_group()
    zfg.add_argument("--zf-flip", action="store_true", help="BẺ riêng kết quả ZF (đảo TÀI<->XỈU)")
    zfg.add_argument("--zf-no-flip", action="store_true", help="TẮT bẻ riêng kết quả ZF")
    a = ap.parse_args()
    UPSTREAM_URL, POLL_SEC = a.upstream, a.poll
    if a.zf:
        ZF_ENABLED = True
    elif a.no_zf:
        ZF_ENABLED = False
    if a.zf_window is not None:
        ZF_WINDOW = a.zf_window
    if a.zf_z is not None:
        ZF_Z = a.zf_z
    if a.zf_min is not None:
        ZF_MIN_GAMES = a.zf_min
    if a.zf_flip:
        ZF_FLIP_FINAL = True
    elif a.zf_no_flip:
        ZF_FLIP_FINAL = False
    zf_apply_limits()                              # chuẩn hoá + nới HIST_KEEP / PERSIST_KEEP theo ZF_WINDOW
    if a.flip:
        FLIP_FINAL = True
    elif a.no_flip:
        FLIP_FINAL = False
    if a.lc_flip:
        LC_FLIP_FINAL = True
    elif a.lc_no_flip:
        LC_FLIP_FINAL = False
    if a.wr_flip:
        WR_FLIP_WEIGHT = True
    elif a.no_wr_flip:
        WR_FLIP_WEIGHT = False
    if a.lc_wr_flip:
        LC_WR_FLIP_WEIGHT = True
    elif a.lc_no_wr_flip:
        LC_WR_FLIP_WEIGHT = False
    ensure_poller()
    print(f"SUNVIW API  ->  http://{a.host}:{a.port}/api/predict")
    print(f"upstream    ->  {UPSTREAM_URL}")
    print(f"LC79        ->  http://{a.host}:{a.port}/api/predictlc79 · panel http://{a.host}:{a.port}/api/html (gan token o tab LC79)")
    print(f"LC79 socket ->  {_ws['url']} · token {'da luu' if _ws['token'] else 'CHUA CO — gan o panel'}")
    print(f"LC79 WR     ->  xet {LC_WR_WINDOW} van gan nhat DA CHAM · van moi nhat x{LC_WR_WEIGHT_NEWEST} · be final {'BAT' if LC_FLIP_FINAL else 'TAT'} · flip trong so {'BAT (cu nhat nang nhat)' if LC_WR_FLIP_WEIGHT else 'TAT (moi nhat nang nhat)'}")
    print(f"be final SUN ->  {'BAT' if FLIP_FINAL else 'TAT'}  (chi ap cho van quay ve cach cu; van do ZF chot khong bi be)")
    print(f"ZF SUN      ->  {'BAT' if ZF_ENABLED else 'TAT'} · xet {ZF_WINDOW} van gan nhat · |z| >= {ZF_Z} · toi thieu {ZF_MIN_GAMES} van · be rieng ZF {'BAT' if ZF_FLIP_FINAL else 'TAT'} · loai {list(ZF_EXCLUDE) or 'khong'} · giu lich su {HIST_KEEP} phien")
    print(f"WR          ->  xet {WR_WINDOW} van gan nhat, trong so cao nhat x{WR_WEIGHT_NEWEST}, flip trong so {'BAT (cu nhat nang nhat)' if WR_FLIP_WEIGHT else 'TAT (moi nhat nang nhat)'}, trong so (cu -> moi): "
          + " · ".join(f"{w:.2f}" for w in wr_weights_full()))
    app.run(host=a.host, port=a.port, threaded=True)


if __name__ == "__main__":
    main()
