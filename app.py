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

# ----------- සැකසුම් -----------
SHEET_ID = "105w1W6dFLT8muHuU-MBpZbIntNzT78j9jbS9CC-Bz7g"
LIGHT_SHEET = "LIGHT"
COMPLAINTS_SHEET = "COMPLAINTS"

CSV_URL_LIGHT = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={LIGHT_SHEET}"
CSV_URL_COMPLAINTS = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={COMPLAINTS_SHEET}"

FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSf10fJ0_8h2Llw_hS_8DvWWLyhQwqsbVMLDNCYQINSiXlejQ/viewform?embedded=true"

DEFAULT_CENTER = (6.9136, 81.3455)
BROKEN_PATTERN = "Broken|Inactive|අක්‍රිය|කැඩි|Not Working|වැඩ නැත|වැඩ නොකරයි|අබලන්"


@st.cache_data(ttl=60)
def load_light_data():
    try:
        df = pd.read_csv(CSV_URL_LIGHT)
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"LIGHT දත්ත කියවීමේ දෝෂයක්: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=60)
def load_complaints_data():
    try:
        df = pd.read_csv(CSV_URL_COMPLAINTS)
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        return pd.DataFrame()


def parse_gps(val):
    if pd.isna(val):
        return None
    try:
        parts = str(val).split(",")
        if len(parts) == 2:
            return float(parts[0].strip()), float(parts[1].strip())
    except Exception:
        pass
    return None


def is_broken(row) -> bool:
    text = " ".join(str(row.get(c, "")) for c in ["Status", "Remarks", "Pole_Condition"])
    return pd.Series([text]).str.contains(BROKEN_PATTERN, case=False, regex=True).iloc[0]


df_light = load_light_data()
df_complaints = load_complaints_data()

st.title("💡 මඩුල්ල ප්‍රදේශීය සභාව - වීදි ලාම්පු හා පැමිණිලි පද්ධතිය")

tab1, tab2, tab3 = st.tabs(["🗺️ වීදි ලාම්පු සිතියම හා තත්ත්වය", "📋 මහජන පැමිණිලි", "📝 නව පැමිණිල්ලක් යොමු කරන්න"])

with tab1:
    if not df_light.empty:
        df_light["Broken"] = df_light.apply(is_broken, axis=1)
        total_lights = len(df_light)
        broken_lights = int(df_light["Broken"].sum())
        active_lights = total_lights - broken_lights

        col1, col2, col3 = st.columns(3)
        col1.metric("මුළු ලාම්පු සංඛ්‍යාව", total_lights)
        col2.metric("ක්‍රියාත්මක ලාම්පු", active_lights)
        col3.metric("අක්‍රිය ලාම්පු (වැඩ නොකරන)", broken_lights)

        st.markdown("---")
        st.subheader("📍 වීදි ලාම්පු සිතියම")

        m = folium.Map(location=DEFAULT_CENTER, zoom_start=13)

        for _, row in df_light.iterrows():
            coords = parse_gps(row.get("GPS_Location"))
            if coords:
                broken = row["Broken"]
                color = "red" if broken else "green"
                status_text = "අක්‍රියයි (වැඩ නැත)" if broken else "ක්‍රියාත්මකයි"

                popup_html = f"""
                <b>ID:</b> {row.get('ID', 'N/A')}<br>
                <b>වසම:</b> {row.get('Area', 'N/A')}<br>
                <b>පාර:</b> {row.get('Road_Name', 'N/A')}<br>
                <b>තත්ත්වය:</b> {status_text}<br>
                <b>සටහන්:</b> {row.get('Remarks', '-')}<br>
                """
                folium.CircleMarker(
                    location=coords,
                    radius=6,
                    color=color,
                    fill=True,
                    fill_color=color,
                    fill_opacity=0.8,
                    popup=folium.Popup(popup_html, max_width=250),
                ).add_to(m)

        st_folium(m, width=1200, height=500)

        st.markdown("---")
        st.subheader("📊 වසම් අනුව ලාම්පු තත්ත්වය")
        if "E Area " in df_light.columns or "Area" in df_light.columns:
            area_col = "Area" if "Area" in df_light.columns else "E Area "
            summary = df_light.groupby(area_col).agg(
                මුළු_ලාම්පු=("Broken", "size"),
                අක්‍රිය_ලාම්පු=("Broken", "sum")
            ).reset_index()
            summary["ක්‍රියාත්මක"] = summary["මුළු_ලාම්පු"] - summary["අක්‍රිය_ලාම්පු"]
            st.dataframe(summary, use_container_width=True)
    else:
        st.warning("වීදි ලාම්පු දත්ත ලබා ගැනීමට නොහැකි විය.")

with tab2:
    st.subheader("📑 මහජන පැමිණිලි ලැයිස්තුව")
    if not df_complaints.empty:
        col_c1, col_c2 = st.columns(2)
        col_c1.metric("මුළු පැමිණිලි ගණන", len(df_complaints))
        
        st.dataframe(df_complaints, use_container_width=True)
    else:
        st.info("තවම මහජන පැමිණිලි ඇතුළත් වී නොමැත හෝ COMPLAINTS sheet එක හිස්ව පවතී.")

with tab3:
    st.subheader("📝 අලුත් පැමිණිල්ලක් සටහන් කරන්න")
    components.iframe(FORM_URL, height=700, scrolling=True)
