import streamlit as st
import pandas as pd
import datetime
import time
import json

# Import with error handling
try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    st.warning("MQTT functionality unavailable - install paho-mqtt")

try:
    from PIL import Image
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False
    st.warning("Image processing unavailable - install Pillow")

try:
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    st.warning("Advanced charts unavailable - install plotly")

# MQTT Configuration
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

# Page Configuration
st.set_page_config(
    page_title="Smart Hydro Controller",
    page_icon="💧",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main {
        background-color: #f0f2f6;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border-radius: 5px;
        padding: 10px 24px;
    }
    .stButton>button:disabled {
        background-color: #f44336;
    }
    .moisture-level {
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        margin: 10px 0;
    }
    .moisture-good {
        color: #4CAF50;
    }
    .moisture-warning {
        color: #FFC107;
    }
    .moisture-danger {
        color: #F44336;
    }
    .status-card {
        background-color: white;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 15px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }
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

def get_moisture_class(level):
    if level > 60:
        return "moisture-good"
    elif level > 30:
        return "moisture-warning"
    else:
        return "moisture-danger"

# [Include all your other functions here...]

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
    
    # [Rest of your column 1 content...]

with col2:
    # Moisture Chart
    st.markdown("### Moisture History")
    if not st.session_state.moisture_history.empty:
        if PLOTLY_AVAILABLE:
            fig = px.line(
                st.session_state.moisture_history,
                x="Timestamp",
                y="Moisture",
                title="Soil Moisture Over Time",
                labels={"Moisture": "Moisture Level (%)"},
                range_y=[0, 100]
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.line_chart(
                st.session_state.moisture_history.set_index('Timestamp')['Moisture'],
                use_container_width=True
            )
    else:
        st.info("No moisture data available yet")
    
    # [Rest of your column 2 content...]

# System Status
st.markdown("### System Status")
status_cols = st.columns(3)
with status_cols[0]:
    st.markdown("**Dependencies**")
    st.write(f"MQTT: {'✅' if MQTT_AVAILABLE else '❌'}")
    st.write(f"Pillow: {'✅' if PILLOW_AVAILABLE else '❌'}")
    st.write(f"Plotly: {'✅' if PLOTLY_AVAILABLE else '❌'}")

# [Rest of your app...]

# Initialize MQTT if available
if MQTT_AVAILABLE:
    try:
        mqtt_client = mqtt.Client()
        mqtt_client.on_connect = on_connect
        mqtt_client.on_message = on_message
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.loop_start()
    except Exception as e:
        st.error(f"MQTT connection failed: {str(e)}")
        MQTT_AVAILABLE = False

# Keep the app running
while True:
    time.sleep(1)
