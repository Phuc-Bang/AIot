#!/usr/bin/env python3
"""
Lab 5 - AIoT Inference Service API Client Demo
This script demonstrates how to call the FastAPI server endpoints from an external Python application.
Supports telemetry anomaly detection, forecasting, risk assessment, image classification, and image annotation.
"""
import os
import sys
import argparse
import requests
from pathlib import Path

# ANSI colors for styling console outputs
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(title: str):
    print(f"\n{Colors.HEADER}{Colors.BOLD}=== {title} ==={Colors.ENDC}")

def check_health(base_url: str) -> bool:
    print_header("1. KIỂM TRA TRẠNG THÁI HỆ THỐNG (/health)")
    url = f"{base_url}/health"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"{Colors.OKGREEN}[SUCCESS]{Colors.ENDC} Kết nối thành công!")
            print(f" - Trạng thái dịch vụ: {data.get('service_status')}")
            print(f" - Thư mục mô hình: {data.get('model_dir')}")
            print(f" - Mô hình Vision đã nạp: {data.get('vision_model_loaded')}")
            return True
        else:
            print(f"{Colors.FAIL}[FAIL]{Colors.ENDC} Server phản hồi mã lỗi: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"{Colors.FAIL}[ERROR]{Colors.ENDC} Không thể kết nối tới server tại {base_url}.")
        print(f"Lưu ý: Hãy đảm bảo Docker container Lab 5 đang chạy (mặc định map vào cổng 8001). Chi tiết lỗi: {e}")
        return False

def get_model_info(base_url: str):
    print_header("2. LẤY THÔNG TIN CÁC MÔ HÌNH (/model-info)")
    url = f"{base_url}/model-info"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        print(f"{Colors.OKGREEN}[SUCCESS]{Colors.ENDC} Đã nhận thông tin mô hình:")
        print(f" - Loại dịch vụ: {data.get('service_type')}")
        print(" - Các mô hình cảm biến:")
        for task, name in data.get('sensor_models', {}).items():
            print(f"   + {task}: {name}")
        print(" - Lộ trình học định dạng mô hình:")
        for step in data.get('model_format_learning_path', []):
            print(f"   * {step}")
    else:
        print(f"{Colors.FAIL}[FAIL]{Colors.ENDC} Không lấy được thông tin: {response.text}")

def detect_anomaly(base_url: str):
    print_header("3. KIỂM TRA DỊ THƯỜNG DỮ LIỆU CẢM BIẾN (/detect-anomaly)")
    url = f"{base_url}/detect-anomaly"
    # Dữ liệu giả lập gửi từ thiết bị IoT
    payload = {
        "target": "temperature",
        "current_value": 38.5,
        "recent_values": [26.5, 27.0, 26.8, 27.2, 27.5, 27.1, 26.9],
        "threshold_z": 2.0
    }
    print(f"Gửi dữ liệu kiểm tra: Nhiệt độ hiện tại = {payload['current_value']} °C, Ngưỡng Z-Score = {payload['threshold_z']}")
    
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        data = response.json()
        model_output = data.get("model_output", {})
        event = data.get("event", {})
        z_score = model_output.get("anomaly_score", 0.0)
        is_anomaly = model_output.get("is_anomaly", False)
        
        print(f"{Colors.OKGREEN}[SUCCESS]{Colors.ENDC} Kết quả phân tích từ AI Server:")
        print(f" - Z-Score tính toán: {z_score:.4f}")
        if is_anomaly:
            print(f" - {Colors.FAIL}CẢNH BÁO DỊ THƯỜNG!{Colors.ENDC} Mức độ: {event.get('severity')}")
            print(f"   Lý do: {event.get('explanation')}")
        else:
            print(f" - Dữ liệu bình thường. Mức độ an toàn: {event.get('severity')}")
    else:
        print(f"{Colors.FAIL}[FAIL]{Colors.ENDC} Lỗi khi phân tích dị thường: {response.text}")

def forecast_values(base_url: str) -> float:
    print_header("4. DỰ BÁO CHỈ SỐ CẢM BIẾN (/forecast)")
    url = f"{base_url}/forecast"
    # Dữ liệu chuỗi thời gian khí CO2 gửi từ phòng học nhúng
    payload = {
        "target": "co2",
        "recent_values": [800.0, 850.0, 900.0, 960.0, 1020.0, 1100.0],
        "horizon_minutes": 15
    }
    print(f"Gửi chuỗi dữ liệu CO2 gần đây: {payload['recent_values']}")
    print(f"Yêu cầu dự báo cho {payload['horizon_minutes']} phút tiếp theo...")
    
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        data = response.json()
        predicted_val = data.get("model_output", {}).get("predicted_value")
        print(f"{Colors.OKGREEN}[SUCCESS]{Colors.ENDC} Dự báo từ server:")
        print(f" - Giá trị dự đoán: {predicted_val:.2f} ppm")
        print(f" - Sử dụng thuật toán: {data.get('model_output', {}).get('model_version')}")
        return predicted_val
    else:
        print(f"{Colors.FAIL}[FAIL]{Colors.ENDC} Lỗi khi dự báo: {response.text}")
        return 0.0

def predict_risk(base_url: str, predicted_value: float):
    print_header("5. ĐÁNH GIÁ MỨC ĐỘ RỦI RO (/predict-risk)")
    url = f"{base_url}/predict-risk"
    payload = {
        "target": "co2",
        "predicted_value": predicted_value,
        "warning_threshold": 1000.0,
        "high_threshold": 1200.0
    }
    print(f"Gửi đánh giá rủi ro với giá trị CO2 dự báo = {payload['predicted_value']:.2f} ppm")
    print(f"Ngưỡng Cảnh báo = {payload['warning_threshold']} ppm, Ngưỡng Nguy hiểm = {payload['high_threshold']} ppm")
    
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        data = response.json()
        decision = data.get("decision", {})
        risk_level = decision.get("risk_level")
        
        print(f"{Colors.OKGREEN}[SUCCESS]{Colors.ENDC} Kết quả đánh giá:")
        if risk_level == "HIGH":
            print(f" - Mức độ rủi ro: {Colors.FAIL}{Colors.BOLD}NGUY HIỂM (HIGH){Colors.ENDC}")
        elif risk_level == "WARNING":
            print(f" - Mức độ rủi ro: {Colors.WARNING}{Colors.BOLD}CẢNH BÁO (WARNING){Colors.ENDC}")
        else:
            print(f" - Mức độ rủi ro: {Colors.OKGREEN}AN TOÀN (NORMAL){Colors.ENDC}")
        print(f" - Hành động đề xuất: {decision.get('recommendation')}")
    else:
        print(f"{Colors.FAIL}[FAIL]{Colors.ENDC} Lỗi khi đánh giá rủi ro: {response.text}")

def classify_image(base_url: str, image_path: str):
    print_header("6. SUY LUẬN NHẬN DIỆN ẢNH (/classify-image)")
    url = f"{base_url}/classify-image"
    
    if not os.path.exists(image_path):
        print(f"{Colors.FAIL}[ERROR]{Colors.ENDC} Tệp tin ảnh không tồn tại tại: {image_path}")
        return
        
    print(f"Đọc ảnh từ: {image_path} và gửi lên AI Server...")
    
    with open(image_path, "rb") as f:
        files = {"file": (os.path.basename(image_path), f, "image/jpeg")}
        # Query parameter lấy Top 3 dự đoán
        params = {"top_k": 3}
        
        response = requests.post(url, files=files, params=params)
        
    if response.status_code == 200:
        data = response.json()
        predictions = data.get("model_output", {}).get("predictions", [])
        print(f"{Colors.OKGREEN}[SUCCESS]{Colors.ENDC} Dự đoán phân loại từ ONNX Model:")
        for pred in predictions:
            print(f" - Top {pred['rank']}: {Colors.BOLD}{pred['class_name']}{Colors.ENDC} (Confidence: {pred['confidence'] * 100:.2f}%)")
    else:
        print(f"{Colors.FAIL}[FAIL]{Colors.ENDC} Lỗi phân loại ảnh: {response.text}")

def classify_image_annotated(base_url: str, image_path: str, output_path: str):
    print_header("7. TẢI ẢNH ĐÃ VẼ NHÃN DỰ ĐOÁN (/classify-image-annotated)")
    url = f"{base_url}/classify-image-annotated"
    
    if not os.path.exists(image_path):
        print(f"{Colors.FAIL}[ERROR]{Colors.ENDC} Tệp tin ảnh không tồn tại tại: {image_path}")
        return
        
    print(f"Gửi ảnh lên server vẽ nhãn và tải kết quả...")
    
    with open(image_path, "rb") as f:
        files = {"file": (os.path.basename(image_path), f, "image/jpeg")}
        response = requests.post(url, files=files, stream=True)
        
    if response.status_code == 200:
        # Đảm bảo thư mục đầu ra tồn tại
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "wb") as f_out:
            for chunk in response.iter_content(chunk_size=8192):
                f_out.write(chunk)
        print(f"{Colors.OKGREEN}[SUCCESS]{Colors.ENDC} Đã lưu ảnh kết quả kèm nhãn dự đoán tại:")
        print(f" ➡️ {output_path}")
    else:
        print(f"{Colors.FAIL}[FAIL]{Colors.ENDC} Lỗi xử lý ảnh gắn nhãn: {response.status_code}")

def main():
    parser = argparse.ArgumentParser(description="Lab 5 AIoT API Client Demonstration Tool")
    parser.add_argument("--url", default="http://localhost:8001", help="Base URL of the FastAPI inference service")
    parser.add_argument("--image", default="sample_images/classroom_object.jpg", help="Path to sample image for classification")
    parser.add_argument("--output", default="outputs/client/annotated_response.png", help="Path to save output annotated image")
    parser.add_argument("--task", default="all", choices=["all", "health", "info", "anomaly", "forecast", "risk", "classify", "annotate"],
                        help="Select a specific request task to test")
    
    args = parser.parse_args()
    base_url = args.url.rstrip('/')
    
    print(f"{Colors.BOLD}Khởi động Client gọi vào AI Server tại: {base_url}{Colors.ENDC}")
    
    # Check connection health first
    if not check_health(base_url) and args.task != "health":
        print(f"\n{Colors.WARNING}Dừng chương trình do không kết nối được tới server.{Colors.ENDC}")
        sys.exit(1)
        
    if args.task in ("all", "info"):
        get_model_info(base_url)
        
    if args.task in ("all", "anomaly"):
        detect_anomaly(base_url)
        
    predicted_val = 0.0
    if args.task in ("all", "forecast"):
        predicted_val = forecast_values(base_url)
        
    if args.task in ("all", "risk"):
        # If running separately, provide a default forecast value
        val = predicted_val if predicted_val > 0.0 else 1150.0
        predict_risk(base_url, val)
        
    if args.task in ("all", "classify"):
        classify_image(base_url, args.image)
        
    if args.task in ("all", "annotate"):
        classify_image_annotated(base_url, args.image, args.output)

    print(f"\n{Colors.OKGREEN}{Colors.BOLD}=== HOÀN THÀNH TOÀN BỘ YÊU CẦU ==={Colors.ENDC}\n")

if __name__ == "__main__":
    main()
