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
    python sunviw_api.py --no-af              # TẮT AF của SUN (--af = bật · --af-low 37 / --af-high 63 = ngưỡng bẻ logic · --af-min 13 = số ván tối thiểu · --af-mode-window 7 / --af-mode-below 45 = bẻ theo WR chế độ · --af-flip / --af-no-flip = bẻ riêng AF)
                                              #           hoặc env SUNVIW_AF / SUNVIW_AF_LOW / SUNVIW_AF_HIGH / SUNVIW_AF_MIN / SUNVIW_AF_MODE_WINDOW / SUNVIW_AF_MODE_MIN / SUNVIW_AF_MODE_BELOW / SUNVIW_AF_FLIP, hoặc sửa AF_*_DEFAULT ở khối "CONFIG AF"
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
    GET /api/admin               -> trang quản trị: MỘT ô nhập key, server tự nhận diện admin chính / admin phụ / key người dùng / key không tồn tại — tạo / xóa (tích chọn nhiều key) / xem key, MỌI key gắn HWID thiết bị (1 key dùng được N thiết bị), hiện lần dùng gần nhất, KHÔNG hiện ở trang chủ (xem khối "CONFIG KEY / ADMIN")
    POST /api/key/check          -> tool xác thực + GẮN THIẾT BỊ cho key người dùng: {"key":"...","hwid":"..."} (hoặc header X-HWID) -> {"ok":true,"het_han":<epoch>,"con_lai_giay":N}
    GET /api/ips                 -> DANH SÁCH IP đang dùng + đã từng dùng API / ws (tab "IP" của panel đọc từ đây; có SUNVIW_ADMIN_KEY thì cần header X-Admin-Key hoặc ?key=)

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

🔀 AF = AUTO-FLIP + CAO/THẤP (port từ SUNVIW_9logics_autoflip_auto.html) — cách chốt final của SUN (mặc định BẬT · khối "CONFIG AF" · LC79 KHÔNG đụng tới):
    Bước 1 (bẻ logic):  WR có trọng số của từng logic (cùng WR_WINDOW ván / trọng số như cách cũ của SUN). WR < AF_FLIP_LOW (37%) hoặc > AF_FLIP_HIGH (63%) -> ĐẢO phiếu logic đó
                        (WR dùng = 100 − WR khi bị bẻ). Chưa đủ AF_MIN_GAMES ván -> không bẻ, vote tất cả logic.
    Bước 2 (CAO/THẤP):  WR dùng > 50% -> nhóm CAO · < 50% -> nhóm THẤP. Nhóm nào ĐÔNG hơn thì chỉ vote trong nhóm đó (chế độ CAO / THẤP); bằng nhau -> vote tất cả (chế độ ALL).
    Bước 3 (bẻ chế độ): WR của CHẾ ĐỘ đang chạy trong AF_MODE_WINDOW (7) ván gần nhất của chế độ đó < AF_MODE_BELOW (45%) -> ĐẢO final (không theo đa số nữa);
                        từ 45% trở lên -> theo bình thường. Đang bẻ THẤP mà ván sau lên CAO thì xét lại WR của CAO. Chưa đủ AF_MODE_MIN ván của chế độ đó -> không bẻ.
    Dữ liệu 2 chế độ: MỖI ván đã chấm lưu sẵn vote của nhóm CAO (hv) và của nhóm THẤP (lv) — cả khi tool đang chạy chế độ kia — nên WR 7 ván của cả 2 chế độ luôn có sẵn.
                      WR chế độ luôn đo trên vote GỐC (chưa bẻ chế độ) để bẻ xong WR không tăng lại rồi tắt bẻ (dao động).
    Ván do AF chốt KHÔNG bị bẻ bởi FLIP_FINAL chung (AF đã tự bẻ) — muốn bẻ riêng AF dùng AF_FLIP_FINAL. AF tắt (--no-af) -> quay về đúng cách cũ (WR có trọng số + nhóm THẤP/CAO + FLIP_FINAL).
    Thứ tự chốt của SUN:  ZF (nếu bật & đủ điều kiện)  ->  AF  ->  cách cũ.   JSON thêm: "af", "che_do", "be_che_do"; ?detail=1 thêm chi_tiet.af (WR 2 chế độ, logic nào bị bẻ).

🌐 TAB IP (panel /api/html) — theo dõi ai đang gọi API:
    Mỗi request tới /api/predictsun · /api/predictlc79 · /api/lc79/ws* · /api/html được ghi lại IP của client (sau proxy Railway đọc X-Forwarded-For / X-Real-IP).
    Tab "IP" hiện: IP ĐANG DÙNG (có request trong IP_ACTIVE_SEC giây gần nhất) + IP ĐÃ TỪNG DÙNG (lưu file, còn sau khi restart) · lần đầu / gần nhất · số request · chia theo loại (sun · lc79 · ws · panel) · User-Agent.
    Khối "CONFIG IP" ở gần đầu file. Nên đặt SUNVIW_ADMIN_KEY để chỉ bạn xem được danh sách IP (panel là trang công khai).

🔐 HWID (gắn key theo THIẾT BỊ, thay cho gắn theo IP mạng) — khối "CONFIG KEY / ADMIN":
    Mọi key (người dùng + admin phụ) đều gắn HWID. Mỗi key có số thiết bị tối đa (max_dev, chọn lúc tạo: 1-2-3-5-10-20-50): máy mới dùng key lần đầu tự được gắn nếu còn chỗ,
    đủ chỗ rồi thì máy khác bị chặn tới khi admin reset / gỡ thiết bị. Panel (/api/html, /api/admin) tự tạo HWID; tool tự viết gửi header X-HWID (hoặc ?hwid= / body {"hwid"}) cùng X-User-Key.
    Admin chính + admin phụ đều chọn được số thiết bị khi tạo key; admin phụ chỉ tạo được key người dùng. Trang admin hiện: số thiết bị đang gắn / tối đa · lần dùng gần nhất · từng thiết bị (có nút Gỡ)
    · tích chọn nhiều key để xóa một lượt.
    ⚑ KHÔNG BAO GIỜ chặn theo IP: đổi mạng / đổi IP không ảnh hưởng key, chỉ máy khác mới bị chặn. Mã thiết bị được giữ ổn định (lưu localStorage + cookie, dấu vân tay phần cứng không đổi theo UA / zoom / xoay màn hình),
    server học thêm mã phụ cho từng thiết bị (header X-HWID-ALT) để máy xoá dữ liệu trình duyệt vẫn được nhận lại thay vì chiếm thêm chỗ — chi tiết ở khối "CONFIG KEY / ADMIN".

Server quét upstream nền mỗi POLL_SEC giây, chỉ tính lại khi có phiên mới -> request của HTML trả về tức thì.
"""
import argparse
import atexit
import base64
import collections
import hashlib
import hmac
import ipaddress
import json
import math
import os
import re
import secrets
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
# THƯ MỤC LƯU DỮ LIỆU BỀN: Railway gắn Volume thì tự đặt RAILWAY_VOLUME_MOUNT_PATH (vd. /data) -> mọi file lưu (lịch sử, graded, key, IP, token LC79...)
# nằm trong Volume nên KHÔNG MẤT sau mỗi lần deploy / restart. Không có Volume (chạy máy local) -> dùng /tmp như cũ.
# Muốn tự chọn thư mục: đặt SUNVIW_DATA_DIR. Từng file vẫn ghi đè riêng được bằng SUNVIW_HIST / SUNVIW_PERSIST / SUNVIW_KEYS_PATH / SUNVIW_IPS_PATH / LC79_WS_CFG / LC79_PRED.
DATA_DIR = os.environ.get("SUNVIW_DATA_DIR") or os.environ.get("RAILWAY_VOLUME_MOUNT_PATH") or "/tmp"
try:
    os.makedirs(DATA_DIR, exist_ok=True)
except OSError:
    DATA_DIR = "/tmp"


def _data_path(name):
    return os.path.join(DATA_DIR, name)


HIST_PATH = os.environ.get("SUNVIW_HIST", _data_path("sunviw_hist.json"))   # lịch sử các phiên đã quét (tool tự tích lũy)
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
PERSIST_PATH = os.environ.get("SUNVIW_PERSIST", _data_path("sunviw_graded.json"))
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
#  🔀  CONFIG AF (AUTO-FLIP + CAO/THẤP + BẺ THEO WR CHẾ ĐỘ) — CÁCH CHỐT FINAL CỦA SUN  —  CHỈNH Ở ĐÂY   (LC79 KHÔNG dùng AF, giữ nguyên)
# ═══════════════════════════════════════════════════════════════════════════
#   Port từ SUNVIW_9logics_autoflip_auto.html. WR từng logic = WR CÓ TRỌNG SỐ của SUN (WR_WINDOW / WR_DECAY / WR_FLOOR / WR_WEIGHT_NEWEST / WR_FLIP_WEIGHT).
#   Bước 1  bẻ logic     : WR < AF_FLIP_LOW -> đảo phiếu logic · WR > AF_FLIP_HIGH -> đảo phiếu logic (WR dùng = 100 − WR). Chưa đủ AF_MIN_GAMES ván -> không bẻ, vote tất cả.
#   Bước 2  CAO / THẤP   : WR dùng > 50% -> nhóm CAO · < 50% -> nhóm THẤP · nhóm đông hơn được vote (CHẾ ĐỘ CAO / THẤP) · bằng nhau -> vote tất cả (ALL) · pool hoà phiếu -> đa số tất cả logic.
#   Bước 3  bẻ chế độ    : WR của chế độ đang chạy trong AF_MODE_WINDOW ván gần nhất CỦA CHẾ ĐỘ ĐÓ < AF_MODE_BELOW -> đảo final · ≥ AF_MODE_BELOW -> theo bình thường.
#                          Cần đủ AF_MODE_MIN ván của chế độ đó mới xét bẻ. Cả CAO lẫn THẤP đều có chuỗi ván riêng (hv / lv lưu trong từng ván đã chấm).
#   AF_ENABLED_DEFAULT    True = dùng AF · False = quay về cách cũ (wr_decision + FLIP_FINAL)
#   AF_FLIP_LOW/HIGH      ngưỡng bẻ logic (37 / 63 như file HTML)
#   AF_MIN_GAMES_DEFAULT  số ván đã chấm tối thiểu mới bẻ logic / chia nhóm (tự kẹp ≤ WR_WINDOW)
#   AF_MODE_WINDOW        số ván gần nhất của mỗi chế độ để tính WR chế độ (7)
#   AF_MODE_MIN           số ván tối thiểu của chế độ đó mới xét bẻ (7; tự kẹp ≤ AF_MODE_WINDOW)
#   AF_MODE_BELOW         WR chế độ dưới mức này (%) -> bẻ final (45)
#   AF_FLIP_FINAL_DEFAULT bẻ riêng kết quả AF (TÀI<->XỈU). Mặc định False vì AF đã tự bẻ; FLIP_FINAL chung KHÔNG áp lên ván do AF chốt.
#   Đổi mà không sửa file (ưu tiên: cờ dòng lệnh > biến môi trường > *_DEFAULT):
#       env  : SUNVIW_AF=1|0 · SUNVIW_AF_LOW · SUNVIW_AF_HIGH · SUNVIW_AF_MIN · SUNVIW_AF_MODE_WINDOW · SUNVIW_AF_MODE_MIN · SUNVIW_AF_MODE_BELOW · SUNVIW_AF_FLIP=1|0
#       lệnh : --af / --no-af · --af-low X · --af-high X · --af-min N · --af-mode-window N · --af-mode-below X · --af-flip / --af-no-flip
AF_ENABLED_DEFAULT = True
AF_FLIP_LOW_DEFAULT = 37
AF_FLIP_HIGH_DEFAULT = 63
AF_MIN_GAMES_DEFAULT = 13
AF_MODE_WINDOW_DEFAULT = 7
AF_MODE_MIN_DEFAULT = 7
AF_MODE_BELOW_DEFAULT = 45
AF_FLIP_FINAL_DEFAULT = False

AF_ENABLED = _env_bool("SUNVIW_AF", AF_ENABLED_DEFAULT)
AF_FLIP_LOW = _env_num("SUNVIW_AF_LOW", AF_FLIP_LOW_DEFAULT, float)
AF_FLIP_HIGH = _env_num("SUNVIW_AF_HIGH", AF_FLIP_HIGH_DEFAULT, float)
AF_MIN_GAMES = _env_num("SUNVIW_AF_MIN", AF_MIN_GAMES_DEFAULT, int)
AF_MODE_WINDOW = _env_num("SUNVIW_AF_MODE_WINDOW", AF_MODE_WINDOW_DEFAULT, int)
AF_MODE_MIN = _env_num("SUNVIW_AF_MODE_MIN", AF_MODE_MIN_DEFAULT, int)
AF_MODE_BELOW = _env_num("SUNVIW_AF_MODE_BELOW", AF_MODE_BELOW_DEFAULT, float)
AF_FLIP_FINAL = _env_bool("SUNVIW_AF_FLIP", AF_FLIP_FINAL_DEFAULT)


def af_apply_limits():
    """Chuẩn hoá tham số AF (gọi lúc import và sau khi đọc cờ dòng lệnh)."""
    global AF_FLIP_LOW, AF_FLIP_HIGH, AF_MIN_GAMES, AF_MODE_WINDOW, AF_MODE_MIN, AF_MODE_BELOW
    AF_FLIP_LOW = min(max(0.0, float(AF_FLIP_LOW)), 50.0)
    AF_FLIP_HIGH = min(max(50.0, float(AF_FLIP_HIGH)), 100.0)
    AF_MIN_GAMES = max(1, int(AF_MIN_GAMES))
    AF_MODE_WINDOW = max(1, int(AF_MODE_WINDOW))
    AF_MODE_MIN = max(1, min(int(AF_MODE_MIN), AF_MODE_WINDOW))
    AF_MODE_BELOW = min(max(0.0, float(AF_MODE_BELOW)), 100.0)


af_apply_limits()


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
LC_WS_CFG_PATH = os.environ.get("LC79_WS_CFG", _data_path("lc79_ws_cfg.json"))   # file lưu token + URL + khung auth + cờ tự bật (quyền 600)
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
LC_PRED_PATH = os.environ.get("LC79_PRED", _data_path("lc79_preds.json"))   # file lưu các dự đoán LC đã chấm / đang chờ (kèm vote từng logic để tính WR sau restart)
LC_PRED_KEEP = 300         # giữ tối đa N dự đoán LC trong file

# ─── PANEL /api/html ─────────────────────────────────────────────────────
PANEL_DEFAULT_SHOW = 30    # số ván lịch sử panel hiện mặc định (đổi trực tiếp trên panel, trình duyệt nhớ lại)
HIST_MAX = 300             # trần số ván lịch sử cho ?hist=N và ô nhập trên panel

# ═══════════════════════════════════════════════════════════════════════════
#  🌐  CONFIG IP — THEO DÕI IP TRUY CẬP (tab "IP" của panel /api/html)  —  CHỈNH Ở ĐÂY
# ═══════════════════════════════════════════════════════════════════════════
#   Mỗi request tới /api/predictsun · /api/predictlc79 · /api/lc79/ws* · /api/html được ghi lại IP client. /health, "/", /api/ips (chính tab IP) KHÔNG tính.
#   IP_TRACK_ENABLED_DEFAULT  True = theo dõi · False = tắt (env SUNVIW_IPS=1|0)
#   IP_ACTIVE_SEC             "đang dùng" = có request trong N giây gần nhất (env SUNVIW_IP_ACTIVE)
#   IP_KEEP                   giữ tối đa N IP (đầy thì xoá IP lâu không thấy nhất)
#   IP_PATH                   file lưu danh sách IP đã từng dùng (env SUNVIW_IPS_PATH). Railway nên trỏ vào ổ đĩa bền, không thì /tmp bị xoá mỗi lần deploy.
#   IP_TRUST_PROXY_DEFAULT    True = đọc IP thật từ X-Forwarded-For / X-Real-IP (đúng khi chạy sau Railway / Cloudflare / nginx) · False = chỉ dùng IP kết nối trực tiếp
#                             (env SUNVIW_IP_PROXY=1|0). Lưu ý: chạy KHÔNG qua proxy mà để True thì client tự đặt X-Forwarded-For giả được -> đặt False.
#   IP_HEADER                 (tuỳ chọn) ép đọc IP từ 1 header cụ thể, vd. CF-Connecting-IP (env SUNVIW_IP_HEADER)
#   IP_ADMIN_KEY              (khuyến nghị) đặt thì /api/ips và tab IP đòi key: header X-Admin-Key hoặc ?key=  (env SUNVIW_ADMIN_KEY). Để trống = ai mở panel cũng thấy danh sách IP.
IP_TRACK_ENABLED_DEFAULT = True
IP_ACTIVE_SEC = _env_num("SUNVIW_IP_ACTIVE", 60, int)
IP_KEEP = 500
IP_SAVE_SEC = 10.0         # ghi file tối đa mỗi N giây (IP mới xuất hiện thì ghi ngay)
IP_PATH = os.environ.get("SUNVIW_IPS_PATH", _data_path("sunviw_ips.json"))
IP_TRUST_PROXY_DEFAULT = True
IP_HEADER = os.environ.get("SUNVIW_IP_HEADER", "").strip()
IP_ADMIN_KEY = os.environ.get("SUNVIW_ADMIN_KEY", "")
IP_TRACK_ENABLED = _env_bool("SUNVIW_IPS", IP_TRACK_ENABLED_DEFAULT)
IP_TRUST_PROXY = _env_bool("SUNVIW_IP_PROXY", IP_TRUST_PROXY_DEFAULT)

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


def af_mode_wr(graded):
    """WR của 2 chế độ CAO / THẤP trên AF_MODE_WINDOW ván gần nhất CỦA CHẾ ĐỘ ĐÓ.
    Dữ liệu = vote gốc của nhóm CAO (hv) / nhóm THẤP (lv) đã LƯU trong từng ván đã chấm (cả khi tool đang chạy chế độ kia),
    chấm với kết quả thật. Ván không có vote của nhóm đó (nhóm rỗng / hoà phiếu / chưa đủ ván) thì bỏ qua.
    Trả {"CAO": {...}, "THAP": {...}}, mỗi chế độ có: n · w (số ván đúng) · need · wr (% hoặc None nếu chưa đủ ván) · flip (True = WR < AF_MODE_BELOW) · chuoi (cũ -> mới, True = đúng)."""
    need = max(1, min(AF_MODE_MIN, AF_MODE_WINDOW))
    out = {}
    for mode, key in (("CAO", "hv"), ("THAP", "lv")):
        rows = []
        for g in reversed(graded):                       # đi từ ván mới nhất lùi về, lấy đủ AF_MODE_WINDOW ván có vote của chế độ này
            v = g.get(key)
            if v in (TAI, XIU):
                rows.append(v == g["actual"])
                if len(rows) >= AF_MODE_WINDOW:
                    break
        rows.reverse()
        n, w = len(rows), sum(rows)
        ready = n >= need
        out[mode] = {"n": n, "w": w, "need": need, "wr": (w * 100.0 / n) if ready else None,
                     "flip": bool(ready and w * 100 < AF_MODE_BELOW * n), "chuoi": rows}
    return out


def af_decision(votes, graded):
    """AF (auto-flip + CAO/THẤP + bẻ theo WR chế độ) của SUN — port từ SUNVIW_9logics_autoflip_auto.html (xem khối CONFIG AF).
    Trả dict: mode (CAO | THAP | ALL) · final (SAU bẻ chế độ) · base (TRƯỚC bẻ chế độ) · mflip (đã bẻ chế độ) · tie (pool hoà phiếu -> dùng đa số tất cả logic)
    preds (phiếu sau bẻ logic) · flips[i] (LOW | HIGH | None) · wins / wsum (trọng số) · eff[i] (WR dùng, 0-100) · group[i] (CAO | THAP | None) · hi / lo (chỉ số logic mỗi nhóm)
    hv / lv (vote gốc của nhóm CAO / THẤP — LƯU vào ván đã chấm) · gT / gX (phiếu TÀI / XỈU trong pool) · avg (TB WR dùng của pool, độ tin cậy) · mw (WR 2 chế độ)."""
    nl = len(votes)
    all_vote = vote_result(votes)
    win = graded[-WR_WINDOW:]                             # cũ -> mới (cùng cửa sổ WR với cách cũ của SUN)
    n = len(win)
    need = max(1, min(AF_MIN_GAMES, WR_WINDOW))
    mw = af_mode_wr(graded)
    out = {"mode": "ALL", "n": n, "need": need, "final": all_vote, "base": all_vote, "mflip": False, "tie": False,
           "preds": list(votes), "flips": [None] * nl, "wins": [], "wsum": 0.0, "weights": [], "eff": [None] * nl,
           "group": [None] * nl, "hi": [], "lo": [], "hv": None, "lv": None,
           "gT": sum(1 for v in votes if v == TAI), "gX": sum(1 for v in votes if v == XIU), "avg": None, "mw": mw}
    if n < need:                                          # chưa đủ ván -> không bẻ, vote tất cả (như file HTML)
        return out
    weights = wr_weights(n)                               # trọng số WR của SUN (cũ nhất -> mới nhất)
    wsum = sum(weights)
    wins = [sum((wt for wt, g in zip(weights, win) if g["votes"][i] == g["actual"]), Fraction(0)) for i in range(nl)]
    thr_lo, thr_hi = Fraction(str(AF_FLIP_LOW)), Fraction(str(AF_FLIP_HIGH))
    preds, flips, effw, group = [], [], [], []
    for i, w in enumerate(wins):
        f = "LOW" if w * 100 < thr_lo * wsum else ("HIGH" if w * 100 > thr_hi * wsum else None)     # Bước 1: bẻ logic
        e = (wsum - w) if f else w                        # trọng số đúng SAU bẻ -> WR dùng = 100 − WR gốc khi bị bẻ
        preds.append(flip_pred(votes[i]) if f else votes[i])
        flips.append(f)
        effw.append(e)
        group.append("CAO" if e * 2 > wsum else ("THAP" if e * 2 < wsum else None))                   # Bước 2: nhóm theo WR dùng
    hi = [i for i, g in enumerate(group) if g == "CAO"]
    lo = [i for i, g in enumerate(group) if g == "THAP"]

    def _pv(idx):
        return vote_result([preds[i] for i in idx]) if idx else None

    hv, lv = _pv(hi), _pv(lo)
    if len(hi) > len(lo):
        mode, pool, base = "CAO", hi, hv
    elif len(lo) > len(hi):
        mode, pool, base = "THAP", lo, lv
    else:
        mode, pool = "ALL", list(range(nl))
        base = vote_result(preds)
    tie = False
    if base == "SKIP":                                    # pool hoà phiếu -> đa số tất cả logic (đã bẻ logic); vẫn hoà -> đa số gốc (như cách cũ)
        tie = True
        base = vote_result(preds)
        if base == "SKIP":
            base = all_vote
    mflip, final = False, base
    if mode != "ALL" and not tie and mw[mode]["flip"]:    # Bước 3: bẻ theo WR của chế độ đang chạy
        mflip, final = True, flip_pred(base)
    pv = [preds[i] for i in pool]
    out.update(mode=mode, final=final, base=base, mflip=mflip, tie=tie, preds=preds, flips=flips,
               wins=[float(w) for w in wins], wsum=float(wsum), weights=[float(w) for w in weights],
               eff=[float(e / wsum * 100) for e in effw], group=group, hi=hi, lo=lo,
               hv=hv if hv in (TAI, XIU) else None, lv=lv if lv in (TAI, XIU) else None,
               gT=sum(1 for x in pv if x == TAI), gX=sum(1 for x in pv if x == XIU),
               avg=(float(sum(effw[i] for i in pool) / (len(pool) * wsum) * 100) if pool else None))
    return out


def decide_final(votes, graded, dec_wr=None):
    """Chốt final của SUN: ZF nếu đủ điều kiện -> AF (nếu bật) -> cách cũ (wr_decision). Trả (final, dùng_zf, zf, dec_wr, af).
    `af` = dict của af_decision khi final do AF chốt, không thì None. `dec_wr` truyền sẵn thì không tính lại wr_decision;
    chỉ tính khi thật sự cần quay về cách cũ (AF tắt)."""
    zf = zf_decision(votes, graded) if ZF_ENABLED else None
    if zf is not None and zf["active"]:
        return zf["final"], True, zf, dec_wr, None
    if AF_ENABLED:
        af = af_decision(votes, graded)
        return af["final"], False, zf, dec_wr, af
    if dec_wr is None:
        dec_wr = wr_decision(votes, graded)
    return dec_wr["final"], False, zf, dec_wr, None


def out_final_zf(final, used_zf, used_af=False):
    """Final SUN đã đưa ra API. Ván do ZF chốt: chỉ bẻ khi ZF_FLIP_FINAL bật (KHÔNG dính FLIP_FINAL chung — ZF đã tự chọn hướng từng logic).
    Ván do AF chốt: chỉ bẻ khi AF_FLIP_FINAL bật (KHÔNG dính FLIP_FINAL chung — AF đã tự bẻ logic + chế độ).
    Ván quay về cách cũ: bẻ theo FLIP_FINAL như trước."""
    if used_zf:
        return flip_pred(final) if ZF_FLIP_FINAL else final
    if used_af:
        return flip_pred(final) if AF_FLIP_FINAL else final
    return out_final(final)


def out_final_g(g):
    """Final đã đưa ra API của 1 ván đã chấm (entry cũ không có khoá 'zf' / 'af' = ván chốt bằng cách cũ)."""
    return out_final_zf(g["final"], g.get("zf", False), g.get("af", False))


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
        final, used_zf, _zf, _wr, af = decide_final(votes, combined)      # ZF nếu đủ điều kiện -> AF -> cách cũ
        entry = {"session": nxt["phien"], "total": nxt["total"], "actual": nxt["actual"],
                 "votes": votes, "final": final, "ok": final == nxt["actual"], "zf": used_zf,
                 "sig": LOGIC_SIG}
        if af is not None:                                                # lưu dữ liệu 2 chế độ: vote gốc của nhóm CAO (hv) và nhóm THẤP (lv) của ván này
            entry.update(af=True, mode=af["mode"], mflip=af["mflip"], hv=af["hv"], lv=af["lv"])
        fresh.append(entry)
    return merge_graded(seed, fresh)


def build_result(hist):
    """Từ lịch sử (cũ -> mới) -> dict kết quả dự đoán cho phiên kế tiếp."""
    latest = hist[-1]
    saved = persist_load()
    graded = rebuild_graded(hist, saved_graded=saved)
    persist_save(graded)
    votes = compute_all(latest["phien"] + 1, latest["d1"], latest["d2"], latest["d3"])
    dec = wr_decision(votes, graded)                                   # cách chốt cũ: luôn tính (phương án dự phòng + hiển thị WR cũ)
    final, used_zf, zf, _, af = decide_final(votes, graded, dec)       # ZF nếu đủ điều kiện -> AF -> cách cũ
    used_af = af is not None
    avg = zf["avg"] if used_zf else (af["avg"] if used_af else dec["avg"])
    base = {
        "ok": True,
        "phien": latest["phien"] + 1,
        "du_doan": out_final_zf(final, used_zf, used_af),
        "be_final": ZF_FLIP_FINAL if used_zf else (AF_FLIP_FINAL if used_af else FLIP_FINAL),   # bẻ ĐANG ÁP DỤNG cho ván này (ZF -> ZF_FLIP_FINAL · AF -> AF_FLIP_FINAL · cách cũ -> FLIP_FINAL)
        "zf": used_zf,
        "af": used_af,                                                 # True = final ván này do AF chốt (auto-flip + CAO/THẤP + bẻ chế độ)
        "che_do": af["mode"] if used_af else None,                     # CAO | THAP | ALL (chỉ khi AF chốt)
        "be_che_do": af["mflip"] if used_af else False,                # True = ván này đã bẻ theo WR chế độ (WR 7 ván của chế độ đang chạy < 45%)
        "do_tin_cay": None if avg is None else round(avg, 1),
        "phien_truoc": latest["phien"],
        "xuc_xac": [latest["d1"], latest["d2"], latest["d3"]],
        "tong": latest["total"],
        "ket_qua_truoc": latest["actual"],
        "so_van_wr": zf["n"] if used_zf else (af["n"] if used_af else dec["n"]),
        "tool_dung_sai_10_van": _recent_accuracy(graded, EVAL_WINDOW, with_chuoi=True),
    }
    tai = sum(1 for v in votes if v == TAI)
    detail = {
        "vote_21": {"TÀI": tai, "XỈU": len(votes) - tai},        # tên khóa giữ nguyên cho tương thích; giờ đếm trên các logic đang dùng
        "so_logic": len(votes),
        "che_do_loc_trung": DEDUP_MODE,
        "logic_bi_loai": [n for n in ALL_LOGIC_NAMES if n not in LOGIC_NAMES],
        "nhom_theo": ("ZF (z-filter)" if used_zf else
                      ({"ALL": "AF · da so", "CAO": "AF · WR cao", "THAP": "AF · WR thap"}[af["mode"]] if used_af
                       else {"ALL": "da so", "LOW": "WR thap", "HIGH": "WR cao"}[dec["mode"]])),
        "nhom_tai_xiu": ({"TÀI": zf["tai"], "XỈU": zf["xiu"]} if used_zf else
                         ({"TÀI": af["gT"], "XỈU": af["gX"]} if used_af else {"TÀI": dec["gT"], "XỈU": dec["gX"]})),
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
        "af": {                                                    # AF (auto-flip + CAO/THẤP + bẻ theo WR chế độ) — xem khối CONFIG AF
            "bat": AF_ENABLED,
            "dang_dung": used_af,                                  # True = final ván này do AF chốt
            "che_do": af["mode"] if used_af else None,             # CAO | THAP | ALL
            "be_che_do": af["mflip"] if used_af else False,        # True = đã bẻ theo WR chế độ ở ván này
            "final_truoc_be_che_do": af["base"] if used_af else None,
            "hoa_phieu_nhom": af["tie"] if used_af else False,     # True = nhóm được chọn hoà phiếu -> dùng đa số tất cả logic
            "so_van_wr": af["n"] if used_af else None,
            "van_toi_thieu": max(1, min(AF_MIN_GAMES, WR_WINDOW)),
            "nguong_be_logic": {"thap": AF_FLIP_LOW, "cao": AF_FLIP_HIGH},
            "so_logic_nhom": {"CAO": len(af["hi"]), "THAP": len(af["lo"])} if used_af else None,
            "logic_bi_be": [LOGIC_NAMES[i] for i, f in enumerate(af["flips"]) if f] if used_af else [],
            "wr_che_do": {                                         # WR của từng chế độ trên AF_MODE_WINDOW ván gần nhất CỦA CHẾ ĐỘ ĐÓ (vote gốc, chưa bẻ chế độ)
                m: {"so_van": x["n"], "dung": x["w"], "wr": None if x["wr"] is None else round(x["wr"], 1),
                    "be": x["flip"],                               # True = WR < AF_MODE_BELOW -> chế độ này sẽ bị bẻ khi được chọn
                    "chuoi": "".join(ICON_DUNG if ok else ICON_SAI for ok in reversed(x["chuoi"]))}   # mới -> cũ
                for m, x in (af["mw"] if used_af else af_mode_wr(graded)).items()},
            "cua_so_che_do": AF_MODE_WINDOW,
            "van_toi_thieu_che_do": max(1, min(AF_MODE_MIN, AF_MODE_WINDOW)),
            "nguong_be_che_do": AF_MODE_BELOW,
            "be_final_af": AF_FLIP_FINAL,
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
             "zf_huong": (None if not zf or zf["per"][i] is None else zf["per"][i]["huong"]),      # THEO | ĐẢO | None (không đủ mạnh / bị loại)
             "af_be": (af["flips"][i] if used_af else None),                                         # LOW | HIGH | None: logic có bị bẻ ở bước 1 của AF không
             "af_du_doan": (af["preds"][i] if used_af else None),                                    # phiếu SAU khi bẻ logic
             "af_wr": (round(af["eff"][i], 1) if used_af and af["eff"][i] is not None else None),    # WR dùng (100 − WR gốc nếu bị bẻ)
             "af_nhom": (af["group"][i] if used_af else None)}                                       # CAO | THAP | None
            for i in range(len(votes))
        ],
        "final_goc": final,                                       # final trước khi bẻ chung (của ZF nếu ZF chốt · của AF nếu AF chốt (đã gồm bẻ logic + bẻ chế độ) · không thì của cách cũ)
        "tool_dung_sai_15_van": _recent_accuracy(graded, WR_WINDOW),
    }
    hist_rows = [{"phien": g["session"], "du_doan": out_final_g(g), "ket_qua": g["actual"], "tong": g.get("total"),
                  "dung": out_final_g(g) == g["actual"], "zf": g.get("zf", False),
                  "af": g.get("af", False), "che_do": g.get("mode"), "be_che_do": g.get("mflip", False)} for g in reversed(graded[-HIST_MAX:])]   # mới -> cũ
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
HWID_JS = r"""
function _hw128(s){let a=1779033703,b=3144134277,c=1013904242,d=2773480762;for(let i=0,k;i<s.length;i++){k=s.charCodeAt(i);a=b^Math.imul(a^k,597399067);b=c^Math.imul(b^k,2869860233);c=d^Math.imul(c^k,951274213);d=a^Math.imul(d^k,2716044179)}
  a=Math.imul(c^(a>>>18),597399067);b=Math.imul(d^(b>>>19),2869860233);c=Math.imul(a^(c>>>17),951274213);d=Math.imul(b^(d>>>19),2716044179);a^=(b^c^d);b^=a;c^=a;d^=a;
  return[a,b,c,d].map(x=>(x>>>0).toString(16).padStart(8,'0')).join('')}
/* HWID = mã thiết bị, KHÔNG liên quan IP / mạng. Cách làm (đổi Wi-Fi <-> 4G <-> VPN không đổi mã):
   1) Mã đã lưu (localStorage + cookie dự phòng, lưu 2 năm; mất 1 trong 2 thì tự phục hồi từ cái còn lại) được dùng TRƯỚC.
   2) Chưa có mã -> tính từ dấu vân tay PHẦN CỨNG ổn định (bỏ UA / ngôn ngữ / múi giờ / zoom / xoay màn hình / canvas là các thứ hay đổi) -> cùng máy xoá dữ liệu trình duyệt vẫn ra đúng mã cũ.
   3) HWID_ALT = mã phụ của CHÍNH máy này để server nhận ra máy khi công thức / bộ nhớ thay đổi: bình thường là mã phần cứng ổn định; máy vừa mất bộ nhớ (HWID_FRESH) thì là mã theo công thức cũ. */
const HWID_ALT=[];
let HWID_FRESH=false;
const HWID=(function(){
  const RX=/^[0-9a-f]{32}$/,n=navigator,s=screen;
  const rdLS=()=>{try{return localStorage.getItem('hwid')||''}catch(e){return ''}};
  const rdCK=()=>{try{const m=document.cookie.match(/(?:^|;\s*)hwid=([0-9a-f]{32})(?:;|$)/);return m?m[1]:''}catch(e){return ''}};
  const save=h=>{
    try{localStorage.setItem('hwid',h)}catch(e){}
    try{document.cookie='hwid='+h+'; max-age=63072000; path=/; SameSite=Lax'+(location.protocol==='https:'?'; Secure':'')}catch(e){}};
  let gpu='';
  try{const g=document.createElement('canvas').getContext('webgl');if(g){const x=g.getExtension('WEBGL_debug_renderer_info');gpu=String(x?g.getParameter(x.UNMASKED_VENDOR_WEBGL)+'|'+g.getParameter(x.UNMASKED_RENDERER_WEBGL):g.getParameter(g.RENDERER))}}catch(e){}
  let stable='';
  try{const sp=[n.platform,n.hardwareConcurrency,n.deviceMemory,n.maxTouchPoints,Math.max(s.width,s.height)+'x'+Math.min(s.width,s.height),s.colorDepth,gpu];
    if(sp.join('').length>=12)stable=_hw128('v2||'+sp.join('||'))}catch(e){}
  let legacy='';
  try{const p=[];
    try{p.push(n.userAgent,n.platform,n.hardwareConcurrency,n.deviceMemory,n.language,n.maxTouchPoints,s.width+'x'+s.height,s.colorDepth,devicePixelRatio,Intl.DateTimeFormat().resolvedOptions().timeZone)}catch(e){}
    if(gpu)p.push(gpu);
    try{const cv=document.createElement('canvas');cv.width=220;cv.height=40;const x=cv.getContext('2d');x.textBaseline='top';x.font='14px Arial';x.fillStyle='#f60';x.fillRect(100,1,60,20);x.fillStyle='#069';x.fillText('SUNVIW hwid Cwm fjord',2,10);p.push(cv.toDataURL())}catch(e){}
    if(p.join('').length>=40)legacy=_hw128(p.join('||'))}catch(e){}
  let id=rdLS();if(!RX.test(id))id=rdCK();if(!RX.test(id))id='';
  HWID_FRESH=!id;
  if(!id)id=stable||legacy||_hw128('r'+Math.random()+Date.now()+String(n.userAgent||''));
  save(id);
  const alt=HWID_FRESH?legacy:stable;
  if(alt&&alt!==id)HWID_ALT.push(alt);
  return id})();
const HWID_HDR=Object.assign({'X-HWID':HWID},HWID_ALT.length?{'X-HWID-ALT':HWID_ALT.join(',')}:{},HWID_FRESH?{'X-HWID-FRESH':'1'}:{});
""".strip()


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
.tab.ipt{grid-column:1/-1}
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
.kov{position:fixed;inset:0;background:rgba(10,14,26,.96);display:none;align-items:center;justify-content:center;z-index:99;padding:20px}
.kbox{background:var(--pn);border:1px solid var(--ln);border-radius:14px;padding:20px;width:100%;max-width:360px}
.kbox input{width:100%;margin:10px 0;background:var(--bg);border:1px solid var(--ln);color:var(--tx);border-radius:9px;padding:10px;font:inherit}
.kbox button{width:100%;background:var(--xiu);color:#06121c;border:0;border-radius:10px;padding:10px;font:inherit;font-weight:700;cursor:pointer}
</style></head><body>
<div class="kov" id="kov"><div class="kbox"><b>Nhập key để dùng tool</b><input id="kin" placeholder="SV-XXXX-XXXX-XXXX-XXXX" spellcheck="false" autocomplete="off"><button id="kgo">Xác nhận</button><p id="kmsg" class="noc" style="margin:10px 0 0;font-size:13px"></p></div></div>
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
/*__HWID_JS__*/
(function(){
const f0=window.fetch.bind(window),ov=document.getElementById('kov'),inp=document.getElementById('kin'),mg=document.getElementById('kmsg');
function show(t){mg.textContent=t||'';ov.style.display='flex';inp.focus()}
window.fetch=function(u,o){o=Object.assign({},o||{});const k=localStorage.getItem('uk')||'';o.headers=Object.assign({},o.headers||{},HWID_HDR,k?{'X-User-Key':k}:{});
  return f0(u,o).then(r=>{if(r.status===401&&String(u).indexOf('/api/')===0&&String(u).indexOf('/api/key/')!==0){const dm=k?'Key không hợp lệ hoặc đã hết hạn':'';r.clone().json().then(j=>show(j&&j.can_key&&(j.dev_locked||/HWID/.test(j.loi||''))?j.loi:dm)).catch(()=>show(dm))}return r})};
async function go(){const v=inp.value.trim();if(!v)return;mg.textContent='';
  try{const r=await f0('/api/key/check',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({key:v,hwid:HWID,hwid_alt:HWID_ALT,hwid_fresh:HWID_FRESH})});const j=await r.json();
    if(j.ok){localStorage.setItem('uk',v.toUpperCase());location.reload()}else mg.textContent=j.loi||'Key không hợp lệ'}catch(e){mg.textContent='Không kết nối được server'}}
document.getElementById('kgo').onclick=go;inp.addEventListener('keydown',e=>{if(e.key==='Enter')go()});
if(!localStorage.getItem('uk'))show('');
})();
</script>
<script>
const G={sun:{n:'Sun',u:'/api/predictsun'},lc:{n:'LC79',u:'/api/predictlc79'}};
let cur=(localStorage.getItem('g') in G||localStorage.getItem('g')==='ip')?localStorage.getItem('g'):'sun',N=+localStorage.getItem('n')||__SHOW__,IPD=null;
const D={},$=s=>document.querySelector(s),cl=v=>v==='TÀI'?'tai':v==='XỈU'?'xiu':'';
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const P={1:[[50,50]],2:[[26,26],[74,74]],3:[[26,26],[50,50],[74,74]],4:[[26,26],[74,26],[26,74],[74,74]],5:[[26,26],[74,26],[50,50],[26,74],[74,74]],6:[[26,26],[74,26],[26,50],[74,50],[26,74],[74,74]]};
const dice=a=>`<span class="dice">${a.map(n=>`<i style="background:${P[n].map(([x,y])=>`radial-gradient(circle at ${x}% ${y}%,#1a1f36 0 3.2px,transparent 3.8px)`).join(',')},#f2efe6"></i>`).join('')}</span>`;
const prevHtml=d=>d.phien_truoc==null?'<div class="mu">Chưa có kết quả phiên trước</div>':`<div class="mu">Phiên ${d.phien_truoc}</div>${d.xuc_xac?dice(d.xuc_xac):''}<div>${d.tong==null?'':`<b>${d.tong}</b> `}<span class="${cl(d.ket_qua_truoc)}">${d.ket_qua_truoc}</span></div>`;
const acc=d=>{const h=d.lich_su||[],k=h.filter(x=>x.dung).length;return{k,t:h.length,p:h.length?Math.round(k*100/h.length):null}};
function render(){
  $('#ws').hidden=cur!=='lc';
  $('#tabs').innerHTML=Object.entries(G).map(([k,g])=>{const d=D[k]||{},a=acc(d);
    return `<button class="tab${k===cur?' on':''}" data-g="${k}"><span>${g.n} <b class="${cl(d.du_doan)}">${d.ok?d.du_doan:'…'}</b></span><small>${a.p===null?'–':a.p+'%'}</small></button>`}).join('')+`<button class="tab ipt${cur==='ip'?' on':''}" data-g="ip"><span>IP truy cập <b class="${IPD&&IPD.ok&&IPD.dang_dung?'okc':''}">${IPD&&IPD.ok?IPD.dang_dung+' đang dùng':(IPD&&IPD.khoa?'🔒':'…')}</b></span><small>${IPD&&IPD.ok?IPD.tong+' IP':''}</small></button>`;
  $('.cfg').hidden=cur==='ip';
  if(cur==='ip'){if(!(IPD&&IPD.khoa&&$('#ak')))$('#main').innerHTML=ipHtml();$('#hist').innerHTML='';$('#st').className='';$('#st').innerHTML='<i></i>'+esc(new Date().toLocaleTimeString());return}
  const d=D[cur]||{},a=acc(d);
  if(!d.ok){$('#main').innerHTML=`<div class="hero"><div class="mu">${esc(d.loi||'Đang tải…')}</div></div>`;$('#hist').innerHTML='';return}
  $('#main').innerHTML=`<section class="hero"><div><div class="mu">Dự đoán phiên ${d.phien}</div><div class="big ${cl(d.du_doan)}">${d.du_doan}</div><div class="mu">Độ tin cậy ${d.do_tin_cay==null?'–':d.do_tin_cay+'%'}${d.be_final?' · đã bẻ final':''}${d.be_che_do?' · bẻ chế độ '+d.che_do:''} · xét ${d.so_van_wr} ván</div></div><div class="prev">${prevHtml(d)}</div></section><div class="stats"><span><b class="okc">${a.k}</b> <span class="mu">đúng</span></span><span><b class="noc">${a.t-a.k}</b> <span class="mu">sai</span></span><span><b>${a.p===null?'–':a.p+'%'}</b> <span class="mu">trên ${a.t} ván</span></span></div>`;
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
const agoT=s=>s<60?s+'s':s<3600?Math.floor(s/60)+'p':s<86400?Math.floor(s/3600)+'g':Math.floor(s/86400)+'n';
function ipHtml(){
  const d=IPD||{};
  if(d.khoa)return `<section class="hero" style="grid-template-columns:1fr"><div><div class="mu">🔒 Cần admin key để xem danh sách IP</div><div style="display:flex;gap:8px;margin-top:8px"><input id="ak" type="password" placeholder="Admin key" autocomplete="off" style="width:200px;background:var(--pn);border:1px solid var(--ln);color:var(--tx);border-radius:8px;padding:6px 8px;font:inherit"><button id="akb" style="background:none;border:1px solid var(--ln);color:var(--mu);border-radius:8px;padding:5px 10px;font:inherit;cursor:pointer">Mở</button></div></div></section>`;
  if(!d.ok)return `<div class="hero"><div class="mu">${esc(d.loi||'Đang tải…')}</div></div>`;
  const by=o=>Object.entries(o||{}).map(([k,v])=>k+' '+v).join(' · ');
  return `<section class="hero" style="grid-template-columns:1fr"><div><div class="mu">IP truy cập API (Sun · LC79 · WS · panel)</div><div class="stats"><span><b class="okc">${d.dang_dung}</b> <span class="mu">đang dùng (trong ${d.cua_so_giay}s)</span></span><span><b>${d.tong}</b> <span class="mu">IP đã từng dùng</span></span></div><div class="mu">IP của bạn: ${esc(d.ban||'?')}</div></div></section><table><tr><th>IP</th><th>Trạng thái</th><th>Gần nhất</th><th class="r">Request</th></tr>${(d.ips||[]).map(x=>`<tr><td title="${esc(x.ua||'')}"><b>${esc(x.ip)}</b>${x.la_ban?' <span class="mu">(bạn)</span>':''}<div class="mu" style="font-size:11.5px">${esc(by(x.theo_loai))}</div></td><td class="${x.dang_dung?'okc':'mu'}">${x.dang_dung?'● đang dùng':'○ đã dùng'}</td><td class="mu">${esc(x.gan_nhat)}<div style="font-size:11.5px">${agoT(x.truoc_giay)} trước · từ ${esc(x.lan_dau)}</div></td><td class="r">${x.so_request}</td></tr>`).join('')}</table>`;
}
async function loadIps(){
  try{const k=localStorage.getItem('ak')||'';const r=await fetch('/api/ips',{cache:'no-store',headers:k?{'X-Admin-Key':k}:{}});IPD=await r.json()}
  catch(e){IPD={ok:false,loi:'Mất kết nối: '+e}}
}
document.addEventListener('click',e=>{if(e.target.id==='akb'){const v=$('#ak');localStorage.setItem('ak',v?v.value.trim():'');loadIps().then(render)}});
async function load(){
  await Promise.all([wsLoad(),loadIps(),...Object.entries(G).map(async([k,g])=>{
    try{const r=await fetch(`${g.u}?hist=${N}`,{cache:'no-store'});D[k]=await r.json()}
    catch(e){D[k]={ok:false,loi:'Mất kết nối: '+e}}})]);
  render();
}
load();setInterval(load,3000);
</script></body></html>
"""


# ─── THEO DÕI IP TRUY CẬP (tab "IP" của panel) — xem khối CONFIG IP ──────────
_ip_lock = threading.Lock()
_ip_store = {}              # ip -> {"ip","first","last","hits","by":{loại: số request},"ua"}
_ip_state = {"loaded": False, "saved": 0.0, "dirty": False}


def ip_kind(path):
    """Loại request được tính vào danh sách IP (None = không tính: /health, /, /api/ips ...)."""
    if path in ("/api/predictsun", "/api/predict"):
        return "sun"
    if path in ("/api/predictlc79", "/api/prdictlc79"):
        return "lc79"
    if path.startswith("/api/lc79/ws"):
        return "ws"
    if path == "/api/html":
        return "panel"
    return None


def _fmt_ts(ts):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))


def _ip_load_locked():
    """Nạp danh sách IP đã lưu (1 lần). Gọi trong _ip_lock."""
    if _ip_state["loaded"]:
        return
    _ip_state["loaded"] = True
    try:
        with open(IP_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:  # noqa: BLE001
        return
    for r in data if isinstance(data, list) else []:
        try:
            ip = str(r.get("ip", ""))
            if ip != "unknown":
                ip = str(ipaddress.ip_address(ip))
            by = {str(k): int(v) for k, v in (r.get("by") or {}).items()}
            _ip_store[ip] = {"ip": ip, "first": float(r["first"]), "last": float(r["last"]),
                             "hits": int(r.get("hits", 0)), "by": by, "ua": str(r.get("ua", ""))[:120]}
        except Exception:  # noqa: BLE001
            continue


def _ip_save_locked(now):
    """Ghi danh sách IP ra file (atomic). Gọi trong _ip_lock."""
    try:
        tmp = IP_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(sorted(_ip_store.values(), key=lambda r: r["first"]), f, ensure_ascii=False)
        os.replace(tmp, IP_PATH)
        _ip_state["saved"] = now
        _ip_state["dirty"] = False
    except Exception:  # noqa: BLE001
        pass


def ip_flush():
    """Ghi nốt các request chưa kịp lưu (gọi khi tắt server) để không mất tối đa IP_SAVE_SEC giây dữ liệu."""
    with _ip_lock:
        if _ip_state["loaded"] and _ip_state["dirty"]:
            _ip_save_locked(time.time())


atexit.register(ip_flush)


def ip_touch(ip, kind, ua=""):
    """Ghi 1 request của `ip` (loại `kind`). IP mới -> ghi file ngay; IP cũ -> ghi file tối đa mỗi IP_SAVE_SEC giây."""
    now = time.time()
    ua = re.sub(r"[\x00-\x1f\x7f]", " ", str(ua or ""))[:120]
    with _ip_lock:
        _ip_load_locked()
        r = _ip_store.get(ip)
        is_new = r is None
        if is_new:
            r = _ip_store[ip] = {"ip": ip, "first": now, "last": now, "hits": 0, "by": {}, "ua": ""}
            while len(_ip_store) > IP_KEEP:                       # đầy -> bỏ IP lâu không thấy nhất
                del _ip_store[min(_ip_store, key=lambda k: _ip_store[k]["last"])]
        r["last"] = now
        r["hits"] += 1
        r["by"][kind] = r["by"].get(kind, 0) + 1
        if ua:
            r["ua"] = ua
        _ip_state["dirty"] = True
        if is_new or now - _ip_state["saved"] >= IP_SAVE_SEC:
            _ip_save_locked(now)


def ip_snapshot(me=None):
    """Danh sách IP cho /api/ips: đang dùng trước (mới nhất trước), rồi tới các IP đã từng dùng."""
    now = time.time()
    with _ip_lock:
        _ip_load_locked()
        rows = [dict(r, by=dict(r["by"])) for r in _ip_store.values()]
    out = []
    for r in rows:
        age = max(0.0, now - r["last"])
        out.append({"ip": r["ip"], "dang_dung": age <= IP_ACTIVE_SEC, "lan_dau": _fmt_ts(r["first"]), "gan_nhat": _fmt_ts(r["last"]),
                    "truoc_giay": int(age), "so_request": r["hits"], "theo_loai": r["by"], "ua": r.get("ua", ""), "la_ban": r["ip"] == me})
    out.sort(key=lambda x: (not x["dang_dung"], x["truoc_giay"]))
    return {"ok": True, "tong": len(out), "dang_dung": sum(1 for x in out if x["dang_dung"]),
            "cua_so_giay": IP_ACTIVE_SEC, "ban": me, "ips": out}


def ip_health():
    with _ip_lock:
        _ip_load_locked()
        n = len(_ip_store)
    return dict(bat=IP_TRACK_ENABLED, tong=n, active_sec=IP_ACTIVE_SEC, khoa=bool(IP_ADMIN_KEY), tin_proxy=IP_TRUST_PROXY)


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


def client_ip():
    """IP của client. Sau proxy (Railway / Cloudflare / nginx) đọc X-Forwarded-For / X-Real-IP (hoặc header đặt ở SUNVIW_IP_HEADER) khi IP_TRUST_PROXY bật;
    giá trị không phải IP hợp lệ thì bỏ qua và dùng IP kết nối trực tiếp (remote_addr)."""
    cands = []
    if IP_TRUST_PROXY:
        if IP_HEADER:
            cands.append(request.headers.get(IP_HEADER, ""))
        else:
            cands += [request.headers.get("X-Forwarded-For", ""), request.headers.get("X-Real-IP", "")]
    cands.append(request.remote_addr or "")
    for c in cands:
        v = (c or "").split(",")[0].strip()            # X-Forwarded-For: client, proxy1, proxy2 -> lấy phần tử đầu
        if v.startswith("["):
            v = v[1:].split("]")[0]
        elif v.count(":") == 1:                        # IPv4:port
            v = v.split(":")[0]
        if v:
            try:
                return str(ipaddress.ip_address(v))
            except ValueError:
                continue
    return "unknown"


@app.before_request
def _track_ip():
    """Ghi IP mọi request tới API / ws / panel. Không bao giờ được làm hỏng request."""
    if not IP_TRACK_ENABLED or request.method == "OPTIONS":
        return None
    try:
        kind = ip_kind(request.path)
        if kind:
            ip_touch(client_ip(), kind, request.headers.get("User-Agent", ""))
    except Exception:  # noqa: BLE001
        pass
    return None


# ─── KEY NGƯỜI DÙNG + TRANG ADMIN (/api/admin) ────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════
#  🔑  CONFIG KEY / ADMIN  —  CHỈNH Ở ĐÂY
# ═══════════════════════════════════════════════════════════════════════════
#   Trang quản trị: GET /api/admin  (KHÔNG hiện ở trang chủ "/").  CHỈ MỘT Ô NHẬP KEY — server tự phân loại:
#     · Admin chính : nhập MẬT KHẨU admin chính vào chính ô đó (kiểm tra Ở SERVER, trình duyệt / view-source KHÔNG chứa mật khẩu). Tạo key admin phụ + key người dùng (chọn số thiết bị tối đa cho từng key),
#                     xóa key (tích chọn nhiều key rồi xóa một lượt), xem mọi key (ai tạo, hạn, số thiết bị đang gắn, LẦN DÙNG GẦN NHẤT, từng thiết bị) và RESET / GỠ THIẾT BỊ.
#     · Admin phụ   : nhập key admin phụ (do admin chính tạo). Key chưa ai dùng -> nhập username (vd. Dark) -> key gắn với username đó VÀ gắn với HWID của thiết bị đăng nhập đầu tiên.
#                     Key dùng được tối đa N thiết bị (N do admin chính chọn lúc tạo key): máy thứ N+1 bị chặn cho tới khi admin chính reset / gỡ thiết bị.
#                     Admin phụ tạo / xóa KEY NGƯỜI DÙNG (chỉ key mình tạo; cũng chọn được số thiết bị tối đa, tích chọn xóa nhiều key, reset thiết bị key của mình) với hạn 1-2-7-14-30-60-90-180-365 ngày.
#     · Key người dùng / key không tồn tại -> trang admin báo rõ là key người dùng (không phải admin) hoặc không tìm thấy key.
#   Người dùng nhập KEY NGƯỜI DÙNG ở panel /api/html (hoặc tool gọi POST /api/key/check {"key": "...", "hwid": "..."}).
#   HWID = mã thiết bị. KHÔNG dùng IP / mạng để chặn: đổi Wi-Fi <-> 4G <-> VPN, đổi IP thoải mái, cùng máy vẫn dùng bình thường (server chỉ GHI IP để admin xem). Chỉ MÁY KHÁC mới bị chặn khi key đã đủ thiết bị.
#   Panel tự tạo mã: ưu tiên mã đã lưu (localStorage + cookie dự phòng 2 năm, mất 1 trong 2 thì tự phục hồi từ cái còn lại); chưa có thì tính từ dấu vân tay PHẦN CỨNG ổn định (nền tảng, số nhân CPU, RAM,
#   cảm ứng, kích thước màn hình không phân biệt xoay ngang/dọc, GPU) — không dùng UA / ngôn ngữ / múi giờ / zoom / canvas vì các thứ này tự đổi, nên xoá dữ liệu trình duyệt rồi vào lại vẫn ra ĐÚNG mã cũ.
#   Panel còn gửi mã phụ của chính máy đó (header X-HWID-ALT; X-HWID-FRESH: 1 khi máy vừa mất bộ nhớ) -> server nhớ mã phụ cho từng thiết bị (_dev_learn) và tự nhận lại máy cũ khi công thức / bộ nhớ đổi.
#   Giới hạn không tránh được: trình duyệt không đọc được số serial phần cứng, nên 2 máy CÙNG ĐỜI y hệt nhau (vd. 2 iPhone cùng model) mà đều mới xoá sạch dữ liệu có thể ra cùng mã. Chặn chia sẻ key thông thường, không chống được người cố tình giả mạo.
#   Tool tự viết: gửi header X-HWID (hoặc ?hwid= / body {"hwid"}) = mã MÁY THẬT của tool (8-64 ký tự A-Z a-z 0-9 _ -), nên băm từ mã cài đặt hệ điều hành (Windows: HKLM\SOFTWARE\Microsoft\Cryptography\MachineGuid ·
#   Linux: /etc/machine-id · macOS: IOPlatformUUID) và TUYỆT ĐỐI KHÔNG dùng MAC / IP / tên mạng / SSID (các thứ này đổi khi đổi mạng hoặc cắm card mới -> chính là lỗi "đổi mạng là mất key").
#   Khi KEY_GATE_API bật: /api/predictsun · /api/predictlc79 · /api/lc79/ws* · /api/ips đòi key hợp lệ (header X-User-Key hoặc ?key=; riêng /api/ips chỉ nhận header).
#
#   SUNVIW_MAIN_PASS   (KHUYẾN NGHỊ) mật khẩu admin chính đặt ở biến môi trường Railway -> trong code không còn dấu vết mật khẩu nào. Không đặt = dùng hash mặc định trong code.
#   SUNVIW_KEYS_PATH   file lưu key (mặc định <DATA_DIR>/sunviw_keys.json; DATA_DIR = Volume Railway nếu có, không thì /tmp). Railway: PHẢI gắn Volume, không thì MẤT KEY mỗi lần deploy.
#   SUNVIW_SECRET      (tuỳ chọn) khoá ký phiên đăng nhập admin; không đặt = tự sinh và lưu chung file key.
#   SUNVIW_GATE_API    1 = bắt buộc key cho các endpoint ở trên (mặc định) · 0 = tắt (ai gọi API cũng được như trước)
#   SUNVIW_HWID_REQUIRED  1 = request dùng key người dùng mà KHÔNG kèm HWID bị từ chối (mặc định) · 0 = cho qua (không gắn thiết bị). Có gửi HWID thì luôn được kiểm tra + gắn thiết bị.
ADMIN_MAIN_NAME = "admin chính"
_ADMIN_SALT = b"sunviw-admin-v1:93eacb1bcbb59252"
ADMIN_PASS_HASH_DEFAULT = "69eb8d5a0692dade93234908118f99d1b8990e3484dc3fca7bb3847d8b6578eb"         # PBKDF2-SHA256 (200.000 vòng) — không đảo ngược được thành mật khẩu, nhưng mật khẩu toàn số ngắn vẫn dò được nếu lộ hash -> nên đặt SUNVIW_MAIN_PASS
KEYS_PATH = os.environ.get("SUNVIW_KEYS_PATH", _data_path("sunviw_keys.json"))
KEY_GATE_API = _env_bool("SUNVIW_GATE_API", True)
KEY_DAYS = (1, 2, 7, 14, 30, 60, 90, 180, 365)       # hạn key cho phép (ngày)
KEY_MAX_TOTAL = 5000                                  # trần số key lưu trong file
ADMIN_SESSION_SEC = 12 * 3600                         # phiên đăng nhập admin sống bao lâu
LOGIN_MAX_FAIL = 8                                    # sai quá N lần trong LOGIN_LOCK_SEC -> khóa IP đó LOGIN_LOCK_SEC giây
LOGIN_LOCK_SEC = 900
KEY_DEV_OPTIONS = (1, 2, 3, 5, 10, 20, 50)            # số thiết bị tối đa chọn được khi tạo key (1 key dùng được trên N thiết bị)
KEY_DEV_DEFAULT = 1                                   # mặc định (cũng là số thiết bị của key cũ tạo trước bản này)
HWID_REQUIRED = _env_bool("SUNVIW_HWID_REQUIRED", True)
HWID_TOUCH_SEC = 60                                   # ghi "lần dùng gần nhất" tối đa 1 lần / phút / thiết bị (đỡ ghi file mỗi lần panel poll)


def _pw_hash(pw):
    return hashlib.pbkdf2_hmac("sha256", str(pw).encode("utf-8"), _ADMIN_SALT, 200000).hex()


_ENV_MAIN_PASS = os.environ.get("SUNVIW_MAIN_PASS", "")
ADMIN_PASS_HASH = _pw_hash(_ENV_MAIN_PASS) if _ENV_MAIN_PASS else ADMIN_PASS_HASH_DEFAULT
_MEM_SECRET = secrets.token_hex(32)
_kv_lock = threading.RLock()
_KEY_ALPHA = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"        # bỏ 0/O/1/I cho dễ đọc


def _kv_load():
    try:
        with open(KEYS_PATH, "r", encoding="utf-8") as f:
            d = json.load(f)
        if isinstance(d, dict) and isinstance(d.get("keys"), dict):
            return d
    except Exception:  # noqa: BLE001
        pass
    return {"secret": "", "keys": {}}


def _kv_save(d):
    if not d.get("secret"):
        d["secret"] = _MEM_SECRET
    tmp = KEYS_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)
    os.replace(tmp, KEYS_PATH)


def _secret_bytes():
    s = os.environ.get("SUNVIW_SECRET", "")
    if not s:
        with _kv_lock:
            d = _kv_load()
            if not d.get("secret"):
                try:
                    _kv_save(d)
                except OSError:
                    pass
            s = d.get("secret") or _MEM_SECRET
    return s.encode("utf-8")


def _norm_key(s):
    return re.sub(r"[^A-Za-z0-9-]", "", str(s or "")).upper()[:40]


def _new_key(prefix, keys):
    while True:
        k = prefix + "-" + "-".join("".join(secrets.choice(_KEY_ALPHA) for _ in range(4)) for _ in range(4))
        if k not in keys:
            return k


def _clean_username(s):
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    if not 2 <= len(s) <= 20 or not all(c.isalnum() or c in " _.-" for c in s):
        return None
    if s.lower() in ("admin", "admin chính", "admin chinh", "main"):
        return None
    return s


def _norm_hwid(s):
    """HWID hợp lệ = 8-64 ký tự [A-Za-z0-9_-] (panel gửi 32 hex). Sai định dạng -> "". Luôn chữ thường để so khớp."""
    s = str(s or "").strip()
    return s.lower() if re.fullmatch(r"[A-Za-z0-9_-]{8,64}", s) else ""


DEV_ALIAS_MAX = 6                                     # số mã phụ tối đa nhớ cho 1 thiết bị (mã cũ nhất bị bỏ khi đầy)


def req_hw_ids(body=None):
    """Mã thiết bị của request -> (hw, alts, fresh).
       hw    : mã CHÍNH = header X-HWID · ?hwid= · body {"hwid"} · cookie "hwid" (cookie để mở thẳng link API trên trình duyệt vẫn nhận ra máy).
       alts  : mã PHỤ của CHÍNH máy đó (header X-HWID-ALT, cách nhau dấu phẩy · ?hwid_alt= · body {"hwid_alt": [...]}): dấu vân tay phần cứng ổn định / công thức cũ.
       fresh : client báo "vừa mất bộ nhớ, không còn mã cũ" (header X-HWID-FRESH: 1 · ?hwid_fresh=1 · body {"hwid_fresh": true}) -> alts được dùng để NHẬN LẠI máy cũ.
       Tool tự viết chỉ cần gửi X-HWID như trước (không cần alts / fresh)."""
    b = body if isinstance(body, dict) else {}
    hw = ""
    for c in (request.headers.get("X-HWID"), request.args.get("hwid"), b.get("hwid"), request.cookies.get("hwid")):
        hw = _norm_hwid(c)
        if hw:
            break
    alts = []
    for raw in (request.headers.get("X-HWID-ALT"), request.args.get("hwid_alt"), b.get("hwid_alt")):
        parts = raw if isinstance(raw, (list, tuple)) else re.split(r"[,\s]+", str(raw or ""))
        for x in parts[:6]:
            n = _norm_hwid(x)
            if n and n != hw and n not in alts:
                alts.append(n)
    fresh = str(request.headers.get("X-HWID-FRESH") or request.args.get("hwid_fresh") or b.get("hwid_fresh") or "").strip().lower() in ("1", "true", "yes")
    return hw, tuple(alts[:4]), fresh


def req_hwid(body=None):
    """HWID chính của thiết bị gọi request (giữ để tool cũ không hỏng) — xem req_hw_ids."""
    return req_hw_ids(body)[0]


def _max_dev(rec):
    """Số thiết bị tối đa của key (key cũ chưa có max_dev = KEY_DEV_DEFAULT)."""
    try:
        return max(1, int(rec.get("max_dev") or KEY_DEV_DEFAULT))
    except (TypeError, ValueError):
        return KEY_DEV_DEFAULT


def _dev_find(devs, hw, alts=(), fresh=False):
    """Khoá của thiết bị ĐÃ GẮN ứng với request, không có -> None. KHÔNG dùng IP.
       1) mã chính hw trùng khoá thiết bị, hoặc trùng 1 mã phụ máy đó đã được học  -> đúng máy.
       2) chỉ khi client báo fresh (máy vừa mất bộ nhớ nên không còn mã cũ): mã dự phòng alts trùng khoá / mã phụ -> nhận lại máy cũ.
          Máy KHÁC (còn mã riêng của nó) không bao giờ được nhận nhầm bằng alts."""
    if hw in devs:
        return hw
    for k, v in devs.items():
        if hw in (v.get("alt") or ()):
            return k
    if fresh:
        for a in alts:
            if a in devs:
                return a
        for k, v in devs.items():
            al = v.get("alt") or ()
            if any(a in al for a in alts):
                return k
    return None


def _dev_learn(dv, key, ids):
    """Nhớ thêm mã phụ cho thiết bị đã khớp (để lần sau mất bộ nhớ / đổi công thức vẫn nhận ra máy). Trả True nếu có thay đổi."""
    al = dv.get("alt")
    if not isinstance(al, list):
        al = dv["alt"] = []
    ch = False
    for i in ids:
        if i and i != key and i not in al:
            al.append(i)
            ch = True
    if len(al) > DEV_ALIAS_MAX:
        del al[:-DEV_ALIAS_MAX]
        ch = True
    return ch


def _dev_use(rec, hw, ip, ua, now, alts=(), fresh=False, bind=True):
    """Dùng key trên thiết bị hw: đã gắn -> cập nhật "lần dùng gần nhất" (tối đa 1 lần / HWID_TOUCH_SEC) + học mã phụ;
    chưa gắn -> gắn thêm nếu key còn chỗ (số thiết bị < max_dev) và bind=True. Gọi trong _kv_lock với rec lấy từ _kv_load().
    IP chỉ được GHI LẠI cho admin xem, KHÔNG bao giờ dùng để chặn -> đổi mạng / đổi IP không ảnh hưởng.
    Trả (ok, lỗi, changed): changed=True -> nơi gọi phải _kv_save."""
    devs = rec.get("devs")
    if not isinstance(devs, dict):
        devs = rec["devs"] = {}
    k = _dev_find(devs, hw, alts, fresh)
    if k is not None:
        dv = devs[k]
        ch = _dev_learn(dv, k, [hw] if fresh else [hw, *alts])
        if now - int(dv.get("last") or 0) >= HWID_TOUCH_SEC:
            dv["last"], dv["ip"] = now, ip
            rec["last"], rec["last_ip"] = now, ip
            ch = True
        return True, "", ch
    if not bind:
        return False, "thiet bi chua gan vao key", False
    cap = _max_dev(rec)
    if len(devs) >= cap:
        return False, (f"Key đã đủ {cap} thiết bị — thiết bị này chưa được gắn với key (đổi mạng / đổi IP KHÔNG ảnh hưởng, chỉ máy khác mới bị chặn). "
                       f"Nhờ admin reset / gỡ thiết bị cũ hoặc xin key có nhiều thiết bị hơn. Mã thiết bị của bạn: {hw[:8]}…{hw[-4:]}"), False
    dv = devs[hw] = {"first": now, "last": now, "ip": ip, "ua": str(ua or "")[:80]}
    if not fresh:
        _dev_learn(dv, hw, alts)
    rec["last"], rec["last_ip"] = now, ip
    return True, "", True


def _own_user_key(s, r):
    """Admin phụ chỉ động được vào key NGƯỜI DÙNG do chính mình tạo; admin chính động được mọi key."""
    return s["r"] == "main" or (r.get("type") == "user" and r.get("by") == "sub" and r.get("by_name") == s["n"])


# ─ phiên đăng nhập admin: token ký HMAC (không lưu server, chạy được nhiều worker) ─
def _tok_make(role, name, key="", hw=""):
    p = {"r": role, "n": name, "k": key, "h": hw, "e": int(time.time()) + ADMIN_SESSION_SEC}
    raw = base64.urlsafe_b64encode(json.dumps(p, ensure_ascii=False).encode("utf-8")).decode().rstrip("=")
    return raw + "." + hmac.new(_secret_bytes(), raw.encode(), hashlib.sha256).hexdigest()


def _tok_check():
    """Trả {"r","n","k"} nếu header X-Admin-Token hợp lệ, ngược lại None.
    Admin phụ: key của họ còn tồn tại + còn hạn + request đến từ ĐÚNG thiết bị đã đăng nhập (HWID chính hoặc mã phụ của cùng máy đó) + máy đó vẫn đang được gắn vào key
    (admin chính reset / gỡ thiết bị / xóa key -> phiên cũ chết ngay). Mỗi request hợp lệ cập nhật "lần dùng gần nhất" (tối đa 1 lần / phút). Không xét IP."""
    t = request.headers.get("X-Admin-Token", "")
    try:
        raw, sig = t.split(".", 1)
        if not hmac.compare_digest(sig, hmac.new(_secret_bytes(), raw.encode(), hashlib.sha256).hexdigest()):
            return None
        p = json.loads(base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)).decode("utf-8"))
        if p["e"] < time.time():
            return None
        if p["r"] == "main":
            return {"r": "main", "n": ADMIN_MAIN_NAME, "k": ""}
        if p["r"] == "sub":
            hw, alts, hfresh = req_hw_ids()
            if not hw:
                return None
            now = int(time.time())
            with _kv_lock:
                d = _kv_load()
                rec = d["keys"].get(p["k"])
                if rec and rec.get("type") == "sub" and rec.get("owner") == p["n"] and rec["exp"] > now:
                    devs = rec.get("devs") if isinstance(rec.get("devs"), dict) else {}
                    kr = _dev_find(devs, hw, alts, hfresh)                  # thiết bị đang gọi
                    if kr is not None and kr == _dev_find(devs, p.get("h", "")):      # = thiết bị đã đăng nhập tạo ra phiên này
                        _, _, ch = _dev_use(rec, hw, client_ip(), request.headers.get("User-Agent", ""), now, alts, hfresh, bind=False)
                        if ch:
                            try:
                                _kv_save(d)
                            except OSError:
                                pass
                        return {"r": "sub", "n": p["n"], "k": p["k"]}
    except Exception:  # noqa: BLE001
        pass
    return None


# ─ chống dò mật khẩu / key: sai quá LOGIN_MAX_FAIL lần thì khóa IP ─
_rl = {}
_rl_lock = threading.Lock()


def _rl_wait(ip):
    with _rl_lock:
        r = _rl.get(ip)
        return max(0, int(r[2] - time.time())) if r else 0


def _rl_fail(ip):
    now = time.time()
    with _rl_lock:
        if len(_rl) > 5000:
            _rl.clear()
        r = _rl.get(ip)
        if not r or now - r[1] > LOGIN_LOCK_SEC:
            r = _rl[ip] = [0, now, 0.0]
        r[0] += 1
        if r[0] >= LOGIN_MAX_FAIL:
            r[2] = now + LOGIN_LOCK_SEC


def _rl_reset(ip):
    with _rl_lock:
        _rl.pop(ip, None)


def _check_user_key(k, hw=None, ip="", ua="", alts=(), fresh=False):
    """(record, lỗi, đã_tồn_tại). Chỉ key loại 'user' còn hạn mới qua. Có HWID -> kiểm tra / gắn thiết bị (đủ chỗ mới gắn thêm) và ghi "lần dùng gần nhất";
    không có HWID mà HWID_REQUIRED bật -> từ chối. `ip` chỉ để ghi lại, không dùng để chặn."""
    k = _norm_key(k)
    if not k:
        return None, "thieu key", False
    with _kv_lock:
        d = _kv_load()
        r = d["keys"].get(k)
        if not r or r.get("type") != "user":
            return None, "key khong hop le", False
        now = int(time.time())
        if r["exp"] <= now:
            return None, "key da het han", True
        if hw:
            ok, err, ch = _dev_use(r, hw, ip, ua, now, alts, fresh)
            if not ok:
                return None, err, True
            if ch:
                try:
                    _kv_save(d)
                except OSError:
                    pass
        elif HWID_REQUIRED:
            return None, "Thiếu mã thiết bị (HWID) — gửi header X-HWID hoặc ?hwid= cùng key.", True
        return r, "", True


_GATED_EXACT = {"/api/predictsun", "/api/predict", "/api/predictlc79", "/api/prdictlc79", "/api/ips"}


@app.before_request
def _gate_key():
    """KEY_GATE_API bật -> các endpoint dữ liệu đòi key người dùng hợp lệ + HWID thiết bị (còn chỗ thì tự gắn)."""
    p = request.path
    if not KEY_GATE_API or request.method == "OPTIONS" or not (p in _GATED_EXACT or p.startswith("/api/lc79/ws")):
        return None
    k = request.headers.get("X-User-Key", "")
    if not k and p != "/api/ips":                      # /api/ips đã dùng ?key= cho admin key cũ -> chỉ nhận header
        k = request.args.get("key", "")
    hw, alts, hfresh = req_hw_ids()
    rec, err, _ = _check_user_key(k, hw, client_ip(), request.headers.get("User-Agent", ""), alts, hfresh)
    if rec:
        return None
    hint = " (gui header X-User-Key hoac ?key=)" if err in ("thieu key", "key khong hop le") else ""
    return _json({"ok": False, "can_key": True, "dev_locked": err.startswith("Key đã đủ"), "loi": err + hint}, 401)


@app.route("/api/key/check", methods=["GET", "POST"])
def api_key_check():
    """Tool / panel xác thực key người dùng + gắn thiết bị: POST {"key": "...", "hwid": "..."} hoặc GET ?key=...&hwid=... (hoặc header X-User-Key / X-HWID)."""
    ip = client_ip()
    w = _rl_wait(ip)
    if w:
        return _json({"ok": False, "loi": f"nhap sai qua nhieu, thu lai sau {w}s"}, 429)
    b = request.get_json(silent=True) or {}
    k = b.get("key") or request.headers.get("X-User-Key") or request.args.get("key", "")
    hw, alts, hfresh = req_hw_ids(b)
    rec, err, exists = _check_user_key(k, hw, ip, request.headers.get("User-Agent", ""), alts, hfresh)
    if not rec:
        if not exists:
            _rl_fail(ip)
        return _json({"ok": False, "dev_locked": err.startswith("Key đã đủ"), "loi": err}, 401)
    _rl_reset(ip)
    return _json({"ok": True, "het_han": rec["exp"], "con_lai_giay": max(0, int(rec["exp"] - time.time())),
                  "so_dev": len(rec.get("devs") or {}), "max_dev": _max_dev(rec)})


@app.route("/api/admin")
def api_admin_page():
    resp = Response(ADMIN_HTML, content_type="text/html; charset=utf-8")
    resp.headers["X-Robots-Tag"] = "noindex, nofollow"
    return resp


@app.route("/api/admin/login", methods=["POST"])
def api_admin_login():
    """Đăng nhập admin bằng MỘT ô key: {"key": "..."} (+ "username" khi key admin phụ chưa ai dùng) + HWID thiết bị (header X-HWID hoặc "hwid" trong body).
       Server tự phân loại: key admin phụ · key người dùng (không vào được trang admin) · mật khẩu admin chính · không tồn tại.
       Trả luôn "kind": main | sub | user | none | locked. (Còn nhận cả {"password"} cũ cho tool đã viết từ trước.)
       Admin chính (mật khẩu) không cần HWID. Key admin phụ: gắn thêm thiết bị nếu còn chỗ (max_dev), đủ chỗ rồi -> dev_locked."""
    ip = client_ip()
    w = _rl_wait(ip)
    if w:
        return _json({"ok": False, "kind": "locked", "loi": f"Nhập sai quá nhiều, thử lại sau {w} giây."}, 429)
    b = request.get_json(silent=True) or {}
    raw = str(b.get("key") or b.get("password") or "")[:128]
    k = _norm_key(raw)
    hw, alts, hfresh = req_hw_ids(b)
    ua = request.headers.get("User-Agent", "")
    now = int(time.time())
    with _kv_lock:
        d = _kv_load()
        rec = d["keys"].get(k) if k else None
        if rec:                                          # key có trong file -> phân loại theo type
            if rec["exp"] <= now:
                return _json({"ok": False, "kind": rec.get("type"), "loi": "Key này đã hết hạn."}, 403)
            if rec.get("type") != "sub":
                return _json({"ok": False, "kind": "user", "loi": "Key hợp lệ nhưng chỉ dùng để vào tool ở panel /api/html, không phải key admin."}, 403)
            if not hw:
                return _json({"ok": False, "kind": "sub", "loi": "Thiếu mã thiết bị (HWID) — hãy mở trang /api/admin bằng trình duyệt, hoặc tool phải gửi header X-HWID."}, 400)
            fresh = False
            if not rec.get("owner"):                     # key admin phụ chưa ai dùng -> nhập username, gắn username + thiết bị đầu tiên
                if not str(b.get("username") or "").strip():
                    return _json({"ok": False, "kind": "sub", "need_username": True, "loi": "Nhập username để kích hoạt. Key sẽ gắn với username này và thiết bị (HWID) bạn đang dùng."})
                name = _clean_username(b.get("username"))
                if not name:
                    return _json({"ok": False, "kind": "sub", "need_username": True, "loi": "Username 2-20 ký tự (chữ, số, dấu cách . _ -), không dùng 'admin'."}, 400)
                if any(r.get("type") == "sub" and str(r.get("owner") or "").lower() == name.lower() for r in d["keys"].values()):
                    return _json({"ok": False, "kind": "sub", "need_username": True, "loi": "Username này đã có người dùng, chọn tên khác."}, 400)
                rec["owner"], rec["bound"] = name, now
                fresh = True
            ok, err, ch = _dev_use(rec, hw, ip, ua, now, alts, hfresh)  # thiết bị đã gắn -> cho vào · chưa gắn mà còn chỗ -> gắn thêm · hết chỗ -> chặn tới khi admin chính reset
            if not ok:
                _rl_fail(ip)
                return _json({"ok": False, "kind": "sub", "dev_locked": True, "loi": err}, 403)
            if ch or fresh:
                try:
                    _kv_save(d)
                except OSError as e:
                    return _json({"ok": False, "kind": "sub", "loi": f"Không ghi được file key: {e}"}, 500)
            name = rec["owner"]
            _rl_reset(ip)
            return _json({"ok": True, "kind": "sub", "role": "sub", "name": name, "dev": len(rec.get("devs") or {}), "max_dev": _max_dev(rec),
                          "token": _tok_make("sub", name, k, hw)})
    if raw and hmac.compare_digest(_pw_hash(raw), ADMIN_PASS_HASH):   # không phải key trong file -> thử mật khẩu admin chính
        _rl_reset(ip)
        return _json({"ok": True, "kind": "main", "role": "main", "name": ADMIN_MAIN_NAME, "token": _tok_make("main", ADMIN_MAIN_NAME)})
    _rl_fail(ip)
    return _json({"ok": False, "kind": "none", "loi": "Không có key nào khớp (hoặc sai mật khẩu admin chính)."}, 403)


def _need_admin():
    s = _tok_check()
    return s, (None if s else _json({"ok": False, "loi": "chua dang nhap / phien het han"}, 401))


@app.route("/api/admin/keys")
def api_admin_keys():
    s, err = _need_admin()
    if err:
        return err
    now = time.time()
    keys = _kv_load()["keys"]
    made = {}
    for r in keys.values():
        if r.get("by") == "sub":
            made[r.get("by_name")] = made.get(r.get("by_name"), 0) + 1
    rows = []
    for k, r in keys.items():
        if s["r"] != "main" and not _own_user_key(s, r):
            continue                                    # admin phụ chỉ thấy key người dùng do chính mình tạo
        devs = r.get("devs") if isinstance(r.get("devs"), dict) else {}
        tb = sorted(({"hw": h, "lan_dau": v.get("first"), "gan_nhat": v.get("last"), "ip": v.get("ip"), "ua": v.get("ua", "")} for h, v in devs.items()),
                    key=lambda x: -(x["gan_nhat"] or 0))
        rows.append({"key": k, "loai": r.get("type"), "nguoi_tao": r.get("by_name"), "tao_luc": r.get("created"), "het_han": r["exp"],
                     "con_lai": max(0, int(r["exp"] - now)), "het": r["exp"] <= now, "ngay": r.get("days"), "ghi_chu": r.get("note", ""),
                     "dung_boi": r.get("owner"), "da_tao": made.get(r.get("owner"), 0) if r.get("type") == "sub" else None,
                     "max_dev": _max_dev(r), "so_dev": len(devs), "dung_luc": r.get("last"), "ip_cuoi": r.get("last_ip"), "thiet_bi": tb})
    rows.sort(key=lambda x: -(x["tao_luc"] or 0))
    return _json({"ok": True, "role": s["r"], "name": s["n"], "ngay": list(KEY_DAYS), "so_tb": list(KEY_DEV_OPTIONS), "keys": rows})


@app.route("/api/admin/keys/create", methods=["POST"])
def api_admin_keys_create():
    s, err = _need_admin()
    if err:
        return err
    b = request.get_json(silent=True) or {}
    kind = "sub" if b.get("type") == "sub" else "user"
    if kind == "sub" and s["r"] != "main":
        return _json({"ok": False, "loi": "chi admin chinh moi tao duoc key admin phu"}, 403)
    try:
        days = int(b.get("days"))
    except (TypeError, ValueError):
        days = 0
    if days not in KEY_DAYS:
        return _json({"ok": False, "loi": "han key khong hop le"}, 400)
    try:
        mdev = int(b.get("max_dev", KEY_DEV_DEFAULT))
    except (TypeError, ValueError):
        mdev = 0
    if mdev not in KEY_DEV_OPTIONS:
        return _json({"ok": False, "loi": "so thiet bi khong hop le"}, 400)
    try:
        cnt = max(1, min(int(b.get("count", 1)), 20))
    except (TypeError, ValueError):
        cnt = 1
    note = re.sub(r"[\x00-\x1f\x7f]", " ", str(b.get("note") or "")).strip()[:40]
    now = int(time.time())
    with _kv_lock:
        d = _kv_load()
        if len(d["keys"]) + cnt > KEY_MAX_TOTAL:
            return _json({"ok": False, "loi": "day file key, xoa bot key het han"}, 400)
        made = []
        for _ in range(cnt):
            k = _new_key("AD" if kind == "sub" else "SV", d["keys"])
            d["keys"][k] = {"type": kind, "by": s["r"], "by_name": s["n"], "created": now, "exp": now + days * 86400,
                            "days": days, "note": note, "owner": None, "max_dev": mdev, "devs": {}}
            made.append(k)
        try:
            _kv_save(d)
        except OSError as e:
            return _json({"ok": False, "loi": f"khong ghi duoc file key: {e}"}, 500)
    return _json({"ok": True, "keys": made, "het_han": now + days * 86400, "max_dev": mdev})


@app.route("/api/admin/keys/delete", methods=["POST"])
def api_admin_keys_delete():
    """Xóa 1 key {"key": "..."} · NHIỀU key {"keys": ["...", ...]} (admin phụ: key không phải của mình bị bỏ qua, đếm ở "bo_qua") · {"expired": true} (admin chính: dọn key hết hạn)."""
    s, err = _need_admin()
    if err:
        return err
    b = request.get_json(silent=True) or {}
    now = time.time()
    skipped = 0
    with _kv_lock:
        d = _kv_load()
        keys = d["keys"]
        if b.get("expired") and s["r"] == "main":        # dọn mọi key hết hạn
            dead = [k for k, r in keys.items() if r["exp"] <= now]
        else:
            lst = b.get("keys") if isinstance(b.get("keys"), list) else [b.get("key")]
            want = list(dict.fromkeys(x for x in (_norm_key(v) for v in lst[:KEY_MAX_TOTAL]) if x))
            if not want:
                return _json({"ok": False, "loi": "chua chon key nao"}, 400)
            dead, miss, denied = [], 0, 0
            for k in want:
                r = keys.get(k)
                if not r:
                    miss += 1
                elif not _own_user_key(s, r):
                    denied += 1
                else:
                    dead.append(k)
            skipped = miss + denied
            if not dead:
                return (_json({"ok": False, "loi": "chi xoa duoc key do ban tao"}, 403) if denied
                        else _json({"ok": False, "loi": "khong thay key"}, 404))
        for k in dead:
            keys.pop(k, None)
        try:
            _kv_save(d)
        except OSError as e:
            return _json({"ok": False, "loi": f"khong ghi duoc file key: {e}"}, 500)
    return _json({"ok": True, "da_xoa": len(dead), "bo_qua": skipped})


@app.route("/api/admin/keys/reset-dev", methods=["POST"])
@app.route("/api/admin/keys/reset-ip", methods=["POST"])    # tên cũ — giữ để tool đã viết từ trước không hỏng
def api_admin_keys_reset_dev():
    """Gỡ thiết bị đã gắn của 1 key: {"key": "..."} = gỡ TOÀN BỘ (máy nào dùng key trước sẽ được gắn lại) · thêm "hwid" = chỉ gỡ thiết bị đó.
    Admin chính: mọi key · admin phụ: key người dùng do mình tạo. Phiên admin phụ chạy trên thiết bị bị gỡ chết ngay vì _tok_check đòi HWID vẫn đang gắn."""
    s, err = _need_admin()
    if err:
        return err
    b = request.get_json(silent=True) or {}
    k = _norm_key(b.get("key"))
    hw = ""
    if b.get("hwid"):
        hw = _norm_hwid(b.get("hwid"))
        if not hw:
            return _json({"ok": False, "loi": "hwid khong hop le"}, 400)
    with _kv_lock:
        d = _kv_load()
        rec = d["keys"].get(k)
        if not rec:
            return _json({"ok": False, "loi": "khong thay key"}, 404)
        if not _own_user_key(s, rec):
            return _json({"ok": False, "loi": "chi reset duoc key do ban tao"}, 403)
        devs = rec.get("devs") if isinstance(rec.get("devs"), dict) else {}
        if hw:
            if hw not in devs:
                return _json({"ok": False, "loi": "khong thay thiet bi nay trong key"}, 404)
            devs.pop(hw)
            n = 1
        else:
            n = len(devs)
            devs = {}
        rec["devs"] = devs
        rec.pop("ip", None)                              # dọn trường IP của bản cũ (gắn theo IP mạng)
        rec.pop("ip_at", None)
        rec["dev_reset"] = int(time.time())
        try:
            _kv_save(d)
        except OSError as e:
            return _json({"ok": False, "loi": f"khong ghi duoc file key: {e}"}, 500)
    return _json({"ok": True, "da_go": n})


ADMIN_HTML = r"""<!doctype html>
<html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<meta name="theme-color" content="#0c1022">
<title>Quản trị SUNVIW</title>
<style>
:root{--bg:#0c1022;--pn:#151b35;--pn2:#1c2344;--ln:#273056;--tx:#eef0fb;--mu:#8f98bd;--au:#f2b33d;--au2:#ffd98a;--ok:#35d6a0;--no:#ff6b7d;--vi:#a395ff;color-scheme:dark}
*{box-sizing:border-box}
html{background:var(--bg)}
body{margin:0;min-height:100vh;color:var(--tx);font:15px/1.5 "Segoe UI",system-ui,-apple-system,Roboto,sans-serif;background:radial-gradient(800px 380px at 8% -8%,rgba(242,179,61,.11),transparent 60%),radial-gradient(700px 420px at 100% 0,rgba(163,149,255,.12),transparent 58%),var(--bg) fixed}
button,input,select{font:inherit;color:inherit}button{cursor:pointer}
:focus-visible{outline:2px solid var(--au);outline-offset:2px}
.w{max-width:980px;margin:0 auto;padding:22px 16px 70px}
.mu{color:var(--mu)}.s{font-size:13px}.mono{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
svg{flex:none;vertical-align:middle}
/* cổng đăng nhập */
.gate{max-width:440px;margin:9vh auto 0}
.mark{width:52px;height:52px;border-radius:15px;display:grid;place-items:center;background:linear-gradient(145deg,var(--au2),var(--au));color:#2a1c00;box-shadow:0 10px 30px -8px rgba(242,179,61,.55)}
.gate h1{font-size:30px;line-height:1.15;letter-spacing:-.02em;margin:22px 0 8px;font-weight:800}
.gate>p{margin:0 0 22px;color:var(--mu)}
.kf{position:relative;margin-bottom:0}
.kf>svg{position:absolute;left:16px;top:17px;color:var(--mu)}
.kf input{width:100%;height:56px;padding:0 82px 0 48px;background:var(--pn);border:1.5px solid var(--ln);border-radius:14px;font-size:17px;letter-spacing:.04em;transition:border-color .15s,box-shadow .15s}
.kf input:focus{outline:0;border-color:var(--au);box-shadow:0 0 0 4px rgba(242,179,61,.16)}
.kf button{position:absolute;right:8px;top:8px;height:40px;padding:0 12px;border-radius:10px;border:0;background:transparent;color:var(--mu)}
.kf button:hover{color:var(--tx)}
.go{width:100%;height:52px;margin-top:14px;border:0;border-radius:14px;background:linear-gradient(145deg,var(--au2),var(--au));color:#2a1c00;font-weight:800;font-size:16px;transition:transform .12s,filter .12s}
.go:hover{filter:brightness(1.06)}.go:active{transform:scale(.99)}.go:disabled{opacity:.6;cursor:wait}
.res{margin-top:16px;display:flex;gap:12px;align-items:flex-start;padding:13px 14px;border-radius:12px;border:1px solid var(--ln);background:var(--pn);font-size:14px;animation:pop .22s ease-out}
.res b{display:block;font-size:15px}.res .ic{margin-top:1px}
.res.bad{border-color:rgba(255,107,125,.55)}.res.bad .ic{color:var(--no)}
.res.warn{border-color:rgba(242,179,61,.55)}.res.warn .ic{color:var(--au)}
.res.good{border-color:rgba(53,214,160,.55)}.res.good .ic{color:var(--ok)}
@keyframes pop{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}
/* bảng điều khiển */
.top{display:flex;align-items:center;gap:14px;margin-bottom:18px}
.top .mark{width:42px;height:42px;border-radius:12px}
.top h1{margin:0;font-size:19px;font-weight:800;letter-spacing:-.01em}
.top .sp{flex:1}
.role{display:inline-block;margin-top:2px;font-size:12.5px;font-weight:700;padding:1px 9px;border-radius:99px;border:1px solid}
.role.m{color:var(--au);border-color:rgba(242,179,61,.5);background:rgba(242,179,61,.1)}
.role.s{color:var(--vi);border-color:rgba(163,149,255,.5);background:rgba(163,149,255,.1)}
.gh{display:inline-flex;align-items:center;gap:6px;height:36px;padding:0 12px;border-radius:10px;border:1px solid var(--ln);background:transparent;color:var(--mu);font-size:13.5px;transition:color .12s,border-color .12s}
.gh:hover{color:var(--tx);border-color:var(--mu)}.gh.dg:hover{color:var(--no);border-color:var(--no)}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));margin-bottom:18px;border-top:1px solid var(--ln);border-bottom:1px solid var(--ln)}
.stats div{padding:14px 16px;border-left:1px solid var(--ln)}.stats div:first-child{border-left:0;padding-left:2px}
.stats b{display:block;font-size:30px;line-height:1.1;font-weight:800;letter-spacing:-.02em;font-variant-numeric:tabular-nums}
.stats span{color:var(--mu);font-size:13px}
.pn{background:var(--pn);border:1px solid var(--ln);border-radius:16px;padding:18px;margin-bottom:16px}
.hd{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;margin-bottom:14px}
.hd h2,.pn>h2{margin:0;font-size:16px;font-weight:800}.hd .act{display:flex;gap:8px;flex-wrap:wrap}
.lb{color:var(--mu);font-size:13px;margin:14px 0 6px}
.seg{display:inline-flex;padding:3px;border-radius:12px;background:var(--bg);border:1px solid var(--ln);margin-top:12px}
.seg button{border:0;background:none;color:var(--mu);padding:7px 14px;border-radius:9px;font-size:14px}
.seg button.on{background:var(--pn2);color:var(--tx);box-shadow:0 0 0 1px var(--ln)}
.pills{display:flex;flex-wrap:wrap;gap:8px}
.pills button{height:36px;padding:0 14px;border-radius:99px;border:1px solid var(--ln);background:var(--bg);color:var(--mu);font-size:14px;transition:all .12s}
.pills button:hover{color:var(--tx)}.pills button.on{border-color:var(--au);color:var(--au2);background:rgba(242,179,61,.1)}
.fr{display:flex;gap:16px;flex-wrap:wrap}.fr .gr{flex:1 1 220px}
.step{display:inline-flex;align-items:center;border:1px solid var(--ln);border-radius:10px;background:var(--bg);height:40px}
.step button{width:38px;height:100%;border:0;background:none;color:var(--mu);font-size:18px}.step button:hover{color:var(--tx)}
.step b{min-width:30px;text-align:center;font-variant-numeric:tabular-nums}
input.f{width:100%;height:40px;padding:0 12px;border-radius:10px;border:1px solid var(--ln);background:var(--bg)}
input.f:focus{outline:0;border-color:var(--au)}
.mk{width:auto;padding:0 26px;height:44px;margin-top:18px;font-size:15px}
.newk{margin-top:16px;border:1px dashed rgba(53,214,160,.6);border-radius:12px;padding:6px 12px;background:rgba(53,214,160,.05);animation:pop .22s ease-out}
.newk div{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:7px 0}.newk div+div{border-top:1px solid var(--ln)}
.tb{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:6px}.tb .f{flex:1 1 220px}
.chips{display:flex;gap:6px;flex-wrap:wrap}
.chips button{height:40px;padding:0 13px;border-radius:10px;border:1px solid var(--ln);background:none;color:var(--mu);font-size:13.5px}
.chips button.on{color:var(--tx);background:var(--pn2);border-color:var(--mu)}
.rw{display:grid;grid-template-columns:minmax(0,1.5fr) minmax(0,1fr) minmax(0,1.25fr) auto;gap:8px 18px;align-items:center;padding:14px 2px;border-top:1px solid var(--ln)}
.rw:first-child{border-top:0}
.kk{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.kk .mono{font-size:13.5px;font-weight:600;letter-spacing:.02em;user-select:all;word-break:break-all}
.bd{display:inline-block;font-size:12px;font-weight:700;padding:1px 8px;border-radius:99px;border:1px solid var(--ln);color:var(--mu)}
.bd.sb{color:var(--vi);border-color:rgba(163,149,255,.5)}.bd.us{color:var(--ok);border-color:rgba(53,214,160,.45)}.bd.ex{color:var(--no);border-color:rgba(255,107,125,.5)}
.bar{height:4px;border-radius:4px;background:var(--bg);margin-top:6px;overflow:hidden}.bar i{display:block;height:100%;border-radius:4px;background:var(--ok)}.bar i.lo{background:var(--au)}.bar i.xx{background:var(--no)}
.ipb{display:inline-flex;align-items:center;gap:6px;margin-top:3px;padding:2px 8px;border-radius:8px;background:var(--bg);border:1px solid var(--ln);font-size:12.5px}
.sel{display:flex;align-items:center;gap:12px;flex-wrap:wrap;padding:10px 2px;border-bottom:1px solid var(--ln);font-size:13.5px}.sel .sp{flex:1}
.ck{display:inline-flex;align-items:center;cursor:pointer;gap:8px}.ck input{width:18px;height:18px;margin:0;accent-color:var(--au);cursor:pointer}
.dvb{display:inline-flex;align-items:center;gap:5px;padding:1px 8px;border-radius:99px;border:1px solid var(--ln);font-size:12.5px;color:var(--mu)}.dvb.full{color:var(--au);border-color:rgba(242,179,61,.5)}
.dv{grid-column:1/-1;margin-top:-2px}.dv summary{cursor:pointer;width:max-content}.dv summary:hover{color:var(--tx)}
.dvr{display:flex;align-items:center;gap:6px 14px;flex-wrap:wrap;padding:7px 10px;margin-top:6px;border-radius:10px;background:var(--bg);border:1px solid var(--ln)}.dvr .mono{font-size:13px}.dvr .mu{flex:1 1 220px}
.dvr .gh{height:30px;padding:0 10px}
.ra{display:flex;gap:6px;justify-content:flex-end}
.ib{width:36px;height:36px;padding:0;justify-content:center}
.emp{padding:34px 0 20px;text-align:center;color:var(--mu)}
dialog{border:1px solid var(--ln);border-radius:16px;background:var(--pn);color:var(--tx);padding:20px;max-width:380px;width:calc(100% - 32px)}
dialog::backdrop{background:rgba(5,8,20,.7);backdrop-filter:blur(2px)}
dialog p{margin:0 0 18px}dialog form{margin:0}.da{display:flex;gap:8px;justify-content:flex-end}
.da .go{width:auto;height:40px;margin:0;padding:0 18px;font-size:14px}.da .go.dgb{background:var(--no);color:#2b0710}
#ts{position:fixed;left:0;right:0;bottom:22px;display:flex;flex-direction:column;align-items:center;gap:8px;pointer-events:none;z-index:9}
#ts div{background:var(--pn2);border:1px solid var(--ln);border-radius:12px;padding:9px 16px;font-size:14px;box-shadow:0 10px 30px -10px #000;animation:pop .2s ease-out}#ts div.e{border-color:var(--no)}
@media(max-width:720px){.rw{grid-template-columns:1fr auto}.rw>:nth-child(2),.rw>:nth-child(3){grid-column:1/-1}.rw>:nth-child(4){grid-column:2;grid-row:1}.gate{margin-top:5vh}.stats b{font-size:26px}}
@media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
</style></head><body>
<div class="w" id="app"></div>
<dialog id="dlg"><form method="dialog"><p id="dm"></p><div class="da"><button class="gh" value="no">Hủy</button><button class="go dgb" value="ok" id="dok">Xác nhận</button></div></form></dialog>
<div id="ts"></div>
<script>
/*__HWID_JS__*/
const $=s=>document.querySelector(s);
const esc=s=>String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=t=>t?new Date(t*1000).toLocaleString('vi-VN'):'';
const left=s=>{if(s<=0)return 'đã hết hạn';const d=Math.floor(s/86400),h=Math.floor(s%86400/3600),m=Math.floor(s%3600/60);return 'còn '+(d?d+' ngày '+h+' giờ':h?h+' giờ '+m+' phút':m+' phút')};
const ago=t=>{const s=Math.max(0,Math.floor(Date.now()/1000-t));return s<60?'vừa xong':s<3600?Math.floor(s/60)+' phút trước':s<86400?Math.floor(s/3600)+' giờ trước':Math.floor(s/86400)+' ngày trước'};
const shortHw=h=>String(h).length>14?String(h).slice(0,8)+'…'+String(h).slice(-4):String(h);
const DAYLBL={1:'1 ngày',2:'2 ngày',7:'7 ngày',14:'14 ngày',30:'1 tháng',60:'2 tháng',90:'3 tháng',180:'6 tháng',365:'1 năm'};
const ic=p=>'<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'+p+'</svg>';
const I={key:ic('<circle cx="8" cy="15" r="4"/><path d="M10.8 12.2 20 3m-4 4 3 3m-6-1 2 2"/>'),lock:ic('<path d="M7 11V8a5 5 0 0 1 10 0v3"/><rect x="5" y="11" width="14" height="10" rx="2"/>'),
 copy:ic('<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V6a2 2 0 0 1 2-2h9"/>'),del:ic('<path d="M4 7h16M10 11v6m4-6v6M6 7l1 13h10l1-13M9 7V4h6v3"/>'),
 rf:ic('<path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7"/>'),ok:ic('<path d="m5 12 5 5 9-10"/>'),x:ic('<path d="M6 6l12 12M18 6 6 18"/>'),info:ic('<circle cx="12" cy="12" r="9"/><path d="M12 8v5m0 3h.01"/>'),
 rs:ic('<path d="M3 12a9 9 0 1 0 3-6.7M3 4v5h5"/>'),dev:ic('<rect x="2" y="4" width="20" height="12" rx="2"/><path d="M8 20h8M12 16v4"/>'),out:ic('<path d="M10 4H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h4M16 8l4 4-4 4M20 12H9"/>')};
let S=null;try{S=JSON.parse(sessionStorage.getItem('as')||'null')}catch(e){}
let need=false,busy=false,KEYS=[],DAYS=[1,2,7,14,30,60,90,180,365],NEW=[],F={t:'all',q:''},CF={type:'user',days:30,n:1,dev:1},DEVO=[1,2,3,5,10,20,50],SEL=new Set(),OPEN=new Set();
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
function toast(m,bad){const e=document.createElement('div');if(bad)e.className='e';e.textContent=m;$('#ts').appendChild(e);setTimeout(()=>e.remove(),2600)}
function ask(msg,ok){return new Promise(r=>{const d=$('#dlg');$('#dm').textContent=msg;$('#dok').textContent=ok||'Xác nhận';d.onclose=()=>r(d.returnValue==='ok');d.returnValue='no';d.showModal()})}
async function api(p,body){
  const o={headers:Object.assign({'Content-Type':'application/json'},HWID_HDR)};
  if(S)o.headers['X-Admin-Token']=S.token;
  if(body!==undefined){o.method='POST';o.body=JSON.stringify(body)}
  let r,j={};
  try{r=await fetch(p,o);j=await r.json()}catch(e){j={ok:false,loi:'Không kết nối được server'}}
  if(r&&r.status===401&&S){S=null;sessionStorage.removeItem('as');renderLogin('Phiên đã hết hạn hoặc thiết bị này đã bị gỡ khỏi key — nhập key lại để vào.')}
  return j;
}
/* ── ĐĂNG NHẬP: 1 ô key, server tự nhận diện ── */
function showRes(c,t,d){$('#res').innerHTML=t?`<div class="res ${c}"><span class="ic">${I[c==='good'?'ok':c==='warn'?'info':'x']}</span><div><b>${esc(t)}</b>${d?`<span class="mu">${esc(d)}</span>`:''}</div></div>`:''}
function renderLogin(msg){
  need=false;
  $('#app').innerHTML=`<div class="gate"><div class="mark">${I.key.replace(/18/g,'26')}</div><h1>Nhập key để vào quản trị</h1>
  <p>Chỉ cần một ô. Hệ thống tự nhận ra đây là admin chính, admin phụ hay key không dùng được ở trang này.</p>
  <div class="kf">${I.key}<input id="k" type="password" autocomplete="off" spellcheck="false" placeholder="Dán key hoặc mật khẩu admin" autofocus><button type="button" id="eye">Hiện</button></div>
  <div id="unw" hidden><div class="lb">Key này chưa ai dùng — chọn username của bạn (gắn vĩnh viễn với key)</div><div class="kf"><input id="un" maxlength="20" autocomplete="off" placeholder="Ví dụ: Dark" style="padding:0 16px"></div></div>
  <button class="go" id="go">Vào</button><div id="res"></div></div>`;
  if(msg)showRes('warn',msg);
}
async function login(){
  if(busy)return;const k=$('#k').value.trim();
  if(!k){showRes('bad','Chưa nhập key','Dán key vào ô phía trên rồi bấm Vào.');return}
  busy=true;const b=$('#go');b.disabled=true;b.textContent='Đang kiểm tra…';
  const body={key:k};if(need&&$('#un'))body.username=$('#un').value.trim();
  const j=await api('/api/admin/login',body);
  busy=false;b.disabled=false;b.textContent='Vào';
  if(j.ok){
    showRes('good',j.role==='main'?'Nhận diện: Admin chính':'Nhận diện: Admin phụ · '+j.name,j.role==='sub'?'Thiết bị này đã gắn với key ('+j.dev+'/'+j.max_dev+' thiết bị).':'Đang mở bảng quản trị…');
    await sleep(650);S={token:j.token,role:j.role,name:j.name};sessionStorage.setItem('as',JSON.stringify(S));need=false;await loadKeys();return}
  if(j.need_username){need=true;$('#unw').hidden=false;showRes('warn','Nhận diện: key admin phụ mới',j.loi||'');$('#un').focus();return}
  if(j.dev_locked)return showRes('bad','Key đã đủ số thiết bị',j.loi);
  const t={user:['warn','Đây là key người dùng'],none:['bad','Không tìm thấy key này'],locked:['bad','Tạm khóa vì nhập sai nhiều lần']}[j.kind]||['bad','Không vào được'];
  showRes(t[0],t[1],j.loi||'');
}
/* ── BẢNG ĐIỀU KHIỂN ── */
async function loadKeys(){
  const j=await api('/api/admin/keys');if(!S)return;
  if(j.ok){KEYS=j.keys;DAYS=j.ngay||DAYS;DEVO=j.so_tb||DEVO;const have=new Set(KEYS.map(r=>r.key));SEL=new Set([...SEL].filter(k=>have.has(k)))}
  paint();
}
const isMain=()=>S&&S.role==='main';
function stats(){
  const live=KEYS.filter(r=>!r.het).length,a=[[KEYS.length,isMain()?'Tổng key':'Key của bạn'],[live,'Còn hạn'],[KEYS.length-live,'Hết hạn']];
  if(isMain()){const sb=KEYS.filter(r=>r.loai==='sub');a.push([sb.length,'Key admin phụ'],[KEYS.reduce((n,r)=>n+r.so_dev,0),'Thiết bị đang gắn'])}
  return a.map(([n,l])=>`<div><b>${n}</b><span>${l}</span></div>`).join('');
}
function renderDash(){
  const m=isMain();
  $('#app').innerHTML=`<div class="top"><div class="mark">${I.key.replace(/18/g,'22')}</div><div><h1>SUNVIW · Quản trị</h1><span class="role ${m?'m':'s'}">${m?'Admin chính':'Admin phụ · '+esc(S.name)}</span></div><div class="sp"></div><button class="gh" id="out">${I.out} Đăng xuất</button></div>
  <div class="stats" id="stats"></div>
  <section class="pn"><h2>Tạo key mới</h2>
  ${m?`<div class="seg" id="ct"><button data-t="user" class="on">Key người dùng</button><button data-t="sub">Key admin phụ</button></div>`:''}
  <div class="lb">Thời hạn</div><div class="pills" id="cd">${DAYS.map(d=>`<button data-d="${d}" class="${d===CF.days?'on':''}">${DAYLBL[d]||d+' ngày'}</button>`).join('')}</div>
  <div class="lb">Số thiết bị tối đa mỗi key <span class="mu s">(1 key dùng được trên bấy nhiêu máy)</span></div><div class="pills" id="cv">${DEVO.map(v=>`<button data-v="${v}" class="${v===CF.dev?'on':''}">${v} thiết bị</button>`).join('')}</div>
  <div class="fr"><div><div class="lb">Số lượng</div><div class="step"><button data-n="-1" aria-label="Giảm">−</button><b id="cn">${CF.n}</b><button data-n="1" aria-label="Tăng">+</button></div></div>
  <div class="gr"><div class="lb">Ghi chú (không bắt buộc)</div><input class="f" id="cnote" maxlength="40" placeholder="Ví dụ: khách A"></div></div>
  <button class="go mk" id="mk">Tạo key</button><div id="newk"></div></section>
  <section class="pn"><div class="hd"><h2>Danh sách key <span class="mu s" id="cnt"></span></h2><div class="act"><button class="gh" id="rf">${I.rf} Làm mới</button>${m?`<button class="gh dg" id="clean">${I.del} Dọn key hết hạn</button>`:''}</div></div>
  <div class="tb"><input class="f" id="fq" placeholder="Tìm key, người tạo, ghi chú…"><div class="chips" id="ft">${[['all','Tất cả'],['live','Còn hạn'],['exp','Hết hạn']].concat(m?[['user','Người dùng'],['sub','Admin phụ']]:[]).map(c=>`<button data-f="${c[0]}" class="${F.t===c[0]?'on':''}">${c[1]}</button>`).join('')}</div></div>
  <div class="sel" id="selbar"></div><div id="tbl"></div></section>`;
}
function paint(){
  if(!$('#tbl'))renderDash();
  $('#stats').innerHTML=stats();renderNew();renderTable();
}
function renderNew(){
  const el=$('#newk');if(!el)return;
  el.innerHTML=NEW.length?`<div class="newk">${NEW.map(k=>`<div><span class="mono">${esc(k)}</span><button class="gh" data-copy="${esc(k)}">${I.copy} Sao chép</button></div>`).join('')}${NEW.length>1?`<div><span class="mu">Cả ${NEW.length} key</span><button class="gh" data-copy="${esc(NEW.join('\n'))}">${I.copy} Sao chép hết</button></div>`:''}</div>`:'';
}
function useBox(r,noLast){
  return `<div class="s" style="margin-top:4px"><span class="dvb ${r.so_dev>=r.max_dev?'full':''}">${I.dev.replace(/18/g,'14')} ${r.so_dev}/${r.max_dev} thiết bị</span></div>`+(noLast?'':(r.dung_luc?`<div class="s">Dùng gần nhất: ${esc(fmt(r.dung_luc))} <span class="mu">· ${esc(ago(r.dung_luc))}${r.ip_cuoi?' · IP '+esc(r.ip_cuoi):''}</span></div>`:`<div class="s mu">Chưa dùng lần nào</div>`));
}
function devList(r){
  if(!r.thiet_bi||!r.thiet_bi.length)return '';
  return `<details class="dv" data-k="${esc(r.key)}"${OPEN.has(r.key)?' open':''}><summary class="s mu">Xem ${r.thiet_bi.length} thiết bị đã gắn</summary>${r.thiet_bi.map(t=>`<div class="dvr"><span class="mono" title="${esc(t.hw)}">${esc(shortHw(t.hw))}</span><span class="mu s">IP ${esc(t.ip||'?')} · gắn ${esc(fmt(t.lan_dau))} · dùng gần nhất ${esc(fmt(t.gan_nhat))} (${esc(ago(t.gan_nhat))})</span><button class="gh dg" data-rd="${esc(r.key)}" data-hw="${esc(t.hw)}" title="Gỡ thiết bị này khỏi key">Gỡ</button></div>`).join('')}</details>`;
}
function row(r){
  const m=isMain(),sub=r.loai==='sub',pct=r.ngay?Math.max(0,Math.min(100,r.con_lai/(r.ngay*86400)*100)):0;
  let who;
  if(sub&&m)who=(r.dung_boi?`<div><b>${esc(r.dung_boi)}</b> <span class="mu s">· đã tạo ${r.da_tao} key</span></div>`:`<span class="mu">Chưa ai kích hoạt</span>`)+useBox(r,!r.dung_boi);
  else who=`<div class="mu s">${m?'Tạo bởi '+esc(r.nguoi_tao||''):''}</div><div>${esc(r.ghi_chu||'')}</div>`+useBox(r);
  return `<div class="rw"><div><div class="kk"><label class="ck" title="Chọn để xóa nhiều key"><input type="checkbox" data-sel="${esc(r.key)}"${SEL.has(r.key)?' checked':''}></label><span class="mono">${esc(r.key)}</span><span class="bd ${sub?'sb':'us'}">${sub?'admin phụ':'người dùng'}</span>${r.het?'<span class="bd ex">hết hạn</span>':''}</div></div>
  <div><div class="s">${esc(fmt(r.het_han))}</div><div class="s ${r.het?'':'mu'}" style="${r.het?'color:var(--no)':''}">${esc(left(r.con_lai))}${r.ngay?' · gói '+esc(DAYLBL[r.ngay]||r.ngay+' ngày'):''}</div><div class="bar"><i class="${r.het?'xx':pct<20?'lo':''}" style="width:${pct}%"></i></div></div>
  <div>${who}</div>
  <div class="ra"><button class="gh ib" data-copy="${esc(r.key)}" title="Sao chép" aria-label="Sao chép">${I.copy}</button>${r.so_dev?`<button class="gh ib" data-rs="${esc(r.key)}" title="Reset thiết bị" aria-label="Reset thiết bị">${I.rs}</button>`:''}<button class="gh dg ib" data-del="${esc(r.key)}" title="Xóa" aria-label="Xóa">${I.del}</button></div>${devList(r)}</div>`;
}
function visible(){
  const q=(F.q||'').toLowerCase();
  return KEYS.filter(r=>(F.t==='all'||(F.t==='live'?!r.het:F.t==='exp'?r.het:r.loai===F.t))&&(!q||[r.key,r.nguoi_tao,r.ghi_chu,r.dung_boi,r.ip_cuoi].join(' ').toLowerCase().includes(q)));
}
function renderSel(){
  const el=$('#selbar');if(!el)return;
  const vis=visible(),n=SEL.size,all=vis.length>0&&vis.every(r=>SEL.has(r.key));
  el.innerHTML=`<label class="ck"><input type="checkbox" id="selall"${all?' checked':''}${vis.length?'':' disabled'}><span>Chọn tất cả (${vis.length})</span></label><span class="mu">${n?'Đã chọn <b style="color:var(--tx)">'+n+'</b> key':'Tích ô vuông ở từng key để chọn nhiều key rồi xóa một lượt'}</span><div class="sp"></div>${n?`<button class="gh" id="selclr">${I.x} Bỏ chọn</button><button class="gh dg" id="bulk" style="color:var(--no);border-color:var(--no)">${I.del} Xóa ${n} key đã chọn</button>`:''}`;
}
function renderTable(){
  const rows=visible();
  $('#cnt').textContent='('+rows.length+')';
  $('#tbl').innerHTML=rows.length?rows.map(row).join(''):'<div class="emp">'+(KEYS.length?'Không có key nào khớp bộ lọc.':'Chưa có key nào. Tạo key đầu tiên ở khung phía trên.')+'</div>';
  renderSel();
}
document.addEventListener('click',async e=>{
  const b=e.target.closest('button');if(!b)return;const d=b.dataset;
  if(b.id==='go')return login();
  if(b.id==='eye'){const k=$('#k');k.type=k.type==='password'?'text':'password';b.textContent=k.type==='password'?'Hiện':'Ẩn';return}
  if(b.id==='out'){S=null;sessionStorage.removeItem('as');NEW=[];return renderLogin()}
  if(b.id==='rf'){await loadKeys();return toast('Đã làm mới')}
  if(d.copy!==undefined){try{await navigator.clipboard.writeText(d.copy);toast('Đã sao chép')}catch(x){prompt('Sao chép:',d.copy)}return}
  if(d.t&&b.parentNode.id==='ct'){CF.type=d.t;b.parentNode.querySelectorAll('button').forEach(x=>x.classList.toggle('on',x===b));return}
  if(d.d){CF.days=+d.d;b.parentNode.querySelectorAll('button').forEach(x=>x.classList.toggle('on',x===b));return}
  if(d.v){CF.dev=+d.v;b.parentNode.querySelectorAll('button').forEach(x=>x.classList.toggle('on',x===b));return}
  if(b.id==='selclr'){SEL.clear();renderTable();return}
  if(b.id==='bulk'){
    const ks=[...SEL];if(!ks.length)return;
    if(!await ask('Xóa '+ks.length+' key đã chọn ('+ks.slice(0,3).join(', ')+(ks.length>3?'…':'')+')? Người đang dùng các key này sẽ bị đăng xuất ngay.','Xóa '+ks.length+' key'))return;
    const j=await api('/api/admin/keys/delete',{keys:ks});
    if(j.ok){SEL.clear();NEW=NEW.filter(k=>!ks.includes(k));await loadKeys();toast('Đã xóa '+j.da_xoa+' key'+(j.bo_qua?' (bỏ qua '+j.bo_qua+')':''))}else toast(j.loi||'Lỗi',1);return}
  if(d.n){CF.n=Math.max(1,Math.min(20,CF.n+(+d.n)));$('#cn').textContent=CF.n;return}
  if(d.f){F.t=d.f;b.parentNode.querySelectorAll('button').forEach(x=>x.classList.toggle('on',x===b));renderTable();return}
  if(b.id==='mk'){
    const j=await api('/api/admin/keys/create',{type:isMain()?CF.type:'user',days:CF.days,count:CF.n,max_dev:CF.dev,note:$('#cnote').value});
    if(j.ok){NEW=j.keys;await loadKeys();toast('Đã tạo '+j.keys.length+' key')}else toast(j.loi||'Lỗi',1);return}
  if(d.del){if(!await ask('Xóa key '+d.del+'? Người đang dùng key này sẽ bị đăng xuất ngay.','Xóa key'))return;const j=await api('/api/admin/keys/delete',{key:d.del});if(j.ok){NEW=NEW.filter(k=>k!==d.del);await loadKeys();toast('Đã xóa key')}else toast(j.loi||'Lỗi',1);return}
  if(d.rs){if(!await ask('Reset TOÀN BỘ thiết bị đang gắn của key '+d.rs+'? Máy nào dùng key trước sẽ được gắn lại; phiên admin phụ đang mở trên các máy cũ bị đăng xuất.','Reset thiết bị'))return;const j=await api('/api/admin/keys/reset-dev',{key:d.rs});if(j.ok){await loadKeys();toast('Đã gỡ '+j.da_go+' thiết bị')}else toast(j.loi||'Lỗi',1);return}
  if(d.rd){if(!await ask('Gỡ thiết bị '+shortHw(d.hw)+' khỏi key '+d.rd+'?','Gỡ thiết bị'))return;const j=await api('/api/admin/keys/reset-dev',{key:d.rd,hwid:d.hw});if(j.ok){await loadKeys();toast('Đã gỡ thiết bị')}else toast(j.loi||'Lỗi',1);return}
  if(b.id==='clean'){if(!await ask('Xóa toàn bộ key đã hết hạn?','Xóa hết'))return;const j=await api('/api/admin/keys/delete',{expired:true});if(j.ok){await loadKeys();toast('Đã xóa '+j.da_xoa+' key')}else toast(j.loi||'Lỗi',1)}
});
document.addEventListener('input',e=>{if(e.target.id==='fq'){F.q=e.target.value;renderTable()}});
document.addEventListener('change',e=>{
  const t=e.target;
  if(t.dataset&&t.dataset.sel){t.checked?SEL.add(t.dataset.sel):SEL.delete(t.dataset.sel);renderSel();return}
  if(t.id==='selall'){visible().forEach(r=>t.checked?SEL.add(r.key):SEL.delete(r.key));renderTable()}
});
document.addEventListener('toggle',e=>{const t=e.target;if(t.classList&&t.classList.contains('dv')){t.open?OPEN.add(t.dataset.k):OPEN.delete(t.dataset.k)}},true);
document.addEventListener('keydown',e=>{if(e.key==='Enter'&&['k','un'].includes(e.target.id))login()});
setInterval(()=>{if(S&&$('#tbl'))loadKeys()},60000);
if(S)loadKeys();else renderLogin();
</script></body></html>
"""
ADMIN_HTML = ADMIN_HTML.replace("/*__HWID_JS__*/", HWID_JS)


@app.route("/api/ips")
def api_ips():
    """Danh sách IP đang dùng + đã từng dùng (tab IP của panel). Có SUNVIW_ADMIN_KEY thì cần header X-Admin-Key hoặc ?key=."""
    if IP_ADMIN_KEY:
        k = request.headers.get("X-Admin-Key") or request.args.get("key", "")
        if not hmac.compare_digest(str(k).encode("utf-8"), IP_ADMIN_KEY.encode("utf-8")):
            return _json({"ok": False, "khoa": True, "loi": "can admin key (header X-Admin-Key hoac ?key=)"}, 403)
    return _json(ip_snapshot(client_ip()))


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
    page = PANEL_HTML.replace("__SHOW__", str(PANEL_DEFAULT_SHOW)).replace("__MAX__", str(HIST_MAX)).replace("/*__HWID_JS__*/", HWID_JS)
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
                     loai=list(ZF_EXCLUDE), hist_keep=HIST_KEEP, persist_keep=PERSIST_KEEP),
             af=dict(bat=AF_ENABLED, flip_low=AF_FLIP_LOW, flip_high=AF_FLIP_HIGH, min_games=AF_MIN_GAMES, mode_window=AF_MODE_WINDOW,
                     mode_min=AF_MODE_MIN, mode_below=AF_MODE_BELOW, be_final_af=AF_FLIP_FINAL),
             ips=ip_health())
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
    return _json({"ok": True, "api": "SUNVIW"})          # cố ý KHÔNG liệt kê endpoint (/api/html, /api/admin ...)


# Chạy dưới gunicorn (Railway) thì main() không được gọi -> bật poller ngay khi import.
if __name__ != "__main__":
    ensure_poller()


def main():
    global UPSTREAM_URL, POLL_SEC, FLIP_FINAL, LC_FLIP_FINAL, WR_FLIP_WEIGHT, LC_WR_FLIP_WEIGHT
    global ZF_ENABLED, ZF_WINDOW, ZF_Z, ZF_MIN_GAMES, ZF_FLIP_FINAL
    global AF_ENABLED, AF_FLIP_LOW, AF_FLIP_HIGH, AF_MIN_GAMES, AF_MODE_WINDOW, AF_MODE_BELOW, AF_FLIP_FINAL
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
    ag = ap.add_mutually_exclusive_group()
    ag.add_argument("--af", action="store_true", help="BẬT AF (auto-flip + CAO/THẤP + bẻ theo WR chế độ) cho SUN")
    ag.add_argument("--no-af", action="store_true", help="TẮT AF, quay về cách chốt cũ của SUN")
    ap.add_argument("--af-low", type=float, default=None, help="AF: WR logic dưới mức này (%%) -> bẻ logic (mặc định AF_FLIP_LOW_DEFAULT)")
    ap.add_argument("--af-high", type=float, default=None, help="AF: WR logic trên mức này (%%) -> bẻ logic (mặc định AF_FLIP_HIGH_DEFAULT)")
    ap.add_argument("--af-min", type=int, default=None, help="AF: số ván đã chấm tối thiểu mới bẻ logic / chia nhóm (mặc định AF_MIN_GAMES_DEFAULT)")
    ap.add_argument("--af-mode-window", type=int, default=None, help="AF: số ván gần nhất của mỗi chế độ để tính WR chế độ (mặc định AF_MODE_WINDOW_DEFAULT)")
    ap.add_argument("--af-mode-below", type=float, default=None, help="AF: WR chế độ dưới mức này (%%) -> bẻ final (mặc định AF_MODE_BELOW_DEFAULT)")
    afg = ap.add_mutually_exclusive_group()
    afg.add_argument("--af-flip", action="store_true", help="BẺ riêng kết quả AF (đảo TÀI<->XỈU)")
    afg.add_argument("--af-no-flip", action="store_true", help="TẮT bẻ riêng kết quả AF")
    a = ap.parse_args()
    UPSTREAM_URL, POLL_SEC = a.upstream, a.poll
    if a.af:
        AF_ENABLED = True
    elif a.no_af:
        AF_ENABLED = False
    if a.af_low is not None:
        AF_FLIP_LOW = a.af_low
    if a.af_high is not None:
        AF_FLIP_HIGH = a.af_high
    if a.af_min is not None:
        AF_MIN_GAMES = a.af_min
    if a.af_mode_window is not None:
        AF_MODE_WINDOW = a.af_mode_window
    if a.af_mode_below is not None:
        AF_MODE_BELOW = a.af_mode_below
    if a.af_flip:
        AF_FLIP_FINAL = True
    elif a.af_no_flip:
        AF_FLIP_FINAL = False
    af_apply_limits()                              # chuẩn hoá tham số AF
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
    print(f"be final SUN ->  {'BAT' if FLIP_FINAL else 'TAT'}  (chi ap cho van quay ve cach cu; van do ZF / AF chot khong bi be)")
    print(f"IP          ->  theo doi {'BAT' if IP_TRACK_ENABLED else 'TAT'} · dang dung = co request trong {IP_ACTIVE_SEC}s · tin proxy {'BAT' if IP_TRUST_PROXY else 'TAT'} · admin key {'CO' if IP_ADMIN_KEY else 'KHONG (ai mo panel cung thay danh sach IP)'} · file {IP_PATH}")
    print(f"AF SUN      ->  {'BAT' if AF_ENABLED else 'TAT'} · be logic WR < {AF_FLIP_LOW:g}% hoac > {AF_FLIP_HIGH:g}% (toi thieu {AF_MIN_GAMES} van) · be che do CAO/THAP khi WR {AF_MODE_WINDOW} van gan nhat cua che do < {AF_MODE_BELOW:g}% (can {AF_MODE_MIN} van) · be rieng AF {'BAT' if AF_FLIP_FINAL else 'TAT'}")
    print(f"ZF SUN      ->  {'BAT' if ZF_ENABLED else 'TAT'} · xet {ZF_WINDOW} van gan nhat · |z| >= {ZF_Z} · toi thieu {ZF_MIN_GAMES} van · be rieng ZF {'BAT' if ZF_FLIP_FINAL else 'TAT'} · loai {list(ZF_EXCLUDE) or 'khong'} · giu lich su {HIST_KEEP} phien")
    print(f"WR          ->  xet {WR_WINDOW} van gan nhat, trong so cao nhat x{WR_WEIGHT_NEWEST}, flip trong so {'BAT (cu nhat nang nhat)' if WR_FLIP_WEIGHT else 'TAT (moi nhat nang nhat)'}, trong so (cu -> moi): "
          + " · ".join(f"{w:.2f}" for w in wr_weights_full()))
    print(f"KEY/ADMIN   ->  trang admin /api/admin (1 o nhap key, tu nhan dien · moi key gan HWID thiet bi (nhieu thiet bi / key, admin chinh + admin phu deu chon duoc) · bat buoc HWID {'BAT' if HWID_REQUIRED else 'TAT'}) · mat khau admin chinh {'tu env SUNVIW_MAIN_PASS' if _ENV_MAIN_PASS else 'tu hash mac dinh trong code (nen dat SUNVIW_MAIN_PASS)'} · bat key cho API {'BAT' if KEY_GATE_API else 'TAT'} · file key {KEYS_PATH}")
    app.run(host=a.host, port=a.port, threaded=True)


if __name__ == "__main__":
    main()
