import streamlit as st
import pandas as pd
import requests
import datetime
import time
from PIL import Image

# Try to import plotly with fallback
try:
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    st.warning("Plotly not available - charts will be simplified")

# Page configuration
st.set_page_config(
    page_title="Smart Pump Controller",
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
    .schedule-box {
        background-color: white;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .status-card {
        background-color: white;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 15px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
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
</style>
""", unsafe_allow_html=True)

# App title and description
st.title("💧 Smart Pump Controller")
st.markdown("Control your water pump remotely and monitor soil moisture levels.")

# Device configuration (replace with your ESP8266 IP)
ESP8266_IP = "192.168.1.100"
PUMP_ON_URL = f"http://{ESP8266_IP}/pump_on"
PUMP_OFF_URL = f"http://{ESP8266_IP}/pump_off"
STATUS_URL = f"http://{ESP8266_IP}/status"
MOISTURE_URL = f"http://{ESP8266_IP}/moisture"

# Initialize session state variables
if 'pump_status' not in st.session_state:
    st.session_state.pump_status = "OFF"
if 'schedules' not in st.session_state:
    st.session_state.schedules = pd.DataFrame(columns=["Day", "Start Time", "End Time", "Duration", "Enabled"])
if 'alarms' not in st.session_state:
    st.session_state.alarms = []
if 'moisture_level' not in st.session_state:
    st.session_state.moisture_level = 0
if 'moisture_history' not in st.session_state:
    st.session_state.moisture_history = pd.DataFrame(columns=["Timestamp", "Moisture"])

# Function to control pump
def control_pump(action):
    try:
        if action == "ON":
            response = requests.get(PUMP_ON_URL, timeout=5)
            if response.status_code == 200:
                st.session_state.pump_status = "ON"
                st.success("Pump turned ON successfully")
            else:
                st.error("Failed to turn ON pump")
        else:
            response = requests.get(PUMP_OFF_URL, timeout=5)
            if response.status_code == 200:
                st.session_state.pump_status = "OFF"
                st.success("Pump turned OFF successfully")
            else:
                st.error("Failed to turn OFF pump")
    except Exception as e:
        st.error(f"Error communicating with device: {str(e)}")

# Function to get device status
def get_device_status():
    try:
        # Get pump status
        response = requests.get(STATUS_URL, timeout=5)
        if response.status_code == 200:
            data = response.json()
            st.session_state.pump_status = data.get("pump_status", "OFF")
        
        # Get moisture level
        response = requests.get(MOISTURE_URL, timeout=5)
        if response.status_code == 200:
            data = response.json()
            moisture = data.get("moisture", 0)
            st.session_state.moisture_level = moisture
            
            # Add to history (keep last 100 readings)
            new_entry = pd.DataFrame({
                "Timestamp": [datetime.datetime.now()],
                "Moisture": [moisture]
            })
            st.session_state.moisture_history = pd.concat(
                [st.session_state.moisture_history, new_entry]
            ).tail(100)
            
    except Exception as e:
        st.error(f"Error getting device status: {str(e)}")

# Function to get moisture status class
def get_moisture_class(level):
    if level > 60:
        return "moisture-good"
    elif level > 30:
        return "moisture-warning"
    else:
        return "moisture-danger"

# Function to add schedule
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

# Function to delete schedule
def delete_schedule(index):
    st.session_state.schedules = st.session_state.schedules.drop(index).reset_index(drop=True)
    st.success("Schedule deleted successfully!")

# Function to add alarm
def add_alarm():
    alarm_time = st.session_state.new_alarm_time
    st.session_state.alarms.append(alarm_time.strftime("%H:%M"))
    st.success(f"Alarm set for {alarm_time.strftime('%H:%M')}")

# Function to delete alarm
def delete_alarm(index):
    deleted_alarm = st.session_state.alarms.pop(index)
    st.success(f"Alarm for {deleted_alarm} deleted")

# Layout columns
col1, col2 = st.columns([1, 2])

with col1:
    # Moisture level display
    st.markdown("### Soil Moisture Level")
    with st.container():
        moisture_class = get_moisture_class(st.session_state.moisture_level)
        st.markdown(f"""
        <div class="{moisture_class} moisture-level">
            {st.session_state.moisture_level}%
        </div>
        """, unsafe_allow_html=True)
        
        # Moisture status indicator
        if st.session_state.moisture_level > 60:
            st.success("Soil moisture level is good")
        elif st.session_state.moisture_level > 30:
            st.warning("Soil moisture level is moderate")
        else:
            st.error("Soil moisture level is low - consider watering")
        
        # Refresh button
        if st.button("Refresh Moisture Level", key="btn_refresh_moisture"):
            get_device_status()
    
    # Pump control card
    st.markdown("### Pump Control")
    with st.container():
        st.markdown(f"**Current Status:** `{st.session_state.pump_status}`")
        
        # Manual control buttons
        col1_1, col1_2 = st.columns(2)
        with col1_1:
            if st.button("Turn ON Pump", key="btn_on"):
                control_pump("ON")
        with col1_2:
            if st.button("Turn OFF Pump", key="btn_off"):
                control_pump("OFF")
        
        # Status refresh
        if st.button("Refresh Status", key="btn_refresh"):
            get_device_status()

    # Alarm settings
    st.markdown("### Alarm Settings")
    with st.container():
        st.time_input("Set Alarm Time", key="new_alarm_time")
        st.button("Add Alarm", on_click=add_alarm)
        
        if st.session_state.alarms:
            st.markdown("**Active Alarms:**")
            for i, alarm in enumerate(st.session_state.alarms):
                cols = st.columns([3, 1])
                cols[0].write(f"⏰ {alarm}")
                cols[1].button("Delete", key=f"del_alarm_{i}", on_click=delete_alarm, args=(i,))

with col2:
    # Moisture history chart
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
            fig.update_layout(
                xaxis_title="Time",
                yaxis_title="Moisture (%)",
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.line_chart(
                st.session_state.moisture_history.set_index('Timestamp')['Moisture'],
                use_container_width=True
            )
    else:
        st.info("No moisture data available yet. Refresh to get readings.")
    
    # Scheduling section
    st.markdown("### Pump Scheduling")
    with st.container():
        # Schedule form
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
        
        # Display schedules
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

# System status and logs
st.markdown("### System Status")
with st.container():
    status_cols = st.columns(3)
    
    with status_cols[0]:
        st.markdown("**Device Connection**")
        try:
            response = requests.get(STATUS_URL, timeout=5)
            if response.status_code == 200:
                st.success("✅ Connected")
            else:
                st.warning("⚠️ Connection issues")
        except:
            st.error("❌ Device offline")
    
    with status_cols[1]:
        st.markdown("**Last Update**")
        st.write(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    with status_cols[2]:
        st.markdown("**System Uptime**")
        try:
            response = requests.get(STATUS_URL, timeout=5)
            if response.status_code == 200:
                data = response.json()
                uptime = data.get("uptime", 0)
                hours = uptime // 3600
                minutes = (uptime % 3600) // 60
                st.write(f"{hours}h {minutes}m")
        except:
            st.write("Unknown")

# Initialize device status on first run
if 'initialized' not in st.session_state:
    get_device_status()
    st.session_state.initialized = True

# Footer
st.markdown("---")
st.markdown("""
**Smart Pump Controller**  
Developed with ❤️ using Streamlit and ESP8266  
[GitHub Repository](#) | [Documentation](#)
""")
