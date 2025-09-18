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

# --- Upload Shapefile/KML Proyek ---
st.subheader("📂 Upload Shapefile Proyek (ZIP) atau banyak KML")
uploaded_files = st.file_uploader(
    "Upload file .zip (shapefile) atau .kml (bisa lebih dari 1 KML)",
    type=["zip", "kml"],
    accept_multiple_files=True
)

gdf_proyek = None
all_gdfs = []  # list gabungan
if uploaded_files:
    for uploaded_file in uploaded_files:
        ext = os.path.splitext(uploaded_file.name)[1].lower()
        fname = os.path.splitext(uploaded_file.name)[0]

        if ext == ".zip":  # Shapefile ZIP
            with tempfile.TemporaryDirectory() as tmpdir:
                zip_path = os.path.join(tmpdir, "proyek.zip")
                with open(zip_path, "wb") as f:
                    f.write(uploaded_file.read())
                with zipfile.ZipFile(zip_path, "r") as zip_ref:
                    zip_ref.extractall(tmpdir)

                for file in os.listdir(tmpdir):
                    if file.endswith(".shp"):
                        gdf = gpd.read_file(os.path.join(tmpdir, file))
                        gdf["source_file"] = uploaded_file.name
                        all_gdfs.append(gdf)
                        break

        elif ext == ".kml":  # File KML
            with tempfile.NamedTemporaryFile(delete=False, suffix=".kml") as tmpfile:
                tmpfile.write(uploaded_file.read())
                tmpfile_path = tmpfile.name

            try:
                gdf_kml = gpd.read_file(tmpfile_path, driver="KML")
                gdf_kml["source_file"] = uploaded_file.name
                all_gdfs.append(gdf_kml)

                # Ringkasan geometry
                geom_summary = gdf_kml.geometry.geom_type.value_counts().to_dict()
                st.markdown(f"**📊 Ringkasan geometry dari {uploaded_file.name}:**")
                for geom, count in geom_summary.items():
                    st.write(f"- {geom}: {count} fitur")

                # Konversi ke SHP per geometry type dan buat zip sendiri
                with tempfile.TemporaryDirectory() as tmpdir:
                    zip_buffer = BytesIO()
                    geom_types = {
                        "polygon": ["Polygon", "MultiPolygon"],
                        "line": ["LineString", "MultiLineString"],
                        "point": ["Point", "MultiPoint"],
                    }

                    with zipfile.ZipFile(zip_buffer, "w") as zf:
                        for gname, gtypes in geom_types.items():
                            gdf_sub = gdf_kml[gdf_kml.geometry.geom_type.isin(gtypes)]
                            if not gdf_sub.empty:
                                shp_path = os.path.join(tmpdir, f"{fname}_{gname}.shp")
                                gdf_sub.to_file(shp_path)

                                for f in os.listdir(tmpdir):
                                    if f.startswith(f"{fname}_{gname}."):
                                        zf.write(os.path.join(tmpdir, f), arcname=f)

                    st.download_button(
                        label=f"⬇️ Download SHP dari {uploaded_file.name}",
                        data=zip_buffer.getvalue(),
                        file_name=f"{fname}.zip",
                        mime="application/zip"
                    )

            except Exception as e:
                st.error(f"❌ Gagal membaca {uploaded_file.name}: {e}")

    # Gabungan semua layer jadi 1
    if all_gdfs:
        gdf_proyek = gpd.GeoDataFrame(pd.concat(all_gdfs, ignore_index=True), crs=all_gdfs[0].crs)

        # Ringkasan gabungan
        st.markdown("### 📊 Ringkasan geometry dari semua file")
        geom_counts = gdf_proyek.geometry.geom_type.value_counts()
        for gtype, count in geom_counts.items():
            st.write(f"- {gtype}: {count} fitur")

        # Konversi gabungan
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_buffer = BytesIO()
            geom_types = {
                "polygon": ["Polygon", "MultiPolygon"],
                "line": ["LineString", "MultiLineString"],
                "point": ["Point", "MultiPoint"],
            }

            with zipfile.ZipFile(zip_buffer, "w") as zf:
                for gname, gtypes in geom_types.items():
                    gdf_sub = gdf_proyek[gdf_proyek.geometry.geom_type.isin(gtypes)]
                    if not gdf_sub.empty:
                        shp_path = os.path.join(tmpdir, f"all_{gname}.shp")
                        gdf_sub.to_file(shp_path)

                        for f in os.listdir(tmpdir):
                            if f.startswith(f"all_{gname}."):
                                zf.write(os.path.join(tmpdir, f), arcname=f)

            st.download_button(
                label="⬇️ Download SHP Gabungan",
                data=zip_buffer.getvalue(),
                file_name="all_kmls_shp.zip",
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
if gdf_proyek is not None:
    gdf_centroid = gdf_proyek.to_crs(epsg=4326).geometry.centroid
    center = [gdf_centroid.y.mean(), gdf_centroid.x.mean()]
    m = folium.Map(location=center, zoom_start=12)

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
