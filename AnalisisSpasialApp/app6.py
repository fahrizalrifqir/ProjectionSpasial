import streamlit as st
import geopandas as gpd
import folium
from shapely.ops import unary_union
from streamlit_folium import st_folium

st.set_page_config(layout="wide")
st.title("🗺️ Aplikasi Analisis Spasial Interaktif")

# ================== Upload File ==================
st.sidebar.header("📂 Upload Data")
tapak_file = st.sidebar.file_uploader("Upload Shapefile Tapak (ZIP)", type="zip")
ref_file = st.sidebar.file_uploader("Upload Shapefile Referensi (ZIP)", type="zip")

# Pilihan basemap
basemap_choice = st.sidebar.selectbox(
    "🗺️ Pilih Basemap",
    ["OpenStreetMap", "CartoDB positron", "CartoDB dark_matter", "Stamen Terrain", "Stamen Toner"]
)

# ================== Proses Data ==================
if tapak_file and ref_file:
    # Baca data
    tapak = gpd.read_file(f"zip://{tapak_file.name}")
    referensi = gpd.read_file(f"zip://{ref_file.name}")

    # Samakan CRS ke WGS84
    tapak = tapak.to_crs(epsg=4326)
    referensi = referensi.to_crs(epsg=4326)

    # Hitung overlay (intersection)
    overlay = gpd.overlay(tapak, referensi, how="intersection")

    # ================== Analisis ==================
    luas_tapak = tapak.area.sum() * (111000**2)  # luas kira2 m²
    luas_ref = referensi.area.sum() * (111000**2)
    luas_overlap = overlay.area.sum() * (111000**2)

    st.subheader("📊 Hasil Analisis")
    st.write(f"**Luas Tapak:** {luas_tapak:,.0f} m²")
    st.write(f"**Luas Referensi:** {luas_ref:,.0f} m²")
    st.write(f"**Luas Overlay:** {luas_overlap:,.0f} m²")

    # ================== Peta Interaktif ==================
    st.subheader("🗺️ Peta Interaktif (Geser & Zoom)")

    # Tentukan center map dari tapak
    centroid = tapak.geometry.centroid.iloc[0]
    m = folium.Map(location=[centroid.y, centroid.x], zoom_start=14, tiles=basemap_choice)

    # Tambahkan layer Referensi
    folium.GeoJson(
        referensi,
        name="Referensi",
        style_function=lambda x: {"color": "black", "fillOpacity": 0.1},
    ).add_to(m)

    # Tambahkan layer Tapak
    folium.GeoJson(
        tapak,
        name="Tapak Proyek",
        style_function=lambda x: {"color": "purple", "fillOpacity": 0.4},
        tooltip=folium.GeoJsonTooltip(fields=tapak.columns.tolist(), aliases=tapak.columns.tolist())
    ).add_to(m)

    # Tambahkan layer Overlay
    if not overlay.empty:
        folium.GeoJson(
            overlay,
            name="Overlay",
            style_function=lambda x: {"color": "red", "fillOpacity": 0.6},
        ).add_to(m)

    # Layer control
    folium.LayerControl().add_to(m)

    # Tampilkan peta ke Streamlit
    st_data = st_folium(m, width=900, height=600)
