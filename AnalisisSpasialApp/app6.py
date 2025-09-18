import streamlit as st
import geopandas as gpd
import matplotlib.pyplot as plt
import contextily as ctx
import os
import zipfile

# Terapkan caching untuk fungsi yang memuat data GeoPandas
@st.cache_data
def load_geodataframe_from_zip(uploaded_file, upload_dir):
    """Fungsi untuk memuat GeoDataFrame dari file ZIP yang diunggah."""
    try:
        # Hapus konten folder unggahan sebelumnya untuk menghindari konflik
        if os.path.exists(upload_dir):
            for file in os.listdir(upload_dir):
                os.remove(os.path.join(upload_dir, file))
        else:
            os.makedirs(upload_dir, exist_ok=True)
            
        # Simpan dan ekstrak file yang baru diunggah
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

st.set_page_config(layout="wide")
st.title("🗺️ Analisis Spasial - Overlay Luasan")

# === Jalur yang disesuaikan untuk GitHub dan lokal ===
script_dir = os.path.dirname(os.path.abspath(__file__))
REFERENSI_DIR = os.path.join(script_dir, "referensi")

# Tambahkan tombol untuk membersihkan cache
if st.button("Bersihkan Cache dan Muat Ulang"):
    st.cache_data.clear()
    st.experimental_rerun()

# === Input widget utama ===
uploaded_file = st.file_uploader("Upload Shapefile Tapak Proyek (ZIP)", type="zip")

st.subheader("Pilih atau Unggah Shapefile Referensi")
referensi_files = []
try:
    referensi_files = [f for f in os.listdir(REFERENSI_DIR) if f.endswith(".shp")]
    if not referensi_files:
        st.warning(f"Folder referensi kosong di jalur: {REFERENSI_DIR}")
except FileNotFoundError:
    st.error(f"❌ Folder 'referensi' tidak ditemukan. Pastikan folder 'referensi' ada di direktori yang sama dengan 'app.py' atau 'app6.py'.")
    st.stop()

referensi_options = ["Unggah file sendiri"] + sorted(referensi_files)
referensi_choice = st.selectbox("Pilih Shapefile Referensi", referensi_options)

uploaded_referensi_file = None
if referensi_choice == "Unggah file sendiri":
    uploaded_referensi_file = st.file_uploader("Unggah Shapefile Referensi (ZIP)", type="zip")

zona = st.number_input("Masukkan zona UTM (46 - 54)", min_value=46, max_value=54, value=50)
hemisphere = st.radio("Pilih Hemisfer", ["S", "N"])

# === Widget basemap dipindahkan ke atas agar dapat diperbarui ===
basemap_options = {
    "OpenStreetMap": ctx.providers.OpenStreetMap.Mapnik,
    "ESRI Satelit": ctx.providers.Esri.WorldImagery,
    "Carto Positron": ctx.providers.CartoDB.Positron,
}
basemap_choice = st.selectbox("Pilih Basemap", list(basemap_options.keys()))

# === Plotting dan analisis hanya akan berjalan jika file diunggah ===
if uploaded_file is not None:
    upload_dir = "uploads"
    
    # Panggil fungsi cached dengan file_uploader sebagai input
    tapak, error_tapak = load_geodataframe_from_zip(uploaded_file, upload_dir)
    
    if error_tapak:
        st.error(f"❌ Error pada file tapak: {error_tapak}")
        st.stop()
    
    referensi_path = None
    if referensi_choice == "Unggah file sendiri":
        if uploaded_referensi_file:
            referensi_upload_dir = "uploaded_referensi"
            os.makedirs(referensi_upload_dir, exist_ok=True)
            referensi_zip_path = os.path.join(referensi_upload_dir, uploaded_referensi_file.name)
            with open(referensi_zip_path, "wb") as f:
                f.write(uploaded_referensi_file.getbuffer())
            with zipfile.ZipFile(referensi_zip_path, "r") as zip_ref:
                zip_ref.extractall(referensi_upload_dir)
            referensi_shp_files = [f for f in os.listdir(referensi_upload_dir) if f.endswith(".shp")]
            if not referensi_shp_files:
                st.error("❌ Tidak ada file .shp dalam ZIP referensi yang diunggah")
                st.stop()
            referensi_path = os.path.join(referensi_upload_dir, referensi_shp_files[0])
        else:
            st.warning("Silakan unggah file referensi.")
            st.stop()
    else:
        referensi_path = os.path.join(REFERENSI_DIR, referensi_choice)
    
    if referensi_path:
        referensi = gpd.read_file(referensi_path)

        epsg_code = f"326{zona}" if hemisphere == "N" else f"327{zona}"
        try:
            tapak = tapak.to_crs(epsg=epsg_code)
            referensi = referensi.to_crs(epsg=epsg_code)
        except Exception as e:
            st.error(f"❌ Error saat melakukan proyeksi ulang: {e}. Pastikan file Shapefile proyek memiliki sistem koordinat yang valid.")
            st.stop()

        tapak["luas_m2"] = tapak.geometry.area
        overlay = gpd.overlay(tapak, referensi, how="intersection", keep_geom_type=True)
        overlay["luas_m2"] = overlay.geometry.area

        st.subheader("📊 Hasil Luasan")
        
        luas_tapak_str = f"{tapak['luas_m2'].sum():,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
        luas_overlay_str = f"{overlay['luas_m2'].sum():,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
        
        st.write(f"**Luas Tapak Proyek (m²):** {luas_tapak_str}")
        st.write(f"**Luas Overlay (m²):** {luas_overlay_str}")
        
        # --- Kode Plotting ---
        st.subheader("Peta Overlay")
        
        fig, ax = plt.subplots(figsize=(10, 10))
        ax.set_aspect('equal')

        try:
            ctx.add_basemap(ax, source=basemap_options[basemap_choice], crs=tapak.crs.to_string())
        except Exception as e:
            st.warning(f"⚠️ Gagal memuat basemap: {basemap_choice}. Menampilkan peta tanpa basemap. Error: {e}")

        referensi.boundary.plot(ax=ax, color="black", linewidth=0.5, label="Referensi")
        tapak.plot(ax=ax, color="purple", alpha=0.5, label="Tapak Proyek")
        if not overlay.empty:
            overlay.plot(ax=ax, color="red", alpha=0.7, label="Overlay")
        
        ax.set_xlim(tapak.total_bounds[0] - 500, tapak.total_bounds[2] + 500)
        ax.set_ylim(tapak.total_bounds[1] - 500, tapak.total_bounds[3] + 500)
        
        ax.legend()
        ax.set_title("Peta Overlay (Zoom ke Tapak)", fontsize=16)
        st.pyplot(fig)
