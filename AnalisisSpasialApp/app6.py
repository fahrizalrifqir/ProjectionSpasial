import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import os
import zipfile
import tempfile

# --- Konfigurasi Halaman ---
st.set_page_config(page_title="Analisis Spasial Interaktif", layout="wide")
st.title("🌍 Analisis Spasial Interaktif dengan Peta Interaktif")

# =====================================================================
# 1. Upload Shapefile Proyek
# =====================================================================
st.subheader("📂 Upload Shapefile Proyek (ZIP)")

uploaded_file = st.file_uploader(
    "Upload file .zip berisi shapefile proyek", 
    type="zip"
)

gdf_proyek = None
if uploaded_file:
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = os.path.join(tmpdir, "proyek.zip")
        with open(zip_path, "wb") as f:
            f.write(uploaded_file.read())
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(tmpdir)

        for file in os.listdir(tmpdir):
            if file.endswith(".shp"):
                gdf_proyek = gpd.read_file(os.path.join(tmpdir, file))
                break

# =====================================================================
# 2. Shapefile Referensi
# =====================================================================
st.subheader("📂 Shapefile Referensi")

REFERENSI_DIR = "referensi"
if not os.path.exists(REFERENSI_DIR):
    os.makedirs(REFERENSI_DIR)

uploaded_ref = st.file_uploader(
    "Upload Shapefile Referensi (ZIP)", 
    type="zip", 
    key="ref"
)

if uploaded_ref:
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = os.path.join(tmpdir, "referensi.zip")
        with open(zip_path, "wb") as f:
            f.write(uploaded_ref.read())
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(REFERENSI_DIR)
    st.success("✅ Shapefile referensi berhasil disimpan!")

shp_files = [f for f in os.listdir(REFERENSI_DIR) if f.endswith(".shp")]
selected_refs = st.multiselect("Pilih Shapefile Referensi", shp_files)

gdf_refs = []
for ref_file in selected_refs:
    ref_path = os.path.join(REFERENSI_DIR, ref_file)
    if os.path.exists(ref_path):
        gdf_refs.append(gpd.read_file(ref_path))

# =====================================================================
# 3. Pilihan Basemap
# =====================================================================
st.subheader("🗺️ Pilih Basemap")

basemap_options = {
    "OpenStreetMap": "OpenStreetMap",
    "ESRI Satelit": "Esri.WorldImagery",
    "Carto Positron": "CartoDB.Positron"
}
basemap_choice = st.selectbox("Pilih Basemap", list(basemap_options.keys()))

# =====================================================================
# 4. Tampilkan Peta Interaktif
# =====================================================================
if gdf_proyek is not None:
    st.subheader("🗺️ Peta Interaktif")

    # Gunakan centroid untuk zoom awal
    centroid = gdf_proyek.to_crs(epsg=4326).geometry.centroid.iloc[0]
    m = folium.Map(
        location=[centroid.y, centroid.x],
        zoom_start=12,
        tiles=basemap_options[basemap_choice]
    )

    # Tambahkan proyek
    folium.GeoJson(
        gdf_proyek.to_crs(epsg=4326),
        name="Proyek",
        style_function=lambda x: {"fillColor": "purple", "color": "black", "weight": 2, "fillOpacity": 0.5},
        tooltip=folium.GeoJsonTooltip(fields=gdf_proyek.columns.tolist())
    ).add_to(m)

    # Tambahkan referensi
    for i, gdf_ref in enumerate(gdf_refs):
        folium.GeoJson(
            gdf_ref.to_crs(epsg=4326),
            name=f"Referensi {i+1}",
            style_function=lambda x: {"fillColor": "none", "color": "gray", "weight": 1},
            tooltip=folium.GeoJsonTooltip(fields=gdf_ref.columns.tolist())
        ).add_to(m)

    folium.LayerControl().add_to(m)
    st_folium(m, width=900, height=600)
