# -*- coding: utf-8 -*-
"""
SUNVIW - API JSON.  SUN: 15 LOGIC DỰ ĐOÁN (SEQ15) dựa trên CHUỖI TÀI/XỈU + XÚC XẮC + TỔNG gần nhất (KHÔNG dùng MD5) · HITCLUB: 2 bàn (TX thường + TX MD5) dùng cùng bộ 15 logic

Chạy:
    pip install flask
    python sunviw_api.py                      # mặc định http://0.0.0.0:5000
    python sunviw_api.py --port 8080 --upstream https://xxx.trycloudflare.com/api/tx
    python sunviw_api.py --flip               # BẬT bẻ final của SUN (mặc định TẮT; hoặc SUNVIW_FLIP=1, hoặc sửa FLIP_FINAL_DEFAULT)
    python sunviw_api.py --wr-flip            # BẬT FLIP TRỌNG SỐ WR của SUN: ván CŨ nhất nặng nhất -> giảm dần tới ván MỚI nhất (--no-wr-flip = tắt; hoặc SUNVIW_WR_FLIP=1|0, hoặc sửa WR_FLIP_WEIGHT_DEFAULT)
    python sunviw_api.py --no-af              # TẮT AF của SUN (--af = bật · --af-low 37 / --af-high 63 = ngưỡng bẻ logic · --af-min 13 = số ván tối thiểu · --af-mode-window 7 / --af-mode-below 45 = bẻ theo WR chế độ · --af-flip / --af-no-flip = bẻ riêng AF)
                                              #           hoặc env SUNVIW_AF / SUNVIW_AF_LOW / SUNVIW_AF_HIGH / SUNVIW_AF_MIN / SUNVIW_AF_MODE_WINDOW / SUNVIW_AF_MODE_MIN / SUNVIW_AF_MODE_BELOW / SUNVIW_AF_MODE_FLIP (bước 3 bẻ chế độ, mặc định TẮT · --af-mode-flip / --af-no-mode-flip) / SUNVIW_AF_FLIP, hoặc sửa AF_*_DEFAULT ở khối "CONFIG AF"
    python sunviw_api.py --af-flip-ct         # CHỈ bẻ final của AF khi chế độ CAO/THẤP (chế độ ALL giữ nguyên; --af-no-flip-ct = tắt; hoặc SUNVIW_AF_FLIP_CT=1|0, hoặc sửa AF_FLIP_FINAL_CT_DEFAULT)
    python sunviw_api.py --af-flip-all        # CHỈ bẻ final của AF khi chế độ ALL (CAO/THẤP giữ nguyên; --af-no-flip-all = tắt; hoặc SUNVIW_AF_FLIP_ALL=1|0, hoặc sửa AF_FLIP_FINAL_ALL_DEFAULT)

Endpoint:
    GET /api/predictsun          -> [SUN] JSON dự đoán (đọc từ cache, trả về ngay). /api/predict = tên cũ, giữ để tool cũ không hỏng
    GET /api/predictsun?detail=1 -> thêm chi_tiet: vote từng logic + WR từng logic
    GET /api/predicthittxthuong  -> [HITCLUB · bàn TX THƯỜNG] JSON dự đoán, cùng cấu trúc /api/predictsun (game="hitclub", ban="hittxthuong"); cũng có ?hist=N · ?detail=1
    GET /api/predicthittxmd5     -> [HITCLUB · bàn TX MD5] như trên (ban="hittxmd5")
    ...?hist=N                   -> (mọi game) thêm lich_su: N ván đúng/sai gần nhất, mới -> cũ
    GET /api/html                -> panel HTML theo dõi Sun + Hit, đổi qua lại, chọn số ván lịch sử. CHỈ MỞ KHI ADMIN CHÍNH DUYỆT THIẾT BỊ (HWID): máy lạ thấy bảng "Đang chờ admin duyệt", được duyệt thì tự mở, KHÔNG cần key, vào cả Sun + Hit
    GET /api/panel/status        -> panel hỏi trạng thái duyệt của thiết bị này (gửi yêu cầu lần đầu): {"status": "approved" | "pending" | "denied" | "limit"} (xem khối "DUYỆT THIẾT BỊ VÀO PANEL")
    GET /api/admin/panel (+ POST /approve · /deny · /remove) -> admin CHÍNH xem + duyệt / từ chối / gỡ quyền thiết bị vào panel (mục "Duyệt thiết bị vào panel HTML" ở trang /api/admin)
    GET /health                  -> trạng thái nền của Sun + Hit
    GET /api/admin               -> trang quản trị: MỘT ô nhập key, server tự nhận diện admin chính / admin phụ / key người dùng / key không tồn tại — tạo / xóa (tích chọn nhiều key) / xem key, MỌI key gắn HWID thiết bị (1 key dùng được N thiết bị), hiện lần dùng gần nhất, KHÔNG hiện ở trang chủ (xem khối "CONFIG KEY / ADMIN")
    POST /api/key/check          -> tool xác thực + GẮN THIẾT BỊ cho key người dùng: {"key":"...","hwid":"..."} (hoặc header X-HWID) -> {"ok":true,"het_han":<epoch>,"con_lai_giay":N}
    POST /api/history/clear      -> XÓA LỊCH SỬ DỰ ĐOÁN hiển thị: {"game":"sun"|"hittxthuong"|"hittxmd5"|"hitclub"|"all"} (nút "Xóa lịch sử" ở panel /api/html). CHỈ ẩn lich_su + số liệu đúng/sai đã hiển thị bằng 1 mốc phiên (file riêng),
                                    KHÔNG xóa dữ liệu nào khác và KHÔNG ảnh hưởng các logic / WR / AF dự đoán (xem khối "CONFIG XÓA LỊCH SỬ"; tắt hẳn bằng SUNVIW_HIST_CLEAR=0)
    GET /api/ips                 -> DANH SÁCH IP đang dùng + đã từng dùng API (tab "IP" của panel đọc từ đây; có SUNVIW_ADMIN_KEY thì cần header X-Admin-Key hoặc ?key=)

JSON /api/predict:
    {
      "ok": true,
      "phien": 12346,            # phiên được dự đoán (n)
      "du_doan": "TÀI",          # TÀI | XỈU  (mặc định = final của 15 logic SUN; nếu BẬT bẻ final thì = đảo ngược final)
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


🧠 15 LOGIC CỦA SUN (SEQ15 · thuần chuỗi Tài/Xỉu + xúc xắc + tổng + số phiên, KHÔNG dùng MD5):
    Mỗi logic là một thuật toán tự học ONLINE trên lịch sử các phiên đã quét (không dùng MD5, không dùng số phiên). Mỗi ván tính lại từ lịch sử, KHÔNG nhìn trước kết quả:
        MKT2   Markov bậc 2 (2 kết quả gần nhất) + nhóm tổng ván trước · cửa sổ 250 ván
        PPM6   PPM: trộn có trọng số các bậc 1..6, tin cậy theo số mẫu · cửa sổ 250
        KNNT   k-NN mẫu 8 TỔNG gần nhất (khoảng cách L1 giữa các tổng) · 15 láng giềng · cửa sổ 150
        CT2    tỉ lệ Tài có điều kiện theo (nhóm tổng ván trước, nhóm tổng ván trước nữa) · co về 50% (m=6) · cửa sổ 250
        CMM    tỉ lệ Tài có điều kiện theo (xúc xắc nhỏ nhất, lớn nhất) của ván trước · cửa sổ 250
        CDT    tỉ lệ Tài có điều kiện theo (tổng tăng/giảm so với ván trước nữa, nhóm tổng ván trước) · cửa sổ 250
        NBMIX  Naive Bayes (3 kết quả gần nhất, nhóm tổng, xúc xắc max/min, số mặt khác nhau) · cửa sổ 250
        NBY4   Naive Bayes (4 kết quả gần nhất, chẵn/lẻ của tổng, số mặt khác nhau) · cửa sổ 250
        PAT    nhận diện cầu lặp chu kỳ 2/3/4/6 (1-1, chu kỳ 3, 2-2, 3-3): khớp trọn P+3 bước liên tiếp -> đoán tiếp theo đúng chu kỳ; không có cầu -> bỏ phiếu trắng (theo ván trước)
        EWMA   trung bình trượt mũ của TỔNG (α=0.1, nhớ ~10 ván) chia 5 nhóm; học online P(Tài | nhóm) trong 250 ván, co về 50% (m=10)
        REGIME nhịp đảo cầu: tỉ lệ đảo cầu 20 ván gần nhất chia 4 nhóm (<=35% · 35-50% · 50-65% · >65%); học online P(ván sau ĐẢO | nhóm) trong 250 ván, co về 50% (m=8) -> đảo hoặc bệt theo dữ liệu
        SESS   số phiên: Naive Bayes trên (số phiên mod 2/3/5/7/10), học online P(Tài | phiên mod m) trong 250 ván, làm mượt mạnh (a=4) · logic duy nhất nhìn SỐ PHIÊN thay vì kết quả quá khứ (cần S["p"] từ compute_all)
        LAGAC  tự tương quan độ trễ 1..16 của chuỗi Tài/Xỉu (cửa sổ = toàn bộ lịch sử đang giữ, tối đa 1500; hiện HIST_KEEP=500) + KIỂM ĐỊNH TỔNG THỂ kiểu Ljung–Box (Σz² > 26.3 = mức 95%): chỉ khi chuỗi "không ngẫu nhiên" mới bỏ phiếu theo Σ z_k × (kết quả cách k ván); không thì BỎ PHIẾU TRẮNG (xem ⚑) · bắt phụ thuộc xa (lag 7..16) mà PPM6 (bậc <= 6) không thấy
        PERIOD chu kỳ theo SỐ PHIÊN: thử phiên mod m = 2..32, chọn m có chi-bình-phương lệch mạnh nhất (ngưỡng z >= 3 đã hiệu chỉnh cho 31 phép thử), rồi dùng P(Tài | phiên mod m) co về tỉ lệ chung (m0=8); không m nào đủ ngưỡng -> BỎ PHIẾU TRẮNG · cửa sổ = toàn bộ lịch sử đang giữ, tối đa 2000 ván (⚠ với HIST_KEEP=500 chỉ bắt được ~3-13% số ván có mẫu theo phiên; cần HIST_KEEP >= 2000 mới đủ mạnh — không có mẫu thì vô hại: bỏ phiếu trắng)
        SGDLR  hồi quy logistic online (12 kết quả gần nhất + 2 tổng gần nhất + độ dài đợt, L2, 2 epoch trên 300 ván gần nhất, huấn luyện lại mỗi ván) · khác họ mô hình: tuyến tính gộp nhiều tín hiệu yếu thay vì đếm theo ngữ cảnh
    ⚙ Đã bỏ FACE · REV40 (hướng đoán đặt cứng; đo trên 11 loại chuỗi giả lập đều <= 50% khi có cấu trúc) và thêm LAGAC · PERIOD · SGDLR -> 15 logic (SỐ LẺ: đa số tất cả logic không bị hoà 7-7; các bước còn lại nếu hoà vẫn được phá bằng phiếu của logic SUN_TIE_LOGIC (mặc định PPM6, env SUNVIW_TIE_LOGIC)).
    ⚑ PHIẾU TRẮNG: LAGAC / PERIOD chỉ kích hoạt khi thấy cấu trúc có ý nghĩa thống kê (chuỗi ngẫu nhiên: LAGAC ~3% số ván, PERIOD ~0.1%). Lúc không kích hoạt, phiếu của chúng = ĐA SỐ của các logic còn lại (SUN_ABSTAIN) thay vì "theo ván trước" như các logic khác -> không biến thành 2 phiếu "copy ván trước".
    ⚠ Backtest 4 bộ x ~2.940 ván xúc xắc ngẫu nhiên: cả 6 logic mới ≈ 50% (nhiễu) · chỉ bắt được khi dữ liệu CÀI SẴN thiên lệch -> không có lợi thế trên RNG công bằng.
    Chưa đủ lịch sử cho một logic -> logic đó tạm theo kết quả ván trước. WR / AF / CAO-THẤP / bẻ final GIỮ NGUYÊN như bản trước (chỉ bỏ ZF).
    ⚠ Backtest trên data thật (457 ván) + 40 chuỗi ngẫu nhiên đối chứng: KHÔNG tìm thấy logic nào có lợi thế đứng vững ngoài mẫu -> xem báo cáo backtest đi kèm.

🔀 AF = AUTO-FLIP + CAO/THẤP (port từ SUNVIW_9logics_autoflip_auto.html) — cách chốt final của SUN (mặc định BẬT · khối "CONFIG AF"):
    Bước 1 (bẻ logic):  WR có trọng số của từng logic (cùng WR_WINDOW ván / trọng số như cách cũ của SUN). WR < AF_FLIP_LOW (37%) hoặc > AF_FLIP_HIGH (63%) -> ĐẢO phiếu logic đó
                        (WR dùng = 100 − WR khi bị bẻ). Chưa đủ AF_MIN_GAMES ván -> không bẻ, vote tất cả logic.
                        ⚙ GIỚI HẠN VÙNG BẺ (AF_FLIP_BAND, mặc định BẬT): chỉ bẻ khi WR nằm TRONG vùng THẤP 32-40% hoặc vùng CAO 60-68% (gồm đầu mút); ngoài vùng (vd 29% / 41% / 59% / 69%) KHÔNG bẻ.
                        Vùng chỉnh bằng AF_FLIP_LOW_MIN/MAX · AF_FLIP_HIGH_MIN/MAX (env SUNVIW_AF_LOW_MIN... · cờ --af-low-min...) · tắt: --af-no-band hoặc SUNVIW_AF_BAND=0 (về ngưỡng 37/63 cũ)
    Bước 2 (CAO/THẤP):  ⚙ CHỈ logic ĐÃ BỊ BẺ (WR trong vùng bẻ) mới vào nhóm CAO/THẤP; logic không bẻ mặc định ALL (không thuộc nhóm nào) — AF_GROUP_FLIPPED_ONLY (--af-no-group-flipped = tắt).
                        ⚙ Nhóm CAO/THẤP được chọn phải có >= ĐA SỐ toàn bộ logic (n//2+1 = 8/15); ít hơn -> dùng chế độ ALL — AF_GROUP_NEED_MAJORITY (--af-no-group-majority = tắt).
                        WR dùng > 50% -> nhóm CAO · < 50% -> nhóm THẤP. Nhóm nào ĐÔNG hơn thì chỉ vote trong nhóm đó (chế độ CAO / THẤP); bằng nhau -> vote tất cả (chế độ ALL).
    Bước 3 (bẻ chế độ): WR của CHẾ ĐỘ đang chạy trong AF_MODE_WINDOW (7) ván gần nhất của chế độ đó < AF_MODE_BELOW (45%) -> ĐẢO final (không theo đa số nữa);
                        từ 45% trở lên -> theo bình thường. Đang bẻ THẤP mà ván sau lên CAO thì xét lại WR của CAO. Chưa đủ AF_MODE_MIN ván của chế độ đó -> không bẻ.
                        ⛔ BƯỚC 3 ĐANG TẮT MẶC ĐỊNH (AF_MODE_FLIP_DEFAULT = False · env SUNVIW_AF_MODE_FLIP=1 / cờ --af-mode-flip để bật lại): final = kết quả sau bước 2, không đảo theo WR chế độ.
    Dữ liệu 2 chế độ: MỖI ván đã chấm lưu sẵn vote của nhóm CAO (hv) và của nhóm THẤP (lv) — cả khi tool đang chạy chế độ kia — nên WR 7 ván của cả 2 chế độ luôn có sẵn.
                      WR chế độ luôn đo trên vote GỐC (chưa bẻ chế độ) để bẻ xong WR không tăng lại rồi tắt bẻ (dao động).
    Ván do AF chốt KHÔNG bị bẻ bởi FLIP_FINAL chung (AF đã tự bẻ) — muốn bẻ riêng AF dùng AF_FLIP_FINAL (bẻ MỌI chế độ) · AF_FLIP_FINAL_CT (CHỈ bẻ khi chế độ CAO/THẤP, ALL giữ nguyên) · AF_FLIP_FINAL_ALL (CHỈ bẻ khi chế độ ALL, CAO/THẤP giữ nguyên). AF tắt (--no-af) -> quay về đúng cách cũ (WR có trọng số + nhóm THẤP/CAO + FLIP_FINAL).
    Thứ tự chốt của SUN:  AF  ->  cách cũ (khi tắt AF).   JSON thêm: "af", "che_do", "be_che_do", "du_doan_goc", "du_doan_truoc_be_che_do", "wr_che_do_hien_tai" (panel dùng để hiện đúng chế độ hiện tại); mỗi dòng lich_su có thêm "be_final" (ván đó có bị bẻ final theo cấu hình HIỆN TẠI không); ?detail=1 thêm chi_tiet.af (WR 2 chế độ, logic nào bị bẻ).

🌐 TAB IP (panel /api/html) — theo dõi ai đang gọi API:
    Mỗi request tới /api/predictsun · /api/predicthittxthuong · /api/predicthittxmd5 · /api/html được ghi lại IP của client (sau proxy Railway đọc X-Forwarded-For / X-Real-IP).
    Tab "IP" hiện: IP ĐANG DÙNG (có request trong IP_ACTIVE_SEC giây gần nhất) + IP ĐÃ TỪNG DÙNG (lưu file, còn sau khi restart) · lần đầu / gần nhất · số request · chia theo loại (sun · hit · panel) · User-Agent.
    Khối "CONFIG IP" ở gần đầu file. Nên đặt SUNVIW_ADMIN_KEY để chỉ bạn xem được danh sách IP (panel là trang công khai).

🔐 HWID (gắn key theo THIẾT BỊ, thay cho gắn theo IP mạng) — khối "CONFIG KEY / ADMIN":
    Mọi key (người dùng + admin phụ) đều gắn HWID. Mỗi key có số thiết bị tối đa (max_dev, chọn lúc tạo: 1-2-3-5-10-20-50): máy mới dùng key lần đầu tự được gắn nếu còn chỗ,
    đủ chỗ rồi thì máy khác bị chặn tới khi admin reset / gỡ thiết bị. Panel (/api/html, /api/admin) tự tạo HWID; tool tự viết gửi header X-HWID (hoặc ?hwid= / body {"hwid"}) cùng X-User-Key.
    Admin chính + admin phụ đều chọn được số thiết bị khi tạo key; admin phụ chỉ tạo được key người dùng. Trang admin hiện: số thiết bị đang gắn / tối đa · lần dùng gần nhất · từng thiết bị (có nút Gỡ)
    · tích chọn nhiều key để xóa một lượt.
    ⚑ KHÔNG BAO GIỜ chặn theo IP: đổi mạng / đổi IP không ảnh hưởng key, chỉ máy khác mới bị chặn. Mã thiết bị được giữ ổn định (lưu localStorage + cookie, dấu vân tay phần cứng không đổi theo UA / zoom / xoay màn hình),
    server học thêm mã phụ cho từng thiết bị (header X-HWID-ALT) để máy xoá dữ liệu trình duyệt vẫn được nhận lại thay vì chiếm thêm chỗ — chi tiết ở khối "CONFIG KEY / ADMIN".

🎯 HITCLUB (GAME 3 · 2 BÀN) — port từ hittxthuong.js / hittxmd5.js (khối "CONFIG HITCLUB" + phần "HITCLUB" ở giữa file):
    Bàn TX THƯỜNG (gid vgmn_100, cmd 1008 + 1003) và bàn TX MD5 (gid vgmn_101, cmd 2006): mỗi bàn một poller (mặc định 3s), tự tích lũy lịch sử xúc xắc.
    Dự đoán = bộ 15 logic SEQ15 + AF + WR có trọng số như SUN, nhưng mỗi bàn đọc CONFIG RIÊNG (HIT_TXTHUONG_CFG / HIT_TXMD5_CFG — hiện đang bằng mặc định của SUN) -> chỉnh bàn nào chỉ ảnh hưởng bàn đó.
    Data lưu RIÊNG: <DATA_DIR>/hittxthuong.json và <DATA_DIR>/hittxmd5.json (mỗi file = lịch sử xúc xắc + các ván đã chấm của bàn đó). Panel /api/html có thêm 2 tab "Hit Thường" · "Hit MD5".
    Tắt: HITCLUB=0 hoặc --no-hit. Đổi config không sửa file: biến môi trường HITTXTHUONG_<TÊN> / HITTXMD5_<TÊN> (vd. HITTXMD5_AF_ENABLED=0).

Server quét upstream nền mỗi POLL_SEC giây, chỉ tính lại khi có phiên mới -> request của HTML trả về tức thì.
"""
import argparse
import atexit
import base64
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


# ═══════════════════════════════════════════════════════════════════════════
#  ⬆  KHỐI CONFIG AF CỦA SUN NẰM NGAY ĐÂY (đầu file) — sửa mọi thông số AF ở khối này, không cần tìm xuống dưới
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
#   Bước 3  bẻ chế độ    : WR của chế độ đang chạy trong AF_MODE_WINDOW ván gần nhất CỦA CHẾ ĐỘ ĐÓ < AF_MODE_BELOW -> đảo final · ≥ AF_MODE_BELOW -> theo bình thường.
#                          Cần đủ AF_MODE_MIN ván của chế độ đó mới xét bẻ. Cả CAO lẫn THẤP đều có chuỗi ván riêng (hv / lv lưu trong từng ván đã chấm).
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
#       Cả 3 công tắc (AF_FLIP_FINAL · _CT · _ALL) là phép HOẶC: ván thuộc chế độ nào có ÍT NHẤT 1 công tắc áp dụng thì bẻ ĐÚNG 1 lần (không bẻ đôi). Bật AF_FLIP_FINAL = bẻ hết, 2 công tắc kia khỏi cần.
#       Chọn 1 trong 2 (_CT hoặc _ALL) để bẻ có chọn lọc; bật cả 2 = giống bật AF_FLIP_FINAL. Bẻ này nằm SAU 'bẻ chế độ' (bước 3) nên chỉ là lớp bẻ thêm của riêng bạn.
#   Đổi mà không sửa file (ưu tiên: cờ dòng lệnh > biến môi trường > *_DEFAULT):
#       env  : SUNVIW_AF=1|0 · SUNVIW_AF_LOW · SUNVIW_AF_HIGH · SUNVIW_AF_MIN · SUNVIW_AF_MODE_WINDOW · SUNVIW_AF_MODE_MIN · SUNVIW_AF_MODE_BELOW · SUNVIW_AF_MODE_FLIP=1|0 · SUNVIW_AF_FLIP=1|0 · SUNVIW_AF_FLIP_CT=1|0 · SUNVIW_AF_FLIP_ALL=1|0
#       lệnh : --af / --no-af · --af-low X · --af-high X · --af-min N · --af-mode-window N · --af-mode-below X · --af-mode-flip / --af-no-mode-flip · --af-flip / --af-no-flip · --af-flip-ct / --af-no-flip-ct · --af-flip-all / --af-no-flip-all
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
AF_FLIP_LOW_MIN_DEFAULT = 20
AF_FLIP_LOW_MAX_DEFAULT = 37
AF_FLIP_HIGH_MIN_DEFAULT = 65
AF_FLIP_HIGH_MAX_DEFAULT = 75
# ── CHỈ LOGIC BỊ BẺ MỚI VÀO NHÓM CAO / THẤP (Bước 2) — AF_GROUP_FLIPPED_ONLY + AF_GROUP_NEED_MAJORITY ─────────────
#   AF_GROUP_FLIPPED_ONLY_DEFAULT  BẬT (mặc định): CHỈ logic ĐÃ BỊ BẺ (WR nằm TRONG vùng bẻ ở khối trên) mới được xếp vào nhóm CAO / THẤP
#       (theo WR dùng sau bẻ). Logic KHÔNG bẻ (WR ngoài vùng bẻ) KHÔNG thuộc nhóm nào — mặc định ở chế độ ALL (panel hiện nhãn ALL).
#       TẮT: như bản trước — mọi logic đều được chia CAO (WR dùng > 50%) / THẤP (< 50%).
#   AF_GROUP_NEED_MAJORITY_DEFAULT BẬT (mặc định): nhóm CAO / THẤP được chọn (nhóm đông hơn) phải có SỐ LOGIC >= ĐA SỐ của TOÀN BỘ logic
#       (n // 2 + 1 · vd 15 logic -> cần >= 8). Ít hơn đa số -> bỏ nhóm, dùng chế độ ALL (vote tất cả logic sau bẻ logic).
#       Vd ảnh panel: chỉ 4/15 logic bị bẻ (2 CAO + 2 THẤP) -> không nhóm nào đủ 8 logic -> chế độ ALL thay vì CAO.
#       TẮT: nhóm đông hơn luôn được chọn dù chỉ có 1-2 logic.
#   Đổi mà không sửa file: env SUNVIW_AF_GROUP_FLIPPED=1|0 · SUNVIW_AF_GROUP_MAJORITY=1|0
#                          lệnh --af-group-flipped / --af-no-group-flipped · --af-group-majority / --af-no-group-majority
AF_GROUP_FLIPPED_ONLY_DEFAULT = True
AF_GROUP_NEED_MAJORITY_DEFAULT = True
AF_MIN_GAMES_DEFAULT = 7
AF_MODE_WINDOW_DEFAULT = 11
AF_MODE_MIN_DEFAULT = 7
AF_MODE_BELOW_DEFAULT = 45
AF_MODE_FLIP_DEFAULT = False          # BƯỚC 3 (bẻ final theo WR chế độ): False = TẮT · True = BẬT
AF_FLIP_FINAL_DEFAULT = False
AF_FLIP_FINAL_CT_DEFAULT = False       # True = bẻ final của chế độ CAO / THẤP  (BẬT theo yêu cầu: bẻ CAO/THẤP + bẻ ALL)
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
AF_MIN_GAMES =_env_num("SUNVIW_AF_MIN", AF_MIN_GAMES_DEFAULT, int)
AF_MODE_WINDOW = _env_num("SUNVIW_AF_MODE_WINDOW", AF_MODE_WINDOW_DEFAULT, int)
AF_MODE_MIN = _env_num("SUNVIW_AF_MODE_MIN", AF_MODE_MIN_DEFAULT, int)
AF_MODE_BELOW = _env_num("SUNVIW_AF_MODE_BELOW", AF_MODE_BELOW_DEFAULT, float)
AF_MODE_FLIP = _env_bool("SUNVIW_AF_MODE_FLIP", AF_MODE_FLIP_DEFAULT)            # bước 3: bẻ final theo WR chế độ
AF_FLIP_FINAL = _env_bool("SUNVIW_AF_FLIP", AF_FLIP_FINAL_DEFAULT)
AF_FLIP_FINAL_CT = _env_bool("SUNVIW_AF_FLIP_CT", AF_FLIP_FINAL_CT_DEFAULT)      # chỉ bẻ final khi chế độ CAO / THẤP
AF_FLIP_FINAL_ALL = _env_bool("SUNVIW_AF_FLIP_ALL", AF_FLIP_FINAL_ALL_DEFAULT)   # chỉ bẻ final khi chế độ ALL


def af_apply_limits():
    """Chuẩn hoá tham số AF (gọi lúc import và sau khi đọc cờ dòng lệnh)."""
    global AF_FLIP_LOW, AF_FLIP_HIGH, AF_MIN_GAMES, AF_MODE_WINDOW, AF_MODE_MIN, AF_MODE_BELOW
    global AF_FLIP_LOW_MIN, AF_FLIP_LOW_MAX, AF_FLIP_HIGH_MIN, AF_FLIP_HIGH_MAX
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


# ─── CẤU HÌNH ────────────────────────────────────────────────────────────
# Upstream MỚI: /api/tx chỉ trả 1 PHIÊN MỚI NHẤT dạng 1 object:
#   {"ket_qua":"Tài","phien":3284075,"thoi_gian":"11-10-2026 13:50:38 UTC+7","tong":15,"xuc_xac_1":6,"xuc_xac_2":3,"xuc_xac_3":6}
# -> tool quét 1 phiên gần nhất mỗi lần, tự tích lũy vào lịch sử (HIST_PATH) để phần WR vẫn có ván để chấm.
UPSTREAM_URL = os.environ.get(
    "SUNVIW_UPSTREAM",
    "https://well-summary-oclc-invisible.trycloudflare.com/api/tx",
)
UPSTREAM_TIMEOUT = 9      # giây
# THƯ MỤC LƯU DỮ LIỆU BỀN: Railway gắn Volume thì tự đặt RAILWAY_VOLUME_MOUNT_PATH (vd. /data) -> mọi file lưu (lịch sử, graded, key, IP...)
# nằm trong Volume nên KHÔNG MẤT sau mỗi lần deploy / restart. Không có Volume (chạy máy local) -> dùng /tmp như cũ.
# Muốn tự chọn thư mục: đặt SUNVIW_DATA_DIR. Từng file vẫn ghi đè riêng được bằng SUNVIW_HIST / SUNVIW_PERSIST / SUNVIW_KEYS_PATH / SUNVIW_IPS_PATH.
DATA_DIR = os.environ.get("SUNVIW_DATA_DIR") or os.environ.get("RAILWAY_VOLUME_MOUNT_PATH") or "/tmp"
try:
    os.makedirs(DATA_DIR, exist_ok=True)
except OSError:
    DATA_DIR = "/tmp"


def _data_path(name):
    return os.path.join(DATA_DIR, name)


HIST_PATH = os.environ.get("SUNVIW_HIST", _data_path("sunviw_hist.json"))   # lịch sử các phiên đã quét (tool tự tích lũy)
HIST_KEEP = 500            # CỬA SỔ TRƯỢT: chỉ lưu 500 phiên GẦN NHẤT (cả trong RAM lẫn file sunviw_hist.json) — có phiên thứ 501 thì phiên cũ nhất (phiên 1) bị bỏ. Các logic cũ dùng <= 250 ván, SGDLR 300, LAGAC tới 500 · riêng PERIOD cần ~2000 ván mới bắt được chu kỳ theo phiên (ở 500 ván gần như luôn bỏ phiếu trắng) -> muốn PERIOD hiệu quả thì nâng số này lên 2000
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
WR_DECAY = 0.95           # tốc độ giảm trọng số khi ván cũ dần (nhỏ = phản ứng nhanh)
WR_FLOOR = 0.75            # sàn trọng số của ván cũ so với ván mới nhất (lớn = nhớ cầu cũ nhiều)
WR_WEIGHT_NEWEST = 1.4    # trọng số ván mới nhất (ĐÃ ÁP DỤNG vào tính WR; 1.00 = hành vi bản gốc)
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
EVAL_WINDOW = 100           # số phiên gần nhất để đánh giá đúng/sai = WR 100 phiên (hiện thẳng trong /api/predict · tool_dung_sai_10_van) — cần PERSIST_KEEP >= EVAL_WINDOW mới đủ ván để tính
ICON_DUNG = "✅"            # icon hiện cho ván ĐOÁN ĐÚNG trong chuỗi "chuoi" của /api/predict
ICON_SAI = "❌"             # icon hiện cho ván ĐOÁN SAI

# ─── PERSISTENCE (lưu graded để Railway không mất sau restart) ───────────
PERSIST_PATH = os.environ.get("SUNVIW_PERSIST", _data_path("sunviw_graded.json"))
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


# ─── PANEL /api/html ─────────────────────────────────────────────────────
PANEL_DEFAULT_SHOW = 30    # số ván lịch sử panel hiện mặc định (đổi trực tiếp trên panel, trình duyệt nhớ lại)
HIST_MAX = 300             # trần số ván lịch sử cho ?hist=N và ô nhập trên panel

# ═══════════════════════════════════════════════════════════════════════════
#  🎯  CONFIG HITCLUB (GAME 3 · 2 BÀN)  —  MỖI BÀN MỘT BỘ CONFIG RIÊNG  —  CHỈNH Ở ĐÂY
# ═══════════════════════════════════════════════════════════════════════════
#   2 bàn (port từ hittxthuong.js / hittxmd5.js):
#       TX THƯỜNG  gid=vgmn_100 · GET /api/predicthittxthuong · file data hittxthuong.json (lịch sử xúc xắc + các ván đã chấm của RIÊNG bàn này)
#       TX MD5     gid=vgmn_101 · GET /api/predicthittxmd5    · file data hittxmd5.json    (RIÊNG bàn này)
#   Nguồn = HTTP polling: quét API Hit mỗi POLL_SEC giây, tự tích lũy lịch sử (giống cách SUN tích lũy).
#       TX THƯỜNG : cmd 1008 nhả sid · cmd 1003 nhả xúc xắc -> ghép sid + xúc xắc (y như file JS)
#       TX MD5    : cmd 2006 nhả luôn sid + xúc xắc
#   Dự đoán = ĐÚNG bộ 15 logic SEQ15 + AF + WR có trọng số của SUN (dùng chung hàm), nhưng mỗi bàn ĐỌC CONFIG RIÊNG ở 2 khối dưới đây.
#   ► Hiện 2 khối đang BẰNG giá trị mặc định hiện tại của SUN (copy lúc ghép). Sửa khối bàn nào CHỈ ảnh hưởng bàn đó — không đụng SUN hay bàn còn lại.
#   ► Ý nghĩa từng thông số giống hệt tên ở các khối "CONFIG AF" · "CONFIG WR CÓ TRỌNG SỐ" · "CONFIG BẺ FINAL" phía trên (AF_* · WR_* · FLIP_FINAL · EVAL_WINDOW · PERSIST_KEEP).
#   Thông số riêng của bàn:
#       ENABLED       True/False  bật/tắt riêng bàn này
#       GID           mã bàn trên API Hit (vgmn_100 = thường · vgmn_101 = MD5)
#       POLL_SEC      chu kỳ quét API (giây)
#       HIST_KEEP     số phiên xúc xắc giữ lại (cửa sổ trượt, như HIST_KEEP của SUN)
#       TIE_LOGIC     logic phá hoà (như SUNVIW_TIE_LOGIC của SUN)
#       CONSEC_CHECK  True = chỉ chấm ván khi số phiên liền nhau (phiên n+1) · False = coi 2 phiên đứng cạnh nhau trong lịch sử là liền nhau
#                     (đặt False nếu số phiên của Hit không tăng đều 1 đơn vị -> không thì tool không chấm được ván nào)
#   Đổi mà không sửa file — biến môi trường <TIỀN TỐ><TÊN>, tiền tố HITTXTHUONG_ hoặc HITTXMD5_:
#       vd. HITTXMD5_AF_ENABLED=0 · HITTXTHUONG_WR_WINDOW=17 · HITTXMD5_FLIP_FINAL=1 · HITTXTHUONG_POLL_SEC=2
#   HITCLUB=0 (hoặc cờ --no-hit) tắt cả 2 bàn · HIT_API_URL đổi địa chỉ API ({GID} được thay bằng GID của bàn) · HITTXTHUONG_PATH / HITTXMD5_PATH đổi file lưu.
HIT_ENABLED = _env_bool("HITCLUB", True)
HIT_API_URL = os.environ.get("HIT_API_URL", "https://jakpotgwab.geightdors.net/glms/v1/notify/taixiu?platform_id=g8&gid={GID}")
HIT_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
HIT_TXTHUONG_PATH = os.environ.get("HITTXTHUONG_PATH", _data_path("hittxthuong.json"))
HIT_TXMD5_PATH = os.environ.get("HITTXMD5_PATH", _data_path("hittxmd5.json"))


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


# ─ BÀN 1: TX THƯỜNG (gid vgmn_100) — config RIÊNG, chỉnh ở đây ─
HIT_TXTHUONG_CFG = TableCfg("hittxthuong", _hit_env("HITTXTHUONG_", {
    "ENABLED": True,
    "GID": "vgmn_100",
    "POLL_SEC": 3.0,
    "HIST_KEEP": 500,
    "TIE_LOGIC": "PPM6",
    "CONSEC_CHECK": True,
    # WR có trọng số
    "WR_WINDOW": 13, "WR_DECAY": 0.95, "WR_FLOOR": 0.75, "WR_WEIGHT_NEWEST": 1.4, "WR_FLIP_WEIGHT": False, "WR_MIN_GAMES": 1,
    # bẻ final (dùng khi AF tắt)
    "FLIP_FINAL": False,
    # AF: bước 1 bẻ logic
    "AF_ENABLED": True, "AF_FLIP_LOW": 37, "AF_FLIP_HIGH": 68,
    "AF_FLIP_BAND": True, "AF_FLIP_LOW_MIN": 20, "AF_FLIP_LOW_MAX": 42, "AF_FLIP_HIGH_MIN": 57, "AF_FLIP_HIGH_MAX": 70,
    "AF_MIN_GAMES": 7,
    # AF: bước 2 nhóm CAO/THẤP
    "AF_GROUP_FLIPPED_ONLY": True, "AF_GROUP_NEED_MAJORITY": True,
    # AF: bước 3 bẻ theo WR chế độ (mặc định TẮT)
    "AF_MODE_FLIP": False, "AF_MODE_WINDOW": 13, "AF_MODE_MIN": 7, "AF_MODE_BELOW": 45,
    # AF: bẻ final riêng
    "AF_FLIP_FINAL": False, "AF_FLIP_FINAL_CT": True, "AF_FLIP_FINAL_ALL": True,
    # đánh giá đúng/sai + số ván lưu
    "EVAL_WINDOW": 100, "PERSIST_KEEP": 100,
}))

# ─ BÀN 2: TX MD5 (gid vgmn_101) — config RIÊNG, chỉnh ở đây ─
HIT_TXMD5_CFG = TableCfg("hittxmd5", _hit_env("HITTXMD5_", {
    "ENABLED": True,
    "GID": "vgmn_101",
    "POLL_SEC": 3.0,
    "HIST_KEEP": 500,
    "TIE_LOGIC": "PPM6",
    "CONSEC_CHECK": True,
    # WR có trọng số
    "WR_WINDOW": 13, "WR_DECAY": 0.95, "WR_FLOOR": 0.75, "WR_WEIGHT_NEWEST": 1.4, "WR_FLIP_WEIGHT": False, "WR_MIN_GAMES": 1,
    # bẻ final (dùng khi AF tắt)
    "FLIP_FINAL": False,
    # AF: bước 1 bẻ logic
    "AF_ENABLED": True, "AF_FLIP_LOW": 37, "AF_FLIP_HIGH": 63,
    "AF_FLIP_BAND": True, "AF_FLIP_LOW_MIN": 30, "AF_FLIP_LOW_MAX": 45, "AF_FLIP_HIGH_MIN": 55, "AF_FLIP_HIGH_MAX": 70,
    "AF_MIN_GAMES": 7,
    # AF: bước 2 nhóm CAO/THẤP
    "AF_GROUP_FLIPPED_ONLY": True, "AF_GROUP_NEED_MAJORITY": True,
    # AF: bước 3 bẻ theo WR chế độ (mặc định TẮT)
    "AF_MODE_FLIP": False, "AF_MODE_WINDOW": 13, "AF_MODE_MIN": 7, "AF_MODE_BELOW": 45,
    # AF: bẻ final riêng
    "AF_FLIP_FINAL": False, "AF_FLIP_FINAL_CT": False, "AF_FLIP_FINAL_ALL": True,
    # đánh giá đúng/sai + số ván lưu
    "EVAL_WINDOW": 100, "PERSIST_KEEP": 100,
}))

# ═══════════════════════════════════════════════════════════════════════════
#  🗑  CONFIG XÓA LỊCH SỬ DỰ ĐOÁN (nút "Xóa lịch sử" ở panel /api/html)  —  CHỈNH Ở ĐÂY
# ═══════════════════════════════════════════════════════════════════════════
#   Nút này CHỈ làm sạch phần HIỂN THỊ: danh sách "lich_su" + số liệu đúng/sai (tool_dung_sai_*, % đúng, chuỗi ✅❌ trên panel).
#   Cách làm: lưu 1 MỐC phiên cho từng game (SUN / HIT thường / HIT MD5) — ván có phiên <= mốc bị ẩn khỏi lịch sử / thống kê hiển thị.
#   KHÔNG xóa / sửa bất cứ dữ liệu nào khác: lịch sử xúc xắc (hist) · các ván đã chấm + vote từng logic (graded) · key / IP / cấu hình.
#   -> 15 logic SUN (và các bàn Hit), WR có trọng số, AF (CAO/THẤP, WR chế độ), do_tin_cay, du_doan của phiên đang dự đoán: GIỮ NGUYÊN 100%, vì chúng vẫn đọc đủ dữ liệu cũ.
#   Mốc lưu file riêng nên còn sau khi restart / deploy (cần Volume như các file khác trên Railway).
#   HIST_CLEAR_ENABLED_DEFAULT  True = cho xóa · False = tắt hẳn tính năng (endpoint trả 403)  (env SUNVIW_HIST_CLEAR=1|0)
#   HIST_CLEAR_PATH             file lưu mốc (env SUNVIW_HISTCLEAR_PATH)
#   Endpoint: POST /api/history/clear  {"game": "sun" | "hittxthuong" | "hittxmd5" | "hitclub" | "all"}  (cần key người dùng; key chỉ xóa được lịch sử của game nó thuộc về)
HIST_CLEAR_ENABLED_DEFAULT = True
HIST_CLEAR_ENABLED = _env_bool("SUNVIW_HIST_CLEAR", HIST_CLEAR_ENABLED_DEFAULT)
HIST_CLEAR_PATH = os.environ.get("SUNVIW_HISTCLEAR_PATH", _data_path("sunviw_histclear.json"))

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
    """Vote của 15 logic SUN cho phiên KẾ TIẾP, từ lịch sử `hist` (cũ -> mới; mỗi phần tử có actual / total / d1 d2 d3 / phien). Thứ tự = SUN_NAMES.
    Logic bình thường chưa đủ lịch sử / không có tín hiệu -> theo kết quả ván trước. Logic trong SUN_ABSTAIN (LAGAC, PERIOD) chỉ kích hoạt khi thấy cấu trúc có ý nghĩa thống kê;
    không kích hoạt -> phiếu = ĐA SỐ của các logic bình thường (không biến thành phiếu "copy ván trước")."""
    S = {"y": [1 if r["actual"] == TAI else 0 for r in hist], "t": [int(r["total"]) for r in hist],
         "d": [(r["d1"], r["d2"], r["d3"]) for r in hist],
         "p": [int(r["phien"]) for r in hist]}              # số phiên (SESS · PERIOD dùng)
    fb = S["y"][-1] if S["y"] else 0
    out = []
    for nm, fn in SUN_LOGICS:
        try:
            v = fn(S)
        except Exception:  # noqa: BLE001 - 1 logic lỗi không được làm sập cả dự đoán
            v = None
        if v is None and nm in SUN_ABSTAIN:
            out.append(None)                                # phiếu trắng thật: điền sau bằng đa số
        else:
            out.append(TAI if (fb if v is None else v) == 1 else XIU)
    reg = [o for (nm, _f), o in zip(SUN_LOGICS, out) if nm not in SUN_ABSTAIN]
    nt, nx = sum(1 for o in reg if o == TAI), sum(1 for o in reg if o == XIU)
    maj = TAI if nt > nx else XIU if nx > nt else (TAI if fb == 1 else XIU)
    return [maj if o is None else o for o in out]


# ─── 15 LOGIC CỦA SUN (thuần Python, tự học online từ lịch sử — mô tả ở docstring đầu file) ───
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


def lg_mk(S, k, W, extra=None):
    y, t, d = S["y"], S["t"], S["d"]
    n = len(y)
    if n < k + 1:
        return None
    if extra == "t1":
        key = lambda j: tuple(y[j - k:j]) + (_tb1(t[j - 1]),)
    else:
        key = lambda j: tuple(y[j - k:j])
    c = _win_counts(n, key, y, W, k)
    n0, n1 = c[key(n)] if key(n) in c else (0, 0)
    return _vote01(n1, n0, y[-1])


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


def lg_knn(S, L, K, W, mode):
    y, t = S["y"], S["t"]
    n = len(y)
    if n < L + 10:
        return None
    lo = max(L, n - W)
    cur = y[n - L:n] if mode == "y" else t[n - L:n]
    rows = []
    for j in range(lo, n):
        if mode == "y":
            dist = float(sum(1 for a, b in zip(y[j - L:j], cur) if a != b))
            w = 1.0 / (1 + dist) ** 2
        else:
            dist = float(sum(abs(a - b) for a, b in zip(t[j - L:j], cur)))
            w = 1.0 / (1 + dist / L) ** 2
        rows.append((dist, j, w))
    rows.sort(key=lambda r: (r[0], r[1]))
    s1 = s0 = 0.0
    for dist, j, w in rows[:K]:
        if y[j] == 1:
            s1 += w
        else:
            s0 += w
    return 1 if s1 > s0 else 0 if s0 > s1 else y[-1]


def _f_t2(S, j):
    t = S["t"]
    return (_tb1(t[j - 1]), _tb1(t[j - 2]))


def _f_mm(S, j):
    dd = S["d"][j - 1]
    return (min(dd), max(dd))


def _f_dtt(S, j):
    t = S["t"]
    df = t[j - 1] - t[j - 2]
    return ((df > 0) - (df < 0), _tb1(t[j - 1]))


def lg_cond(S, featfn, W, m=6.0):
    y = S["y"]
    n = len(y)
    if n < 5:
        return None
    key = lambda j: featfn(S, j)
    c = _win_counts(n, key, y, W, 4)
    n0, n1 = c[key(n)] if key(n) in c else (0, 0)
    rate = (n1 + 0.5 * m) / (n0 + n1 + m)
    return 1 if rate > 0.5 else 0 if rate < 0.5 else y[-1]


def lg_nb(S, featfns, W, a=1.0):
    y = S["y"]
    n = len(y)
    if n < 6:
        return None
    tabs = [defaultdict(lambda: [0, 0]) for _ in featfns]
    prior = [0, 0]
    for j in range(max(5, n - W), n):
        for q, f in enumerate(featfns):
            tabs[q][f(S, j)][y[j]] += 1
        prior[y[j]] += 1
    s = math.log((prior[1] + 1) / (prior[0] + 1))
    for q, f in enumerate(featfns):
        k = f(S, n)
        n0, n1 = tabs[q][k] if k in tabs[q] else (0, 0)
        s += math.log((n1 + a) / (prior[1] + 2 * a)) - math.log((n0 + a) / (prior[0] + 2 * a))
    return 1 if s > 0 else 0 if s < 0 else y[-1]


_nb_y3 = lambda S, j: tuple(S["y"][j - 3:j])
_nb_y4 = lambda S, j: tuple(S["y"][j - 4:j])
_nb_t1b = lambda S, j: _tb1(S["t"][j - 1])
_nb_max = lambda S, j: max(S["d"][j - 1])
_nb_min = lambda S, j: min(S["d"][j - 1])
_nb_dist = lambda S, j: len(set(S["d"][j - 1]))
_nb_par = lambda S, j: S["t"][j - 1] % 2


# ── logic thêm ở bản SEQ14/SEQ15 (PAT · EWMA · REGIME · SESS · LAGAC · PERIOD · SGDLR). Trả 1 = TÀI · 0 = XỈU · None = bỏ phiếu trắng (compute_all -> theo kết quả ván trước) ──
def lg_alt(S):
    """PAT: nhận diện cầu lặp chu kỳ P ∈ {2,3,4,6} (1-1 · chu kỳ 3 · 2-2 · 3-3): y[n-i] == y[n-i-P] trọn P+3 bước liền nhau -> ván kế = y[n-P]."""
    y = S["y"]
    n = len(y)
    for P in (2, 3, 4, 6):
        M = P + 3
        if n < P + M + 1:
            continue
        if all(y[n - i] == y[n - i - P] for i in range(1, M + 1)):
            return y[n - P]
    return None


def lg_ewma(S, alpha=0.1, W=250, m=10.0):
    """EWMA: trung bình trượt mũ của TỔNG chia 5 nhóm; học online P(Tài | nhóm) trong W ván (co về 50%, m=10). Hướng (Tài/Xỉu) do dữ liệu quyết định, không đặt cứng."""
    t, y = S["t"], S["y"]
    n = len(y)
    if n < 40:
        return None
    e = [float(t[0])]
    for i in range(1, n):
        e.append(alpha * t[i] + (1 - alpha) * e[-1])
    bk = lambda v: 0 if v < 9.5 else 1 if v < 10.2 else 2 if v < 10.8 else 3 if v < 11.5 else 4
    cnt = defaultdict(lambda: [0, 0])
    for j in range(max(30, n - W), n):
        k = bk(e[j - 1])
        cnt[k][1] += 1
        cnt[k][0] += y[j]
    kk = bk(e[n - 1])
    c, tot = cnt[kk] if kk in cnt else (0, 0)
    rate = (c + 0.5 * m) / (tot + m)
    return 1 if rate > 0.5 else 0 if rate < 0.5 else None


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


def _p_at(S, j):
    """Số phiên của ván j (j = len(y) là ván CẦN DỰ ĐOÁN = phiên cuối + 1)."""
    p = S["p"]
    return p[j] if j < len(p) else p[-1] + (j - len(p) + 1)


_nb_sm = lambda m: (lambda S, j: _p_at(S, j) % m)


def lg_sess(S, W=250, a=4.0):
    """SESS: Naive Bayes trên số phiên mod 2/3/5/7/10 (học online, làm mượt a=4 để bucket ít mẫu không gây nhiễu)."""
    if not S.get("p"):
        return None
    return lg_nb(S, [_nb_sm(2), _nb_sm(3), _nb_sm(5), _nb_sm(7), _nb_sm(10)], W, a)


def lg_lagac(S, K=16, W=1500, crit=26.3):
    """LAGAC: tự tương quan độ trễ k = 1..K của chuỗi Tài/Xỉu trong W ván gần nhất. z_k = (số lần y[i] == y[i-k] - m/2) / (0.5·√m).
    Kiểm định tổng thể (kiểu Ljung–Box): Σ z_k² > crit (= χ²(K) mức 95%) mới coi chuỗi là KHÔNG ngẫu nhiên và bỏ phiếu theo Σ z_k × (kết quả cách k ván); không thì None (phiếu trắng)."""
    y = S["y"]
    n = len(y)
    N = min(n, W)
    if N < 80:
        return None
    ys = y[n - N:]
    sc = chi = 0.0
    for k in range(1, K + 1):
        m = N - k
        ag = 0
        for i in range(k, N):
            if ys[i] == ys[i - k]:
                ag += 1
        z = (ag - m / 2.0) / (0.5 * math.sqrt(m))
        chi += z * z
        sc += z * (1 if ys[N - k] == 1 else -1)
    if chi < crit:
        return None
    return 1 if sc > 0 else 0 if sc < 0 else None


def lg_period(S, W=2000, ms=range(2, 33), zc=3.0, m0=8.0):
    """PERIOD: dò chu kỳ theo SỐ PHIÊN. Thử m = 2..32: chi-bình-phương của tỉ lệ Tài theo (phiên mod m) so với tỉ lệ chung -> z (Wilson–Hilferty); lấy m có z lớn nhất nếu z >= zc
    (zc = 3 đã gồm hiệu chỉnh cho 31 phép thử), rồi P(Tài | phiên kế tiếp mod m) co về tỉ lệ chung (m0). Không m nào đạt ngưỡng -> None (phiếu trắng). Cần nhiều ván (W = 2000) mới đủ mạnh."""
    y, p = S["y"], S["p"]
    n = len(y)
    N = min(n, W)
    if N < 150 or not p:
        return None
    ph, ys = p[n - N:], y[n - N:]
    ov = sum(ys) / float(N)
    if ov <= 0 or ov >= 1:
        return None
    var = ov * (1 - ov)
    best = None
    for m in ms:
        cnt, tai = [0] * m, [0] * m
        for a, b in zip(ph, ys):
            cnt[a % m] += 1
            tai[a % m] += b
        chi = sum((tai[r] - cnt[r] * ov) ** 2 / (cnt[r] * var) for r in range(m) if cnt[r] > 0)
        df = m - 1
        z = ((chi / df) ** (1.0 / 3) - (1 - 2.0 / (9 * df))) / math.sqrt(2.0 / (9 * df))
        if z >= zc and (best is None or z > best[0]):
            best = (z, m, cnt, tai)
    if best is None:
        return None
    _z, m, cnt, tai = best
    r = _p_at(S, n) % m
    rate = (tai[r] + m0 * ov) / (cnt[r] + m0)
    return 1 if rate > 0.5 else 0 if rate < 0.5 else None


def lg_sgdlr(S, W=300, ep=2, lr=0.05, lam=0.02, NL=12):
    """SGDLR: hồi quy logistic online (SGD, L2) trên 300 ván gần nhất, huấn luyện lại mỗi ván.
    Đặc trưng: 1 (bias) · 12 kết quả gần nhất (±1) · 2 tổng gần nhất (chuẩn hoá) · độ dài đợt hiện tại có dấu (cắt ở 8)."""
    y, t = S["y"], S["t"]
    n = len(y)
    lo = max(NL + 2, n - W)
    if n - lo < 60:
        return None

    def feat(j):
        f = [1.0] + [2.0 * y[j - k] - 1.0 for k in range(1, NL + 1)]
        f += [(t[j - 1] - 10.5) / 3.4, (t[j - 2] - 10.5) / 3.4]
        r = 1
        while r < 8 and j - 1 - r >= 0 and y[j - 1 - r] == y[j - 1]:
            r += 1
        f.append((2.0 * y[j - 1] - 1.0) * r / 8.0)
        return f

    X = [feat(j) for j in range(lo, n)]
    Yv = y[lo:n]
    w = [0.0] * len(X[0])
    for _ in range(ep):
        for x, yy in zip(X, Yv):
            z = sum(a * b for a, b in zip(w, x))
            pr = 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, z))))
            e = yy - pr
            w = [wi + lr * (e * xi - lam * wi) for wi, xi in zip(w, x)]
    z = sum(a * b for a, b in zip(w, feat(n)))
    return 1 if z > 0 else 0 if z < 0 else None


SUN_LOGICS = [
    ("MKT2", lambda S: lg_mk(S, 2, 250, "t1")),
    ("PPM6", lambda S: lg_ppm(S, 6, 250, 1.5)),
    ("KNNT", lambda S: lg_knn(S, 8, 15, 150, "t")),
    ("CT2", lambda S: lg_cond(S, _f_t2, 250)),
    ("CMM", lambda S: lg_cond(S, _f_mm, 250)),
    ("CDT", lambda S: lg_cond(S, _f_dtt, 250)),
    ("NBMIX", lambda S: lg_nb(S, [_nb_y3, _nb_t1b, _nb_max, _nb_min, _nb_dist], 250)),
    ("NBY4", lambda S: lg_nb(S, [_nb_y4, _nb_par, _nb_dist], 250)),
    ("PAT", lambda S: lg_alt(S)),
    ("EWMA", lambda S: lg_ewma(S, 0.1, 250)),
    ("REGIME", lambda S: lg_regime(S, 20, 250)),
    ("SESS", lambda S: lg_sess(S, 250, 4.0)),
    ("LAGAC", lambda S: lg_lagac(S, 16, 1500)),
    ("PERIOD", lambda S: lg_period(S, 2000)),
    ("SGDLR", lambda S: lg_sgdlr(S, 300)),
]


SUN_NAMES = [n for n, _ in SUN_LOGICS]
SUN_SIG = "SEQ15v1:" + ",".join(SUN_NAMES)         # dấu vân tay bộ logic SUN (bỏ dữ liệu graded của bộ logic cũ; file graded cũ 14 phiếu sẽ tự được chấm lại từ lịch sử)
SUN_ABSTAIN = {"LAGAC", "PERIOD"}                  # logic chuyên biệt kích hoạt hiếm: không kích hoạt -> phiếu = đa số các logic còn lại (xem compute_all)

# 15 logic là số LẺ nên đa số tất cả logic không hoà; nhưng nhóm CAO/THẤP của AF có thể chẵn -> vẫn giữ phiếu phá hoà: lấy phiếu của logic này (mặc định PPM6; env SUNVIW_TIE_LOGIC).
SUN_TIE_LOGIC = os.environ.get("SUNVIW_TIE_LOGIC", "PPM6")
if SUN_TIE_LOGIC not in SUN_NAMES:
    SUN_TIE_LOGIC = "PPM6" if "PPM6" in SUN_NAMES else SUN_NAMES[0]


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
    """WR của 2 chế độ CAO / THẤP trên AF_MODE_WINDOW ván gần nhất CỦA CHẾ ĐỘ ĐÓ.
    Dữ liệu = vote gốc của nhóm CAO (hv) / nhóm THẤP (lv) đã LƯU trong từng ván đã chấm (cả khi tool đang chạy chế độ kia),
    chấm với kết quả thật. Ván không có vote của nhóm đó (nhóm rỗng / hoà phiếu / chưa đủ ván) thì bỏ qua.
    Trả {"CAO": {...}, "THAP": {...}}, mỗi chế độ có: n · w (số ván đúng) · need · wr (% hoặc None nếu chưa đủ ván) · flip (True = WR < AF_MODE_BELOW) · chuoi (cũ -> mới, True = đúng)."""
    need = max(1, min(cfg.AF_MODE_MIN, cfg.AF_MODE_WINDOW))
    out = {}
    for mode, key in (("CAO", "hv"), ("THAP", "lv")):
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


def af_decision(votes, graded, cfg=SUN):
    """AF (auto-flip + CAO/THẤP + bẻ theo WR chế độ) của SUN — port từ SUNVIW_9logics_autoflip_auto.html (xem khối CONFIG AF).
    Trả dict: mode (CAO | THAP | ALL) · final (SAU bẻ chế độ) · base (TRƯỚC bẻ chế độ) · mflip (đã bẻ chế độ) · tie (pool hoà phiếu -> dùng đa số tất cả logic)
    preds (phiếu sau bẻ logic) · flips[i] (LOW | HIGH | None) · wins / wsum (trọng số) · eff[i] (WR dùng, 0-100) · group[i] (CAO | THAP | None) · hi / lo (chỉ số logic mỗi nhóm)
    hv / lv (vote gốc của nhóm CAO / THẤP — LƯU vào ván đã chấm) · gT / gX (phiếu TÀI / XỈU trong pool) · avg (TB WR dùng của pool, độ tin cậy) · mw (WR 2 chế độ)
    demoted (True = nhóm CAO / THẤP được chọn ít hơn đa số toàn bộ logic -> đã hạ về ALL) · need_maj (số logic tối thiểu để một nhóm được dùng).
    AF_GROUP_FLIPPED_ONLY: chỉ logic bị bẻ mới có group (CAO | THAP); logic không bẻ -> group None = mặc định ALL."""
    nl = len(votes)
    all_vote = vote_result(votes)
    win = graded[-cfg.WR_WINDOW:]                             # cũ -> mới (cùng cửa sổ WR với cách cũ của SUN)
    n = len(win)
    need = max(1, min(cfg.AF_MIN_GAMES, cfg.WR_WINDOW))
    mw = af_mode_wr(graded, cfg)
    out = {"mode": "ALL", "n": n, "need": need, "final": all_vote, "base": all_vote, "mflip": False, "tie": False, "demoted": False,
           "need_maj": nl // 2 + 1,
           "preds": list(votes), "flips": [None] * nl, "wins": [], "wsum": 0.0, "weights": [], "eff": [None] * nl,
           "group": [None] * nl, "hi": [], "lo": [], "hv": None, "lv": None, "pool": list(range(nl)),     # pool = logic THỰC SỰ tham gia vote ván này (chưa đủ ván -> vote tất cả)
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
    need_maj = nl // 2 + 1                                # đa số của TOÀN BỘ logic (15 -> 8)

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
    demoted = False
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
    if cfg.AF_MODE_FLIP and mode != "ALL" and not tie and mw[mode]["flip"]:    # Bước 3: bẻ theo WR của chế độ đang chạy (chỉ khi AF_MODE_FLIP bật)
        mflip, final = True, flip_pred(base)
    pv = [preds[i] for i in pool]
    vpool = list(range(nl)) if tie else list(pool)         # logic THAM GIA vote ván này (nhóm hoà phiếu -> thực tế dùng pool ALL) — panel hiện "logic đang dự đoán"
    out.update(mode=mode, final=final, base=base, mflip=mflip, tie=tie, demoted=demoted, need_maj=need_maj, pool=vpool, preds=preds, flips=flips,
               wins=[float(w) for w in wins], wsum=float(wsum), weights=[float(w) for w in weights],
               eff=[float(e / wsum * 100) for e in effw], group=group, hi=hi, lo=lo,
               hv=hv if hv in (TAI, XIU) else None, lv=lv if lv in (TAI, XIU) else None,
               gT=sum(1 for x in pv if x == TAI), gX=sum(1 for x in pv if x == XIU),
               avg=(float(sum(effw[i] for i in pool) / (len(pool) * wsum) * 100) if pool else None))
    return out


def decide_final(votes, graded, dec_wr=None, cfg=SUN):
    """Chốt final của SUN: AF (nếu bật) -> cách cũ (wr_decision). Trả (final, af). `af` = dict của af_decision khi final do AF chốt, không thì None.
    `dec_wr` truyền sẵn thì không tính lại wr_decision; chỉ tính khi thật sự cần quay về cách cũ (AF tắt)."""
    if cfg.AF_ENABLED:
        af = af_decision(votes, graded, cfg)
        if af["final"] not in (TAI, XIU):                 # hoà 7-7 tới tận bước cuối (số logic chẵn) -> phá hoà, không để 'SKIP' lọt ra API
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
    AF_FLIP_FINAL = bẻ mọi chế độ · AF_FLIP_FINAL_CT = chỉ CAO/THẤP (ALL giữ nguyên) · AF_FLIP_FINAL_ALL = chỉ ALL (CAO/THẤP giữ nguyên).
    Phép HOẶC: có ít nhất 1 công tắc áp dụng cho chế độ đó thì bẻ ĐÚNG 1 lần."""
    if cfg.AF_FLIP_FINAL:
        return True
    if mode == "ALL":
        return bool(cfg.AF_FLIP_FINAL_ALL)
    if mode in ("CAO", "THAP"):
        return bool(cfg.AF_FLIP_FINAL_CT)
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
            # bỏ entry lưu từ bộ logic khác (vd. file cũ dùng logic MD5) -> tránh lệch chỉ số vote
            return [g for g in data if isinstance(g, dict) and g.get("sig") == SUN_SIG]
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


def rebuild_graded(hist, saved_graded=None, cfg=SUN):
    """Chấm lại lịch sử: dự đoán phiên k+1 từ LỊCH SỬ tới phiên k (15 logic SEQ15 cần cả chuỗi chứ không chỉ xúc xắc phiên k), chấm bằng kết quả thật.
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
        if af is not None:                                                # lưu dữ liệu 2 chế độ: vote gốc của nhóm CAO (hv) và nhóm THẤP (lv) của ván này
            entry.update(af=True, mode=af["mode"], mflip=af["mflip"], hv=af["hv"], lv=af["lv"])
        fresh.append(entry)
    return merge_graded(seed, fresh)


def build_result(hist, cfg=SUN, persist=None):
    """Từ lịch sử (cũ -> mới) -> dict kết quả dự đoán cho phiên kế tiếp.
    cfg = SUN (mặc định) hoặc TableCfg của 1 bàn HITCLUB · persist = (load, save) nơi lưu các ván đã chấm (None -> file graded của SUN)."""
    latest = hist[-1]
    load, save = persist if persist else (persist_load, persist_save)
    saved = load()
    graded = rebuild_graded(hist, saved_graded=saved, cfg=cfg)
    save(graded)
    votes = compute_all(hist)
    dec = _wr_decision_cfg(votes, graded, cfg)                                   # cách chốt cũ: luôn tính (phương án dự phòng + hiển thị WR cũ)
    final, af = decide_final(votes, graded, dec, cfg)                       # AF -> cách cũ
    used_af = af is not None
    avg = af["avg"] if used_af else dec["avg"]
    mwc = af["mw"].get(af["mode"]) if used_af and cfg.AF_MODE_FLIP and af["mode"] in ("CAO", "THAP") else None     # WR của CHẾ ĐỘ đang chạy (ALL không bẻ theo WR chế độ -> None · AF_MODE_FLIP tắt -> None, panel ẩn dòng này)
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
        "bo_logic": "SEQ15 (chuoi + xuc xac + tong + so phien, khong dung MD5)",
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
            "be_final_cao_thap": cfg.AF_FLIP_FINAL_CT,                 # CHỈ bẻ final khi chế độ CAO / THẤP (ALL giữ nguyên)
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
    hit_ensure_pollers()                          # HITCLUB: bật poller 2 bàn (TX thường + TX MD5)


def _acc_rows(rows, n=10):
    w = rows[:n]
    dung = sum(1 for r in w if r["dung"])
    return {"dung": dung, "sai": len(w) - dung, "tong": len(w),
            "chuoi": "".join(ICON_DUNG if r["dung"] else ICON_SAI for r in w)}      # mới -> cũ


# ─── HITCLUB (GAME 3): 2 BÀN · HTTP POLLING · MỖI BÀN MỘT FILE DATA RIÊNG ───
# Port từ hittxthuong.js / hittxmd5.js. Mỗi bàn = 1 HitTable: poller riêng + config riêng (xem CONFIG HITCLUB) + file riêng (hittxthuong.json / hittxmd5.json
# chứa lịch sử xúc xắc + các ván đã chấm). Dự đoán dùng bộ 15 logic SEQ15 / AF / WR của SUN qua build_result(hist, cfg, persist).
def _hit_fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": HIT_UA, "Accept": "application/json", "Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=UPSTREAM_TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))


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


def _hit_parse_md5(tb, data):
    """TX MD5 (gid vgmn_101): mục cmd 2006 có sid + d1 d2 d3. Lấy MỌI mục hợp lệ trong payload (bản JS chỉ giữ mục cuối)."""
    out = {}
    for g in data:
        if _hit_cmd(g) == 2006:
            r = _hit_rec(g.get("sid"), g.get("d1"), g.get("d2"), g.get("d3"))
            if r:
                out[r["phien"]] = r
    return list(out.values())


def _hit_parse_thuong(tb, data):
    """TX THƯỜNG (gid vgmn_100): cmd 1008 nhả sid (nhớ lại qua các lần quét) · cmd 1003 nhả xúc xắc -> ghép sid + xúc xắc. Mỗi sid chỉ ghi 1 lần (y như file JS)."""
    for g in data:
        if _hit_cmd(g) == 1008 and g.get("sid"):
            p = _parse_int(g["sid"])
            if p is not None:
                tb.pending_sid = p
    out = {}
    for g in data:
        if _hit_cmd(g) == 1003 and g.get("d1") is not None and tb.pending_sid is not None:
            sid = tb.pending_sid
            if sid != tb.last_sid and sid not in tb.hist and sid not in out:
                r = _hit_rec(sid, g.get("d1"), g.get("d2"), g.get("d3"))
                if r:
                    out[sid] = r
                    tb.last_sid = sid
    return list(out.values())


class HitTable:
    """1 bàn HitClub: quét API nền, tích lũy lịch sử, tính dự đoán bằng config RIÊNG (self.cfg), lưu data vào file RIÊNG (self.path)."""

    def __init__(self, key, label, cfg, path, parser):
        self.key, self.label, self.cfg, self.path, self.parse = key, label, cfg, path, parser
        self.url = HIT_API_URL.replace("{GID}", cfg.GID)
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

    @property
    def active(self):
        return bool(HIT_ENABLED and self.cfg.ENABLED)

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

    def _write(self):
        try:
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"ban": self.key, "gid": self.cfg.GID, "luu_luc": _now(),
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
            data = _hit_fetch_json(self.url)
            if not isinstance(data, dict) or data.get("status") != "OK" or not isinstance(data.get("data"), list):
                raise ValueError("API Hit tra ve khong hop le (status != OK hoac thieu data)")
            items = data["data"]
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
            self._write()                               # 1 lần ghi: lịch sử xúc xắc + ván đã chấm
            with self.slock:
                self.state.update(result=res, latest=latest, error=None, updated=_now(), checked=_now())

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
                  an_den_phien=hist_hidden_upto(self.key), payload_cuoi=self.dbg, config=c.as_dict())
        return st


HIT_TABLES = {
    "hittxthuong": HitTable("hittxthuong", "TX Thường", HIT_TXTHUONG_CFG, HIT_TXTHUONG_PATH, _hit_parse_thuong),
    "hittxmd5": HitTable("hittxmd5", "TX MD5", HIT_TXMD5_CFG, HIT_TXMD5_PATH, _hit_parse_md5),
}


def hit_ensure_pollers():
    for tb in HIT_TABLES.values():
        tb.start()


# ─── XÓA LỊCH SỬ DỰ ĐOÁN (chỉ ẩn phần hiển thị — xem khối CONFIG XÓA LỊCH SỬ) ───
_hc_lock = threading.Lock()
_hc = {"loaded": False, "d": {"sun": {"den": 0, "luc": None},
                              "hittxthuong": {"den": 0, "luc": None}, "hittxmd5": {"den": 0, "luc": None}}}


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
:root{--bg:#0f1424;--pn:#171d33;--ln:#252d4a;--tx:#e8ebf5;--mu:#8a93b2;--tai:#f5b942;--xiu:#5cc8ff;--ok:#3ddc97;--no:#ff6b81;--cao:#b79cff;--thap:#ff9f5c}
*{box-sizing:border-box}
body{margin:0 auto;max-width:720px;padding:14px 14px 40px;background:var(--bg);color:var(--tx);font:15px/1.45 "Be Vietnam Pro",system-ui,sans-serif;font-variant-numeric:tabular-nums}
header{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px}
h1{font-size:17px;margin:0;font-weight:800}
#st{font-size:12px;color:var(--mu)}
#st i{display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--ok);margin-right:6px}
#st.bad i{background:var(--no)}
.tabs{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px;margin-bottom:12px}
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
.cfg button.dg{margin-left:auto}.cfg button.dg:hover{color:var(--no);border-color:var(--no)}
.strip{display:flex;flex-wrap:wrap;gap:4px;margin-bottom:12px}
.chip{width:20px;height:20px;border-radius:5px;font-size:12px;line-height:20px;text-align:center;color:#0f1424;font-weight:800}
.chip.ok{background:var(--ok)}.chip.no{background:var(--no)}
table{width:100%;border-collapse:collapse}
th{font-weight:600;color:var(--mu);font-size:12px;text-align:left;padding:6px 8px}
td{padding:7px 8px;border-top:1px solid var(--ln)}
.r{text-align:right}
[hidden]{display:none!important}
@media(max-width:480px){.hero{grid-template-columns:1fr}.prev{text-align:left}}
.kov{position:fixed;inset:0;background:rgba(10,14,26,.96);display:none;align-items:center;justify-content:center;z-index:99;padding:20px}
.kbox{background:var(--pn);border:1px solid var(--ln);border-radius:14px;padding:20px;width:100%;max-width:360px}
.kbox input{width:100%;margin:10px 0;background:var(--bg);border:1px solid var(--ln);color:var(--tx);border-radius:9px;padding:10px;font:inherit}
.kbox button{width:100%;background:var(--xiu);color:#06121c;border:0;border-radius:10px;padding:10px;font:inherit;font-weight:700;cursor:pointer}
.mbar{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0 4px}
.bd{display:inline-block;padding:1px 9px;border-radius:999px;font-size:11.5px;font-weight:700;border:1px solid var(--ln);color:var(--mu);white-space:nowrap;margin:0 3px 0 0}
.bd.ALL{color:var(--tx);border-color:var(--mu)}.bd.CAO{color:var(--cao);border-color:var(--cao)}.bd.THAP{color:var(--thap);border-color:var(--thap)}
.bd.flip{color:var(--no);border-color:var(--no)}.bd.off{opacity:.55}
.chain{margin-top:3px}
.mst{display:flex;flex-wrap:wrap;gap:6px;margin:0 2px 6px}
.mst button{background:var(--pn);border:1px solid var(--ln);color:var(--tx);border-radius:10px;padding:5px 10px;font:inherit;font-size:13px;cursor:pointer;display:flex;gap:6px;align-items:baseline}
.mst button.on{border-color:var(--tx);box-shadow:inset 0 -3px 0 var(--tx)}
.mst .nm{font-weight:800}.mst .ALL .nm{color:var(--tx)}.mst .CAO .nm{color:var(--cao)}.mst .THAP .nm{color:var(--thap)}
.mst .now{font-style:normal;font-size:11px;color:var(--ok)}
.mhint{margin:0 2px 12px;font-size:12px;color:var(--mu)}
.chip.m-ALL{box-shadow:inset 0 -3px 0 #e8ebf5}.chip.m-CAO{box-shadow:inset 0 -3px 0 var(--cao)}.chip.m-THAP{box-shadow:inset 0 -3px 0 var(--thap)}
.leg{margin-top:8px;font-size:12px;color:var(--mu)}
.lg{background:var(--pn);border:1px solid var(--ln);border-radius:12px;margin:0 0 12px}
.lg>summary{cursor:pointer;padding:10px 14px;list-style:none;display:flex;justify-content:space-between;align-items:center;gap:8px;font-weight:600}
.lg>summary::-webkit-details-marker{display:none}
.lg-b{padding:0 14px 12px}
.lg-b table{margin-top:6px}
.lg-b td,.lg-b th{padding:6px 6px;font-size:13.5px}
.lg-b .band{font-size:12px;color:var(--mu);margin:2px 0 4px}
.kbox{text-align:center}.kbox p{margin:6px 0 4px}.kbox b{font-size:16px}
.gi{font-size:34px;line-height:1;margin-bottom:8px}
.spin{width:34px;height:34px;border:3px solid var(--ln);border-top-color:var(--tai);border-radius:50%;animation:sp 1s linear infinite;margin:0 auto 14px}
@keyframes sp{to{transform:rotate(360deg)}}
.gcode{margin:14px 0;padding:8px 10px;border-radius:9px;background:var(--bg);border:1px solid var(--ln);font-size:12.5px;color:var(--mu)}
.gcode b{display:block;color:var(--tx);font:700 14px ui-monospace,Menlo,Consolas,monospace;letter-spacing:.04em}
@media(prefers-reduced-motion:reduce){.spin{animation:none}}
</style></head><body>
<div class="kov" id="kov" style="display:flex"><div class="kbox" id="kbox"><div class="spin"></div><b>Đang kiểm tra quyền truy cập…</b></div></div>
<header><h1>SUNVIW · Tài Xỉu</h1><div id="st"></div></header>
<nav class="tabs" id="tabs"></nav>
<main id="main"></main>
<div class="cfg">
  <label for="n" class="mu">Số ván lịch sử hiển thị</label>
  <input id="n" type="number" min="1" max="__MAX__">
  <button data-n="10">10</button><button data-n="20">20</button><button data-n="50">50</button><button data-n="100">100</button>
  <button class="dg" id="clr" title="Chỉ xóa lịch sử dự đoán đang hiển thị của game đang chọn — không ảnh hưởng các logic dự đoán">🗑 Xóa lịch sử</button>
</div>
<div id="hist"></div>
<script>
/*__HWID_JS__*/
/* ── CỔNG DUYỆT THIẾT BỊ: panel chỉ mở khi admin chính đã duyệt HWID này (KHÔNG cần key, vào cả Sun + Hit). Mọi lời gọi /api/... tự kèm HWID. ── */
let ACC=false,GV='';
const KOV=document.getElementById('kov'),KB=document.getElementById('kbox'),f0=window.fetch.bind(window);
window.fetch=function(u,o){o=Object.assign({},o||{});o.headers=Object.assign({},o.headers||{},HWID_HDR);
  return f0(u,o).then(r=>{if(r.status===401&&ACC&&String(u).indexOf('/api/')===0&&String(u).indexOf('/api/panel/')!==0){ACC=false;access()}return r})};   /* bị gỡ quyền giữa chừng -> khóa lại ngay */
function gateView(st,msg){
  const key=st+'|'+(msg||'');if(GV===key&&KOV.style.display==='flex')return;GV=key;
  const T={pending:['<div class="spin"></div>','Đang chờ admin duyệt','Yêu cầu truy cập của thiết bị này đã được gửi tới admin chính. Trang sẽ tự mở ngay khi được duyệt — không cần nhập key, không cần tải lại.'],
    denied:['<div class="gi">⛔</div>','Thiết bị bị từ chối','Admin chính đã từ chối thiết bị này. Hãy liên hệ admin nếu cần được cấp quyền.'],
    limit:['<div class="gi">⚠️</div>','Quá nhiều yêu cầu chờ duyệt','Mạng này đã gửi quá nhiều yêu cầu. Hãy nhờ admin xử lý bớt rồi bấm kiểm tra lại.'],
    error:['<div class="gi">⚠️</div>','Chưa kết nối được',msg||'Đang thử lại…']}[st]||['<div class="gi">⚠️</div>','Chưa vào được',msg||''];
  KB.innerHTML=T[0]+'<b>'+T[1]+'</b><p class="mu">'+T[2]+'</p><div class="gcode">Mã thiết bị<b>'+HWID.slice(0,8)+'…'+HWID.slice(-4)+'</b></div><button id="gre" type="button">Kiểm tra lại</button>';
  KOV.style.display='flex';
}
async function access(){
  try{
    const r=await fetch('/api/panel/status',{cache:'no-store'}),j=await r.json().catch(()=>({}));
    if(j.status==='approved'){if(!ACC){ACC=true;GV='';KOV.style.display='none';load()}return}
    ACC=false;gateView(['pending','denied','limit'].includes(j.status)?j.status:'error',j.loi);
  }catch(e){ACC=false;gateView('error','Mất kết nối tới server — đang thử lại…')}
}
document.addEventListener('click',e=>{if(e.target&&e.target.id==='gre')access()});
</script>
<script>
const G={sun:{n:'Sun',u:'/api/predictsun',g:'sun'},hitt:{n:'Hit Thường',u:'/api/predicthittxthuong',g:'hittxthuong'},hitm:{n:'Hit MD5',u:'/api/predicthittxmd5',g:'hittxmd5'}};
const okG=()=>true;   /* thiết bị đã duyệt vào được cả Sun lẫn 2 bàn Hit -> hiện đủ mọi tab */
let cur=(localStorage.getItem('g') in G||localStorage.getItem('g')==='ip')?localStorage.getItem('g'):'sun',N=+localStorage.getItem('n')||__SHOW__,IPD=null;
if(cur!=='ip'&&!okG(cur))cur=Object.keys(G).find(okG)||'ip';
const D={},$=s=>document.querySelector(s),cl=v=>v==='TÀI'?'tai':v==='XỈU'?'xiu':'';
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const P={1:[[50,50]],2:[[26,26],[74,74]],3:[[26,26],[50,50],[74,74]],4:[[26,26],[74,26],[26,74],[74,74]],5:[[26,26],[74,26],[50,50],[26,74],[74,74]],6:[[26,26],[74,26],[26,50],[74,50],[26,74],[74,74]]};
const dice=a=>`<span class="dice">${a.map(n=>`<i style="background:${P[n].map(([x,y])=>`radial-gradient(circle at ${x}% ${y}%,#1a1f36 0 3.2px,transparent 3.8px)`).join(',')},#f2efe6"></i>`).join('')}</span>`;
const prevHtml=d=>d.phien_truoc==null?'<div class="mu">Chưa có kết quả phiên trước</div>':`<div class="mu">Phiên ${d.phien_truoc}</div>${d.xuc_xac?dice(d.xuc_xac):''}<div>${d.tong==null?'':`<b>${d.tong}</b> `}<span class="${cl(d.ket_qua_truoc)}">${d.ket_qua_truoc}</span></div>`;
const acc=d=>{const h=d.lich_su||[],k=h.filter(x=>x.dung).length;return{k,t:h.length,p:h.length?Math.round(k*100/h.length):null}};
const MN={ALL:'ALL',CAO:'CAO',THAP:'THẤP'},MS=['ALL','CAO','THAP'],MTIP={ALL:'Không chia nhóm: vote tất cả logic',CAO:'Nhóm logic WR cao đông hơn -> chỉ vote nhóm CAO',THAP:'Nhóm logic WR thấp đông hơn -> chỉ vote nhóm THẤP'};
let MF=MS.includes(localStorage.getItem('mf'))?localStorage.getItem('mf'):'';
const bd=(c,t,tip)=>`<span class="bd ${c}"${tip?` title="${esc(tip)}"`:''}>${t}</span>`;
const modeAcc=(h,m)=>{const r=h.filter(x=>x.che_do===m),k=r.filter(x=>x.dung).length;return{k,t:r.length,p:r.length?Math.round(k*100/r.length):null}};
function modeBar(d){
  if(!d.che_do)return '';
  const m=d.che_do,w=d.wr_che_do_hien_tai,goc=d.du_doan_goc||d.du_doan;
  const parts=[bd(m,'Chế độ '+MN[m],MTIP[m]),bd(d.be_final?'flip':'off','Bẻ final '+(d.be_final?'BẬT':'TẮT'),'Bẻ final theo cấu hình hiện tại, áp dụng cho chế độ '+MN[m])];
  if(m!=='ALL')parts.push(bd(d.be_che_do?'flip':'off','Bẻ chế độ '+(d.be_che_do?'BẬT':'TẮT'),'Bẻ theo WR của chế độ đang chạy'));
  const ex=w?`<div class="mu">WR chế độ ${MN[w.che_do]} (${w.cua_so} ván gần nhất của chế độ): ${w.wr==null?`chưa đủ ván (${w.so_van}/${w.van_toi_thieu})`:`${w.dung}/${w.so_van} = ${w.wr}% ${w.se_be?'< '+w.nguong_be+'% → bẻ chế độ':'≥ '+w.nguong_be+'% → không bẻ chế độ'}`}</div>`:'';
  const seq=d.be_che_do&&d.du_doan_truoc_be_che_do?[d.du_doan_truoc_be_che_do,goc]:[goc];
  if(d.be_final)seq.push(d.du_doan);
  const how=[d.be_che_do?'bẻ chế độ':'',d.be_final?'bẻ final':''].filter(Boolean).join(' + ');
  const ch=seq.length>1?`<div class="mu chain">Gốc ${seq.map(v=>`<b class="${cl(v)}">${v}</b>`).join(' → ')} <span>(${how})</span></div>`:'';
  return `<div class="mbar">${parts.join('')}</div>${ex}${ch}`;
}
function modeStats(d,h){
  if(!h.some(x=>x.che_do))return '';
  const a=acc(d);
  return `<div class="mst"><button class="${MF===''?'on':''}" data-m=""><span class="nm">Tất cả</span> <b>${a.k}/${a.t}</b> <span class="mu">${a.p===null?'–':a.p+'%'}</span></button>${MS.map(m=>{const s=modeAcc(h,m);return `<button class="${m}${MF===m?' on':''}" data-m="${m}" title="${esc(MTIP[m])}"><span class="nm">${MN[m]}</span> <b>${s.k}/${s.t}</b> <span class="mu">${s.p==null?'–':s.p+'%'}</span>${d.che_do===m?' <i class="now">● hiện tại</i>':''}</button>`}).join('')}</div><div class="mhint">Đúng/sai tính lại theo cấu hình bẻ hiện tại · bấm một chế độ để lọc lịch sử</div>`;
}
let LO=localStorage.getItem('lo')!=='0';
function logicHtml(d){
  const ct=d.chi_tiet,L=ct&&ct.logic;
  if(!L||!L.length)return '';
  const A=ct.af,af=!!(A&&A.dang_dung),use=x=>af?x.af_du_doan:x.du_doan;
  const nT=L.filter(x=>use(x)==='TÀI').length,nX=L.filter(x=>use(x)==='XỈU').length;
  let band='';
  if(af){const v=A.gioi_han_vung_be,ng=A.nguong_be_logic;
    band=v&&v.bat?`Chỉ bẻ logic khi WR trong vùng THẤP ${v.thap[0]}–${v.thap[1]}% hoặc CAO ${v.cao[0]}–${v.cao[1]}% · ngoài vùng không bẻ`:(ng?`Bẻ logic khi WR < ${ng.thap}% hoặc > ${ng.cao}%`:'');
    if(A.chi_be_vao_nhom)band+=' · chỉ logic đã bẻ mới vào nhóm CAO/THẤP, logic không bẻ = ALL';
    if(A.can_da_so_nhom)band+=' · nhóm CAO/THẤP cần ≥ '+A.da_so_toi_thieu+' logic (đa số), ít hơn → dùng ALL';
    if(A.ha_xuong_all)band+=' · ván này: nhóm chưa đủ đa số → ĐÃ HẠ VỀ ALL'}
  const rows=L.map(x=>{
    const eff=x.af_be&&x.af_wr!=null?` <span class="mu">→ ${x.af_wr}%</span>`:'';
    const nh=af?x.af_nhom:x.nhom;
    const fb=x.af_be?bd('flip',x.af_be==='LOW'?'BẺ · WR thấp':'BẺ · WR cao','Phiếu của logic này bị đảo ở bước 1 của AF'):'<span class="mu">–</span>';
    return `<tr><td><b>${esc(x.ten)}</b></td><td class="${cl(x.du_doan)}">${x.du_doan}</td><td>${x.wr==null?'–':x.wr+'%'}${eff}</td>${af?`<td>${fb}</td><td class="${cl(x.af_du_doan)}"><b>${x.af_du_doan}</b></td>`:''}<td>${nh?bd(nh,MN[nh]||nh):(af?bd('ALL','ALL','Không bẻ → mặc định chế độ ALL'):'<span class="mu">–</span>')}</td></tr>`}).join('');
  return `<details class="lg" id="lg"${LO?' open':''}><summary><span>🧠 Từng logic · WR &amp; dự đoán hiện tại</span><span class="mu"><span class="tai">TÀI ${nT}</span> · <span class="xiu">XỈU ${nX}</span></span></summary><div class="lg-b">${band?`<div class="band">${esc(band)}</div>`:''}<table><tr><th>Logic</th><th>${af?'Phiếu gốc':'Dự đoán'}</th><th>WR</th>${af?'<th>Bẻ</th><th>Phiếu dùng</th>':''}<th>Nhóm</th></tr>${rows}</table>${af?'<div class="band" style="margin-top:6px">WR = tỉ lệ đúng có trọng số trong '+(d.so_van_wr||'?')+' ván gần nhất · khi bị bẻ, “→ x%” là WR sau bẻ (100 − WR) · Phiếu dùng = phiếu sau khi bẻ logic</div>':''}</div></details>`;
}
document.addEventListener('toggle',e=>{if(e.target&&e.target.id==='lg'){LO=e.target.open;localStorage.setItem('lo',LO?'1':'0')}},true);
function render(){
  if(cur!=='ip'&&!okG(cur))cur=Object.keys(G).find(okG)||'ip';
  $('#tabs').innerHTML=Object.entries(G).filter(([k])=>okG(k)).map(([k,g])=>{const d=D[k]||{},a=acc(d);
    return `<button class="tab${k===cur?' on':''}" data-g="${k}"><span>${g.n} <b class="${cl(d.du_doan)}">${d.ok?d.du_doan:'…'}</b></span><small>${a.p===null?'–':a.p+'%'}</small></button>`}).join('')+`<button class="tab ipt${cur==='ip'?' on':''}" data-g="ip"><span>IP truy cập <b class="${IPD&&IPD.ok&&IPD.dang_dung?'okc':''}">${IPD&&IPD.ok?IPD.dang_dung+' đang dùng':(IPD&&IPD.khoa?'🔒':'…')}</b></span><small>${IPD&&IPD.ok?IPD.tong+' IP':''}</small></button>`;
  $('.cfg').hidden=cur==='ip';
  if(cur==='ip'){if(!(IPD&&IPD.khoa&&$('#ak')))$('#main').innerHTML=ipHtml();$('#hist').innerHTML='';$('#st').className='';$('#st').innerHTML='<i></i>'+esc(new Date().toLocaleTimeString());return}
  const d=D[cur]||{},a=acc(d);
  if(!d.ok){$('#main').innerHTML=`<div class="hero"><div class="mu">${esc(d.loi||'Đang tải…')}</div></div>`;$('#hist').innerHTML='';return}
  const h=d.lich_su||[],hm=h.some(x=>x.che_do),hv=(MF&&hm)?h.filter(x=>x.che_do===MF):h;
  $('#main').innerHTML=`<section class="hero"><div><div class="mu">Dự đoán phiên ${d.phien}</div><div class="big ${cl(d.du_doan)}">${d.du_doan}</div><div class="mu">Độ tin cậy ${d.do_tin_cay==null?'–':d.do_tin_cay+'%'}${!d.che_do&&d.be_final?' · đã bẻ final':''} · xét ${d.so_van_wr} ván</div>${modeBar(d)}</div><div class="prev">${prevHtml(d)}</div></section><div class="stats"><span><b class="okc">${a.k}</b> <span class="mu">đúng</span></span><span><b class="noc">${a.t-a.k}</b> <span class="mu">sai</span></span><span><b>${a.p===null?'–':a.p+'%'}</b> <span class="mu">trên ${a.t} ván</span></span></div>${modeStats(d,h)}${logicHtml(d)}`;
  const mcell=x=>x.che_do?bd(x.che_do,MN[x.che_do],MTIP[x.che_do])+(x.be_final?bd('flip','BẺ','Final bị bẻ (theo cấu hình hiện tại)'):'')+(x.be_che_do?bd('flip','BẺ CĐ','Bẻ theo WR chế độ'):''):'<span class="mu">–</span>';
  $('#hist').innerHTML=hv.length?`<div class="strip">${hv.map(x=>`<span class="chip ${x.dung?'ok':'no'}${x.che_do?' m-'+x.che_do:''}" title="#${x.phien}${x.che_do?' · '+MN[x.che_do]:''}${x.be_final?' · bẻ final':''}">${x.dung?'✓':'✗'}</span>`).join('')}</div><table><tr><th>Phiên</th>${hm?'<th>Chế độ</th>':''}<th>Dự đoán</th><th>Kết quả</th><th class="r">Đúng/sai</th></tr>${hv.map(x=>`<tr><td>#${x.phien}</td>${hm?`<td>${mcell(x)}</td>`:''}<td class="${cl(x.du_doan)}">${x.du_doan}</td><td class="${cl(x.ket_qua)}">${x.ket_qua}${x.tong==null?'':` <span class="mu">(${x.tong})</span>`}</td><td class="r ${x.dung?'okc':'noc'}">${x.dung?'Đúng':'Sai'}</td></tr>`).join('')}</table>${hm?'<div class="leg">BẺ = final bị bẻ theo cấu hình hiện tại · BẺ CĐ = bẻ theo WR chế độ · vạch màu dưới ô ✓/✗ = chế độ của ván</div>':''}`:(h.length?`<p class="mu">Không có ván nào ở chế độ ${MN[MF]||''} trong ${h.length} ván đang hiển thị — tăng số ván lịch sử hoặc bấm “Tất cả”.</p>`:`<p class="mu">Chưa có ván nào được chấm. Tool lưu dự đoán rồi chờ kết quả phiên đó (Sun · Hit: kết quả lấy từ API).</p>`);
  $('#st').className=Object.entries(D).some(([k,x])=>okG(k)&&x&&(!x.ok||x.stale))?'bad':'';
  $('#st').innerHTML=`<i></i>${esc(d.cap_nhat||'')}`;
}
$('#tabs').onclick=e=>{const b=e.target.closest('[data-g]');if(b){cur=b.dataset.g;localStorage.setItem('g',cur);render()}};
document.addEventListener('click',e=>{const b=e.target.closest('[data-m]');if(b&&cur!=='ip'){MF=(b.dataset.m===MF)?'':b.dataset.m;localStorage.setItem('mf',MF);render()}});
$('#n').value=N;
function setN(v){N=Math.max(1,Math.min(+v||1,__MAX__));$('#n').value=N;localStorage.setItem('n',N);load()}
$('#n').onchange=e=>setN(e.target.value);
document.querySelectorAll('[data-n]').forEach(b=>b.onclick=()=>setN(b.dataset.n));
$('#clr').onclick=async()=>{
  if(!G[cur])return;
  if(!confirm('Xóa lịch sử dự đoán của '+G[cur].n+'?\n\nChỉ xóa danh sách đúng/sai và số liệu thống kê đang hiển thị (từ nay đếm lại từ đầu).\nKhông xóa dữ liệu nào khác và không ảnh hưởng các logic / WR dùng để dự đoán.'))return;
  try{
    const r=await fetch('/api/history/clear',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({game:G[cur].g})});
    const j=await r.json().catch(()=>({}));
    if(!r.ok||j.ok===false){if(r.status!==401)alert(j.loi||'Không xóa được lịch sử');return}
  }catch(e){alert('Mất kết nối: '+e);return}
  load();
};
const agoT=s=>s<60?s+'s':s<3600?Math.floor(s/60)+'p':s<86400?Math.floor(s/3600)+'g':Math.floor(s/86400)+'n';
function ipHtml(){
  const d=IPD||{};
  if(d.khoa)return `<section class="hero" style="grid-template-columns:1fr"><div><div class="mu">🔒 Cần admin key để xem danh sách IP</div><div style="display:flex;gap:8px;margin-top:8px"><input id="ak" type="password" placeholder="Admin key" autocomplete="off" style="width:200px;background:var(--pn);border:1px solid var(--ln);color:var(--tx);border-radius:8px;padding:6px 8px;font:inherit"><button id="akb" style="background:none;border:1px solid var(--ln);color:var(--mu);border-radius:8px;padding:5px 10px;font:inherit;cursor:pointer">Mở</button></div></div></section>`;
  if(!d.ok)return `<div class="hero"><div class="mu">${esc(d.loi||'Đang tải…')}</div></div>`;
  const by=o=>Object.entries(o||{}).map(([k,v])=>k+' '+v).join(' · ');
  return `<section class="hero" style="grid-template-columns:1fr"><div><div class="mu">IP truy cập API (Sun · Hit · panel)</div><div class="stats"><span><b class="okc">${d.dang_dung}</b> <span class="mu">đang dùng (trong ${d.cua_so_giay}s)</span></span><span><b>${d.tong}</b> <span class="mu">IP đã từng dùng</span></span></div><div class="mu">IP của bạn: ${esc(d.ban||'?')}</div></div></section><table><tr><th>IP</th><th>Trạng thái</th><th>Gần nhất</th><th class="r">Request</th></tr>${(d.ips||[]).map(x=>`<tr><td title="${esc(x.ua||'')}"><b>${esc(x.ip)}</b>${x.la_ban?' <span class="mu">(bạn)</span>':''}<div class="mu" style="font-size:11.5px">${esc(by(x.theo_loai))}</div></td><td class="${x.dang_dung?'okc':'mu'}">${x.dang_dung?'● đang dùng':'○ đã dùng'}</td><td class="mu">${esc(x.gan_nhat)}<div style="font-size:11.5px">${agoT(x.truoc_giay)} trước · từ ${esc(x.lan_dau)}</div></td><td class="r">${x.so_request}</td></tr>`).join('')}</table>`;
}
async function loadIps(){
  try{const k=localStorage.getItem('ak')||'';const r=await fetch('/api/ips',{cache:'no-store',headers:k?{'X-Admin-Key':k}:{}});IPD=await r.json()}
  catch(e){IPD={ok:false,loi:'Mất kết nối: '+e}}
}
document.addEventListener('click',e=>{if(e.target.id==='akb'){const v=$('#ak');localStorage.setItem('ak',v?v.value.trim():'');loadIps().then(render)}});
async function load(){
  await Promise.all([loadIps(),...Object.entries(G).filter(([k])=>okG(k)).map(async([k,g])=>{
    try{const r=await fetch(`${g.u}?hist=${N}&detail=1`,{cache:'no-store'});D[k]=await r.json()}
    catch(e){D[k]={ok:false,loi:'Mất kết nối: '+e}}})]);
  render();
}
setInterval(()=>{if(ACC)load()},3000);
access();setInterval(access,3000);   /* hỏi trạng thái duyệt 3s/lần: được duyệt -> tự mở · bị gỡ quyền -> tự khóa */
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
    if path in ("/api/predicthittxthuong", "/api/predicthittxmd5"):
        return "hit"
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
from flask import g as flask_g  # noqa: E402  (đặt tên khác vì nhiều hàm dùng biến cục bộ `g`)

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
#   Khi KEY_GATE_API bật: /api/predictsun · /api/predicthittxthuong · /api/predicthittxmd5 · /api/ips · /api/history/clear đòi key hợp lệ (header X-User-Key hoặc ?key=; riêng /api/ips chỉ nhận header).
#
#   🎮 KEY THEO GAME: mỗi KEY NGƯỜI DÙNG chỉ thuộc ĐÚNG 1 GAME, chọn lúc tạo ở trang admin (không có key gộp chung):
#       · key game SUN (tiền tố SUN-)  -> chỉ gọi được /api/predictsun (+ /api/predict tên cũ)
#       · key game HIT (tiền tố HIT-)  -> chỉ gọi được /api/predicthittxthuong + /api/predicthittxmd5 (cả 2 bàn Hit)
#       · dùng key sai game -> HTTP 403 {"sai_game":true,"game_can":"sun"|"hit"}; KHÔNG gắn thiết bị khi sai game. Panel /api/html tự chỉ hiện tab đúng game của key.
#       · /api/ips và /api/history/clear nhận mọi key hợp lệ; riêng xóa lịch sử chỉ xóa được game mà key thuộc về.
#       · POST /api/key/check trả thêm "game" của key; truyền {"game":"sun"|"hit"} (hoặc ?game=) để kiểm tra key có đúng game đó không.
#   KEY_LEGACY_GAME: key tạo TRƯỚC bản có chia game (không có trường game) -> "all" = vẫn dùng được mọi game (mặc định, không khóa ai) · "sun" / "hit" = gán luôn cho game đó (env SUNVIW_KEY_LEGACY_GAME).
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
KEY_GAMES = ("sun", "hit")                            # game gắn được vào key người dùng — MỖI KEY CHỈ THUỘC 1 GAME, không gộp chung
KEY_GAME_LABEL = {"sun": "Sun", "hit": "Hit"}
KEY_PREFIX = {"sun": "SUN", "hit": "HIT"}             # tiền tố key để nhìn là biết game: SUN-XXXX-... / HIT-XXXX-...
_lg = os.environ.get("SUNVIW_KEY_LEGACY_GAME", "all").strip().lower()
KEY_LEGACY_GAME = _lg if _lg in ("all", "sun", "hit") else "all"   # game của key cũ chưa có trường game (xem khối CONFIG KEY / ADMIN)
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


def _key_game(rec):
    """Game của key người dùng: "sun" | "hit"; key cũ chưa gán game -> KEY_LEGACY_GAME ("all" = mọi game)."""
    g = str(rec.get("game") or "").strip().lower()
    return g if g in KEY_GAMES else KEY_LEGACY_GAME


def _game_ok(kg, game):
    """Key thuộc game `kg` có được dùng cho `game` không (game None = endpoint không gắn game cụ thể -> mọi key hợp lệ)."""
    return game is None or kg == "all" or kg == game


def _key_tables(kg):
    """Các khoá lịch sử (hist_clear) mà key thuộc game `kg` được thao tác."""
    out = set()
    if kg in ("all", "sun"):
        out.add("sun")
    if kg in ("all", "hit"):
        out |= set(HIT_TABLES)
    return out


def _path_game(p):
    """Game mà endpoint thuộc về (None = endpoint chung: mọi key hợp lệ đều gọi được)."""
    if p in ("/api/predictsun", "/api/predict"):
        return "sun"
    if p in ("/api/predicthittxthuong", "/api/predicthittxmd5"):
        return "hit"
    return None


WRONG_GAME_MSG = "Key này chỉ dùng cho game"


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


def _check_user_key(k, hw=None, ip="", ua="", alts=(), fresh=False, game=None):
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
        if r["exp"] <= now:
            return None, "key da het han", True, kg
        if not _game_ok(kg, game):
            return None, (f"{WRONG_GAME_MSG} {KEY_GAME_LABEL.get(kg, kg)} — không dùng được cho game {KEY_GAME_LABEL.get(game, game)}. "
                          f"Hãy dùng key {KEY_GAME_LABEL.get(game, game)} (hoặc xin admin tạo key {KEY_GAME_LABEL.get(game, game)})."), True, kg
        if hw:
            ok, err, ch = _dev_use(r, hw, ip, ua, now, alts, fresh)
            if not ok:
                return None, err, True, kg
            if ch:
                try:
                    _kv_save(d)
                except OSError:
                    pass
        elif HWID_REQUIRED:
            return None, "Thiếu mã thiết bị (HWID) — gửi header X-HWID hoặc ?hwid= cùng key.", True, kg
        return r, "", True, kg


# ═══════════════════════════════════════════════════════════════════════════
#  🛂  DUYỆT THIẾT BỊ VÀO PANEL /api/html  —  CHỈNH Ở ĐÂY
# ═══════════════════════════════════════════════════════════════════════════
#   Panel /api/html KHÔNG còn ô nhập key. Ai mở trang cũng chỉ thấy bảng "Đang chờ admin duyệt": panel tự gửi yêu cầu (kèm HWID thiết bị) tới
#   POST/GET /api/panel/status -> thiết bị vào danh sách CHỜ DUYỆT. Admin CHÍNH vào /api/admin -> mục "Duyệt thiết bị vào panel HTML" -> Duyệt / Từ chối / Gỡ quyền.
#   Được duyệt xong, panel tự mở (không cần tải lại), KHÔNG cần key, và vào được CẢ SUN LẪN HIT (2 bàn).
#   Thiết bị đã duyệt cũng gọi thẳng được /api/predictsun · /api/predicthittxthuong · /api/predicthittxmd5 · /api/ips · /api/history/clear không cần key
#   (cổng _gate_key nhận HWID đã duyệt). Key người dùng + tool (X-User-Key + X-HWID) vẫn chạy y như trước, KHÔNG đổi.
#   Gỡ quyền / xóa thiết bị khỏi danh sách -> panel của máy đó bị khóa lại ngay (trong ~3 giây) và phải xin duyệt lại.
#   HWID nhận diện y như hệ key (mã đã lưu localStorage + cookie, mã phụ phần cứng): đổi mạng / đổi IP không ảnh hưởng, IP chỉ GHI LẠI để admin xem.
#   PANEL_DEV_PATH             file lưu danh sách thiết bị (env SUNVIW_PANEL_DEV_PATH; mặc định <DATA_DIR>/sunviw_panel_devices.json). Railway: nằm cùng Volume với file key.
#   PANEL_MAX_DEVICES          trần số thiết bị lưu (đầy -> bỏ yêu cầu CHỜ DUYỆT cũ nhất; thiết bị đã duyệt / từ chối không bị xóa tự động)
#   PANEL_MAX_PENDING_PER_IP   mỗi IP chỉ được có tối đa N yêu cầu đang chờ duyệt cùng lúc (chống spam HWID giả) — env SUNVIW_PANEL_PENDING_PER_IP
PANEL_DEV_PATH = os.environ.get("SUNVIW_PANEL_DEV_PATH", _data_path("sunviw_panel_devices.json"))
PANEL_MAX_DEVICES = 2000
PANEL_MAX_PENDING_PER_IP = _env_num("SUNVIW_PANEL_PENDING_PER_IP", 10, int)
PANEL_TOUCH_SEC = 60                                  # ghi "thấy lần cuối" tối đa 1 lần / phút / thiết bị
_pv_lock = threading.RLock()
_pv_cache = {"sig": None, "d": None}                  # cache theo (mtime, size) của file -> panel poll 3s/lần không đọc lại file; vẫn đúng khi nhiều worker cùng ghi


def _pv_load():
    """{"devs": {hwid: {"st": pending|approved|denied, "first", "last", "ip", "ua", "alt": [...], "dec_at", "dec_by"}}}. Gọi trong _pv_lock."""
    try:
        stt = os.stat(PANEL_DEV_PATH)
        sig = (stt.st_mtime_ns, stt.st_size)
    except OSError:
        return {"devs": {}}
    if _pv_cache["sig"] == sig and _pv_cache["d"] is not None:
        return _pv_cache["d"]
    try:
        with open(PANEL_DEV_PATH, "r", encoding="utf-8") as f:
            d = json.load(f)
        if isinstance(d, dict) and isinstance(d.get("devs"), dict):
            _pv_cache.update(sig=sig, d=d)
            return d
    except Exception:  # noqa: BLE001
        pass
    return {"devs": {}}


def _pv_save(d):
    """Ghi file thiết bị (atomic). Trả True nếu ghi được. Gọi trong _pv_lock."""
    try:
        tmp = PANEL_DEV_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
        os.replace(tmp, PANEL_DEV_PATH)
        stt = os.stat(PANEL_DEV_PATH)
        _pv_cache.update(sig=(stt.st_mtime_ns, stt.st_size), d=d)
        return True
    except OSError:
        _pv_cache.update(sig=None, d=None)             # bỏ cache để lần sau đọc lại file thật (d có thể đã bị sửa dở)
        return False


def _panel_access(hw, alts=(), fresh=False, ip="", ua="", create=True):
    """Trạng thái của thiết bị với panel: 'approved' | 'pending' | 'denied' | 'limit' (IP này đã có quá nhiều yêu cầu chờ duyệt) | 'none' (chưa có và create=False).
    create=True: thiết bị lạ -> tạo yêu cầu CHỜ DUYỆT. Nhận lại máy cũ bằng mã chính / mã phụ giống hệ key (_dev_find / _dev_learn). IP chỉ ghi lại, không dùng để chặn."""
    now = int(time.time())
    with _pv_lock:
        d = _pv_load()
        devs = d["devs"]
        k = _dev_find(devs, hw, alts, fresh)
        if k is not None:
            dv = devs[k]
            ch = _dev_learn(dv, k, [hw] if fresh else [hw, *alts])
            if now - int(dv.get("last") or 0) >= PANEL_TOUCH_SEC:
                dv["last"], dv["ip"], dv["ua"] = now, ip, str(ua or "")[:120]
                ch = True
            if ch:
                _pv_save(d)
            return dv.get("st") if dv.get("st") in ("approved", "pending", "denied") else "pending"
        if not create:
            return "none"
        if sum(1 for v in devs.values() if v.get("st") == "pending" and v.get("ip") == ip) >= PANEL_MAX_PENDING_PER_IP:
            return "limit"
        if len(devs) >= PANEL_MAX_DEVICES:
            old = [x for x, v in devs.items() if v.get("st") == "pending"]
            if not old:
                return "limit"
            del devs[min(old, key=lambda x: devs[x].get("last") or 0)]
        dv = devs[hw] = {"st": "pending", "first": now, "last": now, "ip": ip, "ua": str(ua or "")[:120], "alt": []}
        if not fresh:
            _dev_learn(dv, hw, alts)
        _pv_save(d)
        return "pending"


def _panel_approved(hw, alts=(), fresh=False, ip="", ua=""):
    """Thiết bị này đã được admin chính duyệt vào panel chưa (không tạo yêu cầu mới)."""
    return bool(hw) and _panel_access(hw, alts, fresh, ip, ua, create=False) == "approved"


def panel_health():
    with _pv_lock:
        devs = _pv_load()["devs"]
        c = {"pending": 0, "approved": 0, "denied": 0}
        for v in devs.values():
            if v.get("st") in c:
                c[v["st"]] += 1
    return dict(tong=len(devs), **c)


_PANEL_MSG = {"approved": "Thiết bị đã được duyệt.",
              "pending": "Đang chờ admin chính duyệt thiết bị này.",
              "denied": "Admin chính đã từ chối thiết bị này.",
              "limit": "Mạng này đã gửi quá nhiều yêu cầu chờ duyệt — nhờ admin xử lý bớt rồi thử lại."}


@app.route("/api/panel/status", methods=["GET", "POST"])
def api_panel_status():
    """Panel /api/html gọi 3 giây / lần: gửi yêu cầu duyệt (lần đầu) và hỏi trạng thái. Trả {"ok": true, "status": "approved"} khi đã được duyệt,
    còn lại "pending" | "denied" | "limit". Không cần key."""
    hw, alts, hfresh = req_hw_ids(request.get_json(silent=True) or {})
    if not hw:
        return _json({"ok": False, "status": "error", "loi": "Thiếu mã thiết bị (HWID) — hãy mở panel bằng trình duyệt hoặc gửi header X-HWID."}, 400)
    st = _panel_access(hw, alts, hfresh, client_ip(), request.headers.get("User-Agent", ""))
    return _json({"ok": st == "approved", "status": st, "loi": _PANEL_MSG.get(st, "")}, 429 if st == "limit" else 200)


_GATED_EXACT = {"/api/predictsun", "/api/predict", "/api/predicthittxthuong", "/api/predicthittxmd5", "/api/ips", "/api/history/clear"}


@app.before_request
def _gate_key():
    """KEY_GATE_API bật -> các endpoint dữ liệu đòi key người dùng hợp lệ + HWID thiết bị (còn chỗ thì tự gắn)."""
    p = request.path
    if not KEY_GATE_API or request.method == "OPTIONS" or p not in _GATED_EXACT:
        return None
    k = request.headers.get("X-User-Key", "")
    if not k and p != "/api/ips":                      # /api/ips đã dùng ?key= cho admin key cũ -> chỉ nhận header
        k = request.args.get("key", "")
    hw, alts, hfresh = req_hw_ids()
    if hw and _panel_approved(hw, alts, hfresh, client_ip(), request.headers.get("User-Agent", "")):
        flask_g.key_game = "all"                        # thiết bị ĐÃ ĐƯỢC ADMIN CHÍNH DUYỆT vào panel -> vào cả SUN + HIT, không cần key
        return None
    rec, err, _, kg = _check_user_key(k, hw, client_ip(), request.headers.get("User-Agent", ""), alts, hfresh, _path_game(p))
    if rec:
        flask_g.key_game = kg                           # game của key (history/clear dùng để chỉ cho xóa đúng game)
        return None
    if err.startswith(WRONG_GAME_MSG):                 # key hợp lệ nhưng thuộc game khác
        return _json({"ok": False, "sai_game": True, "game_can": kg, "game": _path_game(p), "loi": err}, 403)
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
    gm = str(b.get("game") or request.args.get("game") or "").strip().lower()    # (tuỳ chọn) kiểm tra key có đúng game này không
    gm = gm if gm in KEY_GAMES else None
    rec, err, exists, kg = _check_user_key(k, hw, ip, request.headers.get("User-Agent", ""), alts, hfresh, gm)
    if not rec:
        if not exists:
            _rl_fail(ip)
        if err.startswith(WRONG_GAME_MSG):
            return _json({"ok": False, "sai_game": True, "game_can": kg, "loi": err}, 403)
        return _json({"ok": False, "dev_locked": err.startswith("Key đã đủ"), "loi": err}, 401)
    _rl_reset(ip)
    return _json({"ok": True, "het_han": rec["exp"], "con_lai_giay": max(0, int(rec["exp"] - time.time())),
                  "game": kg, "game_ten": KEY_GAME_LABEL.get(kg, "Mọi game"),
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
                     "max_dev": _max_dev(r), "so_dev": len(devs), "dung_luc": r.get("last"), "ip_cuoi": r.get("last_ip"), "thiet_bi": tb,
                     "game": _key_game(r) if r.get("type") == "user" else None,                                   # sun | hit | all (key cũ chưa gán game)
                     "game_cu": r.get("type") == "user" and str(r.get("game") or "").lower() not in KEY_GAMES})   # True = key tạo trước khi có chia game
    rows.sort(key=lambda x: -(x["tao_luc"] or 0))
    return _json({"ok": True, "role": s["r"], "name": s["n"], "ngay": list(KEY_DAYS), "so_tb": list(KEY_DEV_OPTIONS),
                  "games": [{"id": g, "ten": KEY_GAME_LABEL[g]} for g in KEY_GAMES], "keys": rows})


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
    if kind == "user" and game not in KEY_GAMES:       # key người dùng PHẢI chọn đúng 1 game (không có key gộp chung)
        return _json({"ok": False, "loi": "chua chon game cho key (sun hoac hit)"}, 400)
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
            k = _new_key("AD" if kind == "sub" else KEY_PREFIX[game], d["keys"])
            d["keys"][k] = {"type": kind, "by": s["r"], "by_name": s["n"], "created": now, "exp": now + days * 86400,
                            "days": days, "note": note, "owner": None, "max_dev": mdev, "devs": {}}
            if kind == "user":
                d["keys"][k]["game"] = game
            made.append(k)
        try:
            _kv_save(d)
        except OSError as e:
            return _json({"ok": False, "loi": f"khong ghi duoc file key: {e}"}, 500)
    return _json({"ok": True, "keys": made, "het_han": now + days * 86400, "max_dev": mdev, "game": game if kind == "user" else None})


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


# ─ DUYỆT THIẾT BỊ VÀO PANEL /api/html — CHỈ ADMIN CHÍNH (xem khối "DUYỆT THIẾT BỊ VÀO PANEL" ở trên) ─
def _need_main():
    s, err = _need_admin()
    if err:
        return None, err
    if s["r"] != "main":
        return None, _json({"ok": False, "loi": "chi admin chinh moi duyet duoc thiet bi vao panel"}, 403)
    return s, None


@app.route("/api/admin/panel")
def api_admin_panel():
    """Danh sách thiết bị đã xin vào panel: chờ duyệt (lên đầu) · đã duyệt · từ chối."""
    s, err = _need_main()
    if err:
        return err
    with _pv_lock:
        devs = _pv_load()["devs"]
        rows = [{"hw": h, "trang_thai": v.get("st"), "lan_dau": v.get("first"), "gan_nhat": v.get("last"), "ip": v.get("ip"), "ua": v.get("ua", ""),
                 "duyet_luc": v.get("dec_at"), "duyet_boi": v.get("dec_by")} for h, v in devs.items()]
    order = {"pending": 0, "approved": 1, "denied": 2}
    rows.sort(key=lambda r: (order.get(r["trang_thai"], 9), -(r["gan_nhat"] or 0)))
    return _json({"ok": True, "devices": rows})


def _panel_admin_act(act):
    """approve / deny / remove cho 1 thiết bị {"hwid": "..."} hoặc nhiều {"hwids": [...]}. remove = xóa khỏi danh sách (đang được duyệt thì mất quyền ngay, phải xin lại)."""
    s, err = _need_main()
    if err:
        return err
    b = request.get_json(silent=True) or {}
    lst = b.get("hwids") if isinstance(b.get("hwids"), list) else [b.get("hwid")]
    want = list(dict.fromkeys(x for x in (_norm_hwid(v) for v in lst[:500]) if x))
    if not want:
        return _json({"ok": False, "loi": "hwid khong hop le"}, 400)
    now = int(time.time())
    done = 0
    with _pv_lock:
        d = _pv_load()
        devs = d["devs"]
        for h in want:
            rec = devs.get(h)
            if not rec:
                continue
            if act == "remove":
                del devs[h]
            else:
                rec["st"] = "approved" if act == "approve" else "denied"
                rec["dec_at"], rec["dec_by"] = now, s["n"]
            done += 1
        if not done:
            return _json({"ok": False, "loi": "khong thay thiet bi"}, 404)
        if not _pv_save(d):
            return _json({"ok": False, "loi": "khong ghi duoc file thiet bi panel"}, 500)
    return _json({"ok": True, "da_xu_ly": done})


@app.route("/api/admin/panel/approve", methods=["POST"])
def api_admin_panel_approve():
    return _panel_admin_act("approve")


@app.route("/api/admin/panel/deny", methods=["POST"])
def api_admin_panel_deny():
    return _panel_admin_act("deny")


@app.route("/api/admin/panel/remove", methods=["POST"])
def api_admin_panel_remove():
    return _panel_admin_act("remove")


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
.bd.g-sun{color:var(--au2);border-color:rgba(242,179,61,.55);background:rgba(242,179,61,.08)}.bd.g-hit{color:#7fd6ff;border-color:rgba(127,214,255,.5);background:rgba(127,214,255,.08)}.bd.g-all{color:var(--mu);border-style:dashed}
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
.pvb{display:inline-flex;align-items:center;justify-content:center;min-width:22px;height:22px;padding:0 8px;margin-left:10px;border-radius:99px;background:var(--au);color:#2a1c00;font-size:12.5px;font-weight:800;vertical-align:middle}
.pr{display:grid;grid-template-columns:minmax(0,1.5fr) minmax(0,1.2fr) auto;gap:8px 18px;align-items:center;padding:13px 2px;border-top:1px solid var(--ln)}
.pr:first-child{border-top:0}
.bd.pd{color:var(--au);border-color:rgba(242,179,61,.55);background:rgba(242,179,61,.08)}.bd.ap{color:var(--ok);border-color:rgba(53,214,160,.45)}.bd.dn{color:var(--no);border-color:rgba(255,107,125,.5)}
.go.sm{width:auto;height:36px;margin:0;padding:0 14px;font-size:14px;display:inline-flex;align-items:center;gap:6px}
@media(max-width:720px){.pr{grid-template-columns:1fr}.pr .ra{justify-content:flex-start;flex-wrap:wrap}}
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
const GN=g=>({sun:'Sun',hit:'Hit'}[g]||'Mọi game');
const gameBd=r=>r.loai==='user'?`<span class="bd g-${esc(r.game)}" title="${r.game_cu?'Key tạo trước khi có chia game — dùng được mọi game':'Key này chỉ dùng cho game '+esc(GN(r.game))}">${esc(GN(r.game))}${r.game_cu?' · key cũ':''}</span>`:'';
const DAYLBL={1:'1 ngày',2:'2 ngày',7:'7 ngày',14:'14 ngày',30:'1 tháng',60:'2 tháng',90:'3 tháng',180:'6 tháng',365:'1 năm'};
const ic=p=>'<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'+p+'</svg>';
const I={key:ic('<circle cx="8" cy="15" r="4"/><path d="M10.8 12.2 20 3m-4 4 3 3m-6-1 2 2"/>'),lock:ic('<path d="M7 11V8a5 5 0 0 1 10 0v3"/><rect x="5" y="11" width="14" height="10" rx="2"/>'),
 copy:ic('<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V6a2 2 0 0 1 2-2h9"/>'),del:ic('<path d="M4 7h16M10 11v6m4-6v6M6 7l1 13h10l1-13M9 7V4h6v3"/>'),
 rf:ic('<path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7"/>'),ok:ic('<path d="m5 12 5 5 9-10"/>'),x:ic('<path d="M6 6l12 12M18 6 6 18"/>'),info:ic('<circle cx="12" cy="12" r="9"/><path d="M12 8v5m0 3h.01"/>'),
 rs:ic('<path d="M3 12a9 9 0 1 0 3-6.7M3 4v5h5"/>'),dev:ic('<rect x="2" y="4" width="20" height="12" rx="2"/><path d="M8 20h8M12 16v4"/>'),out:ic('<path d="M10 4H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h4M16 8l4 4-4 4M20 12H9"/>')};
let S=null;try{S=JSON.parse(sessionStorage.getItem('as')||'null')}catch(e){}
let need=false,busy=false,KEYS=[],DAYS=[1,2,7,14,30,60,90,180,365],NEW=[],F={t:'all',q:''},CF={type:'user',days:30,n:1,dev:1,game:'sun'},GAMES=[{id:'sun',ten:'Sun'},{id:'hit',ten:'Hit'}],DEVO=[1,2,3,5,10,20,50],SEL=new Set(),OPEN=new Set();
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
  if(j.ok){KEYS=j.keys;DAYS=j.ngay||DAYS;DEVO=j.so_tb||DEVO;GAMES=j.games||GAMES;const have=new Set(KEYS.map(r=>r.key));SEL=new Set([...SEL].filter(k=>have.has(k)))}
  paint();
}
const isMain=()=>S&&S.role==='main';
function stats(){
  const live=KEYS.filter(r=>!r.het).length,a=[[KEYS.length,isMain()?'Tổng key':'Key của bạn'],[live,'Còn hạn'],[KEYS.length-live,'Hết hạn']];
  {const us=KEYS.filter(r=>r.loai==='user'),cu=us.filter(r=>r.game==='all').length;a.push([us.filter(r=>r.game==='sun').length,'Key Sun'],[us.filter(r=>r.game==='hit').length,'Key Hit']);if(cu)a.push([cu,'Key cũ (mọi game)'])}
  if(isMain()){const sb=KEYS.filter(r=>r.loai==='sub');a.push([sb.length,'Key admin phụ'],[KEYS.reduce((n,r)=>n+r.so_dev,0),'Thiết bị đang gắn'])}
  return a.map(([n,l])=>`<div><b>${n}</b><span>${l}</span></div>`).join('');
}
function renderDash(){
  const m=isMain();
  $('#app').innerHTML=`<div class="top"><div class="mark">${I.key.replace(/18/g,'22')}</div><div><h1>SUNVIW · Quản trị</h1><span class="role ${m?'m':'s'}">${m?'Admin chính':'Admin phụ · '+esc(S.name)}</span></div><div class="sp"></div><button class="gh" id="out">${I.out} Đăng xuất</button></div>
  <div class="stats" id="stats"></div>
  ${m?'<section class="pn" id="pv"></section>':''}
  <section class="pn"><h2>Tạo key mới</h2>
  ${m?`<div class="seg" id="ct"><button data-t="user" class="on">Key người dùng</button><button data-t="sub">Key admin phụ</button></div>`:''}
  <div id="cgw"${m&&CF.type==='sub'?' hidden':''}><div class="lb">Game của key <span class="mu s">(mỗi key chỉ dùng được cho đúng 1 game — muốn dùng cả 2 game thì tạo 2 key riêng)</span></div><div class="pills" id="cg">${GAMES.map(g=>`<button data-g="${esc(g.id)}" class="${g.id===CF.game?'on':''}">${esc(g.ten)}</button>`).join('')}</div></div>
  <div class="lb">Thời hạn</div><div class="pills" id="cd">${DAYS.map(d=>`<button data-d="${d}" class="${d===CF.days?'on':''}">${DAYLBL[d]||d+' ngày'}</button>`).join('')}</div>
  <div class="lb">Số thiết bị tối đa mỗi key <span class="mu s">(1 key dùng được trên bấy nhiêu máy)</span></div><div class="pills" id="cv">${DEVO.map(v=>`<button data-v="${v}" class="${v===CF.dev?'on':''}">${v} thiết bị</button>`).join('')}</div>
  <div class="fr"><div><div class="lb">Số lượng</div><div class="step"><button data-n="-1" aria-label="Giảm">−</button><b id="cn">${CF.n}</b><button data-n="1" aria-label="Tăng">+</button></div></div>
  <div class="gr"><div class="lb">Ghi chú (không bắt buộc)</div><input class="f" id="cnote" maxlength="40" placeholder="Ví dụ: khách A"></div></div>
  <button class="go mk" id="mk">Tạo key</button><div id="newk"></div></section>
  <section class="pn"><div class="hd"><h2>Danh sách key <span class="mu s" id="cnt"></span></h2><div class="act"><button class="gh" id="rf">${I.rf} Làm mới</button>${m?`<button class="gh dg" id="clean">${I.del} Dọn key hết hạn</button>`:''}</div></div>
  <div class="tb"><input class="f" id="fq" placeholder="Tìm key, người tạo, ghi chú…"><div class="chips" id="ft">${[['all','Tất cả'],['live','Còn hạn'],['exp','Hết hạn'],['sun','Game Sun'],['hit','Game Hit']].concat(m?[['user','Người dùng'],['sub','Admin phụ']]:[]).map(c=>`<button data-f="${c[0]}" class="${F.t===c[0]?'on':''}">${c[1]}</button>`).join('')}</div></div>
  <div class="sel" id="selbar"></div><div id="tbl"></div></section>`;
}
function paint(){
  if(!$('#tbl'))renderDash();
  $('#stats').innerHTML=stats();renderNew();renderTable();renderPv();if(isMain()&&!PVON){PVON=true;loadPanel()}
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
  return `<div class="rw"><div><div class="kk"><label class="ck" title="Chọn để xóa nhiều key"><input type="checkbox" data-sel="${esc(r.key)}"${SEL.has(r.key)?' checked':''}></label><span class="mono">${esc(r.key)}</span><span class="bd ${sub?'sb':'us'}">${sub?'admin phụ':'người dùng'}</span>${gameBd(r)}${r.het?'<span class="bd ex">hết hạn</span>':''}</div></div>
  <div><div class="s">${esc(fmt(r.het_han))}</div><div class="s ${r.het?'':'mu'}" style="${r.het?'color:var(--no)':''}">${esc(left(r.con_lai))}${r.ngay?' · gói '+esc(DAYLBL[r.ngay]||r.ngay+' ngày'):''}</div><div class="bar"><i class="${r.het?'xx':pct<20?'lo':''}" style="width:${pct}%"></i></div></div>
  <div>${who}</div>
  <div class="ra"><button class="gh ib" data-copy="${esc(r.key)}" title="Sao chép" aria-label="Sao chép">${I.copy}</button>${r.so_dev?`<button class="gh ib" data-rs="${esc(r.key)}" title="Reset thiết bị" aria-label="Reset thiết bị">${I.rs}</button>`:''}<button class="gh dg ib" data-del="${esc(r.key)}" title="Xóa" aria-label="Xóa">${I.del}</button></div>${devList(r)}</div>`;
}
/* ── DUYỆT THIẾT BỊ VÀO PANEL HTML (chỉ admin chính) ── */
let PV=[],PF='pending',PFSET=false,PVON=false;
const uaLabel=u=>{u=String(u||'');const os=/iPhone|iPad|iPod/.test(u)?'iOS':/Android/.test(u)?'Android':/Windows/.test(u)?'Windows':/Mac OS X|Macintosh/.test(u)?'macOS':/Linux/.test(u)?'Linux':'?';const br=/Edg\//.test(u)?'Edge':/OPR\/|Opera/.test(u)?'Opera':/Firefox\//.test(u)?'Firefox':/Chrome\/|CriOS/.test(u)?'Chrome':/Safari\//.test(u)?'Safari':'';return os+(br?' · '+br:'')};
async function loadPanel(){
  if(!isMain())return;
  const j=await api('/api/admin/panel');if(!S)return;
  if(j.ok){PV=j.devices;if(!PFSET){PFSET=true;if(!PV.some(x=>x.trang_thai==='pending')&&PV.some(x=>x.trang_thai==='approved'))PF='approved'}}
  renderPv();
}
function pvRow(x){
  const st=x.trang_thai,bdc={pending:'pd',approved:'ap',denied:'dn'}[st]||'',bl={pending:'chờ duyệt',approved:'đã duyệt',denied:'từ chối'}[st]||st;
  const act=(st!=='approved'?`<button class="go sm" data-pa="${esc(x.hw)}">${I.ok} Duyệt</button>`:'')+(st==='pending'?`<button class="gh dg" data-pd="${esc(x.hw)}">Từ chối</button>`:'')+(st!=='pending'?`<button class="gh dg" data-pr="${esc(x.hw)}" title="${st==='approved'?'Thu hồi quyền — thiết bị phải xin duyệt lại':'Xóa khỏi danh sách'}">${I.del} ${st==='approved'?'Gỡ quyền':'Xóa'}</button>`:'');
  return `<div class="pr"><div><div class="kk"><span class="mono" title="${esc(x.hw)}">${esc(shortHw(x.hw))}</span><span class="bd ${bdc}">${bl}</span><span class="mu s">${esc(uaLabel(x.ua))}</span></div><div class="s mu" style="margin-top:3px">IP ${esc(x.ip||'?')}</div></div>
  <div class="s"><div>Gửi yêu cầu: ${esc(fmt(x.lan_dau))}</div><div class="mu">Thấy lần cuối: ${esc(ago(x.gan_nhat))}${x.duyet_luc?' · '+(st==='approved'?'duyệt':'xử lý')+' '+esc(fmt(x.duyet_luc)):''}</div></div>
  <div class="ra">${act}</div></div>`;
}
function renderPv(){
  const el=$('#pv');if(!el)return;
  const cnt={pending:0,approved:0,denied:0};PV.forEach(x=>{if(cnt[x.trang_thai]!==undefined)cnt[x.trang_thai]++});
  const rows=PV.filter(x=>PF==='all'||x.trang_thai===PF),LB={pending:'Chờ duyệt',approved:'Đã duyệt',denied:'Từ chối'};
  el.innerHTML=`<div class="hd"><h2>Duyệt thiết bị vào panel HTML${cnt.pending?`<span class="pvb">${cnt.pending} chờ</span>`:''}</h2><div class="act"><button class="gh" id="pvrf">${I.rf} Làm mới</button></div></div>
  <p class="mu s" style="margin:-6px 0 12px">Ai mở <b>/api/html</b> sẽ thấy bảng chờ duyệt. Thiết bị được duyệt vào được cả Sun lẫn Hit và không cần key. Gỡ quyền → máy đó bị khóa lại trong vài giây.</p>
  <div class="chips">${['pending','approved','denied','all'].map(f=>`<button data-pf="${f}" class="${PF===f?'on':''}">${f==='all'?'Tất cả ('+PV.length+')':LB[f]+' ('+cnt[f]+')'}</button>`).join('')}</div>
  <div>${rows.length?rows.map(pvRow).join(''):`<div class="emp">${PF==='pending'?'Không có thiết bị nào đang chờ duyệt.':'Không có thiết bị nào ở mục này.'}</div>`}</div>`;
}
function visible(){
  const q=(F.q||'').toLowerCase();
  return KEYS.filter(r=>(F.t==='all'||(F.t==='live'?!r.het:F.t==='exp'?r.het:(F.t==='sun'||F.t==='hit')?(r.loai==='user'&&(r.game===F.t||r.game==='all')):r.loai===F.t))&&(!q||[r.key,r.nguoi_tao,r.ghi_chu,r.dung_boi,r.ip_cuoi,r.loai==='user'?GN(r.game):''].join(' ').toLowerCase().includes(q)));
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
  if(d.t&&b.parentNode.id==='ct'){CF.type=d.t;b.parentNode.querySelectorAll('button').forEach(x=>x.classList.toggle('on',x===b));const w=$('#cgw');if(w)w.hidden=CF.type==='sub';return}
  if(d.g&&b.parentNode.id==='cg'){CF.game=d.g;b.parentNode.querySelectorAll('button').forEach(x=>x.classList.toggle('on',x===b));return}
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
    const j=await api('/api/admin/keys/create',{type:isMain()?CF.type:'user',game:CF.game,days:CF.days,count:CF.n,max_dev:CF.dev,note:$('#cnote').value});
    if(j.ok){NEW=j.keys;await loadKeys();toast('Đã tạo '+j.keys.length+' key'+(j.game?' game '+GN(j.game):''))}else toast(j.loi||'Lỗi',1);return}
  if(d.del){if(!await ask('Xóa key '+d.del+'? Người đang dùng key này sẽ bị đăng xuất ngay.','Xóa key'))return;const j=await api('/api/admin/keys/delete',{key:d.del});if(j.ok){NEW=NEW.filter(k=>k!==d.del);await loadKeys();toast('Đã xóa key')}else toast(j.loi||'Lỗi',1);return}
  if(d.rs){if(!await ask('Reset TOÀN BỘ thiết bị đang gắn của key '+d.rs+'? Máy nào dùng key trước sẽ được gắn lại; phiên admin phụ đang mở trên các máy cũ bị đăng xuất.','Reset thiết bị'))return;const j=await api('/api/admin/keys/reset-dev',{key:d.rs});if(j.ok){await loadKeys();toast('Đã gỡ '+j.da_go+' thiết bị')}else toast(j.loi||'Lỗi',1);return}
  if(d.rd){if(!await ask('Gỡ thiết bị '+shortHw(d.hw)+' khỏi key '+d.rd+'?','Gỡ thiết bị'))return;const j=await api('/api/admin/keys/reset-dev',{key:d.rd,hwid:d.hw});if(j.ok){await loadKeys();toast('Đã gỡ thiết bị')}else toast(j.loi||'Lỗi',1);return}
  if(b.id==='pvrf'){await loadPanel();return toast('Đã làm mới')}
  if(d.pf){PF=d.pf;renderPv();return}
  if(d.pa){const j=await api('/api/admin/panel/approve',{hwid:d.pa});if(j.ok){await loadPanel();toast('Đã duyệt — thiết bị vào được panel')}else toast(j.loi||'Lỗi',1);return}
  if(d.pd){if(!await ask('Từ chối thiết bị '+shortHw(d.pd)+'? Thiết bị sẽ thấy thông báo bị từ chối.','Từ chối'))return;const j=await api('/api/admin/panel/deny',{hwid:d.pd});if(j.ok){await loadPanel();toast('Đã từ chối thiết bị')}else toast(j.loi||'Lỗi',1);return}
  if(d.pr){if(!await ask('Gỡ thiết bị '+shortHw(d.pr)+' khỏi danh sách? Nếu đang được duyệt, máy này mất quyền vào panel ngay và phải xin duyệt lại.','Gỡ'))return;const j=await api('/api/admin/panel/remove',{hwid:d.pr});if(j.ok){await loadPanel();toast('Đã gỡ thiết bị')}else toast(j.loi||'Lỗi',1);return}
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
setInterval(()=>{if(S&&isMain()&&$('#pv'))loadPanel()},5000);   /* yêu cầu duyệt mới hiện nhanh (5s) */
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
    return _json(_predict_out(res, err, upd, "sun", "sun", SUN))


def _predict_out(res, err, upd, game, hc_key, cfg, extra=None):
    """JSON dự đoán dùng chung cho SUN và các bàn HITCLUB (cùng cấu trúc). hc_key = khoá mốc xóa lịch sử · cfg = config của bàn đó."""
    out = dict(res["base"])
    out["game"] = game
    if extra:
        out.update(extra)
    out["stale"] = bool(err)
    if err:
        out["loi"] = err
    out["cap_nhat"] = upd
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
    if request.args.get("detail") in ("1", "true", "yes"):
        out["chi_tiet"] = detail
    return out


def _hit_predict(tb):
    """Handler chung của 2 bàn HITCLUB (cùng cấu trúc JSON với /api/predictsun, game="hitclub", thêm ban / ten_ban)."""
    ensure_poller()
    if not tb.active:
        return _json({"ok": False, "game": "hitclub", "ban": tb.key, "loi": "ban dang tat (HITCLUB=0 / ENABLED=False)"}, 503)
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
        return _json({"ok": False, "game": "hitclub", "ban": tb.key,
                      "loi": err or "dang cho phien dau tien tu API Hit (can it nhat 1 phien co ket qua)"}, 503)
    return _json(_predict_out(res, err, upd, "hitclub", tb.key, tb.cfg, {"ban": tb.key, "ten_ban": tb.label}))


@app.route("/api/predicthittxthuong")
def api_predict_hit_thuong():
    """[HITCLUB · TX THƯỜNG] — config riêng HIT_TXTHUONG_CFG · data riêng hittxthuong.json."""
    return _hit_predict(HIT_TABLES["hittxthuong"])


@app.route("/api/predicthittxmd5")
def api_predict_hit_md5():
    """[HITCLUB · TX MD5] — config riêng HIT_TXMD5_CFG · data riêng hittxmd5.json."""
    return _hit_predict(HIT_TABLES["hittxmd5"])


@app.route("/api/history/clear", methods=["POST"])
def api_history_clear():
    """Xóa LỊCH SỬ DỰ ĐOÁN hiển thị: {"game": "sun" | "hittxthuong" | "hittxmd5" | "hitclub" (cả 2 bàn Hit) | "all"}. Chỉ đặt mốc ẩn (xem khối CONFIG XÓA LỊCH SỬ) —
    KHÔNG xóa dữ liệu nào khác và KHÔNG ảnh hưởng logic / WR / AF dự đoán. Trả {"ok":true,"da_xoa":{"sun":N,"hittxthuong":M}} (N, M = số ván vừa ẩn). Key chỉ xóa được game mà nó thuộc về."""
    if not HIST_CLEAR_ENABLED:
        return _json({"ok": False, "loi": "tinh nang xoa lich su dang tat (SUNVIW_HIST_CLEAR=0)"}, 403)
    ensure_poller()
    b = request.get_json(silent=True) or {}
    g = str(b.get("game") or "").strip().lower()
    if g not in ("sun", "hittxthuong", "hittxmd5", "hitclub", "all"):
        return _json({"ok": False, "loi": 'game phai la "sun", "hittxthuong", "hittxmd5", "hitclub" hoac "all"'}, 400)
    allow = _key_tables(getattr(flask_g, "key_game", "all"))      # key game Sun -> chỉ {"sun"} · key game Hit -> 2 bàn Hit · KEY_GATE_API tắt -> tất cả
    want = {"sun": {"sun"}, "hittxthuong": {"hittxthuong"}, "hittxmd5": {"hittxmd5"}, "hitclub": set(HIT_TABLES), "all": {"sun"} | set(HIT_TABLES)}[g]
    if not (want & allow):
        return _json({"ok": False, "sai_game": True, "loi": "key cua ban khong thuoc game nay, khong xoa duoc lich su game do"}, 403)
    want &= allow                                                 # "all" / "hitclub" với key 1 game -> chỉ xóa phần game của key
    done = {}
    if "sun" in want:
        with _state_lock:
            res = _state["result"]
        rows = res["hist"] if res else []                 # mới -> cũ: ván đầu = ván đã chấm mới nhất đang hiển thị
        hide = hist_hidden_upto("sun")
        shown = [r for r in rows if r["phien"] > hide]
        if shown:
            hist_clear("sun", shown[0]["phien"])
        done["sun"] = len(shown)
    for key, tb in HIT_TABLES.items():                    # 2 bàn HITCLUB: mỗi bàn một mốc riêng
        if key in want:
            with tb.slock:
                res = tb.state["result"]
            rows = res["hist"] if res else []
            hide = hist_hidden_upto(key)
            shown = [r for r in rows if r["phien"] > hide]
            if shown:
                hist_clear(key, shown[0]["phien"])
            done[key] = len(shown)
    return _json({"ok": True, "da_xoa": done})


@app.route("/health")
def health():
    ensure_poller()
    with _state_lock:
        s = {k: _state[k] for k in ("latest", "error", "updated", "checked", "polls")}
    s.update(ok=s["error"] is None and s["latest"] is not None, upstream=UPSTREAM_URL,
             poll_sec=POLL_SEC, wr_window=WR_WINDOW, be_final=FLIP_FINAL,
             wr_weights=wr_weights_full(), wr_flip=WR_FLIP_WEIGHT, wr_decay=WR_DECAY, wr_floor=WR_FLOOR, wr_newest=WR_WEIGHT_NEWEST,       # trọng số cũ nhất -> mới nhất
             hist_keep=HIST_KEEP, persist_keep=PERSIST_KEEP, bo_logic=SUN_NAMES,
             af=dict(bat=AF_ENABLED, chi_be_vao_nhom=AF_GROUP_FLIPPED_ONLY, can_da_so_nhom=AF_GROUP_NEED_MAJORITY, flip_low=AF_FLIP_LOW, flip_high=AF_FLIP_HIGH, min_games=AF_MIN_GAMES, mode_window=AF_MODE_WINDOW,
                     vung_be=dict(bat=AF_FLIP_BAND, thap=[AF_FLIP_LOW_MIN, AF_FLIP_LOW_MAX], cao=[AF_FLIP_HIGH_MIN, AF_FLIP_HIGH_MAX]),
                     mode_min=AF_MODE_MIN, mode_below=AF_MODE_BELOW, be_che_do=AF_MODE_FLIP, be_final_af=AF_FLIP_FINAL,
                     be_final_cao_thap=AF_FLIP_FINAL_CT, be_final_all=AF_FLIP_FINAL_ALL),
             xoa_lich_su=dict(bat=HIST_CLEAR_ENABLED, sun_an_den_phien=hist_hidden_upto("sun")),
             ips=ip_health(), panel_duyet=panel_health())
    s["hitclub"] = {"bat": HIT_ENABLED, "ban": {k: tb.health() for k, tb in HIT_TABLES.items()}}
    return _json(s)


@app.route("/")
def index():
    return _json({"ok": True, "api": "SUNVIW"})          # cố ý KHÔNG liệt kê endpoint (/api/html, /api/admin ...)


# Chạy dưới gunicorn (Railway) thì main() không được gọi -> bật poller ngay khi import.
if __name__ != "__main__":
    ensure_poller()


def main():
    global UPSTREAM_URL, POLL_SEC, FLIP_FINAL, WR_FLIP_WEIGHT, HIT_ENABLED
    global AF_ENABLED, AF_FLIP_LOW, AF_FLIP_HIGH, AF_MIN_GAMES, AF_MODE_WINDOW, AF_MODE_BELOW, AF_FLIP_FINAL, AF_FLIP_FINAL_CT, AF_FLIP_FINAL_ALL, AF_MODE_FLIP
    global AF_FLIP_BAND, AF_FLIP_LOW_MIN, AF_FLIP_LOW_MAX, AF_FLIP_HIGH_MIN, AF_FLIP_HIGH_MAX
    global AF_GROUP_FLIPPED_ONLY, AF_GROUP_NEED_MAJORITY
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(description="SUNVIW - API JSON (SUN + HITCLUB: 15 logic chuoi/xuc xac/tong/so phien · key theo game)")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=int(os.environ.get("PORT", 5000)))
    ap.add_argument("--upstream", default=UPSTREAM_URL, help="URL API phien moi nhat (…/api/tx)")
    ap.add_argument("--poll", type=float, default=POLL_SEC, help="chu ky quet upstream (giay)")
    ap.add_argument("--no-hit", action="store_true", help="TAT ca 2 ban HITCLUB (tx thuong + tx md5)")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--flip", action="store_true", help="BẬT bẻ final (đảo TÀI<->XỈU)")
    g.add_argument("--no-flip", action="store_true", help="TẮT bẻ final (giữ nguyên final của các logic đang dùng)")
    wg = ap.add_mutually_exclusive_group()
    wg.add_argument("--wr-flip", action="store_true", help="BẬT flip trọng số WR của SUN (ván CŨ nhất nặng nhất -> giảm dần tới ván MỚI nhất)")
    wg.add_argument("--no-wr-flip", action="store_true", help="TẮT flip trọng số WR của SUN (ván mới nhất nặng nhất)")
    ag = ap.add_mutually_exclusive_group()
    ag.add_argument("--af", action="store_true", help="BẬT AF (auto-flip + CAO/THẤP + bẻ theo WR chế độ) cho SUN")
    ag.add_argument("--no-af", action="store_true", help="TẮT AF, quay về cách chốt cũ của SUN")
    ap.add_argument("--af-low", type=float, default=None, help="AF: WR logic dưới mức này (%%) -> bẻ logic (mặc định AF_FLIP_LOW_DEFAULT)")
    ap.add_argument("--af-high", type=float, default=None, help="AF: WR logic trên mức này (%%) -> bẻ logic (mặc định AF_FLIP_HIGH_DEFAULT)")
    bg = ap.add_mutually_exclusive_group()
    bg.add_argument("--af-band", action="store_true", help="BẬT giới hạn vùng bẻ logic của AF (chỉ bẻ khi WR trong vùng thấp / cao)")
    bg.add_argument("--af-no-band", action="store_true", help="TẮT giới hạn vùng bẻ (quay về ngưỡng --af-low / --af-high như cũ)")
    gfg = ap.add_mutually_exclusive_group()
    gfg.add_argument("--af-group-flipped", action="store_true", help="BẬT: chỉ logic ĐÃ BỊ BẺ mới vào nhóm CAO/THẤP (logic không bẻ mặc định ALL)")
    gfg.add_argument("--af-no-group-flipped", action="store_true", help="TẮT: mọi logic đều được chia nhóm CAO/THẤP như bản trước")
    gmg = ap.add_mutually_exclusive_group()
    gmg.add_argument("--af-group-majority", action="store_true", help="BẬT: nhóm CAO/THẤP phải có >= đa số toàn bộ logic, không thì dùng ALL")
    gmg.add_argument("--af-no-group-majority", action="store_true", help="TẮT: nhóm đông hơn luôn được chọn dù ít logic")
    ap.add_argument("--af-low-min", type=float, default=None, help="AF vùng bẻ THẤP: WR tối thiểu (%%) mới bẻ (mặc định 32)")
    ap.add_argument("--af-low-max", type=float, default=None, help="AF vùng bẻ THẤP: WR tối đa (%%) mới bẻ (mặc định 40)")
    ap.add_argument("--af-high-min", type=float, default=None, help="AF vùng bẻ CAO: WR tối thiểu (%%) mới bẻ (mặc định 60)")
    ap.add_argument("--af-high-max", type=float, default=None, help="AF vùng bẻ CAO: WR tối đa (%%) mới bẻ (mặc định 68)")
    ap.add_argument("--af-min", type=int, default=None, help="AF: số ván đã chấm tối thiểu mới bẻ logic / chia nhóm (mặc định AF_MIN_GAMES_DEFAULT)")
    ap.add_argument("--af-mode-window", type=int, default=None, help="AF: số ván gần nhất của mỗi chế độ để tính WR chế độ (mặc định AF_MODE_WINDOW_DEFAULT)")
    ap.add_argument("--af-mode-below", type=float, default=None, help="AF: WR chế độ dưới mức này (%%) -> bẻ final (mặc định AF_MODE_BELOW_DEFAULT)")
    amg = ap.add_mutually_exclusive_group()
    amg.add_argument("--af-mode-flip", action="store_true", help="BẬT bước 3 của AF: bẻ final theo WR chế độ (mặc định TẮT)")
    amg.add_argument("--af-no-mode-flip", action="store_true", help="TẮT bước 3 của AF: không bẻ final theo WR chế độ")
    afg = ap.add_mutually_exclusive_group()
    afg.add_argument("--af-flip", action="store_true", help="BẺ riêng kết quả AF (đảo TÀI<->XỈU)")
    afg.add_argument("--af-no-flip", action="store_true", help="TẮT bẻ riêng kết quả AF")
    afc = ap.add_mutually_exclusive_group()
    afc.add_argument("--af-flip-ct", action="store_true", help="CHỈ bẻ final của AF khi chế độ CAO/THẤP (chế độ ALL giữ nguyên)")
    afc.add_argument("--af-no-flip-ct", action="store_true", help="TẮT bẻ final riêng cho chế độ CAO/THẤP")
    afa = ap.add_mutually_exclusive_group()
    afa.add_argument("--af-flip-all", action="store_true", help="CHỈ bẻ final của AF khi chế độ ALL (CAO/THẤP giữ nguyên)")
    afa.add_argument("--af-no-flip-all", action="store_true", help="TẮT bẻ final riêng cho chế độ ALL")
    a = ap.parse_args()
    UPSTREAM_URL, POLL_SEC = a.upstream, a.poll
    if a.no_hit:
        HIT_ENABLED = False
    if a.af:
        AF_ENABLED = True
    elif a.no_af:
        AF_ENABLED = False
    if a.af_low is not None:
        AF_FLIP_LOW = a.af_low
    if a.af_high is not None:
        AF_FLIP_HIGH = a.af_high
    if a.af_band:
        AF_FLIP_BAND = True
    elif a.af_no_band:
        AF_FLIP_BAND = False
    if a.af_group_flipped:
        AF_GROUP_FLIPPED_ONLY = True
    elif a.af_no_group_flipped:
        AF_GROUP_FLIPPED_ONLY = False
    if a.af_group_majority:
        AF_GROUP_NEED_MAJORITY = True
    elif a.af_no_group_majority:
        AF_GROUP_NEED_MAJORITY = False
    if a.af_low_min is not None:
        AF_FLIP_LOW_MIN = a.af_low_min
    if a.af_low_max is not None:
        AF_FLIP_LOW_MAX = a.af_low_max
    if a.af_high_min is not None:
        AF_FLIP_HIGH_MIN = a.af_high_min
    if a.af_high_max is not None:
        AF_FLIP_HIGH_MAX = a.af_high_max
    if a.af_min is not None:
        AF_MIN_GAMES = a.af_min
    if a.af_mode_window is not None:
        AF_MODE_WINDOW = a.af_mode_window
    if a.af_mode_below is not None:
        AF_MODE_BELOW = a.af_mode_below
    if a.af_mode_flip:
        AF_MODE_FLIP = True
    elif a.af_no_mode_flip:
        AF_MODE_FLIP = False
    if a.af_flip:
        AF_FLIP_FINAL = True
    elif a.af_no_flip:
        AF_FLIP_FINAL = False
    if a.af_flip_ct:
        AF_FLIP_FINAL_CT = True
    elif a.af_no_flip_ct:
        AF_FLIP_FINAL_CT = False
    if a.af_flip_all:
        AF_FLIP_FINAL_ALL = True
    elif a.af_no_flip_all:
        AF_FLIP_FINAL_ALL = False
    af_apply_limits()                              # chuẩn hoá tham số AF
    if a.flip:
        FLIP_FINAL = True
    elif a.no_flip:
        FLIP_FINAL = False
    if a.wr_flip:
        WR_FLIP_WEIGHT = True
    elif a.no_wr_flip:
        WR_FLIP_WEIGHT = False
    ensure_poller()
    print(f"SUNVIW API  ->  http://{a.host}:{a.port}/api/predict")
    print(f"upstream    ->  {UPSTREAM_URL}")
    print(f"be final SUN ->  {'BAT' if FLIP_FINAL else 'TAT'}  (chi ap cho van quay ve cach cu; van do AF chot khong bi be)")
    print(f"IP          ->  theo doi {'BAT' if IP_TRACK_ENABLED else 'TAT'} · dang dung = co request trong {IP_ACTIVE_SEC}s · tin proxy {'BAT' if IP_TRUST_PROXY else 'TAT'} · admin key {'CO' if IP_ADMIN_KEY else 'KHONG (ai mo panel cung thay danh sach IP)'} · file {IP_PATH}")
    _be_logic = (f"chi be khi WR trong {AF_FLIP_LOW_MIN:g}-{AF_FLIP_LOW_MAX:g}% hoac {AF_FLIP_HIGH_MIN:g}-{AF_FLIP_HIGH_MAX:g}% (ngoai vung khong be)" if AF_FLIP_BAND
                 else f"be logic WR < {AF_FLIP_LOW:g}% hoac > {AF_FLIP_HIGH:g}%")
    print(f"AF SUN      ->  {'BAT' if AF_ENABLED else 'TAT'} · {_be_logic} (toi thieu {AF_MIN_GAMES} van) · be che do {('BAT (CAO/THAP khi WR ' + str(AF_MODE_WINDOW) + ' van gan nhat cua che do < ' + format(AF_MODE_BELOW, 'g') + '%, can ' + str(AF_MODE_MIN) + ' van)') if AF_MODE_FLIP else 'TAT'} · be rieng AF {'BAT' if AF_FLIP_FINAL else 'TAT'}")
    print(f"AF nhom     ->  chi logic bi be vao nhom CAO/THAP {'BAT (logic khong be = ALL)' if AF_GROUP_FLIPPED_ONLY else 'TAT'} · nhom phai >= da so toan bo logic (n//2+1) {'BAT (ít hon -> dung ALL)' if AF_GROUP_NEED_MAJORITY else 'TAT'}")
    print(f"be final AF ->  moi che do {'BAT' if AF_FLIP_FINAL else 'TAT'} · chi CAO/THAP {'BAT (ALL giu nguyen)' if AF_FLIP_FINAL_CT else 'TAT'} · chi ALL {'BAT (CAO/THAP giu nguyen)' if AF_FLIP_FINAL_ALL else 'TAT'}")
    print(f"xoa lich su ->  nut o panel {'BAT' if HIST_CLEAR_ENABLED else 'TAT'} · chi an lich su hien thi (khong dung toi logic / WR / AF) · file moc {HIST_CLEAR_PATH}")
    print(f"PANEL HTML  ->  thiet bi phai duoc admin chinh duyet (khong can key, vao ca Sun + Hit) · file {PANEL_DEV_PATH} · toi da {PANEL_MAX_PENDING_PER_IP} yeu cau cho duyet / IP")
    print(f"WR 100 phien ->  luu toi da {PERSIST_KEEP} van da cham · WR dung/sai xet {EVAL_WINDOW} van gan nhat")
    print(f"WR          ->  xet {WR_WINDOW} van gan nhat, trong so cao nhat x{WR_WEIGHT_NEWEST}, flip trong so {'BAT (cu nhat nang nhat)' if WR_FLIP_WEIGHT else 'TAT (moi nhat nang nhat)'}, trong so (cu -> moi): "
          + " · ".join(f"{w:.2f}" for w in wr_weights_full()))
    print(f"KEY/ADMIN   ->  trang admin /api/admin (1 o nhap key, tu nhan dien · moi key chi thuoc 1 game (sun | hit, chon luc tao; key cu chua gan game = {KEY_LEGACY_GAME}) · moi key gan HWID thiet bi (nhieu thiet bi / key, admin chinh + admin phu deu chon duoc) · bat buoc HWID {'BAT' if HWID_REQUIRED else 'TAT'}) · mat khau admin chinh {'tu env SUNVIW_MAIN_PASS' if _ENV_MAIN_PASS else 'tu hash mac dinh trong code (nen dat SUNVIW_MAIN_PASS)'} · bat key cho API {'BAT' if KEY_GATE_API else 'TAT'} · file key {KEYS_PATH}")
    for _tb in HIT_TABLES.values():
        _c = _tb.cfg
        print(f"HITCLUB {_tb.label:<9} ->  {'BAT' if _tb.active else 'TAT'} · http://{a.host}:{a.port}/api/predict{_tb.key} · gid {_c.GID} · quet moi {_c.POLL_SEC:g}s · file {_tb.path} · "
              f"AF {'BAT' if _c.AF_ENABLED else 'TAT'} · WR xet {_c.WR_WINDOW} van · be final {'BAT' if _c.FLIP_FINAL else 'TAT'} · config RIENG (khoi CONFIG HITCLUB)")
    app.run(host=a.host, port=a.port, threaded=True)


if __name__ == "__main__":
    main()
