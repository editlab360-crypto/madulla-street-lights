import pandas as pd
import streamlit as st
import folium
import streamlit.components.v1 as components
from streamlit_folium import st_folium

st.set_page_config(
    page_title="මඩුල්ල ප්‍රාදේශීය සභා වීදි ලාම්පු ඩෑෂ්බෝඩ් එක",
    page_icon="💡",
    layout="wide",
)

# ---------- සැකසුම් ----------
SHEET_ID = "1O5w1W6dfLT8muHhU-MBpZbIntNzT78j9jbS9CC-Bz7g"
SHEET_NAME = "LIGHT"
CSV_URL = (
    f"https://docs.google.com/spreadsheets/d/{SHEET_ID}"
    f"/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"
)

# Google Form link එක මෙතැනට දා ඇත
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSfl0fJ0_8h2LLw_hs_8DvVWLyhQwqsbVBMLDNCYQINsIXlejQ/viewform?embedded=true"

DEFAULT_CENTER = (6.9136, 81.3455)
BROKEN_PATTERN = "Broken|Inactive|අක්‍රිය|කැඩි|Not Working|වැඩ නැත|වැඩ නොකරයි|අබලන්"

@st.cache_data(ttl=60)
def load_data() -> pd.DataFrame:
    try:
        df = pd.read_csv(CSV_URL)
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(
            f"දත්ත ලබාගැනීමේ දෝෂයක්: {e}. Google Sheet එක 'Anyone with the link"
            " can view' ලෙස share කර ඇත්දැයි බලන්න."
        )
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


df = load_data()

st.title("💡 මඩුල්ල ප්‍රාදේශීය සභා - වීදි ලාම්පු කළමනාකරණ පද්ධතිය")

if df.empty:
    st.warning("දත්ත හමු නොවීය. Google Sheet එක සහ sheet නම පරීක්ෂා කරන්න.")
    st.stop()

# ---------- දත්ත සකස් කිරීම ----------
if "GPS_Location" in df.columns:
    coords = df["GPS_Location"].apply(parse_gps)
    df["Lat"] = coords.apply(lambda c: c[0])
    df["Lon"] = coords.apply(lambda c: c[1])
else:
    df["Lat"] = df["Lon"] = None
    st.warning("'GPS_Location' තීරුව Sheet එකේ නැහැ.")

df["Broken"] = df.apply(is_broken, axis=1)
df["තත්ත්වය"] = df["Broken"].map({True: "අක්‍රිය", False: "ක්‍රියාත්මක"})

total = len(df)
broken = int(df["Broken"].sum())
active = total - broken

# ---------- KPI ----------
c1, c2, c3 = st.columns(3)
c1.metric("මුළු ලාම්පු ප්‍රමාණය", total)
c2.metric("ක්‍රියාත්මක ලාම්පු", active)
c3.metric(
    "අක්‍රිය ලාම්පු",
    broken,
    delta=f"-{broken}" if broken else "0",
    delta_color="inverse",
)

st.markdown("---")

# ---------- සිතියම + Form ----------
map_col, form_col = st.columns([2, 1])

with map_col:
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
        color = "red" if row["Broken"] else "green"
        icon = "remove-circle" if row["Broken"] else "ok-sign"
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
        )
        folium.Marker(
            [row["Lat"], row["Lon"]],
            popup=folium.Popup(popup_html, max_width=280),
            tooltip=str(cell(row, "ID")),
            icon=folium.Icon(color=color, icon=icon, prefix="glyphicon"),
        ).add_to(m)

    st_folium(m, height=520, use_container_width=True, returned_objects=[])

    missing = total - len(valid)
    if missing:
        st.caption(f"⚠️ GPS දත්ත නොමැති හෝ වැරදි ලාම්පු {missing}ක් සිතියමේ නොපෙන්වයි.")

with form_col:
    st.subheader("🛠️ අක්‍රිය ලාම්පු පැමිණිලි")
    st.caption("ලාම්පුවේ ID එක ඇතුලත් කර පැමිණිලි කරන්න.")
    components.iframe(FORM_URL, height=600, scrolling=True)

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
