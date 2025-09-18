import streamlit as st
import geopandas as gpd
import os
import zipfile
import shutil
from streamlit_folium import st_folium
import folium

st.set_page_config(layout="wide")
st.title("🗺️ Analisis Spasial Interaktif - Overlay Luasan")

# === Fungsi bantu ===
def load_geodataframe_from_zip(uploaded_file, upload_dir):
    """Membaca shapefile dari ZIP dan kembalikan sebagai GeoDataFrame"""
    try:
        if os.path.exists(upload_dir):
            shutil.rmtree(upload_dir)
        os.makedirs(upload_dir, exist_ok=True)

        zip_path = os.path.join(upload_dir, uploaded_file.name)
        with open(zip_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(upload_dir)

        shp_files = [f for f in os.listdir(upload_dir) if f.endswith(".shp")]
        if not shp_files:
            return None, "Tidak ada file .shp dalam ZIP"

        shp_path = os.path.join(upload_dir, shp_files[0])
        gdf = gpd.read_file(shp_path)
        return gdf, None

    except Exception as e:
        return None, f"Gagal memproses file: {e}"

# === Input utama ===
uploaded_file = st.file_uploader("📂 Upload Shapefile Tapak (ZIP)", type="zip")

st.subheader("Pilih atau Unggah Shapefile Referensi")
script_dir = os.path.dirname(os.path.abspath(__file__))
REFERENSI_DIR = os.path.join(script_dir, "referensi")

referensi_files = []
try:
    referensi_files = [f for f in os.listdir(REFERENSI_DIR) if f.endswith(".shp")]
except FileNotFoundError:
    st.warning("⚠️ Folder 'referensi' belum ada")

referensi_options = ["Unggah file sendiri"] + sorted(referensi_files)
referensi_choice = st.selectbox("Pilih Shapefile Referensi", referensi_options)

uploaded_referensi_file = None
if referensi_choice == "Unggah file sendiri":
    uploaded_referensi_file = st.file_uploader("Unggah Shapefile Referensi (ZIP)", type="zip")

# Pilihan basemap
basemap_options = {
    "OpenStreetMap": "OpenStreetMap",
    "ESRI Satelit": "Esri.WorldImagery",
    "Carto Positron": "CartoDB.Positron"
}
basemap_choice = st.selectbox("Pilih Basemap", list(basemap_options.keys()))

# === Proses data ===
if uploaded_file is not None:
    tapak, error_tapak = load_geodataframe_from_zip(uploaded_file, "uploads")
    if error_tapak:
        st.error(f"❌ Error pada file tapak: {error_tapak}")
        st.stop()

    # Referensi
    referensi = None
    if referensi_choice == "Unggah file sendiri":
        if uploaded_referensi_file:
            referensi, error_ref = load_geodataframe_from_zip(uploaded_referensi_file, "uploaded_referensi")
            if error_ref:
                st.error(f"❌ Error referensi: {error_ref}")
                st.stop()
        else:
            st.warning("⚠️ Silakan unggah shapefile referensi.")
            st.stop()
    else:
        referensi_path = os.path.join(REFERENSI_DIR, referensi_choice)
        referensi = gpd.read_file(referensi_path)

    # Proyeksi ke WGS84 biar cocok folium
    tapak = tapak.to_crs(epsg=4326)
    referensi = referensi.to_crs(epsg=4326)

    # Hitung luas
    tapak["luas_m2"] = tapak.to_crs(epsg=32750).geometry.area  # contoh zona UTM 50S
    overlay = gpd.overlay(tapak, referensi, how="intersection", keep_geom_type=True)
    overlay["luas_m2"] = overlay.to_crs(epsg=32750).geometry.area

    # Tampilkan hasil luas
    st.subheader("📊 Hasil Luasan")
    st.write(f"**Luas Tapak Proyek (m²):** {tapak['luas_m2'].sum():,.2f}")
    st.write(f"**Luas Overlay (m²):** {overlay['luas_m2'].sum():,.2f}")

    # === Peta Interaktif ===
    st.subheader("🌍 Peta Interaktif")
    center = [tapak.geometry.centroid.y.mean(), tapak.geometry.centroid.x.mean()]
    m = folium.Map(location=center, zoom_start=13, tiles=basemap_options[basemap_choice])

    folium.GeoJson(
        referensi,
        name="Referensi",
        style_function=lambda x: {"color": "black", "weight": 1}
    ).add_to(m)

    folium.GeoJson(
        tapak,
        name="Tapak Proyek",
        style_function=lambda x: {"color": "purple", "fillOpacity": 0.4}
    ).add_to(m)

    if not overlay.empty:
        folium.GeoJson(
            overlay,
            name="Overlay",
            style_function=lambda x: {"color": "red", "fillOpacity": 0.6}
        ).add_to(m)

    folium.LayerControl().add_to(m)
    st_folium(m, width=900, height=600)
