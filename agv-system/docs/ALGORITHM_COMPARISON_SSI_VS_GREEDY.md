# So sánh thuật toán phân công AGV: SSI_MARGINAL vs GREEDY_ETA

## 1. Mục tiêu
Tài liệu này mô tả và so sánh 2 thuật toán phân công task trong hệ thống AGV:
- SSI_MARGINAL: thuật toán chính (auction-based, tối ưu đa mục tiêu).
- GREEDY_ETA: baseline đơn giản để đối chiếu khoa học.

Mục tiêu nghiên cứu:
- Đánh giá hiệu năng vận hành (flow time, throughput, makespan).
- Đánh giá cân bằng tải (CV tasks, CV distance).
- Đánh giá độ bền hệ thống trong tắc nghẽn (deadlock/stuck, permission wait).
- Đánh giá hiệu quả năng lượng (energy per task).

---

## 2. Định nghĩa thuật toán

## 2.1. SSI_MARGINAL (thuật toán chính)
Ý tưởng: với mỗi AGV, ước lượng phần chi phí biên khi nhận thêm task mới, sau đó chuẩn hóa và kết hợp nhiều thành phần chi phí để chọn AGV tốt nhất.

Thành phần chính:
- Queue-aware: xét hàng đợi task đang chờ trên AGV.
- Two-leg aware: xét cả chặng start -> pickup và pickup -> delivery.
- Energy-time tradeoff: cân bằng năng lượng và thời gian.
- Fairness-aware: giảm hiện tượng một AGV bị dồn tải quá mức.
- Constraint-aware: ràng buộc pin, lock khi charging, conflict penalty.

Dạng mục tiêu (mức khái quát):
- MiniSum: giảm tổng chi phí biên toàn cục.
- MiniMax: giảm mức tải cực đại trên một AGV.
- Hybrid: Bid = epsilon * MiniSum + (1 - epsilon) * MiniMax.

## 2.2. GREEDY_ETA (baseline)
Ý tưởng: chọn AGV có thời gian hoàn tất dự kiến nhỏ nhất cho task mới.

Hàm điểm baseline:

bid_greedy_eta = queue_time + time(start -> pickup) + time(pickup -> delivery)

Đặc điểm:
- Có xét queue hiện tại của AGV.
- Có xét đủ 2 chặng vận chuyển.
- Có xét ràng buộc tính khả thi (pin, đường đi).
- Không có cơ chế fairness/hybrid objective như SSI.

Lý do chọn làm baseline:
- Đơn giản, trực quan, dễ giải thích.
- Mạnh hơn baseline quá đơn giản (vd: chỉ nearest pickup).
- Phù hợp làm mốc so sánh công bằng.

---

## 3. Thiết kế thí nghiệm công bằng

## 3.1. Kiểm soát biến
Để so sánh công bằng giữa 2 thuật toán:
- Cùng map (map_id, graph topology).
- Cùng fleet initial state.
- Cùng scenario.
- Cùng seed sinh task (SIM_SCENARIO_SEED).
- Cùng hạ tầng và cấu hình container.

## 3.2. Chuyển thuật toán
Hệ thống hỗ trợ chọn thuật toán qua biến môi trường AUCTION_ALGORITHM:
- SSI_MARGINAL
- GREEDY_ETA
- GREEDY_DISTANCE (tuỳ chọn bổ sung)

Ví dụ chạy:
1. Set AUCTION_ALGORITHM=SSI_MARGINAL, chạy simulation.
2. Set AUCTION_ALGORITHM=GREEDY_ETA, chạy lại cùng seed.
3. So sánh các file metrics xuất ra.

## 3.3. Khuyến nghị lặp thí nghiệm
- Chạy mỗi thuật toán >= 5 lần với các seed khác nhau.
- Báo cáo mean +- std cho các metric chính.
- Dùng test thống kê (nếu đủ mẫu): t-test hoặc Mann-Whitney.

---

## 4. Bộ chỉ số báo cáo
Nguồn dữ liệu từ metrics exporter:
- *_fleet_summary.csv
- *_load_balance.csv
- *_agv_summary.csv
- *_orders.csv
- *_assignments.csv

Các chỉ số nên đưa vào bài báo:
- Throughput (tasks/min): càng cao càng tốt.
- Makespan (s): càng thấp càng tốt.
- Avg flow time per task (s): càng thấp càng tốt.
- Energy per task (%): càng thấp càng tốt.
- CV tasks, CV distance: càng thấp càng cân bằng.
- Stuck event count, deadlock count: càng thấp càng ổn định.
- Total permission wait time (s): càng thấp càng tốt trong môi trường có tranh chấp.
- Avg bidding time (ms): overhead tính toán.

---

## 5. Bảng so sánh định tính
| Tiêu chí | SSI_MARGINAL | GREEDY_ETA |
|---|---|---|
| Mục tiêu | Đa mục tiêu (energy + time + fairness) | Đơn mục tiêu (ETA) |
| Xét hàng đợi | Có | Có |
| Xét 2 chặng pickup-delivery | Có | Có |
| Xử lý pin/charging constraints | Có | Có |
| Chống dồn tải 1 AGV | Tốt (MiniMax + penalty) | Trung bình/yếu |
| Ổn định khi tắc nghẽn | Tốt hơn | Dễ cục bộ hóa |
| Đơn giản triển khai/giải thích | Trung bình | Cao |
| Phù hợp làm baseline khoa học | Có (phương pháp chính) | Rất phù hợp |

---

## 6. Điểm mạnh nổi bật của SSI (nên nhấn mạnh khi trình bày)

1. Tối ưu toàn cục tốt hơn Greedy cục bộ
- Greedy tối ưu ngắn hạn cho từng task.
- SSI tối ưu theo chi phí biên có xét trạng thái hệ thống, giúp giảm hiệu ứng dây chuyền khi tải tăng.

2. Cân bằng tải tốt hơn
- Thành phần MiniMax và penalty giúp tránh hiện tượng một AGV bị “hút” task liên tục.
- Kỳ vọng CV tasks và CV distance thấp hơn.

3. Ổn định hơn dưới cạnh tranh tài nguyên
- SSI có thêm conflict/wait-aware components.
- Trong kịch bản deadlock/contention, SSI thường giảm stuck/deadlock và permission wait.

4. Nâng hiệu quả năng lượng theo cấp đội xe
- Không chỉ tối ưu ETA tức thời, SSI cân nhắc energy marginal và trạng thái pin.
- Kỳ vọng energy per task tốt hơn khi chạy dài hạn.

5. Khả năng mở rộng nghiên cứu
- Dễ mở rộng bằng tuning epsilon, K_ENERGY, K_TIME và các penalty.
- Hỗ trợ phân tích trade-off rõ ràng giữa hiệu suất, công bằng, năng lượng.

---

## 7. Gợi ý cấu trúc phần Results trong bài nghiên cứu

1. Experimental setup
- Map, fleet size, scenario, seed policy, số lần lặp.

2. Main quantitative results
- Bảng metric trung bình và độ lệch chuẩn cho SSI vs GREEDY_ETA.

3. Stress-test analysis
- Kết quả trong deadlock_contention hoặc tải cao.

4. Ablation/parameter discussion
- Ảnh hưởng epsilon, queue penalty, conflict penalty.

5. Threats to validity
- Sai số mô hình năng lượng, giả định cảm biến, độ trễ MQTT.

---

## 8. Kết luận ngắn gợi ý dùng trong slide
GREEDY_ETA là baseline mạnh và công bằng để so sánh vì đã xét queue và 2-chặng vận chuyển. Tuy nhiên, SSI_MARGINAL vượt trội ở tối ưu hệ thống dài hạn nhờ objective đa mục tiêu và cơ chế fairness/conflict-aware, từ đó cải thiện đồng thời hiệu năng, độ ổn định và cân bằng tải trong môi trường AGV nhiều tác nhân.
