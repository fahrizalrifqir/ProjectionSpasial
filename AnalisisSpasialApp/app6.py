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

# --- Shapefile Referensi (default + upload opsional) ---
st.subheader("📂 Pilih Shapefile Referensi (Batas Admin)")
REFERENSI_DIR = "referensi"

if not os.path.exists(REFERENSI_DIR):
    os.makedirs(REFERENSI_DIR)

# Tambahkan default batas_admin.shp
default_ref = "batas_admin.shp"
referensi_options = []
if os.path.exists(os.path.join(REFERENSI_DIR, default_ref)):
    referensi_options.append(default_ref)

referensi_options += [f for f in os.listdir(REFERENSI_DIR) if f.endswith(".shp") and f != default_ref]

referensi_choice = st.selectbox(
    "Pilih Shapefile Referensi",
    referensi_options + ["Unggah file sendiri"]
)

gdf_ref = None
if referensi_choice == "Unggah file sendiri":
    uploaded_ref = st.file_uploader("Upload Shapefile Referensi (ZIP)", type="zip", key="ref")
    if uploaded_ref:
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, "referensi.zip")
            with open(zip_path, "wb") as f:
                f.write(uploaded_ref.read())
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(tmpdir)

            for file in os.listdir(tmpdir):
                if file.endswith(".shp"):
                    gdf_ref = gpd.read_file(os.path.join(tmpdir, file))
                    break
else:
    if os.path.exists(os.path.join(REFERENSI_DIR, referensi_choice)):
        gdf_ref = gpd.read_file(os.path.join(REFERENSI_DIR, referensi_choice))

# --- Pilih Basemap ---
st.subheader("🗺️ Pilih Basemap")
basemap_options = {
    "ESRI Satelit": ctx.providers.Esri.WorldImagery,
    "OpenStreetMap": ctx.providers.OpenStreetMap.Mapnik,
    "Carto Positron": ctx.providers.CartoDB.Positron
}
basemap_choice = st.selectbox("Pilih Basemap", list(basemap_options.keys()))

# --- Hasil Luasan ---
if gdf_proyek is not None:
    st.subheader("📊 Hasil Luasan")
    luas_proyek = gdf_proyek.to_crs(epsg=3857).area.sum()
    st.write(f"**Luas Tapak Proyek (m²):** {luas_proyek:,.2f}")

    if gdf_ref is not None:
        luas_overlay = gpd.overlay(
            gdf_proyek.to_crs(epsg=3857),
            gdf_ref.to_crs(epsg=3857),
            how="intersection"
        ).area.sum()
        st.write(f"**Luas Overlay (m²):** {luas_overlay:,.2f}")
    else:
        st.info("Tidak ada shapefile referensi yang dipilih.")

    # --- Peta Overlay ---
    st.subheader("🗺️ Peta Overlay")
    fig, ax = plt.subplots(figsize=(10, 8))

    if gdf_ref is not None:
        gdf_ref.to_crs(epsg=3857).plot(ax=ax, facecolor="none", edgecolor="gray", linewidth=1, label="Referensi")

    gdf_proyek.to_crs(epsg=3857).plot(ax=ax, facecolor="purple", alpha=0.5, edgecolor="black", label="Proyek")

    ctx.add_basemap(ax, source=basemap_options[basemap_choice], crs="EPSG:3857")
    ax.legend()
    ax.set_axis_off()
    st.pyplot(fig)
