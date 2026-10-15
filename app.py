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

# Google Form link එක
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

# ---------- දත්ත සකස් කිරීම ----------
if "GPS_Location" in df.columns:
    coords = df["GPS_Location"].apply(parse_gps)
    df["Lat"] = coords.apply(lambda c: c[0])
    df["Lon"] = coords.apply(lambda c: c[1])
else:
    df["Lat"] = df["Lon"] = None

df["Broken"] = df.apply(is_broken, axis=1)

# මහජන පැමිණිලි ලැබී ඇති ලාම්පු IDs හඳුනා ගැනීම
complained_ids = set()
if not df_complaints.empty:
    # Form එකේ ලාම්පු අංකය ඇතුළත් වන තීරුව සම්මත ලෙස පරීක්ෂා කිරීම (ഉදා: Light_ID හෝ ID)
    for col in df_complaints.columns:
        if "id" in col.lower() or "අංක" in col.lower() or "light" in col.lower():
            complained_ids.update(df_complaints[col].astype(str).str.strip().values)

# පැමිණිල්ලක් ලැබී ඇත්නම්, එය Broken (අක්‍රිය) ලෙස සලකුණු කිරීම
if complained_ids and "ID" in df.columns:
    df.loc[df["ID"].astype(str).str.strip().isin(complained_ids), "Broken"] = True

df["තත්ත්වය"] = df["Broken"].map({True: "අක්‍රිය (පැමිණිලි ලැබී ඇත)", False: "ක්‍රියාත්මක"})

total = len(df)
broken = int(df["Broken"].sum())
active = total - broken

# ---------- ටැබ් සැකසුම ----------
tab1, tab2, tab3 = st.tabs([
    "🗺️ වීදි ලාම්පු සිතියම හා තත්ත්වය", 
    "📋 මහජන පැමිණිලි", 
    "📝 නව පැමිණිල්ලක් යොමු කරන්න"
])

with tab1:
    # ---------- KPI ----------
    c1, c2, c3 = st.columns(3)
    c1.metric("මුළු ලාම්පු ප්‍රමාණය", total)
    c2.metric("ක්‍රියාත්මක ලාම්පු", active)
    c3.metric(
        "අක්‍රිය ලාම්පු / පැමිණිලි",
        broken,
        delta=f"-{broken}" if broken else "0",
        delta_color="inverse",
    )

    st.markdown("---")
    st.subheader("📍 වීදි ලාම්පු සිතියම")

    valid = df.dropna(subset=["Lat", "Lon"])
    if valid.empty:
        center = DEFAULT_CENTER
    else:
        center = (valid["Lat"].mean(), valid["Lon"].mean())

    m = folium.Map(location=center, zoom_start=14)

    def cell(row, col):
        v = row.get(col, "")
        return "-" if pd.isna(v) or str(v).strip() == "" else v

    for _, row in valid.iterrows():
        light_id = str(row.get("ID", "")).strip()
        has_complaint = light_id in complained_ids
        
        color = "red" if row["Broken"] or has_complaint else "green"
        icon = "remove-circle" if row["Broken"] or has_complaint else "ok-sign"
        
        complaint_tag = "<br><b style='color:red;'>⚠️ මහජන පැමිණිල්ලක් ලැබී ඇත!</b>" if has_complaint else ""
        
        popup_html = (
            f"<b>ID:</b> {cell(row,'ID')}<br>"
            f"<b>Area:</b> {cell(row,'Area')}<br>"
            f"<b>E Area:</b> {cell(row,'E Area')}<br>"
            f"<b>Road:</b> {cell(row,'Road_Name')}<br>"
            f"<b>Bulb:</b> {cell(row,'Bulb_Type')}<br>"
            f"<b>Pole:</b> {cell(row,'Pole_Condition')}<br>"
            f"<b>Tower No:</b> {cell(row,'Tower Number')}<br>"
            f"<b>Last Maint.:</b> {cell(row,'Last_Maintenance_Date')}<br>"
            f"<b>Remarks:</b> {cell(row,'Remarks')}<br>"
            f"<b>තත්ත්වය:</b> {row['තත්ත්වය']}"
            f"{complaint_tag}"
        )
        folium.Marker(
            location=[row["Lat"], row["Lon"]],
            popup=folium.Popup(popup_html, max_width=280),
            tooltip=str(cell(row, "ID")),
            icon=folium.Icon(color=color, icon=icon, prefix="glyphicon"),
        ).add_to(m)

    st_folium(m, height=520, use_container_width=True, returned_objects=[])

    missing = total - len(valid)
    if missing:
        st.caption(f"⚠️ GPS දත්ත නොමැති හෝ වැරදි ලාම්පු {missing}ක් සිතියමේ නොපෙන්වයි.")

    # ---------- වසම් වගුව ----------
    st.markdown("---")
    st.subheader("📊 වසම් අනුව ලාම්පු තත්ත්වය")

    group_cols = [c for c in ("E Area", "Area") if c in df.columns]
    if group_cols:
        summary = (
            df.groupby(group_cols, dropna=False)
            .agg(මුළු_ලාම්පු=("Broken", "size"), අක්‍රිය_ලාම්පු=("Broken", "sum"))
            .reset_index()
        )
        summary["ක්‍රියාත්මක"] = summary["මුළු_ලාම්පු"] - summary["අක්‍රිය_ලාම්පු"]
        st.dataframe(summary, use_container_width=True, hide_index=True)
    else:
        st.info("'Area' / 'E Area' තීරු හමු නොවීය.")

    with st.expander("සියලු දත්ත බලන්න"):
        st.dataframe(df.drop(columns=["Lat", "Lon", "Broken"]), use_container_width=True)

with tab2:
    st.subheader("📑 මහජන පැමිණිලි ලැයිස්තුව")
    if not df_complaints.empty:
        st.metric("මුළු පැමිණිලි සංඛ්‍යාව", len(df_complaints))
        st.markdown("---")
        st.dataframe(df_complaints, use_container_width=True)
    else:
        st.info("තවම මහජන පැමිණිලි කිසිවක් ලැබී නැත හෝ 'COMPLAINTS' ෂීට් එක හිස්ව පවතී.")

with tab3:
    st.subheader("📝 අලුත් පැමිණිල්ලක් යොමු කරන්න")
    st.markdown("අක්‍රිය වී ඇති වීදි ලාම්පු පිළිබඳව ප්‍රදේශීය සභාවට පහසුවෙන් දන්වන්න.")
    
    st.markdown(
        """
        <style>
        .form-container {
            border: 2px solid #e0e0e0;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
            background-color: #ffffff;
            margin-top: 10px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown('<div class="form-container">', unsafe_allow_html=True)
    components.iframe(
        FORM_URL,
        height=850,
        scrolling=True
    )
    st.markdown('</div>', unsafe_allow_html=True)
