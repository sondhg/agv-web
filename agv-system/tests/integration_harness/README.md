# AGV Integration Harness

Bộ test này tập trung vào hai kịch bản đầu tiên trong tài liệu `TEST_SETUP_INSTRUCTION.MD`:

1. Test Case 1: Heartbeat, connection state và LWT.
2. Test Case 2: Order parsing và kiểm tra payload vượt giới hạn buffer.

Mục tiêu là giữ code gọn, dễ đọc, và tách các phần theo trách nhiệm riêng:

- `config.py`: cấu hình topic, broker, timeout.
- `payloads.py`: builder cho connection, state và order payload.
- `mqtt_client.py`: lớp MQTT nhỏ để publish/subscribe và chờ message.
- `runner.py`: CLI chạy testcase.

## Chuẩn bị

Đảm bảo Mosquitto và backend đang chạy, rồi cấu hình các biến môi trường nếu cần:

- `MQTT_BROKER` mặc định là `127.0.0.1`
- `MQTT_PORT` mặc định là `1884`
- `AGV_MANUFACTURER` mặc định là `DATN`
- `AGV_SERIAL` mặc định là `CDEF`

Nếu bạn chạy trong Docker hoặc môi trường khác, chỉ cần override các giá trị này trước khi chạy harness.

## Cách chạy

Từ thư mục `agv-system/`:

```bash
python -m tests.integration_harness.runner --case all --dry-run
```

Chế độ `--dry-run` chỉ kiểm tra việc sinh payload và wiring CLI, không cần broker thật.

Chạy thật với broker MQTT:

```bash
python -m tests.integration_harness.runner --case tc1
python -m tests.integration_harness.runner --case tc2
```

Nếu broker hoặc AGV serial khác mặc định:

```bash
python -m tests.integration_harness.runner --case all --broker 127.0.0.1 --port 1884 --serial CDEF
```

## Kết quả mong đợi

- TC1 pass khi nhận được `connectionState=ONLINE` và ít nhất một bản tin `state`.
- TC2 pass khi publish được một order hợp lệ, publish thêm một payload oversized, và nhận lại được một bản tin `state`.

## Lưu ý

- Bộ test này không giả lập full hành vi firmware. Nó chỉ kiểm tra tầng giao tiếp server-side và payload shape.
- Nếu muốn kiểm tra LWT thực sự, cần để AGV thật/firmware thật kết nối với broker rồi ngắt nguồn thiết bị.
