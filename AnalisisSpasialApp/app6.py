import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import os
import zipfile
import tempfile
from io import BytesIO
import pandas as pd

st.set_page_config(page_title="Analisis Spasial Interaktif", layout="wide")
st.title("🌍 Analisis Spasial Interaktif (Optimasi RAM)")

# --- Upload Proyek ---
st.subheader("📂 Upload Shapefile Proyek (ZIP), KML, atau KMZ")
uploaded_files = st.file_uploader(
    "Upload file .zip (shapefile), .kml, atau .kmz (bisa lebih dari 1)",
    type=["zip", "kml", "kmz"],
    accept_multiple_files=True
)

all_gdfs = []
if uploaded_files:
    with tempfile.TemporaryDirectory() as tmpdir:
        for uploaded_file in uploaded_files:
            fname, ext = os.path.splitext(uploaded_file.name)
            ext = ext.lower()
            try:
                if ext == ".zip":
                    zip_path = os.path.join(tmpdir, uploaded_file.name)
                    with open(zip_path, "wb") as f:
                        f.write(uploaded_file.read())
                    with zipfile.ZipFile(zip_path, "r") as zip_ref:
                        zip_ref.extractall(tmpdir)
                    shp_files = [f for f in os.listdir(tmpdir) if f.endswith(".shp")]
                    if not shp_files:
                        st.error(f"❌ Tidak ada .shp di {uploaded_file.name}")
                        continue
                    gdf = gpd.read_file(os.path.join(tmpdir, shp_files[0]))

                elif ext == ".kml":
                    kml_path = os.path.join(tmpdir, uploaded_file.name)
                    with open(kml_path, "wb") as f:
                        f.write(uploaded_file.read())
                    gdf = gpd.read_file(kml_path, driver="KML")

                elif ext == ".kmz":
                    kmz_path = os.path.join(tmpdir, uploaded_file.name)
                    with open(kmz_path, "wb") as f:
                        f.write(uploaded_file.read())
                    with zipfile.ZipFile(kmz_path, "r") as kmz_ref:
                        kmz_ref.extractall(tmpdir)
                    kml_files = [f for f in os.listdir(tmpdir) if f.endswith(".kml")]
                    if not kml_files:
                        st.error(f"❌ Tidak ada .kml dalam {uploaded_file.name}")
                        continue
                    gdf = gpd.read_file(os.path.join(tmpdir, kml_files[0]), driver="KML")
                else:
                    st.error(f"❌ Format {ext} belum didukung")
                    continue

                gdf["source_file"] = uploaded_file.name
                all_gdfs.append(gdf)
                st.success(f"✅ {uploaded_file.name} berhasil diproses")

            except Exception as e:
                st.error(f"❌ Gagal memproses {uploaded_file.name}: {e}")

# --- Upload Shapefile Referensi ---
st.subheader("📂 Shapefile Referensi")
REFERENSI_DIR = "referensi"
if not os.path.exists(REFERENSI_DIR):
    os.makedirs(REFERENSI_DIR)

uploaded_ref = st.file_uploader("Upload Shapefile Referensi (ZIP)", type="zip", key="ref")
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

# --- Pilih Zona UTM ---
st.subheader("📐 Pilihan Sistem Koordinat")
col1, col2 = st.columns(2)
utm_zone = col1.number_input("Masukkan nomor zona UTM", min_value=46, max_value=54, value=48)
hemisphere = col2.radio("Hemisfer", ["N", "S"], index=0)
epsg_code = 32600 + utm_zone if hemisphere == "N" else 32700 + utm_zone

# --- Hitung Luas + Overlap ---
if all_gdfs:
    gdf_proyek = gpd.GeoDataFrame(pd.concat(all_gdfs, ignore_index=True), crs=all_gdfs[0].crs)
    gdf_proj = gdf_proyek.to_crs(epsg=epsg_code)

    # Luas total
    gdf_proj["area_m2"] = gdf_proj.geometry.area
    st.metric("📏 Total Luas Proyek (ha)", round(gdf_proj["area_m2"].sum() / 10000, 2))

    # Overlap dengan referensi
    if gdf_refs:
        gdf_ref = gpd.GeoDataFrame(pd.concat(gdf_refs, ignore_index=True), crs=gdf_refs[0].crs).to_crs(epsg=epsg_code)

        # Filter referensi dengan bounding box
        gdf_ref = gdf_ref[gdf_ref.intersects(gdf_proj.unary_union.envelope)]

        # Sederhanakan geometri tampilan (hemat RAM)
        gdf_proj_simplified = gdf_proj.copy()
        gdf_proj_simplified["geometry"] = gdf_proj_simplified.geometry.simplify(tolerance=50)

        gdf_ref_simplified = gdf_ref.copy()
        gdf_ref_simplified["geometry"] = gdf_ref_simplified.geometry.simplify(tolerance=50)

        # Hitung overlap asli (tanpa simplify)
        overlap = gpd.overlay(gdf_proj, gdf_ref, how="intersection")
        overlap["area_m2"] = overlap.geometry.area
        st.metric("📏 Luas Overlap dengan Referensi (ha)", round(overlap["area_m2"].sum() / 10000, 2))

# --- Peta Interaktif ---
    gdf_centroid = gdf_proj.to_crs(epsg=4326).geometry.centroid
    center = [gdf_centroid.y.mean(), gdf_centroid.x.mean()]
    m = folium.Map(location=center, zoom_start=8)

    folium.GeoJson(
        gdf_proj_simplified.to_crs(epsg=4326),
        name="Proyek",
        style_function=lambda x: {"color": "purple", "fillOpacity": 0.5},
    ).add_to(m)

    for i, gdf_ref in enumerate(gdf_refs):
        folium.GeoJson(
            gdf_ref.to_crs(epsg=4326),
            name=f"Referensi {i+1}",
            style_function=lambda x: {"color": "gray", "fillOpacity": 0},
        ).add_to(m)

    if not overlap.empty:
        folium.GeoJson(
            overlap.to_crs(epsg=4326),
            name="Overlap",
            style_function=lambda x: {"color": "red", "fillOpacity": 0.7},
        ).add_to(m)

    folium.LayerControl().add_to(m)
    st.subheader("🗺️ Peta Interaktif")
    st_folium(m, width=900, height=600)
