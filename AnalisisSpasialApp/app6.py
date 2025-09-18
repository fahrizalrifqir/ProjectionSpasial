import streamlit as st
import geopandas as gpd
import os
import zipfile
import shutil
import matplotlib.pyplot as plt
import contextily as ctx
import io
from streamlit_folium import st_folium
import folium

st.set_page_config(layout="wide")
st.title("🗺️ Analisis Spasial Interaktif + Download Peta")

# === Fungsi load shapefile dari ZIP ===
def load_geodataframe_from_zip(uploaded_file, upload_dir):
    try:
        if os.path.exists(upload_dir):
            shutil.rmtree(upload_dir)
        os.makedirs(upload_dir, exist_ok=True)

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

# === Input utama ===
uploaded_file = st.file_uploader("📂 Upload Shapefile Tapak (ZIP)", type="zip")

st.subheader("📂 Pilih atau Unggah Shapefile Referensi")
script_dir = os.path.dirname(os.path.abspath(__file__))
REFERENSI_DIR = os.path.join(script_dir, "referensi")

referensi_files = []
if os.path.exists(REFERENSI_DIR):
    referensi_files = [f for f in os.listdir(REFERENSI_DIR) if f.endswith(".shp")]

referensi_options = ["Unggah file sendiri"] + sorted(referensi_files)
referensi_choice = st.selectbox("Pilih Shapefile Referensi", referensi_options)

uploaded_referensi_file = None
if referensi_choice == "Unggah file sendiri":
    uploaded_referensi_file = st.file_uploader("📂 Upload Shapefile Referensi (ZIP)", type="zip")

# Pilihan basemap
basemap_options = {
    "OpenStreetMap": "OpenStreetMap",
    "ESRI Satelit": "Esri.WorldImagery",
    "Carto Positron": "CartoDB.Positron"
}
basemap_choice = st.selectbox("🌍 Pilih Basemap", list(basemap_options.keys()))

# === Proses data ===
if uploaded_file is not None:
    tapak, error_tapak = load_geodataframe_from_zip(uploaded_file, "uploads")
    if error_tapak:
        st.error(f"❌ Error Tapak: {error_tapak}")
        st.stop()

    # Referensi
    if referensi_choice == "Unggah file sendiri":
        if uploaded_referensi_file:
            referensi, error_ref = load_geodataframe_from_zip(uploaded_referensi_file, "uploaded_referensi")
            if error_ref:
                st.error(f"❌ Error Referensi: {error_ref}")
                st.stop()
        else:
            st.warning("⚠️ Silakan unggah shapefile referensi.")
            st.stop()
    else:
        referensi_path = os.path.join(REFERENSI_DIR, referensi_choice)
        referensi = gpd.read_file(referensi_path)

    # Pastikan semua ke WGS84
    tapak = tapak.to_crs(epsg=4326)
    referensi = referensi.to_crs(epsg=4326)

    # Hitung luas (pakai UTM zona 50S contoh)
    tapak["luas_m2"] = tapak.to_crs(epsg=32750).geometry.area
    overlay = gpd.overlay(tapak, referensi, how="intersection", keep_geom_type=True)
    if not overlay.empty:
        overlay["luas_m2"] = overlay.to_crs(epsg=32750).geometry.area

    # === Hasil Luas ===
    st.subheader("📊 Hasil Luasan")
    st.write(f"**Luas Tapak Proyek (m²):** {tapak['luas_m2'].sum():,.2f}")
    if not overlay.empty:
        st.write(f"**Luas Overlay (m²):** {overlay['luas_m2'].sum():,.2f}")
    else:
        st.write("**Luas Overlay (m²):** 0")

    # === Peta Interaktif ===
    st.subheader("🌍 Peta Interaktif")
    center = [tapak.geometry.centroid.y.mean(), tapak.geometry.centroid.x.mean()]
    m = folium.Map(location=center, zoom_start=13, tiles=basemap_options[basemap_choice])

    folium.GeoJson(referensi, name="Referensi", style_function=lambda x: {"color": "black"}).add_to(m)
    folium.GeoJson(tapak, name="Tapak Proyek", style_function=lambda x: {"color": "purple", "fillOpacity": 0.4}).add_to(m)
    if not overlay.empty:
        folium.GeoJson(overlay, name="Overlay", style_function=lambda x: {"color": "red", "fillOpacity": 0.6}).add_to(m)

    folium.LayerControl().add_to(m)
    st_folium(m, width=900, height=600)

    # === Peta Statis untuk Download ===
    st.subheader("🖼️ Download Peta")
    fig, ax = plt.subplots(figsize=(8, 8))
    referensi.boundary.plot(ax=ax, color="black", linewidth=0.5)
    tapak.plot(ax=ax, color="purple", alpha=0.5)
    if not overlay.empty:
        overlay.plot(ax=ax, color="red", alpha=0.6)
    ctx.add_basemap(ax, crs=tapak.to_crs(epsg=3857).crs, source=ctx.providers.Esri.WorldImagery)
    ax.set_axis_off()
    st.pyplot(fig)

    # Simpan versi download
    img_png = io.BytesIO()
    fig.savefig(img_png, format="png", dpi=300, bbox_inches="tight")
    img_png.seek(0)

    img_jpg = io.BytesIO()
    fig.savefig(img_jpg, format="jpeg", dpi=300, bbox_inches="tight")
    img_jpg.seek(0)

    pdf_file = io.BytesIO()
    fig.savefig(pdf_file, format="pdf", dpi=300, bbox_inches="tight")
    pdf_file.seek(0)

    st.download_button("📥 Download PNG", data=img_png, file_name="peta.png", mime="image/png")
    st.download_button("📥 Download JPEG", data=img_jpg, file_name="peta.jpeg", mime="image/jpeg")
    st.download_button("📥 Download PDF", data=pdf_file, file_name="peta.pdf", mime="application/pdf")
