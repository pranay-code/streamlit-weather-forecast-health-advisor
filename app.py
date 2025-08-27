import streamlit as st
import requests
import pandas as pd
import json
import os
import google.generativeai as genai

# --- Page Configuration ---

st.set_page_config(
    page_title="Weather Forecast with Health Advisory",
    layout="wide"
)

# CSS to inject contained in a string
layout_control = """
            <style>
            div.block-container {
                padding-top: 1rem;
                padding-bottom: 0rem;
                padding-left: 5rem;
                padding-right: 5rem;
            }
            </style>
            """

st.markdown(layout_control, unsafe_allow_html=True)


# --- Constants & File Paths ---
SITES_FILE = 'sites.json'

# --- Helper Functions for Site Management ---

def load_sites_to_session_state():
    """Loads site data from JSON into session state if not already present."""
    if 'sites' not in st.session_state:
        if os.path.exists(SITES_FILE):
            with open(SITES_FILE, 'r') as f:
                st.session_state.sites = json.load(f)
        else:
            st.session_state.sites = {}

def save_sites(sites_data):
    """Saves site data to the JSON file (for persistent edits)."""
    with open(SITES_FILE, 'w') as f:
        json.dump(sites_data, f, indent=2)

# --- Helper Functions for Data Fetching & Processing ---

@st.cache_data(ttl=3600)
def fetch_forecast_data(latitude, longitude):
    """Fetches weather and air quality data for the next 3 days (72 hours)."""
    try:
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&hourly=temperature_2m,relativehumidity_2m,rain,windspeed_10m&forecast_days=3"
        weather_response = requests.get(weather_url)
        weather_response.raise_for_status()
        weather_data = weather_response.json()

        aqi_url = f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={latitude}&longitude={longitude}&hourly=us_aqi&forecast_days=3"
        aqi_response = requests.get(aqi_url)
        aqi_response.raise_for_status()
        aqi_data = aqi_response.json()
        return weather_data, aqi_data
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to fetch data from APIs. Error: {e}")
        return None, None

def process_data(weather_data, aqi_data):
    """Processes raw API data into a hourly DataFrame and a daily summary DataFrame."""
    if not weather_data or not aqi_data: return None, None
    weather_df = pd.DataFrame(weather_data['hourly']); weather_df['time'] = pd.to_datetime(weather_df['time']); weather_df.set_index('time', inplace=True)
    weather_df.rename(columns={'temperature_2m': 'Temp (°C)', 'relativehumidity_2m': 'Humidity (%)', 'rain': 'Rain (mm)', 'windspeed_10m': 'Wind (km/h)'}, inplace=True)
    aqi_df = pd.DataFrame(aqi_data['hourly']); aqi_df['time'] = pd.to_datetime(aqi_df['time']); aqi_df.set_index('time', inplace=True)
    aqi_df.rename(columns={'us_aqi': 'AQI'}, inplace=True)
    hourly_df = weather_df.join(aqi_df, how='inner')
    summary_df = hourly_df.resample('D').agg({'Temp (°C)': ['min', 'max'], 'Humidity (%)': ['min', 'max'], 'AQI': ['min', 'max'], 'Wind (km/h)': 'mean', 'Rain (mm)': 'sum'})
    summary_df.columns = ['_'.join(col).strip() for col in summary_df.columns.values]
    # Correction 3: Format index to YYYY-MM-DD
    summary_df.index = summary_df.index.strftime('%Y-%m-%d')
    hourly_df.index.name = 'DateTime (UTC)'
    summary_df.index.name = 'Date'
    return hourly_df, summary_df

# Correction 5: Add cache to the recommendation function
@st.cache_data(ttl=3600)
def get_health_recommendations(summary_df_json):
    """Generates health recommendations from the Gemini API."""
    try:
        api_key = st.secrets.get("GOOGLE_API_KEY")
        if not api_key: st.error("API Key for Google Gemini not found."); return None
        genai.configure(api_key=api_key)
    except Exception: return None
    model = genai.GenerativeModel('gemini-2.5-flash')
    # Correction 4: Ensure schema asks for date to match summary index
    json_schema = {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {"day": {"type": "STRING"}, "recommendations": {"type": "OBJECT", "properties": {"children_and_elderly": {"type": "STRING"}, "people_with_morbidities": {"type": "STRING"}, "adults": {"type": "STRING"}}}}}}
    prompt = f"""Analyze the following daily weather summary. For each date ('day'), provide structured, short (atmost 2 lines) health recommendations for three groups: 'Children & Elderly', 'People with Morbidities', and 'Adults'. The date in your response MUST match the date in the input data.
    DATA: {summary_df_json}
    Generate the output in a valid JSON array format according to the provided schema."""
    try:
        response = model.generate_content(prompt, generation_config=genai.types.GenerationConfig(response_mime_type="application/json", response_schema=json_schema))
        return json.loads(response.text)
    except Exception as e: st.error(f"Error generating recommendations: {e}"); return None

def convert_df_to_csv(df):
    return df.to_csv(index=True).encode('utf-8')

st.markdown("<h1 style='text-align: center;'>☀️ Weather Forecast and Health Advisory 🩺</h1>", unsafe_allow_html=True)

# Use thicker horizontal lines
st.markdown("<hr style='height:3px;border-width:0;color:#e65100;background-color:#e65100'>", unsafe_allow_html=True)

# Correction 1: Load sites into session state once
load_sites_to_session_state()

# Initialize other session state variables
if 'edit_mode' not in st.session_state: st.session_state.edit_mode = False

site_options = list(st.session_state.sites.keys())

# --- Layout: Two Columns ---
col1,vcol, col2 = st.columns([0.47,0.06, 0.47])

with col1:
    st.subheader("📍 City Selection")
    selected_site = st.selectbox("Choose an existing site", site_options, key="site_selector",index=len(site_options)-1)

    site_info = st.session_state.sites[selected_site]
    lat = site_info["latitude"]
    lon = site_info["longitude"]
    st.info(f"Displaying forecast for **{selected_site}**")
    lat_display = st.text_input("Latitude", value=lat, disabled=not st.session_state.edit_mode, key=f"lat_{selected_site}")
    lon_display = st.text_input("Longitude", value=lon, disabled=not st.session_state.edit_mode, key=f"lon_{selected_site}")
    if st.session_state.edit_mode:
        if st.button("Save Changes"):
            try:
                st.session_state.sites[selected_site]["latitude"] = float(lat_display)
                st.session_state.sites[selected_site]["longitude"] = float(lon_display)
                save_sites(st.session_state.sites) # Persist edit to file
                st.success("Coordinates updated!"); st.session_state.edit_mode = False; st.rerun()
            except ValueError: st.error("Invalid coordinates.")
    else:
        if st.button("Edit Coordinates"): st.session_state.edit_mode = True; st.rerun()

    # Correction 2: Move "Add New Site" to be after the edit button
    with st.expander("Add New Site"):
        with st.form("new_site_form", clear_on_submit=True):
            new_site_name = st.text_input("Site Name")
            new_lat = st.text_input("Latitude")
            new_lon = st.text_input("Longitude")
            if st.form_submit_button("Add Site"):
                if new_site_name and new_lat and new_lon:
                    try:
                        # Correction 1: Add to session state, not file
                        st.session_state.sites[new_site_name] = {"latitude": float(new_lat), "longitude": float(new_lon)}
                        st.success(f"Site '{new_site_name}' added for this session!"); st.rerun()
                    except ValueError: st.error("Please enter valid numeric coordinates.")

with vcol:
    # Correction 6: Add vertical line using CSS
    st.markdown("""
                <div style='
                    height: 650px; /* Custom height */
                    width: 3px;    /* Custom width */
                    background-color: #e65100; /* Custom color */
                    margin: auto; /* Vertically center the line */
                '></div>
                """, unsafe_allow_html=True)

with col2:
    st.subheader("🗺️ Map View")
    map_data = pd.DataFrame({'lat': [lat], 'lon': [lon]})
    st.map(map_data, zoom=9, size=400, color='#000080')

# Use thicker horizontal lines
st.markdown("<hr style='height:3px;border-width:0;color:#e65100;background-color:#e65100'>", unsafe_allow_html=True)

if selected_site != "Select a site":
    with st.spinner(f"Fetching data for {selected_site}..."):
        weather_data, aqi_data = fetch_forecast_data(lat, lon)
    if weather_data and aqi_data:
        hourly_df, summary_df = process_data(weather_data, aqi_data)
        st.header("☀️ Weather Forecast")
        view_option = st.radio("Select forecast view", ("Daily Summary", "Hourly Forecast"), horizontal=True, label_visibility="collapsed")
        if view_option == "Daily Summary":
            display_summary = summary_df.copy()
            display_summary['Temp Range (°C)'] = display_summary.apply(lambda r: f"{r['Temp (°C)_min']:.1f} - {r['Temp (°C)_max']:.1f}", axis=1)
            display_summary['Humidity Range (%)'] = display_summary.apply(lambda r: f"{r['Humidity (%)_min']:.0f} - {r['Humidity (%)_max']:.0f}", axis=1)
            display_summary['AQI Range'] = display_summary.apply(lambda r: f"{r['AQI_min']:.0f} - {r['AQI_max']:.0f}", axis=1)
            display_summary['Avg. Wind (km/h)'] = display_summary['Wind (km/h)_mean'].map('{:.1f}'.format)
            st.dataframe(display_summary[['Temp Range (°C)', 'Humidity Range (%)', 'AQI Range', 'Avg. Wind (km/h)']], use_container_width=True)
            st.download_button("📥 Download Summary", convert_df_to_csv(summary_df), "summary_forecast.csv", "text/csv")
        else:
            st.dataframe(hourly_df, use_container_width=True)
            st.download_button("📥 Download Hourly Forecast", convert_df_to_csv(hourly_df), "hourly_forecast.csv", "text/csv")

        # Use thicker horizontal lines
        st.markdown("<hr style='height:3px;border-width:0;color:#e65100;background-color:#e65100'>", unsafe_allow_html=True)

        st.header("🩺 Health Recommendations (Gemini Generated)")
        col_rec, col_reload = st.columns([4, 1])
        with col_reload:
            # Correction 5: Add button to clear the recommendations cache
            if st.button("🔄 Reload Recommendations"):
                get_health_recommendations.clear()
                st.toast("Recommendations cache cleared!")
        with st.spinner("Generating health advice..."):
            summary_json = summary_df.to_json(orient='split')
            recommendations = get_health_recommendations(summary_json)
        if recommendations:
            rec_data = {"Children & Elderly": [], "People with Morbidities": [], "Adults": []}
            index_dates = []
            for rec in recommendations:
                # Correction 4: Use date from Gemini response as index
                index_dates.append(rec.get('day', 'N/A'))
                rec_data["Children & Elderly"].append(rec.get('recommendations', {}).get('children_and_elderly', 'N/A'))
                rec_data["People with Morbidities"].append(rec.get('recommendations', {}).get('people_with_morbidities', 'N/A'))
                rec_data["Adults"].append(rec.get('recommendations', {}).get('adults', 'N/A'))
            rec_df = pd.DataFrame(rec_data, index=index_dates)
            st.dataframe(rec_df, use_container_width=True)
            st.download_button("📥 Download Recommendations", convert_df_to_csv(rec_df), "health_recommendations.csv", "text/csv")
        else:
            st.warning("Could not generate health recommendations.")
else:
    st.info("Select a site to view the forecast and health advisory.")

# Use thicker horizontal lines
st.markdown("<hr style='height:3px;border-width:0;color:#e65100;background-color:#e65100'>", unsafe_allow_html=True)
