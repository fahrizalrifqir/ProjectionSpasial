import streamlit as st
import geopandas as gpd
import matplotlib.pyplot as plt
import contextily as ctx
import os
import zipfile
import shutil

# ================= Fungsi Load Shapefile dari ZIP =================
@st.cache_data
def load_geodataframe_from_zip(uploaded_file, folder_name="uploads"):
    try:
        # Gunakan path absolut biar aman
        base_dir = os.path.dirname(os.path.abspath(__file__))
        upload_dir = os.path.join(base_dir, folder_name)

        # Bersihkan folder sebelumnya
        if os.path.exists(upload_dir):
            shutil.rmtree(upload_dir)
        os.makedirs(upload_dir, exist_ok=True)

        # Simpan dan ekstrak file ZIP
        zip_path = os.path.join(upload_dir, uploaded_file.name)
        with open(zip_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(upload_dir)

        # Cari file SHP
        shp_files = [f for f in os.listdir(upload_dir) if f.endswith(".shp")]
        if not shp_files:
            return None, "Tidak ada file .shp dalam ZIP"

        shp_path = os.path.join(upload_dir, shp_files[0])
        gdf = gpd.read_file(shp_path)
        return gdf, None
    except Exception as e:
        return None, f"Gagal memproses file: {e}"

# ================= Konfigurasi Halaman =================
st.set_page_config(layout="wide")
st.title("🗺️ Analisis Spasial - Overlay Luasan")

# Path folder referensi
script_dir = os.path.dirname(os.path.abspath(__file__))
REFERENSI_DIR = os.path.join(script_dir, "referensi")

# Tombol bersihkan cache
if st.button("Bersihkan Cache dan Muat Ulang"):
    st.cache_data.clear()
    st.rerun()

# ================= Input Utama =================
uploaded_file = st.file_uploader("Upload Shapefile Tapak Proyek (ZIP)", type="zip")

st.subheader("Pilih atau Unggah Shapefile Referensi")
referensi_files = []
try:
    referensi_files = [f for f in os.listdir(REFERENSI_DIR) if f.endswith(".shp")]
    if not referensi_files:
        st.warning(f"Folder referensi kosong di jalur: {REFERENSI_DIR}")
except FileNotFoundError:
    st.error(f"❌ Folder 'referensi' tidak ditemukan.")
    st.stop()

referensi_options = ["Unggah file sendiri"] + sorted(referensi_files)
referensi_choice = st.selectbox("Pilih Shapefile Referensi", referensi_options)

uploaded_referensi_file = None
if referensi_choice == "Unggah file sendiri":
    uploaded_referensi_file = st.file_uploader("Unggah Shapefile Referensi (ZIP)", type="zip")

zona = st.number_input("Masukkan zona UTM (46 - 54)", min_value=46, max_value=54, value=50)
hemisphere = st.radio("Pilih Hemisfer", ["S", "N"])

#
