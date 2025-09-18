import streamlit as st
import geopandas as gpd
import matplotlib.pyplot as plt
import contextily as ctx
import os
import zipfile
import tempfile

# Folder penyimpanan shapefile referensi
REFERENSI_DIR = "referensi"
os.makedirs(REFERENSI_DIR, exist_ok=True)

st.title("🌍 Aplikasi Analisis Spasial")

# -------------------------------
# Upload shapefile tapak
# -------------------------------
st.header("📂 Upload Shapefile Tapak")

tapak_file = st.file_uploader("Upload file .zip berisi shapefile tapak", type="zip")

tapak_gdf = None
if tapak_file:
    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(tapak_file, "r") as zip_ref:
            zip_ref.extractall(tmpdir)
        for file in os.listdir(tmpdir):
            if file.endswith(".shp"):
                tapak_path = os.path.join(tmpdir, file)
                tapak_gdf = gpd.read_file(tapak_path)

if tapak_gdf is not None:
    st.success("✅ Shapefile Tapak berhasil dimuat")

# -------------------------------
# Upload shapefile referensi
# -------------------------------
st.header("📂 Upload Shapefile Referensi")

ref_file = st.file_uploader("Upload file .zip berisi shapefile referensi", type="zip")

if ref_file:
    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(ref_file, "r") as zip_ref:
            zip_ref.extractall(tmpdir)
        for file in os.listdir(tmpdir):
            if file.endswith(".shp"):
                ref_path = os.path.join(tmpdir, file)
                ref_gdf = gpd.read_file(ref_path)
                # simpan ke folder referensi
                base_name = os.path.splitext(file)[0]
                for ext in [".shp", ".dbf", ".shx", ".prj", ".cpg"]:
                    src = os.path.join(tmpdir, base_name + ext)
                    if os.path.exists(src):
                        dst = os.path.join(REFERENSI_DIR, base_name + ext)
                        with open(src, "rb") as fsrc, open(dst, "wb") as fdst:
                            fdst.write(fsrc.read())
                st.success(f"✅ Shapefile Referensi '{base_name}' berhasil disimpan")

# -------------------------------
# Pilih shapefile referensi
# -------------------------------
st.header("🗂️ Pilih Shapefile Referensi")

shp_files = [f for f in os.listdir(REFERENSI_DIR) if f.endswith(".shp")]
ref_gdf = None
selected_ref = st.selectbox("Pilih shapefile referensi", ["(Tidak ada)"] + shp_files)

if selected_ref != "(Tidak ada)":
    ref_path = os.path.join(REFERENSI_DIR, selected_ref)
    ref_gdf = gpd.read_file(ref_path)
    st.success(f"✅ Shapefile Referensi '{selected_ref}' berhasil dimuat")

# -------------------------------
# Hapus shapefile referensi
# -------------------------------
st.header("🗑️ Hapus Shapefile Referensi")

if shp_files:
    file_to_delete = st.selectbox("Pilih shapefile untuk dihapus", shp_files)
    if st.button("Hapus"):
        st.warning(f"⚠️ Anda yakin ingin menghapus **{file_to_delete}** beserta file pendukungnya? Aksi ini tidak bisa dibatalkan.")
        if st.button("✅ Ya, hapus permanen"):
            base_name = file_to_delete[:-4]
            for ext in [".shp", ".dbf", ".shx", ".prj", ".cpg"]:
                path = os.path.join(REFERENSI_DIR, base_name + ext)
                if os.path.exists(path):
                    os.remove(path)
            st.success(f"✅ {file_to_delete} dan file pendukungnya sudah dihapus permanen.")
            st.rerun()
else:
    st.info("Belum ada shapefile referensi yang tersimpan.")

# -------------------------------
# Pilihan basemap & UTM
# -------------------------------
st.header("🗺️ Pilihan Peta")

basemap_option = st.selectbox("Pilih basemap", ["OSM", "ESRI"])
utm_zone = st.text_input("Masukkan EPSG UTM (contoh: 32748 untuk UTM zone 48S)", "32748")

# -------------------------------
# Plot peta
# -------------------------------
if tapak_gdf is not None:
    try:
        # Reproject jika perlu
        tapak_proj = tapak_gdf.to_crs(epsg=int(utm_zone))
        fig, ax = plt.subplots(figsize=(8, 8))
        tapak_proj.plot(ax=ax, color="red", alpha=0.5, label="Tapak")

        if ref_gdf is not None:
            ref_proj = ref_gdf.to_crs(epsg=int(utm_zone))
            ref_proj.plot(ax=ax, edgecolor="black", facecolor="none", label="Referensi")

        # Tambah basemap
        if basemap_option == "OSM":
            ctx.add_basemap(ax, crs=tapak_proj.crs, source=ctx.providers.OpenStreetMap.Mapnik)
        elif basemap_option == "ESRI":
            ctx.add_basemap(ax, crs=tapak_proj.crs, source=ctx.providers.Esri.WorldImagery)

        ax.legend()
        st.pyplot(fig)
    except Exception as e:
        st.error(f"❌ Error saat memproses peta: {e}")
