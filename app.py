import streamlit as st
import pandas as pd
import datetime
import time
import json
from PIL import Image

# Try to import MQTT with fallback
try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    st.error("MQTT library not available - some features will be limited")

# Configuration
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
PUMP_CONTROL_TOPIC = "smart-hydro/pump-control"
SENSOR_DATA_TOPIC = "smart-hydro/sensor-data"

# Initialize session state
if 'pump_status' not in st.session_state:
    st.session_state.pump_status = "OFF"
if 'moisture_level' not in st.session_state:
    st.session_state.moisture_level = 0
if 'schedules' not in st.session_state:
    st.session_state.schedules = pd.DataFrame(columns=["Day", "Start Time", "End Time", "Duration", "Enabled"])
if 'alarms' not in st.session_state:
    st.session_state.alarms = []
if 'moisture_history' not in st.session_state:
    st.session_state.moisture_history = pd.DataFrame(columns=["Timestamp", "Moisture"])
if 'mqtt_connected' not in st.session_state:
    st.session_state.mqtt_connected = False

# MQTT Client Setup
if MQTT_AVAILABLE:
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            st.session_state.mqtt_connected = True
            client.subscribe(SENSOR_DATA_TOPIC)
        else:
            st.session_state.mqtt_connected = False

    def on_message(client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
            st.session_state.moisture_level = data.get("moisture", 0)
            st.session_state.pump_status = data.get("pump_status", "OFF")
            
            new_entry = pd.DataFrame({
                "Timestamp": [datetime.datetime.now()],
                "Moisture": [st.session_state.moisture_level]
            })
            st.session_state.moisture_history = pd.concat(
                [st.session_state.moisture_history, new_entry]
            ).tail(100)
            
        except Exception as e:
            st.error(f"Error processing message: {str(e)}")

    try:
        mqtt_client = mqtt.Client()
        mqtt_client.on_connect = on_connect
        mqtt_client.on_message = on_message
        mqtt_client.connect(MQTT_BROKER, MTT_PORT, 60)
        mqtt_client.loop_start()
    except Exception as e:
        st.error(f"MQTT connection failed: {str(e)}")
        MQTT_AVAILABLE = False

# Page Configuration
st.set_page_config(
    page_title="Smart Hydro Controller",
    page_icon="💧",
    layout="wide"
)

# Custom CSS (same as before)
st.markdown("""
<style>
    /* Your existing CSS styles */
</style>
""", unsafe_allow_html=True)

# App Title
st.title("💧 Smart Hydro Controller")
st.markdown("Remote pump control with soil moisture monitoring")

# Control Functions
def control_pump(action):
    if not MQTT_AVAILABLE:
        st.error("MQTT not available - cannot control pump")
        return
        
    try:
        mqtt_client.publish(PUMP_CONTROL_TOPIC, action)
        st.session_state.pump_status = action
        st.success(f"Pump turned {action} successfully")
    except Exception as e:
        st.error(f"Error controlling pump: {str(e)}")

# (Keep all your other functions the same as before)

# Layout
col1, col2 = st.columns([1, 2])

with col1:
    # Moisture Level Card
    st.markdown("### Soil Moisture")
    moisture_class = get_moisture_class(st.session_state.moisture_level)
    st.markdown(f"""
    <div class="{moisture_class} moisture-level">
        {st.session_state.moisture_level}%
    </div>
    """, unsafe_allow_html=True)
    
    # (Rest of your column 1 content)

with col2:
    # Moisture Chart
    st.markdown("### Moisture History")
    if not st.session_state.moisture_history.empty:
        st.line_chart(
            st.session_state.moisture_history.set_index('Timestamp')['Moisture'],
            use_container_width=True
        )
    else:
        st.info("No moisture data available yet")
    
    # (Rest of your column 2 content)

# System Status
st.markdown("### System Status")
status_cols = st.columns(3)
with status_cols[0]:
    st.markdown("**MQTT Connection**")
    if MQTT_AVAILABLE:
        st.success("✅ Connected" if st.session_state.mqtt_connected else "❌ Disconnected")
    else:
        st.error("❌ Not Available")

# (Rest of your app content)

# Keep the app running
while True:
    if MQTT_AVAILABLE:
        mqtt_client.loop()
    time.sleep(1)
