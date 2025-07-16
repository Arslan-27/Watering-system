import streamlit as st
import pandas as pd
import datetime
import time
import json
import paho.mqtt.client as mqtt
from PIL import Image

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

# MQTT Client Setup
def on_connect(client, userdata, flags, rc):
    st.success("Connected to MQTT Broker")
    client.subscribe(SENSOR_DATA_TOPIC)

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        st.session_state.moisture_level = data.get("moisture", 0)
        st.session_state.pump_status = data.get("pump_status", "OFF")
        
        # Update history
        new_entry = pd.DataFrame({
            "Timestamp": [datetime.datetime.now()],
            "Moisture": [st.session_state.moisture_level]
        })
        st.session_state.moisture_history = pd.concat(
            [st.session_state.moisture_history, new_entry]
        ).tail(100)
        
    except Exception as e:
        st.error(f"Error processing MQTT message: {str(e)}")

mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
mqtt_client.loop_start()

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

def add_schedule():
    day = st.session_state.new_schedule_day
    start_time = st.session_state.new_schedule_start
    end_time = st.session_state.new_schedule_end
    enabled = st.session_state.new_schedule_enabled
    
    duration = (datetime.datetime.combine(datetime.date.today(), end_time) - 
               datetime.datetime.combine(datetime.date.today(), start_time)).seconds // 60
    
    new_schedule = pd.DataFrame([{
        "Day": day,
        "Start Time": start_time.strftime("%H:%M"),
        "End Time": end_time.strftime("%H:%M"),
        "Duration": f"{duration} minutes",
        "Enabled": enabled
    }])
    
    st.session_state.schedules = pd.concat([st.session_state.schedules, new_schedule], ignore_index=True)
    st.success("Schedule added successfully!")

def delete_schedule(index):
    st.session_state.schedules = st.session_state.schedules.drop(index).reset_index(drop=True)
    st.success("Schedule deleted successfully!")

def add_alarm():
    alarm_time = st.session_state.new_alarm_time
    st.session_state.alarms.append(alarm_time.strftime("%H:%M"))
    st.success(f"Alarm set for {alarm_time.strftime('%H:%M')}")

def delete_alarm(index):
    deleted_alarm = st.session_state.alarms.pop(index)
    st.success(f"Alarm for {deleted_alarm} deleted")

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
    
    if st.session_state.moisture_level > 60:
        st.success("Moisture level is good")
    elif st.session_state.moisture_level > 30:
        st.warning("Moisture level is moderate")
    else:
        st.error("Moisture level is low - consider watering")
    
    # Pump Control Card
    st.markdown("### Pump Control")
    st.markdown(f"**Status:** `{st.session_state.pump_status}`")
    
    col1_1, col1_2 = st.columns(2)
    with col1_1:
        st.button("Turn ON", on_click=control_pump, args=("ON",), key="btn_on")
    with col1_2:
        st.button("Turn OFF", on_click=control_pump, args=("OFF",), key="btn_off")
    
    # Alarm Card
    st.markdown("### Alarms")
    st.time_input("Set Alarm Time", key="new_alarm_time")
    st.button("Add Alarm", on_click=add_alarm)
    
    if st.session_state.alarms:
        st.markdown("**Active Alarms:**")
        for i, alarm in enumerate(st.session_state.alarms):
            cols = st.columns([3, 1])
            cols[0].write(f"⏰ {alarm}")
            cols[1].button("Delete", key=f"del_alarm_{i}", on_click=delete_alarm, args=(i,))

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
    
    # Scheduling
    st.markdown("### Pump Schedule")
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday", "Everyday"]
    
    cols = st.columns(3)
    with cols[0]:
        st.selectbox("Day", days, key="new_schedule_day")
    with cols[1]:
        st.time_input("Start Time", key="new_schedule_start")
    with cols[2]:
        st.time_input("End Time", key="new_schedule_end")
    
    st.checkbox("Enable Schedule", value=True, key="new_schedule_enabled")
    st.button("Add Schedule", on_click=add_schedule)
    
    if not st.session_state.schedules.empty:
        st.markdown("**Active Schedules:**")
        for i, row in st.session_state.schedules.iterrows():
            with st.expander(f"Schedule {i+1}: {row['Day']} {row['Start Time']} to {row['End Time']}"):
                cols = st.columns([4, 1])
                cols[0].write(f"""
                - Day: {row['Day']}
                - Time: {row['Start Time']} to {row['End Time']}
                - Duration: {row['Duration']}
                - Enabled: {'✅' if row['Enabled'] else '❌'}
                """)
                cols[1].button("Delete", key=f"del_sched_{i}", on_click=delete_schedule, args=(i,))

# System Status
st.markdown("### System Status")
status_cols = st.columns(3)
with status_cols[0]:
    st.markdown("**Connection Status**")
    st.success("✅ Connected" if mqtt_client.is_connected() else "❌ Disconnected")
with status_cols[1]:
    st.markdown("**Last Update**")
    st.write(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
with status_cols[2]:
    st.markdown("**Messages Received**")
    st.write(len(st.session_state.moisture_history))

# Footer
st.markdown("---")
st.markdown("""
**Smart Hydro Controller**  
*Developed with Streamlit and ESP8266*  
[GitHub Repository](#) | [Documentation](#)
""")

# Keep the MQTT connection alive
while True:
    mqtt_client.loop()
    time.sleep(1)
