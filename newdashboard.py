import streamlit as st
import pandas as pd
import time
import os
import plotly.express as px
from plotly.graph_objects import Indicator, Figure
#import plotly.graph_objects as go
import requests

st.set_page_config("IoT Real-Time Weather Dashboard", layout="wide")


st.markdown("""
    <style>
    html, body, [class*="css"] {
        font-family: 'Segoe UI', 'Roboto', sans-serif;
        color: #E0E0E0;
        background-color: #111827;
    }
    h1, h2, h3, h4 {
        color: #00FFFF !important;
        letter-spacing: 0.5px;
    }
    .stApp {
        background-color: #111827;
    }
    .st-expander, .st-expander > div > div {
        background-color: #1F2937;
        border-radius: 8px;
        padding: 10px;
    }
    .stMetric {
        background-color: #1F2937;
        border-radius: 8px;
        padding: 8px 12px;
        font-size: 16px;
    }
    .css-1d391kg {
        background-color: #1E293B !important;
        color: #E5E7EB !important;
    }
    section[data-testid="stSidebar"] {
        background-color: #1E293B;
    }
    .stSelectbox div, .stSlider {
        background-color: #1F2937 !important;
        color: #E0E0E0 !important;
    }
    ::-webkit-scrollbar {
        width: 8px;
    }
    ::-webkit-scrollbar-thumb {
        background-color: #00FFFF;
        border-radius: 10px;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='margin-bottom: 0;'>🌐 IoT Real-Time Weather Dashboard</h1>", unsafe_allow_html=True)
st.markdown("<p style='color:#38bdf8;font-size:16px;'>Live telemetry from global capital cities via Azure IoT Hub</p>", unsafe_allow_html=True)

CSV_PATH = "telemetry_log.csv"

def draw_gauge(value, title, unit, min_val, max_val, color="blue"):
    return Indicator(
        mode="gauge+number",
        value=value,
        title={'text': f"{title} ({unit})"},
        gauge={
            'axis': {'range': [min_val, max_val]},
            'bar': {'color': color}
        }
    )

def show_device_metrics(df, device):
    dev_df = df[df['device'] == device].tail(1)
    if dev_df.empty:
        return st.warning(f"No data for {device}")

    temperature = dev_df["temperature"].values[0]
    humidity = dev_df["humidity"].values[0]
    alert = dev_df["alert"].values[0]
    timestamp = dev_df["timestamp"].values[0]
    city = dev_df["city"].values[0]

    col1, col2 = st.columns(2)
    with col1:
        fig = Figure(draw_gauge(temperature, "Temperature", "°C", -10, 50, "orange"))
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig = Figure(draw_gauge(humidity, "Humidity", "%", 0, 100, "teal"))
        st.plotly_chart(fig, use_container_width=True)

    st.caption(f"📍 City: `{city}` | 📅 Timestamp: `{timestamp}` | 🚨 Alert: `{alert}`")

if not os.path.exists(CSV_PATH):
    st.error("⚠️ Waiting for telemetry data...")
    st.stop()

refresh_interval = st.sidebar.slider("⏱️ Auto-refresh interval (seconds)", 5, 60, 10)

try:
    df = pd.read_csv(CSV_PATH)
    df.columns = df.columns.str.strip().str.lower()

    expected_cols = ["timestamp", "temperature", "humidity", "alert", "device", "city", "lat", "lon"]
    if not all(col in df.columns for col in expected_cols):
        st.error(f"❌ CSV missing columns. Expected: {expected_cols}")
        st.stop()

    df = df[expected_cols]
    df["device"] = df["device"].astype(str)
    df["city"] = df["city"].astype(str)
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")

    device_options = sorted(df["device"].unique())
    selected_device = st.selectbox("📡 Select Device", device_options)
    show_device_metrics(df, selected_device)

    with st.expander("📈 Last 15 readings"):
        st.markdown('<h2 id="recent"></h2>', unsafe_allow_html=True)
        recent_df = df[df["device"] == selected_device].tail(15)
        st.dataframe(recent_df, use_container_width=True)

    with st.expander("📊 Avg Temp/Humidity by Device"):
        st.markdown('<h2 id="metrics"></h2>', unsafe_allow_html=True)
        avg_df = df.groupby("device")[["temperature", "humidity"]].mean()
        st.bar_chart(avg_df)

    with st.expander("🗺️ Global Device Map (Temperature & Humidity)"):
        st.markdown('<h2 id="map"></h2>', unsafe_allow_html=True)
        latest_records = df.dropna(subset=["city", "lat", "lon"]).groupby("device").tail(1)
        if latest_records.empty:
            st.warning("No data to plot yet.")
        else:
            latest_records["text"] = latest_records.apply(
                lambda row: f"📍 <b>{row['city']}</b><br>🌡 Temp: {row['temperature']}°C<br>💧 Humidity: {row['humidity']}%<br>🚨 Alert: {row['alert']}", axis=1
            )
            fig = px.scatter_mapbox(
                latest_records,
                lat="lat",
                lon="lon",
                hover_name="city",
                hover_data={"lat": False, "lon": False, "temperature": False, "humidity": False, "alert": False},
                color="alert",
                color_discrete_map={"NORMAL": "green", "HIGH": "red"},
                zoom=1,
                size_max=20,
                height=500,
                text="text"
            )
            fig.update_layout(mapbox_style="carto-positron", margin={"r": 0, "t": 0, "l": 0, "b": 0})
            fig.update_traces(marker=dict(size=12))
            fig.update_layout(template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)

    device_city_map = {
        "device001": "Dublin",
        "device002": "Mumbai",
        "device003": "Tokyo"
    }

    def fetch_forecast(city):
        url = f"https://api.openweathermap.org/data/2.5/forecast?q={city}&appid=8825007cb988e95d24e21e9ffce75e2a&units=metric"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        return None

    with st.expander("📅 5-Day Forecast by Device Location"):
        st.markdown('<h2 id="forecast"></h2>', unsafe_allow_html=True)
        if selected_device in device_city_map:
            city = device_city_map[selected_device]
            st.write(f"Showing forecast for **{city}**")
            forecast_data = fetch_forecast(city)
            if forecast_data:
                forecast_list = forecast_data["list"]
                forecast_df = pd.DataFrame([{
                    "datetime": entry["dt_txt"],
                    "temperature": entry["main"]["temp"],
                    "humidity": entry["main"]["humidity"],
                    "weather": entry["weather"][0]["main"]
                } for entry in forecast_list])
                fig_temp = px.line(forecast_df, x="datetime", y="temperature", title="Forecasted Temperature")
                fig_temp.update_layout(template="plotly_dark")
                fig_humidity = px.line(forecast_df, x="datetime", y="humidity", title="Forecasted Humidity")
                fig_humidity.update_layout(template="plotly_dark")
                st.plotly_chart(fig_temp, use_container_width=True)
                st.plotly_chart(fig_humidity, use_container_width=True)
            else:
                st.error("Failed to fetch forecast data. Please check API key or city name.")

    with st.expander("📉 Multi-Device Trend Comparison (Temperature / Humidity)"):
        st.markdown('<h2 id="compare"></h2>', unsafe_allow_html=True)
        metric = st.selectbox("Select metric to compare", ["temperature", "humidity"])
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        fig = px.line(
            df,
            x="timestamp",
            y=metric,
            color="device",
            line_group="device",
            markers=True,
            title=f"{metric.capitalize()} Trend Across Devices"
        )
        fig.update_layout(xaxis_title="Timestamp", yaxis_title=metric.capitalize(), template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown('<h2 id="health">📦 Device Health Summary</h2>', unsafe_allow_html=True)
    now = pd.Timestamp.now()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    summary_cols = st.columns(len(device_options))
    for i, device in enumerate(device_options):
        dev_data = df[df["device"] == device]
        if dev_data.empty:
            with summary_cols[i]:
                st.warning(f"No data for {device}")
            continue
        last_seen = dev_data["timestamp"].max()
        minutes_ago = (now - last_seen).total_seconds() / 60
        status = "🟢 Online" if minutes_ago <= 5 else "🔴 Offline"
        avg_temp = dev_data["temperature"].mean()
        avg_hum = dev_data["humidity"].mean()
        cutoff_time = now - pd.Timedelta(hours=24)
        alert_count = dev_data[
            (dev_data["timestamp"] >= cutoff_time) &
            (dev_data["alert"] == "HIGH")
        ].shape[0]
        with summary_cols[i]:
            st.markdown(f"### `{device}`")
            st.markdown(f"{status}")
            st.metric("🌡 Avg Temp (°C)", f"{avg_temp:.1f}")
            st.metric("💧 Avg Humidity (%)", f"{avg_hum:.1f}")
            st.metric("🚨 Alerts (24h)", alert_count)

    time.sleep(refresh_interval)
    st.rerun()

except Exception as e:
    st.error(f"Error loading or displaying data: {e}")
