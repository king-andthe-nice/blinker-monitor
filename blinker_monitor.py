import json
import time
import os
import paho.mqtt.client as mqtt
import ssl
import requests
from serverchan_sdk import sc_send

# ===================== 你的配置 =====================
# 随便写一个不重复的ID
MY_CLIENT_ID = "3"
MY_USER_ID   = "3"
MY_PASSWORD  = "3"

# 要查询的硬件设备
TARGET_DEVICE = "9B9A77D5PLBP22KLCRYNH4S5"

# Server酱 SendKey（换成你自己的）
SERVERCHAN_SENDKEY = "SCT346756TC2fPdtaZVPV1P8rrGep9icgK"

# 超时等待时间
WAIT_TIMEOUT = 4
# ====================================================

# 状态保存文件（自动创建）
STATE_FILE = "last_state.txt"
result = None
got_response = False

# ------------------- MQTT 消息回调 -------------------
def on_connect(client, userdata, flags, rc, reasonCode):
    print("✅ MQTT 连接成功")
    client.subscribe(f"/device/{MY_CLIENT_ID}/r")
    
    payload = {
        "fromDevice": MY_CLIENT_ID,
        "toDevice": TARGET_DEVICE,
        "deviceType": "DiyArduino",
        "data": {"get": "state"}
    }
    client.publish(f"/device/{MY_CLIENT_ID}/s", json.dumps(payload))

def on_message(client, userdata, msg):
    global result, got_response
    try:
        data = json.loads(msg.payload.decode())
        if "data" in data and "state" in data["data"]:
            result = "online"
            got_response = True
    except:
        pass

# ------------------- 发送 Server 酱微信消息 -------------------
def send_wechat(title, content):
    try:
        sc_send(SERVERCHAN_SENDKEY, title, content)
        print("📩 微信消息已发送")
    except Exception as e:
        print("❌ 微信消息发送失败", e)

# ------------------- 读取 / 保存 上一次状态 -------------------
# 获取上一次状态（从 GitHub 变量）
def get_last_state():
    try:
        repo = os.getenv("GITHUB_REPOSITORY")
        token = os.getenv("GITHUB_TOKEN")
        url = f"https://api.github.com/repos/{repo}/actions/variables/LAST_STATE"
        headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            return r.json()["value"]
    except:
        return None
    return None

# 保存新状态（写入 GitHub 变量）
def save_state(state):
    try:
        repo = os.getenv("GITHUB_REPOSITORY")
        token = os.getenv("GITHUB_TOKEN")
        url = f"https://api.github.com/repos/{repo}/actions/variables/LAST_STATE"
        headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
        data = {"name": "LAST_STATE", "value": state}
        requests.patch(url, json=data, headers=headers)
    except:
        pass

# ------------------- 主逻辑 -------------------
if __name__ == "__main__":
    print("="*50)
    print("         点灯设备在线状态查询（云端版）")
    print("="*50)

    # 1. 连接MQTT并查询
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, MY_CLIENT_ID, protocol=mqtt.MQTTv311)
    client.username_pw_set(MY_USER_ID, MY_PASSWORD)
    client.tls_set(cert_reqs=ssl.CERT_NONE)
    client.tls_insecure_set(True)
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect("broker.diandeng.tech", 1884, 60)
    except:
        print("❌ 连接服务器失败")
        current_state = "offline"
    else:
        client.loop_start()
        start = time.time()
        while time.time() - start < WAIT_TIMEOUT:
            if got_response:
                break
            time.sleep(0.2)
        client.loop_stop()
        client.disconnect()
        current_state = result if result == "online" else "offline"

    # 2. 打印本次状态
    if current_state == "online":
        print("✅ 设备【在线】")
    else:
        print("❌ 设备【不在线】")

    # 3. 状态变化判断（只有变了才发微信）
    last_state = get_last_state()

    if last_state != current_state:
        print("🔔 设备状态发生变化！")
        
        if current_state == "online":
            send_wechat("设备已上线", "✅ 点灯设备恢复在线")
        else:
            send_wechat("设备已离线", "❌ 点灯设备断开连接")
        
        # 保存新状态
        save_state(current_state)
    else:
        print("ℹ️  设备状态未变化，不发送微信")

    print("="*50)
    print("程序正常退出\n")
