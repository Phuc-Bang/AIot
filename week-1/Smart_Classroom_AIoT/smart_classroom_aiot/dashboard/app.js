// Cấu hình kết nối
const MQTT_WS_URL = "ws://127.0.0.1:9001";
const BACKEND_URL = "http://127.0.0.1:8000";

// Trạng thái thiết bị và chế độ điều khiển
const deviceStates = { light: "OFF", ac: "OFF" };
let currentMode = "auto";

// --- Khởi tạo Biểu đồ ---
const ctx = document.getElementById('tempChart').getContext('2d');
const tempChart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: [],
        datasets: [
            {
                label: 'Nhiệt độ (°C)',
                borderColor: '#ef4444',
                backgroundColor: 'rgba(239, 68, 68, 0.1)',
                data: [],
                borderWidth: 3,
                tension: 0.4,
                fill: true,
                pointRadius: 0
            },
            {
                label: 'Độ ẩm (%)',
                borderColor: '#38bdf8',
                backgroundColor: 'rgba(56, 189, 248, 0.1)',
                data: [],
                borderWidth: 3,
                tension: 0.4,
                fill: true,
                pointRadius: 0
            }
        ]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { labels: { color: '#94a3b8', font: { size: 12 } } }
        },
        scales: {
            x: { grid: { display: false }, ticks: { color: '#64748b' } },
            y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#64748b' } }
        }
    }
});

// --- Kết nối MQTT ---
// addLog được gọi sau khi DOM sẵn sàng (script ở cuối body nên safe, nhưng guard cho chắc)
document.addEventListener('DOMContentLoaded', () => {
    addLog(`Khởi tạo kết nối MQTT tại ${MQTT_WS_URL}...`, "info");
});

const client = mqtt.connect(MQTT_WS_URL, {
    protocolVersion: 4,
    connectTimeout: 5000,
    keepalive: 60
});

client.on('connect', () => {
    addLog("✅ Đã kết nối MQTT thành công!", "success");
    client.subscribe("classroom/#", (err) => {
        if (!err) addLog("📡 Đã đăng ký nhận dữ liệu từ 'classroom/#'", "info");
    });
});

client.on('error', (err) => {
    addLog(`❌ Lỗi MQTT: ${err.message}`, "danger");
});

client.on('message', (topic, message) => {
    try {
        const payload = JSON.parse(message.toString());
        if (topic.includes("sensors")) {
            updateUI(payload);
        } else if (topic.includes("anomaly")) {
            showAnomaly(payload);
        } else if (topic.includes("status")) {
            addLog(`📢 Trạng thái: ${payload.device} đang ${payload.state}`, "warning");
            // Cập nhật UI ngay lập tức dựa trên phản hồi từ actuator
            updateDeviceUI(payload.device, payload.state);
        }
    } catch (e) {
        console.error("Lỗi parse dữ liệu:", e);
    }
});

// --- Cập nhật giao diện ---
function updateDeviceUI(device, state) {
    deviceStates[device] = state; // Đồng bộ state

    if (device === "ac") {
        const acGlow = document.getElementById('ac-glow');
        if (state === "ON") {
            acGlow.style.display = "block";
            document.getElementById('status-ac').innerText = "ON";
            document.getElementById('status-ac').style.color = "#38bdf8";
        } else {
            acGlow.style.display = "none";
            document.getElementById('status-ac').innerText = "OFF";
            document.getElementById('status-ac').style.color = "#94a3b8";
        }
    } else if (device === "light") {
        const l1Glow = document.getElementById('light1-glow');
        const l2Glow = document.getElementById('light2-glow');
        if (state === "ON") {
            l1Glow.style.display = "block";
            l2Glow.style.display = "block";
            document.getElementById('status-light').innerText = "ON";
            document.getElementById('status-light').style.color = "#fbbf24";
        } else {
            l1Glow.style.display = "none";
            l2Glow.style.display = "none";
            document.getElementById('status-light').innerText = "OFF";
            document.getElementById('status-light').style.color = "#94a3b8";
        }
    }
}

function updateUI(data) {
    // 1. Cập nhật các thẻ Stats
    document.getElementById('card-temp').innerText = `${data.temperature.toFixed(1)}°C`;
    document.getElementById('card-hum').innerText = `${data.humidity.toFixed(1)}%`;
    document.getElementById('card-people').innerText = data.people_count;
    document.getElementById('card-power').innerText = `${data.power_consumption.toFixed(2)} kW`;

    // 2. Cập nhật SVG Digital Twin
    document.getElementById('svg-temp').innerText = `${data.temperature.toFixed(1)}°C`;
    document.getElementById('svg-people').innerText = `Sĩ số: ${data.people_count}`;

    // 3. Hiệu ứng thiết bị (Chỉ cập nhật nếu đang ở chế độ AUTO để không ghi đè lệnh MANUAL của user do độ trễ của simulator)
    if (currentMode === "auto") {
        updateDeviceUI("ac", data.ac_state);
        updateDeviceUI("light", data.light_state);
    }

    // 4. Cập nhật biểu đồ
    const now = new Date().toLocaleTimeString();
    tempChart.data.labels.push(now);
    tempChart.data.datasets[0].data.push(data.temperature);
    tempChart.data.datasets[1].data.push(data.humidity);

    if (tempChart.data.labels.length > 20) {
        tempChart.data.labels.shift();
        tempChart.data.datasets[0].data.shift();
        tempChart.data.datasets[1].data.shift();
    }
    tempChart.update('none');
}

// --- Điều khiển ---
async function toggleDevice(device) {
    const currentState = deviceStates[device] || "OFF";
    const newCommand = currentState === "ON" ? "OFF" : "ON";
    addLog(`📤 Gửi lệnh ${device.toUpperCase()} → ${newCommand}`, "warning");
    try {
        const response = await fetch(`${BACKEND_URL}/api/control`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ device, command: newCommand })
        });
        const result = await response.json();
        addLog(`✅ Lệnh đã gửi: ${device} ${newCommand}`, "success");
    } catch (e) {
        addLog(`❌ Lỗi điều khiển: ${e.message}`, "danger");
    }
}

async function toggleMode() {
    const newMode = currentMode === "auto" ? "manual" : "auto";
    try {
        const res = await fetch(`${BACKEND_URL}/api/mode`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mode: newMode })
        });
        const result = await res.json();
        currentMode = result.mode;
        updateModeButton();
        const label = currentMode === "auto" ? "TỰ ĐỘNG (Rule Engine bật)" : "THỦ CÔNG (toàn quyền điều khiển)";
        addLog(`🔄 Chế độ: ${label}`, "info");
    } catch (e) {
        addLog(`❌ Lỗi đổi chế độ: ${e.message}`, "danger");
    }
}

function updateModeButton() {
    const btn = document.getElementById('mode-btn');
    const controlButtons = document.querySelectorAll('.control-buttons button');
    
    if (!btn) return;
    if (currentMode === "auto") {
        btn.innerHTML = '<i class="ph ph-robot"></i> AUTO';
        btn.style.background = "linear-gradient(135deg, #22c55e, #16a34a)";
        controlButtons.forEach(b => {
            b.disabled = true;
            b.style.opacity = "0.5";
            b.style.cursor = "not-allowed";
        });
    } else {
        btn.innerHTML = '<i class="ph ph-hand"></i> MANUAL';
        btn.style.background = "linear-gradient(135deg, #f59e0b, #d97706)";
        controlButtons.forEach(b => {
            b.disabled = false;
            b.style.opacity = "1";
            b.style.cursor = "pointer";
        });
    }
}

// Đồng bộ chế độ từ backend khi tải trang
fetch(`${BACKEND_URL}/api/mode`).then(r => r.json()).then(d => {
    currentMode = d.mode;
    updateModeButton();
}).catch(() => {});

function showAnomaly(data) {
    const panel = document.getElementById('twin-panel');
    const reason = data.reason || data.message || "Phát hiện bất thường";
    addLog(`⚠️ CẢNH BÁO AI [${data.room_id || ""}]: ${reason}`, "danger");
    panel.classList.add('anomaly-active');
    setTimeout(() => panel.classList.remove('anomaly-active'), 5000);
}

function addLog(msg, type = "info") {
    const container = document.getElementById('log-container');
    const entry = document.createElement('div');
    entry.className = `log-entry log-${type}`;
    entry.innerHTML = `[${new Date().toLocaleTimeString()}] ${msg}`;
    container.prepend(entry);
}
