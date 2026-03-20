import json
import time
import uuid
from datetime import datetime, timezone
import paho.mqtt.client as mqtt

# --- CẤU HÌNH ---
BROKER = "127.0.0.1"
PORT = 1884
MANUFACTURER = "HUST"
SERIAL_NUMBER = "AGV_01"

TOPIC_CONNECTION = f"uagv/v2/{MANUFACTURER}/{SERIAL_NUMBER}/connection"
TOPIC_STATE = f"uagv/v2/{MANUFACTURER}/{SERIAL_NUMBER}/state"
TOPIC_ORDER = f"uagv/v2/{MANUFACTURER}/{SERIAL_NUMBER}/order"
TOPIC_INSTANT_ACTION = f"uagv/v2/{MANUFACTURER}/{SERIAL_NUMBER}/instantActions"

# --- TRẠNG THÁI XE (MEMORY) ---
current_state = {
    "orderId": "",
    "lastNodeId": "Node_A",
    "lastNodeSequenceId": 0,
    "driving": False,
    "nodes_to_visit": [],
    "battery": 100.0,
    "x": 0,
    "y": 0,
}

client = mqtt.Client(client_id=f"mock_agv_{uuid.uuid4().hex[:6]}")


def on_connect(client, userdata, flags, rc):
    print("✅ Connected to Broker")
    client.subscribe([(TOPIC_ORDER, 1), (TOPIC_INSTANT_ACTION, 1)])
    send_connection_message()


def on_message(client, userdata, msg):
    """Nhận Order và nạp vào bộ nhớ"""
    try:
        payload = json.loads(msg.payload.decode())
        if "nodes" in payload:
            print(f"\n🔥 RECEIVED ORDER: {payload['orderId']}")

            # Cập nhật trạng thái xe để bắt đầu chạy
            current_state["orderId"] = payload["orderId"]
            current_state["nodes_to_visit"] = payload["nodes"]  # Lưu danh sách điểm
            current_state["driving"] = True

            # Nếu điểm đầu tiên khác điểm hiện tại -> Xe bắt đầu di chuyển
            print(
                f"   -> Start driving... Path: {len(current_state['nodes_to_visit'])} nodes"
            )

        if "instantActions" in payload:
            print("\n⚡ RECEIVED ACTION!")
            for action in payload["instantActions"]:
                a_type = action["actionType"]
                print(f"   -> Type: {a_type}")

                if a_type == "startPause":
                    current_state["paused"] = True
                    current_state["driving"] = False  # Dừng xe
                    print("   🛑 PAUSED AGV!")

                elif a_type == "stopPause":
                    current_state["paused"] = False
                    if current_state["nodes_to_visit"]:
                        current_state["driving"] = True  # Chạy tiếp nếu còn đường
                    print("   ▶️ RESUMED AGV!")

                elif a_type == "cancelOrder":
                    current_state["nodes_to_visit"] = []  # Xóa hết hành trình
                    current_state["driving"] = False
                    current_state["paused"] = False
                    current_state["orderId"] = "CANCELLED"
                    print("   🗑️ ORDER CANCELLED!")

    except Exception as e:
        print(f"❌ Error: {e}")


def send_connection_message():
    payload = {
        "headerId": 1,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "version": "2.1.0",
        "manufacturer": MANUFACTURER,
        "serialNumber": SERIAL_NUMBER,
        "connectionState": "ONLINE",
    }
    client.publish(TOPIC_CONNECTION, json.dumps(payload), qos=1, retain=True)


def simulate_loop():
    """Vòng lặp mô phỏng hành vi xe"""
    seq_counter = 0

    while True:
        # 1. LOGIC DI CHUYỂN
        if (
            current_state["driving"]
            and current_state["nodes_to_visit"]
            and not current_state.get("paused", False)
        ):
            # Lấy điểm tiếp theo trong danh sách
            next_node = current_state["nodes_to_visit"][0]

            # Giả lập xe đi đến điểm đó (Update vị trí)
            current_state["lastNodeId"] = next_node["nodeId"]
            current_state["lastNodeSequenceId"] = next_node["sequenceId"]

            # Update tọa độ giả (để vẽ map cho đẹp)
            if "nodePosition" in next_node:
                current_state["x"] = next_node["nodePosition"].get("x", 0)
                current_state["y"] = next_node["nodePosition"].get("y", 0)

            # Xóa điểm đã đi qua khỏi danh sách
            current_state["nodes_to_visit"].pop(0)
            print(
                f"🚚 Arrived at {current_state['lastNodeId']} ({current_state['x']}, {current_state['y']})"
            )

            # Nếu hết điểm -> Dừng xe
            if not current_state["nodes_to_visit"]:
                print("🏁 Destination Reached! Stopping...")
                current_state["driving"] = False

        # 2. GỬI STATE LÊN SERVER
        payload = {
            "headerId": seq_counter,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "version": "2.1.0",
            "manufacturer": MANUFACTURER,
            "serialNumber": SERIAL_NUMBER,
            "orderId": current_state["orderId"],
            "lastNodeId": current_state["lastNodeId"],
            "lastNodeSequenceId": current_state["lastNodeSequenceId"],
            "driving": current_state["driving"],
            "paused": current_state.get("paused", False),
            "batteryState": {
                "batteryCharge": current_state["battery"],
                "charging": not current_state["driving"],
            },
            "agvPosition": {
                "x": current_state["x"],
                "y": current_state["y"],
                "mapId": "map_1",
            },
            "errors": [],
        }
        client.publish(TOPIC_STATE, json.dumps(payload), qos=0)

        # 3. NGHỈ (Giả lập thời gian xe chạy giữa các điểm)
        seq_counter += 1
        current_state["battery"] -= 0.1
        time.sleep(5)  # Cứ 5 giây đi được 1 điểm


# --- MAIN ---
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER, PORT, 60)
client.loop_start()

try:
    simulate_loop()
except KeyboardInterrupt:
    client.disconnect()
    print("\n🛑 Stopped.")
