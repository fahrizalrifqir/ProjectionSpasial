import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import os
import zipfile
import tempfile

st.set_page_config(page_title="Analisis Spasial Interaktif", layout="wide")
st.title("🌍 Analisis Spasial Interaktif")

# =========================
# Upload Shapefile Proyek
# =========================
st.subheader("📂 Upload Shapefile Proyek (ZIP)")
uploaded_file = st.file_uploader("Upload file .zip berisi shapefile proyek", type="zip")

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

# =========================
# Shapefile Referensi
# =========================
st.subheader("📂 Shapefile Referensi")
REFERENSI_DIR = "referensi"
if not os.path.exists(REFERENSI_DIR):
    os.makedirs(REFERENSI_DIR)

# Upload Shapefile Referensi
uploaded_ref = st.file_uploader("Upload Shapefile Referensi (ZIP)", type="zip", key="ref")
if uploaded_ref:
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = os.path.join(tmpdir, "referensi.zip")
        with open(zip_path, "wb") as f:
            f.write(uploaded_ref.read())
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(REFERENSI_DIR)
    st.success("✅ Shapefile referensi berhasil disimpan!")

# List shapefile referensi
shp_files = [f for f in os.listdir(REFERENSI_DIR) if f.endswith(".shp")]
selected_refs = st.multiselect(
    "Pilih Shapefile Referensi",
    shp_files,
    default=shp_files[:1] if shp_files else None
)

gdf_refs = []
for ref_file in selected_refs:
    ref_path = os.path.join(REFERENSI_DIR, ref_file)
    if os.path.exists(ref_path):
        gdf_refs.append(gpd.read_file(ref_path))

# =========================
# Pilihan Zona UTM
# =========================
st.subheader("📐 Pilih Proyeksi UTM untuk Analisis")
col1, col2 = st.columns(2)
with col1:
    utm_zone = st.number_input("Zona UTM", min_value=1, max_value=60, value=48, step=1)
with col2:
    hemisphere = st.radio("Belahan Bumi", ["N", "S"], index=0)

if hemisphere == "N":
    epsg_code = 32600 + utm_zone
else:
    epsg_code = 32700 + utm_zone

st.info(f"EPSG yang dipakai: **{epsg_code}**")

# =========================
# Peta Interaktif Folium
# =========================
if gdf_proyek is not None:
    st.subheader("🗺️ Peta Interaktif")

    # Gunakan centroid proyek sebagai center map
    gdf_centroid = gdf_proyek.to_crs(epsg=4326).geometry.centroid
    center = [gdf_centroid.y.mean(), gdf_centroid.x.mean()]

    m = folium.Map(location=center, zoom_start=12, tiles="CartoDB positron")

    # Tambahkan proyek
    proyek_fields = [c for c in gdf_proyek.columns if c != "geometry"]
    folium.GeoJson(
        gdf_proyek.to_crs(epsg=4326),
        name="Proyek",
        style_function=lambda x: {
            "fillColor": "purple",
            "color": "black",
            "weight": 2,
            "fillOpacity": 0.5,
        },
        tooltip=folium.GeoJsonTooltip(fields=proyek_fields),
    ).add_to(m)

    # Tambahkan referensi
    for i, gdf_ref in enumerate(gdf_refs):
        ref_fields = [c for c in gdf_ref.columns if c != "geometry"]
        folium.GeoJson(
            gdf_ref.to_crs(epsg=4326),
            name=f"Referensi {i+1}",
            style_function=lambda x: {
                "fillColor": "none",
                "color": "gray",
                "weight": 1,
            },
            tooltip=folium.GeoJsonTooltip(fields=ref_fields),
        ).add_to(m)

    folium.LayerControl().add_to(m)

    st_folium(m, width=900, height=600)
