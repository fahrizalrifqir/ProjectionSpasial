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
file_names = []

if uploaded_files:
    zip_buffer_all = BytesIO()
    with tempfile.TemporaryDirectory() as shpdir:
        with zipfile.ZipFile(zip_buffer_all, "w") as zf_all:

            for uploaded_file in uploaded_files:
                fname, ext = os.path.splitext(uploaded_file.name)
                ext = ext.lower()

                try:
                    with tempfile.TemporaryDirectory() as tmpdir:
                        # ================= ZIP (shapefile) =================
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

                        # ================= KML =================
                        elif ext == ".kml":
                            kml_path = os.path.join(tmpdir, uploaded_file.name)
                            with open(kml_path, "wb") as f:
                                f.write(uploaded_file.read())
                            gdf = gpd.read_file(kml_path, driver="KML")

                        # ================= KMZ =================
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

                        # Tambah kolom nama file sumber
                        gdf["source_file"] = uploaded_file.name
                        all_gdfs.append(gdf)
                        file_names.append(fname)

                        # Ringkasan geometry per file
                        geom_summary = gdf.geometry.geom_type.value_counts().to_dict()
                        st.markdown(f"**📊 Ringkasan geometry dari {uploaded_file.name}:**")
                        for geom, count in geom_summary.items():
                            st.write(f"- {geom}: {count} fitur")

                        # Simpan shapefile hasil konversi (dipisah per geometry type)
                        geom_types = {
                            "polygon": ["Polygon", "MultiPolygon"],
                            "line": ["LineString", "MultiLineString"],
                            "point": ["Point", "MultiPoint"],
                        }

                        for gname, gtypes in geom_types.items():
                            gdf_sub = gdf[gdf.geometry.geom_type.isin(gtypes)]
                            if not gdf_sub.empty:
                                shp_path = os.path.join(shpdir, f"{fname}_{gname}.shp")
                                gdf_sub.to_file(shp_path)

                                # Masukkan ke dalam ZIP besar
                                for f in os.listdir(shpdir):
                                    if f.startswith(f"{fname}_{gname}."):
                                        zf_all.write(os.path.join(shpdir, f), arcname=f)

                        st.success(f"✅ {uploaded_file.name} berhasil diproses")

                except Exception as e:
                    st.error(f"❌ Gagal memproses {uploaded_file.name}: {e}")

    # Download gabungan semua file
    st.download_button(
        label="⬇️ Download Semua SHP (all_files.zip)",
        data=zip_buffer_all.getvalue(),
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
