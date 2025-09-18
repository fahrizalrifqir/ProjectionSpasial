import streamlit as st
import geopandas as gpd
import matplotlib.pyplot as plt
import contextily as ctx
import os
import zipfile

# Folder referensi
REFERENSI_DIR = r"F:\AnalisisSpasialApp\referensi"

st.title("🗺️ Analisis Spasial - Overlay Luasan")

# === Upload shapefile proyek ===
uploaded_file = st.file_uploader("Upload Shapefile Tapak Proyek (ZIP)", type="zip")

# === Pilih shapefile referensi dari folder ===
referensi_files = [f for f in os.listdir(REFERENSI_DIR) if f.endswith(".shp")]
referensi_choice = st.selectbox("Pilih Shapefile Referensi", referensi_files)
REFERENSI_PATH = os.path.join(REFERENSI_DIR, referensi_choice)

# === Input zona UTM dan hemisphere ===
zona = st.number_input("Masukkan zona UTM (46 - 54)", min_value=46, max_value=54, value=50)
hemisphere = st.radio("Pilih Hemisfer", ["S", "N"])
hemisphere_code = " +south" if hemisphere == "S" else ""

# === Pilih basemap ===
basemap_options = {
    "OpenStreetMap": ctx.providers.OpenStreetMap.Mapnik,
    "ESRI Satelit": ctx.providers.Esri.WorldImagery,
    "Carto Positron": ctx.providers.CartoDB.Positron,
}
basemap_choice = st.selectbox("Pilih Basemap", list(basemap_options.keys()))

if uploaded_file is not None:
    # Simpan file zip sementara
    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)
    zip_path = os.path.join(upload_dir, uploaded_file.name)

    with open(zip_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    # Ekstrak isi zip
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(upload_dir)

    # Cari file SHP dalam ZIP
    shp_files = [f for f in os.listdir(upload_dir) if f.endswith(".shp")]
    if not shp_files:
        st.error("❌ Tidak ada file .shp dalam ZIP")
    else:
        shp_path = os.path.join(upload_dir, shp_files[0])

        # Baca shapefile proyek
        tapak = gpd.read_file(shp_path)

        # Baca shapefile referensi
        referensi = gpd.read_file(REFERENSI_PATH)

        # === Proyeksi ke UTM sesuai input user ===
        epsg_code = f"326{zona}" if hemisphere == "Utara" else f"327{zona}"
        tapak = tapak.to_crs(epsg=epsg_code)
        referensi = referensi.to_crs(epsg=epsg_code)

        # Hitung luas
        tapak["luas_m2"] = tapak.geometry.area
        overlay = gpd.overlay(tapak, referensi, how="intersection")
        overlay["luas_m2"] = overlay.geometry.area

        # === Tampilkan hasil luas ===
        st.subheader("📊 Hasil Luasan")
        st.write("**Luas Tapak Proyek (m²):**", round(tapak["luas_m2"].sum(), 2))
        st.write("**Luas Overlay (m²):**", round(overlay["luas_m2"].sum(), 2))

        # === Plot peta dengan zoom ke tapak ===
        fig, ax = plt.subplots(figsize=(8, 8))
        referensi.boundary.plot(ax=ax, color="black", linewidth=0.5, label="Referensi")
        tapak.plot(ax=ax, color="purple", alpha=0.5, label="Tapak Proyek")
        overlay.plot(ax=ax, color="red", alpha=0.7, label="Overlay")

        # Zoom ke batas tapak
        ax.set_xlim(tapak.total_bounds[0] - 500, tapak.total_bounds[2] + 500)
        ax.set_ylim(tapak.total_bounds[1] - 500, tapak.total_bounds[3] + 500)

        # Tambahkan basemap
        ctx.add_basemap(ax, source=basemap_options[basemap_choice], crs=tapak.crs.to_string())

        ax.legend()
        ax.set_title("Peta Overlay (Zoom ke Tapak)", fontsize=14)
        st.pyplot(fig)
#python -m streamlit run F:\AnalisisSpasialApp\app6.py