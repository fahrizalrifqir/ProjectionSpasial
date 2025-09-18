import streamlit as st
import geopandas as gpd
import matplotlib.pyplot as plt
import contextily as ctx
import os
import zipfile

# Terapkan caching untuk fungsi yang memuat data GeoPandas
@st.cache_data
def load_geodataframe(path):
    """Fungsi untuk memuat GeoDataFrame dari file."""
    return gpd.read_file(path)

st.title("🗺️ Analisis Spasial - Overlay Luasan")

# === Perbaiki jalur agar selalu berfungsi di Streamlit Cloud ===
# Dapatkan jalur absolut dari direktori skrip saat ini
script_dir = os.path.dirname(os.path.abspath(__file__))
# Gabungkan dengan nama folder referensi
REFERENSI_DIR = os.path.join(script_dir, "referensi")

# === Input widget di luar blok if ===
uploaded_file = st.file_uploader("Upload Shapefile Tapak Proyek (ZIP)", type="zip")

# Pilih atau unggah shapefile referensi
st.subheader("Pilih atau Unggah Shapefile Referensi")
referensi_files = []
try:
    # Menggunakan jalur absolut yang sudah diperbaiki
    referensi_files = [f for f in os.listdir(REFERENSI_DIR) if f.endswith(".shp")]
    if not referensi_files:
        st.warning(f"Folder referensi kosong di jalur: {REFERENSI_DIR}")
except FileNotFoundError:
    st.error(f"❌ Folder 'referensi' tidak ditemukan di jalur: {REFERENSI_DIR}. Pastikan folder diunggah ke GitHub.")
    st.stop()

referensi_options = ["Unggah file sendiri"] + referensi_files
referensi_choice = st.selectbox("Pilih Shapefile Referensi", referensi_options)

uploaded_referensi_file = None
if referensi_choice == "Unggah file sendiri":
    uploaded_referensi_file = st.file_uploader("Unggah Shapefile Referensi (ZIP)", type="zip")

zona = st.number_input("Masukkan zona UTM (46 - 54)", min_value=46, max_value=54, value=50)
hemisphere = st.radio("Pilih Hemisfer", ["S", "N"])

# === Plotting dan analisis hanya akan berjalan jika file diunggah ===
if uploaded_file is not None:
    # Logika untuk menyimpan dan mengekstrak file yang diunggah
    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)
    zip_path = os.path.join(upload_dir, uploaded_file.name)
    with open(zip_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(upload_dir)
    shp_files = [f for f in os.listdir(upload_dir) if f.endswith(".shp")]

    if not shp_files:
        st.error("❌ Tidak ada file .shp dalam ZIP tapak proyek")
    else:
        shp_path = os.path.join(upload_dir, shp_files[0])
        referensi_path = None
        if uploaded_referensi_file is not None:
            referensi_upload_dir = "uploaded_referensi"
            os.makedirs(referensi_upload_dir, exist_ok=True)
            referensi_zip_path = os.path.join(referensi_upload_dir, uploaded_referensi_file.name)
            with open(referensi_zip_path, "wb") as f:
                f.write(uploaded_referensi_file.getbuffer())
            with zipfile.ZipFile(referensi_zip_path, "r") as zip_ref:
                zip_ref.extractall(referensi_upload_dir)
            referensi_shp_files = [f for f in os.listdir(referensi_upload_dir) if f.endswith(".shp")]
            if not referensi_shp_files:
                st.error("❌ Tidak ada file .shp dalam ZIP referensi")
                st.stop()
            referensi_path = os.path.join(referensi_upload_dir, referensi_shp_files[0])
        elif referensi_choice != "Unggah file sendiri":
            referensi_path = os.path.join(REFERENSI_DIR, referensi_choice)
        
        if referensi_path is None:
            st.warning("Silakan unggah file referensi atau pilih salah satu.")
        else:
            tapak = load_geodataframe(shp_path)
            referensi = load_geodataframe(referensi_path)

            epsg_code = f"326{zona}" if hemisphere == "N" else f"327{zona}"
            tapak = tapak.to_crs(epsg=epsg_code)
            referensi = referensi.to_crs(epsg=epsg_code)

            tapak["luas_m2"] = tapak.geometry.area
            overlay = gpd.overlay(tapak, referensi, how="intersection")
            overlay["luas_m2"] = overlay.geometry.area

            st.subheader("📊 Hasil Luasan")
            st.write("**Luas Tapak Proyek (m²):**", round(tapak["luas_m2"].sum(), 2))
            st.write("**Luas Overlay (m²):**", round(overlay["luas_m2"].sum(), 2))
            
            # --- Plotting Code ---
            fig, ax = plt.subplots(figsize=(8, 8))
            
            basemap_options = {
                "OpenStreetMap": ctx.providers.OpenStreetMap.Mapnik,
                "ESRI Satelit": ctx.providers.Esri.WorldImagery,
                "Carto Positron": ctx.providers.CartoDB.Positron,
            }
            basemap_choice = st.selectbox("Pilih Basemap", list(basemap_options.keys()))
            ctx.add_basemap(ax, source=basemap_options[basemap_choice], crs=tapak.crs.to_string())
            
            referensi.boundary.plot(ax=ax, color="black", linewidth=0.5, label="Referensi")
            tapak.plot(ax=ax, color="purple", alpha=0.5, label="Tapak Proyek")
            overlay.plot(ax=ax, color="red", alpha=0.7, label="Overlay")
            
            ax.set_xlim(tapak.total_bounds[0] - 500, tapak.total_bounds[2] + 500)
            ax.set_ylim(tapak.total_bounds[1] - 500, tapak.total_bounds[3] + 500)
            
            ax.legend()
            ax.set_title("Peta Overlay (Zoom ke Tapak)", fontsize=14)
            st.pyplot(fig)
