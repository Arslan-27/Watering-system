import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sqlite3
import json
import requests
import time
from threading import Thread
import schedule

# Page configuration
st.set_page_config(
    page_title="🌱 IoT Watering System",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Database setup
def init_database():
    conn = sqlite3.connect('watering_system.db')
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sensor_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT,
            timestamp INTEGER,
            moisture_percent INTEGER,
            moisture_raw INTEGER,
            pump_state BOOLEAN,
            manual_mode BOOLEAN,
            dry_threshold INTEGER,
            wet_threshold INTEGER,
            wifi_rssi INTEGER,
            free_heap INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            hour INTEGER,
            minute INTEGER,
            duration INTEGER,
            enabled BOOLEAN,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pump_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT,
            trigger_type TEXT,
            moisture_level INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

# Database operations
def insert_sensor_data(data):
    conn = sqlite3.connect('watering_system.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO sensor_data 
        (device_id, timestamp, moisture_percent, moisture_raw, pump_state, manual_mode, 
         dry_threshold, wet_threshold, wifi_rssi, free_heap)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data['device_id'], data['timestamp'], data['moisture_percent'], data['moisture_raw'],
        data['pump_state'], data['manual_mode'], data['dry_threshold'], data['wet_threshold'],
        data['wifi_rssi'], data['free_heap']
    ))
    
    conn.commit()
    conn.close()

def get_recent_data(hours=24):
    conn = sqlite3.connect('watering_system.db')
    query = '''
        SELECT * FROM sensor_data 
        WHERE created_at >= datetime('now', '-{} hours')
        ORDER BY created_at DESC
    '''.format(hours)
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_latest_data():
    conn = sqlite3.connect('watering_system.db')
    query = 'SELECT * FROM sensor_data ORDER BY created_at DESC LIMIT 1'
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df.iloc[0] if not df.empty else None

def save_schedule(name, hour, minute, duration, enabled):
    conn = sqlite3.connect('watering_system.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO schedules (name, hour, minute, duration, enabled)
        VALUES (?, ?, ?, ?, ?)
    ''', (name, hour, minute, duration, enabled))
    
    conn.commit()
    conn.close()

def get_schedules():
    conn = sqlite3.connect('watering_system.db')
    df = pd.read_sql_query('SELECT * FROM schedules ORDER BY hour, minute', conn)
    conn.close()
    return df

def delete_schedule(schedule_id):
    conn = sqlite3.connect('watering_system.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM schedules WHERE id = ?', (schedule_id,))
    conn.commit()
    conn.close()

def log_pump_action(action, trigger_type, moisture_level):
    conn = sqlite3.connect('watering_system.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO pump_logs (action, trigger_type, moisture_level)
        VALUES (?, ?, ?)
    ''', (action, trigger_type, moisture_level))
    
    conn.commit()
    conn.close()

# ESP8266 Communication
def send_command_to_esp(command, esp_ip="192.168.1.100"):
    try:
        response = requests.post(f"http://{esp_ip}/api/{command}", timeout=5)
        return response.status_code == 200
    except:
        return False

# Initialize database
init_database()

# Sidebar
st.sidebar.title("🌱 IoT Watering System")
st.sidebar.markdown("---")

# ESP8266 IP Configuration
esp_ip = st.sidebar.text_input("ESP8266 IP Address", value="192.168.1.100")
st.sidebar.markdown("---")

# Manual Controls
st.sidebar.subheader("Manual Control")
col1, col2 = st.sidebar.columns(2)

with col1:
    if st.button("💧 Pump ON"):
        if send_command_to_esp("pump/on", esp_ip):
            st.sidebar.success("Pump turned ON")
            log_pump_action("ON", "Manual", 0)
        else:
            st.sidebar.error("Failed to send command")

with col2:
    if st.button("⏹️ Pump OFF"):
        if send_command_to_esp("pump/off", esp_ip):
            st.sidebar.success("Pump turned OFF")
            log_pump_action("OFF", "Manual", 0)
        else:
            st.sidebar.error("Failed to send command")

if st.sidebar.button("🤖 Auto Mode"):
    if send_command_to_esp("mode/auto", esp_ip):
        st.sidebar.success("Auto mode enabled")
    else:
        st.sidebar.error("Failed to send command")

st.sidebar.markdown("---")

# Threshold Settings
st.sidebar.subheader("Threshold Settings")
dry_threshold = st.sidebar.slider("Dry Threshold (%)", 0, 100, 30)
wet_threshold = st.sidebar.slider("Wet Threshold (%)", 0, 100, 50)

if st.sidebar.button("Update Thresholds"):
    # Send to ESP8266
    try:
        response = requests.post(f"http://{esp_ip}/api/thresholds", 
                               data={"dry": dry_threshold, "wet": wet_threshold}, 
                               timeout=5)
        if response.status_code == 200:
            st.sidebar.success("Thresholds updated")
        else:
            st.sidebar.error("Failed to update thresholds")
    except:
        st.sidebar.error("Connection failed")

# Main content
st.title("🌱 IoT Automatic Watering System Dashboard")

# Get latest data
latest_data = get_latest_data()

if latest_data is not None:
    # Current Status
    st.subheader("📊 Current Status")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Soil Moisture", 
            f"{latest_data['moisture_percent']}%",
            delta=None
        )
    
    with col2:
        pump_status = "ON" if latest_data['pump_state'] else "OFF"
        st.metric("Pump Status", pump_status)
    
    with col3:
        mode = "Manual" if latest_data['manual_mode'] else "Auto"
        st.metric("Mode", mode)
    
    with col4:
        st.metric("WiFi Signal", f"{latest_data['wifi_rssi']} dBm")
    
    # Moisture gauge
    fig_gauge = go.Figure(go.Indicator(
        mode = "gauge+number+delta",
        value = latest_data['moisture_percent'],
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Soil Moisture Level"},
        delta = {'reference': 50},
        gauge = {
            'axis': {'range': [None, 100]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, 30], 'color': "red"},
                {'range': [30, 50], 'color': "yellow"},
                {'range': [50, 100], 'color': "green"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 30
            }
        }
    ))
    
    st.plotly_chart(fig_gauge, use_container_width=True)
    
    # Historical Data
    st.subheader("📈 Historical Data")
    
    # Time range selector
    time_range = st.selectbox("Select time range", 
                             ["Last 1 hour", "Last 6 hours", "Last 24 hours", "Last 7 days"])
    
    hours_map = {
        "Last 1 hour": 1,
        "Last 6 hours": 6,
        "Last 24 hours": 24,
        "Last 7 days": 168
    }
    
    df = get_recent_data(hours_map[time_range])
    
    if not df.empty:
        df['created_at'] = pd.to_datetime(df['created_at'])
        
        # Moisture chart
        fig_moisture = px.line(df, x='created_at', y='moisture_percent', 
                              title='Soil Moisture Over Time',
                              labels={'created_at': 'Time', 'moisture_percent': 'Moisture (%)'})
        fig_moisture.add_hline(y=dry_threshold, line_dash="dash", line_color="red", 
                              annotation_text="Dry Threshold")
        fig_moisture.add_hline(y=wet_threshold, line_dash="dash", line_color="green", 
                              annotation_text="Wet Threshold")
        st.plotly_chart(fig_moisture, use_container_width=True)
        
        # Pump activity
        pump_data = df[df['pump_state'] == True]
        if not pump_data.empty:
            fig_pump = px.scatter(pump_data, x='created_at', y='moisture_percent', 
                                 title='Pump Activity',
                                 labels={'created_at': 'Time', 'moisture_percent': 'Moisture (%) when pump was ON'})
            st.plotly_chart(fig_pump, use_container_width=True)

# Scheduling System
st.subheader("⏰ Watering Schedule")

# Add new schedule
with st.expander("Add New Schedule"):
    col1, col2, col3 = st.columns(3)
    
    with col1:
        schedule_name = st.text_input("Schedule Name", "Morning Watering")
        schedule_hour = st.number_input("Hour (24h format)", 0, 23, 7)
    
    with col2:
        schedule_minute = st.number_input("Minute", 0, 59, 0)
        schedule_duration = st.number_input("Duration (minutes)", 1, 60, 5)
    
    with col3:
        schedule_enabled = st.checkbox("Enabled", True)
        
        if st.button("Add Schedule"):
            save_schedule(schedule_name, schedule_hour, schedule_minute, schedule_duration, schedule_enabled)
            st.success("Schedule added!")
            st.experimental_rerun()

# Display existing schedules
schedules_df = get_schedules()
if not schedules_df.empty:
    st.subheader("Current Schedules")
    
    for idx, schedule in schedules_df.iterrows():
        col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])
        
        with col1:
            st.write(f"**{schedule['name']}**")
        
        with col2:
            st.write(f"{schedule['hour']:02d}:{schedule['minute']:02d}")
        
        with col3:
            st.write(f"{schedule['duration']} min")
        
        with col4:
            status = "✅ Enabled" if schedule['enabled'] else "❌ Disabled"
            st.write(status)
        
        with col5:
            if st.button("Delete", key=f"del_{schedule['id']}"):
                delete_schedule(schedule['id'])
                st.experimental_rerun()

# Statistics
st.subheader("📊 Statistics")
if not df.empty:
    col1, col2, col3 = st.columns(3)
    
    with col1:
        avg_moisture = df['moisture_percent'].mean()
        st.metric("Average Moisture", f"{avg_moisture:.1f}%")
    
    with col2:
        pump_time = len(df[df['pump_state'] == True]) * 10 / 60  # Assuming 10 second intervals
        st.metric("Pump Runtime", f"{pump_time:.1f} minutes")
    
    with col3:
        last_update = df['created_at'].max()
        st.metric("Last Update", last_update.strftime("%H:%M:%S"))

# Auto-refresh
if st.checkbox("Auto-refresh (every 10 seconds)"):
    time.sleep(10)
    st.experimental_rerun()

# Footer
st.markdown("---")
st.markdown("*IoT Watering System - Real-time monitoring and control*")
