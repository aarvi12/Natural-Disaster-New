import streamlit as st
import requests
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
import openai

# Optional JS Eval for geolocation
try:
    from streamlit_js_eval import streamlit_js_eval
    JS_EVAL_AVAILABLE = True
except ImportError:
    JS_EVAL_AVAILABLE = False

# Load API keys
openai.api_key = st.secrets.get("OPENAI_API_KEY", None)
GOOGLE_API_KEY = st.secrets.get("GOOGLE_API_KEY", None)

# Disaster types
DISASTER_OPTIONS = ["Earthquake", "Flood", "Wildfire", "Hurricane", "Tornado", "Landslide", "Pandemic"]

# App settings
st.set_page_config(page_title="🌪️ Disaster Rescue Assistant", layout="wide")
st.markdown("<h1 style='text-align: center; color: #FF6B6B;'>🌍 Natural Disaster Rescue Assistant</h1>", unsafe_allow_html=True)
st.markdown("---")

# Get coordinates from address
def get_coordinates(address):
    url = f"https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": address, "key": GOOGLE_API_KEY}
    res = requests.get(url, params=params, timeout=10)
    res.raise_for_status()
    results = res.json().get("results")
    if results:
        loc = results[0]["geometry"]["location"]
        return loc["lat"], loc["lng"]
    return None, None

# Google Places API
def get_google_places(lat, lon, place_type, radius_meters):
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "location": f"{lat},{lon}",
        "radius": radius_meters,
        "type": place_type,
        "key": GOOGLE_API_KEY
    }
    res = requests.get(url, params=params, timeout=10)
    res.raise_for_status()
    return res.json().get("results", [])

# AI Rescue Plan
def generate_rescue_plan(disaster, location):
    prompt = f"""
You are an emergency response assistant. Generate a concise and actionable rescue plan for a user located in "{location}" facing a "{disaster}".
Include 3-5 steps, mention communication, medical help, safety zones, and local resources.
"""
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
    )
    return response['choices'][0]['message']['content'].strip()

# Sidebar - User Input
with st.sidebar:
    st.header("📍 Location & Disaster")
    
   
    address = st.text_input("Enter address:", placeholder="Ex: 1600 Amphitheatre Pkwy, Mountain View, CA")

    disaster_type = st.selectbox("🌋 Disaster Type:", DISASTER_OPTIONS)
    radius_miles = st.slider("📏 Search Radius (miles):", 1, 10, 5)
    radius_meters = radius_miles * 1609

# Determine coordinates
lat, lon = None, None
detected_address =""
if "lat" in st.session_state and "lon" in st.session_state:
    lat, lon = st.session_state.lat, st.session_state.lon
    geolocator = Nominatim(user_agent="disaster_helper")
    try:
        location = geolocator.reverse((lat, lon))
        detected_address = location.address if location else "Address not found"
    except:
        pass
elif address:
    lat, lon = get_coordinates(address)
    detected_address = address if lat and lon else "Address not found"

# Show detected address
if detected_address =="":
    st.markdown("### 📌 Detected Address")
   
else: 
    st.markdown(f"### 📌 Detected/Entered Address: `{detected_address}`")

# If location is valid, proceed
if lat and lon:
    # Rescue Plan
    with st.spinner("🧠 Generating Rescue Plan..."):
        st.markdown("## 📝 AI-Generated Rescue Plan")
        plan = generate_rescue_plan(disaster_type, detected_address)
        st.markdown(f"""
<div style="background-color:#FDF1DC; padding: 15px; border-radius: 10px; border-left: 5px solid #FFA726;">
{plan}
</div>
""", unsafe_allow_html=True)

    # Map
    m = folium.Map(location=[lat, lon], zoom_start=14)
    folium.Marker(
        [lat, lon],
        popup="📍 You are here",
        icon=folium.DivIcon(html='<div style="font-size:24px;">📍</div>')
    ).add_to(m)

    place_types = {
        "hospital": "🏥",
        "police": "👮",
        "church": "⛪"  # Used as proxy for shelter
    }

    st.markdown("## 🗺️ Nearby Help Map")
    cols = st.columns(len(place_types))

    for i, (place_type, emoji) in enumerate(place_types.items()):
        with cols[i]:
            places = get_google_places(lat, lon, place_type, radius_meters)
            st.metric(label=f"{emoji} {place_type.title()}s Found", value=len(places))
            for place in places:
                name = place.get("name", "Unknown")
                loc = place["geometry"]["location"]
                folium.Marker(
                    [loc["lat"], loc["lng"]],
                    popup=f"{emoji} {name}\n{place.get('vicinity', '')}",
                    icon=folium.DivIcon(html=f'<div style="font-size:24px;">{emoji}</div>')
                ).add_to(m)

    st_folium(m, width=1000, height=600)

else:
    st.warning("⚠️ Please enter a valid address or enable browser location to continue.")
