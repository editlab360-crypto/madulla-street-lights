import pandas as pd
import streamlit as st
import folium
import streamlit.components.v1 as components
from streamlit_folium import st_folium

st.set_page_config(
    page_title="මඩුල්ල ප්‍රදේශීය සභා වීදි ලාම්පු ඩෑෂ්බෝඩ් එක",
    page_icon="💡",
    layout="wide",
)

# ---------- සැකසුම් ----------
SHEET_ID = "1O5w1W6dfLT8muHhU-MBpZbIntNzT78j9jbS9CC-Bz7g"
LIGHT_SHEET = "LIGHT"
COMPLAINTS_SHEET = "COMPLAINTS"

CSV_URL_LIGHT = (
    f"https://docs.google.com/spreadsheets/d/{SHEET_ID}"
    f"/gviz/tq?tqx=out:csv&sheet={LIGHT_SHEET}"
)
CSV_URL_COMPLAINTS = (
    f"https://docs.google.com/spreadsheets/d/{SHEET_ID}"
    f"/gviz/tq?tqx=out:csv&sheet={COMPLAINTS_SHEET}"
)

FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSe-16vJbXysS0hkdP434Eri_4Lij9DJH0CoCNT0sjUgpmzYGA/viewform?embedded=true"

DEFAULT_CENTER = (6.9136, 81.3455)
BROKEN_PATTERN = "Broken|Inactive|අක්‍රිය|කැඩි|Not Working|වැඩ නැත|වැඩ නොකරයි|අබලන්"


@st.cache_data(ttl=60)
def load_light_data() -> pd.DataFrame:
    try:
        df = pd.read_csv(CSV_URL_LIGHT)
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"LIGHT දත්ත ලබාගැනීමේ දෝෂයක්: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=60)
def load_complaints_data() -> pd.DataFrame:
    try:
        df = pd.read_csv(CSV_URL_COMPLAINTS)
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        return pd.DataFrame()


def parse_gps(value):
    try:
        lat, lon = str(value).split(",")
        lat, lon = float(lat.strip()), float(lon.strip())
        if -90 <= lat <= 90 and -180 <= lon <= 180:
            return lat, lon
    except (ValueError, AttributeError):
        pass
    return None, None


def is_broken(row) -> bool:
    text = " ".join(
        str(row.get(c, "")) for c in ("Status", "Remarks", "Pole_Condition")
    )
    return pd.Series([text]).str.contains(BROKEN_PATTERN, case=False, regex=True).iloc[0]


df = load_light_data()
df_complaints = load_complaints_data()

st.title("💡 මඩුල්ල ප්‍රදේශීය සභා - වීදි ලාම්පු හා පැමිණිලි කළමනාකරණ පද්ධතිය")

if df.empty:
    st.warning("වීදි ලාම්පු දත්ත හමු නොවීය. Google Sheet එක පරීක්ෂා කරන්න.")
    st.stop()

# ---------- Tower Number Column Find ----------
tower_col = None
for col in df.columns:
    if "tower" in col.lower() or "ටවර්" in col.lower():
        tower_col = col
        break

# ---------- Session State Status Save ----------
if "fixed_towers" not in st.session_state:
    st.session_state.fixed_towers = set()

# ---------- Data Processing ----------
if "GPS_Location" in df.columns:
    coords = df["GPS_Location"].apply(parse_gps)
    df["Lat"] = coords.apply(lambda c: c[0])
    df["Lon"] = coords.apply(lambda c: c[1])
else:
    df["Lat"] = df["Lon"] = None

df["Broken"] = df.apply(is_broken, axis=1)

if tower_col and st.session_state.fixed_towers:
    df.loc[df[tower_col].astype(str).str.strip().isin(st.session_state.fixed_towers), "Broken"] = False

complained_ids = set()
if not df_complaints.empty:
    for col in df_complaints.columns:
        if "id" in col.lower() or "අංක" in col.lower() or "light" in col.lower() or "tower" in col.lower():
            complained_ids.update(df_complaints[col].astype(str).str.strip().values)

if complained_ids:
    if tower_col:
        for t_val in complained_ids:
            if t_val not in st.session_state.fixed_towers:
                df.loc[df[tower_col].astype(str).str.strip() == t_val, "Broken"] = True

df["තත්ත්වය"] = df["Broken"].map({True: "අක්‍රිය", False: "ක්‍රියාත්මක"})

total = len(df)
broken = int(df["Broken"].sum())
active = total - broken

# ---------- Admin Panel (Sidebar) ----------
with st.sidebar:
    st.subheader("🔐 නිලධාරී පිවිසුම (Admin Login)")
    admin_user = st.text_input("පරිශීලක නාමය (Username)")
    admin_pass = st.text_input("මුරපදය (Password)", type="password")
    
    if admin_user == "admin" and admin_pass == "admin123":
        st.success("පිවිසීම සාර්ථකයි!")
        st.markdown("---")
        st.subheader("🛠️ ලාම්පු තත්ත්වය යාවත්කාලීන කරන්න")
        
        if tower_col:
            tower_options = [""] + list(df[tower_col].dropna().astype(str).unique())
            
            input_method = st.radio("ක්‍රමය තෝරන්න:", ["ලැයිස්තුවෙන් තෝරන්න", "අංකය ටයිප් කරන්න"])
            
            fix_tower = ""
            if input_method == "ලැයිස්තුවෙන් තෝරන්න":
                fix_tower = st.selectbox("Tower Number එක තෝරන්න:", options=tower_options)
            else:
                fix_tower = st.text_input("Tower Number එක ටයිප් කරන්න (උදා: 4):")
            
            # Status Selection Box (Active / Broken)
