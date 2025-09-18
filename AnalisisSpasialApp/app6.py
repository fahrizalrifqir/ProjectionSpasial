import streamlit as st
import geopandas as gpd
import matplotlib.pyplot as plt
import contextily as ctx
import os
import zipfile
import shutil

# === Fungsi untuk memuat GeoDataFrame dari file ZIP ===
@st.cache_data
def load_geodataframe_from_zip(uploaded_file, folder_name="uploads"):
    try:
        # Gunakan path absolut agar folder selalu ada
        base_dir = os.path.dirname(os.path.abspath(__file__))
        upload_dir = os.path.join(base_dir, folder_name)

        if os.path.exists(upload_dir):
            shutil.rmtree(upload_dir)
        os.makedirs(upload_dir, exist_ok=True)

        # Simpan dan ekstrak file ZIP
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

# === Konfigurasi halaman ===
st.set_page_config(layout="wide")
st.title("🗺️ Analisis Spasial - Overlay Luasan")

# === Jalur referensi ===
script_dir = os.path.dirname(os.path.abspath(__file__))
REFERENSI_DIR = os.path.join(script_dir, "referensi")

# === Upload Shapefile Tapak Proyek ===
uploaded_file = st.file_uploader("Upload Shapefile Tapak Proyek (ZIP)", type="zip")

# === Pilih / Upload Referensi ===
st.subheader("Pilih atau Unggah Shapefile Referensi")
referensi_files = []
try:
    referensi_files = [f for f in os.listdir(REFERENSI_DIR) if f.endswith(".shp")]
except FileNotFoundError:
    st.error(f"❌ Folder 'referensi' tidak ditemukan di {REFERENSI_DIR}")
    st.stop()

referensi_options = ["Unggah file sendiri"] + sorted(referensi_files)
referensi_choice = st.selectbox("Pilih Shapefile Referensi", referensi_options)

uploaded_referensi_file = None
if referensi_choice == "Unggah file sendiri":
    uploaded_referensi_file = st.file_uploader("Unggah Shapefile Referensi (ZIP)", type="zip")

# === Input Zona & Hemisfer ===
zona = st.number_input("Masukkan zona UTM (46 - 54)", min_value=46, max_value=54, value=50)
hemisphere = st.radio("Pilih Hemisfer", ["S", "N"])

# === Pilihan Basemap ===
basemap_options = {
    "OpenStreetMap": ctx.providers.OpenStreetMap.Mapnik,
    "ESRI Satelit": ctx.providers.Esri.WorldImagery,
    "Carto Positron": ctx.providers.CartoDB.Positron,
}
basemap_choice = st.selectbox("Pilih Basemap", list(basemap_options.keys()))

# === Jika ada file yang diupload ===
if uploaded_file is not None:
    tapak, error_tapak = load_geodataframe_from_zip(uploaded_file, "uploads")
    if error_tapak:
        st.error(f"❌ Error pada file tapak: {error_tapak}")
        st.stop()

    # --- Proses referensi ---
    referensi_path = None
    if referensi_choice == "Unggah file sendiri":
        if uploaded_referensi_file:
            referensi, error_ref = load_geodataframe_from_zip(uploaded_referensi_file, "uploaded_referensi")
            if error_ref:
                st.error(f"❌ Error pada file referensi: {error_ref}")
                st.stop()
        else:
            st.warning("Silakan unggah file referensi.")
            st.stop()
    else:
        referensi_path = os.path.join(REFERENSI_DIR, referensi_choice)
        referensi = gpd.read_file(referensi_path)

    # --- Reproject ke UTM ---
    epsg_code = f"326{zona}" if hemisphere == "N" else f"327{zona}"
    tapak = tapak.to_crs(epsg=epsg_code)
    referensi = referensi.to_crs(epsg=epsg_code)

    # --- Hitung Luasan ---
    tapak["luas_m2"] = tapak.geometry.area
    overlay = gpd.overlay(tapak, referensi, how="intersection", keep_geom_type=True)
    overlay["luas_m2"] = overlay.geometry.area

    # === Tampilkan hasil luasan ===
    st.subheader("📊 Hasil Luasan")
    luas_tapak = f"{tapak['luas_m2'].sum():,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    luas_overlay = f"{overlay['luas_m2'].sum():,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    st.write(f"**Luas Tapak Proyek (m²):** {luas_tapak}")
    st.write(f"**Luas Overlay (m²):** {luas_overlay}")

    # === Plotting Peta ===
    st.subheader("Peta Overlay")
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.set_aspect("equal")

    # Plot shapefile dulu
    referensi.boundary.plot(ax=ax, color="black", linewidth=0.5, label="Referensi")
    tapak.plot(ax=ax, color="purple", alpha=0.5, label="Tapak Proyek")
    if not overlay.empty:
        overlay.plot(ax=ax, color="red", alpha=0.7, label="Overlay")

    # Baru tambahkan basemap terakhir
    try:
        ctx.add_basemap(ax, source=basemap_options[basemap_choice], crs=tapak.crs.to_string())
    except Exception as e:
        st.warning(f"⚠️ Gagal memuat basemap {basemap_choice}. Error: {e}")

    # Atur tampilan
    ax.set_xlim(tapak.total_bounds[0] - 500, tapak.total_bounds[2] + 500)
    ax.set_ylim(tapak.total_bounds[1] - 500, tapak.total_bounds[3] + 500)
    ax.legend()
    ax.set_title("Peta Overlay", fontsize=16)

    st.pyplot(fig)
