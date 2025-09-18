import streamlit as st
import geopandas as gpd
import matplotlib.pyplot as plt
import contextily as ctx
import os
import zipfile
import tempfile

st.set_page_config(page_title="Analisis Spasial Interaktif", layout="wide")

st.title("🌍 Analisis Spasial Interaktif")

# --- Upload Shapefile Proyek ---
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

# --- Folder Referensi ---
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
            zip_ref.extractall(REFERENSI_DIR)  # Simpan langsung ke folder referensi

    st.success("✅ Shapefile referensi berhasil disimpan!")

# List semua shapefile referensi yang tersedia permanen
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

# --- Pilihan Zona UTM ---
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

# --- Pilih Basemap ---
st.subheader("🗺️ Pilih Basemap")
basemap_options = {
    "ESRI Satelit": ctx.providers.Esri.WorldImagery,
    "OpenStreetMap": ctx.providers.OpenStreetMap.Mapnik,
    "Carto Positron": ctx.providers.CartoDB.Positron
}
basemap_choice = st.selectbox("Pilih Basemap", list(basemap_options.keys()))

# --- Hasil Luasan & Peta ---
if gdf_proyek is not None:
    st.subheader("📊 Hasil Luasan")
    luas_proyek = gdf_proyek.to_crs(epsg=epsg_code).area.sum()
    st.write(f"**Luas Tapak Proyek (m²):** {luas_proyek:,.2f}")

    if gdf_refs:
        luas_overlay_total = 0
        for gdf_ref in gdf_refs:
            luas_overlay = gpd.overlay(
                gdf_proyek.to_crs(epsg=epsg_code),
                gdf_ref.to_crs(epsg=epsg_code),
                how="intersection"
            ).area.sum()
            luas_overlay_total += luas_overlay
        st.write(f"**Total Luas Overlay (m²):** {luas_overlay_total:,.2f}")
    else:
        st.info("Tidak ada shapefile referensi yang dipilih.")

    # --- Peta Overlay ---
    st.subheader("🗺️ Peta Overlay")
    fig, ax = plt.subplots(figsize=(10, 8))

    for i, gdf_ref in enumerate(gdf_refs):
        gdf_ref.to_crs(epsg=3857).plot(ax=ax, facecolor="none", edgecolor="gray", linewidth=1, label=f"Referensi {i+1}")

    gdf_proyek.to_crs(epsg=3857).plot(ax=ax, facecolor="purple", alpha=0.5, edgecolor="black", label="Proyek")

    ctx.add_basemap(ax, source=basemap_options[basemap_choice], crs="EPSG:3857")
    ax.legend()
    ax.set_axis_off()
    st.pyplot(fig)
