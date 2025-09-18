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
st.title("🌍 Analisis Spasial Interaktif")

# --- Upload Shapefile/KML/KMZ Proyek ---
st.subheader("📂 Upload Shapefile Proyek (ZIP), KML, atau KMZ")

uploaded_files = st.file_uploader(
    "Upload file .zip (shapefile), .kml, atau .kmz (bisa lebih dari 1)",
    type=["zip", "kml", "kmz"],
    accept_multiple_files=True
)

all_gdfs = []
per_shp_zips = []   # simpan hasil per SHP
per_file_zips = []  # simpan hasil per file
all_zip_buffer = BytesIO()

# --- Pilihan Zona UTM ---
st.sidebar.subheader("⚙️ Pengaturan")
utm_zone = st.sidebar.number_input("Zona UTM (misalnya 48 untuk Indonesia barat)", 45, 55, 48)
hemisphere = st.sidebar.selectbox("Belahan Bumi", ["Utara", "Selatan"])
epsg_code = 32600 + utm_zone if hemisphere == "Utara" else 32700 + utm_zone

if uploaded_files:
    with tempfile.TemporaryDirectory() as shpdir:
        with zipfile.ZipFile(all_zip_buffer, "w") as zf_all:
            for uploaded_file in uploaded_files:
                fname, ext = os.path.splitext(uploaded_file.name)
                ext = ext.lower()
                try:
                    with tempfile.TemporaryDirectory() as tmpdir:
                        # --- ZIP (shapefile) ---
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

                        # --- KML ---
                        elif ext == ".kml":
                            kml_path = os.path.join(tmpdir, uploaded_file.name)
                            with open(kml_path, "wb") as f:
                                f.write(uploaded_file.read())
                            gdf = gpd.read_file(kml_path, driver="KML")

                        # --- KMZ ---
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

                        # --- Ringkasan geometry per file ---
                        geom_summary = gdf.geometry.geom_type.value_counts().to_dict()
                        st.markdown(f"### 📂 Konversi ke Shapefile")
                        for geom, count in geom_summary.items():
                            st.write(f"- {geom}: {count} fitur")

                        # --- Perhitungan luas ---
                        try:
                            gdf_projected = gdf.to_crs(epsg=epsg_code)
                            if "Polygon" in geom_summary or "MultiPolygon" in geom_summary:
                                gdf_projected["area_ha"] = gdf_projected.area / 10000
                                total_area = gdf_projected["area_ha"].sum()
                                st.info(f"📐 Total Luas: {total_area:,.2f} ha (EPSG:{epsg_code})")
                        except Exception as e:
                            st.warning(f"Gagal menghitung luas: {e}")

                        st.success(f"✅ {uploaded_file.name} berhasil diproses")

                        # --- Simpan hasil per geometry ---
                        geom_types = {
                            "polygon": ["Polygon", "MultiPolygon"],
                            "line": ["LineString", "MultiLineString"],
                            "point": ["Point", "MultiPoint"],
                        }

                        # ZIP untuk file ini
                        file_zip_buffer = BytesIO()
                        with zipfile.ZipFile(file_zip_buffer, "w") as zf_file:
                            for gname, gtypes in geom_types.items():
                                gdf_sub = gdf[gdf.geometry.geom_type.isin(gtypes)]
                                if not gdf_sub.empty:
                                    shp_path = os.path.join(shpdir, f"{fname}_{gname}.shp")
                                    gdf_sub.to_file(shp_path)

                                    # --- ZIP per SHP ---
                                    shp_zip_buffer = BytesIO()
                                    with zipfile.ZipFile(shp_zip_buffer, "w") as zf_shp:
                                        for f in os.listdir(shpdir):
                                            if f.startswith(f"{fname}_{gname}."):
                                                file_path = os.path.join(shpdir, f)
                                                zf_shp.write(file_path, arcname=f)
                                                zf_file.write(file_path, arcname=f)
                                                zf_all.write(file_path, arcname=f)

                                    per_shp_zips.append((f"{fname}_{gname}", shp_zip_buffer.getvalue()))

                            per_file_zips.append((fname, file_zip_buffer.getvalue()))

                except Exception as e:
                    st.error(f"❌ Gagal memproses {uploaded_file.name}: {e}")

    # --- Download hasil ---
    st.subheader("📥 Download Hasil")

    with st.expander("📦 Download Per Shapefile", expanded=False):
        for shp_name, shp_zip in per_shp_zips:
            st.download_button(
                label=f"⬇️ {shp_name}.zip",
                data=shp_zip,
                file_name=f"{shp_name}.zip",
                mime="application/zip"
            )

    with st.expander("📂 Download Per File", expanded=False):
        for fname, file_zip in per_file_zips:
            st.download_button(
                label=f"⬇️ {fname}.zip",
                data=file_zip,
                file_name=f"{fname}.zip",
                mime="application/zip"
            )

    if len(uploaded_files) > 1:
        with st.expander("📦 Download Semua Sekaligus", expanded=False):
            st.download_button(
                label="⬇️ Download all_files.zip",
                data=all_zip_buffer.getvalue(),
                file_name="all_files.zip",
                mime="application/zip"
            )

# --- Folder Referensi ---
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

# --- Pilih Basemap ---
st.subheader("🗺️ Pilih Basemap")
basemap_choice = st.selectbox(
    "Pilih jenis basemap",
    ["OpenStreetMap", "CartoDB Positron", "CartoDB DarkMatter", "Esri Satellite"]
)

# --- Peta Interaktif ---
if all_gdfs:
    gdf_proyek = gpd.GeoDataFrame(pd.concat(all_gdfs, ignore_index=True), crs=all_gdfs[0].crs)
    gdf_centroid = gdf_proyek.to_crs(epsg=4326).geometry.centroid
    center = [gdf_centroid.y.mean(), gdf_centroid.x.mean()]

    m = folium.Map(location=center, zoom_start=8)

    # Basemap
    if basemap_choice == "OpenStreetMap":
        folium.TileLayer("OpenStreetMap").add_to(m)
    elif basemap_choice == "CartoDB Positron":
        folium.TileLayer("CartoDB positron").add_to(m)
    elif basemap_choice == "CartoDB DarkMatter":
        folium.TileLayer("CartoDB dark_matter").add_to(m)
    elif basemap_choice == "Esri Satellite":
        folium.TileLayer(
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            attr="Tiles © Esri &mdash; Source: Esri, USGS, NOAA",
            name="Esri Satellite",
            overlay=False,
            control=True
        ).add_to(m)

    # Layer proyek
    folium.GeoJson(
        gdf_proyek.to_crs(epsg=4326),
        name="Proyek",
        style_function=lambda x: {"color": "purple", "fillOpacity": 0.5},
    ).add_to(m)

    # Layer referensi
    for i, gdf_ref in enumerate(gdf_refs):
        folium.GeoJson(
            gdf_ref.to_crs(epsg=4326),
            name=f"Referensi {i+1}",
            style_function=lambda x: {"color": "gray", "fillOpacity": 0},
        ).add_to(m)

    folium.LayerControl().add_to(m)

    st.subheader("🗺️ Peta Interaktif")
    st_folium(m, width=900, height=600)
