import os
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests
import os
from dotenv import load_dotenv
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import time
import json
from streamlit_autorefresh import st_autorefresh

# Load environment variables
load_dotenv()

# Set page configuration
st.set_page_config(
    page_title="Air Quality Dashboard",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state for theme
if 'dark_mode' not in st.session_state:
    st.session_state.dark_mode = False

def toggle_theme():
    st.session_state.dark_mode = not st.session_state.dark_mode

def get_theme():
    return 'dark' if st.session_state.dark_mode else 'light'

def get_theme_colors():
    if st.session_state.dark_mode:
        return {
            'bg': '#1a1a1a',
            'card_bg': '#2d2d2d',
            'text': '#f0f0f0',
            'text_secondary': '#b0b0b0',
            'border': '#444',
            'shadow': 'rgba(0, 0, 0, 0.3)',
            'metric_bg': '#3a3a3a',
            'weather_bg': '#333333',
            'hover_bg': '#3a3a3a',
            'icon_bg': 'rgba(255, 255, 255, 0.1)'
        }
    else:
        return {
            'bg': '#ffffff',
            'card_bg': '#ffffff',
            'text': '#333333',
            'text_secondary': '#666666',
            'border': '#f0f0f0',
            'shadow': 'rgba(0, 0, 0, 0.05)',
            'metric_bg': '#f8f9fa',
            'weather_bg': '#f8f9fa',
            'hover_bg': '#f5f5f5',
            'icon_bg': '#e6f7ff'
        }

# Initialize session state for selected locations
if 'selected_locations' not in st.session_state:
    st.session_state.selected_locations = []

# Create a reference to selected_locations for easier access
selected_locations = st.session_state.selected_locations

# Constants
OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY')
CACHE_EXPIRY = 3600  # 1 hour cache for weather data

# Theme toggle button in the top right
col1, col2 = st.columns([6, 1])
with col2:
    theme_emoji = '🌙' if not st.session_state.dark_mode else '☀️'
    st.button(theme_emoji, on_click=toggle_theme, help='Toggle dark/light mode')

# Custom CSS for better styling
st.markdown("""
<style>
    /* Main container */
    .main {
        background-color: #f8f9fa;
    }
    .stApp {
        max-width: 100%;
        padding: 1rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre;
        border-radius: 4px 4px 0 0;
        gap: 1px;
        padding: 0 16px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #f0f2f6;
    }
</style>
""", unsafe_allow_html=True)

# Title and description
st.markdown("""
<div style='margin-bottom: 2rem;'>
    <h1 style='margin-bottom: 0.5rem;'>🌤️ Air Quality Dashboard</h1>
    <p style='color: #666; margin-top: 0;'>Monitor and analyze air quality metrics and weather conditions across different locations.</p>
</div>
""", unsafe_allow_html=True)

# Function to calculate AQI
@st.cache_data
def calculate_aqi(pm25, pm10, no2, o3):
    """Calculate Air Quality Index (AQI) based on EPA standards"""
    def get_aqi(concentration, breakpoints):
        for i in range(len(breakpoints) - 1):
            if breakpoints[i][0] <= concentration <= breakpoints[i + 1][0]:
                aqi_low, aqi_high = breakpoints[i][1], breakpoints[i + 1][1]
                conc_low, conc_high = breakpoints[i][0], breakpoints[i + 1][0]
                return int(((aqi_high - aqi_low) / (conc_high - conc_low)) * (concentration - conc_low) + aqi_low)
        return 0

    # AQI breakpoints (concentration, AQI) for each pollutant
    pm25_breakpoints = [(0, 0), (12.0, 50), (35.4, 100), (55.4, 150), (150.4, 200), (250.4, 300), (350.4, 400), (500.4, 500)]
    pm10_breakpoints = [(0, 0), (54, 50), (154, 100), (254, 150), (354, 200), (424, 300), (504, 400), (604, 500)]
    no2_breakpoints = [(0, 0), (53, 50), (100, 100), (360, 150), (649, 200), (1249, 300), (1649, 400), (2049, 500)]
    o3_breakpoints = [(0, 0), (54, 50), (70, 100), (85, 150), (105, 200), (200, 300), (300, 400), (500, 500)]

    aqi_pm25 = get_aqi(pm25, pm25_breakpoints)
    aqi_pm10 = get_aqi(pm10, pm10_breakpoints)
    aqi_no2 = get_aqi(no2, no2_breakpoints)
    aqi_o3 = get_aqi(o3, o3_breakpoints)
    
    return max(aqi_pm25, aqi_pm10, aqi_no2, aqi_o3)

def get_aqi_category(aqi):
    if aqi <= 50:
        return "Good", "#00E400"
    elif aqi <= 100:
        return "Moderate", "#FFFF00"
    elif aqi <= 150:
        return "Unhealthy for Sensitive Groups", "#FF7E00"
    elif aqi <= 200:
        return "Unhealthy", "#FF0000"
    elif aqi <= 300:
        return "Very Unhealthy", "#8F3F97"
    else:
        return "Hazardous", "#7E0023"

def get_weather_condition(temp_c):
    if temp_c < 0:
        return "❄️ Snowy"
    elif temp_c < 10:
        return "🌧️ Rainy"
    elif temp_c < 20:
        return "⛅ Cloudy"
    else:
        return "☀️ Sunny"

# Initialize geocoder
def init_geocoder():
    try:
        from geopy.geocoders import Nominatim
        from geopy.extra.rate_limiter import RateLimiter
        
        # Initialize the geocoder with a custom user agent
        geolocator = Nominatim(
            user_agent="air_quality_dashboard_app",
            timeout=10  # Add timeout to prevent hanging
        )
        
        # Create a rate-limited version of the geocode function
        return {
            'geocoder': geolocator,
            'geocode': RateLimiter(geolocator.geocode, min_delay_seconds=1)
        }
    except Exception as e:
        st.error(f"Error initializing geocoder: {str(e)}")
        return None

# Get location coordinates
@st.cache_data(ttl=3600)  # Cache results for 1 hour to avoid redundant API calls
def get_location_coordinates(location_name, retry=2):
    """
    Get latitude and longitude for a location name using geopy.
    
    Args:
        location_name (str): Name of the location to geocode
        retry (int): Number of retry attempts if the first attempt fails
        
    Returns:
        tuple: (latitude, longitude) or None if not found
    """
    if not location_name or not isinstance(location_name, str) or not location_name.strip():
        return None
    
    # Initialize geocoder
    geocoder = init_geocoder()
    if not geocoder:
        st.error("Failed to initialize geocoder")
        return None
    
    # Get the rate-limited geocode function
    geocode = geocoder['geocode']
    
    # Try with different location strings if first attempt fails
    location_attempts = [
        location_name,
        f"{location_name}, {location_name}",  # Try with duplicated name (helps with some city names)
        f"city of {location_name}",
        f"{location_name}, country"
    ]
    
    for attempt in range(retry + 1):
        for loc_str in location_attempts:
            try:
                # Use the rate-limited geocode function
                location = geocode(
                    loc_str,
                    exactly_one=True,
                    timeout=10,
                    language='en',
                    addressdetails=True
                )
                
                if location:
                    # Verify the result is reasonable
                    if (-90 <= location.latitude <= 90 and 
                        -180 <= location.longitude <= 180 and
                        location.latitude != 0 and  # Skip 0,0 (null island)
                        location.longitude != 0):
                        return (location.latitude, location.longitude)
                        
            except Exception as e:
                if attempt == retry:  # Only show error on final attempt
                    st.warning(f"Error geocoding '{location_name}': {str(e)}")
                continue
    
    # If we get here, all attempts failed
    st.warning(f"Could not find coordinates for: {location_name}")
    return None

# Get weather and air quality data from OpenWeatherMap
@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_air_quality_data(lat, lon, _api_key):
    base_url = "http://api.openweathermap.org/data/2.5/air_pollution"
    params = {
        'lat': lat,
        'lon': lon,
        'appid': _api_key
    }
    
    try:
        response = requests.get(base_url, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Error fetching air quality data: {response.text}")
            return None
    except Exception as e:
        st.error(f"Error connecting to OpenWeatherMap: {str(e)}")
        return None

# Get weather data from OpenWeatherMap
@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_weather_data(lat, lon, _api_key):
    base_url = "http://api.openweathermap.org/data/2.5/weather"
    params = {
        'lat': lat,
        'lon': lon,
        'appid': _api_key,
        'units': 'metric'  # Get temperature in Celsius
    }
    
    try:
        response = requests.get(base_url, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Error fetching weather data: {response.text}")
            return None
    except Exception as e:
        st.error(f"Error connecting to OpenWeatherMap: {str(e)}")
        return None

# Get forecast data
@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_forecast_data(lat, lon, _api_key):
    base_url = "http://api.openweathermap.org/data/2.5/forecast"
    params = {
        'lat': lat,
        'lon': lon,
        'appid': _api_key,
        'units': 'metric',
        'cnt': 40  # 5-day forecast (8 data points per day * 5 days)
    }
    
    try:
        response = requests.get(base_url, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Error fetching forecast data: {response.text}")
            return None
    except Exception as e:
        st.error(f"Error connecting to OpenWeatherMap: {str(e)}")
        return None

# Process air quality data from OpenWeatherMap
def process_air_quality_data(aq_data, weather_data, location_name):
    if not aq_data or 'list' not in aq_data or not aq_data['list']:
        return None
    
    # Get current air quality
    current_aq = aq_data['list'][0]
    components = current_aq['components']
    
    # Get weather info
    temp = weather_data['main']['temp'] if weather_data else 20
    humidity = weather_data['main']['humidity'] if weather_data else 50
    wind_speed = weather_data['wind']['speed'] if weather_data else 2.5
    
    # Map weather condition to emoji
    weather_condition = "⛅"  # Default
    if weather_data and 'weather' in weather_data and weather_data['weather']:
        weather_main = weather_data['weather'][0]['main'].lower()
        if 'rain' in weather_main:
            weather_condition = "🌧️"
        elif 'cloud' in weather_main:
            weather_condition = "☁️"
        elif 'clear' in weather_main:
            weather_condition = "☀️"
        elif 'snow' in weather_main:
            weather_condition = "❄️"
        elif 'thunder' in weather_main:
            weather_condition = "⛈️"
    
    # Convert units (OpenWeatherMap provides data in µg/m³)
    pm25 = components.get('pm2_5', 0)
    pm10 = components.get('pm10', 0)
    no2 = components.get('no2', 0) / 1.88  # Convert to ppb
    o3 = components.get('o3', 0) / 2.0     # Convert to ppb
    
    # Calculate AQI
    aqi = current_aq['main']['aqi']  # OpenWeatherMap provides AQI (1-5 scale)
    
    # Map to standard AQI scale (1-500)
    aqi_mapping = {1: 50, 2: 100, 3: 150, 4: 200, 5: 300}
    aqi_value = aqi_mapping.get(aqi, 0)
    
    # Get AQI category and color
    aqi_category, aqi_color = get_aqi_category(aqi_value)
    
    # Get coordinates
    lat = aq_data.get('coord', {}).get('lat', 0)
    lon = aq_data.get('coord', {}).get('lon', 0)
    
    return {
        'date': datetime.now(),
        'location': location_name,
        'latitude': lat,
        'longitude': lon,
        'pm25': pm25,
        'pm10': pm10,
        'no2': no2,
        'o3': o3,
        'temp_c': temp,
        'humidity': humidity,
        'wind_speed': wind_speed,
        'aqi': aqi_value,
        'aqi_category': aqi_category,
        'aqi_color': aqi_color,
        'weather': weather_condition
    }

# Load data from OpenWeatherMap API
@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_weather_data(locations, _api_key):
    all_data = []
    
    for location_name in locations:
        # Get coordinates for the location
        coords = get_location_coordinates(location_name)
        if not coords:
            st.warning(f"Could not find coordinates for {location_name}. Skipping...")
            continue
            
        lat, lon = coords
        
        # Get air quality and weather data
        aq_data = get_air_quality_data(lat, lon, _api_key)
        weather_data = get_weather_data(lat, lon, _api_key)
        
        if aq_data and weather_data:
            # Process the data
            processed_data = process_air_quality_data(aq_data, weather_data, location_name)
            if processed_data:
                all_data.append(processed_data)
        
        # Add a small delay to avoid hitting API rate limits
        time.sleep(1)
    
    if not all_data:
        return None
        
    # Convert to DataFrame
    df = pd.DataFrame(all_data)
    
    # Add historical data (last 7 days) for trends
    historical_data = []
    for location_name in locations:
        coords = get_location_coordinates(location_name)
        if not coords:
            continue
            
        lat, lon = coords
        
        # Get historical data (last 7 days)
        for days_ago in range(1, 8):
            dt = int((datetime.now() - timedelta(days=days_ago)).timestamp())
            hist_url = f"http://api.openweathermap.org/data/2.5/air_pollution/history"
            params = {
                'lat': lat,
                'lon': lon,
                'start': dt - 3600,  # 1 hour window
                'end': dt,
                'appid': _api_key
            }
            
            try:
                response = requests.get(hist_url, params=params)
                if response.status_code == 200 and 'list' in response.json() and response.json()['list']:
                    hist_data = response.json()['list'][0]
                    hist_components = hist_data['components']
                    
                    # Convert units
                    pm25 = hist_components.get('pm2_5', 0)
                    pm10 = hist_components.get('pm10', 0)
                    no2 = hist_components.get('no2', 0) / 1.88
                    o3 = hist_components.get('o3', 0) / 2.0
                    
                    # Add to historical data
                    historical_data.append({
                        'date': datetime.fromtimestamp(hist_data['dt']),
                        'location': location_name,
                        'latitude': lat,
                        'longitude': lon,
                        'pm25': pm25,
                        'pm10': pm10,
                        'no2': no2,
                        'o3': o3,
                        'temp_c': np.nan,  # Not available in historical AQ data
                        'humidity': np.nan,
                        'wind_speed': np.nan,
                        'aqi': hist_data['main']['aqi'],
                        'aqi_category': '',  # Will be filled later
                        'aqi_color': '',     # Will be filled later
                        'weather': '📅'       # Historical data marker
                    })
                
                time.sleep(0.5)  # Rate limiting
                    
            except Exception as e:
                st.error(f"Error fetching historical data for {location_name}: {str(e)}")
    
    # Add historical data to the main DataFrame
    if historical_data:
        hist_df = pd.DataFrame(historical_data)
        
        # Calculate AQI category and color for historical data
        hist_df[['aqi_category', 'aqi_color']] = hist_df['aqi'].apply(
            lambda x: pd.Series(get_aqi_category(x * 50))  # Scale 1-5 to 50-250
        )
        
        # Combine with current data
        df = pd.concat([df, hist_df], ignore_index=True)
    
    return df

# Default locations with coordinates for initial suggestions
DEFAULT_LOCATIONS = {
    'New York, US': (40.7128, -74.0060),
    'Los Angeles, US': (34.0522, -118.2437),
    'London, UK': (51.5074, -0.1278),
    'Tokyo, Japan': (35.6762, 139.6503),
    'Sydney, Australia': (-33.8688, 151.2093),
    'Cape Town, South Africa': (-33.9249, 18.4241),
    'Rio de Janeiro, Brazil': (-22.9068, -43.1729),
    'Mumbai, India': (19.0760, 72.8777)
}

# Load data
def load_data(selected_locations, use_sample_data=False):
    """Load data from OpenWeatherMap API or use sample data."""
    if use_sample_data:
        return load_sample_data(selected_locations)
    
    all_data = []
    
    # Process each selected location
    for location in selected_locations:
        try:
            # Get coordinates for the location (either from DEFAULT_LOCATIONS or geocoding)
            if location in DEFAULT_LOCATIONS:
                lat, lon = DEFAULT_LOCATIONS[location]
            else:
                # Try to get coordinates for custom locations
                coords = get_location_coordinates(location)
                if coords:
                    lat, lon = coords
                else:
                    st.warning(f"Could not find coordinates for {location}. Skipping...")
                    continue
            
            # Load data for this location
            if OPENWEATHER_API_KEY:
                location_data = []
                
                # Try to get current air quality data
                aq_data = get_air_quality_data(lat, lon, OPENWEATHER_API_KEY)
                weather_data = get_weather_data(lat, lon, OPENWEATHER_API_KEY)
                
                if aq_data and weather_data:
                    processed_data = process_air_quality_data(aq_data, weather_data, location)
                    if processed_data:
                        location_data.append(processed_data)
                
                # Try to get forecast data
                forecast_data = get_forecast_data(lat, lon, OPENWEATHER_API_KEY)
                if forecast_data and 'list' in forecast_data:
                    for item in forecast_data['list']:
                        processed_forecast = process_air_quality_data(
                            item,  # Some forecast items include air quality data
                            item,  # Use the same item for weather data
                            location
                        )
                        if processed_forecast:
                            location_data.append(processed_forecast)
                
                if location_data:
                    all_data.extend(location_data)
                else:
                    st.warning(f"No data available for {location}. It might not be covered by the air quality monitoring network.")
            
        except Exception as e:
            st.error(f"Error loading data for {location}: {str(e)}")
    
    # If we have data, return as DataFrame
    if all_data:
        return pd.DataFrame(all_data)
    
    # Fall back to sample data if no data was loaded
    st.warning("No data could be loaded. Falling back to sample data.")
    return load_sample_data(selected_locations)

# Generate sample data for locations without API data
@st.cache_data
def load_sample_data(selected_locations):
    np.random.seed(42)
    dates = pd.date_range(end=datetime.now(), periods=7, freq='D')
    
    data = []
    for date in dates:
        for location_name in selected_locations:
            coords = DEFAULT_LOCATIONS.get(location_name, (0, 0))
            lat, lon = coords
            
            # Generate realistic values with some randomness
            base_temp = 15 + 10 * np.sin((date.month - 3) * np.pi / 6)  # Seasonal variation
            temp = np.random.normal(base_temp, 5)
            
            # Air quality metrics with some correlation to weather
            pm25 = np.random.gamma(2, 5) * (1 + 0.1 * (temp > 25))
            pm10 = pm25 * (1.5 + np.random.random() * 1.5)
            no2 = np.random.gamma(3, 4) * (1 + 0.2 * (temp < 10 or temp > 30))
            o3 = np.random.gamma(4, 5) * (1 + 0.3 * (temp > 25))
            
            # Calculate AQI
            aqi = calculate_aqi(pm25, pm10, no2, o3)
            aqi_category, aqi_color = get_aqi_category(aqi)
            
            # Weather condition based on temperature
            weather = get_weather_condition(temp)
            
            data.append({
                'date': date,
                'location': location_name,
                'latitude': lat,
                'longitude': lon,
                'pm25': max(0, pm25),
                'pm10': max(0, pm10),
                'no2': max(0, no2),
                'o3': max(0, o3),
                'temp_c': temp,
                'humidity': np.random.normal(60, 15),
                'wind_speed': np.random.gamma(2, 2.5),
                'aqi': aqi,
                'aqi_category': aqi_category,
                'aqi_color': aqi_color,
                'weather': weather
            })
    
    df = pd.DataFrame(data)
    # Ensure no negative values for air quality metrics
    for col in ['pm25', 'pm10', 'no2', 'o3', 'humidity', 'wind_speed']:
        df[col] = df[col].clip(lower=0.1)
    
    return df

# Custom CSS for better styling
st.markdown("""
<style>
    /* Main container */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Cards */
    .stMetric {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        transition: transform 0.2s;
    }
    
    .stMetric:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #f8f9fa;
        padding: 1.5rem;
    }
    
    /* Buttons */
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.2s;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0 !important;
        padding: 0.5rem 1rem;
    }
    
    /* Map container */
    .map-container {
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# Sidebar configuration
with st.sidebar:
    # Header with logo and title
    st.markdown("""
    <div style='text-align: center; margin-bottom: 1.5rem;'>
        <h1 style='font-size: 1.8rem; margin-bottom: 0.5rem;'>🌍 Air Quality</h1>
        <p style='color: #666; font-size: 0.9rem;'>Monitor air quality worldwide in real-time</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Search section
    st.markdown("### 🔍 Search Location")
    custom_location = st.text_input("Enter city or country", label_visibility="collapsed", 
                                 placeholder="e.g., Tokyo, Kenya, New York")
    
    # Popular locations
    st.markdown("### 🌟 Popular Locations")
    st.caption("Click to add to your selection")
    
    # Create two columns for the location buttons
    col1, col2 = st.columns(2)
    
    # Add buttons for default locations with better styling
    for i, location in enumerate(DEFAULT_LOCATIONS.keys()):
        with col1 if i % 2 == 0 else col2:
            btn = st.button(location, key=f"loc_{i}", 
                         help=f"View air quality in {location}")
            if btn:
                if location not in selected_locations:
                    selected_locations.append(location)
                    st.session_state.selected_locations = selected_locations
                    st.rerun()
    
    # Custom location search
    with st.spinner(f"Searching for {custom_location}..."):
        try:
            location_coords = get_location_coordinates(custom_location)
            if location_coords:
                if custom_location not in selected_locations:
                    if custom_location not in DEFAULT_LOCATIONS:
                        DEFAULT_LOCATIONS[custom_location] = location_coords
                    selected_locations.append(custom_location)
                    st.session_state.selected_locations = selected_locations
                    st.success(f"Added {custom_location} to your locations!")
                    st.rerun()
            else:
                st.warning(f"Could not find location: {custom_location}")
        except Exception as e:
            st.error(f"Error searching for location: {str(e)}")
    
    # Selected locations
    if selected_locations:
        st.markdown("---")
        st.markdown("### 📌 Your Locations")
        
        for loc in selected_locations[:]:  # Create a copy for iteration
            loc_col, btn_col = st.columns([4, 1])
            loc_col.markdown(f"📍 **{loc}**")
            if btn_col.button("×", key=f"remove_{loc}", 
                            help=f"Remove {loc}"):
                if loc in selected_locations:
                    selected_locations.remove(loc)
                    st.session_state.selected_locations = selected_locations
                    st.rerun()
    
    # Sample data toggle
    st.markdown("---")
    use_sample_data = st.checkbox(
        "Use sample data",
        value=not bool(OPENWEATHER_API_KEY),
        help="Enable to use sample data instead of making API calls"
    )
    
    # API key note
    if not OPENWEATHER_API_KEY and not use_sample_data:
        st.warning(
            "⚠️ No API key found. Using sample data. "
            "Add your OpenWeatherMap API key in the .env file for real-time data."
        )
        use_sample_data = True
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; font-size: 0.8rem; margin-top: 1rem;'>
        <p>Data provided by OpenWeatherMap</p>
        <p>Updated: {}</p>
    </div>
    """.format(pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")), unsafe_allow_html=True)

# Load data
with st.spinner('Loading air quality data...'):
    if not selected_locations:
        st.info("🌍 Search for a city or country above, or select from the suggested locations to view air quality data.")
        st.stop()
    
    try:
        # Load data for all selected locations
        df = load_data(selected_locations, use_sample_data=use_sample_data)
        
        # If no data was loaded, show an error
        if df is None or df.empty:
            st.error("Failed to load data for the selected locations. Please try different locations or enable sample data.")
            st.stop()
            
    except Exception as e:
        st.error(f"An error occurred while loading data: {str(e)}")
        st.error("Please try again or enable sample data.")
        st.stop()

# Sidebar filters
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/4052/4052984.png", width=100)
    st.header("🌤️ Dashboard Filters")
    
    # Date range filter
    st.subheader("Date Range")
    min_date = df['date'].min().date()
    max_date = df['date'].max().date()
    date_range = st.date_input(
        "Select date range",
        [min_date, max_date],
        min_value=min_date,
        max_value=max_date
    )
    
    # Handle date range selection
    if len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date = date_range[0]
        end_date = date_range[0] + timedelta(days=30)
    
    # Location filter with map preview
    st.subheader("Locations")
    all_locations = sorted(df['location'].unique())
    selected_locations = st.multiselect(
        'Select locations to analyze',
        all_locations,
        default=all_locations[:3],
        help="Select one or more locations to analyze"
    )
    
    # Show selected locations on a small map
    if selected_locations:
        map_data = df[df['location'].isin(selected_locations)].drop_duplicates('location')
        st.map(map_data[['latitude', 'longitude']].rename(columns={"latitude": "LAT", "longitude": "LON"}), 
              size=15, color='#FF4B4B')
    
    # Metric selection
    st.subheader("Metrics")
    metric = st.selectbox(
        'Primary metric to analyze',
        ['aqi', 'pm25', 'pm10', 'no2', 'o3', 'temp_c'],
        index=0,
        format_func=lambda x: {
            'aqi': 'Air Quality Index (AQI)',
            'pm25': 'PM2.5 (µg/m³)',
            'pm10': 'PM10 (µg/m³)',
            'no2': 'NO₂ (ppb)',
            'o3': 'O₃ (ppb)',
            'temp_c': 'Temperature (°C)'
        }[x]
    )
    
    # Additional options
    st.subheader("Display Options")
    show_raw_data = st.checkbox("Show raw data", value=False)
    show_forecast = st.checkbox("Show forecast (simulated)", value=True)
    
    # Add a download button for the filtered data
    csv = df[df['location'].isin(selected_locations) & 
             (df['date'].dt.date >= start_date) & 
             (df['date'].dt.date <= end_date)].to_csv(index=False).encode('utf-8')
    
    st.download_button(
        label="📥 Download Current Data",
        data=csv,
        file_name=f'air_quality_data_{start_date}_to_{end_date}.csv',
        mime='text/csv',
        use_container_width=True
    )
    
    # Add a footer
    st.markdown("---")
    st.markdown("### About")
    st.markdown("""
    This dashboard provides insights into air quality metrics and weather conditions.
    
    Data is provided by [OpenWeatherMap](https://openweathermap.org/) when using real-time data.
    """)
    
    # Add API status
    if OPENWEATHER_API_KEY and not use_sample_data:
        st.success("✅ Using OpenWeatherMap API with a valid API key")
    else:
        st.info("ℹ️ Using sample data. To enable real-time data, add your OpenWeatherMap API key to the .env file.")

# Filter data based on selections
filtered_df = df[
    (df['date'].dt.date >= start_date) & 
    (df['date'].dt.date <= end_date) &
    (df['location'].isin(selected_locations))
].copy()

# Calculate daily averages
daily_avg = filtered_df.groupby(['date', 'location', 'aqi_category', 'aqi_color', 'weather']).agg({
    'pm25': 'mean',
    'pm10': 'mean',
    'no2': 'mean',
    'o3': 'mean',
    'temp_c': 'mean',
    'humidity': 'mean',
    'wind_speed': 'mean',
    'aqi': 'mean'
}).reset_index()

# Main content with tabs
tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "📈 Trends", "🌍 Map", "📋 Details"])

# Function to get weather emoji based on weather condition
def get_weather_emoji(weather_condition):
    if not weather_condition or pd.isna(weather_condition):
        return "🌡️"  # Default emoji if weather data is missing
    
    weather_condition = str(weather_condition).lower()
    
    if any(term in weather_condition for term in ['rain', 'drizzle', 'shower']):
        return '🌧️'
    elif any(term in weather_condition for term in ['thunder', 'storm', 'lightning']):
        return '⛈️'
    elif any(term in weather_condition for term in ['snow', 'sleet', 'blizzard']):
        return '❄️'
    elif any(term in weather_condition for term in ['fog', 'mist', 'haze']):
        return '🌫️'
    elif any(term in weather_condition for term in ['cloud', 'overcast']):
        return '☁️'
    elif any(term in weather_condition for term in ['clear', 'sunny', 'fair']):
        return '☀️'
    return '🌡️'  # Default emoji

with tab1:  # Overview tab
    st.markdown("### 🌤️ Air Quality Summary")
    
    if daily_avg.empty:
        st.info("No air quality data available. Please select locations to view data.")
        st.stop()
    
    # Calculate current AQI (most recent data point)
    with st.spinner('Updating air quality data...'):
        current_aqi = daily_avg.sort_values('date').groupby('location').last().reset_index()
        
        # Handle missing values
        current_aqi = current_aqi.fillna({
            'humidity': 'N/A',
            'wind_speed': 'N/A',
            'temp_c': '--',
            'weather': 'No data'
        })
        
        # Create columns for AQI cards (1-4 columns based on number of locations)
        num_columns = max(1, min(4, len(current_aqi)))
        cols = st.columns(num_columns, gap="medium")
        
        # Display AQI cards in a grid
        for idx, (_, row) in enumerate(current_aqi.iterrows()):
            with cols[idx % num_columns]:
                try:
                    aqi = int(round(row['aqi'])) if pd.notna(row['aqi']) else '--'
                    category, color = get_aqi_category(aqi) if aqi != '--' else ('No data', '#666666')
                    weather_emoji = get_weather_emoji(row.get('weather', ''))
                    
                    # Get temperature, handle missing values
                    temp = f"{row['temp_c']:.1f}°C" if pd.notna(row['temp_c']) and row['temp_c'] != 'N/A' else '--°C'
                    
                    # Get humidity, handle missing values
                    humidity = f"{float(row['humidity']):.1f}%" if pd.notna(row['humidity']) and row['humidity'] != 'N/A' else '--%'
                    
                    # Get wind speed, handle missing values
                    wind_speed = f"{float(row['wind_speed']):.1f} m/s" if pd.notna(row['wind_speed']) and row['wind_speed'] != 'N/A' else '-- m/s'
                    
                    # Create a responsive card using Streamlit components with theme support
                    with st.container():
                        # Get theme colors
                        theme = get_theme_colors()
                        
                        # Add responsive CSS with media queries and theme support
                        st.markdown(f"""
                            <style>
                            /* Base styles for all devices */
                            .aqi-card {{
                                background: {theme['card_bg']};
                                border-radius: 12px;
                                padding: 16px;
                                margin-bottom: 20px;
                                box-shadow: 0 2px 4px {theme['shadow']};
                                border-left: 4px solid {color};
                                transition: all 0.3s ease;
                                width: 100%;
                                box-sizing: border-box;
                                color: {theme['text']};
                            }}
                            
                            .aqi-header {{
                                border-bottom: 1px solid {theme['border']};
                                padding-bottom: 10px;
                                margin-bottom: 12px;
                                display: flex;
                                flex-direction: column;
                                gap: 8px;
                            }}
                            
                            .location-name {{
                                font-size: 1.25rem;
                                font-weight: 700;
                                color: {theme['text']};
                                margin: 0;
                                line-height: 1.2;
                            }}
                            
                            .aqi-category {{
                                display: inline-block;
                                background: {color}15;
                                color: {color};
                                padding: 4px 10px;
                                border-radius: 12px;
                                font-size: 0.75rem;
                                font-weight: 600;
                                text-align: center;
                                width: fit-content;
                            }}
                            
                            .aqi-value {{
                                font-size: 2.5rem;
                                font-weight: 800;
                                color: {color};
                                text-align: center;
                                margin: 12px 0;
                                line-height: 1;
                                text-shadow: 0 2px 4px {color}20;
                            }}
                            
                            .weather-section {{
                                background: {theme['weather_bg']};
                                border-radius: 8px;
                                padding: 12px;
                                margin: 16px 0;
                                border: 1px solid {theme['border']};
                            }}
                            
                            .weather-content {{
                                display: flex;
                                flex-direction: column;
                                gap: 8px;
                            }}
                            
                            .weather-row {{
                                display: flex;
                                justify-content: space-between;
                                align-items: center;
                            }}
                            
                            .weather-info {{
                                display: flex;
                                align-items: center;
                                gap: 10px;
                            }}
                            
                            .weather-emoji {{
                                font-size: 1.8rem;
                                line-height: 1;
                            }}
                            
                            .weather-text {{
                                font-size: 1rem;
                                font-weight: 600;
                                color: {theme['text']};
                            }}
                            
                            .weather-label {{
                                font-size: 0.8rem;
                                color: {theme['text_secondary']};
                                margin-top: 2px;
                            }}
                            
                            .temp-display {{
                                text-align: center;
                                min-width: 80px;
                            }}
                            
                            .temp-label {{
                                font-size: 0.8rem;
                                color: {theme['text_secondary']};
                                margin-bottom: 2px;
                            }}
                            
                            .temp-value {{
                                font-size: 1.4rem;
                                font-weight: 700;
                                color: {theme['text']};
                            }}
                            
                            .metrics-container {{
                                display: grid;
                                grid-template-columns: 1fr 1fr;
                                gap: 10px;
                                margin: 16px 0;
                            }}
                            
                            .metric-card {{
                                background: {theme['metric_bg']};
                                border-radius: 8px;
                                padding: 10px;
                                box-shadow: 0 1px 3px {theme['shadow']};
                                border: 1px solid {theme['border']};
                                min-height: 60px;
                                display: flex;
                                align-items: center;
                                transition: all 0.2s ease;
                            }}
                            
                            .metric-icon {{
                                background: {theme['icon_bg']};
                                width: 32px;
                                height: 32px;
                                border-radius: 50%;
                                display: flex;
                                align-items: center;
                                justify-content: center;
                                margin-right: 10px;
                                flex-shrink: 0;
                            }}
                            
                            .wind-icon {{
                                background: {theme['dark_mode'] ? '#1a3a1a' : '#f6ffed'} !important;
                            }}
                            
                            .metric-icon span {{
                                font-size: 1.1rem;
                            }}
                            
                            .metric-value {{
                                font-size: 1.1rem;
                                font-weight: 600;
                                color: {theme['text']};
                                line-height: 1.2;
                            }}
                            
                            .metric-label {{
                                font-size: 0.75rem;
                                color: {theme['text_secondary']};
                                margin-top: 2px;
                            }}
                            
                            .last-updated {{
                                display: flex;
                                justify-content: flex-end;
                                align-items: center;
                                gap: 6px;
                                font-size: 0.75rem;
                                color: {theme['text_secondary']};
                                margin-top: 12px;
                            }}
                            
                            /* Tablet and larger */
                            @media (min-width: 640px) {{
                                .aqi-card {{
                                    padding: 20px;
                                    margin-bottom: 24px;
                                }}
                                
                                .aqi-header {{
                                    flex-direction: row;
                                    justify-content: space-between;
                                    align-items: center;
                                    gap: 16px;
                                }}
                                
                                .location-name {{
                                    font-size: 1.4rem;
                                }}
                                
                                .weather-content {{
                                    flex-direction: row;
                                    justify-content: space-between;
                                    align-items: center;
                                }}
                                
                                .metrics-container {{
                                    grid-template-columns: 1fr 1fr;
                                    gap: 12px;
                                }}
                            }}
                            
                            /* Desktop */
                            @media (min-width: 1024px) {{
                                .aqi-value {{
                                    font-size: 2.8rem;
                                    margin: 16px 0;
                                }}
                                
                                .weather-emoji {{
                                    font-size: 2rem;
                                }}
                                
                                .weather-text {{
                                    font-size: 1.1rem;
                                }}
                                
                                .temp-value {{
                                    font-size: 1.6rem;
                                }}
                                
                                .metric-card {{
                                    padding: 12px;
                                    min-height: 70px;
                                }}
                                
                                .metric-icon {{
                                    width: 36px;
                                    height: 36px;
                                }}
                                
                                .metric-icon span {{
                                    font-size: 1.2rem;
                                }}
                                
                                .metric-value {{
                                    font-size: 1.2rem;
                                }}
                            }}
                            
                            /* Hover effects for devices that support hover */
                            @media (hover: hover) {{
                                .aqi-card:hover {{
                                    transform: translateY(-2px);
                                    box-shadow: 0 4px 12px {theme['shadow']};
                                    background: {theme['hover_bg']};
                                }}
                                
                                .metric-card:hover {{
                                    transform: translateY(-1px);
                                    box-shadow: 0 2px 8px {theme['shadow']};
                                    background: {theme['hover_bg']};
                                }}
                            }}
                            
                            /* System preference for dark mode */
                            @media (prefers-color-scheme: dark) {{
                                .stApp {{
                                    background-color: #121212 !important;
                                    color: #f0f0f0 !important;
                                }}
                                
                                .stSidebar {{
                                    background-color: #1e1e1e !important;
                                }}
                                
                                .stTextInput > div > div > input,
                                .stTextInput > div > div > input:focus {{
                                    background-color: #2d2d2d;
                                    color: #f0f0f0;
                                    border-color: #444;
                                }}
                                
                                .stButton > button {{
                                    background-color: #3a3a3a;
                                    color: #f0f0f0;
                                    border-color: #444;
                                }}
                                
                                .stButton > button:hover {{
                                    background-color: #4a4a4a;
                                    border-color: #666;
                                }}
                            }}
                            
                            /* Dark mode overrides */
                            .stApp[data-theme="dark"] {{
                                background-color: #121212 !important;
                                color: #f0f0f0 !important;
                            }}
                            
                            .stApp[data-theme="dark"] .stSidebar {{
                                background-color: #1e1e1e !important;
                            }}
                            
                            .stApp[data-theme="dark"] .stTextInput > div > div > input,
                            .stApp[data-theme="dark"] .stTextInput > div > div > input:focus {{
                                background-color: #2d2d2d;
                                color: #f0f0f0;
                                border-color: #444;
                            }}
                            
                            .stApp[data-theme="dark"] .stButton > button {{
                                background-color: #3a3a3a;
                                color: #f0f0f0;
                                border-color: #444;
                            }}
                            
                            .stApp[data-theme="dark"] .stButton > button:hover {{
                                background-color: #4a4a4a;
                                border-color: #666;
                            }}
                            </style>
                        """, unsafe_allow_html=True)
                        
                        # Main card content
                        with st.container():
                            # Card header with location and category
                            st.markdown(f"<div class='aqi-card' data-theme='{get_theme()}'>"
                                      f"<div class='aqi-header'>"
                                      f"<div class='location-name'>{row['location']}</div>"
                                      f"<div class='aqi-category'>{category}</div>"
                                      f"</div>", unsafe_allow_html=True)
                            
                            # AQI value
                            st.markdown(f"<div class='aqi-value'>{aqi}</div>", unsafe_allow_html=True)
                            
                            # Weather section
                            st.markdown(f"<div class='weather-section'>"
                                      f"<div class='weather-content'>"
                                      f"<div class='weather-row'>"
                                      f"<div class='weather-info'>"
                                      f"<span class='weather-emoji'>{weather_emoji}</span>"
                                      f"<div>"
                                      f"<div class='weather-text'>{row.get('weather', 'No data')}</div>"
                                      f"<div class='weather-label'>Weather Condition</div>"
                                      f"</div>"
                                      f"</div>"
                                      f"<div class='temp-display'>"
                                      f"<div class='temp-label'>Temperature</div>"
                                      f"<div class='temp-value'>{temp}</div>"
                                      f"</div>"
                                      f"</div>"
                                      f"</div>"
                                      f"</div>", unsafe_allow_html=True)
                            
                            # Metrics section
                            st.markdown(f"<div class='metrics-container'>"
                                      f"<div class='metric-card'>"
                                      f"<div class='metric-icon'><span>💧</span></div>"
                                      f"<div>"
                                      f"<div class='metric-value'>{humidity}</div>"
                                      f"<div class='metric-label'>Humidity</div>"
                                      f"</div>"
                                      f"</div>"
                                      f"<div class='metric-card'>"
                                      f"<div class='metric-icon wind-icon'><span>💨</span></div>"
                                      f"<div>"
                                      f"<div class='metric-value'>{wind_speed}</div>"
                                      f"<div class='metric-label'>Wind Speed</div>"
                                      f"</div>"
                                      f"</div>"
                                      f"</div>"
                                      f"<div class='last-updated'>"
                                      f"<span>🕒</span>"
                                      f"<span>Updated: {pd.to_datetime(row['date']).strftime('%b %d, %I:%M %p') if pd.notna(row.get('date')) else '--:--'}</span>"
                                      f"</div>"
                                      f"</div>", unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Error displaying data for {row.get('location', 'this location')}: {str(e)}")
                    st.exception(e)  # This will show the full traceback in the app for debugging
    
    # Add some space
    st.markdown("<div style='margin: 30px 0;'></div>", unsafe_allow_html=True)
    
    # Weather vs AQI Scatter Plot with better styling
    st.markdown("### 🌦️ Weather vs Air Quality")
    
    if daily_avg.empty:
        st.info("No data available for visualization. Please select locations to view trends.")
    else:
        # Create a copy of the data and handle NaN values
        plot_data = daily_avg.copy()
        
        # Fill NaN values in humidity with the mean, or 50 if all values are NaN
        if 'humidity' in plot_data.columns:
            mean_humidity = plot_data['humidity'].mean()
            plot_data['humidity'] = plot_data['humidity'].fillna(mean_humidity if not pd.isna(mean_humidity) else 50)
        
        # Ensure we have valid data for the plot
        if not plot_data.empty and 'temp_c' in plot_data.columns and 'aqi' in plot_data.columns:
            fig_scatter = px.scatter(
                plot_data,
                x='temp_c',
                y='aqi',
                color='location',
                size='humidity',
                hover_data={
                    'location': True,
                    'date': '|%Y-%m-%d %H:%M',
                    'weather': True,
                    'temp_c': ':.1f°C',
                    'humidity': ':.0f%',
                    'aqi': ':.0f',
                    'wind_speed': ':.1f m/s'
                },
                labels={
                    'temp_c': 'Temperature (°C)',
                    'aqi': 'Air Quality Index (AQI)',
                    'humidity': 'Humidity',
                    'location': 'Location'
                },
                title='Temperature vs Air Quality Index',
                size_max=30,  # Limit the maximum bubble size
                template='plotly_white'
            )
            
            # Customize the plot appearance
            fig_scatter.update_layout(
                plot_bgcolor='rgba(0,0,0,0.02)',
                paper_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(
                    title='Temperature (°C)',
                    showgrid=True,
                    gridcolor='rgba(0,0,0,0.05)',
                    showline=True,
                    linewidth=1,
                    linecolor='lightgray'
                ),
                yaxis=dict(
                    title='Air Quality Index (AQI)',
                    showgrid=True,
                    gridcolor='rgba(0,0,0,0.05)',
                    showline=True,
                    linewidth=1,
                    linecolor='lightgray'
                ),
                legend=dict(
                    title='',
                    orientation='h',
                    yanchor='bottom',
                    y=1.02,
                    xanchor='right',
                    x=1
                ),
                hovermode='closest',
                margin=dict(l=0, r=0, t=40, b=20),
                height=500
            )
            
            # Customize hover template
            fig_scatter.update_traces(
                hovertemplate="""
                <b>%{customdata[0]}</b><br>
                Date: %{customdata[1]}<br>
                Weather: %{customdata[2]}<br>
                Temp: %{customdata[3]}<br>
                AQI: %{y:.0f}<br>
                Humidity: %{customdata[4]}<br>
                Wind: %{customdata[5]}<br>
                <extra></extra>
                """
            )
            
            st.plotly_chart(fig_scatter, use_container_width=True, theme=None)
        else:
            st.warning("Insufficient data to generate the weather vs AQI scatter plot.")
    
    # Add some space before the next section
    st.markdown("<div style='margin: 40px 0;'></div>", unsafe_allow_html=True)

with tab2:  # Trends tab
    # Time series chart
    st.markdown("### 📈 Trends Over Time")
    
    # Allow comparison of multiple metrics
    compare_metrics = st.multiselect(
        'Compare with additional metrics',
        ['pm25', 'pm10', 'no2', 'o3', 'temp_c', 'humidity'],
        default=[],
        key='compare_metrics'
    )
    
    # Create figure with secondary y-axis
    fig = go.Figure()
    
    # Add primary metric
    for location in selected_locations:
        location_data = daily_avg[daily_avg['location'] == location]
        fig.add_trace(go.Scatter(
            x=location_data['date'],
            y=location_data[metric],
            name=f"{location} - {metric.upper()}",
            mode='lines+markers',
            line=dict(width=2)
        ))
    
    # Add secondary metrics
    for i, comp_metric in enumerate(compare_metrics):
        if i == 0:  # Only show legend for first secondary metric to avoid duplicates
            show_legend = True
            name = f"{comp_metric.upper()} (right axis)"
        else:
            show_legend = False
            name = f"{comp_metric.upper()}"
            
        fig.add_trace(go.Scatter(
            x=daily_avg['date'].unique(),
            y=daily_avg.groupby('date')[comp_metric].mean(),
            name=name,
            yaxis='y2',
            line=dict(dash='dot', width=1, color=f'rgb({200 - i*30}, {100 - i*20}, {i*50})'),
            showlegend=show_legend
        ))
    
    # Update layout with rangeslider and buttons
    fig.update_layout(
        xaxis=dict(
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1m", step="month", stepmode="backward"),
                    dict(count=3, label="3m", step="month", stepmode="backward"),
                    dict(count=6, label="6m", step="month", stepmode="backward"),
                    dict(count=1, label="YTD", step="year", stepmode="todate"),
                    dict(step="all")
                ])
            ),
            rangeslider=dict(visible=True),
            type="date"
        ),
        yaxis=dict(title=metric.upper()),
        yaxis2=dict(
            title="Secondary Metrics",
            overlaying="y",
            side="right",
            showgrid=False
        ) if compare_metrics else {},
        hovermode="x unified",
        height=500
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Heatmap of AQI by location and date
    st.subheader("🔥 AQI Heatmap by Location and Date")
    heatmap_df = filtered_df.pivot_table(
        index='location',
        columns=pd.Grouper(key='date', freq='W'),
        values='aqi',
        aggfunc='mean'
    )
    
    fig_heatmap = px.imshow(
        heatmap_df,
        labels=dict(x="Week", y="Location", color="AQI"),
        color_continuous_scale='RdYlGn_r',  # Red-Yellow-Green (reversed)
        aspect="auto"
    )
    
    # Add AQI color scale annotations
    aqi_breaks = [0, 50, 100, 150, 200, 300, 500]
    aqi_colors = ['#00E400', '#FFFF00', '#FF7E00', '#FF0000', '#8F3F97', '#7E0023']
    
    for i in range(len(aqi_breaks) - 1):
        fig_heatmap.add_annotation(
            x=1.02, 
            y=1 - (i * 0.15),
            xref="paper",
            yref="paper",
            text=f"{aqi_breaks[i]}-{aqi_breaks[i+1]}",
            showarrow=False,
            bgcolor=aqi_colors[i],
            bordercolor='#333',
            borderwidth=1,
            borderpad=2,
            opacity=0.8,
            font=dict(color='black' if i < 3 else 'white')
        )
    
    fig_heatmap.update_layout(
        coloraxis_colorbar=dict(
            title="AQI",
            thicknessmode="pixels", thickness=20,
            lenmode="pixels", len=300,
            yanchor="top", y=1,
            xanchor="left", x=1.02
        ),
        margin=dict(l=100, r=150)  # Add margin for annotations
    )
    
    st.plotly_chart(fig_heatmap, use_container_width=True)

with tab3:  # Map tab
    st.subheader("🌍 Air Quality Map")
    
    # Aggregate data for map
    map_data = filtered_df.groupby(['location', 'latitude', 'longitude']).agg({
        'aqi': 'mean',
        'pm25': 'mean',
        'pm10': 'mean',
        'no2': 'mean',
        'o3': 'mean',
        'temp_c': 'mean',
        'weather': lambda x: x.mode()[0] if not x.empty else 'N/A'
    }).reset_index()
    
    # Add AQI category and color
    map_data[['aqi_category', 'aqi_color']] = map_data['aqi'].apply(
        lambda x: pd.Series(get_aqi_category(x))
    )
    
    # Create map
    fig_map = px.scatter_mapbox(
        map_data,
        lat='latitude',
        lon='longitude',
        color='aqi',
        color_continuous_scale='RdYlGn_r',
        size='aqi',
        size_max=30,
        hover_name='location',
        hover_data={
            'aqi': ':.0f',
            'pm25': ':.1f',
            'pm10': ':.1f',
            'temp_c': ':.1f',
            'weather': True,
            'latitude': False,
            'longitude': False
        },
        zoom=3,
        height=600
    )
    
    # Update map layout
    fig_map.update_layout(
        mapbox_style="open-street-map",
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        coloraxis_colorbar=dict(
            title="AQI",
            thicknessmode="pixels", thickness=20,
            lenmode="pixels", len=300,
            yanchor="top", y=1,
            xanchor="left", x=1.02
        )
    )
    
    st.plotly_chart(fig_map, use_container_width=True)
    
    # Add a table with detailed metrics
    st.subheader("📍 Location Details")
    st.dataframe(
        map_data.drop(['latitude', 'longitude'], axis=1).sort_values('aqi', ascending=False),
        column_config={
            'location': 'Location',
            'aqi': st.column_config.NumberColumn('AQI', format='%.0f'),
            'pm25': st.column_config.NumberColumn('PM2.5', format='%.1f µg/m³'),
            'pm10': st.column_config.NumberColumn('PM10', format='%.1f µg/m³'),
            'no2': st.column_config.NumberColumn('NO₂', format='%.1f ppb'),
            'o3': st.column_config.NumberColumn('O₃', format='%.1f ppb'),
            'temp_c': st.column_config.NumberColumn('Temp', format='%.1f °C'),
            'weather': 'Weather',
            'aqi_category': 'AQI Category',
            'aqi_color': None
        },
        hide_index=True,
        use_container_width=True
    )

with tab4:  # Details tab
    st.subheader("📋 Detailed Data")
    
    # Show data table with all metrics
    st.dataframe(
        filtered_df.sort_values(['date', 'location'], ascending=[False, True]),
        column_config={
            'date': 'Date',
            'location': 'Location',
            'pm25': st.column_config.NumberColumn('PM2.5', format='%.1f µg/m³'),
            'pm10': st.column_config.NumberColumn('PM10', format='%.1f µg/m³'),
            'no2': st.column_config.NumberColumn('NO₂', format='%.1f ppb'),
            'o3': st.column_config.NumberColumn('O₃', format='%.1f ppb'),
            'temp_c': st.column_config.NumberColumn('Temp', format='%.1f °C'),
            'humidity': st.column_config.NumberColumn('Humidity', format='.0f%%'),
            'wind_speed': st.column_config.NumberColumn('Wind Speed', format='.1f m/s'),
            'aqi': st.column_config.NumberColumn('AQI', format='%.0f'),
            'aqi_category': 'AQI Category',
            'weather': 'Weather',
            'latitude': None,
            'longitude': None,
            'aqi_color': None
        },
        hide_index=True,
        use_container_width=True,
        height=500
    )
    
    # Add data export button
    st.download_button(
        label="📥 Export Data as CSV",
        data=filtered_df.to_csv(index=False).encode('utf-8'),
        file_name=f'air_quality_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
        mime='text/csv',
        use_container_width=True
    )

# Add a footer
st.markdown("---")
st.markdown(f"""
<div style="text-align: center; color: #666; font-size: 0.9em; margin-top: 30px;">
    <p>🌤️ Air Quality Dashboard • Data is simulated for demonstration purposes</p>
    <p><small>Last updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</small></p>
</div>
""", unsafe_allow_html=True)
