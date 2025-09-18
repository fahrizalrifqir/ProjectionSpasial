import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import os
import zipfile
import shutil

st.set_page_config(page_title="Analisis Spasial Interaktif", layout="wide")
st.title("🌍 Analisis Spasial Interaktif - Overlay Luasan")

# --- Fungsi load shapefile dari ZIP ---
def load_shapefile_from_zip(uploaded_file, extract_dir):
    if os.path.exists(extract_dir):
        shutil.rmtree(extract_dir)
    os.makedirs(extract_dir, exist_ok=True)

    zip_path = os.path.join(extract_dir, uploaded_file.name)
    with open(zip_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(extract_dir)

    shp_files = [f for f in os.listdir(extract_dir) if f.endswith(".shp")]
    if not shp_files:
        return None
    return gpd.read_file(os.path.join(extract_dir, shp_files[0]))

# --- Upload Tapak ---
uploaded_tapak = st.file_uploader("📂 Upload Shapefile Tapak Proyek (ZIP)", type="zip")

# --- Referensi: pilih dari folder atau upload ---
st.subheader("📂 Pilih Shapefile Referensi (Batas Admin)")
REFERENSI_DIR = "referensi"

# Pastikan folder referensi ada
if not os.path.exists(REFERENSI_DIR):
    os.makedirs(REFERENSI_DIR)

# Daftar shp referensi bawaan
referensi_options = [f for f in os.listdir(REFERENSI_DIR) if f.endswith(".shp")]

referensi_choice = st.selectbox(
    "Pilih Shapefile Referensi",
    ["Unggah file sendiri"] + referensi_options
)

uploaded_ref = None
if referensi_choice == "Unggah file sendiri":
    uploaded_ref = st.file_uploader("Upload Shapefile Referensi (ZIP)", type="zip")

# --- Pilihan basemap ---
basemap_choice = st.selectbox(
    "🗺️ Pilih Basemap",
    ["OpenStreetMap", "ESRI Satelit"]
)

# --- Proses jika tapak ada ---
if uploaded_tapak:
    tapak = load_shapefile_from_zip(uploaded_tapak, "uploads_tapak")

    if tapak is None:
        st.error("❌ Tidak ada file .shp pada ZIP tapak.")
        st.stop()

    # Ambil referensi
    referensi = None
    if referensi_choice == "Unggah file sendiri":
        if uploaded_ref:
            referensi = load_shapefile_from_zip(uploaded_ref, "uploads_ref")
    else:
        referensi = gpd.read_file(os.path.join(REFERENSI_DIR, referensi_choice))

    if referensi is None:
        st.error("❌ Tidak ada referensi yang valid.")
        st.stop()

    # --- Hitung luas ---
    tapak["luas_m2"] = tapak.geometry.area
    overlay = gpd.overlay(tapak, referensi, how="intersection")
    overlay["luas_m2"] = overlay.geometry.area

    st.subheader("📊 Hasil Luasan")
    st.write(f"**Luas Tapak Proyek (m²):** {tapak['luas_m2'].sum():,.2f}")
    st.write(f"**Luas Overlay (m²):** {overlay['luas_m2'].sum():,.2f}")

    # --- Peta interaktif ---
    center = [tapak.geometry.centroid.y.mean(), tapak.geometry.centroid.x.mean()]
    m = folium.Map(
        location=center,
        zoom_start=13,
        tiles="OpenStreetMap" if basemap_choice == "OpenStreetMap" else None
    )

    if basemap_choice == "ESRI Satelit":
        folium.TileLayer("Esri.WorldImagery").add_to(m)

    folium.GeoJson(
        tapak, name="Tapak", style_function=lambda x: {"color": "purple", "fillOpacity": 0.4}
    ).add_to(m)
    folium.GeoJson(
        referensi, name="Referensi (Batas Admin)", style_function=lambda x: {"color": "black", "weight": 1}
    ).add_to(m)
    if not overlay.empty:
        folium.GeoJson(
            overlay, name="Overlay", style_function=lambda x: {"color": "red", "fillOpacity": 0.6}
        ).add_to(m)

    folium.LayerControl().add_to(m)

    st.subheader("🗺️ Peta Interaktif")
    st_folium(m, width=950, height=600)
