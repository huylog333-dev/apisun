# -*- coding: utf-8 -*-
"""
LC79 SERVER — TÁCH RIÊNG GAME LC (2 BÀN: LC MD5 + LC HŨ) từ sunviw_api.py · KHÔNG có auto cược · KHÔNG có Sun / Hit.

Phần LC được TRÍCH NGUYÊN VĂN từ file gốc (bộ 13 logic SEQ13v6 · WR có trọng số · AF auto-flip + CAO/THẤP · config RIÊNG từng bàn · poller · file data · hệ key / HWID / bảo mật),
không viết lại thuật toán nên kết quả dự đoán giống hệt bản gốc với cùng dữ liệu + cùng config.

Chạy:
    pip install flask
    export SUNVIW_MAIN_PASS='mat-khau-admin-it-nhat-16-ky-tu'      # BẮT BUỘC nên đặt (không đặt = mật khẩu TẠM ngẫu nhiên in ra log, mất khi restart)
    python lc79_server.py                                          # mặc định http://0.0.0.0:5000   (--host / --port; Railway tự dùng biến PORT)
    gunicorn lc79_server:app --workers 1 --threads 8 --bind 0.0.0.0:$PORT      # chạy production: BẮT BUỘC --workers 1 (poller + phiên admin nằm trong RAM)

Endpoint (tool khách — đều đòi KEY LC + HWID: header X-User-Key + X-HWID, hoặc ?key=...&hwid=...):
    GET  /api/predictlcmd5            [LC MD5] dự đoán phiên kế tiếp   (alias cũ: /api/predicttele68txmd5)
    GET  /api/predictlchu             [LC HŨ]  dự đoán phiên kế tiếp
         ...?hist=N                   thêm lich_su: N ván đúng/sai gần nhất (tool khách tối đa SUNVIW_TOOL_HIST_MAX = 60)
    POST /api/key/check               xác thực key + gắn thiết bị + kích hoạt:  {"key":"...","hwid":"..."}  (tuỳ chọn "game":"lc79")
    GET  /api/notice?game=lc79        thông báo của admin tới tool (chỉ đọc)
    GET  /health                      công khai, chỉ {"ok":true}

Quản trị (CHỈ qua đường BÍ MẬT /<ADMIN_SLUG> — slug in ra log lúc khởi động; đặt SUNVIW_ADMIN_PATH để tự chọn; /api/admin* gọi trực tiếp từ ngoài luôn 404):
    GET  /<slug>                      trang tạo key tạm (1 ô nhập: mật khẩu admin chính / key admin phụ) — tạo · xem · xóa · cộng ngày · gỡ thiết bị · off server · tính lại · thông báo
    Mọi request admin phải kèm phiên + chữ ký HMAC (X-Admin-Token + X-Ts / X-Nonce / X-Sig) y hệt bản gốc → CẦN HTTPS (hoặc localhost) để trình duyệt ký được.
    (admin chính, qua phiên ký) GET /api/admin/health · GET /api/ips · POST /api/history/clear|regrade|wipe · GET /api/predictlc*?detail=1&hist=N (xem đủ chi tiết AF / WR từng logic)

Giữ nguyên so với bản gốc (không đổi tên để KHÔNG mất data / key đang chạy):
    · file data:  tele68_txmd5.json (LC MD5) · lc_hu.json (LC Hũ) · sunviw_keys.json (key) · sun15_histclear.json · sunviw_offserver.json · sunviw_notice.json · sunviw_ips.json
    · biến môi trường: SUNVIW_* · LC_ENABLED · LC_MD5_API_URL · LC_HU_API_URL · LC_REFERER · LC_MD5_PATH · LC_HU_PATH · LCMD5_<TÊN> · LCHU_<TÊN> (xem khối "CONFIG LC")
    · key game "lc79" (tiền tố LC79-): 1 key dùng được CẢ 2 bàn. Key Sun / Hit / Auto cược nằm trong file key (nếu bạn copy file cũ sang) vẫn bị CHẶN, không dùng được LC.

Đã BỎ so với file gốc: Sun · Hit · auto cược / auto rút · panel /api/html + duyệt thiết bị panel · trang admin gốc (thay bằng trang tạo key tạm ở trên).
"""
import argparse
import atexit
import collections as _collections
import hashlib
import hmac
import ipaddress
import json
import math
import os
import re
import secrets
import shutil
import sys
import threading
import time
import unicodedata
import urllib.request
from fractions import Fraction


# ═══════════════════════════════════════════════════════════════════════════
#  ⚙  CẤU HÌNH MẶC ĐỊNH CỦA BỘ MÁY DỰ ĐOÁN (trích nguyên văn từ file gốc)
#  Mỗi bàn LC dùng config RIÊNG ở khối "CONFIG LC" bên dưới (LC_MD5_CFG / LC_HU_CFG); các giá trị ở đây chỉ là mặc định của hàm (cfg=SUN) — GIỮ để bộ hàm chạy y như bản gốc.
# ═══════════════════════════════════════════════════════════════════════════

def _env_bool(name, default):
    """Đọc biến môi trường dạng bật/tắt; không đặt hoặc giá trị lạ -> dùng `default`."""
    v = os.environ.get(name, "").strip().lower()
    if v in ("1", "true", "yes", "on"):
        return True
    if v in ("0", "false", "no", "off"):
        return False
    return default


def _env_num(name, default, cast):
    v = os.environ.get(name, "").strip()
    if not v:
        return default
    try:
        return cast(v)
    except ValueError:
        return default


# ═══════════════════════════════════════════════════════════════════════════
#  🔀  CONFIG AF (AUTO-FLIP + CAO/THẤP + BẺ THEO WR CHẾ ĐỘ) — CÁCH CHỐT FINAL CỦA SUN  —  CHỈNH Ở ĐÂY
# ═══════════════════════════════════════════════════════════════════════════
#   Port từ SUNVIW_9logics_autoflip_auto.html. WR từng logic = WR CÓ TRỌNG SỐ của SUN (WR_WINDOW / WR_DECAY / WR_FLOOR / WR_WEIGHT_NEWEST / WR_FLIP_WEIGHT).
#   Bước 1  bẻ logic     : WR < AF_FLIP_LOW -> đảo phiếu logic · WR > AF_FLIP_HIGH -> đảo phiếu logic (WR dùng = 100 − WR). Chưa đủ AF_MIN_GAMES ván -> không bẻ, vote tất cả.
#   Bước 2  CAO / THẤP   : WR dùng > 50% -> nhóm CAO · < 50% -> nhóm THẤP · nhóm đông hơn được vote (CHẾ ĐỘ CAO / THẤP) · bằng nhau -> vote tất cả (ALL) · pool hoà phiếu -> đa số tất cả logic.
#                          AF_SWITCH BẬT (mặc định): thay "nhóm đông hơn thắng + đa số 7/13" bằng ĐỔI CHẾ ĐỘ DỄ HƠN — nhớ chế độ ván trước, chế độ khác đủ AF_SWITCH_NEED (6/13) phiếu là đổi (xem khối ĐỔI CHẾ ĐỘ DỄ HƠN bên dưới).
#   Bước 3  bẻ chế độ    : WR của chế độ đang chạy trong AF_MODE_WINDOW ván gần nhất CỦA CHẾ ĐỘ ĐÓ < AF_MODE_BELOW -> đảo final · ≥ AF_MODE_BELOW -> theo bình thường.
#                          Cần đủ AF_MODE_MIN ván của chế độ đó mới xét bẻ. CAO / THẤP / ALL đều có chuỗi ván riêng (hv / lv / av lưu trong từng ván đã chấm) — WR của từng chế độ xét RIÊNG, chế độ nào < AF_MODE_BELOW thì chế độ đó bị bẻ khi được chọn.
#                          ⛔ MẶC ĐỊNH ĐANG TẮT (AF_MODE_FLIP_DEFAULT = False): bước 3 bị bỏ qua -> final = kết quả sau bước 2 (CAO / THẤP / ALL), không bị đảo theo WR chế độ.
#                          Bật lại: sửa AF_MODE_FLIP_DEFAULT = True · hoặc env SUNVIW_AF_MODE_FLIP=1 · hoặc cờ --af-mode-flip (--af-no-mode-flip = tắt).
#                          Khi TẮT: AF_MODE_WINDOW / AF_MODE_MIN / AF_MODE_BELOW không còn tác dụng; be_che_do luôn false; wr_che_do_hien_tai = null.
#   AF_ENABLED_DEFAULT    True = dùng AF · False = quay về cách cũ (wr_decision + FLIP_FINAL)
#   AF_FLIP_LOW/HIGH      ngưỡng bẻ logic (37 / 63 như file HTML)
#   AF_MIN_GAMES_DEFAULT  số ván đã chấm tối thiểu mới bẻ logic / chia nhóm (tự kẹp ≤ WR_WINDOW)
#   AF_MODE_WINDOW        số ván gần nhất của mỗi chế độ để tính WR chế độ (7)
#   AF_MODE_MIN           số ván tối thiểu của chế độ đó mới xét bẻ (7; tự kẹp ≤ AF_MODE_WINDOW)
#   AF_MODE_BELOW         WR chế độ dưới mức này (%) -> bẻ final (45)
#   AF_MODE_FLIP_DEFAULT  công tắc BƯỚC 3 (bẻ chế độ): False = TẮT (mặc định, theo yêu cầu) · True = bật như bản trước
#   AF_FLIP_FINAL_DEFAULT bẻ riêng kết quả AF (TÀI<->XỈU) ở MỌI chế độ (CAO · THẤP · ALL). Mặc định False vì AF đã tự bẻ; FLIP_FINAL chung KHÔNG áp lên ván do AF chốt.
#   AF_FLIP_FINAL_CT_DEFAULT  True = CHỈ bẻ final khi AF đang ở chế độ CAO / THẤP · final của chế độ ALL GIỮ NGUYÊN (không bẻ).
#   AF_FLIP_FINAL_ALL_DEFAULT True = CHỈ bẻ final khi AF đang ở chế độ ALL · final của chế độ CAO / THẤP GIỮ NGUYÊN (không bẻ).
#   AF_FLIP_FINAL_CAO_DEFAULT  True = CHỈ bẻ final khi AF đang ở chế độ CAO  · THẤP + ALL GIỮ NGUYÊN.   ┐ TÁCH RIÊNG CAO / THẤP: vd muốn THEO final CAO nhưng BẺ final THẤP
#   AF_FLIP_FINAL_THAP_DEFAULT True = CHỈ bẻ final khi AF đang ở chế độ THẤP · CAO + ALL GIỮ NGUYÊN.   ┘ -> CAO = False · THẤP = True (và _CT = False).
#       AF_FLIP_FINAL_CT (cũ) = công tắc GỘP: True = bẻ cả CAO lẫn THẤP (tương đương bật _CAO + _THAP). Tất cả công tắc là phép HOẶC.
#       Cả 3 công tắc (AF_FLIP_FINAL · _CT · _ALL) là phép HOẶC: ván thuộc chế độ nào có ÍT NHẤT 1 công tắc áp dụng thì bẻ ĐÚNG 1 lần (không bẻ đôi). Bật AF_FLIP_FINAL = bẻ hết, 2 công tắc kia khỏi cần.
#       Chọn 1 trong 2 (_CT hoặc _ALL) để bẻ có chọn lọc; bật cả 2 = giống bật AF_FLIP_FINAL. Bẻ này nằm SAU 'bẻ chế độ' (bước 3) nên chỉ là lớp bẻ thêm của riêng bạn.
#   Đổi mà không sửa file (ưu tiên: cờ dòng lệnh > biến môi trường > *_DEFAULT):
#       env  : SUNVIW_AF=1|0 · SUNVIW_AF_LOW · SUNVIW_AF_HIGH · SUNVIW_AF_MIN · SUNVIW_AF_MODE_WINDOW · SUNVIW_AF_MODE_MIN · SUNVIW_AF_MODE_BELOW · SUNVIW_AF_MODE_FLIP=1|0 · SUNVIW_AF_FLIP=1|0 · SUNVIW_AF_FLIP_CT=1|0 · SUNVIW_AF_FLIP_CAO=1|0 · SUNVIW_AF_FLIP_THAP=1|0 · SUNVIW_AF_FLIP_ALL=1|0
#       lệnh : --af / --no-af · --af-low X · --af-high X · --af-min N · --af-mode-window N · --af-mode-below X · --af-mode-flip / --af-no-mode-flip · --af-flip / --af-no-flip · --af-flip-ct / --af-no-flip-ct · --af-flip-cao / --af-no-flip-cao · --af-flip-thap / --af-no-flip-thap · --af-flip-all / --af-no-flip-all
AF_ENABLED_DEFAULT = True
AF_FLIP_LOW_DEFAULT = 37
AF_FLIP_HIGH_DEFAULT = 63
# ── GIỚI HẠN VÙNG BẺ LOGIC (Bước 1) — AF_FLIP_BAND ────────────────────────────────────────────────
#   BẬT (mặc định): CHỈ bẻ logic khi WR nằm TRONG vùng cho phép (gồm cả 2 đầu mút); ngoài vùng -> KHÔNG bẻ (giữ nguyên phiếu).
#       Vùng THẤP : AF_FLIP_LOW_MIN  <= WR <= AF_FLIP_LOW_MAX   (mặc định 32 - 40)  -> vd WR 29% KHÔNG bẻ · 32-40% bẻ · 41% KHÔNG bẻ
#       Vùng CAO  : AF_FLIP_HIGH_MIN <= WR <= AF_FLIP_HIGH_MAX  (mặc định 60 - 68)  -> vd WR 59% KHÔNG bẻ · 60-68% bẻ · 69% KHÔNG bẻ   (đối xứng vùng thấp qua 50%)
#       Khi BẬT: AF_FLIP_LOW / AF_FLIP_HIGH (37 / 63) bị bỏ qua — vùng mới thay thế ngưỡng cũ.
#   TẮT : quay về cách cũ (WR < AF_FLIP_LOW -> bẻ · WR > AF_FLIP_HIGH -> bẻ, không có cận dưới / cận trên).
#   Đổi mà không sửa file: env SUNVIW_AF_BAND=1|0 · SUNVIW_AF_LOW_MIN · SUNVIW_AF_LOW_MAX · SUNVIW_AF_HIGH_MIN · SUNVIW_AF_HIGH_MAX
#                          lệnh --af-band / --af-no-band · --af-low-min X · --af-low-max X · --af-high-min X · --af-high-max X
AF_FLIP_BAND_DEFAULT = True
AF_FLIP_LOW_MIN_DEFAULT = 30
AF_FLIP_LOW_MAX_DEFAULT = 45
AF_FLIP_HIGH_MIN_DEFAULT = 53
AF_FLIP_HIGH_MAX_DEFAULT = 65
# ── CHỈ LOGIC BỊ BẺ MỚI VÀO NHÓM CAO / THẤP (Bước 2) — AF_GROUP_FLIPPED_ONLY + AF_GROUP_NEED_MAJORITY ─────────────
#   AF_GROUP_FLIPPED_ONLY_DEFAULT  BẬT (mặc định): CHỈ logic ĐÃ BỊ BẺ (WR nằm TRONG vùng bẻ ở khối trên) mới được xếp vào nhóm CAO / THẤP
#       (theo WR dùng sau bẻ). Logic KHÔNG bẻ (WR ngoài vùng bẻ) KHÔNG thuộc nhóm nào — mặc định ở chế độ ALL (panel hiện nhãn ALL).
#       TẮT: như bản trước — mọi logic đều được chia CAO (WR dùng > 50%) / THẤP (< 50%).
#   AF_GROUP_NEED_MAJORITY_DEFAULT BẬT (mặc định): nhóm CAO / THẤP được chọn (nhóm đông hơn) phải có SỐ LOGIC >= ĐA SỐ của TOÀN BỘ logic
#       (n // 2 + 1 · vd 13 logic -> cần >= 7). Ít hơn đa số -> bỏ nhóm, dùng chế độ ALL (vote tất cả logic sau bẻ logic).
#       Vd ảnh panel: chỉ 4/13 logic bị bẻ (2 CAO + 2 THẤP) -> không nhóm nào đủ 7 logic -> chế độ ALL thay vì CAO.
#       TẮT: nhóm đông hơn luôn được chọn dù chỉ có 1-2 logic.
#   Đổi mà không sửa file: env SUNVIW_AF_GROUP_FLIPPED=1|0 · SUNVIW_AF_GROUP_MAJORITY=1|0
#                          lệnh --af-group-flipped / --af-no-group-flipped · --af-group-majority / --af-no-group-majority
AF_GROUP_FLIPPED_ONLY_DEFAULT = True
AF_GROUP_NEED_MAJORITY_DEFAULT = True
# ── ĐỔI CHẾ ĐỘ DỄ HƠN (Bước 2) — AF_SWITCH + AF_SWITCH_NEED ─────────────────────────────────────────────────
#   Xoay quanh 3 chế độ ALL · THẤP · CAO. Mỗi logic "bỏ phiếu" cho 1 chế độ: logic nhóm CAO -> phiếu CAO · nhóm THẤP -> phiếu THẤP · logic không thuộc nhóm nào (không bẻ) -> phiếu ALL.
#   Tổng luôn = số logic (vd 15): phiếu ALL + phiếu CAO + phiếu THẤP = 15.
#   AF_SWITCH_DEFAULT BẬT (mặc định): chế độ có NHỚ chế độ của ván trước (đang ALL / CAO / THẤP) rồi mới xét đổi:
#       · Chế độ KHÁC có >= AF_SWITCH_NEED phiếu (mặc định 6/13) -> ĐỔI sang chế độ đó (bản gốc phải 7/13 = đa số mới đổi sang CAO / THẤP).
#           vd đang ALL: CAO được 4 phiếu -> sang CAO · THẤP được 4 phiếu -> sang THẤP.   vd đang CAO: ALL hoặc THẤP được 4 phiếu -> sang ALL / THẤP.   (tương tự khi đang THẤP)
#       · Không chế độ khác nào đủ AF_SWITCH_NEED phiếu -> GIỮ chế độ hiện tại.
#       · Nhiều chế độ cùng đủ phiếu (kể cả chế độ hiện tại) -> chọn chế độ NHIỀU phiếu nhất (tránh nhảy qua nhảy lại mỗi ván); bằng nhau ở đầu bảng -> giữ chế độ hiện tại.
#       · Chế độ đang giữ là CAO / THẤP mà nhóm đó không còn logic nào -> không có ai để vote, tạm dùng ALL ván này.
#       Khi BẬT: AF_GROUP_NEED_MAJORITY (đa số 7/13) KHÔNG còn tác dụng — ngưỡng 6/13 thay cho nó.
#   TẮT : quay về cách gốc (không nhớ chế độ cũ · nhóm đông hơn thắng · nhóm CAO / THẤP phải >= đa số 7/13 nếu AF_GROUP_NEED_MAJORITY bật).
#   Ván đầu / ván cũ chưa lưu chế độ -> coi chế độ trước là ALL.
#   Đổi mà không sửa file: env SUNVIW_AF_SWITCH=1|0 · SUNVIW_AF_SWITCH_NEED     lệnh --af-switch / --af-no-switch · --af-switch-need N
#   AF_SWITCH_LEAD_DEFAULT = False (mặc định): chỉ cần chế độ khác đủ AF_SWITCH_NEED phiếu là đổi, KỂ CẢ khi chế độ đang chạy nhiều phiếu hơn (đúng ý "chỉ cần 6/13").
#       Hệ quả: khi cả 2 chế độ cùng >= AF_SWITCH_NEED phiếu thì ván sau có thể đổi ngược lại (vd ALL 9 · CAO 4: ALL -> CAO, rồi CAO -> ALL ...) — chế độ đổi nhiều hơn.
#       True = êm hơn: chế độ mới còn phải DẪN ĐẦU duy nhất (nhiều phiếu hơn cả chế độ đang chạy) mới đổi. Lưu ý: 13 logic chia cho 3 chế độ thì bên dẫn đầu luôn >= 5 phiếu,
#       nên với True mọi AF_SWITCH_NEED <= 5 cho kết quả GIỐNG HỆT nhau (6/13 không dễ hơn 7/15).   env SUNVIW_AF_SWITCH_LEAD · lệnh --af-switch-lead / --af-no-switch-lead
AF_SWITCH_DEFAULT = True
AF_SWITCH_NEED_DEFAULT = 6
AF_SWITCH_LEAD_DEFAULT = False
#   AF_SWITCH_PRIO_DEFAULT BẬT (mặc định): khi đang ở 1 chế độ mà CẢ 2 chế độ còn lại đều đủ AF_SWITCH_NEED phiếu (vd 6/13) thì chọn theo ƯU TIÊN dựa trên chế độ VÁN TRƯỚC (không so số phiếu):
#       · ván trước ALL  -> ưu tiên CAO      · ván trước CAO -> ưu tiên ALL      · ván trước THẤP -> ưu tiên CAO
#       Chỉ 1 chế độ đủ phiếu -> đổi sang chế độ đó như bình thường · không chế độ nào đủ -> giữ chế độ hiện tại.  Chỉ có tác dụng khi AF_SWITCH bật và AF_SWITCH_LEAD tắt.
#       TẮT: quay về cách cũ (cả 2 cùng đủ phiếu -> lấy chế độ nhiều phiếu hơn, bằng nhau -> giữ chế độ hiện tại).   env SUNVIW_AF_SWITCH_PRIO=1|0 · lệnh --af-switch-prio / --af-no-switch-prio
AF_SWITCH_PRIO_DEFAULT = True
AF_MIN_GAMES_DEFAULT = 7
AF_MODE_WINDOW_DEFAULT = 11
AF_MODE_MIN_DEFAULT = 7
AF_MODE_BELOW_DEFAULT = 45
AF_MODE_FLIP_DEFAULT = False          # BƯỚC 3 (bẻ final theo WR chế độ): False = TẮT · True = BẬT
AF_FLIP_FINAL_DEFAULT = False
AF_FLIP_FINAL_CT_DEFAULT = False       # True = bẻ final của chế độ CAO / THẤP  (BẬT theo yêu cầu: bẻ CAO/THẤP + bẻ ALL)
AF_FLIP_FINAL_CAO_DEFAULT = False      # True = CHỈ bẻ final của chế độ CAO   (TÁCH RIÊNG khỏi THẤP)
AF_FLIP_FINAL_THAP_DEFAULT = True     # True = CHỈ bẻ final của chế độ THẤP  (TÁCH RIÊNG khỏi CAO) — vd theo CAO nhưng bẻ THẤP: CAO=False · THAP=True
AF_FLIP_FINAL_ALL_DEFAULT = True      # True = bẻ final của chế độ ALL        (BẬT)

AF_ENABLED = _env_bool("SUNVIW_AF", AF_ENABLED_DEFAULT)
AF_FLIP_LOW = _env_num("SUNVIW_AF_LOW", AF_FLIP_LOW_DEFAULT, float)
AF_FLIP_HIGH = _env_num("SUNVIW_AF_HIGH", AF_FLIP_HIGH_DEFAULT, float)
AF_FLIP_BAND = _env_bool("SUNVIW_AF_BAND", AF_FLIP_BAND_DEFAULT)                          # giới hạn vùng bẻ logic (xem khối GIỚI HẠN VÙNG BẺ)
AF_FLIP_LOW_MIN = _env_num("SUNVIW_AF_LOW_MIN", AF_FLIP_LOW_MIN_DEFAULT, float)
AF_FLIP_LOW_MAX = _env_num("SUNVIW_AF_LOW_MAX", AF_FLIP_LOW_MAX_DEFAULT, float)
AF_FLIP_HIGH_MIN = _env_num("SUNVIW_AF_HIGH_MIN", AF_FLIP_HIGH_MIN_DEFAULT, float)
AF_FLIP_HIGH_MAX = _env_num("SUNVIW_AF_HIGH_MAX", AF_FLIP_HIGH_MAX_DEFAULT, float)
AF_GROUP_FLIPPED_ONLY = _env_bool("SUNVIW_AF_GROUP_FLIPPED", AF_GROUP_FLIPPED_ONLY_DEFAULT)      # chỉ logic bị bẻ mới vào nhóm CAO / THẤP
AF_GROUP_NEED_MAJORITY = _env_bool("SUNVIW_AF_GROUP_MAJORITY", AF_GROUP_NEED_MAJORITY_DEFAULT)   # nhóm chọn < đa số toàn bộ logic -> dùng ALL
AF_SWITCH = _env_bool("SUNVIW_AF_SWITCH", AF_SWITCH_DEFAULT)                                     # đổi chế độ ALL / CAO / THẤP dễ hơn: chỉ cần AF_SWITCH_NEED phiếu (thay vì đa số)
AF_SWITCH_LEAD = _env_bool("SUNVIW_AF_SWITCH_LEAD", AF_SWITCH_LEAD_DEFAULT)                      # True = chế độ mới còn phải dẫn đầu duy nhất mới đổi (êm hơn)
AF_SWITCH_PRIO = _env_bool("SUNVIW_AF_SWITCH_PRIO", AF_SWITCH_PRIO_DEFAULT)                      # True = 2 chế độ còn lại cùng đủ phiếu -> ưu tiên theo chế độ ván trước (ALL->CAO · CAO->ALL · THẤP->CAO)
AF_SWITCH_NEED = _env_num("SUNVIW_AF_SWITCH_NEED", AF_SWITCH_NEED_DEFAULT, int)                 # số phiếu (trên tổng số logic) để đổi sang chế độ khác (mặc định 6/13)
AF_MIN_GAMES =_env_num("SUNVIW_AF_MIN", AF_MIN_GAMES_DEFAULT, int)
AF_MODE_WINDOW = _env_num("SUNVIW_AF_MODE_WINDOW", AF_MODE_WINDOW_DEFAULT, int)
AF_MODE_MIN = _env_num("SUNVIW_AF_MODE_MIN", AF_MODE_MIN_DEFAULT, int)
AF_MODE_BELOW = _env_num("SUNVIW_AF_MODE_BELOW", AF_MODE_BELOW_DEFAULT, float)
AF_MODE_FLIP = _env_bool("SUNVIW_AF_MODE_FLIP", AF_MODE_FLIP_DEFAULT)            # bước 3: bẻ final theo WR chế độ
AF_FLIP_FINAL = _env_bool("SUNVIW_AF_FLIP", AF_FLIP_FINAL_DEFAULT)
AF_FLIP_FINAL_CT = _env_bool("SUNVIW_AF_FLIP_CT", AF_FLIP_FINAL_CT_DEFAULT)      # chỉ bẻ final khi chế độ CAO / THẤP
AF_FLIP_FINAL_CAO = _env_bool("SUNVIW_AF_FLIP_CAO", AF_FLIP_FINAL_CAO_DEFAULT)    # chỉ bẻ final khi chế độ CAO
AF_FLIP_FINAL_THAP = _env_bool("SUNVIW_AF_FLIP_THAP", AF_FLIP_FINAL_THAP_DEFAULT)  # chỉ bẻ final khi chế độ THẤP
AF_FLIP_FINAL_ALL = _env_bool("SUNVIW_AF_FLIP_ALL", AF_FLIP_FINAL_ALL_DEFAULT)   # chỉ bẻ final khi chế độ ALL


def af_apply_limits():
    """Chuẩn hoá tham số AF (gọi lúc import và sau khi đọc cờ dòng lệnh)."""
    global AF_FLIP_LOW, AF_FLIP_HIGH, AF_MIN_GAMES, AF_MODE_WINDOW, AF_MODE_MIN, AF_MODE_BELOW
    global AF_FLIP_LOW_MIN, AF_FLIP_LOW_MAX, AF_FLIP_HIGH_MIN, AF_FLIP_HIGH_MAX, AF_SWITCH_NEED
    AF_SWITCH_NEED = max(1, int(AF_SWITCH_NEED))
    AF_FLIP_LOW = min(max(0.0, float(AF_FLIP_LOW)), 50.0)
    AF_FLIP_HIGH = min(max(50.0, float(AF_FLIP_HIGH)), 100.0)
    lo_a, lo_b = sorted((min(max(0.0, float(AF_FLIP_LOW_MIN)), 50.0), min(max(0.0, float(AF_FLIP_LOW_MAX)), 50.0)))          # vùng thấp nằm trong 0-50 (tự đổi chỗ nếu gõ ngược)
    hi_a, hi_b = sorted((min(max(50.0, float(AF_FLIP_HIGH_MIN)), 100.0), min(max(50.0, float(AF_FLIP_HIGH_MAX)), 100.0)))   # vùng cao nằm trong 50-100
    AF_FLIP_LOW_MIN, AF_FLIP_LOW_MAX, AF_FLIP_HIGH_MIN, AF_FLIP_HIGH_MAX = lo_a, lo_b, hi_a, hi_b
    AF_MIN_GAMES = max(1, int(AF_MIN_GAMES))
    AF_MODE_WINDOW = max(1, int(AF_MODE_WINDOW))
    AF_MODE_MIN = max(1, min(int(AF_MODE_MIN), AF_MODE_WINDOW))
    AF_MODE_BELOW = min(max(0.0, float(AF_MODE_BELOW)), 100.0)


af_apply_limits()


UPSTREAM_TIMEOUT = 9      # giây (timeout gọi API nguồn LC)
# THƯ MỤC LƯU DỮ LIỆU BỀN: Railway gắn Volume thì tự đặt RAILWAY_VOLUME_MOUNT_PATH (vd. /data) -> mọi file lưu (lịch sử, graded, key, IP...)
# nằm trong Volume nên KHÔNG MẤT sau mỗi lần deploy / restart. Không có Volume (chạy máy local) -> dùng /tmp như cũ.
# Muốn tự chọn thư mục: đặt SUNVIW_DATA_DIR. Từng file vẫn ghi đè riêng được bằng SUNVIW_HIST / SUNVIW_PERSIST / SUNVIW_KEYS_PATH / SUNVIW_IPS_PATH.
ON_RAILWAY = bool(os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("RAILWAY_PROJECT_ID") or os.environ.get("RAILWAY_SERVICE_ID"))
DATA_DIR = os.environ.get("SUNVIW_DATA_DIR") or os.environ.get("RAILWAY_VOLUME_MOUNT_PATH") or ""
if not DATA_DIR and ON_RAILWAY:                        # Railway nhưng chưa có biến Volume -> thử các điểm gắn ổ đĩa hay dùng (chỉ nhận nếu THẬT SỰ là ổ đĩa gắn riêng)
    for _cand in ("/data", "/app/data", "/mnt/data"):
        if os.path.ismount(_cand):
            DATA_DIR = _cand
            break
DATA_DIR = DATA_DIR or "/tmp"
try:
    os.makedirs(DATA_DIR, exist_ok=True)
except OSError:
    DATA_DIR = "/tmp"
# Dữ liệu có BỀN qua redeploy không? /tmp (hoặc thư mục tạm) = KHÔNG. Chạy máy local thì ổ đĩa bình thường nên coi là bền, chỉ cảnh báo khi đang ở Railway.
DATA_PERSISTENT = (DATA_DIR == os.environ.get("RAILWAY_VOLUME_MOUNT_PATH")) or not (DATA_DIR == "/tmp" or DATA_DIR.startswith("/tmp/")) or not ON_RAILWAY


def _data_path(name):
    return os.path.join(DATA_DIR, name)


BOOT_PATH = os.environ.get("SUNVIW_BOOT_PATH", _data_path("sunviw_boot.json"))


def _boot_mark():
    """Ghi mốc khởi động vào thư mục data: lần đầu (first) + số lần khởi động (count). Redeploy xong mà `first` vẫn cũ và `count` tăng = data đã được giữ lại.
    Ngược lại `first` = vừa mới => thư mục data đã bị xoá sạch (chưa gắn Volume)."""
    now = int(time.time())
    d = {"first": now, "count": 0}
    try:
        with open(BOOT_PATH, "r", encoding="utf-8") as f:
            o = json.load(f)
        if isinstance(o, dict) and o.get("first"):
            d["first"], d["count"] = int(o["first"]), int(o.get("count") or 0)
    except Exception:  # noqa: BLE001
        pass
    d["count"] += 1
    d["last"] = now
    try:
        tmp = BOOT_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f)
        os.replace(tmp, BOOT_PATH)
    except OSError:
        d["loi_ghi"] = True
    return d


BOOT_INFO = _boot_mark()


HIST_KEEP = int(os.environ.get("SUNVIW_HIST_KEEP", "600") or 600)   # CỬA SỔ TRƯỢT 600 VÁN: chỉ giữ 600 phiên GẦN NHẤT (RAM + file) — có phiên thứ 601 thì phiên cũ nhất bị bỏ. Mỗi logic đọc cửa sổ riêng LOGIC_WIN (≤ 500) trong số này. Đổi: env SUNVIW_HIST_KEEP
WR_MIN_GAMES = 1           # số ván đã chấm tối thiểu để dùng WR (dưới mức này -> đa số 21 logic)

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
#   🔄 FLIP TRỌNG SỐ (WR_FLIP_WEIGHT_DEFAULT) — công tắc RIÊNG cho SUN:
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
WR_DECAY = 0.95           # (vô tác dụng khi WR_FLOOR = WR_WEIGHT_NEWEST)
WR_FLOOR = 1.0            # SEQ13v4: BỎ decay -> sàn = trọng số ván mới nhất = 1.0 => MỌI ván trong WR_WINDOW nặng như nhau (bản cũ: DECAY 0.95 · FLOOR 0.75 · NEWEST 1.4 — muốn bật lại: đặt 0.75 / 1.4 ở đây và ở các khối CONFIG từng bàn bên dưới)
WR_WEIGHT_NEWEST = 1.0    # trọng số ván mới nhất (= WR_FLOOR -> không decay)
# dạng Fraction để tính/so sánh chính xác (dùng trong wr_weights)
_W_DECAY = Fraction(str(WR_DECAY))
_W_FLOOR = Fraction(str(WR_FLOOR))
_W_NEWEST = Fraction(str(WR_WEIGHT_NEWEST))
WR_FLIP_WEIGHT_DEFAULT = False   # FLIP trọng số WR của SUN: True = ván CŨ nhất nặng nhất -> giảm dần tới ván MỚI nhất · False = ván mới nhất nặng nhất (mặc định)

# ═══════════════════════════════════════════════════════════════════════════
#  ⚙  CONFIG BẺ FINAL CỦA SUN  (bật / tắt)  —  CHỈNH Ở ĐÂY
# ═══════════════════════════════════════════════════════════════════════════
#   FLIP_FINAL_DEFAULT = False  ->  TẮT (mặc định): du_doan = final của 21 logic, KHÔNG bẻ
#   FLIP_FINAL_DEFAULT = True   ->  BẬT : du_doan = đảo ngược final (TÀI <-> XỈU)
#
#  Muốn đổi mà không sửa file (ưu tiên: cờ dòng lệnh > biến môi trường > FLIP_FINAL_DEFAULT):
#     biến môi trường :  SUNVIW_FLIP=1  (bật)  |  SUNVIW_FLIP=0  (tắt)
#     dòng lệnh       :  python sunviw_api.py --flip      (bật)
#                        python sunviw_api.py --no-flip   (tắt)
FLIP_FINAL_DEFAULT = False


FLIP_FINAL = _env_bool("SUNVIW_FLIP", FLIP_FINAL_DEFAULT)
WR_FLIP_WEIGHT = _env_bool("SUNVIW_WR_FLIP", WR_FLIP_WEIGHT_DEFAULT)      # flip trọng số WR của SUN (xem CONFIG WR CÓ TRỌNG SỐ)

# ─── ĐÁNH GIÁ ĐÚNG/SAI ───────────────────────────────────────────────────
EVAL_WINDOW = 300           # số phiên gần nhất để đánh giá đúng/sai = WR 100 phiên (hiện thẳng trong /api/predict · tool_dung_sai_10_van) — cần PERSIST_KEEP >= EVAL_WINDOW mới đủ ván để tính
ICON_DUNG = "✅"            # icon hiện cho ván ĐOÁN ĐÚNG trong chuỗi "chuoi" của /api/predict
ICON_SAI = "❌"             # icon hiện cho ván ĐOÁN SAI

# ─── PERSISTENCE (lưu graded để Railway không mất sau restart) ───────────
PERSIST_PATH = os.environ.get("SUNVIW_PERSIST", _data_path("sun15_graded.json"))
PERSIST_KEEP = max(100, EVAL_WINDOW)   # giữ tối đa N graded entry trong file (100 ván; trước là 50 nên WR "100 phiên" thực chất chỉ đo được 50 ván). Tự nâng theo EVAL_WINDOW


SUN_REBUILD_MAX = PERSIST_KEEP   # chấm lại tối đa N ván gần nhất trong lịch sử: lần đầu (file graded trống) chấm đủ N ván; về sau chấm thêm ván MỚI hơn ván đã lưu, và chấm BÙ ván CŨ hơn nếu file chưa đủ PERSIST_KEEP ván


# ═══════════════════════════════════════════════════════════════════════════
#  🧩  CFG THEO BÀN — SUN và các bàn HITCLUB dùng CHUNG một bộ hàm AF / WR / chấm ván, mỗi nơi có config RIÊNG
# ═══════════════════════════════════════════════════════════════════════════
#   Các hàm af_decision / af_mode_wr / decide_final / rebuild_graded / build_result ... nhận tham số `cfg`.
#     · cfg = SUN (mặc định)  -> đọc THẲNG các biến global của SUN ở trên (AF_*, WR_*, FLIP_FINAL, EVAL_WINDOW ...), kể cả khi cờ dòng lệnh đổi chúng lúc chạy -> SUN giữ nguyên hành vi.
#     · cfg = TableCfg(...)    -> bộ config riêng của 1 bàn HITCLUB (khối "CONFIG HITCLUB" bên dưới). Sửa bàn này KHÔNG ảnh hưởng SUN và bàn kia.
class _SunCfg:
    """Proxy chỉ-đọc: cfg.X trả về biến global X của SUN tại thời điểm gọi."""
    _ALIAS = {"W_DECAY": "_W_DECAY", "W_FLOOR": "_W_FLOOR", "W_NEWEST": "_W_NEWEST",
              "REBUILD_MAX": "SUN_REBUILD_MAX", "TIE_LOGIC": "SUN_TIE_LOGIC"}

    def __getattr__(self, name):
        try:
            return globals()[self._ALIAS.get(name, name)]
        except KeyError:
            raise AttributeError(name) from None


SUN = _SunCfg()


class TableCfg:
    """Config đầy đủ của 1 bàn (thuộc tính trùng tên biến config của SUN). Tự chuẩn hoá giống af_apply_limits() của SUN."""

    def __init__(self, name, values):
        self.name = name
        self.__dict__.update(values)
        self.__dict__.setdefault("AF_FLIP_FINAL_CAO", False)    # công tắc bẻ final RIÊNG chế độ CAO (thiếu -> không bẻ)
        self.__dict__.setdefault("AF_FLIP_FINAL_THAP", False)   # công tắc bẻ final RIÊNG chế độ THẤP (thiếu -> không bẻ)
        self.__dict__.setdefault("AF_SWITCH", True)             # đổi chế độ ALL / CAO / THẤP dễ hơn (xem khối ĐỔI CHẾ ĐỘ DỄ HƠN)
        self.__dict__.setdefault("AF_SWITCH_NEED", 6)           # số phiếu để đổi sang chế độ khác (6/13)
        self.__dict__.setdefault("AF_SWITCH_PRIO", True)        # 2 chế độ còn lại cùng đủ phiếu -> ưu tiên theo chế độ ván trước (ALL->CAO · CAO->ALL · THẤP->CAO)
        self.__dict__.setdefault("AF_SWITCH_LEAD", False)       # True = chế độ mới còn phải dẫn đầu duy nhất mới đổi (êm hơn) · False = chỉ cần đủ AF_SWITCH_NEED phiếu
        self.normalize()

    def normalize(self):
        self.AF_FLIP_LOW = min(max(0.0, float(self.AF_FLIP_LOW)), 50.0)
        self.AF_FLIP_HIGH = min(max(50.0, float(self.AF_FLIP_HIGH)), 100.0)
        lo_a, lo_b = sorted((min(max(0.0, float(self.AF_FLIP_LOW_MIN)), 50.0), min(max(0.0, float(self.AF_FLIP_LOW_MAX)), 50.0)))
        hi_a, hi_b = sorted((min(max(50.0, float(self.AF_FLIP_HIGH_MIN)), 100.0), min(max(50.0, float(self.AF_FLIP_HIGH_MAX)), 100.0)))
        self.AF_FLIP_LOW_MIN, self.AF_FLIP_LOW_MAX, self.AF_FLIP_HIGH_MIN, self.AF_FLIP_HIGH_MAX = lo_a, lo_b, hi_a, hi_b
        self.WR_WINDOW = max(1, int(self.WR_WINDOW))
        self.WR_MIN_GAMES = max(1, int(self.WR_MIN_GAMES))
        self.AF_MIN_GAMES = max(1, int(self.AF_MIN_GAMES))
        self.AF_SWITCH_NEED = max(1, int(self.AF_SWITCH_NEED))
        self.AF_MODE_WINDOW = max(1, int(self.AF_MODE_WINDOW))
        self.AF_MODE_MIN = max(1, min(int(self.AF_MODE_MIN), self.AF_MODE_WINDOW))
        self.AF_MODE_BELOW = min(max(0.0, float(self.AF_MODE_BELOW)), 100.0)
        self.EVAL_WINDOW = max(1, int(self.EVAL_WINDOW))
        self.PERSIST_KEEP = max(100, self.EVAL_WINDOW, int(self.PERSIST_KEEP))
        self.REBUILD_MAX = self.PERSIST_KEEP
        self.HIST_KEEP = max(50, int(self.HIST_KEEP))
        self.POLL_SEC = max(1.0, float(self.POLL_SEC))
        self.W_DECAY, self.W_FLOOR, self.W_NEWEST = (Fraction(str(self.WR_DECAY)), Fraction(str(self.WR_FLOOR)), Fraction(str(self.WR_WEIGHT_NEWEST)))

    def as_dict(self):
        """Các tham số config (chỉ khoá IN HOA gốc, bỏ khoá phái sinh) — để hiển thị ở /health."""
        skip = {"W_DECAY", "W_FLOOR", "W_NEWEST", "REBUILD_MAX"}
        return {k: v for k, v in self.__dict__.items() if k.isupper() and k not in skip}


HIST_MAX = 300             # trần số ván lịch sử cho ?hist=N

HIT_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
def _hit_env(prefix, d):
    """Ghi đè giá trị config của 1 bàn từ biến môi trường <prefix><TÊN> (kiểu theo giá trị mặc định; giá trị lạ -> bỏ qua)."""
    out = dict(d)
    for k, v in d.items():
        raw = os.environ.get(prefix + k, "").strip()
        if not raw:
            continue
        try:
            if isinstance(v, bool):
                low = raw.lower()
                if low in ("1", "true", "yes", "on"):
                    out[k] = True
                elif low in ("0", "false", "no", "off"):
                    out[k] = False
            elif isinstance(v, (int, float)):
                out[k] = float(raw) if "." in raw else int(raw)
            else:
                out[k] = raw
        except ValueError:
            pass
    return out


#  🟣  CONFIG LC (GAME 4 · 2 BÀN: LC MD5 + LC HŨ)  —  MỖI BÀN MỘT BỘ CONFIG RIÊNG, DATA RIÊNG  —  CHỈNH Ở ĐÂY
# ═══════════════════════════════════════════════════════════════════════════
#   2 bàn (key game "lc79", tiền tố LC79- — 1 key LC79 dùng được CẢ 2 bàn):
#       LC MD5 (tên cũ: Tele68 MD5) · GET /api/predictlcmd5 · file data tele68_txmd5.json (GIỮ tên file cũ để không mất lịch sử / WR đã học)
#                                     nguồn https://wtxmd52.tele68.com/v1/txmd5/sessions?cp=R&cl=R&pf=web&at=<TOKEN>
#       LC HŨ                       · GET /api/predictlchu  · file data lc_hu.json
#                                     nguồn https://wtx.tele68.com/v1/tx/sessions?cp=R&cl=R&pf=web&at=<TOKEN>
#   Endpoint cũ /api/predicttele68txmd5 vẫn chạy (alias của /api/predictlcmd5) để tool đang gọi tên cũ không hỏng.
#   Cả 2 nguồn trả CẢ DANH SÁCH {"list":[{id, resultTruyenThong, dices:[a,b,c], point}, ...]} (~105 phiên, phiên ĐẦU = MỚI NHẤT) — khác các game kia chỉ trả 1 phiên mới nhất.
#   Cách tool làm (GIỐNG HỆT nhau ở 2 bàn):
#       · Mỗi lần quét: đọc TOÀN BỘ list, chỉ LƯU THÊM các phiên CHƯA có trong data (phiên đã học giữ nguyên) -> tích lũy tối đa HIST_KEEP phiên.
#       · Dự đoán = phiên MỚI NHẤT + 1 (bộ 13 logic SEQ13v6 + AF + WR như SUN/Hit, đọc config RIÊNG của bàn ở 2 khối dưới).
#       · Dự đoán được giữ trong file data (trường "pending") cho tới khi API trả ra kết quả đúng phiên đó -> khi phiên đó xuất hiện, tool so sánh & chấm ĐÚNG / SAI (vào lich_su + WR/AF).
#       · Tài/Xỉu tính theo TỔNG xúc xắc (>= 11 = Tài), không đọc resultTruyenThong.
#   Panel /api/html có 2 tab "LC MD5" · "LC Hũ" (mỗi tab có nút Xóa lịch sử / Tính lại theo config / Xóa data riêng).
#   Ý nghĩa thông số: giống các khối "CONFIG HITCLUB" / "CONFIG AF" / "CONFIG WR CÓ TRỌNG SỐ" phía trên. Sửa khối bàn nào CHỈ ảnh hưởng bàn đó.
#   ► Khối LC HŨ đang là BẢN SAO config của LC MD5 (chưa backtest riêng cho Hũ) — chỉnh riêng khi đã có số liệu.
#   Đổi mà không sửa file (env):
#       LC_ENABLED=0 (tắt cả 2 bàn; tên cũ TELE68_ENABLED vẫn nhận) · LC_MD5_API_URL (tên cũ TELE68_API_URL) · LC_HU_API_URL — dùng khi token `at=` đổi
#       LC_REFERER (tên cũ TELE68_REFERER; thêm header Referer/Origin nếu server đòi) · LC_MD5_PATH (tên cũ TELE68_TXMD5_PATH) · LC_HU_PATH đổi file lưu
#       LCMD5_<TÊN> / LCHU_<TÊN> ghi đè từng thông số của khối config (vd. LCMD5_AF_ENABLED=0 · LCHU_WR_WINDOW=17 · LCHU_POLL_SEC=2); tiền tố cũ TELE68TXMD5_ vẫn nhận cho LC MD5.
LC_ENABLED = _env_bool("LC_ENABLED", _env_bool("TELE68_ENABLED", True))
LC_MD5_API_URL = os.environ.get("LC_MD5_API_URL") or os.environ.get("TELE68_API_URL") or "https://wtxmd52.tele68.com/v1/txmd5/sessions?cp=R&cl=R&pf=web&at=6cd221bcc034632d6cb745a302c066c6"
LC_HU_API_URL = os.environ.get("LC_HU_API_URL") or "https://wtx.tele68.com/v1/tx/sessions?cp=R&cl=R&pf=web&at=ca2f3e546e6d4c9ea5736bdfba726929"
LC_REFERER = (os.environ.get("LC_REFERER") or os.environ.get("TELE68_REFERER") or "").strip()
LC_MD5_PATH = os.environ.get("LC_MD5_PATH") or os.environ.get("TELE68_TXMD5_PATH") or _data_path("tele68_txmd5.json")
LC_HU_PATH = os.environ.get("LC_HU_PATH") or _data_path("lc_hu.json")

# ─ BÀN 1: LC MD5 (tên cũ Tele68 MD5) — config RIÊNG, chỉnh ở đây ─
LC_MD5_CFG = TableCfg("lcmd5", _hit_env("LCMD5_", _hit_env("TELE68TXMD5_", {
    "ENABLED": True,
    "GID": "lc_md5",
    "POLL_SEC": 3.0,
    "HIST_KEEP": HIST_KEEP,
    "TIE_LOGIC": "AFM",
    "CONSEC_CHECK": True,
    # WR có trọng số
    "WR_WINDOW": 13, "WR_DECAY": 0.95, "WR_FLOOR": 1.0, "WR_WEIGHT_NEWEST": 1.0, "WR_FLIP_WEIGHT": False, "WR_MIN_GAMES": 1,
    # bẻ final (dùng khi AF tắt)
    "FLIP_FINAL": False,
    # AF: bước 1 bẻ logic
    "AF_ENABLED": True, "AF_FLIP_LOW": 37, "AF_FLIP_HIGH": 63,
    "AF_FLIP_BAND": True, "AF_FLIP_LOW_MIN": 0, "AF_FLIP_LOW_MAX": 40, "AF_FLIP_HIGH_MIN": 57, "AF_FLIP_HIGH_MAX": 100,
    "AF_MIN_GAMES": 8,
    # AF: bước 2 nhóm CAO/THẤP
    "AF_GROUP_FLIPPED_ONLY": True, "AF_GROUP_NEED_MAJORITY": True,
    "AF_SWITCH": True, "AF_SWITCH_NEED": 5, "AF_SWITCH_LEAD": False, "AF_SWITCH_PRIO": True,       # đổi chế độ ALL / CAO / THẤP chỉ cần N phiếu (thay vì đa số 7/13) — AF_SWITCH=False = về cách gốc · AF_SWITCH_LEAD=True = chế độ mới phải dẫn đầu mới đổi
    # AF: bước 3 bẻ theo WR chế độ (WR chế độ < AF_MODE_BELOW % -> đảo final TÀI<->XỈU)
    "AF_MODE_FLIP": False, "AF_MODE_WINDOW": 9, "AF_MODE_MIN": 7, "AF_MODE_BELOW": 45,
    # AF: bẻ final riêng
    "AF_FLIP_FINAL": False, "AF_FLIP_FINAL_CT": False, "AF_FLIP_FINAL_CAO": True, "AF_FLIP_FINAL_THAP": False, "AF_FLIP_FINAL_ALL": True,   # bộ backtest 300 ván (ALL cao nhất + ALL nhiều ván nhất): KHÔNG bẻ final chế độ nào
    # đánh giá đúng/sai + số ván lưu
    "EVAL_WINDOW": 500, "PERSIST_KEEP": 300,
})))

# ─ BÀN 2: LC HŨ — config RIÊNG, chỉnh ở đây (đang là bản sao config LC MD5) ─
LC_HU_CFG = TableCfg("lchu", _hit_env("LCHU_", {
    "ENABLED": True,
    "GID": "lc_hu",
    "POLL_SEC": 3.0,
    "HIST_KEEP": HIST_KEEP,
    "TIE_LOGIC": "AFM",
    "CONSEC_CHECK": True,
    # WR có trọng số
    "WR_WINDOW": 20, "WR_DECAY": 0.95, "WR_FLOOR": 1.0, "WR_WEIGHT_NEWEST": 1.0, "WR_FLIP_WEIGHT": False, "WR_MIN_GAMES": 1,
    # bẻ final (dùng khi AF tắt)
    "FLIP_FINAL": False,
    # AF: bước 1 bẻ logic
    "AF_ENABLED": True, "AF_FLIP_LOW": 37, "AF_FLIP_HIGH": 63,
    "AF_FLIP_BAND": True, "AF_FLIP_LOW_MIN": 20, "AF_FLIP_LOW_MAX": 47, "AF_FLIP_HIGH_MIN": 57, "AF_FLIP_HIGH_MAX": 75,
    "AF_MIN_GAMES": 8,
    # AF: bước 2 nhóm CAO/THẤP
    "AF_GROUP_FLIPPED_ONLY": True, "AF_GROUP_NEED_MAJORITY": True,
    "AF_SWITCH": True, "AF_SWITCH_NEED": 5, "AF_SWITCH_LEAD": False, "AF_SWITCH_PRIO": True,
    # AF: bước 3 bẻ theo WR chế độ (WR chế độ < AF_MODE_BELOW % -> đảo final TÀI<->XỈU)
    "AF_MODE_FLIP": False, "AF_MODE_WINDOW": 9, "AF_MODE_MIN": 7, "AF_MODE_BELOW": 45,
    # AF: bẻ final riêng
    "AF_FLIP_FINAL": False, "AF_FLIP_FINAL_CT": False, "AF_FLIP_FINAL_CAO": False, "AF_FLIP_FINAL_THAP": False, "AF_FLIP_FINAL_ALL": True,
    # đánh giá đúng/sai + số ván lưu
    "EVAL_WINDOW": 500, "PERSIST_KEEP": 300,
}))

# ═══════════════════════════════════════════════════════════════════════════
#  🗑  CONFIG XÓA LỊCH SỬ DỰ ĐOÁN (nút "Xóa lịch sử" ở panel /api/html)  —  CHỈNH Ở ĐÂY
# ═══════════════════════════════════════════════════════════════════════════
#   Nút này CHỈ làm sạch phần HIỂN THỊ: danh sách "lich_su" + số liệu đúng/sai (tool_dung_sai_*, % đúng, chuỗi ✅❌ trên panel).
#   Cách làm: lưu 1 MỐC phiên cho từng game (SUN / HIT thường / HIT MD5) — ván có phiên <= mốc bị ẩn khỏi lịch sử / thống kê hiển thị.
#   KHÔNG xóa / sửa bất cứ dữ liệu nào khác: lịch sử xúc xắc (hist) · các ván đã chấm + vote từng logic (graded) · key / IP / cấu hình.
#   -> 13 logic SUN (và các bàn Hit), WR có trọng số, AF (CAO/THẤP, WR chế độ), do_tin_cay, du_doan của phiên đang dự đoán: GIỮ NGUYÊN 100%, vì chúng vẫn đọc đủ dữ liệu cũ.
#   Mốc lưu file riêng nên còn sau khi restart / deploy (cần Volume như các file khác trên Railway).
#   HIST_CLEAR_ENABLED_DEFAULT  True = cho xóa · False = tắt hẳn tính năng (endpoint trả 403)  (env SUNVIW_HIST_CLEAR=1|0)
#   HIST_CLEAR_PATH             file lưu mốc (env SUNVIW_HISTCLEAR_PATH)
#   Endpoint: POST /api/history/clear  {"game": "sun" | "hittxthuong" | "hittxmd5" | "hitclub" | "all"}  (cần key người dùng; key chỉ xóa được lịch sử của game nó thuộc về)
HIST_CLEAR_ENABLED_DEFAULT = True
HIST_CLEAR_ENABLED = _env_bool("SUNVIW_HIST_CLEAR", HIST_CLEAR_ENABLED_DEFAULT)
HIST_CLEAR_PATH = os.environ.get("SUNVIW_HISTCLEAR_PATH", _data_path("sun15_histclear.json"))

# ═══════════════════════════════════════════════════════════════════════════
#  🌐  CONFIG IP — THEO DÕI IP TRUY CẬP (tab "IP" của panel /api/html)  —  CHỈNH Ở ĐÂY
# ═══════════════════════════════════════════════════════════════════════════
#   Mỗi request tới /api/predictsun · /api/predicthittxthuong · /api/predicthittxmd5 · /api/html được ghi lại IP client. /health, "/", /api/ips (chính tab IP) KHÔNG tính.
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

# ─── HELPERS ─────────────────────────────────────────────────────────────
def actual_of(total):
    return TAI if total >= 11 else XIU


def flip_pred(p):
    """Bẻ: đảo TÀI <-> XỈU (giá trị khác giữ nguyên)."""
    return XIU if p == TAI else TAI if p == XIU else p


def vote_result(preds):
    tai = sum(1 for x in preds if x == TAI)
    xiu = sum(1 for x in preds if x == XIU)
    if tai == xiu:
        return 'SKIP'
    return TAI if tai > xiu else XIU


def compute_all(hist):
    """Vote của 13 logic SUN (SEQ13v6) cho phiên KẾ TIẾP, từ lịch sử `hist` (cũ -> mới; mỗi phần tử có actual / total / d1 d2 d3 / phien). Thứ tự = SUN_NAMES.
    MỖI LOGIC CHỈ ĐỌC LOGIC_WIN[tên] VÁN GẦN NHẤT (cửa sổ mạnh nhất của logic đó, mọi ván trọng số như nhau). Cả 13 logic LUÔN bỏ phiếu (không cổng, không phiếu trắng):
    chưa đủ lịch sử cho một logic (hoặc logic lỗi) -> logic đó tạm theo kết quả ván trước."""
    S = {"y": [1 if r["actual"] == TAI else 0 for r in hist], "t": [int(r["total"]) for r in hist],
         "d": [(r["d1"], r["d2"], r["d3"]) for r in hist],
         "p": [int(r["phien"]) for r in hist]}              # số phiên
    n = len(S["y"])
    fb = S["y"][-1] if n else 0
    cache = {}
    out = []
    for nm, fn in SUN_LOGICS:
        W = LOGIC_WIN.get(nm, 0)
        if W and n > W:
            Sw = cache.get(W)
            if Sw is None:
                Sw = cache[W] = {k: v[-W:] for k, v in S.items()}
        else:
            Sw = S
        try:
            v = fn(Sw)
        except Exception:  # noqa: BLE001 - 1 logic lỗi không được làm sập cả dự đoán
            v = None
        out.append(TAI if (fb if v is None else v) == 1 else XIU)
    return out


# ─── 13 LOGIC CỦA SUN (thuần Python, tự học online từ lịch sử — mô tả ở docstring đầu file) ───
from collections import defaultdict


def _tb1(t):
    return 0 if t <= 7 else 1 if t <= 10 else 2 if t <= 13 else 3


def _vote01(n1, n0, fb):
    return 1 if n1 > n0 else 0 if n0 > n1 else fb


def _win_counts(n, keyfn, y, W, start):
    """Đếm (n0, n1) theo khoá keyfn(j) trên các bước j ∈ [max(start, n-W), n-1] (mục tiêu y[j])."""
    cnt = defaultdict(lambda: [0, 0])
    for j in range(max(start, n - W), n):
        cnt[keyfn(j)][y[j]] += 1
    return cnt


def lg_ppm(S, K, W, alpha):
    y = S["y"]
    n = len(y)
    if n <= K:
        return None
    s = 0.0
    for k in range(1, K + 1):
        key = lambda j, k=k: tuple(y[j - k:j])
        c = _win_counts(n, key, y, W, k)
        n0, n1 = c[key(n)] if key(n) in c else (0, 0)
        m = n0 + n1
        if m > 0:
            pr = (n1 + 0.5) / (m + 1.0)
            s += (k ** alpha) * (m / (m + 3.0)) * math.log(pr / (1 - pr))
    return 1 if s > 0 else 0 if s < 0 else y[-1]


# ── logic thêm ở bản SEQ14/SEQ13v4 (REGIME; LAGAC · SGDLR · ARSUM · EWMA · PERIOD đã bị loại). Trả 1 = TÀI · 0 = XỈU · None = bỏ phiếu trắng (compute_all -> theo kết quả ván trước) ──
def lg_regime(S, K=20, W=250, m=8.0):
    """REGIME: nhịp đảo cầu của K ván gần nhất chia 4 nhóm; học online P(ván sau ĐẢO | nhóm) trong W ván (co về 50%, m=8). Rate > 50% -> đảo cầu · < 50% -> bệt."""
    y = S["y"]
    n = len(y)
    if n < K + 40:
        return None
    a = [0] + [1 if y[i] != y[i - 1] else 0 for i in range(1, n)]
    c = [0]
    for v in a:
        c.append(c[-1] + v)                                 # c[i+1] = a[0..i]
    fr = lambda j: (c[j] - c[j - K + 1]) / (K - 1)          # nhịp đảo trong y[j-K .. j-1] (K-1 bước chuyển)
    bk = lambda r: 0 if r <= .35 else 1 if r <= .5 else 2 if r <= .65 else 3
    cnt = defaultdict(lambda: [0, 0])
    for j in range(max(K, n - W), n):
        k = bk(fr(j))
        cnt[k][1] += 1
        cnt[k][0] += a[j]
    kk = bk(fr(n))
    alt, tot = cnt[kk] if kk in cnt else (0, 0)
    rate = (alt + 0.5 * m) / (tot + m)
    if rate > 0.5:
        return 1 - y[-1]
    if rate < 0.5:
        return y[-1]
    return None


def _gj_solve(A, b):
    """Giải A x = b bằng Gauss–Jordan (pivot từng phần). Trả None nếu suy biến."""
    n = len(A)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(M[r][c]))
        if abs(M[p][c]) < 1e-12:
            return None
        M[c], M[p] = M[p], M[c]
        piv = M[c][c]
        for j in range(c, n + 1):
            M[c][j] /= piv
        for r in range(n):
            if r != c and M[r][c] != 0.0:
                f = M[r][c]
                for j in range(c, n + 1):
                    M[r][j] -= f * M[c][j]
    return [M[i][n] for i in range(n)]


def lg_blrev(S, W=250, NL=8, iters=5):
    """BLREV: hồi quy logistic Bayes (Newton/IRLS) trên W ván gần nhất. Đặc trưng: bias (không phạt) · 8 kết quả gần nhất (±1) · 2 tổng gần nhất (chuẩn hoá) · độ dài đợt hiện tại có dấu.
    Hệ số phạt ridge α KHÔNG đặt tay mà tự chọn theo bằng chứng (MacKay: α = γ / |w|²) -> chuỗi ngẫu nhiên thì α lớn, hệ số co về 0, dự đoán ≈ theo thiên lệch chung; có cấu trúc thì α nhỏ lại.
    Nâng cấp của SGDLR (SGDLR cố định tốc độ học + L2 + 2 epoch). Luôn bỏ phiếu (logic THƯỜNG); thiếu dữ liệu -> None -> theo ván trước."""
    y, t = S["y"], S["t"]
    n = len(y)
    lo = max(NL + 3, n - W)
    if n - lo < 100:
        return None

    def feat(j):
        f = [2.0 * y[j - k] - 1.0 for k in range(1, NL + 1)]
        f += [(t[j - 1] - 10.5) / 3.0, (t[j - 2] - 10.5) / 3.0]
        r = 1
        while r < 8 and j - 1 - r >= 0 and y[j - 1 - r] == y[j - 1]:
            r += 1
        f.append((2.0 * y[j - 1] - 1.0) * r / 8.0)
        return f

    X = [[1.0] + feat(j) for j in range(lo, n)]
    Yv = y[lo:n]
    d = len(X[0])
    w = [0.0] * d
    alpha = 5.0
    for _ in range(iters):
        H = [[0.0] * d for _ in range(d)]
        g = [0.0] * d
        for x, yy in zip(X, Yv):
            z = max(-30.0, min(30.0, sum(a * b for a, b in zip(w, x))))
            p = 1.0 / (1.0 + math.exp(-z))
            sv = p * (1.0 - p)
            e = yy - p
            for a_ in range(d):
                xa = x[a_]
                g[a_] += e * xa
                sa = sv * xa
                Ha = H[a_]
                for b_ in range(a_, d):
                    Ha[b_] += sa * x[b_]
        for a_ in range(d):
            for b_ in range(a_):
                H[a_][b_] = H[b_][a_]
        for a_ in range(1, d):
            g[a_] -= alpha * w[a_]
            H[a_][a_] += alpha
        H[0][0] += 1e-6
        dw = _gj_solve(H, g)
        if dw is None:
            return None
        w = [wi + di for wi, di in zip(w, dw)]
        ww = sum(wi * wi for wi in w[1:])
        if ww > 1e-9:
            tr = sum(1.0 / H[a_][a_] for a_ in range(1, d))
            gamma = max(0.0, (d - 1) - alpha * tr)
            alpha = min(max(gamma / ww, 0.5), 2000.0)
    z = sum(a * b for a, b in zip(w, [1.0] + feat(n)))
    return 1 if z > 0 else 0 if z < 0 else None


# ── 4 logic giữ lại từ SEQ13v4 (KNNH · RUNCTX · DIEMK · BAL; TVBIAS · RLSFF đã bỏ ở SEQ13v4) ──────────────────────
# Nguyên tắc chung: cả 4 là logic THƯỜNG — LUÔN bỏ phiếu (không có cổng thống kê, không phiếu trắng). Thiếu bằng chứng -> mô hình tự co về prior rồi vẫn lấy dấu của xác suất;
# chỉ khi chưa đủ lịch sử (n < ~30-40 ván) mới trả None -> compute_all cho theo kết quả ván trước. Trên chuỗi ngẫu nhiên mọi logic ≈ 50% (không logic nào tạo lợi thế trên RNG công bằng).
def _sgn_vote(s, eps=1e-12):
    return 1 if s > eps else 0 if s < -eps else None


def lg_knnh(S, Ls=(6, 10, 14), K=15, W=200):
    """KNNH: láng giềng gần nhất MỜ trên chuỗi Tài/Xỉu. Với mỗi độ dài đoạn L ∈ (6, 10, 14): so L ván cuối với MỌI đoạn L ván trong cửa sổ bằng khoảng cách Hamming có trọng số
    (ván càng gần càng nặng; +0.5 nếu nhóm tổng ván trước khác), lấy K đoạn gần nhất, bỏ phiếu theo kết quả NGAY SAU mỗi đoạn với trọng số 1/(1+khoảng cách). Trung bình 3 độ dài -> dấu.
    Khớp MỜ (không đòi khớp chính xác) nên luôn có láng giềng để bỏ phiếu."""
    y, t = S["y"], S["t"]
    n = len(y)
    if n < 30:
        return None
    tq = _tb1(t[n - 1])
    tot, used = 0.0, 0
    for L in Ls:
        lo = max(L, n - W)
        if n - lo < 20:
            continue
        q = y[n - L:n]
        wp = [1.0 + i / float(L) for i in range(L)]                 # ván càng gần (cuối đoạn) trọng số càng cao
        cand = []
        for j in range(lo, n):
            d = 0.5 if _tb1(t[j - 1]) != tq else 0.0
            base = j - L
            for i in range(L):
                if y[base + i] != q[i]:
                    d += wp[i]
            cand.append((d, -j, y[j]))                              # hoà khoảng cách -> ưu tiên đoạn mới hơn
        cand.sort()
        sw = sv = 0.0
        for d, _nj, yy in cand[:K]:
            w = 1.0 / (1.0 + d)
            sw += w
            sv += w * (2 * yy - 1)
        if sw > 0:
            tot += sv / sw
            used += 1
    if not used:
        return None
    return _sgn_vote(tot)


def lg_runctx(S, cl=7, cp=4, m=4.0):
    """RUNCTX: mô hình hazard theo ĐỘ DÀI ĐỢT có ngữ cảnh. Mỗi bước trong lịch sử: 'đợt đang dài l ván (cắt ở 7), 2 đợt trước dài p1 / p2 (cắt ở 4)' -> đợt có KẾT THÚC ở bước này không.
    Hazard ước lượng theo 4 tầng back-off (l,p1,p2) -> (l,p1) -> (l) -> chung, mỗi tầng co về tầng dưới (m=4) nên ngữ cảnh ít mẫu tự dựa vào tầng thô hơn.
    P(đợt kết thúc ngay ván này) > 50% -> ĐẢO cầu, < 50% -> BỆT. Bắt cầu 1-1, 2-2, 1-2-1, 2-1-2… ở tầng độ dài đợt (PPM6 chỉ thấy 6 ký tự liền nhau)."""
    y = S["y"]
    n = len(y)
    if n < 30:
        return None
    runs = []
    for v in y:
        if runs and runs[-1][0] == v:
            runs[-1][1] += 1
        else:
            runs.append([v, 1])
    kl = len(runs) - 1
    c3 = defaultdict(lambda: [0, 0])
    c2 = defaultdict(lambda: [0, 0])
    c1 = defaultdict(lambda: [0, 0])
    c0 = [0, 0]
    for k, (_s, ln) in enumerate(runs):
        p1 = min(runs[k - 1][1], cp) if k >= 1 else 0
        p2 = min(runs[k - 2][1], cp) if k >= 2 else 0
        for l in range(1, ln + 1):
            if k == kl and l == ln:                                 # bước hiện tại của đợt đang chạy = câu hỏi, chưa có đáp án
                break
            e = 1 if l == ln else 0                                 # 1 = đợt kết thúc sau l ván
            lc = min(l, cl)
            c3[(lc, p1, p2)][e] += 1
            c2[(lc, p1)][e] += 1
            c1[lc][e] += 1
            c0[e] += 1
    p1q = min(runs[-2][1], cp) if len(runs) >= 2 else 0
    p2q = min(runs[-3][1], cp) if len(runs) >= 3 else 0
    lq = min(runs[-1][1], cl)
    h = (c0[1] + 1.0) / (c0[0] + c0[1] + 2.0)
    for tbl, key in ((c1, lq), (c2, (lq, p1q)), (c3, (lq, p1q, p2q))):
        a = tbl[key] if key in tbl else (0, 0)
        h = (a[1] + m * h) / (a[0] + a[1] + m)
    if h > 0.5:
        return 1 - y[-1]
    if h < 0.5:
        return y[-1]
    return None


def lg_diemk(S, W=200, m=6.0):
    """DIEMK: Markov mức TỪNG VIÊN xúc xắc. Mỗi viên (3 vị trí) có bảng 'mức viên đó ván trước (thấp 1-2 · giữa 3-4 · cao 5-6) -> phân phối mặt 1..6 ván sau', học trong W ván,
    làm mịn Dirichlet về phân phối chung của viên đó (m=6). Nhân chập 3 phân phối -> P(tổng >= 11). Đi đường KHÁC với CT2/CDT cũ (gom nhóm tổng làm mất thông tin từng viên)
    và với bản gom nhóm tổng cũ (mất thông tin từng viên)."""
    d = S["d"]
    n = len(d)
    if n < 30:
        return None
    try:
        lv = lambda v: 0 if v <= 2 else 1 if v <= 4 else 2
        lo = max(1, n - W)
        dists = []
        for k in range(3):
            cnt = [[0] * 7 for _ in range(3)]
            mg = [0] * 7
            for j in range(lo, n):
                v = int(d[j][k])
                if not 1 <= v <= 6:
                    return None
                cnt[lv(int(d[j - 1][k]))][v] += 1
                mg[v] += 1
            tm = float(sum(mg))
            mp = [(mg[v] + 1.0) / (tm + 6.0) for v in range(1, 7)]
            c = cnt[lv(int(d[n - 1][k]))]
            tc = float(sum(c))
            dists.append([(c[v] + m * mp[v - 1]) / (tc + m) for v in range(1, 7)])
    except (TypeError, ValueError, IndexError):
        return None
    pt = 0.0
    for a in range(6):
        for b in range(6):
            pab = dists[0][a] * dists[1][b]
            for c_ in range(6):
                if a + b + c_ + 3 >= 11:
                    pt += pab * dists[2][c_]
    return _sgn_vote(pt - 0.5, 1e-9)


def lg_bal(S, wins=(8, 16, 32, 64), minn=30):
    """BAL: 'cân cầu' — độ lệch Tài-Xỉu (z-score) trong cửa sổ 8 / 16 / 32 / 64 ván gần nhất. Với mỗi cửa sổ, học TRÊN LỊCH SỬ hệ số hồi quy ridge: độ lệch cửa sổ đó -> kết quả ván sau
    (hệ số âm = hồi quy về trung bình / nhà cái cân bằng, dương = đà tiếp tục). Điểm = Σ hệ số × độ lệch hiện tại -> dấu. Dấu của hệ số do dữ liệu quyết định, không đặt tay;
    RNG độc lập thì hệ số ≈ 0 và logic chỉ bỏ phiếu theo nhiễu nhỏ."""
    y = S["y"]
    n = len(y)
    if n < 40:
        return None
    c = [0]
    for v in y:
        c.append(c[-1] + v)
    score, used = 0.0, 0
    for w in wins:
        N = n - w
        if N < minn:
            continue
        sd = 0.5 * math.sqrt(w)
        f = [(c[j] - c[j - w] - w / 2.0) / sd for j in range(w, n)]
        tg = y[w:n]
        yb = sum(tg) / float(N)
        fb = sum(f) / float(N)                                      # TRUNG TÂM hoá cả độ lệch lẫn kết quả: logic chỉ đo 'lệch hơn mức thường lệ', thiên lệch cố định để các logic khác (CMIXL · SPARSE) lo
        sxy = sum((fi - fb) * (yy - yb) for fi, yy in zip(f, tg))
        sxx = sum((fi - fb) ** 2 for fi in f)
        beta = sxy / (sxx + 1.0 * N)                                # ridge: co hệ số về 0 khi tín hiệu yếu
        score += beta * ((c[n] - c[n - w] - w / 2.0) / sd - fb)
        used += 1
    if not used:
        return None
    return _sgn_vote(score, 1e-12)


# ── 6 logic MỚI ở bản SEQ13v4 (CMIXL · SPARSE · HMM3 · TOTK · SPEC · CPSEG) — thay CTW · SELKEY · LSM · DECAYMIX · CONV3 · TVBIAS · RLSFF ──────────────────────────────
# Nguyên tắc chung: (1) LUÔN bỏ phiếu (dấu của xác suất/dự báo, không cổng thống kê, không phiếu trắng) — chỉ khi chưa đủ lịch sử mới trả None -> theo ván trước;
# (2) mọi ván trong cửa sổ có TRỌNG SỐ NHƯ NHAU (không decay) — "cửa sổ" do LOGIC_WIN cắt trong compute_all (mỗi logic đọc đúng số ván mà nó mạnh nhất);
# (3) không đặt tay tham số nhạy: hệ số phạt / băng thông / bậc mô hình do DỮ LIỆU chọn (evidence · leave-one-out · log-likelihood) -> chuỗi ngẫu nhiên thì co về 50% chứ không bịa cấu trúc.
_pc = int.bit_count if hasattr(int, "bit_count") else (lambda x: bin(x).count("1"))      # popcount


def _loo_ll(n0, n1, a=1.0):
    """Log-likelihood LEAVE-ONE-OUT của 1 ngữ cảnh có n0 ván Xỉu / n1 ván Tài (bộ ước lượng Beta(a,a)): mỗi ván được dự đoán bằng phần còn lại của ngữ cảnh đó."""
    n = n0 + n1
    if n == 0:
        return 0.0
    den = n - 1.0 + 2.0 * a
    s = 0.0
    if n1:
        s += n1 * math.log((n1 - 1.0 + a) / den)
    if n0:
        s += n0 * math.log((n0 - 1.0 + a) / den)
    return s


def _ridge_logit(X, Yv, w0, iters=4, alpha0=5.0, a_min=0.5, a_max=2000.0):
    """Hồi quy logistic ridge (Newton/IRLS) với PRIOR TRUNG TÂM w0 (phạt α|w−w0|², bias w[0] không phạt). α tự chọn theo bằng chứng (MacKay: α = γ/|w−w0|²).
    Khác BLREV: hệ số co về w0 (vd. 'trung bình đều các mô hình') chứ không co về 0 -> không có bằng chứng thì kết quả = trung bình các đầu vào."""
    d = len(w0)
    w = list(w0)
    alpha = alpha0
    for _ in range(iters):
        H = [[0.0] * d for _ in range(d)]
        g = [0.0] * d
        for x, yy in zip(X, Yv):
            z = 0.0
            for a_ in range(d):
                z += w[a_] * x[a_]
            z = max(-30.0, min(30.0, z))
            p = 1.0 / (1.0 + math.exp(-z))
            sv = p * (1.0 - p)
            e = yy - p
            for a_ in range(d):
                xa = x[a_]
                g[a_] += e * xa
                sa = sv * xa
                Ha = H[a_]
                for b_ in range(a_, d):
                    Ha[b_] += sa * x[b_]
        for a_ in range(d):
            for b_ in range(a_):
                H[a_][b_] = H[b_][a_]
        for a_ in range(1, d):
            g[a_] -= alpha * (w[a_] - w0[a_])
            H[a_][a_] += alpha
        H[0][0] += 1e-6
        dw = _gj_solve(H, g)
        if dw is None:
            return None
        w = [wi + di for wi, di in zip(w, dw)]
        ww = sum((w[a_] - w0[a_]) ** 2 for a_ in range(1, d))
        if ww > 1e-9:
            tr = sum(1.0 / H[a_][a_] for a_ in range(1, d))
            gamma = max(0.0, (d - 1) - alpha * tr)
            alpha = min(max(gamma / ww, a_min), a_max)
    return w


# ── 1) CMIXL — Context Mixing Logistic (kiểu PAQ): nhiều mô hình ngữ cảnh + match model, trộn bằng hồi quy logistic ─────────────────────────────────────────────────────
def lg_cmixl(S, W=500, burn=60):
    """CMIXL: 'trộn ngữ cảnh' kiểu PAQ/cmix trên chuỗi Tài/Xỉu. 9 mô hình con, mỗi mô hình học ONLINE (đếm dần theo thứ tự thời gian, ván j chỉ thấy ván < j) rồi đưa ra stretch(P(Tài)):
    bậc 1 · 2 · 3 · 4 · 6 · 8 (ngữ cảnh = k kết quả gần nhất) · RUNCTX (ván trước + độ dài đợt hiện tại + độ dài đợt trước) · TỔNG (nhóm tổng 2 ván trước) · MATCH (tìm lần xuất hiện gần nhất của 12 ván cuối,
    dự đoán theo ván nằm sau nó; độ tin cậy theo độ dài khớp học online). Bộ trộn = hồi quy logistic ridge trên chính các dự đoán ĐÃ-LÀ-OUT-OF-SAMPLE đó (ván nào cũng nặng như nhau),
    hệ số co về TRUNG BÌNH ĐỀU 1/9 (không có bằng chứng thì ≈ trung bình các mô hình) và độ phạt α tự chọn theo bằng chứng MacKay. Cửa sổ 500 ván. Luôn bỏ phiếu.
    Mạnh: bắt cùng lúc cầu ngắn (bậc thấp) · cầu dài lặp (match/bậc 8) · nhịp đợt (RUNCTX) mà không phải đoán 'bậc nào đúng' — bộ trộn tự chọn. Yếu: nhiều mô hình -> cần ≥ 100 ván (tốt nhất ≥ 300) mới có bằng chứng; nguồn thật sự ngẫu nhiên thì ≈ 50%."""
    y, t = S["y"], S["t"]
    n = len(y)
    if n < 100:
        return None
    burn = min(burn, max(20, n // 8))
    J0 = 12
    ORD = (1, 2, 3, 4, 6, 8)
    cn1 = [[0] * (1 << k) for k in ORD]
    cn0 = [[0] * (1 << k) for k in ORD]
    masks = [(1 << k) - 1 for k in ORD]
    rc = {}                                                     # RUNCTX: (ván trước, độ dài đợt cắt 8, độ dài đợt trước cắt 4) -> [n0, n1]
    tc = {}                                                     # TỔNG: nhóm tổng 2 ván trước -> [n0, n1]
    tb = [_tb1(v) for v in t]
    last = {}                                                   # 12 ván cuối (số nguyên 12 bit) -> chỉ số ván nằm NGAY SAU lần xuất hiện gần nhất
    mh = [0] * 10
    mt = [0] * 10
    h = 0
    run, prun = 0, 0
    for i in range(J0):
        h = (h << 1) | y[i]
        if i and y[i] == y[i - 1]:
            run += 1
        else:
            prun, run = run, 1
    X, Yv = [], []
    feats = None
    for j in range(J0, n + 1):
        f = [1.0]
        for oi in range(6):
            cx = h & masks[oi]
            f.append(math.log((cn1[oi][cx] + 1.0) / (cn0[oi][cx] + 1.0)))
        rk = (y[j - 1], run if run < 8 else 8, prun if prun < 4 else 4)
        r = rc.get(rk)
        f.append(math.log((r[1] + 1.0) / (r[0] + 1.0)) if r else 0.0)
        tk = tb[j - 1] * 4 + tb[j - 2]
        r = tc.get(tk)
        f.append(math.log((r[1] + 1.0) / (r[0] + 1.0)) if r else 0.0)
        p = last.get(h)
        pred, mb = -1, 0
        if p is not None:
            ln_ = 12
            while ln_ < 32 and p - 1 - ln_ >= 0 and y[p - 1 - ln_] == y[j - 1 - ln_]:
                ln_ += 1
            mb = ln_ >> 2
            pred = y[p]
            rr = (mh[mb] + 1.0) / (mt[mb] + 2.0)
            sv = math.log(rr / (1.0 - rr))
            f.append(sv if pred else -sv)
        else:
            f.append(0.0)
        if j == n:
            feats = f
            break
        yy = y[j]
        if j >= J0 + burn:
            X.append(f)
            Yv.append(yy)
        for oi in range(6):
            cx = h & masks[oi]
            if yy:
                cn1[oi][cx] += 1
            else:
                cn0[oi][cx] += 1
        r = rc.get(rk)
        if r is None:
            r = rc[rk] = [0, 0]
        r[yy] += 1
        r = tc.get(tk)
        if r is None:
            r = tc[tk] = [0, 0]
        r[yy] += 1
        if pred >= 0:
            mt[mb] += 1
            if pred == yy:
                mh[mb] += 1
        last[h] = j
        h = ((h << 1) | yy) & 0xFFF
        if yy == y[j - 1]:
            run += 1
        else:
            prun, run = run, 1
    if len(X) < 50 or feats is None:
        return None
    d = len(feats)
    w0 = [0.0] + [1.0 / (d - 1)] * (d - 1)
    w = _ridge_logit(X, Yv, w0)
    if w is None:
        return None
    return _sgn_vote(sum(a * b for a, b in zip(w, feats)), 1e-12)


# ── 2) SPARSE — mô hình trễ THƯA, trung bình Bayes (BMA) bằng bitset + popcount ───────────────────────────────────────────────────────────────────────────────────────────
def lg_sparse(S, W=500, L1=16, L3=10, a=1.0):
    """SPARSE: thay vì ngữ cảnh 'k ván liền nhau' (PPM) — xét mọi tập TRỄ THƯA: 1 trễ ∈ 1..16 (16 mô hình) · 2 trễ ∈ 1..16 (120) · 3 trễ ∈ 1..10 (120) + mô hình rỗng (tỉ lệ chung) = 257 mô hình.
    Ví dụ {2,5}: 'ván cách 2 và cách 5 ván trước -> ván này' (bắt cầu có nhịp cách quãng / chu kỳ mà PPM không thấy vì bị ván xen giữa che). Mỗi mô hình = bảng đếm Tài/Xỉu theo giá trị các trễ đó trong W=500 ván
    (đếm bằng bitset + popcount nên cả 257 mô hình chỉ vài ms). Bằng chứng mỗi mô hình = log-likelihood LEAVE-ONE-OUT (đã tự phạt độ phức tạp: mô hình nhiều ngữ cảnh mà chỉ khớp nhiễu sẽ bị trừ điểm);
    prior chia ĐỀU theo số trễ (rỗng / 1 / 2 / 3 trễ mỗi nhóm 1/4, rồi chia đều trong nhóm). Dự đoán = trung bình Bayes P(Tài) theo trọng số exp(bằng chứng). Luôn bỏ phiếu (dấu của P − 0.5).
    Mạnh: bắt chu kỳ/nhịp cách quãng, bù cho PPM6 (liền kề) và RUNCTX (độ dài đợt). Yếu: trên nguồn ngẫu nhiên vẫn có 'người thắng do may' trong 257 mô hình — LOO + prior nhóm chỉ giảm chứ không loại bỏ."""
    y = S["y"]
    n = len(y)
    lo = max(L1, n - W)
    N = n - lo
    if N < 80:
        return None
    full = (1 << N) - 1
    mk = lambda seq: int("".join(map(str, seq)), 2)
    T = mk(y[lo:n])
    B = [None] * (L1 + 1)
    for l_ in range(1, L1 + 1):
        B[l_] = mk(y[lo - l_:n - l_])
    P1 = [None] + [(B[l_] ^ full, B[l_]) for l_ in range(1, L1 + 1)]       # P1[l][v] = tập vị trí mà ván cách l ván có giá trị v
    qb = [None] + [y[n - l_] for l_ in range(1, L1 + 1)]                    # giá trị các trễ tại thời điểm cần dự đoán
    a2 = 2.0 * a
    n1_all = _pc(T)
    n0_all = N - n1_all
    cand = [(math.log(0.25) + _loo_ll(n0_all, n1_all, a), (n1_all + a) / (N + a2))]
    g1 = float(L1)
    g2 = L1 * (L1 - 1) / 2.0
    g3 = L3 * (L3 - 1) * (L3 - 2) / 6.0
    lp1, lp2, lp3 = math.log(0.25 / g1), math.log(0.25 / g2), math.log(0.25 / g3)

    for l1 in range(1, L1 + 1):
        ll, pq = 0.0, 0.5
        for v in (0, 1):
            m = P1[l1][v]
            nn = _pc(m)
            k1 = _pc(m & T)
            ll += _loo_ll(nn - k1, k1, a)
            if v == qb[l1]:
                pq = (k1 + a) / (nn + a2)
        cand.append((lp1 + ll, pq))
        for l2 in range(l1 + 1, L1 + 1):
            sets2 = []
            ll, pq = 0.0, 0.5
            for v1 in (0, 1):
                for v2 in (0, 1):
                    m = P1[l1][v1] & P1[l2][v2]
                    sets2.append(m)
                    nn = _pc(m)
                    k1 = _pc(m & T)
                    ll += _loo_ll(nn - k1, k1, a)
                    if v1 == qb[l1] and v2 == qb[l2]:
                        pq = (k1 + a) / (nn + a2)
            cand.append((lp2 + ll, pq))
            if l2 <= L3:
                for l3 in range(l2 + 1, L3 + 1):
                    ll, pq = 0.0, 0.5
                    for i4 in range(4):
                        m4 = sets2[i4]
                        for v3 in (0, 1):
                            m = m4 & P1[l3][v3]
                            nn = _pc(m)
                            k1 = _pc(m & T)
                            ll += _loo_ll(nn - k1, k1, a)
                            if (i4 >> 1) == qb[l1] and (i4 & 1) == qb[l2] and v3 == qb[l3]:
                                pq = (k1 + a) / (nn + a2)
                    cand.append((lp3 + ll, pq))
    mx = max(c[0] for c in cand)
    sw = sq = 0.0
    for lw, pq in cand:
        wgt = math.exp(lw - mx)
        sw += wgt
        sq += wgt * pq
    return _sgn_vote(sq / sw - 0.5, 1e-12)


# ── 3) HMM3 — Hidden Markov 3 trạng thái (Baum–Welch, MAP) ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def _hmm_forward(ys, A, e):
    """Forward có chuẩn hoá. Trả (list alpha-chuẩn-hoá, list hệ số c, log-likelihood)."""
    a00, a01, a02, a10, a11, a12, a20, a21, a22 = A[0][0], A[0][1], A[0][2], A[1][0], A[1][1], A[1][2], A[2][0], A[2][1], A[2][2]
    e0, e1, e2 = e
    q0, q1, q2 = 1.0 - e0, 1.0 - e1, 1.0 - e2
    y0 = ys[0]
    f0 = (e0 if y0 else q0) / 3.0
    f1 = (e1 if y0 else q1) / 3.0
    f2 = (e2 if y0 else q2) / 3.0
    c = f0 + f1 + f2
    f0, f1, f2 = f0 / c, f1 / c, f2 / c
    al = [(f0, f1, f2)]
    cs = [c]
    ll = math.log(c)
    for t in range(1, len(ys)):
        yy = ys[t]
        g0 = (f0 * a00 + f1 * a10 + f2 * a20) * (e0 if yy else q0)
        g1 = (f0 * a01 + f1 * a11 + f2 * a21) * (e1 if yy else q1)
        g2 = (f0 * a02 + f1 * a12 + f2 * a22) * (e2 if yy else q2)
        c = g0 + g1 + g2
        if c < 1e-300:
            c = 1e-300
        f0, f1, f2 = g0 / c, g1 / c, g2 / c
        al.append((f0, f1, f2))
        cs.append(c)
        ll += math.log(c)
    return al, cs, ll


def _hmm_fit(ys, A, e, iters, tol=0.01):
    """Baum–Welch MAP: prior Dirichlet(1) cho từng hàng chuyển trạng thái (+1 giả-đếm) và Beta(2,2) cho xác suất phát Tài (+1/+1) -> không bao giờ suy biến về 0/1."""
    T = len(ys)
    A = [r[:] for r in A]
    e = list(e)
    prev = -1e300
    al = cs = None
    ll = prev
    for _ in range(iters):
        al, cs, ll = _hmm_forward(ys, A, e)
        if ll - prev < tol:
            break
        prev = ll
        a00, a01, a02, a10, a11, a12, a20, a21, a22 = A[0][0], A[0][1], A[0][2], A[1][0], A[1][1], A[1][2], A[2][0], A[2][1], A[2][2]
        e0, e1, e2 = e
        q0, q1, q2 = 1.0 - e0, 1.0 - e1, 1.0 - e2
        b0 = b1 = b2 = 1.0                                      # beta chuẩn hoá của bước cuối
        x00 = x01 = x02 = x10 = x11 = x12 = x20 = x21 = x22 = 0.0
        sg0 = sg1 = sg2 = 0.0
        sy0 = sy1 = sy2 = 0.0
        yy = ys[T - 1]
        f0, f1, f2 = al[T - 1]
        sg0 += f0
        sg1 += f1
        sg2 += f2
        if yy:
            sy0 += f0
            sy1 += f1
            sy2 += f2
        for t in range(T - 2, -1, -1):
            yn = ys[t + 1]
            c = cs[t + 1]
            u0 = (e0 if yn else q0) * b0 / c
            u1 = (e1 if yn else q1) * b1 / c
            u2 = (e2 if yn else q2) * b2 / c
            f0, f1, f2 = al[t]
            x00 += f0 * u0
            x01 += f0 * u1
            x02 += f0 * u2
            x10 += f1 * u0
            x11 += f1 * u1
            x12 += f1 * u2
            x20 += f2 * u0
            x21 += f2 * u1
            x22 += f2 * u2
            b0 = a00 * u0 + a01 * u1 + a02 * u2
            b1 = a10 * u0 + a11 * u1 + a12 * u2
            b2 = a20 * u0 + a21 * u1 + a22 * u2
            g0, g1, g2 = f0 * b0, f1 * b1, f2 * b2
            sg0 += g0
            sg1 += g1
            sg2 += g2
            if ys[t]:
                sy0 += g0
                sy1 += g1
                sy2 += g2
        X = ((x00 * a00, x01 * a01, x02 * a02), (x10 * a10, x11 * a11, x12 * a12), (x20 * a20, x21 * a21, x22 * a22))
        A = []
        for r in X:
            s = r[0] + r[1] + r[2] + 3.0
            A.append([(r[0] + 1.0) / s, (r[1] + 1.0) / s, (r[2] + 1.0) / s])
        e = [(sy0 + 1.0) / (sg0 + 2.0), (sy1 + 1.0) / (sg1 + 2.0), (sy2 + 1.0) / (sg2 + 2.0)]
    al, cs, ll = _hmm_forward(ys, A, e)
    return A, e, al, ll


def lg_hmm3(S, W=400, iters=10):
    """HMM3: mô hình Markov ẩn 3 trạng thái (mỗi trạng thái có xác suất ra Tài riêng + ma trận chuyển trạng thái 3x3), học bằng Baum–Welch MAP trên W=400 ván (mọi ván trọng số như nhau).
    2 điểm khởi tạo CỐ ĐỊNH (deterministic): (a) 'chế độ dính' — 3 trạng thái nghiêng Xỉu / giữa / nghiêng Tài, ở lâu trong mỗi trạng thái; (b) 'chu trình' — 3 trạng thái luân phiên theo vòng (bắt cầu 1-1 / nhịp 3);
    lấy cái có likelihood cao hơn. Dự đoán = lọc forward ra phân phối trạng thái hiện tại -> chuyển 1 bước -> P(Tài) -> dấu của P − 0.5. Luôn bỏ phiếu.
    Mạnh: bắt 'chế độ' ẩn thay đổi (lúc bệt, lúc đảo, lúc lệch Tài…) mà các mô hình ngữ cảnh cố định không có khái niệm 'đang ở chế độ nào'; prior MAP nên không suy biến. Yếu: EM có thể kẹt cực trị địa phương
    (đã giảm bằng 2 khởi tạo) và trên nguồn ngẫu nhiên 3 trạng thái chỉ fit nhiễu -> ≈ 50%."""
    y = S["y"]
    n = len(y)
    if n < 100:
        return None
    best = None
    for A0, e0 in (([[0.8, 0.1, 0.1], [0.1, 0.8, 0.1], [0.1, 0.1, 0.8]], (0.3, 0.5, 0.7)),
                   ([[0.15, 0.7, 0.15], [0.15, 0.15, 0.7], [0.7, 0.15, 0.15]], (0.2, 0.8, 0.5))):
        r = _hmm_fit(y, A0, e0, iters)
        if best is None or r[3] > best[3]:
            best = r
    A, e, al, _ll = best
    f = al[-1]
    p = 0.0
    for j in range(3):
        p += e[j] * (f[0] * A[0][j] + f[1] * A[1][j] + f[2] * A[2][j])
    return _sgn_vote(p - 0.5, 1e-12)


# ── 4) TOTK — hồi quy hạt nhân (Nadaraya–Watson) trên TỔNG xúc xắc, băng thông chọn bằng LOO + BMA ───────────────────────────────────────────────────────────────────────────
def _smooth1d(arr, ker):
    V = len(arr)
    R = len(ker) - 1
    out = [0.0] * V
    for c in range(V):
        s = 0.0
        for d_ in range(-R, R + 1):
            i = c + d_
            if 0 <= i < V:
                s += ker[abs(d_)] * arr[i]
        out[c] = s
    return out


def lg_totk(S, W=400, m=2.0):
    """TOTK: hồi quy hạt nhân trên TỔNG xúc xắc (3..18) — 'tổng gần đây ở gần mức nào thì ván sau hay ra Tài hay Xỉu', dùng thông tin mà nhị phân Tài/Xỉu (PPM/CMIXL) vứt đi (tổng 10 và 3 cùng là Xỉu).
    3 bộ đặc trưng: (a) tổng ván trước · (b) cặp (tổng ván trước, tổng ván trước nữa) · (c) tổng 3 ván gần nhất. Mỗi bộ x 4 băng thông Gauss (hẹp -> rộng ≈ tỉ lệ chung) = 12 ước lượng NW:
    P(Tài | ngữ cảnh) = (Σ K·y + m·p0)/(Σ K + m), m = 2 co về tỉ lệ chung p0. Băng thông KHÔNG đặt tay: bằng chứng mỗi ước lượng = log-likelihood LEAVE-ONE-OUT trên W=400 ván (công thức đóng, ván nào cũng nặng như nhau),
    dự đoán = trung bình Bayes theo exp(bằng chứng). Luôn bỏ phiếu. Mạnh: dùng được cả độ lớn tổng (nguồn có 'đà' theo mức tổng); LOO tự chọn băng thông. Yếu: nếu cầu chỉ phụ thuộc Tài/Xỉu thì chẳng thêm gì so với PPM6."""
    y, t = S["y"], S["t"]
    n = len(y)
    if n < 60:
        return None
    tt = [min(18, max(3, int(v))) - 3 for v in t]               # 0..15
    j0 = 3
    N = n - j0
    n1_all = sum(y[j0:n])
    p0 = (n1_all + 1.0) / (N + 2.0)
    V1, V3 = 16, 46
    # đếm ô
    g1_n, g1_1 = [0.0] * V1, [0.0] * V1
    g2_n = [[0.0] * V1 for _ in range(V1)]
    g2_1 = [[0.0] * V1 for _ in range(V1)]
    g3_n, g3_1 = [0.0] * V3, [0.0] * V3
    for j in range(j0, n):
        yy = y[j]
        a_, b_ = tt[j - 1], tt[j - 2]
        s3 = a_ + b_ + tt[j - 3]
        g1_n[a_] += 1.0
        g2_n[a_][b_] += 1.0
        g3_n[s3] += 1.0
        if yy:
            g1_1[a_] += 1.0
            g2_1[a_][b_] += 1.0
            g3_1[s3] += 1.0
    qa, qb_ = tt[n - 1], tt[n - 2]
    qs = qa + qb_ + tt[n - 3]

    def kern(h, V):
        R = min(V - 1, int(math.ceil(3.0 * h)))
        return [math.exp(-0.5 * (i / h) ** 2) for i in range(R + 1)]

    def loo_cells(cells, p0_, m_):
        """cells: list (n_c, n1_c, S_c, S1_c) -> LOO log-lik của ước lượng NW (đã bỏ chính ván đó khỏi tổng hạt nhân: S-1, S1-y)."""
        ll = 0.0
        for nc, k1, Sc, S1c in cells:
            if nc <= 0.0:
                continue
            den = Sc - 1.0 + m_
            if k1 > 0.0:
                ll += k1 * math.log((S1c - 1.0 + m_ * p0_) / den)
            k0 = nc - k1
            if k0 > 0.0:
                ll += k0 * math.log(((Sc - S1c) - 1.0 + m_ * (1.0 - p0_)) / den)
        return ll

    cand = []
    for h in (0.6, 1.2, 2.5, 6.0):
        ker = kern(h, V1)
        # (a) 1D tổng ván trước
        S_n, S_1 = _smooth1d(g1_n, ker), _smooth1d(g1_1, ker)
        ll = loo_cells([(g1_n[c], g1_1[c], S_n[c], S_1[c]) for c in range(V1)], p0, m)
        cand.append((ll, (S_1[qa] + m * p0) / (S_n[qa] + m)))
        # (b) 2D (tổng ván trước, tổng ván trước nữa) — tách biến: làm mịn theo hàng rồi theo cột
        r_n = [_smooth1d(row, ker) for row in g2_n]
        r_1 = [_smooth1d(row, ker) for row in g2_1]
        cols_n = [_smooth1d([r_n[a][b] for a in range(V1)], ker) for b in range(V1)]     # cols_n[b][a]
        cols_1 = [_smooth1d([r_1[a][b] for a in range(V1)], ker) for b in range(V1)]
        cells = []
        for a in range(V1):
            for b in range(V1):
                if g2_n[a][b] > 0.0:
                    cells.append((g2_n[a][b], g2_1[a][b], cols_n[b][a], cols_1[b][a]))
        ll = loo_cells(cells, p0, m)
        cand.append((ll, (cols_1[qb_][qa] + m * p0) / (cols_n[qb_][qa] + m)))
        # (c) 1D tổng 3 ván (đơn vị lớn hơn ≈ √3 lần)
        ker3 = kern(h * 1.7, V3)
        S_n, S_1 = _smooth1d(g3_n, ker3), _smooth1d(g3_1, ker3)
        ll = loo_cells([(g3_n[c], g3_1[c], S_n[c], S_1[c]) for c in range(V3)], p0, m)
        cand.append((ll, (S_1[qs] + m * p0) / (S_n[qs] + m)))
    mx = max(c[0] for c in cand)
    sw = sq = 0.0
    for ll, q in cand:
        wgt = math.exp(ll - mx)
        sw += wgt
        sq += wgt * q
    return _sgn_vote(sq / sw - 0.5, 1e-12)


# ── 5) SPEC — ngoại suy phổ DFT (chu kỳ ẩn) ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
_FFT_TW = {}


def _fft(a):
    """FFT radix-2 lặp tại chỗ (len(a) là luỹ thừa của 2), thuần Python."""
    n = len(a)
    tw = _FFT_TW.get(n)
    if tw is None:
        tw = _FFT_TW[n] = [complex(math.cos(-2.0 * math.pi * k / n), math.sin(-2.0 * math.pi * k / n)) for k in range(n // 2)]
    j = 0
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j ^= bit
        if i < j:
            a[i], a[j] = a[j], a[i]
    ln_ = 2
    while ln_ <= n:
        half = ln_ >> 1
        step = n // ln_
        for i in range(0, n, ln_):
            k = 0
            for q in range(i, i + half):
                u = a[q]
                v = a[q + half] * tw[k]
                a[q] = u + v
                a[q + half] = u - v
                k += step
        ln_ <<= 1
    return a


def lg_spec(S, W=400, K=3):
    """SPEC: tìm chu kỳ ẩn bằng phổ Fourier. Lấy W=400 ván (Tài=+1/Xỉu=−1, trừ trung bình), DFT có đệm 0 (kích thước luỹ thừa 2 ≥ 2W), lấy K=3 đỉnh phổ mạnh nhất có chu kỳ 2..W/3 (≥ 3 chu kỳ trong cửa sổ, nên không nhầm xu hướng với chu kỳ),
    tinh chỉnh tần số bằng nội suy parabol quanh đỉnh rồi ước lượng biên độ + pha đúng tại tần số đó (Goertzel), cộng K sóng sin NGOẠI SUY tới ván kế tiếp -> dấu. Luôn bỏ phiếu (dấu của tổng sóng).
    Mạnh: bắt chu kỳ cố định (bệt 3 – đảo 3, nhịp 7/11/13 ván…) kể cả khi bị nhiễu chen — thứ mà mô hình ngữ cảnh (PPM/CMIXL) không tổng quát hoá được. Yếu: nguồn ngẫu nhiên thì đỉnh phổ chỉ là nhiễu
    (K đỉnh lớn nhất của nhiễu luôn tồn tại) -> ≈ 50%; chu kỳ trôi pha / đổi giữa chừng thì ngoại suy sai."""
    y = S["y"]
    n = len(y)
    if n < 60:
        return None
    mu = sum(y) / float(n)
    x = [v - mu for v in y]
    M = 1
    while M < 2 * n:
        M <<= 1
    a = [complex(v, 0.0) for v in x] + [0j] * (M - n)
    X = _fft(a)
    half = M // 2
    Pw = [X[k].real * X[k].real + X[k].imag * X[k].imag for k in range(half)]
    kmin = max(2, int(math.ceil(3.0 * M / n)))
    peaks = [k for k in range(kmin, half - 1) if Pw[k] >= Pw[k - 1] and Pw[k] > Pw[k + 1]]
    if not peaks:
        return None
    peaks.sort(key=lambda k: -Pw[k])
    xhat = 0.0
    for k in peaks[:K]:
        m1, m0, p1 = math.sqrt(Pw[k - 1]), math.sqrt(Pw[k]), math.sqrt(Pw[k + 1])
        den = m1 - 2.0 * m0 + p1
        dl = 0.5 * (m1 - p1) / den if den < -1e-12 else 0.0
        f = (k + max(-0.5, min(0.5, dl))) / M
        rot = complex(math.cos(-2.0 * math.pi * f), math.sin(-2.0 * math.pi * f))
        cur = 1.0 + 0j
        z = 0j
        for v in x:
            z += v * cur
            cur *= rot
        th = 2.0 * math.pi * f * n
        xhat += (2.0 / n) * (z * complex(math.cos(th), math.sin(th))).real
    return _sgn_vote(xhat, 1e-12)


# ── 6) CPSEG — phát hiện điểm đổi chế độ + Markov bậc 2 co phân cấp ────────────────────────────────────────────────────────────────────────────────────────────────────────
def _bern_ll(k, m):
    """Log-likelihood cực đại của m phép thử Bernoulli có k lần '1'."""
    if m <= 0 or k <= 0 or k >= m:
        return 0.0
    return k * math.log(k / m) + (m - k) * math.log((m - k) / m)


def _binseg(c, a, b, minseg, pen, out):
    """Phân đoạn nhị phân trên chuỗi 0/1 có prefix-sum c (c[i] = tổng x[0..i-1]): tìm điểm cắt s ∈ [a+minseg, b−minseg] tối đa hoá LR Bernoulli; nhận nếu LR > pen rồi đệ quy 2 nửa."""
    stack = [(a, b)]
    while stack:
        lo, hi = stack.pop()
        if hi - lo < 2 * minseg:
            continue
        whole = _bern_ll(c[hi] - c[lo], hi - lo)
        best, bs = 0.0, -1
        for s in range(lo + minseg, hi - minseg + 1):
            g = _bern_ll(c[s] - c[lo], s - lo) + _bern_ll(c[hi] - c[s], hi - s) - whole
            if g > best:
                best, bs = g, s
        if bs >= 0 and best > pen:
            out.append(bs)
            stack.append((lo, bs))
            stack.append((bs, hi))


def lg_cpseg(S, W=300, minseg=20, m=4.0):
    """CPSEG: 'chế độ' đổi thì chỉ phần SAU điểm đổi mới có giá trị. Bước 1: phân đoạn nhị phân tìm điểm đổi chế độ trên 2 chuỗi — (i) Tài/Xỉu (tỉ lệ Tài đổi) và (ii) chỉ báo ĐẢO CẦU (nhịp đảo đổi) —
    nhận điểm cắt khi tỉ số likelihood Bernoulli > 3·ln(W) (phạt kiểu BIC cho 2 tham số thêm), đoạn tối thiểu 20 ván; lấy điểm đổi MỚI NHẤT. Bước 2: Markov bậc 2 trên đoạn hiện tại với CO PHÂN CẤP:
    đoạn hiện tại (ngữ cảnh 2 ván) -> toàn cửa sổ W=300 (ngữ cảnh 2 ván) -> toàn cửa sổ (ngữ cảnh 1 ván) -> tỉ lệ chung (mỗi tầng co về tầng trên với giả-đếm m=4), nên đoạn ngắn tự dựa vào thống kê cả cửa sổ.
    Luôn bỏ phiếu. Mạnh: phản ứng nhanh khi nguồn đổi chế độ nhưng KHÔNG vứt dữ liệu cũ một cách mù quáng (shrink); là logic duy nhất tự nhận biết 'đã đổi chế độ' bằng kiểm định. Yếu: điểm đổi cuối cửa sổ (< 20 ván) chưa phát hiện được."""
    y = S["y"]
    n = len(y)
    if n < 80:
        return None
    pen = 3.0 * math.log(n)
    cps = []
    c = [0]
    for v in y:
        c.append(c[-1] + v)
    _binseg(c, 0, n, minseg, pen, cps)
    alt = [0] + [1 if y[i] != y[i - 1] else 0 for i in range(1, n)]
    c2 = [0]
    for v in alt:
        c2.append(c2[-1] + v)
    _binseg(c2, 1, n, minseg, pen, cps)
    st = max(cps) if cps else 0
    st = max(st, 2)
    # đếm
    w2 = [[0, 0] for _ in range(4)]
    w1 = [[0, 0] for _ in range(2)]
    s2 = [[0, 0] for _ in range(4)]
    g0 = g1 = 0
    for j in range(2, n):
        yy = y[j]
        k2 = 2 * y[j - 2] + y[j - 1]
        w2[k2][yy] += 1
        w1[y[j - 1]][yy] += 1
        if j >= st:
            s2[k2][yy] += 1
        if yy:
            g1 += 1
        else:
            g0 += 1
    pg = (g1 + 1.0) / (g0 + g1 + 2.0)
    q1 = y[n - 1]
    q2 = 2 * y[n - 2] + y[n - 1]
    p1 = (w1[q1][1] + m * pg) / (w1[q1][0] + w1[q1][1] + m)
    p2 = (w2[q2][1] + m * p1) / (w2[q2][0] + w2[q2][1] + m)
    ps = (s2[q2][1] + m * p2) / (s2[q2][0] + s2[q2][1] + m)
    return _sgn_vote(ps - 0.5, 1e-12)


# ─── 6 LOGIC MỚI CỦA SEQ12v5 (thuần Python, KHÔNG cần numpy) ─────────────────────────────────────────────
# CAUTPL · FSHARE · BLKHAZ · BOCPD · GBS · AFM — mỗi logic nhận S (y / t / d / p đã cắt đúng cửa sổ của nó) và trả 1 = TÀI · 0 = XỈU · None = chưa đủ ván (compute_all -> theo ván trước).
def _n_runs(y):
    """RLE: [[giá trị, độ dài], ...]"""
    r = []
    for v in y:
        if r and r[-1][0] == v:
            r[-1][1] += 1
        else:
            r.append([v, 1])
    return r


def _n_cont_vote(p_cont, y):
    """p_cont = P(ván sau GIỐNG ván trước) -> phiếu."""
    last = y[-1]
    if p_cont > 0.5:
        return last
    if p_cont < 0.5:
        return 1 - last
    return last


# ── CAUTPL: HMM "cầu mẫu" (bệt · 1-1 · 2-2 · 3-3 · 1-2 · 2-1 · 1-2-3 · 3-2-1 · 1-2-1 ...) + trạng thái "không có cầu" ──
def _build_tpl():
    tuples = [(1,), (2,), (3,), (4,), (1, 2), (2, 1), (1, 3), (3, 1), (2, 3), (3, 2),
              (1, 1, 2), (1, 2, 1), (2, 1, 1), (1, 2, 3), (3, 2, 1), (2, 2, 1), (2, 1, 2), (1, 2, 2), (3, 3, 1), (1, 1, 3)]
    seen, seqs = set(), []
    for t in tuples:
        for c0 in (0, 1):
            bits, c = [], c0
            for _ in range(2 if len(t) % 2 == 1 else 1):        # số khối lẻ -> lặp 2 lần để quay về cùng màu
                for L in t:
                    bits += [c] * L
                    c = 1 - c
            key = tuple(bits)
            if key not in seen:
                seen.add(key)
                seqs.append(key)
    seqs.append((0,))
    seqs.append((1,))                                           # bệt
    return seqs


_TPL = _build_tpl()
_TPL_BIT, _TPL_ADV, _TPL_SKIP = [], [], []
for _s in _TPL:
    _b0 = len(_TPL_BIT)
    _P = len(_s)
    for _ph in range(_P):
        _TPL_BIT.append(_s[_ph])
        _TPL_ADV.append(_b0 + (_ph + 1) % _P)
        _TPL_SKIP.append(_b0 + (_ph + 2) % _P)
_TPL_NT = len(_TPL_BIT)
_TPL_STICKY = (0.5, 0.7, 0.85, 0.3)       # P(giống ván trước) của 4 trạng thái không chu kỳ: ngẫu nhiên · bệt dính 70% · bệt dính 85% · hay đảo
_TPL_N = _TPL_NT + len(_TPL_STICKY)
# (eta nhảy mẫu, sigma trượt pha, eps nhiễu phát xạ) — 3 bộ, chọn bộ có likelihood biên cao nhất
_TPL_PARAMS = ((0.02, 0.02, 0.08), (0.05, 0.03, 0.15), (0.10, 0.04, 0.28))


def _tpl_emit(eps):
    E = [[None, None], [None, None]]                            # E[obs][prev] = danh sách P(obs | prev, state)
    for obs in (0, 1):
        for prev in (0, 1):
            row = [(1 - eps) if b == obs else eps for b in _TPL_BIT]
            row += [q if obs == prev else 1 - q for q in _TPL_STICKY]
            E[obs][prev] = row
    return E


_TPL_E = [_tpl_emit(p[2]) for p in _TPL_PARAMS]


def lg_cautpl(S, W=150):
    y = S["y"][-W:]
    n = len(y)
    if n < 12:
        return None
    N, NT = _TPL_N, _TPL_NT
    best = None
    for (eta, sig, _eps), E in zip(_TPL_PARAMS, _TPL_E):
        a_adv, a_stay = 1 - eta - 2 * sig, sig
        a = [1.0 / N] * N
        ll = 0.0
        for j in range(1, n):
            jump = eta / N                                      # tổng a = 1 -> khối nhảy mẫu chia đều
            nw = [jump] * N
            for s in range(NT):
                x = a[s]
                nw[_TPL_ADV[s]] += x * a_adv
                nw[s] += x * a_stay
                nw[_TPL_SKIP[s]] += x * a_stay
            for k in range(NT, N):
                nw[k] += a[k] * (1 - eta)
            e = E[y[j]][y[j - 1]]
            a = [nw[i] * e[i] for i in range(N)]
            sm = sum(a)
            ll += math.log(sm)
            a = [v / sm for v in a]
        jump = eta / N
        nw = [jump] * N
        for s in range(NT):
            x = a[s]
            nw[_TPL_ADV[s]] += x * a_adv
            nw[s] += x * a_stay
            nw[_TPL_SKIP[s]] += x * a_stay
        for k in range(NT, N):
            nw[k] += a[k] * (1 - eta)
        e1 = E[1][y[-1]]
        p1 = sum(nw[i] * e1[i] for i in range(N))
        if best is None or ll > best[0]:
            best = (ll, p1)
    p1 = best[1]
    return 1 if p1 > 0.5 else 0 if p1 < 0.5 else y[-1]


# ── FSHARE: Fixed-share Hedge trên ~25 "chuyên gia cầu" ──
def _fs_experts(y, j):
    last = y[j - 1]
    L = 1
    while L < j and y[j - 1 - L] == last:
        L += 1
    a = 0
    while a < j - 1 and y[j - 1 - a] != y[j - 2 - a]:
        a += 1
    e = [last, 1 - last, y[j - 2], y[j - 3], y[j - 4], y[j - 6]]
    for k in (2, 3, 4, 5, 6):
        e.append(last if L < k else 1 - last)                   # theo bệt tới k rồi bẻ
    for k in (3, 4, 5, 6, 7):
        e.append(1 - last if a < k else last)                   # theo 1-1 tới k rồi bẻ
    for k in (2, 3, 4):
        e.append(1 - last if L < k else last)                   # bẻ sớm, bệt k thì theo
    s5 = sum(y[j - 5:j])
    s9 = sum(y[j - 9:j]) if j >= 9 else s5 * 9 / 5.0
    e += [1 if s5 >= 3 else 0, 1 if s9 >= 4.5 else 0, 0 if s5 >= 3 else 1, 0 if s9 >= 4.5 else 1]
    return e


def lg_fshare(S, W=300, eta=1.0, alpha=0.05):
    y = S["y"][-W:]
    n = len(y)
    if n < 15:
        return None
    N = len(_fs_experts(y, 10))
    w = [1.0 / N] * N
    ex = math.exp(-eta)
    for j in range(10, n):
        e = _fs_experts(y, j)
        yj = y[j]
        w = [w[i] * (ex if e[i] != yj else 1.0) for i in range(N)]
        sm = sum(w)
        w = [(1 - alpha) * v / sm + alpha / N for v in w]
    e = _fs_experts(y, n)
    sc = sum(w[i] * (2 * e[i] - 1) for i in range(N))
    return 1 if sc > 0 else 0 if sc < 0 else y[-1]


# ── BLKHAZ: hazard "bậc thang" (độ dài đợt trước k · số đợt liên tiếp cùng độ dài m · độ dài hiện tại L) ──
def lg_blkhaz(S, W=400, m=6.0):
    y = S["y"][-W:]
    n = len(y)
    if n < 30:
        return None
    c3, c2, c1 = {}, {}, {}
    runs, cur = [], 1

    def state():
        if runs:
            k = runs[-1]
            mm = 1
            for i in range(len(runs) - 2, -1, -1):
                if runs[i] == k:
                    mm += 1
                else:
                    break
        else:
            k, mm = 0, 0
        return (min(k, 5), min(mm, 6), min(cur, 8))

    for j in range(1, n):
        st = state()
        cont = 1 if y[j] == y[j - 1] else 0
        c3.setdefault(st, [0, 0])[cont] += 1
        c2.setdefault((st[0], st[2]), [0, 0])[cont] += 1
        c1.setdefault(st[2], [0, 0])[cont] += 1
        if cont:
            cur += 1
        else:
            runs.append(cur)
            cur = 1
    st = state()
    b1, a1 = c1.get(st[2], (0, 0))
    p1 = (a1 + 1.0) / (a1 + b1 + 2.0)
    b2, a2 = c2.get((st[0], st[2]), (0, 0))
    p2 = (a2 + m * p1) / (a2 + b2 + m)
    b3, a3 = c3.get(st, (0, 0))
    p3 = (a3 + m * p2) / (a3 + b3 + m)
    return _n_cont_vote(p3, y)


# ── BOCPD: Bayesian Online Changepoint Detection trên chuỗi GIỐNG/KHÁC ván trước (có ngữ cảnh z ván trước) ──
def lg_bocpd(S, W=400, hz=1 / 50.0, maxh=100):
    y = S["y"][-W:]
    n = len(y)
    if n < 20:
        return None
    z = [1 if y[j] == y[j - 1] else 0 for j in range(1, n)]
    w = [1.0]
    cnt = [[0, 0, 0, 0]]                                        # cnt[r][ctx*2 + obs]
    for j in range(1, len(z)):
        ctx, obs = z[j - 1], z[j]
        i0, i1 = ctx * 2, ctx * 2 + 1
        pr = [(c[ctx * 2 + obs] + 1.0) / (c[i0] + c[i1] + 2.0) for c in cnt]
        g = [w[r] * pr[r] * (1 - hz) for r in range(len(w))]
        cp = sum(w[r] * pr[r] for r in range(len(w))) * hz
        w = [cp] + g
        cnt = [[0, 0, 0, 0]] + cnt
        for r in range(1, len(cnt)):
            cnt[r][ctx * 2 + obs] += 1
        sm = sum(w)
        if sm > 0:
            w = [v / sm for v in w]
        else:
            w = [1.0 / len(w)] * len(w)
        if len(w) > maxh:
            keep = sorted(sorted(range(len(w)), key=lambda r: -w[r])[:maxh])
            w = [w[r] for r in keep]
            cnt = [cnt[r] for r in keep]
            sm = sum(w)
            w = [v / sm for v in w]
    ctx = z[-1]
    i0, i1 = ctx * 2, ctx * 2 + 1
    p_stay = (1 - hz) * sum(w[r] * (cnt[r][i1] + 1.0) / (cnt[r][i0] + cnt[r][i1] + 2.0) for r in range(len(w))) + hz * 0.5
    return _n_cont_vote(p_stay, y)


# ── GBS: boosting cây gốc (stump) log-loss trên ~12 đặc trưng cầu — mô hình CỘNG, co mạnh về 50% khi không có cấu trúc ──
def _gbs_feats(y, t, j):
    last = y[j - 1]
    L = 1
    while L < j and y[j - 1 - L] == last:
        L += 1
    pl = 0
    if L < j:
        pl = 1
        while L + pl < j and y[j - 1 - L - pl] == y[j - 1 - L]:
            pl += 1
    a = 0
    while a < j - 1 and y[j - 1 - a] != y[j - 2 - a]:
        a += 1
    b8 = sum(y[j - 8:j]) if j >= 8 else 4
    b24 = sum(y[max(0, j - 24):j]) * 24 // max(1, min(24, j)) // 3
    sw10 = sum(1 for i in range(max(1, j - 10), j) if y[i] != y[i - 1])
    return [y[j - 1], y[j - 2], y[j - 3], y[j - 4], min(L, 12), min(pl, 8), min(a, 12), b8, b24, t[j - 1], (t[j - 1] + t[j - 2]) // 3, sw10]


def lg_gbs(S, W=500, rounds=30, lr=0.12, lam=8.0, minh=6.0):
    y = S["y"][-W:]
    t = S["t"][-W:]
    n = len(y)
    if n < 80:
        return None
    X = [_gbs_feats(y, t, j) for j in range(12, n)]
    Y = y[12:]
    xc = _gbs_feats(y, t, n)
    m = len(Y)
    nf = len(xc)
    cols = [[X[i][f] for i in range(m)] for f in range(nf)]
    vals = [sorted(set(c)) for c in cols]
    pos = [{v: k for k, v in enumerate(vs)} for vs in vals]
    idx = [[pos[f][v] for v in cols[f]] for f in range(nf)]    # chỉ số giá trị của từng mẫu theo từng đặc trưng
    F = [0.0] * m
    Fc = 0.0
    for _ in range(rounds):
        p = [1.0 / (1.0 + math.exp(-v)) for v in F]
        g = [Y[i] - p[i] for i in range(m)]
        h = [p[i] * (1 - p[i]) for i in range(m)]
        Gt, Ht = sum(g), sum(h)
        best = None
        for f in range(nf):
            k = len(vals[f])
            if k < 2:
                continue
            G = [0.0] * k
            H = [0.0] * k
            ix = idx[f]
            for i in range(m):
                v = ix[i]
                G[v] += g[i]
                H[v] += h[i]
            Gl = Hl = 0.0
            for q in range(k - 1):
                Gl += G[q]
                Hl += H[q]
                Gr, Hr = Gt - Gl, Ht - Hl
                if Hl < minh or Hr < minh:
                    continue
                gain = Gl * Gl / (Hl + lam) + Gr * Gr / (Hr + lam)
                if best is None or gain > best[0]:
                    best = (gain, f, q, Gl / (Hl + lam), Gr / (Hr + lam))
        if best is None:
            break
        _, f, q, vl, vr = best
        ix = idx[f]
        for i in range(m):
            F[i] += lr * (vl if ix[i] <= q else vr)
        # giá trị chưa từng gặp trong cửa sổ: so với ngưỡng bằng số thật
        thr_val = vals[f][q]
        Fc += lr * (vl if xc[f] <= thr_val else vr)
    return 1 if Fc > 0 else 0 if Fc < 0 else y[-1]


# ── AFM: Markov bậc 1..4 × 4 hệ số QUÊN, trọng số theo log-loss tiên nghiệm gần đây ──
def lg_afm(S, W=450, orders=(1, 2, 3, 4), lams=(0.90, 0.96, 0.99, 1.0), ld=0.97, beta=1.0):
    y = S["y"][-W:]
    n = len(y)
    if n < 40:
        return None
    exps = [(o, l) for o in orders for l in lams]
    cnt = [dict() for _ in exps]
    loss = [0.0] * len(exps)
    omax = max(orders)

    def pred(i, ctx, j):
        l = exps[i][1]
        c = cnt[i].get(ctx)
        if c is None:
            return 0.5, 0.0, 0.0
        n0, n1, t0 = c
        if l < 1.0 and t0 != j:
            f = l ** (j - t0)
            n0 *= f
            n1 *= f
        return (n1 + 0.5) / (n0 + n1 + 1.0), n0, n1

    for j in range(omax, n):
        yj = y[j]
        for i, (o, l) in enumerate(exps):
            ctx = tuple(y[j - o:j])
            p, n0, n1 = pred(i, ctx, j)
            pp = p if yj == 1 else 1 - p
            loss[i] = ld * loss[i] - math.log(max(pp, 1e-6))
            if yj == 1:
                n1 += 1
            else:
                n0 += 1
            cnt[i][ctx] = (n0, n1, j)
    lo = min(loss)
    wts = [math.exp(-beta * (v - lo)) for v in loss]
    sw = sum(wts)
    ps = 0.0
    for i, (o, l) in enumerate(exps):
        p, _, _ = pred(i, tuple(y[n - o:n]), n)
        ps += wts[i] / sw * p
    return 1 if ps > 0.5 else 0 if ps < 0.5 else y[-1]


# ─── 5 LOGIC MỚI Ở SEQ13v6 (thuần Python, KHÔNG cần numpy) — CTW · MATCHR · FTRL · ESN2 · RLS (+ CMIXL là hàm cũ có sẵn ở trên, nay đưa lại vào SUN_LOGICS) ─────────────────
# Mỗi logic nhận S (y / t / d / p đã cắt đúng cửa sổ của nó) và trả 1 = TÀI · 0 = XỈU · None = chưa đủ ván (compute_all -> theo ván trước). Cả 5 luôn bỏ phiếu khi đủ ván (không cổng thống kê).

# ── CTW: Context Tree Weighting (ước lượng KT) — trộn Bayes TẤT CẢ cây ngữ cảnh độ sâu <= D ──
def _ctw_lae(a, b):
    m = a if a > b else b
    return m + math.log1p(math.exp(-abs(a - b)))


def _ctw_path(y, i, D):
    """Khoá nút từ gốc tới độ sâu D của ván i: (độ sâu, ngữ cảnh = D ván gần nhất trước i, trước 0 coi là 0)."""
    ks = [(0, 0)]
    c = 0
    for d in range(1, D + 1):
        b = y[i - d] if i - d >= 0 else 0
        c |= b << (d - 1)
        ks.append((d, c))
    return ks


def _ctw_upd(nodes, ks, D, x, commit):
    """Cập nhật các nút trên đường ks bằng ký hiệu x; trả log xác suất có trọng số ở gốc. commit=False -> chỉ tính thử, không ghi."""
    lw_child = 0.0
    for d in range(D, -1, -1):
        key = ks[d]
        nd = nodes.get(key)
        if nd is None:
            a = b = 0
            lpe = 0.0
        else:
            a, b, lpe, _ = nd
        if x:
            lpe += math.log((b + 0.5) / (a + b + 1.0))
            b += 1
        else:
            lpe += math.log((a + 0.5) / (a + b + 1.0))
            a += 1
        if d == D:
            lpw = lpe
        else:
            sn = nodes.get((d + 1, ks[d + 1][1] ^ (1 << d)))
            lsib = sn[3] if sn is not None else 0.0
            lpw = _ctw_lae(math.log(0.5) + lpe, math.log(0.5) + lw_child + lsib)
        lw_child = lpw
        if commit:
            nodes[key] = [a, b, lpe, lpw]
    return lw_child


def lg_ctw(S, D=8):
    """CTW: Context Tree Weighting (Willems–Shtarkov–Tjalkens) với ước lượng KT, độ sâu D=8. Mỗi ván trong cửa sổ cập nhật 9 nút (ngữ cảnh 0..8 ván trước); mỗi nút giữ 'bằng chứng' của chính nó
    và của việc CHIA nhỏ ngữ cảnh -> gốc là TRUNG BÌNH BAYES của mọi cây ngữ cảnh có độ sâu <= 8 (không phải đoán 'bậc nào đúng'). Dự đoán = so xác suất có trọng số khi nối thêm Tài với nối thêm Xỉu. Luôn bỏ phiếu.
    Mạnh: bắt được cầu ngắn lẫn dài, tự co về bậc thấp khi ít mẫu, co về 50% khi chuỗi ngẫu nhiên (không bịa cấu trúc); chặt về lý thuyết (tối ưu cho nguồn cây ngữ cảnh). Yếu: coi cửa sổ là DỪNG nên chậm theo kịp khi
    cầu đổi chế độ giữa chừng (REGIME · BOCPD · RLS bù chỗ này); chỉ nhìn Tài/Xỉu, không dùng tổng."""
    y = S["y"]
    n = len(y)
    if n < 20:
        return None
    nodes = {}
    for i in range(n):
        _ctw_upd(nodes, _ctw_path(y, i, D), D, y[i], True)
    ks = _ctw_path(y, n, D)
    l1 = _ctw_upd(nodes, ks, D, 1, False)
    l0 = _ctw_upd(nodes, ks, D, 0, False)
    return 1 if l1 > l0 + 1e-12 else 0 if l0 > l1 + 1e-12 else None


# ── MATCHR: khớp hậu tố DÀI NHẤT (kiểu PPM*) có ưu tiên ván gần ──
def lg_matchr(S, Lmax=32, pw=2.0, tau=150.0):
    """MATCHR: mọi vị trí j trong cửa sổ mà ván j-1 trùng ván cuối đều là 1 'ứng viên'; độ dài khớp L = số ván liền trước chung với hậu tố hiện tại (tối đa 32). Mỗi ứng viên bỏ phiếu cho ván y[j] đứng NGAY SAU nó
    với trọng số L^2 × exp(-tuổi/150) (khớp càng dài và càng gần thì càng nặng). Tổng phiếu có dấu > 0 -> TÀI. Luôn bỏ phiếu.
    Mạnh: bậc tự thích nghi theo độ dài khớp — cầu lặp dài thì khớp dài thắng, không có thì rơi về bậc 1 (≈ Markov bậc 1); không có tham số 'bậc'; cực nhanh (<1 ms). Yếu: gần như TRÙNG phiếu AFM · KNNH (cùng họ 'tìm đoạn giống');
    khớp ngẫu nhiên ở L ngắn là nhiễu; không học được quy luật không nằm trong chuỗi liền kề (SPARSE · CMIXL bù chỗ này)."""
    y = S["y"]
    n = len(y)
    if n < 30:
        return None
    s = 0.0
    last = y[n - 1]
    for j in range(1, n):
        if y[j - 1] != last:
            continue
        L = 1
        while L < Lmax and j - 1 - L >= 0 and y[j - 1 - L] == y[n - 1 - L]:
            L += 1
        s += (L ** pw) * math.exp(-(n - j) / tau) * (1 if y[j] else -1)
    return 1 if s > 0 else 0 if s < 0 else None


# ── FTRL: hồi quy logistic ONLINE (FTRL-Proximal) trên đặc trưng n-gram + lag đơn + độ dài đợt ──
def _ftrl_feats(y, i, kmax, lagmax):
    f = [("b",)]
    c = 0
    for k in range(1, kmax + 1):
        if i - k < 0:
            break
        c = c * 2 + y[i - k]
        f.append(("g", k, c))
    for j in range(1, lagmax + 1):
        if i - j < 0:
            break
        f.append(("l", j, y[i - j]))
    if i >= 1:
        r = 1
        while i - 1 - r >= 0 and y[i - 1 - r] == y[i - 1] and r < 12:
            r += 1
        f.append(("r", r, y[i - 1]))
    return f


def lg_ftrl(S, kmax=8, lagmax=12, alpha=0.15, beta=1.0, l1=0.2, l2=1.0, epochs=1):
    """FTRL: hồi quy logistic học ONLINE bằng FTRL-Proximal (tốc độ học riêng từng đặc trưng + phạt L1/L2) trên ~22 đặc trưng thưa của mỗi ván: n-gram độ dài 1..8, bit đơn ở lag 1..12, (độ dài đợt hiện tại, ván trước).
    Duyệt 1 lượt theo thứ tự thời gian (ván j chỉ thấy ván < j) rồi dự đoán ván kế. Luôn bỏ phiếu. Mạnh: học kiểu PHÂN BIỆT (các đặc trưng cạnh tranh trọng số trong 1 mô hình logistic) khác hẳn kiểu ĐẾM của CTW · MATCHR · AFM;
    phạt L1 làm đặc trưng ồn về 0 nên co về 50% khi không có cấu trúc. Yếu: nhạy tham số (alpha / l1); hơi kém khi cầu thưa lag xa; các đặc trưng chồng lấn nên 'chia' trọng số thiếu ổn định khi ít ván."""
    y = S["y"]
    n = len(y)
    if n < 60:
        return None
    z = {}
    nn = {}

    def wt(k):
        zz = z.get(k, 0.0)
        if abs(zz) <= l1:
            return 0.0
        return -(zz - (l1 if zz > 0 else -l1)) / ((beta + math.sqrt(nn.get(k, 0.0))) / alpha + l2)

    for _ in range(epochs):
        for i in range(2, n):
            fs = _ftrl_feats(y, i, kmax, lagmax)
            ws = [wt(k) for k in fs]
            s = max(-30.0, min(30.0, sum(ws)))
            g = 1.0 / (1.0 + math.exp(-s)) - y[i]
            for k, w in zip(fs, ws):
                n0 = nn.get(k, 0.0)
                z[k] = z.get(k, 0.0) + g - (math.sqrt(n0 + g * g) - math.sqrt(n0)) / alpha * w
                nn[k] = n0 + g * g
    s = sum(wt(k) for k in _ftrl_feats(y, n, kmax, lagmax))
    return 1 if s > 0 else 0 if s < 0 else None


# ── ESN2: Echo-State Network nhỏ (reservoir ngẫu nhiên CỐ ĐỊNH) + ridge readout ──
_ESN_NETS = {}


def _esn_net(R, seed=7):
    k = (R, seed)
    net = _ESN_NETS.get(k)
    if net is not None:
        return net
    import random
    rnd = random.Random(seed)
    W = [[(rnd.uniform(-1, 1) if rnd.random() < 0.25 else 0.0) for _ in range(R)] for _ in range(R)]
    v = [1.0] * R
    nm = 1.0
    for _ in range(40):                                         # power iteration -> bán kính phổ ≈ 0.9
        u = [sum(W[i][j] * v[j] for j in range(R)) for i in range(R)]
        nm = math.sqrt(sum(a * a for a in u)) or 1.0
        v = [a / nm for a in u]
    W = [[0.9 * w / nm for w in row] for row in W]
    Win = [rnd.uniform(-1, 1) for _ in range(R)]
    net = _ESN_NETS[k] = (W, Win)
    return net


def _esn_solve(A, b):
    n = len(A)
    M = [A[i][:] + [b[i]] for i in range(n)]
    for c in range(n):
        piv = max(range(c, n), key=lambda r: abs(M[r][c]))
        M[c], M[piv] = M[piv], M[c]
        d = M[c][c]
        if abs(d) < 1e-12:
            continue
        for j in range(c, n + 1):
            M[c][j] /= d
        for r in range(n):
            if r != c and M[r][c] != 0.0:
                f = M[r][c]
                for j in range(c, n + 1):
                    M[r][j] -= f * M[c][j]
    return [M[i][n] for i in range(n)]


def lg_esn2(S, R=24, leak=0.3, lam=10.0, wash=20):
    """ESN2: Echo-State Network — reservoir 24 nơ-ron tanh (kết nối thưa, bán kính phổ 0.9, seed cố định = kết quả lặp lại được) chạy dọc cửa sổ 300 ván làm 'bộ nhớ động' phi tuyến của chuỗi ±1; chỉ lớp ĐỌC RA
    (ridge λ=10, 25 trọng số) được học: trạng thái hiện tại -> ván kế. Dấu của đầu ra = phiếu. Luôn bỏ phiếu. Mạnh: mô hình PHI TUYẾN có bộ nhớ liên tục — khác hẳn các logic đếm ngữ cảnh rời rạc (trùng phiếu thấp nhất trong nhóm mới);
    bắt tốt cầu nghiêng / trôi chậm và đổi chế độ mượt. Yếu: khó giải thích; có thể 'học' nhiễu (ridge λ lớn + cửa sổ 300 ván chỉ hạn chế chứ không loại bỏ); chậm nhất nhóm mới (~15 ms)."""
    y = S["y"]
    n = len(y)
    if n < 80:
        return None
    W, Win = _esn_net(R)
    x = [0.0] * R
    X = []
    for i in range(n):
        u = 2 * y[i] - 1
        nx = []
        for r in range(R):
            a = Win[r] * u
            Wr = W[r]
            for j in range(R):
                if Wr[j] != 0.0:
                    a += Wr[j] * x[j]
            nx.append((1 - leak) * x[r] + leak * math.tanh(a))
        x = nx
        X.append(x + [1.0])
    D = R + 1
    A = [[0.0] * D for _ in range(D)]
    bv = [0.0] * D
    for i in range(wash, n - 1):
        xi = X[i]
        tgt = 2 * y[i + 1] - 1
        for a in range(D):
            xa = xi[a]
            bv[a] += xa * tgt
            Aa = A[a]
            for c in range(D):
                Aa[c] += xa * xi[c]
    for a in range(D):
        A[a][a] += lam
    w = _esn_solve(A, bv)
    f = sum(w[a] * X[n - 1][a] for a in range(D))
    return 1 if f > 0 else 0 if f < 0 else None


# ── RLS: bộ lọc tuyến tính THÍCH NGHI (Recursive Least Squares, hệ số quên λ) ──
def lg_rlsar(S, p=6, lam=0.99, delta=50.0):
    """RLS: hồi quy tự hồi quy bậc 6 trên chuỗi ±1 (có hằng số), hệ số cập nhật từng ván bằng Recursive Least Squares với hệ số QUÊN λ=0.99 (trí nhớ hiệu dụng ~100 ván) -> dự đoán tuyến tính ván kế từ 6 ván cuối. Dấu = phiếu.
    Luôn bỏ phiếu. Mạnh: THEO KỊP cầu đổi chế độ (bệt <-> 1-1 <-> ngẫu nhiên) nhanh hơn các logic học cố định cả cửa sổ; rất nhẹ (~5 ms). Yếu: chỉ thấy quan hệ TUYẾN TÍNH ở 6 ván liền kề —
    mù với cầu lag thưa / XOR (SPARSE · CMIXL bù); trí nhớ ngắn nên hệ số ồn khi chuỗi ngẫu nhiên (≈ 50%, không hơn)."""
    y = S["y"]
    n = len(y)
    if n < 40:
        return None
    x = [2.0 * v - 1.0 for v in y]
    d = p + 1
    w = [0.0] * d
    P = [[delta if i == j else 0.0 for j in range(d)] for i in range(d)]
    for i in range(p, n):
        u = [1.0] + [x[i - 1 - k] for k in range(p)]
        Pu = [sum(P[a][b] * u[b] for b in range(d)) for a in range(d)]
        den = lam + sum(u[a] * Pu[a] for a in range(d))
        kk = [v / den for v in Pu]
        e = x[i] - sum(w[a] * u[a] for a in range(d))
        w = [w[a] + kk[a] * e for a in range(d)]
        P = [[(P[a][b] - kk[a] * Pu[b]) / lam for b in range(d)] for a in range(d)]
    u = [1.0] + [x[n - 1 - k] for k in range(p)]
    f = sum(w[a] * u[a] for a in range(d))
    return 1 if f > 0 else 0 if f < 0 else None


# ── CỬA SỔ DỮ LIỆU RIÊNG CỦA TỪNG LOGIC (SEQ13v6): mỗi logic CHỈ ĐỌC đúng số ván GẦN NHẤT mà nó mạnh nhất (compute_all cắt lịch sử trước khi gọi) ───────────────────────────────
# Lý do: logic nhẹ/ngắn hạn (KNNH · REGIME · RLS…) càng đọc nhiều ván cũ càng bị pha loãng bởi chế độ cũ; logic mô hình-dày (CMIXL · SPARSE · CTW) cần nhiều ván mới đủ bằng chứng.
# Mọi ván trong cửa sổ có trọng số NHƯ NHAU (không decay). Đổi từng logic bằng env SUNVIW_WIN_<TÊN> (vd. SUNVIW_WIN_CTW=300); chạy tune_windows.py trên data thật để tìm cửa sổ tốt nhất cho từng logic.
# Lịch sử tool giữ HIST_KEEP (mặc định 600) ván — cửa sổ lớn hơn số ván đang có thì logic đọc hết số ván đang có.
LOGIC_WIN_DEFAULT = (("REGIME", 250), ("KNNH", 200), ("SPARSE", 500), ("BLKHAZ", 400), ("BOCPD", 400), ("GBS", 500), ("AFM", 450),
                     ("CTW", 450), ("MATCHR", 450), ("FTRL", 450), ("ESN2", 300), ("RLS", 400), ("CMIXL", 500))
LOGIC_WIN = {_nm: max(40, _env_num("SUNVIW_WIN_" + _nm, _w, int)) for _nm, _w in LOGIC_WIN_DEFAULT}


SUN_LOGICS = [
    ("REGIME", lambda S: lg_regime(S, 20, 250)),
    ("KNNH", lambda S: lg_knnh(S)),
    ("SPARSE", lambda S: lg_sparse(S)),
    ("BLKHAZ", lambda S: lg_blkhaz(S)),
    ("BOCPD", lambda S: lg_bocpd(S)),
    ("GBS", lambda S: lg_gbs(S)),
    ("AFM", lambda S: lg_afm(S)),
    ("CTW", lambda S: lg_ctw(S, 8)),
    ("MATCHR", lambda S: lg_matchr(S)),
    ("FTRL", lambda S: lg_ftrl(S)),
    ("ESN2", lambda S: lg_esn2(S)),
    ("RLS", lambda S: lg_rlsar(S, 6, 0.99)),
    ("CMIXL", lambda S: lg_cmixl(S)),
]


SUN_NAMES = [n for n, _ in SUN_LOGICS]
SUN_SIG = "SEQ13v6:" + ",".join(SUN_NAMES)         # dấu vân tay bộ logic SUN (bỏ dữ liệu graded của bộ logic cũ -> không lẫn data bộ 13 logic SEQ13v6)

# 13 logic là số LẺ nên đa số tất cả logic không bao giờ hoà, nhưng NHÓM CAO/THẤP của AF (kích thước bất kỳ) vẫn có thể hoà -> phiếu phá hoà: lấy phiếu của logic này (mặc định AFM; env SUNVIW_TIE_LOGIC).
SUN_TIE_LOGIC = os.environ.get("SUNVIW_TIE_LOGIC", "AFM")
if SUN_TIE_LOGIC not in SUN_NAMES:
    SUN_TIE_LOGIC = "AFM" if "AFM" in SUN_NAMES else SUN_NAMES[0]


def _sun_tiebreak(votes, cfg=SUN):
    """Phiếu phá hoà của SUN: phiếu của logic SUN_TIE_LOGIC."""
    i = SUN_NAMES.index(cfg.TIE_LOGIC if cfg.TIE_LOGIC in SUN_NAMES else SUN_TIE_LOGIC)
    return votes[i] if i < len(votes) else votes[0]


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


def _wr_decision_cfg(votes, graded, cfg=SUN):
    """wr_decision (cách chốt cũ / dự phòng) với tham số WR của `cfg`. cfg = SUN -> y hệt wr_decision(votes, graded)."""
    return wr_decision(votes, graded, cfg.WR_WINDOW, cfg.W_DECAY, cfg.W_FLOOR, cfg.WR_MIN_GAMES, cfg.W_NEWEST, cfg.WR_FLIP_WEIGHT)


def af_mode_wr(graded, cfg=SUN):
    """WR của 3 chế độ CAO / THẤP / ALL trên AF_MODE_WINDOW ván gần nhất CỦA CHẾ ĐỘ ĐÓ — mỗi chế độ được xét RIÊNG.
    Dữ liệu = vote gốc của nhóm CAO (hv) / nhóm THẤP (lv) / pool ALL = đa số tất cả logic sau bẻ logic (av) đã LƯU trong từng ván đã chấm (cả khi tool đang chạy chế độ khác),
    chấm với kết quả thật. Ván không có vote của chế độ đó (nhóm rỗng / hoà phiếu / chưa đủ ván / ván cũ chưa lưu av) thì bỏ qua.
    Trả {"CAO": {...}, "THAP": {...}, "ALL": {...}}, mỗi chế độ có: n · w (số ván đúng) · need · wr (% hoặc None nếu chưa đủ ván) · flip (True = WR < AF_MODE_BELOW) · chuoi (cũ -> mới, True = đúng)."""
    need = max(1, min(cfg.AF_MODE_MIN, cfg.AF_MODE_WINDOW))
    out = {}
    for mode, key in (("CAO", "hv"), ("THAP", "lv"), ("ALL", "av")):
        rows = []
        for g in reversed(graded):                       # đi từ ván mới nhất lùi về, lấy đủ AF_MODE_WINDOW ván có vote của chế độ này
            v = g.get(key)
            if v in (TAI, XIU):
                rows.append(v == g["actual"])
                if len(rows) >= cfg.AF_MODE_WINDOW:
                    break
        rows.reverse()
        n, w = len(rows), sum(rows)
        ready = n >= need
        out[mode] = {"n": n, "w": w, "need": need, "wr": (w * 100.0 / n) if ready else None,
                     "flip": bool(cfg.AF_MODE_FLIP and ready and w * 100 < cfg.AF_MODE_BELOW * n), "chuoi": rows}   # AF_MODE_FLIP tắt -> flip luôn False (không bẻ chế độ)
    return out


def _af_prev_mode(graded):
    """Chế độ (ALL | CAO | THAP) của ván đã chấm GẦN NHẤT — dùng để xét đổi chế độ. Ván đầu / ván cũ chưa lưu chế độ (AF tắt lúc đó) -> ALL."""
    if graded:
        m = graded[-1].get("mode")
        if m in ("ALL", "CAO", "THAP"):
            return m
    return "ALL"


AF_SWITCH_PRIO_ORDER = {"ALL": "CAO", "CAO": "ALL", "THAP": "CAO"}   # ván trước ở chế độ nào -> khi 2 chế độ còn lại cùng đủ phiếu thì ưu tiên chế độ này


def _af_pick_mode(mvotes, cur, need, lead=False, prio=False):
    """ĐỔI CHẾ ĐỘ DỄ HƠN (AF_SWITCH): từ chế độ hiện tại `cur`, chọn chế độ cho ván này theo phiếu của 3 chế độ `mvotes` ({"ALL","CAO","THAP"} -> số logic).
    lead=False (mặc định, đúng ý "chỉ cần N phiếu"): chế độ KHÁC có >= `need` phiếu (vd 6/13; bản gốc phải đa số 7/13) là ĐỔI, kể cả khi chế độ hiện tại đang nhiều phiếu hơn.
        Nhiều chế độ khác cùng đủ `need` -> lấy chế độ nhiều phiếu nhất; bằng nhau ở đầu bảng, hoặc không chế độ khác nào đủ `need` -> GIỮ `cur`.
        prio=True (AF_SWITCH_PRIO): khi CẢ 2 chế độ còn lại cùng đủ `need` phiếu thì KHÔNG so số phiếu nữa mà ưu tiên theo chế độ ván trước:
            đang ALL -> ưu tiên CAO · đang CAO -> ưu tiên ALL · đang THẤP -> ưu tiên CAO (xem AF_SWITCH_PRIO_ORDER). Chỉ 1 chế độ đủ phiếu -> đổi sang chế độ đó như thường.
    lead=True (êm hơn): chế độ mới còn phải DẪN ĐẦU DUY NHẤT (nhiều phiếu hơn mọi chế độ khác, kể cả chế độ đang chạy) mới đổi.
        Lưu ý: 13 logic chia cho 3 chế độ thì bên dẫn đầu luôn >= 5 phiếu nên với lead=True mọi `need` <= 5 cho kết quả y hệt nhau."""
    if lead:
        ok = {m: c for m, c in mvotes.items() if c >= need}
        if not ok:
            return cur
        best = max(ok.values())
        top = [m for m, c in ok.items() if c == best]
        if cur in top or len(top) != 1:
            return cur
        return top[0]
    cand = {m: c for m, c in mvotes.items() if m != cur and c >= need}
    if not cand:
        return cur
    if prio and len(cand) >= 2:                           # cả 2 chế độ còn lại đều đủ phiếu -> ưu tiên theo chế độ ván trước
        pm = AF_SWITCH_PRIO_ORDER.get(cur)
        if pm in cand:
            return pm
    best = max(cand.values())
    top = [m for m, c in cand.items() if c == best]
    return top[0] if len(top) == 1 else cur


def af_decision(votes, graded, cfg=SUN):
    """AF (auto-flip + CAO/THẤP + bẻ theo WR chế độ) của SUN — port từ SUNVIW_9logics_autoflip_auto.html (xem khối CONFIG AF).
    Trả dict: mode (CAO | THAP | ALL) · final (SAU bẻ chế độ) · base (TRƯỚC bẻ chế độ) · mflip (đã bẻ chế độ) · tie (pool hoà phiếu -> dùng đa số tất cả logic)
    preds (phiếu sau bẻ logic) · flips[i] (LOW | HIGH | None) · wins / wsum (trọng số) · eff[i] (WR dùng, 0-100) · group[i] (CAO | THAP | None) · hi / lo (chỉ số logic mỗi nhóm)
    hv / lv / av (vote gốc của nhóm CAO / nhóm THẤP / pool ALL — LƯU vào ván đã chấm) · gT / gX (phiếu TÀI / XỈU trong pool) · avg (TB WR dùng của pool, độ tin cậy) · mw (WR 3 chế độ CAO / THAP / ALL)
    demoted (True = nhóm CAO / THẤP được chọn ít hơn đa số toàn bộ logic -> đã hạ về ALL) · need_maj (số logic tối thiểu để một nhóm được dùng).
    prev (chế độ ván trước) · mvotes (phiếu 3 chế độ: ALL = logic không thuộc nhóm nào · CAO · THAP) · sw_need (số phiếu để đổi chế độ, AF_SWITCH_NEED) · switched (True = chế độ ván này khác ván trước).
    AF_SWITCH bật: chế độ NHỚ ván trước, chế độ khác đủ sw_need phiếu (6/13) là đổi (xem _af_pick_mode); AF_SWITCH tắt: nhóm đông hơn thắng + đa số 7/13 như bản gốc.
    AF_GROUP_FLIPPED_ONLY: chỉ logic bị bẻ mới có group (CAO | THAP); logic không bẻ -> group None = mặc định ALL."""
    nl = len(votes)
    all_vote = vote_result(votes)
    win = graded[-cfg.WR_WINDOW:]                             # cũ -> mới (cùng cửa sổ WR với cách cũ của SUN)
    n = len(win)
    need = max(1, min(cfg.AF_MIN_GAMES, cfg.WR_WINDOW))
    mw = af_mode_wr(graded, cfg)
    out = {"mode": "ALL", "n": n, "need": need, "final": all_vote, "base": all_vote, "mflip": False, "tie": False, "demoted": False,
           "need_maj": nl // 2 + 1,
           "prev": _af_prev_mode(graded), "mvotes": {"ALL": nl, "CAO": 0, "THAP": 0}, "sw_need": max(1, min(int(cfg.AF_SWITCH_NEED), nl)),     # chưa đủ ván -> chưa chia nhóm: mọi logic = phiếu ALL
           "switched": _af_prev_mode(graded) != "ALL",
           "preds": list(votes), "flips": [None] * nl, "wins": [], "wsum": 0.0, "weights": [], "eff": [None] * nl,
           "group": [None] * nl, "hi": [], "lo": [], "hv": None, "lv": None, "av": all_vote if all_vote in (TAI, XIU) else None, "pool": list(range(nl)),     # pool = logic THỰC SỰ tham gia vote ván này (chưa đủ ván -> vote tất cả)
           "gT": sum(1 for v in votes if v == TAI), "gX": sum(1 for v in votes if v == XIU), "avg": None, "mw": mw}
    if n < need:                                          # chưa đủ ván -> không bẻ, vote tất cả (như file HTML)
        return out
    weights = wr_weights(n, cfg.W_DECAY, cfg.W_FLOOR, cfg.W_NEWEST, cfg.WR_FLIP_WEIGHT)                               # trọng số WR của SUN (cũ nhất -> mới nhất)
    wsum = sum(weights)
    wins = [sum((wt for wt, g in zip(weights, win) if g["votes"][i] == g["actual"]), Fraction(0)) for i in range(nl)]
    thr_lo, thr_hi = Fraction(str(cfg.AF_FLIP_LOW)), Fraction(str(cfg.AF_FLIP_HIGH))
    b_lo = (Fraction(str(cfg.AF_FLIP_LOW_MIN)), Fraction(str(cfg.AF_FLIP_LOW_MAX)))                       # vùng bẻ THẤP [min, max] (%)
    b_hi = (Fraction(str(cfg.AF_FLIP_HIGH_MIN)), Fraction(str(cfg.AF_FLIP_HIGH_MAX)))                     # vùng bẻ CAO  [min, max] (%)

    def _flip_kind(w):
        x = w * 100                                                                               # so với (% × tổng trọng số) -> chính xác, không sai số float
        if cfg.AF_FLIP_BAND:                                                                          # chỉ bẻ khi WR nằm TRONG vùng (gồm đầu mút); ngoài vùng -> không bẻ
            if b_lo[0] * wsum <= x <= b_lo[1] * wsum:
                return "LOW"
            if b_hi[0] * wsum <= x <= b_hi[1] * wsum:
                return "HIGH"
            return None
        return "LOW" if x < thr_lo * wsum else ("HIGH" if x > thr_hi * wsum else None)             # cách cũ: không có cận

    preds, flips, effw, group = [], [], [], []
    for i, w in enumerate(wins):
        f = _flip_kind(w)                                                                         # Bước 1: bẻ logic
        e = (wsum - w) if f else w                        # trọng số đúng SAU bẻ -> WR dùng = 100 − WR gốc khi bị bẻ
        preds.append(flip_pred(votes[i]) if f else votes[i])
        flips.append(f)
        effw.append(e)
        if cfg.AF_GROUP_FLIPPED_ONLY and not f:                                                         # Bước 2: logic KHÔNG bẻ (WR ngoài vùng bẻ) -> không thuộc nhóm nào = mặc định ALL
            group.append(None)
        else:                                                                                         # nhóm theo WR dùng (sau bẻ)
            group.append("CAO" if e * 2 > wsum else ("THAP" if e * 2 < wsum else None))
    hi = [i for i, g in enumerate(group) if g == "CAO"]
    lo = [i for i, g in enumerate(group) if g == "THAP"]
    need_maj = nl // 2 + 1                                # đa số của TOÀN BỘ logic (12 -> 7)

    def _pv(idx):
        return vote_result([preds[i] for i in idx]) if idx else None

    hv, lv = _pv(hi), _pv(lo)
    av = vote_result(preds)                               # vote gốc của pool ALL (đa số tất cả logic sau bẻ logic) — lưu để đo WR riêng của chế độ ALL
    mvotes = {"ALL": nl - len(hi) - len(lo), "CAO": len(hi), "THAP": len(lo)}    # "phiếu chọn chế độ" của từng logic: nhóm CAO -> CAO · nhóm THẤP -> THẤP · không thuộc nhóm nào -> ALL
    prev_mode = _af_prev_mode(graded)                     # chế độ của ván trước (ván đầu / ván cũ chưa lưu -> ALL)
    sw_need = max(1, min(int(cfg.AF_SWITCH_NEED), nl))
    demoted = False
    if cfg.AF_SWITCH:                                     # ĐỔI CHẾ ĐỘ DỄ HƠN: chế độ khác đủ sw_need phiếu (mặc định 6/13) là đổi, thay vì phải đa số 7/13
        mode = _af_pick_mode(mvotes, prev_mode, sw_need, bool(cfg.AF_SWITCH_LEAD), bool(cfg.AF_SWITCH_PRIO))
        if mode == "CAO":
            pool, base = hi, hv
        elif mode == "THAP":
            pool, base = lo, lv
        else:
            pool, base = list(range(nl)), vote_result(preds)
        if mode != "ALL" and not pool:                    # đang giữ CAO / THẤP mà nhóm hết logic -> không ai vote, tạm dùng ALL ván này
            demoted = True
            mode, pool, base = "ALL", list(range(nl)), vote_result(preds)
    else:                                                 # cách gốc: nhóm đông hơn thắng · nhóm CAO / THẤP phải >= đa số (7/13) nếu AF_GROUP_NEED_MAJORITY
        if len(hi) > len(lo):
            mode, pool, base = "CAO", hi, hv
        elif len(lo) > len(hi):
            mode, pool, base = "THAP", lo, lv
        else:
            mode, pool = "ALL", list(range(nl))
            base = vote_result(preds)
        if cfg.AF_GROUP_NEED_MAJORITY and mode != "ALL" and len(pool) < need_maj:    # nhóm được chọn ít hơn đa số của pool ALL -> bỏ nhóm, dùng ALL
            demoted = True
            mode, pool = "ALL", list(range(nl))
            base = vote_result(preds)
    tie = False
    if base == "SKIP":                                    # pool hoà phiếu -> đa số tất cả logic (đã bẻ logic); vẫn hoà -> đa số gốc (như cách cũ)
        tie = True
        base = vote_result(preds)
        if base == "SKIP":
            base = all_vote
    mflip, final = False, base
    if cfg.AF_MODE_FLIP and not tie and mw[mode]["flip"]:    # Bước 3: bẻ theo WR RIÊNG của chế độ đang chạy (CAO / THẤP / ALL — chỉ khi AF_MODE_FLIP bật)
        mflip, final = True, flip_pred(base)
    pv = [preds[i] for i in pool]
    vpool = list(range(nl)) if tie else list(pool)         # logic THAM GIA vote ván này (nhóm hoà phiếu -> thực tế dùng pool ALL) — panel hiện "logic đang dự đoán"
    out.update(mode=mode, final=final, base=base, mflip=mflip, tie=tie, demoted=demoted, need_maj=need_maj, pool=vpool, preds=preds, flips=flips,
               prev=prev_mode, mvotes=mvotes, sw_need=sw_need, switched=(mode != prev_mode),
               wins=[float(w) for w in wins], wsum=float(wsum), weights=[float(w) for w in weights],
               eff=[float(e / wsum * 100) for e in effw], group=group, hi=hi, lo=lo,
               hv=hv if hv in (TAI, XIU) else None, lv=lv if lv in (TAI, XIU) else None, av=av if av in (TAI, XIU) else None,
               gT=sum(1 for x in pv if x == TAI), gX=sum(1 for x in pv if x == XIU),
               avg=(float(sum(effw[i] for i in pool) / (len(pool) * wsum) * 100) if pool else None))
    return out


def decide_final(votes, graded, dec_wr=None, cfg=SUN):
    """Chốt final của SUN: AF (nếu bật) -> cách cũ (wr_decision). Trả (final, af). `af` = dict của af_decision khi final do AF chốt, không thì None.
    `dec_wr` truyền sẵn thì không tính lại wr_decision; chỉ tính khi thật sự cần quay về cách cũ (AF tắt)."""
    if cfg.AF_ENABLED:
        af = af_decision(votes, graded, cfg)
        if af["final"] not in (TAI, XIU):                 # hoà tới tận bước cuối (nhóm CAO/THẤP có thể chẵn) -> phá hoà, không để 'SKIP' lọt ra API
            tb = _sun_tiebreak(votes, cfg)
            af["final"] = tb
            if af["base"] not in (TAI, XIU):
                af["base"] = tb
        return af["final"], af
    if dec_wr is None:
        dec_wr = _wr_decision_cfg(votes, graded, cfg)
    fin = dec_wr["final"]
    if fin not in (TAI, XIU):
        fin = _sun_tiebreak(votes, cfg)
    return fin, None


def af_flip_applies(mode, cfg=SUN):
    """Final của ván AF ở chế độ `mode` (CAO | THAP | ALL) có bị bẻ thêm không.
    AF_FLIP_FINAL = bẻ mọi chế độ · AF_FLIP_FINAL_CAO = chỉ CAO · AF_FLIP_FINAL_THAP = chỉ THẤP · AF_FLIP_FINAL_CT = gộp CAO + THẤP (ALL giữ nguyên) · AF_FLIP_FINAL_ALL = chỉ ALL (CAO/THẤP giữ nguyên).
    Phép HOẶC: có ít nhất 1 công tắc áp dụng cho chế độ đó thì bẻ ĐÚNG 1 lần."""
    if cfg.AF_FLIP_FINAL:
        return True
    if mode == "ALL":
        return bool(cfg.AF_FLIP_FINAL_ALL)
    if mode == "CAO":
        return bool(cfg.AF_FLIP_FINAL_CAO or cfg.AF_FLIP_FINAL_CT)
    if mode == "THAP":
        return bool(cfg.AF_FLIP_FINAL_THAP or cfg.AF_FLIP_FINAL_CT)
    return False


def out_final_sun(final, used_af=False, mode=None, cfg=SUN):
    """Final SUN đã đưa ra API. Ván do AF chốt: bẻ theo af_flip_applies(mode) — AF_FLIP_FINAL (mọi chế độ) / AF_FLIP_FINAL_CT (chỉ CAO/THẤP) / AF_FLIP_FINAL_ALL (chỉ ALL)
    (KHÔNG dính FLIP_FINAL chung — AF đã tự bẻ logic + chế độ). Ván quay về cách cũ (AF tắt): bẻ theo FLIP_FINAL như trước."""
    if used_af:
        return flip_pred(final) if af_flip_applies(mode, cfg) else final
    return flip_pred(final) if cfg.FLIP_FINAL else final


def out_final_g(g, cfg=SUN):
    """Final đã đưa ra API của 1 ván đã chấm (entry không có khoá 'af' = ván chốt bằng cách cũ; entry AF có 'mode' = CAO | THAP | ALL)."""
    return out_final_sun(g["final"], g.get("af", False), g.get("mode"), cfg)


def be_final_g(g, cfg=SUN):
    """Ván đã chấm này có bị bẻ final (theo cấu hình HIỆN TẠI: AF_FLIP_FINAL / _CT / _ALL · cách cũ -> FLIP_FINAL) khi đưa ra API không."""
    return af_flip_applies(g.get("mode"), cfg) if g.get("af", False) else bool(cfg.FLIP_FINAL)


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


def merge_graded(saved, fresh):
    """Ghép saved (từ file) + fresh (rebuild từ hist hiện tại), dedup + sort theo session.
    fresh luôn được ưu tiên (overwrite saved nếu trùng session)."""
    by_sess = {g["session"]: g for g in saved}
    for g in fresh:
        by_sess[g["session"]] = g
    return [by_sess[k] for k in sorted(by_sess)]


def rebuild_graded(hist, saved_graded=None, cfg=SUN):
    """Chấm lại lịch sử: dự đoán phiên k+1 từ LỊCH SỬ tới phiên k (13 logic SEQ13v6 cần cả chuỗi chứ không chỉ xúc xắc phiên k), chấm bằng kết quả thật.
    Ván ĐÃ lưu trong saved_graded giữ nguyên, không tính lại -> nhanh và dự đoán đã đưa ra không đổi; chỉ chấm thêm các ván MỚI hơn ván đã lưu (file trống: tối đa SUN_REBUILD_MAX ván gần nhất)."""
    fresh = []
    seed = list(saved_graded) if saved_graded else []
    newest = max((g["session"] for g in seed), default=-1)
    oldest = min((g["session"] for g in seed), default=None)
    backfill = oldest is not None and len(seed) < cfg.PERSIST_KEEP     # file chưa đủ PERSIST_KEEP ván (vd. file cũ chỉ có 50) -> chấm BÙ các ván CŨ hơn ván cũ nhất đã lưu
    for i in range(max(0, len(hist) - 1 - cfg.REBUILD_MAX), len(hist) - 1):
        cur, nxt = hist[i], hist[i + 1]
        if getattr(cfg, "CONSEC_CHECK", True) and nxt["phien"] != cur["phien"] + 1:
            continue
        if not (nxt["phien"] > newest or (backfill and nxt["phien"] < oldest)):    # chỉ ván MỚI hơn ván đã lưu, hoặc (khi chấm bù) ván CŨ hơn ván cũ nhất đã lưu
            continue
        votes = compute_all(hist[:i + 1])
        # Chỉ dùng các ván đã chấm TRƯỚC phiên nxt (seed có thể chứa ván mới hơn -> nhìn trước đáp án, làm lệch đánh giá)
        combined = [g for g in merge_graded(seed, fresh) if g["session"] < nxt["phien"]]
        final, af = decide_final(votes, combined, None, cfg)                          # AF -> cách cũ
        entry = {"session": nxt["phien"], "total": nxt["total"], "actual": nxt["actual"],
                 "votes": votes, "final": final, "ok": final == nxt["actual"],
                 "sig": SUN_SIG}
        if af is not None:                                                # lưu dữ liệu 3 chế độ: vote gốc của nhóm CAO (hv) · nhóm THẤP (lv) · pool ALL (av) của ván này
            entry.update(af=True, mode=af["mode"], mflip=af["mflip"], hv=af["hv"], lv=af["lv"], av=af["av"])
        fresh.append(entry)
    return merge_graded(seed, fresh)


def regrade_graded(graded, cfg=SUN):
    """CHẤM LẠI toàn bộ các ván đã lưu theo CONFIG HIỆN TẠI (ngưỡng AF · vùng bẻ · bẻ final · WR_*...).
    Dùng lại `votes` (13 logic) đã lưu trong từng ván -> KHÔNG chạy lại compute_all nên rất nhanh (vài trăm ms thay vì phải đợi ván mới chạy tới).
    Đi từ ván cũ -> mới: ván k được chốt bằng WR của các ván đã chấm lại TRƯỚC nó (y hệt lúc chạy live, không nhìn trước đáp án).
    Giữ nguyên phiên · tổng · kết quả thật · votes; chỉ tính lại final / ok / af / mode / mflip / hv / lv / av. Ván không có votes thì giữ nguyên."""
    out = []
    for g in graded:
        votes = g.get("votes")
        if not isinstance(votes, list) or not votes or g.get("actual") not in (TAI, XIU):
            out.append(g)
            continue
        final, af = decide_final(votes, out, None, cfg)
        e = {k: v for k, v in g.items() if k not in ("af", "mode", "mflip", "hv", "lv", "av")}
        e.update(final=final, ok=final == g["actual"])
        if af is not None:
            e.update(af=True, mode=af["mode"], mflip=af["mflip"], hv=af["hv"], lv=af["lv"], av=af["av"])
        out.append(e)
    return out


def _regrade_report(before, after, cfg):
    """So sánh trước / sau khi chấm lại: số ván đổi dự đoán + đúng/sai trong EVAL_WINDOW ván gần nhất."""
    changed = sum(1 for a, b in zip(before, after) if out_final_g(a, cfg) != out_final_g(b, cfg))
    ba, aa = _recent_accuracy(before, cfg.EVAL_WINDOW, cfg=cfg), _recent_accuracy(after, cfg.EVAL_WINDOW, cfg=cfg)
    return {"so_van": len(after), "doi_du_doan": changed,
            "truoc": {"dung": ba["dung"], "tong": ba["tong"]}, "sau": {"dung": aa["dung"], "tong": aa["tong"]}}


def build_result(hist, cfg=SUN, persist=None):
    """Từ lịch sử (cũ -> mới) -> dict kết quả dự đoán cho phiên kế tiếp.
    cfg = SUN (mặc định) hoặc TableCfg của 1 bàn HITCLUB · persist = (load, save) nơi lưu các ván đã chấm (None -> file graded của SUN)."""
    latest = hist[-1]
    load, save = persist
    saved = load()
    graded = rebuild_graded(hist, saved_graded=saved, cfg=cfg)
    save(graded)
    votes = compute_all(hist)
    dec = _wr_decision_cfg(votes, graded, cfg)                                   # cách chốt cũ: luôn tính (phương án dự phòng + hiển thị WR cũ)
    final, af = decide_final(votes, graded, dec, cfg)                       # AF -> cách cũ
    used_af = af is not None
    avg = af["avg"] if used_af else dec["avg"]
    mwc = af["mw"].get(af["mode"]) if used_af and cfg.AF_MODE_FLIP and af["mode"] in ("CAO", "THAP", "ALL") else None     # WR RIÊNG của CHẾ ĐỘ đang chạy (CAO / THAP / ALL · AF_MODE_FLIP tắt -> None, panel ẩn dòng này)
    base = {
        "ok": True,
        "phien": latest["phien"] + 1,
        "du_doan": out_final_sun(final, used_af, af["mode"] if used_af else None, cfg),
        "be_final": af_flip_applies(af["mode"], cfg) if used_af else cfg.FLIP_FINAL,   # bẻ ĐANG ÁP DỤNG cho ván này (AF -> theo chế độ: AF_FLIP_FINAL / _CT / _ALL · cách cũ -> FLIP_FINAL)
        "af": used_af,                                                 # True = final ván này do AF chốt (auto-flip + CAO/THẤP + bẻ chế độ)
        "che_do": af["mode"] if used_af else None,                     # CAO | THAP | ALL (chỉ khi AF chốt)
        "be_che_do": af["mflip"] if used_af else False,                # True = ván này đã bẻ theo WR chế độ (WR 7 ván của chế độ đang chạy < 45%)
        "du_doan_goc": final,                                          # final SAU bẻ chế độ, TRƯỚC bẻ final (AF_FLIP_FINAL / _CT / _ALL) — panel dùng để hiện chuỗi gốc -> bẻ
        "du_doan_truoc_be_che_do": af["base"] if used_af else None,    # final TRƯỚC bẻ chế độ (chỉ khi AF chốt)
        "wr_che_do_hien_tai": None if mwc is None else {               # WR 7 ván của chế độ đang chạy (CAO | THAP) -> panel hiện "vì sao bẻ / không bẻ chế độ"
            "che_do": af["mode"], "so_van": mwc["n"], "dung": mwc["w"], "van_toi_thieu": mwc["need"],
            "wr": None if mwc["wr"] is None else round(mwc["wr"], 1),
            "cua_so": cfg.AF_MODE_WINDOW, "nguong_be": cfg.AF_MODE_BELOW, "se_be": mwc["flip"]},
        "do_tin_cay": None if avg is None else round(avg, 1),
        "phien_truoc": latest["phien"],
        "xuc_xac": [latest["d1"], latest["d2"], latest["d3"]],
        "tong": latest["total"],
        "ket_qua_truoc": latest["actual"],
        "so_van_wr": af["n"] if used_af else dec["n"],
        "tool_dung_sai_10_van": _recent_accuracy(graded, cfg.EVAL_WINDOW, with_chuoi=True, cfg=cfg),
    }
    tai = sum(1 for v in votes if v == TAI)
    detail = {
        "vote_21": {"TÀI": tai, "XỈU": len(votes) - tai},        # tên khóa giữ nguyên cho tương thích; giờ đếm trên các logic đang dùng
        "so_logic": len(votes),
        "bo_logic": "SEQ13v6 (chuoi + xuc xac + tong + so phien, khong dung MD5)",
        "nhom_theo": ({"ALL": "AF · da so", "CAO": "AF · WR cao", "THAP": "AF · WR thap"}[af["mode"]] if used_af
                      else {"ALL": "da so", "LOW": "WR thap", "HIGH": "WR cao"}[dec["mode"]]),
        "nhom_tai_xiu": ({"TÀI": af["gT"], "XỈU": af["gX"]} if used_af else {"TÀI": dec["gT"], "XỈU": dec["gX"]}),
        "hoa_dung_da_so_21": dec["tie"],
        "af": {                                                    # AF (auto-flip + CAO/THẤP + bẻ theo WR chế độ) — xem khối CONFIG AF
            "bat": cfg.AF_ENABLED,
            "dang_dung": used_af,                                  # True = final ván này do AF chốt
            "bat_be_che_do": cfg.AF_MODE_FLIP,                         # công tắc bước 3 (bẻ chế độ): False = TẮT (mặc định)
            "che_do": af["mode"] if used_af else None,             # CAO | THAP | ALL
            "be_che_do": af["mflip"] if used_af else False,        # True = đã bẻ theo WR chế độ ở ván này
            "final_truoc_be_che_do": af["base"] if used_af else None,
            "hoa_phieu_nhom": af["tie"] if used_af else False,     # True = nhóm được chọn hoà phiếu -> dùng đa số tất cả logic
            "so_van_wr": af["n"] if used_af else None,
            "van_toi_thieu": max(1, min(cfg.AF_MIN_GAMES, cfg.WR_WINDOW)),
            "nguong_be_logic": {"thap": cfg.AF_FLIP_LOW, "cao": cfg.AF_FLIP_HIGH},
            "gioi_han_vung_be": {                                  # chỉ bẻ logic khi WR nằm TRONG vùng (bat=False -> dùng nguong_be_logic như cũ)
                "bat": cfg.AF_FLIP_BAND,
                "thap": [cfg.AF_FLIP_LOW_MIN, cfg.AF_FLIP_LOW_MAX],
                "cao": [cfg.AF_FLIP_HIGH_MIN, cfg.AF_FLIP_HIGH_MAX]},
            "so_logic_nhom": {"CAO": len(af["hi"]), "THAP": len(af["lo"])} if used_af else None,
            "logic_du_doan": [SUN_NAMES[i] for i in af["pool"]] if used_af else [],      # logic THAM GIA vote ván này 
            "chi_be_vao_nhom": cfg.AF_GROUP_FLIPPED_ONLY,              # True = chỉ logic ĐÃ BỊ BẺ mới vào nhóm CAO / THẤP, logic không bẻ mặc định ALL
            "can_da_so_nhom": cfg.AF_GROUP_NEED_MAJORITY,              # True = nhóm CAO / THẤP phải có >= đa số toàn bộ logic, không thì dùng ALL
            "da_so_toi_thieu": af["need_maj"] if used_af else (len(votes) // 2 + 1),
            "ha_xuong_all": af["demoted"] if used_af else False,   # True = nhóm CAO / THẤP chọn được ít hơn đa số -> đã hạ về ALL ở ván này
            "uu_tien_doi_che_do": cfg.AF_SWITCH_PRIO,                   # True = 2 chế độ còn lại cùng đủ phiếu -> ưu tiên theo chế độ ván trước (ALL->CAO · CAO->ALL · THẤP->CAO)
            "doi_che_do_de": cfg.AF_SWITCH,                            # True = đổi chế độ ALL / CAO / THẤP chỉ cần `phieu_doi_che_do` phiếu (thay vì đa số 7/13)
            "phieu_doi_che_do": af["sw_need"] if used_af else max(1, min(int(cfg.AF_SWITCH_NEED), len(votes))),
            "che_do_truoc": af["prev"] if used_af else None,           # chế độ của ván trước (cơ sở để xét đổi chế độ)
            "phieu_che_do": af["mvotes"] if used_af else None,         # số logic bỏ phiếu cho từng chế độ: ALL (không bẻ) · CAO · THAP
            "da_doi_che_do": af["switched"] if used_af else False,     # True = chế độ ván này khác ván trước
            "logic_bi_be": [SUN_NAMES[i] for i, f in enumerate(af["flips"]) if f] if used_af else [],
            "wr_che_do": {                                         # WR của từng chế độ trên AF_MODE_WINDOW ván gần nhất CỦA CHẾ ĐỘ ĐÓ (vote gốc, chưa bẻ chế độ)
                m: {"so_van": x["n"], "dung": x["w"], "wr": None if x["wr"] is None else round(x["wr"], 1),
                    "be": x["flip"],                               # True = WR < AF_MODE_BELOW -> chế độ này sẽ bị bẻ khi được chọn
                    "chuoi": "".join(ICON_DUNG if ok else ICON_SAI for ok in reversed(x["chuoi"]))}   # mới -> cũ
                for m, x in (af["mw"] if used_af else af_mode_wr(graded, cfg)).items()},
            "cua_so_che_do": cfg.AF_MODE_WINDOW,
            "van_toi_thieu_che_do": max(1, min(cfg.AF_MODE_MIN, cfg.AF_MODE_WINDOW)),
            "nguong_be_che_do": cfg.AF_MODE_BELOW,
            "be_final_af": cfg.AF_FLIP_FINAL,                          # bẻ final của AF ở MỌI chế độ
            "be_final_cao_thap": cfg.AF_FLIP_FINAL_CT,                 # công tắc GỘP: bẻ final cả CAO lẫn THẤP (ALL giữ nguyên)
            "be_final_cao": cfg.AF_FLIP_FINAL_CAO,                     # CHỈ bẻ final khi chế độ CAO (THẤP / ALL giữ nguyên)
            "be_final_thap": cfg.AF_FLIP_FINAL_THAP,                   # CHỈ bẻ final khi chế độ THẤP (CAO / ALL giữ nguyên)
            "be_final_all": cfg.AF_FLIP_FINAL_ALL,                     # CHỈ bẻ final khi chế độ ALL (CAO / THẤP giữ nguyên)
        },
        "trong_so_wr": {                                          # cơ chế WR có trọng số (cách cũ / dự phòng)
            "so_van": dec["n"],
            "trong_so": dec["weights"],                           # cũ nhất -> mới nhất (đã tính flip nếu bật)
            "flip_trong_so": dec["flip"],                         # True = ván CŨ nhất nặng nhất -> giảm dần tới ván MỚI nhất
            "van_moi_nhat": cfg.WR_WEIGHT_NEWEST,                     # trọng số CAO NHẤT (WR_WEIGHT_NEWEST; gán cho ván mới nhất, hoặc ván cũ nhất nếu flip)
            "he_so_giam": cfg.WR_DECAY,                               # WR_DECAY: tốc độ quên ván cũ
            "san_trong_so": cfg.WR_FLOOR,                             # WR_FLOOR: sàn trọng số ván cũ
        },
        "logic": [
            {"ten": SUN_NAMES[i], "du_doan": votes[i],
             "wr": (round(dec["wins"][i] / dec["wsum"] * 100, 1) if dec["wins"] else None),       # WR có trọng số (cách cũ)
             "nhom": (None if not dec["wins"] else ("THAP" if i in dec["low"] else "CAO")),
             "af_be": (af["flips"][i] if used_af else None),                                         # LOW | HIGH | None: logic có bị bẻ ở bước 1 của AF không
             "af_du_doan": (af["preds"][i] if used_af else None),                                    # phiếu SAU khi bẻ logic
             "af_wr": (round(af["eff"][i], 1) if used_af and af["eff"][i] is not None else None),    # WR dùng (100 − WR gốc nếu bị bẻ)
             "af_nhom": (af["group"][i] if used_af else None),                                       # CAO | THAP | None
             "af_vote": ((i in af["pool"]) if used_af else None)}                                    # True = logic THAM GIA vote ván này (nằm trong nhóm / pool được chọn)
            for i in range(len(votes))
        ],
        "final_goc": final,                                       # final trước khi bẻ chung (của AF nếu AF chốt (đã gồm bẻ logic + bẻ chế độ) · không thì của cách cũ)
        "tool_dung_sai_15_van": _recent_accuracy(graded, cfg.WR_WINDOW, cfg=cfg),
    }
    hist_rows = [{"phien": g["session"], "du_doan": out_final_g(g, cfg), "ket_qua": g["actual"], "tong": g.get("total"),
                  "dung": out_final_g(g, cfg) == g["actual"],
                  "af": g.get("af", False), "che_do": g.get("mode"), "be_che_do": g.get("mflip", False),
                  "be_final": be_final_g(g, cfg)} for g in reversed(graded[-HIST_MAX:])]   # mới -> cũ
    return {"base": base, "detail": detail, "hist": hist_rows}


def _recent_accuracy(graded, size, with_chuoi=False, cfg=SUN):
    """Đúng/sai của final ĐÃ ĐƯA RA API (sau bẻ nếu đang bật) ở `size` ván gần nhất."""
    win = graded[-size:]
    oks = [out_final_g(g, cfg) == g["actual"] for g in win]
    out = {"dung": sum(oks), "tong": len(win)}
    if with_chuoi:
        out = {"dung": out["dung"], "sai": len(win) - out["dung"], "tong": len(win),
               "chuoi": "".join(ICON_DUNG if ok else ICON_SAI for ok in reversed(oks))}     # mới -> cũ
    return out


def _now():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _acc_rows(rows, n=10):
    w = rows[:n]
    dung = sum(1 for r in w if r["dung"])
    return {"dung": dung, "sai": len(w) - dung, "tong": len(w),
            "chuoi": "".join(ICON_DUNG if r["dung"] else ICON_SAI for r in w)}      # mới -> cũ


def _hit_rec(sid, d1, d2, d3):
    """1 phiên hợp lệ (xúc xắc 1..6) -> record như hist của SUN; không hợp lệ -> None. Tổng >= 11 = Tài (như file JS)."""
    p = _parse_int(sid)
    ds = [_parse_int(x) for x in (d1, d2, d3)]
    if p is None or None in ds or any(d < 1 or d > 6 for d in ds):
        return None
    tot = sum(ds)
    return {"phien": p, "d1": ds[0], "d2": ds[1], "d3": ds[2], "total": tot, "actual": actual_of(tot), "time": _now()}


def _hit_cmd(g):
    return _parse_int(g.get("cmd")) if isinstance(g, dict) else None


def _lc_parse(tb, data):
    """LC MD5 + LC HŨ (nguồn tele68): {"list":[{id, resultTruyenThong, dices:[a,b,c], point}, ...]} (phiên đầu = mới nhất). Lấy MỌI phiên hợp lệ; HitTable.refresh chỉ lưu thêm phiên CHƯA có."""
    out = {}
    for g in data:
        if not isinstance(g, dict):
            continue
        d = g.get("dices")
        if not isinstance(d, (list, tuple)) or len(d) != 3:
            continue
        r = _hit_rec(g.get("id"), d[0], d[1], d[2])
        if r:
            out[r["phien"]] = r
    return list(out.values())


def _hit_cmd(g):
    return _parse_int(g.get("cmd")) if isinstance(g, dict) else None


class LcTable:
    """1 bàn LC (LC MD5 / LC HŨ): quét API nền, tích lũy lịch sử, tính dự đoán bằng config RIÊNG (self.cfg), lưu data vào file RIÊNG (self.path)."""

    def __init__(self, key, label, cfg, path, parser, url):
        self.key, self.label, self.cfg, self.path, self.parse = key, label, cfg, path, parser
        self.url = url
        self.rlock = threading.RLock()                 # tuần tự hoá refresh()
        self.slock = threading.Lock()                  # bảo vệ self.state (giữ ngắn)
        self.state = {"result": None, "latest": None, "error": None, "updated": None, "checked": None, "polls": 0}
        self.hist = {}                                 # phien -> record xúc xắc
        self.graded = []                               # các ván đã chấm (cũ -> mới)
        self.loaded = False
        self.pending_sid = None                        # TX THƯỜNG: sid mới nhất từ cmd 1008
        self.last_sid = None
        self.started = False
        self.dbg = {}                                  # tóm tắt payload quét gần nhất (để /health chẩn đoán)

    game = "lc79"               # giá trị trường "game" trong JSON
    kgame = "lc79"              # game của KEY được phép dùng bàn này (key LC79 dùng được cả 2 bàn)
    pending = None              # dự đoán đang chờ kết quả: {"phien": n, "du_doan": "TÀI"|"XỈU"}

    def _fetch_items(self):
        h = {"User-Agent": HIT_UA, "Accept": "application/json", "Cache-Control": "no-cache"}
        if LC_REFERER:
            h["Referer"] = LC_REFERER
            h["Origin"] = LC_REFERER.rstrip("/")
        req = urllib.request.Request(self.url, headers=h)
        with urllib.request.urlopen(req, timeout=UPSTREAM_TIMEOUT) as r:
            data = json.loads(r.read().decode("utf-8"))
        lst = data.get("list") if isinstance(data, dict) else data
        if not isinstance(lst, list):
            raise ValueError(f"API LC ({self.key}) tra ve khong hop le (thieu 'list') - kiem tra token at= trong URL nguon cua ban nay")
        return lst

    @property
    def active(self):
        return bool(LC_ENABLED and self.cfg.ENABLED)

    # ── file data riêng của bàn ──
    def _load(self):
        if self.loaded:
            return
        self.loaded = True
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                d = json.load(f)
        except Exception:  # noqa: BLE001
            return
        if not isinstance(d, dict):
            return
        for r in d.get("hist") or []:
            if isinstance(r, dict) and all(k in r for k in ("phien", "d1", "d2", "d3", "total", "actual")):
                self.hist[r["phien"]] = r
        for k in sorted(self.hist)[:-self.cfg.HIST_KEEP]:
            del self.hist[k]
        self.graded = [g for g in (d.get("graded") or []) if isinstance(g, dict) and g.get("sig") == SUN_SIG]   # bỏ ván của bộ logic khác
        if self.hist:
            self.last_sid = max(self.hist)
        pd = d.get("pending")
        if isinstance(pd, dict) and isinstance(pd.get("phien"), int):
            self.pending = pd

    def _write(self):
        try:
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"ban": self.key, "gid": self.cfg.GID, "luu_luc": _now(),
                           "pending": self.pending,
                           "hist": [self.hist[k] for k in sorted(self.hist)],
                           "graded": self.graded[-self.cfg.PERSIST_KEEP:]}, f, ensure_ascii=False)
            os.replace(tmp, self.path)
        except Exception:  # noqa: BLE001
            pass

    def _graded_load(self):
        return list(self.graded)

    def _graded_save(self, graded):
        self.graded = list(graded[-self.cfg.PERSIST_KEEP:])      # ghi file 1 lần sau build_result (_write), không ghi ở đây

    # ── quét API + tính lại khi có phiên mới ──
    def refresh(self):
        with self.rlock:
            self._load()
            items = self._fetch_items()
            cmds = {}
            for g in items:
                c = _hit_cmd(g)
                if c is not None:
                    cmds[c] = cmds.get(c, 0) + 1
            self.dbg = {"so_muc": len(items), "cmd": cmds, "pending_sid": self.pending_sid}
            recs = self.parse(self, items)
            new = [r for r in recs if r["phien"] not in self.hist]
            for r in new:
                self.hist[r["phien"]] = r
            for k in sorted(self.hist)[:-self.cfg.HIST_KEEP]:
                del self.hist[k]
            if not self.hist:                           # API trả hợp lệ nhưng chưa có kết quả phiên nào
                with self.slock:
                    self.state.update(error=None, checked=_now())
                return
            hist = [self.hist[k] for k in sorted(self.hist)]
            latest = hist[-1]["phien"]
            with self.slock:
                same = self.state["result"] is not None and self.state["latest"] == latest
            if same:
                if new:                                 # chỉ lấp phiên cũ còn thiếu -> lưu lại, không tính lại
                    self._write()
                with self.slock:
                    self.state.update(error=None, checked=_now())
                return
            res = build_result(hist, self.cfg, (self._graded_load, self._graded_save))
            self.pending = {"phien": res["base"]["phien"], "du_doan": res["base"]["du_doan"]}   # dự đoán phiên kế tiếp, giữ tới khi API trả kết quả phiên đó
            self._write()                               # 1 lần ghi: lịch sử xúc xắc + ván đã chấm + dự đoán đang chờ
            with self.slock:
                self.state.update(result=res, latest=latest, error=None, updated=_now(), checked=_now())

    def wipe(self):
        """XÓA SẠCH data của bàn này (lịch sử xúc xắc + ván đã chấm + dự đoán chờ) rồi ghi file rỗng. Poller quét lại API và tích lũy lại từ đầu."""
        with self.rlock:
            self._load()
            n = len(self.hist)
            self.hist.clear()
            self.graded = []
            self.pending = None
            self.last_sid = None
            self._write()
            hist_unhide(self.key)
            with self.slock:
                self.state.update(result=None, latest=None)
            return {"phien_da_xoa": n}

    def regrade(self):
        """Nút \"Tính lại theo config\": chấm lại các ván đã lưu của bàn này bằng config HIỆN TẠI (giữ nguyên lịch sử xúc xắc + ván đã chấm)."""
        with self.rlock:
            self._load()
            if not self.graded:
                return {"so_van": 0, "doi_du_doan": 0, "truoc": {"dung": 0, "tong": 0}, "sau": {"dung": 0, "tong": 0}}
            before = list(self.graded)
            self.graded = regrade_graded(before, self.cfg)[-self.cfg.PERSIST_KEEP:]
            rep = _regrade_report(before, self.graded, self.cfg)
            hist = [self.hist[k] for k in sorted(self.hist)]
            if hist:
                res = build_result(hist, self.cfg, (self._graded_load, self._graded_save))
                self.pending = {"phien": res["base"]["phien"], "du_doan": res["base"]["du_doan"]}
                with self.slock:
                    self.state.update(result=res, latest=hist[-1]["phien"], updated=_now())
            self._write()
            return rep

    def _loop(self):
        while True:
            try:
                self.refresh()
            except Exception as e:  # noqa: BLE001 - giữ poller sống dù API lỗi
                with self.slock:
                    self.state["error"] = f"{type(e).__name__}: {e}"
                    self.state["checked"] = _now()
            with self.slock:
                self.state["polls"] += 1
            time.sleep(self.cfg.POLL_SEC)

    def start(self):
        with self.slock:
            if self.started or not self.active:
                return
            self.started = True
        threading.Thread(target=self._loop, daemon=True, name=f"hit-{self.key}").start()

    def health(self):
        with self.slock:
            st = {k: self.state[k] for k in ("latest", "error", "updated", "checked", "polls")}
        c = self.cfg
        st.update(ok=st["error"] is None and st["latest"] is not None, bat=self.active, ten=self.label, gid=c.GID, file=self.path,
                  so_phien_luu=len(self.hist), so_van_cham=len(self.graded), poll_sec=c.POLL_SEC, hist_keep=c.HIST_KEEP,
                  an_den_phien=hist_hidden_upto(self.key), payload_cuoi=self.dbg, du_doan_cho_ket_qua=self.pending, config=c.as_dict())
        return st





LC_TABLES = {
    "lcmd5": LcTable("lcmd5", "LC MD5", LC_MD5_CFG, LC_MD5_PATH, _lc_parse, LC_MD5_API_URL),
    "lchu": LcTable("lchu", "LC Hũ", LC_HU_CFG, LC_HU_PATH, _lc_parse, LC_HU_API_URL),
}


_poller_started = False


def ensure_poller():
    """Bật poller của 2 bàn LC (mỗi bàn 1 luồng riêng, chỉ bật 1 lần)."""
    global _poller_started
    if _poller_started:
        return
    _poller_started = True
    for tb in LC_TABLES.values():
        tb.start()


# ─── XÓA LỊCH SỬ DỰ ĐOÁN (chỉ ẩn phần hiển thị — xem khối CONFIG XÓA LỊCH SỬ) ───
_hc_lock = threading.Lock()
_hc = {"loaded": False, "d": {"lcmd5": {"den": 0, "luc": None}, "lchu": {"den": 0, "luc": None}}}


def _hc_load_locked():
    """Nạp mốc đã lưu (1 lần). Gọi trong _hc_lock."""
    if _hc["loaded"]:
        return
    _hc["loaded"] = True
    try:
        with open(HIST_CLEAR_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        for g in list(_hc["d"]):
            r = data.get(g) if isinstance(data, dict) else None
            if r is None and g == "lcmd5" and isinstance(data, dict):
                r = data.get("tele68txmd5")                      # mốc cũ của bàn Tele68 MD5 (đã đổi tên thành LC MD5)
            if isinstance(r, dict) and isinstance(r.get("den"), int) and r["den"] > 0:
                _hc["d"][g] = {"den": r["den"], "luc": r.get("luc")}
    except Exception:  # noqa: BLE001
        pass


def hist_hidden_upto(game):
    """Mốc phiên: ván có phiên <= mốc bị ẩn khỏi lịch sử hiển thị (0 = chưa xóa lần nào)."""
    with _hc_lock:
        _hc_load_locked()
        return _hc["d"][game]["den"]


def hist_clear(game, upto):
    """Đặt mốc xóa lịch sử của `game` = `upto` (chỉ tiến, không lùi). Chỉ ghi file mốc riêng — KHÔNG đụng dữ liệu nào khác. Trả mốc mới."""
    with _hc_lock:
        _hc_load_locked()
        cur = _hc["d"][game]
        if upto > cur["den"]:
            cur["den"] = int(upto)
            cur["luc"] = _now()
        try:
            tmp = HIST_CLEAR_PATH + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(_hc["d"], f, ensure_ascii=False)
            os.replace(tmp, HIST_CLEAR_PATH)
        except Exception:  # noqa: BLE001
            pass
        return cur["den"]


def hist_unhide(game):
    """Đặt lại mốc \"Xóa lịch sử\" của `game` về 0 (dùng khi XÓA SẠCH data của game để đếm lại từ đầu)."""
    with _hc_lock:
        _hc_load_locked()
        _hc["d"][game] = {"den": 0, "luc": None}
        try:
            tmp = HIST_CLEAR_PATH + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(_hc["d"], f, ensure_ascii=False)
            os.replace(tmp, HIST_CLEAR_PATH)
        except Exception:  # noqa: BLE001
            pass


# ─── THEO DÕI IP ────────────────────────────────────────────────────────
_ip_lock = threading.Lock()
_ip_store = {}              # ip -> {"ip","first","last","hits","by":{loại: số request},"ua"}
_ip_state = {"loaded": False, "saved": 0.0, "dirty": False}


def ip_kind(path):
    """Loại request được tính vào danh sách IP (None = không tính: /health, /, /api/ips ...)."""
    if path in ("/api/predictlcmd5", "/api/predictlchu", "/api/predicttele68txmd5"):
        return "lc"
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
    """Danh sách IP cho /api/ips: đang dùng trước, rồi tới các IP đã từng dùng. Trong mỗi nhóm sắp theo LẦN ĐẦU XUẤT HIỆN (mới xuất hiện nằm trên) — thứ tự này không đổi theo
    mỗi request nên danh sách trên panel KHÔNG bị xáo / nhảy hàng mỗi lần tool gọi API (trước đây sắp theo \"request gần nhất\" nên hàng nhảy liên tục)."""
    now = time.time()
    with _ip_lock:
        _ip_load_locked()
        rows = [dict(r, by=dict(r["by"])) for r in _ip_store.values()]
    rows.sort(key=lambda r: (-r["first"], r["ip"]))
    out = []
    for r in rows:
        age = max(0.0, now - r["last"])
        out.append({"ip": r["ip"], "dang_dung": age <= IP_ACTIVE_SEC, "lan_dau": _fmt_ts(r["first"]), "gan_nhat": _fmt_ts(r["last"]),
                    "truoc_giay": int(age), "so_request": r["hits"], "theo_loai": r["by"], "ua": r.get("ua", ""), "la_ban": r["ip"] == me})
    out.sort(key=lambda x: not x["dang_dung"])           # sort ổn định -> chỉ tách nhóm đang dùng / đã dùng, giữ nguyên thứ tự lần đầu xuất hiện
    return {"ok": True, "tong": len(out), "dang_dung": sum(1 for x in out if x["dang_dung"]),
            "cua_so_giay": IP_ACTIVE_SEC, "ban": me, "ips": out}


def ip_health():
    with _ip_lock:
        _ip_load_locked()
        n = len(_ip_store)
    return dict(bat=IP_TRACK_ENABLED, tong=n, active_sec=IP_ACTIVE_SEC, khoa=bool(IP_ADMIN_KEY), tin_proxy=IP_TRUST_PROXY)


# ─── FLASK ────────────────────────────────────────────────────────────────
from flask import Flask, Response, abort, redirect, request  # noqa: E402
from flask import g as flask_g  # noqa: E402  (đặt tên khác vì nhiều hàm dùng biến cục bộ `g`)

os.umask(0o077)                                    # file dữ liệu (key / thiết bị / phiên) chỉ chủ tiến trình đọc được
app = Flask(__name__, static_folder=None)           # KHÔNG mở route /static -> không ai kéo file qua đường tĩnh
app.config.update(PROPAGATE_EXCEPTIONS=False, MAX_CONTENT_LENGTH=256 * 1024)   # lỗi không bay ra ngoài · body tối đa 256 KB


def _json(obj, status=200):
    return Response(json.dumps(obj, ensure_ascii=False), status=status,
                    content_type="application/json; charset=utf-8")


import collections as _collections  # noqa: E402
from werkzeug.exceptions import HTTPException as _HTTPExc, NotFound as _NotFound  # noqa: E402
HTTPException_ = _HTTPExc

# ═══════════════════════════════════════════════════════════════════════════
#  🛡  LỚP BẢO MẬT (SEC)  —  env chỉnh được
# ═══════════════════════════════════════════════════════════════════════════
#   SUNVIW_PROXY_HOPS   số proxy tin cậy đứng TRƯỚC app (mặc định 1 = Railway). IP thật = phần tử thứ N TÍNH TỪ CUỐI của X-Forwarded-For
#                       (phần đầu do CLIENT tự điền nên KHÔNG tin được). Nếu thêm Cloudflare trước Railway -> đặt 2.
#   SUNVIW_IP_HEADER    (tuỳ chọn) header IP do proxy ĐÁNG TIN ghi đè, vd CF-Connecting-IP — có đặt thì dùng nó thay cho X-Forwarded-For.
#   SUNVIW_IP_PROXY=0   KHÔNG đứng sau proxy (chạy trực tiếp ra internet) -> chỉ dùng remote_addr.
#   SUNVIW_RATE_TOOL    request / phút / KEY cho endpoint dự đoán (mặc định 90) · SUNVIW_RATE_IP / phút / IP (300) · SUNVIW_RATE_BADKEY key sai / phút / IP (20) · SUNVIW_RATE_PANEL / phút / thiết bị panel (900)
#   SUNVIW_TOOL_HIST_MAX  ?hist=N tối đa cho tool khách (mặc định 60); panel / admin vẫn dùng HIST_MAX.
#   SUNVIW_DEV_TOKEN_STRICT=1  thiết bị panel ĐÃ DUYỆT từ trước bản vá mà chưa có token thì KHÔNG còn được vào (phải gỡ + duyệt lại). Mặc định 0 = tự gắn token ở lần mở panel đầu tiên.
IP_PROXY_HOPS = max(1, _env_num("SUNVIW_PROXY_HOPS", 1, int))
RATE_TOOL_KEY = _env_num("SUNVIW_RATE_TOOL", 90, int)
RATE_IP = _env_num("SUNVIW_RATE_IP", 300, int)
RATE_BADKEY = _env_num("SUNVIW_RATE_BADKEY", 20, int)
RATE_PANEL = _env_num("SUNVIW_RATE_PANEL", 900, int)
TOOL_HIST_MAX = _env_num("SUNVIW_TOOL_HIST_MAX", 60, int)
DEV_TOKEN_STRICT = _env_bool("SUNVIW_DEV_TOKEN_STRICT", True)
DEV_COOKIE = "sv_dt"                                  # cookie HttpOnly chứa token thiết bị do SERVER cấp (JS không đọc được)

_rate_hits = {}
_rate_lock = threading.Lock()


def _rate_ok(bucket, limit, window=60.0):
    """Cửa sổ trượt: True nếu `bucket` còn dưới `limit` lần trong `window` giây (và ghi nhận 1 lần). limit <= 0 = không giới hạn."""
    if limit <= 0:
        return True
    now = time.time()
    with _rate_lock:
        if len(_rate_hits) > 20000:
            cut_t = now - 300
            for b in [b for b, dq in _rate_hits.items() if not dq or dq[-1] < cut_t]:
                del _rate_hits[b]
            if len(_rate_hits) > 20000:
                _rate_hits.clear()
        dq = _rate_hits.get(bucket)
        if dq is None:
            dq = _rate_hits[bucket] = _collections.deque()
        lim = now - window
        while dq and dq[0] <= lim:
            dq.popleft()
        if len(dq) >= limit:
            return False
        dq.append(now)
        return True


def _too_many(msg="qua nhieu request, thu lai sau it giay", sec=20):
    r = _json({"ok": False, "rate_limited": True, "loi": msg}, 429)
    r.headers["Retry-After"] = str(sec)
    return r


def _err500(e, where=""):
    """Lỗi nội bộ: chi tiết chỉ ghi log server, KHÔNG trả ra ngoài (tên lỗi / đường dẫn / URL upstream đều không lộ)."""
    try:
        import traceback
        print(f"[ERR] {where} {type(e).__name__}: {e}", file=sys.stderr)
        traceback.print_exc()
    except Exception:  # noqa: BLE001
        pass
    return _json({"ok": False, "loi": "loi may chu"}, 500)


def _is_panel():
    """Request này đến từ panel đã duyệt / admin chính (được xem chi tiết) — cờ do _gate_key đặt."""
    return bool(getattr(flask_g, "panel", False))


def _pub_err(err, dflt):
    """Chuỗi lỗi chỉ cho panel/admin xem; tool khách chỉ nhận câu chung (lỗi gốc có thể chứa URL upstream / tên exception)."""
    return (err or dflt) if _is_panel() else dflt


_CORS_EXACT = {"/", "/health", "/api/key/check", "/api/predictlcmd5", "/api/predictlchu", "/api/predicttele68txmd5", "/api/notice"}
_NOFRAME_PREFIX = ("/api/admin",)


def _is_https():
    return request.is_secure or request.headers.get("X-Forwarded-Proto", "").split(",")[-1].strip().lower() == "https"


@app.after_request
def _cors(resp):
    p = request.path
    if p in _CORS_EXACT:                                # CORS CHỈ cho endpoint dự đoán / key-check (xác thực bằng header key, không bằng cookie). Admin / panel / history / ips: KHÔNG mở CORS
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        resp.headers["Access-Control-Allow-Headers"] = request.headers.get("Access-Control-Request-Headers") or "Content-Type, X-User-Key, X-HWID, X-HWID-ALT, X-HWID-FRESH"
        resp.headers["Access-Control-Max-Age"] = "600"
    resp.headers["Cache-Control"] = "no-store"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Referrer-Policy"] = "no-referrer"
    resp.headers["X-Robots-Tag"] = "noindex, nofollow"
    resp.headers["Server"] = "web"                      # không lộ Werkzeug / gunicorn / phiên bản Python
    if "Content-Security-Policy" not in resp.headers:
        resp.headers["Content-Security-Policy"] = "frame-ancestors 'none'; base-uri 'none'; object-src 'none'; form-action 'self'"
    resp.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    resp.headers["Cross-Origin-Resource-Policy"] = "same-origin" if p not in _CORS_EXACT else "cross-origin"
    resp.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
    if _is_https():
        resp.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    if p.startswith(_NOFRAME_PREFIX):
        resp.headers["X-Frame-Options"] = "DENY"        # chống clickjacking trang admin / auto cược
    return resp


def _ip_parse(v):
    v = (v or "").split(",")[0].strip()
    if v.startswith("["):
        v = v[1:].split("]")[0]
    elif v.count(":") == 1:                             # IPv4:port
        v = v.split(":")[0]
    if not v:
        return None
    try:
        return str(ipaddress.ip_address(v))
    except ValueError:
        return None


def client_ip():
    """IP của client. Sau proxy: lấy phần tử thứ IP_PROXY_HOPS TÍNH TỪ CUỐI của X-Forwarded-For (proxy tin cậy là bên THÊM vào cuối; phần đầu client tự điền được -> không tin).
    SUNVIW_IP_HEADER đặt thì dùng header đó (proxy phải ghi đè). Không hợp lệ -> IP kết nối trực tiếp (remote_addr)."""
    if IP_TRUST_PROXY:
        if IP_HEADER:
            v = _ip_parse(request.headers.get(IP_HEADER, ""))
            if v:
                return v
        else:
            parts = [x.strip() for x in request.headers.get("X-Forwarded-For", "").split(",") if x.strip()]
            if len(parts) >= IP_PROXY_HOPS:
                v = _ip_parse(parts[-IP_PROXY_HOPS])
                if v:
                    return v
    return _ip_parse(request.remote_addr or "") or "unknown"


# ─ chặn máy quét: dò .env / .git / *.py / wp-admin... hoặc dồn dập 404 -> tạm khoá IP (trả 404 như web không tồn tại) ─
PG_LIMIT, PG_WINDOW, PG_BLOCK = 10, 600.0, 900.0        # >= 10 điểm trong 10 phút -> khoá 15 phút
_pg = {}
_pg_lock = threading.Lock()
_PROBE_RE = re.compile(r"(?i)(\.env|\.git|\.svn|\.htaccess|\.ds_store|\.py($|[/?;])|\.pyc|\.bak|\.old|\.swp|\.sql|\.zip|\.tar|\.gz|\.log($|[/?;])|wp-(admin|login|content|includes)|phpmyadmin"
                       r"|/console|/actuator|/server-status|/__debug__|/debug|/static/|/proc/|/etc/passwd|\.\./|%2e%2e|%252e|\\x00|%00)")


def _pg_strike(ip, pts):
    if not ip or ip == "unknown":
        return
    now = time.time()
    with _pg_lock:
        if len(_pg) > 5000:
            for k in [k for k, v in _pg.items() if v[2] < now and now - v[1] > PG_WINDOW]:
                del _pg[k]
        r = _pg.get(ip)
        if r is None or (r[2] < now and now - r[1] > PG_WINDOW):
            r = _pg[ip] = [0, now, 0.0]
        r[0] += pts
        if r[0] >= PG_LIMIT and r[2] < now:
            r[2] = now + PG_BLOCK
            print(f"[SEC] khoa IP {ip} {PG_BLOCK:.0f}s (quet duong dan / loi lien tuc)", file=sys.stderr)


def _pg_blocked(ip):
    with _pg_lock:
        r = _pg.get(ip)
        return bool(r and r[2] > time.time())


@app.before_request
def _probe_guard():
    ip = client_ip()
    if _pg_blocked(ip):
        abort(404)
    if _PROBE_RE.search(request.path) or _PROBE_RE.search(request.query_string.decode("latin-1", "ignore")[:300]):
        _pg_strike(ip, 4)
        abort(404)
    return None


@app.before_request
def _csrf_origin():
    """POST / PUT / DELETE có Origin khác host (trang web lạ gọi chéo) -> 403, trừ các endpoint công khai dùng key (có CORS)."""
    if request.method in ("POST", "PUT", "PATCH", "DELETE") and request.path not in _CORS_EXACT:
        o = request.headers.get("Origin", "")
        if o and o != "null":
            from urllib.parse import urlsplit
            if urlsplit(o).netloc.lower() != request.host.lower():
                _audit("csrf_block", origin=o[:80])
                return _json({"ok": False, "loi": "forbidden"}, 403)
        elif o == "null":
            return _json({"ok": False, "loi": "forbidden"}, 403)
    return None


@app.errorhandler(Exception)
def _on_exception(e):
    if isinstance(e, _HTTPExc):
        if e.code == 405:
            e = _NotFound()                              # sai method cũng 404: không lộ đường nào có thật
        if e.code == 404 and True:     # 2 đường này trả 404 có chủ ý cho thiết bị bị ban -> không tính là dò quét
            _pg_strike(client_ip(), 1)
        if e.code == 413:
            return _json({"ok": False, "loi": "payload qua lon"}, 413)
        return e
    return _err500(e, request.path)


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


# ─── KEY NGƯỜI DÙNG + ADMIN ──────────────────────────────────────────────
ADMIN_MAIN_NAME = "admin chính"
_ADMIN_SALT = b"sunviw-admin-v1:93eacb1bcbb59252"
ADMIN_PASS_HASH_DEFAULT = ""                          # SEC2: đã GỠ hash mặc định khỏi code (lộ file code không còn dò được mật khẩu offline). Đặt SUNVIW_MAIN_PASS ở Railway
KEYS_PATH = os.environ.get("SUNVIW_KEYS_PATH", _data_path("sunviw_keys.json"))
KEY_GATE_API = _env_bool("SUNVIW_GATE_API", True)
KEY_START_ON_ACTIVATE = _env_bool("SUNVIW_KEY_START_ON_ACTIVATE", True)   # True (mặc định) = key mới tạo CHƯA tính hạn; hạn chỉ bắt đầu chạy từ lần dùng THÀNH CÔNG đầu tiên (kích hoạt). False = như cũ (tính từ lúc tạo)
KEY_DAYS = (1, 3, 7, 30, 60, 90)                     # hạn key cho phép khi TẠO (ngày) = 1 ngày · 3 ngày · 1 tuần · 1 tháng · 2 tháng · 3 tháng. Key cũ có hạn khác (2/14/180/365 ngày) vẫn dùng + hiển thị bình thường
# 💰 GIÁ BÁN KEY (VNĐ) theo số ngày của gói — dùng để TỰ TÍNH DOANH THU khi key được KÍCH HOẠT (áp dụng cho cả key Sun · Hit · LC79).
#    Gói không có trong bảng (60 / 90 ngày, hoặc key cũ 2 / 14 / 180 / 365 ngày) = chưa có giá -> không tính vào doanh thu (chỉ đếm riêng ở "chưa có giá"). Muốn tính thêm gói nào thì thêm vào đây.
#    Giá được CHỐT vào sổ doanh thu ngay lúc kích hoạt -> sau này đổi bảng giá không làm đổi doanh thu cũ. Doanh thu chỉ ADMIN CHÍNH xem được (GET /api/admin/revenue + khối "Doanh thu" ở /api/admin).
KEY_PRICE = {1: 10000, 3: 25000, 7: 75000, 30: 250000}
REV_KEEP_SEC = 400 * 86400                            # sổ doanh thu giữ tối đa bấy lâu (đủ cho doanh thu hôm nay / tuần này / 30 ngày)
VN_UTC_OFFSET = 7 * 3600                              # giờ Việt Nam (UTC+7): mốc 00:00 để RESET doanh thu NGÀY / TUẦN (Railway chạy giờ UTC nên KHÔNG dùng giờ máy chủ)
KEY_MAX_TOTAL = 5000                                  # trần số key lưu trong file
ADMIN_SESSION_SEC = 12 * 3600                         # phiên đăng nhập admin sống bao lâu
LOGIN_MAX_FAIL = 8                                    # sai quá N lần trong LOGIN_LOCK_SEC -> khóa IP đó LOGIN_LOCK_SEC giây
LOGIN_LOCK_SEC = 900
KEY_DEV_OPTIONS = (1, 2, 3, 5, 10, 20, 50)            # số thiết bị tối đa chọn được khi tạo key (1 key dùng được trên N thiết bị)
KEY_DEV_DEFAULT = 1                                   # mặc định (cũng là số thiết bị của key cũ tạo trước bản này)
KEY_GAMES = ("sun", "hit", "lc79", "autolc")                            # game NHẬN DIỆN trong file key (key game khác vẫn nằm trong file nhưng KHÔNG dùng được LC — không biến thành key "mọi game")
KEY_CREATE_GAMES = ("lc79",)                                            # game cho phép TẠO key ở server này
_KEY_DEAD_GAMES = ("gb68",)                          # game ĐÃ GỠ: key cũ của game này vẫn nằm trong file nhưng KHÔNG dùng được game nào (không biến thành key "mọi game")
KEY_GAME_LABEL = {"sun": "Sun", "hit": "Hit", "lc79": "LC79", "gb68": "68GB (đã gỡ)", "autolc": "Auto cược LC"}
KEY_PREFIX = {"sun": "SUN", "hit": "HIT", "lc79": "LC79", "autolc": "AUTOLC"}             # tiền tố key để nhìn là biết game: SUN-XXXX-... / HIT-XXXX-...
_lg = os.environ.get("SUNVIW_KEY_LEGACY_GAME", "all").strip().lower()
_lg = "lc79" if _lg == "tele68" else _lg
KEY_LEGACY_GAME = _lg if _lg in ("all", "sun", "hit", "lc79") else "all"   # game của key cũ chưa có trường game (xem khối CONFIG KEY / ADMIN)
HWID_REQUIRED = _env_bool("SUNVIW_HWID_REQUIRED", True)
HWID_TOUCH_SEC = 60                                   # ghi "lần dùng gần nhất" tối đa 1 lần / phút / thiết bị (đỡ ghi file mỗi lần panel poll)


def _pw_hash(pw):
    return hashlib.pbkdf2_hmac("sha256", str(pw).encode("utf-8"), _ADMIN_SALT, 200000).hex()


_ENV_MAIN_PASS = os.environ.get("SUNVIW_MAIN_PASS", "")
# SUNVIW_ALLOW_DEFAULT_PASS=0 (KHUYẾN NGHỊ sau khi đã đặt SUNVIW_MAIN_PASS): bỏ hẳn hash mặc định nằm trong code -> lộ file code cũng không dò được mật khẩu admin offline
ALLOW_DEFAULT_PASS = False
_TEMP_PASS = ""
if not _ENV_MAIN_PASS:                                # chưa đặt SUNVIW_MAIN_PASS -> mật khẩu TẠM ngẫu nhiên (chỉ sống tới lần restart, chỉ hiện trong log server riêng của bạn)
    _TEMP_PASS = secrets.token_urlsafe(18)
    print("[SEC] !!! SUNVIW_MAIN_PASS CHUA DAT. Mat khau admin TAM (het hieu luc khi restart): " + _TEMP_PASS + "  -> dat SUNVIW_MAIN_PASS (>= 16 ky tu) o Railway Variables", file=sys.stderr)
ADMIN_PASS_HASH = _pw_hash(_ENV_MAIN_PASS or _TEMP_PASS)
_MEM_SECRET = secrets.token_hex(32)


def _admin_slug():
    """Đường dẫn BÍ MẬT của trang + API admin. Đặt SUNVIW_ADMIN_PATH (>= 8 ký tự a-z A-Z 0-9 _ -); không đặt thì suy ra cố định từ SUNVIW_SECRET / mật khẩu admin chính (HMAC, không đảo ngược được)."""
    v = re.sub(r"[^A-Za-z0-9_-]", "", os.environ.get("SUNVIW_ADMIN_PATH", "")).strip("-_")
    if len(v) >= 8:
        return v[:64]
    key = (os.environ.get("SUNVIW_SECRET") or _ENV_MAIN_PASS or _TEMP_PASS).encode("utf-8")
    return "c" + hmac.new(key, b"sunviw-admin-path", hashlib.sha256).hexdigest()[:23]


ADMIN_SLUG = _admin_slug()
print(f"[SEC] Trang admin CHI mo o /{ADMIN_SLUG}  (duong /api/admin cu va moi /api/admin/* tu ngoai deu tra 404) - hay luu lai, dat SUNVIW_ADMIN_PATH de tu chon", file=sys.stderr)


class _AdminMask:
    """Lớp WSGI ngoài cùng: /<ADMIN_SLUG>/... được ánh xạ nội bộ thành /api/admin/... (code bên trong + chữ ký HMAC vẫn dùng đường dẫn gốc);
    còn /api/admin* gọi trực tiếp từ bên ngoài -> 404 như đường không tồn tại (người dùng thường không dò ra được admin)."""

    def __init__(self, inner):
        self.inner = inner
        self.pfx = "/" + ADMIN_SLUG

    def __call__(self, environ, start_response):
        p = environ.get("PATH_INFO", "")
        if p == self.pfx or p.startswith(self.pfx + "/"):
            q = "/api/admin" + p[len(self.pfx):]
            environ["PATH_INFO"] = q.rstrip("/") if q.startswith("/api/admin/") and q.count("/") == 3 else q
        elif p.lower().startswith("/api/admin"):
            environ["PATH_INFO"] = "/__nf__"
        return self.inner(environ, start_response)


app.wsgi_app = _AdminMask(app.wsgi_app)
_kv_lock = threading.RLock()
_KEY_ALPHA = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"        # bỏ 0/O/1/I cho dễ đọc


def _kv_load():
    for pth in (KEYS_PATH, KEYS_PATH + ".bak"):       # file chính hỏng / mất -> đọc bản sao .bak (tránh lần lưu sau ghi đè mất sạch key)
        try:
            with open(pth, "r", encoding="utf-8") as f:
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
    try:
        if os.path.exists(KEYS_PATH) and os.path.getsize(KEYS_PATH) > 2:
            shutil.copyfile(KEYS_PATH, KEYS_PATH + ".bak")   # giữ bản trước đó
    except OSError:
        pass
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


def _activated(rec):
    """Key đã kích hoạt (đã bắt đầu tính hạn) chưa. Key tạo TRƯỚC bản này (không có trường "act") = coi như đã kích hoạt từ lúc tạo -> hạn cũ giữ nguyên."""
    return "act" not in rec or bool(rec.get("act"))


def _is_expired(rec, now):
    """Hết hạn chưa. Key chưa kích hoạt thì KHÔNG BAO GIỜ hết hạn (hạn chưa chạy)."""
    return _activated(rec) and int(rec.get("exp") or 0) <= now


ADD_UNITS = {"hour": 3600, "day": 86400, "week": 7 * 86400, "month": 30 * 86400, "gio": 3600, "ngay": 86400, "tuan": 7 * 86400, "thang": 30 * 86400}   # đơn vị cộng thời gian (tháng = 30 ngày)
ADD_MAX_SEC = 365 * 86400                             # tối đa cộng MỖI LẦN gọi
BONUS_MAX_SEC = 3650 * 86400                          # tổng giờ cộng thêm tối đa của 1 key


def _parse_dur(b, ak="amount", uk="unit", hk="hours"):
    """Đọc {"amount": N, "unit": hour|day|week|month} (hoặc {"hours": N} kiểu cũ) -> số GIÂY > 0, không hợp lệ -> 0. N = số nguyên 1..99999, tối đa ADD_MAX_SEC."""
    try:
        if b.get(ak) is not None:
            a, unit = b.get(ak), str(b.get(uk) or "hour").strip().lower()
        elif b.get(hk) is not None:
            a, unit = b.get(hk), "hour"
        else:
            return 0
        if isinstance(a, bool) or (isinstance(a, float) and a != int(a)):
            return 0
        a = int(a)
    except (TypeError, ValueError, OverflowError):
        return 0
    mul = ADD_UNITS.get(unit)
    if not mul or a <= 0 or a > 99999:
        return 0
    return a * mul if a * mul <= ADD_MAX_SEC else 0


def _bonus(rec):
    """Tổng số GIÂY đã cộng thêm cho key (nút +1 giờ / tặng giờ lúc tạo). Key cũ không có trường này = 0."""
    try:
        return max(0, int(rec.get("bonus") or 0))
    except (TypeError, ValueError):
        return 0


def _add_time(rec, secs, now):
    """Cộng `secs` giây cho key. Đã kích hoạt: dời hạn (key đã hết hạn thì tính từ bây giờ). Chưa kích hoạt: cộng dồn vào bonus, áp dụng khi kích hoạt."""
    rec["bonus"] = _bonus(rec) + int(secs)
    if _activated(rec):
        rec["exp"] = max(int(rec.get("exp") or 0), int(now)) + int(secs)


def _activate(rec, now):
    """Kích hoạt lần đầu: bắt đầu tính hạn từ `now` (exp = now + số ngày của gói). Trả True nếu VỪA kích hoạt (nơi gọi phải _kv_save)."""
    if _activated(rec):
        return False
    try:
        days = max(1, int(rec.get("days") or 1))
    except (TypeError, ValueError):
        days = 1
    rec["act"] = now
    rec["exp"] = now + days * 86400 + _bonus(rec)
    return True


def _left_sec(rec, now):
    """Số giây còn lại; key chưa kích hoạt = trọn gói (days * 86400)."""
    if _activated(rec):
        return max(0, int(rec.get("exp") or 0) - int(now))
    try:
        return max(0, int(rec.get("days") or 0)) * 86400 + _bonus(rec)
    except (TypeError, ValueError):
        return 0


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


def _key_game(rec):
    """Game của key người dùng: "sun" | "hit"; key cũ chưa gán game -> KEY_LEGACY_GAME ("all" = mọi game)."""
    g = str(rec.get("game") or "").strip().lower()
    if g == "tele68":                                  # tên cũ -> LC79 (key TELE-... đã tạo trước vẫn dùng được, chỉ cho game LC79)
        g = "lc79"
    if g in _KEY_DEAD_GAMES:                           # game đã gỡ (68GB): key giữ nguyên game cũ -> không khớp endpoint nào, không lên quyền "mọi game"
        return g
    return g if g in KEY_GAMES else KEY_LEGACY_GAME


def _game_ok(kg, game):
    """Key thuộc game `kg` có được dùng cho `game` không (game None = endpoint không gắn game cụ thể -> mọi key hợp lệ)."""
    if kg == "autolc" or game == "autolc":                # key AUTO CƯỢC LC chỉ dùng cho /tool/autocuoc; key cũ "all" cũng KHÔNG vào được auto cược
        return kg == game
    return game is None or kg == "all" or kg == game


def _key_tables(kg):
    """Các bàn LC mà key thuộc game `kg` được thao tác (key game lc79 hoặc key cũ "all" -> cả 2 bàn LC; key game khác -> không bàn nào)."""
    out = set()
    for k, tb in LC_TABLES.items():
        if kg in ("all", tb.kgame):
            out.add(k)
    return out


def _path_game(p):
    """Game mà endpoint thuộc về (None = endpoint chung: mọi key hợp lệ đều gọi được)."""
    if p in ("/api/predictlcmd5", "/api/predictlchu", "/api/predicttele68txmd5"):
        return "lc79"
    if p == "/api/notice":                                 # thông báo: game lấy từ ?game= (danh sách trắng) -> key game khác bị 403, KHÔNG đọc được thông báo game khác
        g = (request.args.get("game") or "").strip().lower()
        g = "lc79" if g == "tele68" else g
        return g if g in NOTICE_GAMES else None
    return None


WRONG_GAME_MSG = "Key này chỉ dùng cho game"


def _own_user_key(s, r):
    """Admin phụ chỉ động được vào key NGƯỜI DÙNG do chính mình tạo; admin chính động được mọi key."""
    return s["r"] == "main" or (r.get("type") == "user" and r.get("by") == "sub" and r.get("by_name") == s["n"])


# ─ phiên đăng nhập admin (SEC2): token NGẪU NHIÊN 256-bit, server chỉ lưu SHA-256 của nó (không có khoá ký nào để lộ / giả mạo) ─
#   · mỗi phiên có thêm KHOÁ KÝ RIÊNG `sk` (chỉ trả 1 lần lúc đăng nhập). MỌI request admin phải kèm X-Ts + X-Nonce + X-Sig = HMAC-SHA256(sk, METHOD\nPATH?QUERY\nTS\nNONCE\nSHA256(body)).
#     -> chặn: chèn / sửa request giữa đường, phát lại (replay) request cũ, dùng token bị lộ trong log / Referer mà không có `sk`.
#   · nonce chỉ dùng 1 lần (cache 3 phút), lệch giờ tối đa SEC_SIGN_SKEW giây · phiên chết sau SESS_IDLE giây không hoạt động / SESS_ABS giây tuyệt đối · bị gắn với User-Agent đã đăng nhập.
#   · chạy đúng với gunicorn --workers 1 (đã bắt buộc bởi auto cược). Restart server = phiên admin mất, đăng nhập lại.
SESS_IDLE = _env_num("SUNVIW_SESS_IDLE", 30 * 60, int)
SESS_ABS = _env_num("SUNVIW_SESS_ABS", 8 * 3600, int)
SEC_SIGN_ADMIN = _env_bool("SUNVIW_SIGN_ADMIN", True)
SEC_SIGN_SKEW = _env_num("SUNVIW_SIGN_SKEW", 60, int)
_sess = {}
_sess_lock = threading.Lock()
_nonce_seen = {}
SESS_MAX = 200


def _sh(x):
    return hashlib.sha256(("sunviw-sess:" + str(x)).encode("utf-8")).hexdigest()


def _ua_h():
    return hashlib.sha256(request.headers.get("User-Agent", "").encode("utf-8", "ignore")).hexdigest()[:24]


def _tok_make(role, name, key="", hw=""):
    """Tạo phiên. Trả token (chuỗi). Khoá ký sk lấy bằng _tok_sk(token) ngay sau đó (chỉ 1 lần)."""
    sid, sk = secrets.token_urlsafe(32), secrets.token_hex(32)
    now = time.time()
    with _sess_lock:
        for h in [h for h, v in _sess.items() if v["abs"] < now or v["last"] + SESS_IDLE < now]:
            del _sess[h]
        if len(_sess) >= SESS_MAX:                       # đầy -> bỏ phiên cũ nhất
            del _sess[min(_sess, key=lambda h: _sess[h]["last"])]
        _sess[_sh(sid)] = {"r": role, "n": name, "k": key, "h": hw, "ua": _ua_h(), "ip": client_ip(), "sk": sk,
                           "t0": now, "last": now, "abs": now + SESS_ABS}
    flask_g._sk_once = sk
    return sid


def _tok_pair(role, name, key="", hw=""):
    t = _tok_make(role, name, key, hw)
    return {"token": t, "sk": flask_g._sk_once}


def _tok_kill(token):
    with _sess_lock:
        _sess.pop(_sh(token), None)


def _audit(ev, **kw):
    """Nhật ký bảo mật (JSON / dòng). KHÔNG bao giờ ghi key / mật khẩu / token."""
    try:
        rec = {"t": int(time.time()), "ev": ev, "ip": client_ip(), "path": request.path, "ua": request.headers.get("User-Agent", "")[:60]}
        rec.update(kw)
        pth = os.environ.get("SUNVIW_AUDIT_PATH", _data_path("sunviw_audit.log"))
        if os.path.exists(pth) and os.path.getsize(pth) > 2 * 1024 * 1024:
            os.replace(pth, pth + ".1")
        with open(pth, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001
        pass


def _sig_ok(sess):
    """Kiểm chữ ký request admin (xem khối trên). True nếu hợp lệ + nonce chưa dùng."""
    if not SEC_SIGN_ADMIN:
        return True
    ts, nonce, sig = request.headers.get("X-Ts", ""), request.headers.get("X-Nonce", ""), request.headers.get("X-Sig", "")
    if not (ts.isdigit() and 8 <= len(nonce) <= 64 and re.fullmatch(r"[A-Za-z0-9_-]+", nonce) and re.fullmatch(r"[0-9a-f]{64}", sig)):
        return False
    now = time.time()
    if abs(now - int(ts)) > SEC_SIGN_SKEW:
        return False
    qs = request.query_string.decode("latin-1")
    msg = "\n".join((request.method, request.path + ("?" + qs if qs else ""), ts, nonce, hashlib.sha256(request.get_data(cache=True)).hexdigest()))
    good = hmac.new(sess["sk"].encode(), msg.encode("utf-8", "ignore"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(good, sig):
        return False
    nk = sess["sid_h"] + ":" + nonce
    with _sess_lock:
        if len(_nonce_seen) > 20000:
            for k in [k for k, e in _nonce_seen.items() if e < now]:
                del _nonce_seen[k]
        if nk in _nonce_seen:                              # PHÁT LẠI request cũ -> từ chối
            return False
        _nonce_seen[nk] = now + 180
    return True


def _tok_check():
    """Trả {"r","n","k"} nếu X-Admin-Token + chữ ký hợp lệ, ngược lại None (kết quả cache trong 1 request — nonce chỉ dùng 1 lần).
    Admin phụ: key còn tồn tại + còn hạn + đúng THIẾT BỊ đã đăng nhập + máy đó vẫn gắn vào key (admin chính reset / gỡ / xóa key -> phiên chết ngay). Không xét IP."""
    c = getattr(flask_g, "_tok_res", False)
    if c is not False:
        return c
    flask_g._tok_res = None
    t = request.headers.get("X-Admin-Token", "")
    if not t or len(t) > 100:
        return None
    sh = _sh(t)
    now = time.time()
    with _sess_lock:
        v = _sess.get(sh)
        if v is None:
            return None
        if v["abs"] < now or v["last"] + SESS_IDLE < now:
            _sess.pop(sh, None)
            return None
        if not hmac.compare_digest(v["ua"], _ua_h()):      # khác thiết bị: từ chối nhưng KHÔNG huỷ phiên (kẻ cắp token không được phép đá admin thật ra)
            return None
        sess = dict(v, sid_h=sh)
    if not _sig_ok(sess):
        _audit("sig_fail", role=sess["r"])
        return None
    with _sess_lock:
        if sh in _sess:
            _sess[sh]["last"] = now
    try:
        if sess["r"] == "main":
            flask_g._tok_res = {"r": "main", "n": ADMIN_MAIN_NAME, "k": "", "sh": sh}
            return flask_g._tok_res
        if sess["r"] == "sub":
            hw, alts, hfresh = req_hw_ids()
            if not hw:
                return None
            inow = int(now)
            with _kv_lock:
                d = _kv_load()
                rec = d["keys"].get(sess["k"])
                if rec and rec.get("type") == "sub" and rec.get("owner") == sess["n"] and not _is_expired(rec, inow):
                    devs = rec.get("devs") if isinstance(rec.get("devs"), dict) else {}
                    kr = _dev_find(devs, hw, alts, hfresh)
                    if kr is not None and kr == _dev_find(devs, sess.get("h", "")):
                        _, _, ch = _dev_use(rec, hw, client_ip(), request.headers.get("User-Agent", ""), inow, alts, hfresh, bind=False)
                        if ch:
                            try:
                                _kv_save(d)
                            except OSError:
                                pass
                        flask_g._tok_res = {"r": "sub", "n": sess["n"], "k": sess["k"], "sh": sh}
                        return flask_g._tok_res
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


def _key_price(days):
    """Giá bán (VNĐ) của gói `days` ngày; gói chưa có giá -> 0."""
    try:
        return int(KEY_PRICE.get(int(days), 0))
    except (TypeError, ValueError):
        return 0


def _rev_record(d, k, rec, now):
    """Ghi 1 key người dùng VỪA kích hoạt vào sổ doanh thu d["rev"] (nơi gọi tự _kv_save). Sổ độc lập với danh sách key -> xóa key / dọn key hết hạn KHÔNG làm mất doanh thu."""
    if rec.get("type") != "user":
        return
    rv = d.setdefault("rev", {})
    if not isinstance(rv, dict):
        rv = d["rev"] = {}
    rv[k] = {"t": int(now), "g": _key_game(rec), "d": int(rec.get("days") or 0), "p": _key_price(rec.get("days"))}
    cut = now - REV_KEEP_SEC
    for kk in [x for x, v in rv.items() if int((v or {}).get("t") or 0) < cut]:
        del rv[kk]


def _vn_day_start(now):
    """Mốc 00:00 (giờ VN) của NGÀY chứa `now` (epoch giây). Tính bằng số học nên không phụ thuộc múi giờ máy chủ."""
    now = int(now)
    return now - (now + VN_UTC_OFFSET) % 86400


def _vn_week_start(now):
    """Mốc 00:00 THỨ HAI (giờ VN) của TUẦN chứa `now` (tuần tính T2 -> CN)."""
    ds = _vn_day_start(now)
    wd = ((ds + VN_UTC_OFFSET) // 86400 + 3) % 7          # 1970-01-01 là thứ Năm -> T2 = 0 … CN = 6
    return ds - wd * 86400


def _revenue_calc(d, now):
    """Doanh thu tính từ lúc KÍCH HOẠT key, tách theo game:
         · \"ngay\"  = HÔM NAY: từ 00:00 hôm nay (giờ VN) tới giờ — qua 00:00 ngày mới là về 0 (KHÔNG phải cứ đủ 24 giờ)
         · \"tuan\"  = TUẦN NÀY: từ 00:00 thứ Hai (giờ VN) tới giờ — sang thứ Hai mới là về 0
         · \"thang\" = 30 ngày gần nhất (cửa sổ trượt như cũ)
       Mỗi cửa sổ trả thêm \"tu\" (mốc bắt đầu, epoch) và \"den\" (mốc reset kế tiếp, None với tháng) để trang admin tự làm mới khi qua mốc.
       Nguồn = sổ d[\"rev\"] + các key người dùng ĐÃ kích hoạt từ trước bản này mà chưa có trong sổ (tính theo giá hiện tại, thời điểm = lúc kích hoạt; key cũ không có trường act = lúc tạo)."""
    ent = {}
    for k, v in (d.get("rev") or {}).items():
        if isinstance(v, dict):
            ent[k] = (int(v.get("t") or 0), str(v.get("g") or "all"), int(v.get("d") or 0), int(v.get("p") or 0))
    for k, r in (d.get("keys") or {}).items():
        if k in ent or r.get("type") != "user" or not _activated(r):
            continue
        t = int(r.get("act") or r.get("created") or 0)
        if t:
            ent[k] = (t, _key_game(r), int(r.get("days") or 0), _key_price(r.get("days")))
    ds, ws = _vn_day_start(now), _vn_week_start(now)
    wins = (("ngay", ds, ds + 86400), ("tuan", ws, ws + 7 * 86400), ("thang", int(now) - 30 * 86400, None))
    games = list(KEY_GAMES) + ["all"] + [g for g in _KEY_DEAD_GAMES if any(e[1] == g for e in ent.values())]   # game đã gỡ chỉ hiện khi còn doanh thu cũ
    out = {w: {"tu": t0, "den": t1, "tong": 0, "so_key": 0, "chua_co_gia": 0, "game": {g: {"tien": 0, "so_key": 0} for g in games}} for w, t0, t1 in wins}
    for t, g, days, price in ent.values():
        g = g if g in games else "all"
        for w, t0, _t1 in wins:
            if t0 <= t <= now + 60:
                o = out[w]
                if price > 0:
                    o["tong"] += price
                    o["so_key"] += 1
                    o["game"][g]["tien"] += price
                    o["game"][g]["so_key"] += 1
                else:
                    o["chua_co_gia"] += 1
    return out


def _check_user_key(k, hw=None, ip="", ua="", alts=(), fresh=False, game=None, bind=True):
    """(record, lỗi, đã_tồn_tại, game_của_key). Chỉ key loại 'user' còn hạn VÀ đúng game (nếu `game` được truyền) mới qua; sai game -> lỗi bắt đầu bằng WRONG_GAME_MSG, KHÔNG gắn thiết bị. Có HWID -> kiểm tra / gắn thiết bị (đủ chỗ mới gắn thêm) và ghi "lần dùng gần nhất";
    không có HWID mà HWID_REQUIRED bật -> từ chối. `ip` chỉ để ghi lại, không dùng để chặn."""
    k = _norm_key(k)
    if not k:
        return None, "thieu key", False, None
    with _kv_lock:
        d = _kv_load()
        r = d["keys"].get(k)
        if not r or r.get("type") != "user":
            return None, "key khong hop le", False, None
        now = int(time.time())
        kg = _key_game(r)
        if _is_expired(r, now):
            return None, "key da het han", True, kg
        if not _game_ok(kg, game):
            return None, (f"{WRONG_GAME_MSG} {KEY_GAME_LABEL.get(kg, kg)} — không dùng được cho game {KEY_GAME_LABEL.get(game, game)}. "
                          f"Hãy dùng key {KEY_GAME_LABEL.get(game, game)} (hoặc xin admin tạo key {KEY_GAME_LABEL.get(game, game)})."), True, kg
        if not bind:                                     # bind=False: KHÔNG gắn / giới hạn thiết bị (auto cược LC chỉ vào nhánh này khi đặt SUNVIW_AB_BIND_DEVICE=0)
            ch = False
        elif hw:
            ok, err, ch = _dev_use(r, hw, ip, ua, now, alts, fresh)
            if not ok:
                return None, err, True, kg
        elif HWID_REQUIRED:
            return None, "Thiếu mã thiết bị (HWID) — gửi header X-HWID hoặc ?hwid= cùng key.", True, kg
        else:
            ch = False
        if _activate(r, now):                            # lần dùng THÀNH CÔNG đầu tiên (đúng game + gắn được thiết bị) -> bắt đầu tính hạn từ đây
            ch = True
            _rev_record(d, k, r, now)                    # ghi sổ doanh thu (giá chốt ngay lúc kích hoạt)
        if ch:
            try:
                _kv_save(d)
            except OSError:
                pass
        return r, "", True, kg


_GATED_EXACT = {"/api/notice", "/api/predictlcmd5", "/api/predictlchu", "/api/predicttele68txmd5", "/api/ips", "/api/history/clear", "/api/history/regrade", "/api/history/wipe"}


# ═══════════════════════════════════════════════════════════════════════════
#  🔌  OFF SERVER THEO TỪNG BÀN LC (CHỈ ADMIN CHÍNH bật/tắt)  —  CHỈNH Ở ĐÂY
# ═══════════════════════════════════════════════════════════════════════════
#   2 công tắc RIÊNG: lcmd5 (LC · MD5) · lchu (LC · Hũ). Tắt bàn nào thì CHỈ tool dùng bàn đó nhận HTTP 503 {"server_off": true} và không có dự đoán;
#   server VẪN quét API / tính 13 logic / lưu ván đã chấm bình thường. Chỉ admin chính (phiên ký, KHÔNG gửi key) mới đọc được dự đoán của bàn đang OFF.
#   Request tool bị chặn TRƯỚC khi kiểm key -> không kích hoạt key / không gắn thiết bị. Hạn key đã kích hoạt vẫn chạy bình thường trong lúc off.
#   🔒 CHỐNG BYPASS nhiều lớp: _gate_offserver (before_request) -> _gate_key (before_request) -> _view_guard (NGAY TRONG view, không dựa vào before_request) -> _security_selfcheck lúc khởi động -> danh sách trắng đầu ra _tool_view.
#   Trạng thái lưu file OFFSRV_PATH (cùng Volume) -> còn nguyên sau restart / deploy. Env: SUNVIW_OFFSRV=1 (khởi động khi chưa có file: tất cả off) · SUNVIW_OFFSRV_TABLES=lcmd5,lc79 · SUNVIW_OFFSRV_PATH.
#   Endpoint: GET /api/admin/offserver · POST /api/admin/offserver {"tables":["lcmd5"],"off":true} | {"games":["lc79"],"off":true} | {"all":true,"off":false} — cần phiên admin CHÍNH.
OFFSRV_PATH = os.environ.get("SUNVIW_OFFSRV_PATH", _data_path("sunviw_offserver.json"))
OFFSRV_TABLES = ("lcmd5", "lchu")
OFFSRV_LABEL = {"lcmd5": "LC · MD5", "lchu": "LC · Hũ"}
OFFSRV_GAME_TABLES = {"lc79": ("lcmd5", "lchu")}
OFFSRV_GAME_LABEL = {"lc79": "LC79"}
OFFSRV_GAME_ALIAS = {"lc": "lc79", "tele68": "lc79"}
OFFSRV_TABLE_ALIAS = {"tele68txmd5": "lcmd5"}
OFFSRV_PATH_TABLE = {"/api/predictlcmd5": "lcmd5", "/api/predicttele68txmd5": "lcmd5", "/api/predictlchu": "lchu"}
OFFSRV_PATHS = frozenset(OFFSRV_PATH_TABLE)
OFFSRV_MSG = "đang OFF — tạm ngừng cấp dự đoán cho tool. Vui lòng thử lại sau."


def _offsrv_msg(tk):
    return f"Server {OFFSRV_LABEL.get(tk, '')} {OFFSRV_MSG}".replace("  ", " ")


def _offsrv_norm_table(x):
    x = str(x or "").strip().lower()
    x = OFFSRV_TABLE_ALIAS.get(x, x)
    return x if x in OFFSRV_TABLES else None


def _offsrv_norm_game(x):
    x = str(x or "").strip().lower()
    x = OFFSRV_GAME_ALIAS.get(x, x)
    return x if x in OFFSRV_GAME_TABLES else None


def _offsrv_env_default():
    """Tập bàn OFF khi CHƯA có file: SUNVIW_OFFSRV=1 -> tất cả · SUNVIW_OFFSRV_TABLES=lcmd5,hit,... -> các bàn / game liệt kê."""
    if _env_bool("SUNVIW_OFFSRV", False):
        return frozenset(OFFSRV_TABLES)
    out = set()
    for x in os.environ.get("SUNVIW_OFFSRV_TABLES", "").replace(";", ",").split(","):
        t, g = _offsrv_norm_table(x), _offsrv_norm_game(x)
        if t:
            out.add(t)
        elif g:
            out.update(OFFSRV_GAME_TABLES[g])
    return frozenset(out)


OFFSRV_DEFAULT_TABLES = _offsrv_env_default()
OFFSRV_DEFAULT = bool(OFFSRV_DEFAULT_TABLES)            # giữ tên cũ (có bàn nào mặc định off không)
_os_lock = threading.Lock()                              # bảo vệ cache
_os_wlock = threading.Lock()                             # tuần tự hoá đọc-sửa-ghi file
_os_cache = {"sig": None, "t": None, "good": None}       # cache theo (mtime, size, inode) của file -> mỗi request chỉ tốn 1 lần os.stat


def _offsrv_defaults():
    return {k: {"off": k in OFFSRV_DEFAULT_TABLES, "at": None, "by": None} for k in OFFSRV_TABLES}


def _offsrv_parse(o):
    """Nội dung file -> {bàn: {"off","at","by"}}. Hiểu v2 {"tables": {...}} và file cũ {"off": bool} (off cũ = TẤT CẢ bàn). Sai cấu trúc -> ném ValueError."""
    if not isinstance(o, dict):
        raise ValueError("offserver: file khong phai object")
    t = _offsrv_defaults()

    def _meta(e):
        at = e.get("at")
        return (int(at) if isinstance(at, (int, float)) and not isinstance(at, bool) else None), (str(e.get("by") or "")[:40] or None)

    if isinstance(o.get("tables"), dict):
        for k in OFFSRV_TABLES:
            e = o["tables"].get(k)
            if isinstance(e, dict):
                at, by = _meta(e)
                t[k] = {"off": bool(e.get("off")), "at": at, "by": by}
    elif "off" in o:
        at, by = _meta(o)
        for k in OFFSRV_TABLES:
            t[k] = {"off": bool(o.get("off")), "at": at, "by": by}
    else:
        raise ValueError("offserver: file khong co tables / off")
    return t


def _offsrv_read_file():
    """Đọc thẳng file (không cache). Thiếu file -> None; hỏng -> ném."""
    try:
        with open(OFFSRV_PATH, "r", encoding="utf-8") as f:
            return _offsrv_parse(json.load(f))
    except FileNotFoundError:
        return None


def _offsrv_tables():
    """{bàn: {"off","at","by"}} (KHÔNG sửa đối tượng trả về — đang dùng chung với cache). Chưa có file -> mặc định; file hỏng -> trạng thái hợp lệ gần nhất."""
    try:
        stt = os.stat(OFFSRV_PATH)
        sig = (stt.st_mtime_ns, stt.st_size, stt.st_ino)
    except OSError:
        return _offsrv_defaults()
    with _os_lock:
        if _os_cache["sig"] == sig and _os_cache["t"] is not None:
            return _os_cache["t"]
        good = _os_cache["good"]
    try:
        t = _offsrv_read_file()
    except Exception:  # noqa: BLE001
        return good if good is not None else _offsrv_defaults()
    if t is None:
        return _offsrv_defaults()
    with _os_lock:
        _os_cache.update(sig=sig, t=t, good=t)
    return t


def offsrv_table_off(key):
    """Bàn `key` đang OFF SERVER không (khoá lạ -> False)."""
    return bool(_offsrv_tables().get(key, {}).get("off"))


def offsrv_state():
    """Tổng hợp: {"tables": {...}, "off": TẤT CẢ bàn đang off, "any": có bàn nào off, "off_list": [...]}."""
    t = _offsrv_tables()
    offs = [k for k in OFFSRV_TABLES if t[k]["off"]]
    return {"tables": t, "off": len(offs) == len(OFFSRV_TABLES), "any": bool(offs), "off_list": offs}


def offsrv_set_tables(keys, off, by):
    """Bật / tắt OFF SERVER cho các bàn `keys` (chỉ đổi đúng các bàn đó, ghi nguyên tử). Ném OSError nếu không ghi được. Trả {bàn: {...}}."""
    keys = [k for k in OFFSRV_TABLES if k in set(keys)]
    now, off = int(time.time()), bool(off)
    with _os_wlock:
        try:
            base = _offsrv_read_file()
        except Exception:  # noqa: BLE001
            base = None
        t = {k: dict(v) for k, v in (base or _offsrv_defaults()).items()}
        for k in keys:
            if t[k]["off"] != off or t[k]["at"] is None:
                t[k] = {"off": off, "at": now, "by": str(by or "")[:40] or None}
        tmp = OFFSRV_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"v": 2, "tables": t}, f, ensure_ascii=False)
        os.replace(tmp, OFFSRV_PATH)
        with _os_lock:
            _os_cache.update(sig=None, t=None, good=t)           # bỏ cache -> lần đọc sau lấy đúng file mới
    return t


def offsrv_set(off, by):
    """(giữ tên cũ) bật / tắt TẤT CẢ bàn."""
    return offsrv_set_tables(OFFSRV_TABLES, off, by)


def _offsrv_view():
    t = _offsrv_tables()
    rows = [{"key": k, "ten": OFFSRV_LABEL[k], "game": next(g for g, ks in OFFSRV_GAME_TABLES.items() if k in ks),
             "off": t[k]["off"], "luc": t[k]["at"], "boi": t[k]["by"]} for k in OFFSRV_TABLES]
    games = []
    for g, ks in OFFSRV_GAME_TABLES.items():
        n = sum(1 for k in ks if t[k]["off"])
        games.append({"key": g, "ten": OFFSRV_GAME_LABEL[g], "tables": list(ks), "off": n == len(ks), "mot_phan": 0 < n < len(ks)})
    n_off = sum(1 for r in rows if r["off"])
    last = max((r for r in rows if r["off"] and r["luc"]), key=lambda r: r["luc"], default=None)
    return {"ok": True, "off": n_off == len(rows), "any": n_off > 0, "n_off": n_off, "tables": rows, "games": games,
            "luc": last["luc"] if last else None, "boi": last["boi"] if last else None}


def _offsrv_pass():
    """Request này được lấy dự đoán của bàn đang OFF không: CHỈ admin CHÍNH (phiên ký hợp lệ)."""
    if request.headers.get("X-Admin-Token"):
        _s = _tok_check()
        if _s and _s["r"] == "main":
            return True
    return False


def _offsrv_block(tk):
    r = _json({"ok": False, "server_off": True, "loi": _offsrv_msg(tk)}, 503)
    r.headers["Retry-After"] = "30"
    return r


@app.before_request
def _gate_offserver():
    """Bàn của endpoint đang OFF SERVER -> chỉ admin chính nhận được dự đoán; tool ngoài nhận 503. Chạy TRƯỚC _gate_key."""
    if request.method == "OPTIONS":
        return None
    tk = OFFSRV_PATH_TABLE.get(request.path)
    if tk is None or not offsrv_table_off(tk):
        return None
    if not _rate_ok(f"off:{client_ip()}", RATE_IP):                # dội vào endpoint đang off: vẫn bị giới hạn tốc độ
        return _too_many()
    if _offsrv_pass():
        flask_g.off_ok = True                                       # view_guard đọc cờ này: không có cờ mà bàn đang off -> view tự từ chối
        return None
    return _offsrv_block(tk)


def _view_guard(tk):
    """LỚP PHÒNG THỦ NẰM TRONG VIEW (gọi đầu mỗi endpoint dự đoán): không dựa vào before_request. Trả Response nếu phải chặn, None nếu được qua.
    Chặn khi: (a) chưa qua cổng key / panel · (b) key không thuộc game của bàn này · (c) bàn đang OFF mà request chưa được _gate_offserver cho qua."""
    panel = _is_panel()
    if not panel and not getattr(flask_g, "key_ok", False):
        return _json({"ok": False, "can_key": True, "loi": "thieu key"}, 401)
    if tk not in _key_tables(getattr(flask_g, "key_game", "")):
        return _json({"ok": False, "sai_game": True, "loi": "key khong thuoc game nay"}, 403)
    if offsrv_table_off(tk) and not getattr(flask_g, "off_ok", False):
        return _offsrv_block(tk)
    return None


@app.route("/api/admin/offserver", methods=["GET", "POST"])
def api_admin_offserver():
    """Xem / bật / tắt OFF SERVER theo bàn. CHỈ admin chính.
    POST {"off": true|false} + chọn phạm vi: "tables": ["lcmd5", ...] · "games": ["sun"|"hit"|"lc79", ...] · "all": true. Không chọn phạm vi (kiểu cũ {"off": true}) = tất cả bàn."""
    s, err = _need_admin()
    if err:
        return err
    if s["r"] != "main":
        return _json({"ok": False, "loi": "chi admin chinh moi bat / tat duoc off server"}, 403)
    if request.method == "POST":
        b = request.get_json(silent=True) or {}
        if not isinstance(b.get("off"), bool):
            return _json({"ok": False, "loi": 'can {"off": true|false} (+ "tables": [...] | "games": [...] | "all": true)'}, 400)
        keys = set()
        if b.get("all") is True:
            keys.update(OFFSRV_TABLES)
        for fld, norm, expand in (("tables", _offsrv_norm_table, lambda v: (v,)), ("games", _offsrv_norm_game, lambda v: OFFSRV_GAME_TABLES[v])):
            vals = b.get(fld)
            if vals is None:
                continue
            if not isinstance(vals, list) or not vals or len(vals) > 16 or any(not isinstance(x, str) for x in vals):
                return _json({"ok": False, "loi": f'"{fld}" phai la danh sach khong rong cac chuoi'}, 400)
            for x in vals:
                v = norm(x)
                if v is None:
                    return _json({"ok": False, "loi": f'"{fld}" co gia tri khong hop le'}, 400)
                keys.update(expand(v))
        if not keys:
            if any(f in b for f in ("all", "tables", "games")):
                return _json({"ok": False, "loi": "chua chon ban / game nao"}, 400)
            keys.update(OFFSRV_TABLES)                              # kiểu cũ {"off": bool} = tất cả
        try:
            offsrv_set_tables(keys, b["off"], s["n"])
        except OSError as e:
            return _json({"ok": False, "loi": f"khong ghi duoc file off server: {e}"}, 500)
        _audit("offserver_set", by=s["n"], off=b["off"], tables=sorted(keys))
    return _json(_offsrv_view())


# ═══════════════════════════════════════════════════════════════════════════
#  📢  THÔNG BÁO TỚI TOOL LC (CHỈ ADMIN CHÍNH gửi / gỡ; tool chỉ ĐỌC qua GET /api/notice?game=lc79 — cần key LC + HWID)
# ═══════════════════════════════════════════════════════════════════════════
#   Gửi / gỡ chỉ qua POST /api/admin/notice/send · /api/admin/notice/delete và PHẢI có phiên admin CHÍNH: token + chữ ký HMAC từng request (nonce dùng 1 lần, gắn User-Agent).
#   Server làm sạch nội dung (bỏ ký tự điều khiển / đảo chiều chữ, giới hạn độ dài + số dòng), kiểm mọi con số; trần số thông báo chạy cùng lúc + giới hạn tốc độ gửi.
NOTICE_PATH = os.environ.get("SUNVIW_NOTICE_PATH", _data_path("sunviw_notice.json"))
NOTICE_GAMES = ("lc79",)                                      # game nhận được thông báo = tool LC79
NOTICE_TEXT_MAX = 300
NOTICE_LINES_MAX = 6
NOTICE_SIZE_MIN, NOTICE_SIZE_MAX, NOTICE_SIZE_DEFAULT = 12, 96, 28
NOTICE_DUR_MIN = 5                                       # giây
NOTICE_DUR_MAX = 30 * 86400
NOTICE_MAX_ACTIVE = 20
NOTICE_SEND_RATE = _env_num("SUNVIW_NOTICE_RATE", 20, int)
_NT_ID_RE = re.compile(r"[0-9a-f]{12}")
_nt_lock = threading.RLock()
_nt_cache = {"sig": None, "items": None}                 # cache theo (mtime, size) của file -> mỗi request chỉ tốn 1 lần os.stat


def _nt_clean_text(s):
    """Làm sạch nội dung: chuẩn hóa Unicode, bỏ ký tự điều khiển / ký tự đảo chiều chữ (giữ xuống dòng + ZWJ của emoji), cắt khoảng trắng đầu / cuối từng dòng."""
    if not isinstance(s, str):
        return ""
    s = unicodedata.normalize("NFC", s).replace("\r\n", "\n").replace("\r", "\n")
    s = "".join(ch for ch in s if ch in ("\n", "\u200d") or unicodedata.category(ch)[0] != "C")
    s = "\n".join(ln.strip() for ln in s.split("\n")).strip()
    return re.sub(r"\n{3,}", "\n\n", s)


def _nt_num(v, lo, hi, clamp=False):
    """Số hợp lệ trong [lo, hi] (bool / NaN / chuỗi -> None). clamp=True: kẹp vào khoảng; ngược lại ngoài khoảng -> None."""
    if isinstance(v, bool) or not isinstance(v, (int, float)) or v != v or v in (float("inf"), float("-inf")):
        return None
    if clamp:
        return min(hi, max(lo, v))
    return v if lo <= v <= hi else None


def _nt_norm_item(it):
    """Kiểm tra 1 thông báo đọc từ file; sai cấu trúc -> None (bỏ qua, không làm hỏng các thông báo khác)."""
    try:
        if not isinstance(it, dict) or not isinstance(it.get("id"), str) or not _NT_ID_RE.fullmatch(it["id"]):
            return None
        text = _nt_clean_text(it.get("text"))
        games = it.get("games")
        if not text or len(text) > NOTICE_TEXT_MAX or not isinstance(games, list) or not games:
            return None
        games = [g for g in games if g == "all" or g in NOTICE_GAMES]
        x, y = _nt_num(it.get("x"), 0, 100, True), _nt_num(it.get("y"), 0, 100, True)
        size, t, exp = _nt_num(it.get("size"), NOTICE_SIZE_MIN, NOTICE_SIZE_MAX, True), _nt_num(it.get("t"), 0, 4e9), _nt_num(it.get("exp"), 0, 4e9)
        if not games or None in (x, y, size, t, exp):
            return None
        return {"id": it["id"], "text": text, "games": ["all"] if "all" in games else games, "x": round(float(x), 2), "y": round(float(y), 2),
                "size": int(size), "t": int(t), "exp": int(exp), "by": str(it.get("by") or "")[:40]}
    except Exception:  # noqa: BLE001
        return None


def _nt_read(force=False):
    """Danh sách thông báo (cả đã hết hạn nếu chưa bị dọn). File thiếu / hỏng -> []."""
    with _nt_lock:
        try:
            stt = os.stat(NOTICE_PATH)
            sig = (stt.st_mtime_ns, stt.st_size)
        except OSError:
            _nt_cache.update(sig=None, items=[])
            return []
        if not force and _nt_cache["sig"] == sig and _nt_cache["items"] is not None:
            return _nt_cache["items"]
        items = []
        try:
            with open(NOTICE_PATH, "r", encoding="utf-8") as f:
                o = json.load(f)
            for raw in (o.get("items") if isinstance(o, dict) else None) or []:
                it = _nt_norm_item(raw)
                if it:
                    items.append(it)
        except Exception:  # noqa: BLE001
            items = []
        _nt_cache.update(sig=sig, items=items)
        return items


def _nt_write(items):
    """Ghi nguyên tử (file tạm rồi đổi tên). Ném OSError nếu không ghi được."""
    tmp = NOTICE_PATH + ".tmp"
    with _nt_lock:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"v": 1, "items": items}, f, ensure_ascii=False)
        os.replace(tmp, NOTICE_PATH)
        _nt_cache.update(sig=None, items=None)


def _nt_active(now):
    return [it for it in _nt_read() if it["exp"] > now]


def _nt_need_main():
    """Chỉ admin CHÍNH (phiên hợp lệ + chữ ký request). Trả (session, None) hoặc (None, response lỗi)."""
    s, err = _need_admin()
    if err:
        return None, err
    if s["r"] != "main":
        _audit("notice_denied", role=s["r"])
        return None, _json({"ok": False, "loi": "chi admin chinh moi dung duoc thong bao"}, 403)
    return s, None


@app.route("/api/notice")
def api_notice():
    """Tool đọc thông báo (CHỈ ĐỌC). Cổng _gate_key đã bắt buộc key hợp lệ đúng game + HWID (hoặc admin chính / thiết bị panel đã duyệt)."""
    g = _path_game("/api/notice")                         # ?game= đã qua danh sách trắng (và đã khớp game của key ở _gate_key)
    if g is None:
        kg = getattr(flask_g, "key_game", None)
        g = kg if kg in NOTICE_GAMES else None
    now = time.time()
    out = [] if g is None else [{"id": it["id"], "text": it["text"], "x": it["x"], "y": it["y"], "size": it["size"], "con_lai": max(0, int(it["exp"] - now))}
                                for it in _nt_active(now) if "all" in it["games"] or g in it["games"]]
    return _json({"ok": True, "items": out})


@app.route("/api/admin/notice")
def api_admin_notice():
    """Danh sách thông báo đang chạy + cấu hình giới hạn cho form. CHỈ admin chính."""
    s, err = _nt_need_main()
    if err:
        return err
    now = time.time()
    items = sorted(_nt_active(now), key=lambda it: -it["t"])
    return _json({"ok": True, "now": int(now),
                  "items": [dict(it, con_lai=max(0, int(it["exp"] - now))) for it in items],
                  "cfg": {"games": [{"id": g, "ten": KEY_GAME_LABEL.get(g, g)} for g in NOTICE_GAMES], "text_max": NOTICE_TEXT_MAX, "lines_max": NOTICE_LINES_MAX,
                          "size": [NOTICE_SIZE_MIN, NOTICE_SIZE_MAX, NOTICE_SIZE_DEFAULT], "dur": [NOTICE_DUR_MIN, NOTICE_DUR_MAX], "max_active": NOTICE_MAX_ACTIVE}})


@app.route("/api/admin/notice/send", methods=["POST"])
def api_admin_notice_send():
    """Gửi thông báo mới. CHỈ admin chính. Body: {"games": ["lc79", ...] | ["all"], "text": "...", "x": 0-100, "y": 0-100, "size": px, "dur": giây}."""
    s, err = _nt_need_main()
    if err:
        return err
    if not _rate_ok(f"ntsend:{s['sh']}", NOTICE_SEND_RATE):
        return _too_many()
    b = request.get_json(silent=True)
    if not isinstance(b, dict):
        return _json({"ok": False, "loi": "du lieu gui len khong hop le"}, 400)
    text = _nt_clean_text(b.get("text"))
    if not text:
        return _json({"ok": False, "loi": "chua nhap noi dung thong bao"}, 400)
    if len(text) > NOTICE_TEXT_MAX or text.count("\n") + 1 > NOTICE_LINES_MAX:
        return _json({"ok": False, "loi": f"noi dung toi da {NOTICE_TEXT_MAX} ky tu / {NOTICE_LINES_MAX} dong"}, 400)
    raw = b.get("games")
    if not isinstance(raw, list) or not raw or len(raw) > len(NOTICE_GAMES) + 1:
        return _json({"ok": False, "loi": "chua chon game nhan thong bao"}, 400)
    games = []
    for g in raw:
        g = g.strip().lower() if isinstance(g, str) else ""
        if g != "all" and g not in NOTICE_GAMES:
            return _json({"ok": False, "loi": "game khong hop le"}, 400)
        if g not in games:
            games.append(g)
    if "all" in games:
        games = ["all"]
    x, y = _nt_num(b.get("x"), 0, 100, True), _nt_num(b.get("y"), 0, 100, True)
    size, dur = _nt_num(b.get("size"), NOTICE_SIZE_MIN, NOTICE_SIZE_MAX), _nt_num(b.get("dur"), NOTICE_DUR_MIN, NOTICE_DUR_MAX)
    if x is None or y is None:
        return _json({"ok": False, "loi": "vi tri khong hop le"}, 400)
    if size is None:
        return _json({"ok": False, "loi": f"co chu tu {NOTICE_SIZE_MIN} den {NOTICE_SIZE_MAX} px"}, 400)
    if dur is None:
        return _json({"ok": False, "loi": f"thoi gian giu tu {NOTICE_DUR_MIN} giay den {NOTICE_DUR_MAX // 86400} ngay"}, 400)
    now = int(time.time())
    try:
        with _nt_lock:                                    # đọc lại từ file ngay trong khóa (không dùng cache) rồi ghi -> không mất thông báo của lần gửi khác
            items = [it for it in _nt_read(force=True) if it["exp"] > now]
            if len(items) >= NOTICE_MAX_ACTIVE:
                return _json({"ok": False, "loi": f"dang co {len(items)} thong bao chay cung luc (toi da {NOTICE_MAX_ACTIVE}) — go bot roi gui tiep"}, 409)
            it = {"id": secrets.token_hex(6), "text": text, "games": games, "x": round(float(x), 2), "y": round(float(y), 2),
                  "size": int(size), "t": now, "exp": now + int(dur), "by": s["n"]}
            items.append(it)
            _nt_write(items)
    except OSError as e:
        return _json({"ok": False, "loi": f"khong ghi duoc file thong bao: {e}"}, 500)
    _audit("notice_send", by=s["n"], id=it["id"], games=games, dur=int(dur), text=text[:60])
    return _json({"ok": True, "item": dict(it, con_lai=int(dur))})


@app.route("/api/admin/notice/delete", methods=["POST"])
def api_admin_notice_delete():
    """Gỡ thông báo khỏi màn hình tool. CHỈ admin chính. Body: {"id": "..."} hoặc {"all": true}."""
    s, err = _nt_need_main()
    if err:
        return err
    b = request.get_json(silent=True)
    if not isinstance(b, dict):
        return _json({"ok": False, "loi": "du lieu gui len khong hop le"}, 400)
    now = int(time.time())
    nid = b.get("id")
    if b.get("all") is not True and not (isinstance(nid, str) and _NT_ID_RE.fullmatch(nid)):
        return _json({"ok": False, "loi": 'can {"id": "..."} hoac {"all": true}'}, 400)
    try:
        with _nt_lock:
            cur = [it for it in _nt_read(force=True) if it["exp"] > now]
            keep = [] if b.get("all") is True else [it for it in cur if it["id"] != nid]
            _nt_write(keep)
    except OSError as e:
        return _json({"ok": False, "loi": f"khong ghi duoc file thong bao: {e}"}, 500)
    _audit("notice_delete", by=s["n"], id=("all" if b.get("all") is True else nid), da_go=len(cur) - len(keep))
    return _json({"ok": True, "da_go": len(cur) - len(keep)})


_PANEL_ONLY = {"/api/ips", "/api/history/clear", "/api/history/regrade", "/api/history/wipe"}   # CHỈ panel đã duyệt / admin chính — key khách KHÔNG bao giờ được gọi


@app.before_request
def _gate_key():
    """Cổng cho endpoint dữ liệu.
    1) Admin chính (X-Admin-Token + chữ ký HMAC) -> panel=True (được ?detail=1, mọi trường).
    2) _PANEL_ONLY (ips / history clear·regrade·wipe): ngoài (1) -> 403, key khách không được đụng.
    3) Còn lại cần key người dùng hợp lệ + HWID (KEY_GATE_API) và bị giới hạn tốc độ theo IP / key / số lần sai key."""
    p = request.path
    if request.method == "OPTIONS" or p not in _GATED_EXACT:
        return None
    ip = client_ip()
    ua = request.headers.get("User-Agent", "")
    hw, alts, hfresh = req_hw_ids()
    panel = False
    if request.headers.get("X-Admin-Token"):
        _s = _tok_check()
        if _s and _s["r"] == "main":
            panel = True
    if panel:
        if not _rate_ok(f"pn:{hw or ip}", RATE_PANEL):
            return _too_many()
        flask_g.key_game = "all"                        # admin chính vào cả 2 bàn LC, không cần key
        flask_g.panel = True
        return None
    if p in _PANEL_ONLY:
        abort(404)                                      # key khách gọi endpoint chỉ-panel -> 404 như đường không tồn tại
    if not KEY_GATE_API and p not in OFFSRV_PATHS:      # SUNVIW_GATE_API=0 chỉ nới các endpoint phụ — endpoint DỰ ĐOÁN luôn đòi key do admin tạo (không có chuyện dùng free)
        return None
    if not _rate_ok(f"ip:{ip}", RATE_IP):
        return _too_many()
    k = request.headers.get("X-User-Key", "")
    if not k:
        k = request.args.get("key", "")
    nk = _norm_key(k)
    if nk and not _rate_ok(f"key:{nk}", RATE_TOOL_KEY):
        return _too_many()
    rec, err, _, kg = _check_user_key(k, hw, ip, ua, alts, hfresh, _path_game(p))
    if rec:
        flask_g.key_game = kg                           # game của key
        flask_g.key_ok = True                           # _view_guard trong view đọc cờ này (key đã được xác thực)
        return None
    if err.startswith(WRONG_GAME_MSG):                 # key hợp lệ nhưng thuộc game khác
        return _json({"ok": False, "sai_game": True, "game_can": kg, "game": _path_game(p), "loi": err}, 403)
    if not _rate_ok(f"bad:{ip}", RATE_BADKEY):          # dò key / thử bừa: quá RATE_BADKEY lần sai / phút -> 429
        return _too_many("qua nhieu lan sai key, thu lai sau", 60)
    hint = " (gui header X-User-Key)" if err in ("thieu key", "key khong hop le") else ""
    return _json({"ok": False, "can_key": True, "dev_locked": err.startswith("Key đã đủ"), "loi": err + hint}, 401)


@app.route("/api/key/check", methods=["GET", "POST"])
def api_key_check():
    """Tool / panel xác thực key người dùng + gắn thiết bị: POST {"key": "...", "hwid": "..."} hoặc GET ?key=...&hwid=... (hoặc header X-User-Key / X-HWID)."""
    ip = client_ip()
    w = _rl_wait(ip)
    if w:
        return _json({"ok": False, "loi": f"nhap sai qua nhieu, thu lai sau {w}s"}, 429)
    if not _rate_ok(f"kc:{ip}", 30):
        return _too_many()
    b = request.get_json(silent=True) or {}
    k = b.get("key") or request.headers.get("X-User-Key") or request.args.get("key", "")
    hw, alts, hfresh = req_hw_ids(b)
    gm = str(b.get("game") or request.args.get("game") or "").strip().lower()    # (tuỳ chọn) kiểm tra key có đúng game này không
    gm = "lc79" if gm == "tele68" else gm
    gm = gm if gm in KEY_GAMES else None
    rec, err, exists, kg = _check_user_key(k, hw, ip, request.headers.get("User-Agent", ""), alts, hfresh, gm)
    if not rec:
        if not exists:
            _rl_fail(ip)
        if err.startswith(WRONG_GAME_MSG):
            return _json({"ok": False, "sai_game": True, "game_can": kg, "loi": err}, 403)
        return _json({"ok": False, "dev_locked": err.startswith("Key đã đủ"), "loi": err}, 401)
    _rl_reset(ip)
    return _json({"ok": True, "het_han": rec["exp"], "con_lai_giay": _left_sec(rec, time.time()), "kich_hoat": rec.get("act") or None,
                  "game": kg, "game_ten": KEY_GAME_LABEL.get(kg, "Mọi game"),
                  "so_dev": len(rec.get("devs") or {}), "max_dev": _max_dev(rec)})


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




def _lc_visible(r):
    """Key hiển thị / dọn trong console LC: key admin phụ + key người dùng game LC79 (hoặc key cũ chưa gán game). Key game khác (nếu copy file key cũ sang) bị ẩn, không đụng tới."""
    if r.get("type") != "user":
        return True
    return _key_game(r) in ("lc79", "all")


ADMIN_CSP = ("default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; "
             "connect-src 'self'; img-src data:; base-uri 'none'; object-src 'none'; frame-ancestors 'none'; form-action 'none'")


@app.route("/api/admin")
def api_admin_page():
    resp = Response(ADMIN_HTML, content_type="text/html; charset=utf-8")
    resp.headers["Content-Security-Policy"] = ADMIN_CSP
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
    if not _rate_ok(f"adm-ip:{ip}", 20) or not _rate_ok("adm-all", 1200):      # PBKDF2 200k vòng / lần -> chặn dội login làm cạn CPU (theo IP + toàn cục)
        return _json({"ok": False, "kind": "locked", "loi": "Quá nhiều lần đăng nhập, thử lại sau ít phút."}, 429)
    b = request.get_json(silent=True) or {}
    raw = str(b.get("key") or b.get("password") or "")[:128]
    k = _norm_key(raw)
    hw, alts, hfresh = req_hw_ids(b)
    ua = request.headers.get("User-Agent", "")
    now = int(time.time())
    with _kv_lock:
        d = _kv_load()
        rec = d["keys"].get(k) if k else None
        if rec and rec.get("type") != "sub":             # key người dùng KHÔNG được lộ là "có thật": phản hồi y hệt key không tồn tại
            rec = None
        if rec:                                          # key admin phụ
            if _is_expired(rec, now):
                return _json({"ok": False, "kind": "sub", "loi": "Key này đã hết hạn."}, 403)
            if not hw:
                return _json({"ok": False, "kind": "sub", "loi": "Thiếu mã thiết bị (HWID) — hãy mở trang admin bằng trình duyệt, hoặc tool phải gửi header X-HWID."}, 400)
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
            if _activate(rec, now):                      # đăng nhập thành công lần đầu -> bắt đầu tính hạn key admin phụ
                ch = True
            if ch or fresh:
                try:
                    _kv_save(d)
                except OSError as e:
                    return _json({"ok": False, "kind": "sub", "loi": f"Không ghi được file key: {e}"}, 500)
            name = rec["owner"]
            _rl_reset(ip)
            return _json({"ok": True, "kind": "sub", "role": "sub", "name": name, "dev": len(rec.get("devs") or {}), "max_dev": _max_dev(rec),
                          **_tok_pair("sub", name, k, hw)})
    if raw and ADMIN_PASS_HASH and hmac.compare_digest(_pw_hash(raw), ADMIN_PASS_HASH):   # không phải key trong file -> thử mật khẩu admin chính
        _rl_reset(ip)
        _audit("login_main_ok")
        return _json({"ok": True, "kind": "main", "role": "main", "name": ADMIN_MAIN_NAME, **_tok_pair("main", ADMIN_MAIN_NAME)})
    _rl_fail(ip)
    _audit("login_fail")
    return _json({"ok": False, "kind": "none", "loi": "Không có key nào khớp (hoặc sai mật khẩu admin chính)."}, 403)


@app.route("/api/admin/logout", methods=["POST"])
def api_admin_logout():
    s = _tok_check()
    if s:
        with _sess_lock:
            _sess.pop(s["sh"], None)
        _audit("logout", role=s["r"])
    return _json({"ok": True})


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
        if not _lc_visible(r) or (s["r"] != "main" and not _own_user_key(s, r)):
            continue                                    # admin phụ chỉ thấy key người dùng do chính mình tạo
        devs = r.get("devs") if isinstance(r.get("devs"), dict) else {}
        tb = sorted(({"hw": h, "lan_dau": v.get("first"), "gan_nhat": v.get("last"), "ip": v.get("ip"), "ua": v.get("ua", "")} for h, v in devs.items()),
                    key=lambda x: -(x["gan_nhat"] or 0))
        act = _activated(r)
        rows.append({"key": k, "loai": r.get("type"), "nguoi_tao": r.get("by_name"), "tao_luc": r.get("created"), "het_han": (r["exp"] if act else None),
                     "con_lai": _left_sec(r, now), "het": _is_expired(r, now), "ngay": r.get("days"), "ghi_chu": r.get("note", ""), "cong_gio": _bonus(r),
                     "kich_hoat": act, "kich_hoat_luc": (r.get("act") or None),               # kich_hoat=False: chưa ai dùng -> hạn chưa chạy
                     "dung_boi": r.get("owner"), "da_tao": made.get(r.get("owner"), 0) if r.get("type") == "sub" else None,
                     "max_dev": _max_dev(r), "so_dev": len(devs), "dung_luc": r.get("last"), "ip_cuoi": r.get("last_ip"), "thiet_bi": tb,
                     "game": _key_game(r) if r.get("type") == "user" else None,                                   # sun | hit | all (key cũ chưa gán game)
                     "game_cu": r.get("type") == "user" and str(r.get("game") or "").lower() not in KEY_GAMES + _KEY_DEAD_GAMES})   # True = key tạo trước khi có chia game
    rows.sort(key=lambda x: -(x["tao_luc"] or 0))
    return _json({"ok": True, "role": s["r"], "name": s["n"], "ngay": list(KEY_DAYS), "so_tb": list(KEY_DEV_OPTIONS),
                  "games": [{"id": g, "ten": KEY_GAME_LABEL[g]} for g in KEY_CREATE_GAMES], "keys": rows})


@app.route("/api/admin/revenue")
def api_admin_revenue():
    """Doanh thu tự tính theo giá KEY_PRICE khi key được kích hoạt (Sun · Hit · LC79): HÔM NAY (reset 00:00 giờ VN) / TUẦN NÀY (reset 00:00 thứ Hai) / 30 ngày. CHỈ ADMIN CHÍNH — admin phụ và key người dùng đều bị từ chối."""
    s, err = _need_admin()
    if err:
        return err
    if s["r"] != "main":
        return _json({"ok": False, "loi": "chi admin chinh moi xem duoc doanh thu"}, 403)
    now = int(time.time())
    with _kv_lock:
        d = _kv_load()
    return _json({"ok": True, "don_vi": "VND", "bang_gia": {str(k): v for k, v in sorted(KEY_PRICE.items())},
                  "games": [{"id": g, "ten": KEY_GAME_LABEL[g]} for g in KEY_GAMES], "doanh_thu": _revenue_calc(d, now)})


@app.route("/api/admin/keys/create", methods=["POST"])
def api_admin_keys_create():
    s, err = _need_admin()
    if err:
        return err
    b = request.get_json(silent=True) or {}
    kind = "sub" if b.get("type") == "sub" else "user"
    if kind == "sub" and s["r"] != "main":
        return _json({"ok": False, "loi": "chi admin chinh moi tao duoc key admin phu"}, 403)
    game = str(b.get("game") or "").strip().lower()
    game = "lc79" if game == "tele68" else game
    if kind == "user" and game not in KEY_CREATE_GAMES:       # key người dùng PHẢI chọn đúng 1 game (ở server này chỉ lc79)
        return _json({"ok": False, "loi": "game cua key phai la lc79"}, 400)
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
    bonus = _parse_dur(b, "bonus_amount", "bonus_unit", "bonus_hours")      # tặng thêm thời gian ngay lúc tạo (cộng vào hạn khi key kích hoạt)
    if (b.get("bonus_amount") or b.get("bonus_hours")) and not bonus:
        return _json({"ok": False, "loi": "thoi gian tang them khong hop le"}, 400)
    now = int(time.time())
    with _kv_lock:
        d = _kv_load()
        if len(d["keys"]) + cnt > KEY_MAX_TOTAL:
            return _json({"ok": False, "loi": "day file key, xoa bot key het han"}, 400)
        made = []
        for _ in range(cnt):
            k = _new_key("AD" if kind == "sub" else KEY_PREFIX[game], d["keys"])
            d["keys"][k] = {"type": kind, "by": s["r"], "by_name": s["n"], "created": now, "exp": (0 if KEY_START_ON_ACTIVATE else now + days * 86400 + bonus),
                            "days": days, "note": note, "owner": None, "max_dev": mdev, "devs": {}}
            if bonus:
                d["keys"][k]["bonus"] = bonus
            if KEY_START_ON_ACTIVATE:
                d["keys"][k]["act"] = 0                  # 0 = CHƯA KÍCH HOẠT: hạn (exp) chỉ được tính khi key được dùng thành công lần đầu
            if kind == "user":
                d["keys"][k]["game"] = game
            made.append(k)
        try:
            _kv_save(d)
        except OSError as e:
            return _json({"ok": False, "loi": f"khong ghi duoc file key: {e}"}, 500)
    return _json({"ok": True, "keys": made, "het_han": (None if KEY_START_ON_ACTIVATE else now + days * 86400), "tinh_han_tu_kich_hoat": KEY_START_ON_ACTIVATE, "ngay": days, "max_dev": mdev, "game": game if kind == "user" else None})


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
            dead = [k for k, r in keys.items() if _is_expired(r, now) and _lc_visible(r)]
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


@app.route("/api/admin/keys/add-time", methods=["POST"])
def api_admin_keys_add_time():
    """CỘNG GIỜ cho key: {"key": "..."} hoặc {"keys": [...]} + {"amount": N, "unit": "hour"|"day"|"week"|"month"} (tháng = 30 ngày; "hours": N vẫn nhận).
    Admin chính: mọi key (kể cả key admin phụ) · admin phụ: key người dùng do chính mình tạo. Key đã hết hạn được tính lại từ bây giờ.
    Key chưa kích hoạt: giờ cộng được giữ lại và áp dụng khi key kích hoạt. Không đổi doanh thu (giá đã chốt lúc kích hoạt)."""
    s, err = _need_admin()
    if err:
        return err
    b = request.get_json(silent=True) or {}
    if b.get("amount") is None and b.get("hours") is None:
        b = dict(b, hours=1)
    secs = _parse_dur(b)
    if not secs:
        return _json({"ok": False, "loi": f"thoi gian khong hop le (so nguyen duong + don vi hour|day|week|month, toi da {ADD_MAX_SEC // 86400} ngay moi lan)"}, 400)
    lst = b.get("keys") if isinstance(b.get("keys"), list) else [b.get("key")]
    want = list(dict.fromkeys(x for x in (_norm_key(v) for v in lst[:KEY_MAX_TOTAL]) if x))
    if not want:
        return _json({"ok": False, "loi": "chua chon key nao"}, 400)
    now = int(time.time())
    out, skipped = {}, 0
    with _kv_lock:
        d = _kv_load()
        for k in want:
            r = d["keys"].get(k)
            if not r or not _own_user_key(s, r):
                skipped += 1
                continue
            if _bonus(r) + secs > BONUS_MAX_SEC:
                skipped += 1
                continue
            _add_time(r, secs, now)
            act = _activated(r)
            out[k] = {"het_han": (int(r["exp"]) if act else None), "con_lai": _left_sec(r, now), "het": _is_expired(r, now), "kich_hoat": act, "cong_gio": _bonus(r)}
        if not out:
            return _json({"ok": False, "loi": "khong cong gio duoc (chi cong cho key do ban tao)"}, 403 if skipped else 404)
        try:
            _kv_save(d)
        except OSError as e:
            return _json({"ok": False, "loi": f"khong ghi duoc file key: {e}"}, 500)
    _audit("add_time", role=s["r"], n=len(out), giay=secs)
    return _json({"ok": True, "da_cong": len(out), "bo_qua": skipped, "giay": secs, "ket_qua": out})


def _need_main():
    s, err = _need_admin()
    if err:
        return None, err
    if s["r"] != "main":
        return None, _json({"ok": False, "loi": "chi admin chinh moi duyet duoc thiet bi vao panel"}, 403)
    return s, None


def _hist_n():
    """?hist=N -> trả thêm lich_su (N ván đúng/sai gần nhất, mới -> cũ). 0 / không truyền = không trả."""
    try:
        return max(0, min(int(request.args.get("hist", 0)), HIST_MAX if _is_panel() else min(HIST_MAX, TOOL_HIST_MAX)))
    except ValueError:
        return 0



@app.route("/api/ips")
def api_ips():
    """Danh sách IP đang dùng + đã từng dùng (tab IP của panel). Có SUNVIW_ADMIN_KEY thì cần header X-Admin-Key hoặc ?key=."""
    if IP_ADMIN_KEY:
        k = request.headers.get("X-Admin-Key", "")          # chỉ header (không để key trên URL -> khỏi lọt vào log / Referer)
        if not hmac.compare_digest(str(k).encode("utf-8"), IP_ADMIN_KEY.encode("utf-8")):
            return _json({"ok": False, "khoa": True, "loi": "can admin key (header X-Admin-Key hoac ?key=)"}, 403)
    return _json(ip_snapshot(client_ip()))


_TOOL_OUT_KEYS = ("ok", "phien", "du_doan", "do_tin_cay", "phien_truoc", "xuc_xac", "tong", "ket_qua_truoc", "tool_dung_sai_10_van", "stale", "cap_nhat", "game", "ban", "ten_ban")
if _env_bool("SUNVIW_TOOL_SHOW_WRN", False):         # mặc định ẨN so_van_wr (= cỡ cửa sổ WR, tham số thuật toán). Tool cũ cần trường này -> đặt =1
    _TOOL_OUT_KEYS = _TOOL_OUT_KEYS + ("so_van_wr",)
_TOOL_HIST_KEYS = ("phien", "du_doan", "ket_qua", "tong", "dung")


def _tool_view(out):
    """Danh sách trắng cho tool khách (key người dùng): chỉ phần đã công bố trong tài liệu API; mọi thứ nội bộ bị loại."""
    o = {k: out[k] for k in _TOOL_OUT_KEYS if k in out}
    if isinstance(o.get("do_tin_cay"), (int, float)):
        o["do_tin_cay"] = int(round(o["do_tin_cay"] / 5.0) * 5)      # làm tròn 5% -> không dùng để dò ngược WR từng logic
    if "lich_su" in out:
        o["lich_su"] = [{k: r.get(k) for k in _TOOL_HIST_KEYS} for r in out["lich_su"]]
    return o


def _predict_out(res, err, upd, game, hc_key, cfg, extra=None):
    """JSON dự đoán của 1 bàn LC. hc_key = khoá mốc xóa lịch sử · cfg = config của bàn đó."""
    out = dict(res["base"])
    out["game"] = game
    if extra:
        out.update(extra)
    out["stale"] = bool(err)
    if err:
        out["loi"] = err
    out["cap_nhat"] = upd
    if offsrv_table_off(hc_key):
        out["off_server"] = True                     # chỉ xuất hiện khi bàn này OFF SERVER (lúc đó chỉ panel / admin mới nhận được JSON này) -> panel hiện badge
    hist_rows, detail = res["hist"], res["detail"]
    hide = hist_hidden_upto(hc_key)               # đã bấm "Xóa lịch sử" -> chỉ ẩn khỏi phần hiển thị; WR / AF / vote logic vẫn đọc đủ dữ liệu cũ
    if hide:
        hist_rows = [r for r in hist_rows if r["phien"] > hide]
        out["tool_dung_sai_10_van"] = _acc_rows(hist_rows, cfg.EVAL_WINDOW)
        w = hist_rows[:cfg.WR_WINDOW]
        detail = dict(detail, tool_dung_sai_15_van={"dung": sum(1 for r in w if r["dung"]), "tong": len(w)})
    n = _hist_n()
    if n:
        out["lich_su"] = hist_rows[:n]
    if _is_panel():                              # admin chính: đủ trường + ?detail=1
        if request.args.get("detail") in ("1", "true", "yes"):
            out["chi_tiet"] = detail
        return out
    return _tool_view(out)                       # tool khách: KHÔNG chi_tiet, KHÔNG trạng thái AF / bẻ / chế độ / WR từng logic / lỗi upstream


def _lc_predict(tb):
    """Handler chung của 2 bàn LC (LC MD5 + LC HŨ)."""
    g = _view_guard(tb.key)                       # lớp phòng thủ nằm TRONG view: key / đúng bàn / bàn không OFF (xem khối OFF SERVER)
    if g is not None:
        return g
    ensure_poller()
    if not tb.active:
        return _json({"ok": False, "game": tb.game, "ban": tb.key, "loi": _pub_err("ban dang tat (LC_ENABLED=0 / ENABLED=False)", "ban dang tat")}, 503)
    with tb.slock:
        have = tb.state["result"] is not None
    if not have:                                  # request đầu tiên, poller chưa kịp quét xong
        try:
            tb.refresh()
        except Exception as e:  # noqa: BLE001
            with tb.slock:
                tb.state["error"] = f"{type(e).__name__}: {e}"
    with tb.slock:
        res, err, upd = tb.state["result"], tb.state["error"], tb.state["updated"]
    if res is None:
        return _json({"ok": False, "game": tb.game, "ban": tb.key,
                      "loi": _pub_err(err or "dang cho phien dau tien tu API LC (can it nhat 1 phien co ket qua)", "dang cho du lieu")}, 503)
    return _json(_predict_out(res, err, upd, tb.game, tb.key, tb.cfg, {"ban": tb.key, "ten_ban": tb.label}))


@app.route("/api/predictlcmd5")
@app.route("/api/predicttele68txmd5")          # tên cũ (alias) — tool đang gọi tên cũ vẫn chạy
def api_predict_lc_md5():
    """[LC · MD5] — config riêng LC_MD5_CFG · data riêng tele68_txmd5.json · nguồn: list ~105 phiên, chỉ lưu thêm phiên chưa có."""
    return _lc_predict(LC_TABLES["lcmd5"])


@app.route("/api/predictlchu")
def api_predict_lc_hu():
    """[LC · HŨ] — config riêng LC_HU_CFG · data riêng lc_hu.json · nguồn: https://wtx.tele68.com/v1/tx/sessions (cùng định dạng list với LC MD5)."""
    return _lc_predict(LC_TABLES["lchu"])


_HIST_GAMES = {"lcmd5": {"lcmd5"}, "lchu": {"lchu"}, "lc": {"lcmd5", "lchu"}, "lc79": {"lcmd5", "lchu"}, "tele68txmd5": {"lcmd5"}, "tele68": {"lcmd5"}, "all": {"lcmd5", "lchu"}}


def _hist_want(b):
    """Đọc {"game": ...} của 3 endpoint lịch sử -> (tập bàn được thao tác, response lỗi | None). Chỉ admin chính tới được đây (_PANEL_ONLY), vẫn kiểm theo game của key cho chắc."""
    g = str(b.get("game") or "").strip().lower()
    if g not in _HIST_GAMES:
        return None, _json({"ok": False, "loi": 'game phai la "lcmd5", "lchu", "lc" hoac "all"'}, 400)
    allow = _key_tables(getattr(flask_g, "key_game", "all"))
    want = set(_HIST_GAMES[g])
    if not (want & allow):
        return None, _json({"ok": False, "sai_game": True, "loi": "key cua ban khong thuoc game nay"}, 403)
    return want & allow, None


@app.route("/api/history/clear", methods=["POST"])
def api_history_clear():
    """Xóa LỊCH SỬ DỰ ĐOÁN hiển thị: {"game": "lcmd5" | "lchu" | "lc" | "all"}. Chỉ đặt mốc ẩn (xem khối CONFIG XÓA LỊCH SỬ) —
    KHÔNG xóa dữ liệu nào khác và KHÔNG ảnh hưởng logic / WR / AF dự đoán. Trả {"ok":true,"da_xoa":{"lcmd5":N}} (N = số ván vừa ẩn)."""
    if not HIST_CLEAR_ENABLED:
        return _json({"ok": False, "loi": "tinh nang xoa lich su dang tat (SUNVIW_HIST_CLEAR=0)"}, 403)
    ensure_poller()
    want, err = _hist_want(request.get_json(silent=True) or {})
    if err:
        return err
    done = {}
    for key, tb in LC_TABLES.items():
        if key in want:
            with tb.slock:
                res = tb.state["result"]
            rows = res["hist"] if res else []             # mới -> cũ: ván đầu = ván đã chấm mới nhất đang hiển thị
            hide = hist_hidden_upto(key)
            shown = [r for r in rows if r["phien"] > hide]
            if shown:
                hist_clear(key, shown[0]["phien"])
            done[key] = len(shown)
    return _json({"ok": True, "da_xoa": done})


@app.route("/api/history/regrade", methods=["POST"])
def api_history_regrade():
    """TÍNH LẠI đúng/sai của TOÀN BỘ ván đã lưu theo CONFIG HIỆN TẠI: {"game": "lcmd5" | "lchu" | "lc" | "all"}.
    Dùng khi vừa đổi config (ngưỡng AF · bẻ final · WR...) rồi khởi động lại: lịch sử vẫn giữ, đúng/sai được chấm lại bằng config mới ngay. Dùng votes đã lưu nên nhanh. Không đụng mốc "Xóa lịch sử"."""
    ensure_poller()
    want, err = _hist_want(request.get_json(silent=True) or {})
    if err:
        return err
    done = {}
    try:
        for key, tb in LC_TABLES.items():
            if key in want and tb.active:
                done[key] = tb.regrade()
    except Exception as e:  # noqa: BLE001
        return _err500(e, request.path)
    return _json({"ok": True, "ket_qua": done})


@app.route("/api/history/wipe", methods=["POST"])
def api_history_wipe():
    """XÓA SẠCH DATA của bàn: {"game": "lcmd5" | "lchu" | "lc" | "all", "confirm": true}. Khác "Xóa lịch sử" (chỉ ẩn): xóa thật lịch sử xúc xắc + ván đã chấm + mốc ẩn,
    rồi tool đếm lại từ đầu (WR / AF cũng bắt đầu lại). Bắt buộc "confirm": true. Không hoàn tác được."""
    if not HIST_CLEAR_ENABLED:
        return _json({"ok": False, "loi": "tinh nang xoa dang tat (SUNVIW_HIST_CLEAR=0)"}, 403)
    ensure_poller()
    b = request.get_json(silent=True) or {}
    if b.get("confirm") is not True:
        return _json({"ok": False, "loi": 'can {"confirm": true}'}, 400)
    want, err = _hist_want(b)
    if err:
        return err
    done = {}
    try:
        for key, tb in LC_TABLES.items():
            if key in want:
                done[key] = tb.wipe()
    except Exception as e:  # noqa: BLE001
        return _err500(e, request.path)
    return _json({"ok": True, "da_xoa": done})


@app.route("/health")
def health_public():
    """Công khai (healthcheck / uptime monitor): CHỈ báo sống. Không lộ logic, cấu hình, đường dẫn, upstream, dự đoán chờ."""
    ensure_poller()
    return _json({"ok": True})


def _scrub_pub(o):
    """Ẩn URL nguồn dữ liệu + đường dẫn file khỏi dữ liệu chẩn đoán trả ra (không lộ nơi lưu / nguồn kể cả với admin)."""
    if isinstance(o, dict):
        return {k: _scrub_pub(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_scrub_pub(v) for v in o]
    if isinstance(o, str):
        o = re.sub(r"https?://\S+", "[da an]", o)
        return o.replace(DATA_DIR, "<data>") if DATA_DIR else o
    return o


@app.route("/api/admin/health")
def health():
    """Health ĐẦY ĐỦ (bộ logic, ngưỡng AF, config bàn, nguồn, file) — CHỈ admin chính."""
    _s, _e = _need_main()
    if _e:
        return _e
    ensure_poller()
    s = dict(bo_logic=SUN_NAMES, hist_keep=HIST_KEEP, persist_keep=PERSIST_KEEP,
             xoa_lich_su=dict(bat=HIST_CLEAR_ENABLED, lcmd5_an_den_phien=hist_hidden_upto("lcmd5"), lchu_an_den_phien=hist_hidden_upto("lchu")),
             ips=ip_health(), off_server={k: v["off"] for k, v in offsrv_state()["tables"].items()}, tu_kiem_tra_bao_mat=_SELFCHECK or "ok",
             luu_tru=dict(thu_muc=DATA_DIR, ben=DATA_PERSISTENT, tren_railway=ON_RAILWAY, file_key=KEYS_PATH, key_tinh_han_tu_kich_hoat=KEY_START_ON_ACTIVATE,
                          khoi_dong_dau=BOOT_INFO.get("first"), so_lan_khoi_dong=BOOT_INFO.get("count"),
                          canh_bao=(None if DATA_PERSISTENT else "Dang chay tren Railway nhung CHUA co Volume -> key / lich su game se MAT sau moi lan deploy. Gan Volume (mount path /data) cho service.")))
    s["lc79"] = {"bat": LC_ENABLED, "ban": {k: tb.health() for k, tb in LC_TABLES.items()}}
    return _json(_scrub_pub(s))


# ═══════════════════════════════════════════════════════════════════════════
#  🖥  TRANG TẠO KEY TẠM (thay trang admin gốc) — chỉ phục vụ ở đường bí mật /<ADMIN_SLUG>
# ═══════════════════════════════════════════════════════════════════════════
ADMIN_HTML = r"""<!doctype html>
<html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="robots" content="noindex,nofollow">
<title>LC79 · Quản lý key</title>
<style>
:root{--bg:#f1f3f8;--pn:#fff;--ink:#12141c;--mu:#666e84;--ln:#dde1ec;--ac:#2540ff;--on:#fff;--ok:#0c9a6b;--wa:#c97a00;--no:#dc3550;color-scheme:light}
@media(prefers-color-scheme:dark){:root{--bg:#0d0f17;--pn:#161a26;--ink:#eef0fa;--mu:#8f97b3;--ln:#272c42;--ac:#8d9cff;--on:#0d0f17;--ok:#3ccf9c;--wa:#f0a63a;--no:#ff6a80;color-scheme:dark}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:980px;margin:0 auto;padding:16px 14px 80px}
h1{font-size:19px;margin:6px 0 14px;display:flex;align-items:center;gap:10px}
h1 span{flex:1}
h2{font-size:15px;margin:0 0 10px}
.cd{background:var(--pn);border:1px solid var(--ln);border-radius:14px;padding:14px;margin-bottom:12px}
.row{display:flex;gap:8px;flex-wrap:wrap;align-items:flex-end}
label{display:flex;flex-direction:column;gap:3px;font-size:12px;color:var(--mu)}
input,select,textarea,button{font:inherit;color:inherit}
input,select,textarea{background:var(--bg);border:1px solid var(--ln);border-radius:9px;padding:7px 9px;min-width:0}
textarea{width:100%;resize:vertical}
button{cursor:pointer;border:1px solid var(--ln);background:var(--pn);border-radius:9px;padding:7px 12px}
button:hover{border-color:var(--mu)}
button.pr{background:var(--ac);color:var(--on);border-color:var(--ac);font-weight:600}
button.dg{color:var(--no)}
button:disabled{opacity:.5;cursor:default}
.mono{font-family:ui-monospace,Menlo,Consolas,monospace}
.mu{color:var(--mu)}.s{font-size:12px}
.bd{display:inline-block;padding:1px 8px;border-radius:99px;font-size:11.5px;font-weight:600;background:var(--bg);border:1px solid var(--ln)}
.bd.ok{color:var(--ok);border-color:var(--ok)}.bd.ex{color:var(--no);border-color:var(--no)}.bd.wait{color:var(--wa);border-color:var(--wa)}
table{width:100%;border-collapse:collapse}
th,td{text-align:left;padding:7px 6px;border-bottom:1px solid var(--ln);vertical-align:top}
th{font-size:12px;color:var(--mu);font-weight:600}
.acts{display:flex;gap:5px;flex-wrap:wrap}
.acts button{padding:3px 8px;font-size:12px}
.sub td{background:var(--bg);font-size:12px}
.lo{max-width:380px;margin:12vh auto 0;display:flex;flex-direction:column;gap:10px}
#out{width:100%;min-height:70px}
#ts{position:fixed;left:0;right:0;bottom:14px;display:flex;flex-direction:column;align-items:center;gap:6px;pointer-events:none}
#ts div{background:var(--ink);color:var(--bg);padding:8px 14px;border-radius:10px;font-size:13px}
#ts div.e{background:var(--no);color:#fff}
.tb{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:10px}
.tc{border:1px solid var(--ln);border-radius:12px;padding:10px;display:flex;flex-direction:column;gap:6px}
.stat{display:flex;gap:14px;flex-wrap:wrap}.stat b{font-size:16px}
</style></head>
<body>
<main id="app"></main>
<div id="ts"></div>
<script>
/*__HWID_JS__*/
const $=s=>document.querySelector(s);
const esc=s=>String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const now=()=>Math.floor(Date.now()/1000);
const fmt=t=>t?new Date(t*1000).toLocaleString('vi-VN'):'—';
function left(s){s=Math.max(0,Math.floor(s));const d=Math.floor(s/86400),h=Math.floor(s%86400/3600),m=Math.floor(s%3600/60);return d?d+'n '+h+'g':h?h+'g '+m+'p':m+'p'}
function toast(m,bad){const e=document.createElement('div');if(bad)e.className='e';e.textContent=m;$('#ts').appendChild(e);setTimeout(()=>e.remove(),2800)}
let S=null,KEYS=[],DAYS=[1,3,7,30,60,90],DEVO=[1,2,3,5,10,20,50],LT=0,OPEN=new Set(),SEL=new Set(),FILTER='all',BUSY=false;
try{S=JSON.parse(sessionStorage.getItem('lcs')||'null')}catch(e){S=null}
const isM=()=>S&&S.role==='main';
/* ── gọi API: ký HMAC từng request (X-Ts / X-Nonce / X-Sig) giống hệt trang admin gốc ── */
const _hex=b=>[...new Uint8Array(b)].map(x=>x.toString(16).padStart(2,'0')).join('');
const _sha=async m=>_hex(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(m)));
async function _hmac(k,m){const e=new TextEncoder(),ck=await crypto.subtle.importKey('raw',e.encode(k),{name:'HMAC',hash:'SHA-256'},false,['sign']);return _hex(await crypto.subtle.sign('HMAC',ck,e.encode(m)))}
async function api(p,body){
  const s0=S,o={headers:Object.assign({'Content-Type':'application/json'},HWID_HDR)};
  if(s0)o.headers['X-Admin-Token']=s0.token;
  if(body!==undefined){o.method='POST';o.body=JSON.stringify(body)}
  if(s0&&s0.sk){try{const u=new URL(p,location.origin),ts=String(Math.floor(Date.now()/1000)),nn=_hex(crypto.getRandomValues(new Uint8Array(16)));o.headers['X-Ts']=ts;o.headers['X-Nonce']=nn;o.headers['X-Sig']=await _hmac(s0.sk,[(o.method||'GET'),u.pathname+u.search,ts,nn,await _sha(o.body||'')].join('\n'))}catch(e){return{ok:false,loi:'Trình duyệt không ký được request (cần HTTPS hoặc localhost).'}}}
  let r,j={};try{r=await fetch(p.indexOf('/api/admin')===0?ADMX+p.slice(10):p,o);j=await r.json()}catch(e){j={ok:false,loi:'Không kết nối được server'}}
  if(r&&r.status===401&&S){S=null;sessionStorage.removeItem('lcs');loginView('Phiên đã hết hạn — nhập lại.')}
  return j}
/* ── đăng nhập ── */
let NEEDUN=false;
function loginView(msg){$('#app').innerHTML=`<div class="lo cd"><h1><span>LC79 · Quản lý key</span></h1>
<div class="mu s">Nhập mật khẩu admin chính (hoặc key admin phụ).</div>
<input id="k" type="password" autocomplete="off" spellcheck="false" placeholder="Mật khẩu admin / key admin phụ" autofocus>
<input id="un" maxlength="20" placeholder="Username cho key admin phụ mới" hidden>
<button class="pr" id="go">Vào</button><div id="res" class="s"></div></div>`;
  if(msg)$('#res').textContent=msg;
  $('#go').onclick=login;$('#k').onkeydown=e=>{if(e.key==='Enter')login()}}
async function login(){
  if(BUSY)return;const k=$('#k').value.trim();if(!k){$('#res').textContent='Chưa nhập gì.';return}
  BUSY=true;$('#go').disabled=true;const body={key:k};if(NEEDUN)body.username=$('#un').value.trim();
  const j=await api('/api/admin/login',body);BUSY=false;$('#go').disabled=false;
  if(j.ok){S={token:j.token,sk:j.sk,role:j.role,name:j.name};sessionStorage.setItem('lcs',JSON.stringify(S));return boot()}
  if(j.need_username){NEEDUN=true;$('#un').hidden=false;$('#un').focus()}
  $('#res').textContent=j.loi||'Không vào được.'}
async function logout(){await api('/api/admin/logout',{});S=null;sessionStorage.removeItem('lcs');loginView()}
/* ── khung chính ── */
function shell(){
  $('#app').innerHTML=`<h1><span>LC79 · Quản lý key</span><span class="mu s" style="flex:none">${esc(S.name)} · ${S.role==='main'?'admin chính':'admin phụ'}</span><button id="lo">Thoát</button></h1>
<div class="cd"><h2>Tạo key LC (dùng được cả bàn MD5 + bàn Hũ)</h2>
<div class="row">
<label>Hạn (ngày)<select id="cd">${DAYS.map(d=>`<option value="${d}">${d} ngày</option>`).join('')}</select></label>
<label>Số thiết bị<select id="cm">${DEVO.map(d=>`<option value="${d}">${d}</option>`).join('')}</select></label>
<label>Số lượng<input id="cc" type="number" min="1" max="20" value="1" style="width:70px"></label>
<label style="flex:1;min-width:140px">Ghi chú<input id="cn" maxlength="40" placeholder="tên khách (tuỳ chọn)"></label>
<button class="pr" id="mk">Tạo key</button></div>
<div class="mu s" style="margin:8px 0 4px">Hạn chỉ bắt đầu tính từ lần dùng thành công đầu tiên. Key mới:</div>
<textarea id="out" readonly placeholder="Key vừa tạo sẽ hiện ở đây"></textarea>
<div class="row" style="margin-top:6px"><button id="cp">Copy</button></div></div>
<div class="cd"><div class="row" style="justify-content:space-between;margin-bottom:8px"><h2 style="margin:0">Danh sách key</h2>
<div class="row"><select id="fl"><option value="all">Tất cả</option><option value="live">Còn hạn</option><option value="wait">Chờ kích hoạt</option><option value="exp">Hết hạn</option></select>
<button id="rf">Tải lại</button><button id="dl" class="dg">Xóa đã chọn</button>${isM()?'<button id="dx" class="dg">Dọn key hết hạn</button>':''}</div></div>
<div style="overflow-x:auto"><table><thead><tr><th></th><th>Key</th><th>Trạng thái</th><th>Thiết bị</th><th>Dùng gần nhất</th><th></th></tr></thead><tbody id="kb"></tbody></table></div>
<div class="mu s" id="kc" style="margin-top:6px"></div></div>
${isM()?'<div class="cd" id="rv"></div><div class="cd"><h2>Bàn LC (MD5 + Hũ)</h2><div class="tb" id="tbl"></div></div><div class="cd" id="nt"></div>':''}`;
  $('#lo').onclick=logout;$('#mk').onclick=createKeys;$('#rf').onclick=()=>loadKeys();$('#dl').onclick=delSel;
  if($('#dx'))$('#dx').onclick=delExpired;
  $('#fl').onchange=e=>{FILTER=e.target.value;paintKeys()};
  $('#cp').onclick=()=>{const t=$('#out');t.select();try{document.execCommand('copy');toast('Đã copy')}catch(e){}};
  $('#kb').onclick=rowClick}
async function boot(){shell();await loadKeys();if(isM()){loadRv();loadTables();loadNotice()}}
/* ── key ── */
async function loadKeys(){const j=await api('/api/admin/keys');if(!S)return;if(j.ok){KEYS=j.keys;LT=now();DAYS=j.ngay||DAYS;DEVO=j.so_tb||DEVO;const h=new Set(KEYS.map(r=>r.key));SEL=new Set([...SEL].filter(k=>h.has(k)))}else toast(j.loi||'Lỗi tải key',1);paintKeys()}
function stOf(r){if(r.kich_hoat===false)return['wait','Chờ kích hoạt',r.con_lai];const l=Math.max(0,r.het_han-now());return l<=0?['ex','Hết hạn',0]:['ok','Còn hạn',l]}
function paintKeys(){
  const q=KEYS.filter(r=>{const s=stOf(r)[0];return FILTER==='all'||(FILTER==='live'?s!=='ex':s===FILTER)});
  $('#kc').textContent=q.length+' / '+KEYS.length+' key';
  $('#kb').innerHTML=q.map(r=>{
    const[s,l,sec]=stOf(r),dv=r.thiet_bi||[];
    let h=`<tr><td><input type="checkbox" data-sel="${esc(r.key)}"${SEL.has(r.key)?' checked':''}></td>
<td><span class="mono">${esc(r.key)}</span><div class="mu s">${r.loai==='sub'?'admin phụ'+(r.dung_boi?' · '+esc(r.dung_boi):''):'gói '+esc(r.ngay)+' ngày'}${r.ghi_chu?' · '+esc(r.ghi_chu):''}${r.cong_gio?' · +'+Math.round(r.cong_gio/3600)+'g':''}</div></td>
<td><span class="bd ${s}">${l}</span><div class="mu s">${s==='wait'?'trọn gói '+left(sec):s==='ok'?'còn '+left(sec)+' · tới '+fmt(r.het_han):''}</div></td>
<td>${r.so_dev}/${r.max_dev}</td><td class="s">${fmt(r.dung_luc)}<div class="mu">${esc(r.ip_cuoi||'')}</div></td>
<td><div class="acts"><button data-a="tb" data-k="${esc(r.key)}">Máy</button><button data-a="add" data-k="${esc(r.key)}">+1 ngày</button><button data-a="rs" data-k="${esc(r.key)}">Reset máy</button><button class="dg" data-a="del" data-k="${esc(r.key)}">Xóa</button></div></td></tr>`;
    if(OPEN.has(r.key))h+=`<tr class="sub"><td></td><td colspan="5">${dv.length?dv.map(d=>`<div>${esc(d.hw.slice(0,8))}…${esc(d.hw.slice(-4))} · gần nhất ${fmt(d.gan_nhat)} · ${esc(d.ip||'')} <span class="mu">${esc((d.ua||'').slice(0,50))}</span> <button class="dg" data-a="rmdev" data-k="${esc(r.key)}" data-h="${esc(d.hw)}" style="padding:1px 7px">Gỡ</button></div>`).join(''):'<span class="mu">Chưa gắn thiết bị nào.</span>'}</td></tr>`;
    return h}).join('')||'<tr><td colspan="6" class="mu">Chưa có key.</td></tr>'}
async function rowClick(e){
  const c=e.target;if(c.dataset&&c.dataset.sel){c.checked?SEL.add(c.dataset.sel):SEL.delete(c.dataset.sel);return}
  const a=c.dataset&&c.dataset.a;if(!a)return;const k=c.dataset.k;
  if(a==='tb'){OPEN.has(k)?OPEN.delete(k):OPEN.add(k);return paintKeys()}
  if(a==='add'){const j=await api('/api/admin/keys/add-time',{key:k,amount:1,unit:'day'});toast(j.ok?'Đã +1 ngày':j.loi||'Lỗi',!j.ok);return loadKeys()}
  if(a==='rs'){if(!confirm('Gỡ TOÀN BỘ thiết bị khỏi key này?'))return;const j=await api('/api/admin/keys/reset-dev',{key:k});toast(j.ok?'Đã gỡ '+j.da_go+' thiết bị':j.loi||'Lỗi',!j.ok);return loadKeys()}
  if(a==='rmdev'){const j=await api('/api/admin/keys/reset-dev',{key:k,hwid:c.dataset.h});toast(j.ok?'Đã gỡ thiết bị':j.loi||'Lỗi',!j.ok);return loadKeys()}
  if(a==='del'){if(!confirm('Xóa key '+k+' ?'))return;const j=await api('/api/admin/keys/delete',{key:k});toast(j.ok?'Đã xóa':j.loi||'Lỗi',!j.ok);return loadKeys()}}
async function createKeys(){
  const b=$('#mk');b.disabled=true;
  const j=await api('/api/admin/keys/create',{type:'user',game:'lc79',days:+$('#cd').value,max_dev:+$('#cm').value,count:+$('#cc').value||1,note:$('#cn').value});
  b.disabled=false;if(!j.ok)return toast(j.loi||'Không tạo được key',1);
  $('#out').value=j.keys.join('\n');toast('Đã tạo '+j.keys.length+' key');loadKeys()}
async function delSel(){
  const ks=[...SEL];if(!ks.length)return toast('Chưa chọn key nào',1);if(!confirm('Xóa '+ks.length+' key đã chọn?'))return;
  const j=await api('/api/admin/keys/delete',{keys:ks});toast(j.ok?'Đã xóa '+j.da_xoa+' key':j.loi||'Lỗi',!j.ok);SEL.clear();loadKeys()}
async function delExpired(){
  if(!confirm('Xóa mọi key đã hết hạn?'))return;const j=await api('/api/admin/keys/delete',{expired:true});toast(j.ok?'Đã xóa '+j.da_xoa+' key':j.loi||'Lỗi',!j.ok);loadKeys()}
/* ── doanh thu (admin chính) ── */
async function loadRv(){
  const j=await api('/api/admin/revenue');if(!j.ok||!$('#rv'))return;const d=j.doanh_thu,m=x=>(x.tong||0).toLocaleString('vi-VN')+' đ';
  $('#rv').innerHTML=`<h2>Doanh thu (tính khi key kích hoạt)</h2><div class="stat"><div><span class="mu s">Hôm nay</span><br><b>${m(d.ngay)}</b></div><div><span class="mu s">Tuần này</span><br><b>${m(d.tuan)}</b></div><div><span class="mu s">30 ngày</span><br><b>${m(d.thang)}</b></div></div>`}
/* ── 2 bàn LC (admin chính) ── */
async function loadTables(){
  const [h,o]=await Promise.all([api('/api/admin/health'),api('/api/admin/offserver')]);if(!S||!$('#tbl'))return;
  const tb=(h.lc79&&h.lc79.ban)||{},off={};((o&&o.tables)||[]).forEach(r=>off[r.key]=r.off);
  $('#tbl').innerHTML=Object.keys(tb).map(k=>{const t=tb[k],bad=!t.ok;
    return `<div class="tc"><div class="row" style="justify-content:space-between"><b>${esc(t.ten||k)}</b><span class="bd ${t.bat?(bad?'ex':'ok'):'wait'}">${t.bat?(bad?'lỗi nguồn':'chạy'):'tắt'}</span></div>
<div class="s mu">Phiên mới nhất: <b class="mono">${esc(t.latest||'—')}</b> · đã lưu ${t.so_phien_luu} phiên · đã chấm ${t.so_van_cham} ván</div>
<div class="s mu">Dự đoán đang chờ: <b>${t.du_doan_cho_ket_qua?esc(t.du_doan_cho_ket_qua.phien+' → '+t.du_doan_cho_ket_qua.du_doan):'—'}</b></div>
${t.error?`<div class="s" style="color:var(--no)">${esc(t.error)}</div>`:''}
<div class="acts"><button data-t="${esc(k)}" data-x="off">${off[k]?'Bật lại server':'Tắt server (OFF)'}</button><button data-t="${esc(k)}" data-x="regrade">Tính lại theo config</button><button data-t="${esc(k)}" data-x="clear">Ẩn lịch sử</button><button class="dg" data-t="${esc(k)}" data-x="wipe">Xóa data</button></div>
${off[k]?'<div class="s" style="color:var(--no)">Đang OFF: tool khách nhận 503, không có dự đoán.</div>':''}</div>`}).join('')||'<span class="mu">Không có bàn.</span>';
  $('#tbl').onclick=async e=>{const c=e.target,x=c.dataset&&c.dataset.x;if(!x)return;const t=c.dataset.t;let j;
    if(x==='off'){j=await api('/api/admin/offserver',{tables:[t],off:!off[t]})}
    else if(x==='regrade'){j=await api('/api/history/regrade',{game:t})}
    else if(x==='clear'){if(!confirm('Ẩn lịch sử hiển thị của bàn này? (không ảnh hưởng logic / WR)'))return;j=await api('/api/history/clear',{game:t})}
    else if(x==='wipe'){if(!confirm('XÓA SẠCH data bàn này (lịch sử xúc xắc + ván đã chấm)? Không hoàn tác.'))return;j=await api('/api/history/wipe',{game:t,confirm:true})}
    toast(j&&j.ok?'Xong':(j&&j.loi)||'Lỗi',!(j&&j.ok));loadTables()}}
/* ── thông báo tới tool (admin chính) ── */
async function loadNotice(){
  const j=await api('/api/admin/notice');if(!j.ok||!$('#nt'))return;const c=j.cfg;
  $('#nt').innerHTML=`<h2>Thông báo tới tool LC</h2>
<textarea id="nx" rows="2" maxlength="${c.text_max}" placeholder="Nội dung thông báo (tối đa ${c.text_max} ký tự / ${c.lines_max} dòng)"></textarea>
<div class="row" style="margin-top:6px"><label>Giữ<select id="nd"><option value="60">1 phút</option><option value="300">5 phút</option><option value="1800">30 phút</option><option value="7200">2 giờ</option><option value="86400">1 ngày</option></select></label>
<label>Cỡ chữ<input id="ns" type="number" min="${c.size[0]}" max="${c.size[1]}" value="${c.size[2]}" style="width:70px"></label>
<label>Vị trí X %<input id="nxp" type="number" min="0" max="100" value="50" style="width:70px"></label>
<label>Vị trí Y %<input id="nyp" type="number" min="0" max="100" value="10" style="width:70px"></label>
<button class="pr" id="nsend">Gửi</button><button class="dg" id="nall">Gỡ tất cả</button></div>
<div style="margin-top:8px">${j.items.map(it=>`<div class="s" style="padding:4px 0;border-top:1px solid var(--ln)">${esc(it.text)} <span class="mu">· còn ${left(it.con_lai)}</span> <button class="dg" data-n="${esc(it.id)}" style="padding:1px 7px">Gỡ</button></div>`).join('')||'<span class="mu s">Không có thông báo đang chạy.</span>'}</div>`;
  $('#nsend').onclick=async()=>{const r=await api('/api/admin/notice/send',{games:['lc79'],text:$('#nx').value,x:+$('#nxp').value,y:+$('#nyp').value,size:+$('#ns').value,dur:+$('#nd').value});toast(r.ok?'Đã gửi':r.loi||'Lỗi',!r.ok);loadNotice()};
  $('#nall').onclick=async()=>{const r=await api('/api/admin/notice/delete',{all:true});toast(r.ok?'Đã gỡ '+r.da_go:r.loi||'Lỗi',!r.ok);loadNotice()};
  $('#nt').onclick=async e=>{const id=e.target.dataset&&e.target.dataset.n;if(!id)return;const r=await api('/api/admin/notice/delete',{id});toast(r.ok?'Đã gỡ':r.loi||'Lỗi',!r.ok);loadNotice()}}
if(S&&S.token)boot();else loginView();
</script></body></html>
"""
ADMIN_HTML = ADMIN_HTML.replace("/*__HWID_JS__*/", HWID_JS + "\nconst ADMX='/" + ADMIN_SLUG + "';")


@app.route("/")
def index():
    abort(404)                                           # gốc không lộ gì (healthcheck dùng /health)


def _sec_report():
    w = []
    if not os.environ.get("SUNVIW_MAIN_PASS"):
        w.append("SUNVIW_MAIN_PASS CHUA DAT -> dang dung mat khau TAM ngau nhien (xem dong [SEC] o tren). Dat SUNVIW_MAIN_PASS (>= 16 ky tu)")
    elif len(os.environ.get("SUNVIW_MAIN_PASS", "")) < 16:
        w.append("SUNVIW_MAIN_PASS qua ngan (< 16 ky tu)")
    if not (os.environ.get("LC_MD5_API_URL") or os.environ.get("TELE68_API_URL")) or not os.environ.get("LC_HU_API_URL"):
        w.append("LC_MD5_API_URL / LC_HU_API_URL chua dat -> URL (kem token at=) dang nam trong code")
    if IP_TRUST_PROXY and not IP_HEADER:
        w.append(f"IP client lay tu X-Forwarded-For, phan tu thu {IP_PROXY_HOPS} tinh tu cuoi (SUNVIW_PROXY_HOPS). Neu nhieu nguoi bi tinh CHUNG 1 IP (khoa nham) thi tang SUNVIW_PROXY_HOPS hoac dat SUNVIW_IP_HEADER")
    for x in w:
        print("[SEC] " + x, file=sys.stderr)


def _security_selfcheck():
    """Chạy 1 lần lúc khởi động (sau khi mọi route đã đăng ký). Trả danh sách vấn đề (rỗng = ổn):
       · route /api/predict* chưa có trong bảng OFFSRV_PATH_TABLE (không tắt server riêng được) hoặc chưa nằm trong cổng key -> TỰ VÁ vào cổng key (bắt buộc key) rồi báo.
       · endpoint trong bảng nhưng không có route / thiếu ở cổng key / thiếu _view_guard."""
    probs = []
    rules = {r.rule: r for r in app.url_map.iter_rules()}
    for p in sorted(rules):
        if p.startswith("/api/predict"):
            if p not in OFFSRV_PATH_TABLE:
                probs.append(f"route {p} giong endpoint du doan nhung CHUA co trong OFFSRV_PATH_TABLE -> chua tat server rieng duoc (da tu dua vao cong key)")
            if p not in _GATED_EXACT:
                _GATED_EXACT.add(p)
                probs.append(f"route {p} chua nam trong _GATED_EXACT -> da tu them vao cong key")
    for p, tk in OFFSRV_PATH_TABLE.items():
        if p not in rules:
            probs.append(f"OFFSRV_PATH_TABLE co {p} nhung khong co route")
            continue
        if p not in _GATED_EXACT:
            _GATED_EXACT.add(p)
            probs.append(f"{p} chua nam trong _GATED_EXACT -> da tu them vao cong key")
        if tk not in LC_TABLES:
            probs.append(f"{p} tro toi ban '{tk}' khong ton tai")
    for fn in (api_predict_lc_md5, api_predict_lc_hu):
        try:
            if "_lc_predict" not in fn.__code__.co_names:
                probs.append(f"view {fn.__name__} khong goi _lc_predict")
        except Exception:  # noqa: BLE001
            pass
    if "_view_guard" not in _lc_predict.__code__.co_names:
        probs.append("_lc_predict khong goi _view_guard")
    for x in probs:
        print("[SEC] LOI CONG: " + x, file=sys.stderr)
    return probs


_SELFCHECK = _security_selfcheck()
_sec_report()

# Chạy dưới gunicorn (Railway) thì main() không được gọi -> bật poller ngay khi import.
if __name__ != "__main__":
    ensure_poller()


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(description="LC79 SERVER (LC MD5 + LC HŨ: 13 logic chuỗi/xúc xắc/tổng/số phiên · key + HWID)")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=int(os.environ.get("PORT", 5000)))
    a = ap.parse_args()
    ensure_poller()
    if DATA_PERSISTENT:
        print(f"DATA        ->  {DATA_DIR} (BEN · khoi dong lan thu {BOOT_INFO.get('count')} · lan dau {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(BOOT_INFO.get('first') or 0))})")
    else:
        print("!" * 100)
        print(f"!! DATA        ->  {DATA_DIR} KHONG BEN: dang chay tren Railway ma CHUA gan Volume -> key, lich su game se MAT sau moi lan deploy / restart.")
        print("!!                 Cach sua: Railway -> service -> Settings -> Volumes -> New Volume -> Mount path /data -> redeploy. Code tu nhan (RAILWAY_VOLUME_MOUNT_PATH).")
        print("!" * 100)
    print(f"KEY HAN     ->  {'tinh tu LAN DUNG DAU TIEN (kich hoat)' if KEY_START_ON_ACTIVATE else 'tinh tu luc TAO key (kieu cu)'} · key cu tao truoc do giu nguyen han")
    print(f"LC API      ->  http://{a.host}:{a.port}/api/predictlcmd5 · /api/predictlchu  (can key LC79 + HWID)")
    print(f"ADMIN       ->  http://{a.host}:{a.port}/{ADMIN_SLUG}   (trang tao key tam · mat khau admin chinh {'tu env SUNVIW_MAIN_PASS' if _ENV_MAIN_PASS else 'TAM ngau nhien (xem dong [SEC])'} · can HTTPS hoac localhost de ky request)")
    print(f"IP          ->  theo doi {'BAT' if IP_TRACK_ENABLED else 'TAT'} · dang dung = co request trong {IP_ACTIVE_SEC}s · tin proxy {'BAT' if IP_TRUST_PROXY else 'TAT'} · file {IP_PATH}")
    _off = offsrv_state()["off_list"]
    print(f"OFF SERVER  ->  {('DANG OFF: ' + ', '.join(_off)) if _off else 'khong ban nao off'} · file {OFFSRV_PATH}")
    print(f"WR 300 van  ->  luu toi da {PERSIST_KEEP} van da cham · bo logic {len(SUN_NAMES)}: {' '.join(SUN_NAMES)}")
    for _tb in LC_TABLES.values():
        _c = _tb.cfg
        print(f"LC {_tb.label:<7} ->  {'BAT' if _tb.active else 'TAT'} · /api/predict{_tb.key} · quet moi {_c.POLL_SEC:g}s · file {_tb.path} · "
              f"AF {'BAT' if _c.AF_ENABLED else 'TAT'} · WR xet {_c.WR_WINDOW} van · be final {'BAT' if _c.FLIP_FINAL else 'TAT'} · config RIENG (khoi CONFIG LC)")
    app.run(host=a.host, port=a.port, threaded=True)


if __name__ == "__main__":
    main()
