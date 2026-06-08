# -*- coding: utf-8 -*-
"""
Lab 4 AIoT Energy Forecasting - Modern Streamlit Dashboard
Designed as a modern dark-themed Building Energy Management System (BEMS) Analytics panel.
Visualizes real-time telemetry inputs, FastAPI model serving metrics, risk layers, and audit logs.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import requests
import json
from datetime import datetime
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = PROJECT_ROOT / "outputs" / "forecast_log.csv"
METRICS_PATH = PROJECT_ROOT / "outputs" / "forecast_metrics.json"
PRED_PATH = PROJECT_ROOT / "outputs" / "forecast_test_predictions.csv"

# Page configuration
st.set_page_config(
    page_title="AIoT Energy Forecasting Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject Custom CSS for Premium Dark Theme aesthetics
# Inject Custom CSS for Premium Dark Theme aesthetics
st.markdown("""
<style>
    /* Typography improvements */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Inter', 'Segoe UI', sans-serif;
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    
    /* Premium Metric Card Style */
    .metric-card {
        background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 24px;
        text-align: left;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3), 0 4px 6px -2px rgba(0, 0, 0, 0.1);
        transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    .metric-card::before {
        content: "";
        position: absolute;
        top: 0; left: 0; right: 0; height: 3px;
        background: linear-gradient(90deg, #4f46e5, #38bdf8);
        opacity: 0;
        transition: opacity 0.3s ease;
    }
    .metric-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.4), 0 10px 10px -5px rgba(0, 0, 0, 0.2);
    }
    .metric-card:hover::before {
        opacity: 1;
    }
    .metric-label {
        font-size: 13px;
        color: #94a3b8;
        text-transform: uppercase;
        font-weight: 700;
        letter-spacing: 1px;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .metric-value {
        font-size: 36px;
        font-weight: 800;
        color: #f8fafc;
        line-height: 1;
        margin-bottom: 8px;
    }
    .metric-unit {
        font-size: 16px;
        color: #64748b;
        font-weight: 600;
        margin-left: 4px;
    }
    .metric-desc {
        font-size: 12px;
        color: #64748b;
    }
    
    /* Risk cards styling */
    .risk-badge {
        font-size: 20px;
        font-weight: 800;
        padding: 16px 24px;
        border-radius: 12px;
        text-align: center;
        width: 100%;
        display: inline-block;
        text-transform: uppercase;
        letter-spacing: 2px;
        box-shadow: inset 0 2px 4px 0 rgba(255, 255, 255, 0.1);
    }
    .risk-normal {
        background: linear-gradient(135deg, rgba(34, 197, 94, 0.15) 0%, rgba(21, 128, 61, 0.2) 100%);
        color: #4ade80;
        border: 1px solid rgba(34, 197, 94, 0.3);
    }
    .risk-warning {
        background: linear-gradient(135deg, rgba(245, 158, 11, 0.15) 0%, rgba(180, 83, 9, 0.2) 100%);
        color: #fbbf24;
        border: 1px solid rgba(245, 158, 11, 0.3);
    }
    .risk-high {
        background: linear-gradient(135deg, rgba(239, 68, 68, 0.15) 0%, rgba(185, 28, 28, 0.2) 100%);
        color: #f87171;
        border: 1px solid rgba(239, 68, 68, 0.3);
    }
    .risk-critical {
        background: linear-gradient(135deg, rgba(220, 38, 38, 0.25) 0%, rgba(153, 27, 27, 0.3) 100%);
        color: #fca5a5;
        border: 1px solid rgba(220, 38, 38, 0.5);
        box-shadow: 0 0 20px rgba(220, 38, 38, 0.3);
        animation: pulse-critical 2s infinite;
    }
    
    @keyframes pulse-critical {
        0% { transform: scale(1); box-shadow: 0 0 20px rgba(220, 38, 38, 0.3); }
        50% { transform: scale(1.02); box-shadow: 0 0 30px rgba(220, 38, 38, 0.6); }
        100% { transform: scale(1); box-shadow: 0 0 20px rgba(220, 38, 38, 0.3); }
    }
    
    /* Footer */
    .footer-text {
        text-align: center;
        color: #64748b;
        font-size: 13px;
        margin-top: 60px;
        padding-top: 24px;
        border-top: 1px solid rgba(255, 255, 255, 0.05);
    }
</style>
""", unsafe_allow_html=True)


# --- HELPERS & DATA LOADING ---
@st.cache_data
def load_historical_log():
    if LOG_PATH.exists():
        df = pd.read_csv(LOG_PATH)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df.sort_values("timestamp")
    return None

@st.cache_data
def load_metrics():
    if METRICS_PATH.exists():
        with open(METRICS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def fetch_api_health(api_url):
    try:
        r = requests.get(f"{api_url}/health", timeout=2)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None

def fetch_model_info(api_url):
    try:
        r = requests.get(f"{api_url}/model-info", timeout=2)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None

def send_forecast_request(api_url, history_payload):
    try:
        headers = {"Content-Type": "application/json"}
        r = requests.post(f"{api_url}/forecast", json=history_payload, headers=headers, timeout=3)
        if r.status_code == 200:
            return r.json()
        else:
            return {"error": f"API HTTP Error {r.status_code}", "detail": r.text}
    except Exception as e:
        return {"error": "Không thể kết nối tới API Server", "detail": str(e)}

# --- HEADER COMPONENT ---
def render_header(api_health):
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.markdown("<h1 style='margin-bottom: 0;'>⚡ BEMS AIoT Forecasting Panel</h1>", unsafe_allow_html=True)
        st.markdown("<p style='color: #64748b; margin-top: 4px; font-size: 14px;'>Hệ thống Giám sát & Dự báo năng lượng thông minh - Lab 4</p>", unsafe_allow_html=True)
    with col2:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.markdown(f"""
        <div style='text-align: right; padding-top: 10px;'>
            <div style='font-size: 12px; color: #94a3b8; font-weight:600;'>THỜI GIAN HỆ THỐNG</div>
            <div style='font-size: 16px; font-weight:700; color: #f1f5f9;'>{now_str}</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        if api_health and api_health.get("status") == "ok":
            status_text = "ONLINE"
            status_color = "#22c55e"
            bg_color = "rgba(34, 197, 94, 0.15)"
        else:
            status_text = "OFFLINE"
            status_color = "#ef4444"
            bg_color = "rgba(239, 68, 68, 0.15)"
            
        st.markdown(f"""
        <div style='text-align: right; padding-top: 10px;'>
            <div style='font-size: 12px; color: #94a3b8; font-weight:600;'>TRẠNG THÁI API BACKEND</div>
            <div style='display: inline-block; padding: 4px 12px; border-radius: 4px; background-color: {bg_color}; border: 1px solid {status_color}; font-weight:700; color: {status_color}; font-size: 14px; margin-top: 4px;'>
                ● {status_text}
            </div>
        </div>
        """, unsafe_allow_html=True)
    st.markdown("<hr style='border-color: #334155; margin-top: 10px; margin-bottom: 24px;'>", unsafe_allow_html=True)

# --- MAIN DASHBOARD FLOW ---
def main():
    # --- SIDEBAR CONFIG ---
    st.sidebar.markdown("<h2 style='text-align:center;'>⚙️ Cấu hình AIoT</h2>", unsafe_allow_html=True)
    api_url = st.sidebar.text_input("FastAPI Endpoint URL", value="http://127.0.0.1:8080")
    
    st.sidebar.markdown("<hr style='border-color: #334155;'>", unsafe_allow_html=True)
    
    # Live API Check
    api_health = fetch_api_health(api_url)
    model_info = fetch_model_info(api_url)
    
    # Load Offline Assets
    historical_df = load_historical_log()
    metrics_summary = load_metrics()
    
    # Interactive Simulator in Sidebar
    st.sidebar.markdown("### 🧪 Telemetry Simulator")
    st.sidebar.markdown("<p style='font-size: 12px; color: #94a3b8;'>Giả lập gửi 24 bản tin telemetry thời gian thực lên API để dự báo Wh 10 phút sau.</p>", unsafe_allow_html=True)
    
    if st.sidebar.button("🚀 Khởi chạy Dự báo Sim"):
        if not api_health:
            st.sidebar.error("Lỗi: Server API hiện đang Ngoại tuyến (Offline). Vui lòng chạy lệnh: `uvicorn src.app:app --reload --port 8080` trước.")
        else:
            # Try loading some sample test history
            try:
                # Load sample data or create synthetic history
                sample_data_path = PROJECT_ROOT / "data" / "sample_energydata_complete.csv"
                if not sample_data_path.exists():
                    sample_data_path = PROJECT_ROOT / "data" / "energydata_complete.csv"
                    
                if sample_data_path.exists():
                    test_raw = pd.read_csv(sample_data_path).tail(24)
                    history_points = []
                    for _, r in test_raw.iterrows():
                        history_points.append({
                            "date": str(r["date"]),
                            "Appliances": float(r["Appliances"]),
                            "lights": float(r.get("lights", 0.0)),
                            "T1": float(r.get("T1", 20.0)),
                            "RH_1": float(r.get("RH_1", 40.0)),
                            "T_out": float(r.get("T_out", 10.0))
                        })
                    
                    payload = {"history": history_points}
                    with st.spinner("Đang gọi API `/forecast`..."):
                        response = send_forecast_request(api_url, payload)
                        
                        st.sidebar.success("✅ Phân tích hoàn tất!")
                        st.toast("⚡ Dữ liệu Telemetry đã được dự báo thành công!", icon="🚀")
                        # Add micro-animation for critical states
                        if response["decision"]["risk_level"] == "CRITICAL":
                            st.toast("⚠️ CẢNH BÁO: Phát hiện quá tải lưới điện!", icon="🚨")
                        elif response["decision"]["risk_level"] == "NORMAL":
                            st.balloons()
                            
                        # Store in session state to display in dashboard
                        st.session_state["sim_response"] = response
                        st.session_state["sim_input_last"] = history_points[-1]
                        # Invalidate cache to force reload log
                        st.cache_data.clear()
                else:
                    st.sidebar.error("Không tìm thấy tệp dataset thô để rút trích chuỗi dữ liệu thử nghiệm.")
            except Exception as e:
                st.sidebar.error(f"Lỗi Simulator: {str(e)}")
                
    st.sidebar.markdown("<hr style='border-color: #334155;'>", unsafe_allow_html=True)
    st.sidebar.markdown("### 📊 Chỉ số offline (Huấn luyện)")
    if metrics_summary:
        st.sidebar.markdown(f"**Best Model**: `{metrics_summary.get('best_model_name', 'None')}`")
        st.sidebar.markdown(f"**Offline MAE**: `{metrics_summary['metrics_by_model'].get(metrics_summary.get('best_model_name'), {}).get('mae', 'N/A')} Wh`")
        st.sidebar.markdown(f"**Offline RMSE**: `{metrics_summary['metrics_by_model'].get(metrics_summary.get('best_model_name'), {}).get('rmse', 'N/A')} Wh`")
        st.sidebar.markdown(f"**Offline MAPE**: `{metrics_summary['metrics_by_model'].get(metrics_summary.get('best_model_name'), {}).get('mape_percent', 'N/A')}%`")
    else:
        st.sidebar.markdown("Chưa có metrics offline. Vui lòng chạy huấn luyện.")

    # --- MAIN COMPONENT RENDERING ---
    render_header(api_health)
    
    # 1. TELEMETRY CARDS SECTION
    st.markdown("## 1. GIÁM SÁT PHỤ TẢI HIỆN TẠI & DỰ BÁO TƯƠNG LAI")
    
    # Determine active telemetry data (either from live simulator or last row of offline log)
    current_value = 0.0
    forecast_value = 0.0
    risk_level = "NORMAL"
    recommendation = "CONTINUE_MONITORING"
    reason = "Chưa có tín hiệu thời gian thực."
    model_ver = "forecast_v1"
    horizon_min = 10
    
    if "sim_response" in st.session_state:
        sim_out = st.session_state["sim_response"]
        sim_in = st.session_state["sim_input_last"]
        current_value = float(sim_in["Appliances"])
        forecast_value = float(sim_out["model_output"]["predicted_value"])
        risk_level = sim_out["decision"]["risk_level"]
        recommendation = sim_out["decision"]["recommendation"]
        reason = sim_out["decision"]["reason"]
        model_ver = sim_out["model_output"]["model_version"]
        horizon_min = sim_out["model_output"]["forecast_horizon_minutes"]
    elif historical_df is not None and not historical_df.empty:
        last_row = historical_df.iloc[-1]
        current_value = float(last_row["actual_value"])
        forecast_value = float(last_row["predicted_value"])
        risk_level = str(last_row["risk_level"])
        recommendation = str(last_row["recommendation"])
        reason = str(last_row["reason"])
        model_ver = str(last_row["model_version"])
        
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">🔌 Phụ tải hiện tại (t)</div>
            <div class="metric-value" style="color: #38bdf8;">{current_value:.1f}<span class="metric-unit">Wh</span></div>
            <div class="metric-desc">Công suất đo thực tế</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">🔮 Dự báo tương lai (t+10m)</div>
            <div class="metric-value" style="color: #a78bfa;">{forecast_value:.1f}<span class="metric-unit">Wh</span></div>
            <div class="metric-desc">Ngoại suy bởi {model_ver.split('_')[0].title()}</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">⏱️ Chân trời dự báo (Horizon)</div>
            <div class="metric-value" style="color: #10b981;">{horizon_min}<span class="metric-unit">phút</span></div>
            <div class="metric-desc">1 bước dịch chuyển phụ tải</div>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">🤖 Phiên bản Mô hình</div>
            <div class="metric-value" style="color: #f1f5f9; font-size:24px; padding: 4px 0;">{model_ver}</div>
            <div class="metric-desc">Đã tối ưu hóa tham số AI</div>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("<div style='margin-top: 24px;'></div>", unsafe_allow_html=True)
    
    # 2. RISK AND RECOMMENDATION PANEL
    col_risk, col_rec = st.columns([1, 2])
    with col_risk:
        with st.container(border=True):
            st.markdown("### ⚠️ ĐÁNH GIÁ MỨC RỦI RO LƯỚI ĐIỆN")
            
            # Select badge CSS class
            risk_class = f"risk-{risk_level.lower()}"
            st.markdown(f"""
            <div style="margin-top: 20px; text-align: center;">
                <span class="risk-badge {risk_class}">{risk_level}</span>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <p style="font-size: 13px; color: #cbd5e1; margin-top: 20px; font-style: italic;">
                <strong>Giải trình thống kê</strong>: {reason}
            </p>
            """, unsafe_allow_html=True)
        
    with col_rec:
        with st.container(border=True):
            st.markdown("### 💡 KHUYẾN NGHỊ VẬN HÀNH & CHỐT AN TOÀN")
            
            # Color coding for recommendations
            rec_colors = {
                "HUMAN_CHECK_BEFORE_ACTUATOR_CONTROL": "#ef4444",
                "REDUCE_NON_CRITICAL_LOAD_OR_CHECK_HVAC": "#fbbf24",
                "MONITOR_AND_PREPARE_ENERGY_SAVING_ACTION": "#60a5fa",
                "CONTINUE_MONITORING": "#34d399"
            }
            rec_color = rec_colors.get(recommendation, "#f1f5f9")
            
            st.markdown(f"""
            <div style="margin-top: 16px;">
                <div style="font-size: 12px; color: #94a3b8; font-weight: 600;">HÀNH ĐỘNG KHUYẾN NGHỊ (ACTUATOR/BEMS COMMAND)</div>
                <div style="font-size: 18px; font-weight: 700; color: {rec_color}; margin-top: 4px;">👉 {recommendation}</div>
            </div>
            <div style="margin-top: 20px; border-left: 4px solid #ef4444; padding-left: 16px; background-color: rgba(239, 68, 68, 0.05); padding-top: 8px; padding-bottom: 8px; border-radius: 0 4px 4px 0;">
                <div style="font-size: 11px; color: #fca5a5; font-weight: 700; text-transform: uppercase;">⚠️ LƯU Ý AN TOÀN VẬT LÝ (FAIL-SAFE NOTE)</div>
                <div style="font-size: 13px; color: #cbd5e1; margin-top: 4px;">
                    Tín hiệu dự báo của mô hình AI là tín hiệu khuyến nghị tham khảo. Tuyệt đối lệnh không được tự động kích hoạt ngắt nguồn Rơ-le ở biên nếu chưa thỏa mãn quy tắc khóa cứng (Hard Interlock) nhúng biên và sự phê duyệt thủ công (HITL) của kỹ sư trực vận hành tòa nhà.
                </div>
            </div>
            """, unsafe_allow_html=True)

    # 3. CHART VISUALIZATION SECTION
    st.markdown("## 2. PHÂN TÍCH ĐỒ THỊ LIÊN TỤC (ANALYTICS CHART)")
    
    if historical_df is not None and not historical_df.empty:
        # User option to select slice size
        slice_size = st.slider("Chọn số lượng chu kỳ hiển thị gần đây", min_value=20, max_value=200, value=80, step=10)
        df_slice = historical_df.tail(slice_size).copy()
        
        col_c1, col_c2 = st.columns(2)
        
        with col_c1:
            with st.container(border=True):
                st.markdown("### 📈 Đồ thị So sánh Thực tế vs Dự báo (Wh)")
                
                # Plotly Line Chart for Actual vs Forecast
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=df_slice["timestamp"],
                    y=df_slice["actual_value"],
                    mode='lines+markers',
                    name='Thực tế (Actual Future)',
                    line=dict(color='#38bdf8', width=2),
                    marker=dict(size=4)
                ))
                fig.add_trace(go.Scatter(
                    x=df_slice["timestamp"],
                    y=df_slice["predicted_value"],
                    mode='lines+markers',
                    name='Dự báo (Forecasted)',
                    line=dict(color='#6366f1', width=2, dash='dash'),
                    marker=dict(size=4)
                ))
                
                # Add dynamic warning/critical horizontal lines if noded from metrics
                if metrics_summary:
                    thresholds = metrics_summary.get("risk_thresholds_from_training_target", {})
                    if thresholds:
                        fig.add_hline(y=thresholds.get("warning", 80), line_dash="dot", line_color="#fbbf24", annotation_text="Ngưỡng Warning")
                        fig.add_hline(y=thresholds.get("critical", 220), line_dash="dot", line_color="#ef4444", annotation_text="Ngưỡng Critical")
                
                fig.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    margin=dict(l=20, r=20, t=20, b=20),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color="#f8fafc")),
                    xaxis=dict(gridcolor='rgba(255,255,255,0.05)', tickfont=dict(color='#94a3b8')),
                    yaxis=dict(gridcolor='rgba(255,255,255,0.05)', tickfont=dict(color='#94a3b8')),
                    hovermode="x unified",
                    hoverlabel=dict(bgcolor="rgba(15,23,42,0.9)", font_size=13, font_family="Inter")
                )
                st.plotly_chart(fig, use_container_width=True)
            
        with col_c2:
            with st.container(border=True):
                st.markdown("### 📉 Sai số Dự báo Tức thời theo Thời gian (Wh)")
                
                # Plotly Line Chart for error
                fig_err = go.Figure()
                
                # Zero baseline
                fig_err.add_hline(y=0.0, line_color="#64748b", line_width=1)
                
                fig_err.add_trace(go.Scatter(
                    x=df_slice["timestamp"],
                    y=df_slice["forecast_error"],
                    mode='lines',
                    name='Sai số (Pred - Actual)',
                    line=dict(color='#f43f5e', width=2),
                    fill='tozeroy',
                    fillcolor='rgba(244, 63, 94, 0.1)'
                ))
                
                fig_err.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    margin=dict(l=20, r=20, t=20, b=20),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color="#f8fafc")),
                    xaxis=dict(gridcolor='rgba(255,255,255,0.05)', tickfont=dict(color='#94a3b8')),
                    yaxis=dict(gridcolor='rgba(255,255,255,0.05)', tickfont=dict(color='#94a3b8')),
                    hovermode="x unified",
                    hoverlabel=dict(bgcolor="rgba(15,23,42,0.9)", font_size=13, font_family="Inter")
                )
                st.plotly_chart(fig_err, use_container_width=True)
    else:
        st.info("Chưa có dữ liệu nhật ký lịch sử để hiển thị biểu đồ. Vui lòng chạy huấn luyện hoặc kích hoạt Simulator ở thanh sidebar.")

    # 4. LOG TABLE SECTION
    st.markdown("## 3. NHẬT KÝ ĐỐI SOÁT DỰ BÁO CHI TIẾT (AUDIT FORECAST LOGS)")
    if historical_df is not None and not historical_df.empty:
        with st.container(border=True):
            # Display styled table
            st.dataframe(
                historical_df.sort_values("timestamp", ascending=False),
                column_config={
                    "timestamp": st.column_config.DatetimeColumn("Thời gian", format="YYYY-MM-DD HH:mm:ss"),
                    "actual_value": st.column_config.NumberColumn("Thực tế (Wh)", format="%.1f"),
                    "predicted_value": st.column_config.NumberColumn("Dự báo (Wh)", format="%.1f"),
                    "forecast_error": st.column_config.NumberColumn("Lệch (Wh)", format="%.1f"),
                    "abs_error": st.column_config.NumberColumn("Lệch Tuyệt đối (Wh)", format="%.1f"),
                    "risk_level": "Mức rủi ro",
                    "recommendation": "Khuyến nghị vận hành",
                    "model_version": "Mô hình"
                },
                use_container_width=True,
                hide_index=True
            )
    else:
        st.info("Nhật ký forecast_log.csv trống hoặc chưa được khởi tạo.")

    # Footer credit
    st.markdown("""
    <div class="footer-text">
        BEMS AIoT Forecasting System | Thiết kế bởi Đội ngũ kỹ sư cao cấp DeepMind & Antigravity AI<br>
        Dự án thuộc học phần đào tạo chuyên sâu về AIoT Smart Building & Grid Management.
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
