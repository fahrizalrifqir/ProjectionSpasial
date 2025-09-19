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

# ===============================
# Upload Shapefile/KML/KMZ Proyek
# ===============================
st.subheader("📂 Upload Shapefile Proyek (ZIP), KML, atau KMZ")

uploaded_files = st.file_uploader(
    "Upload file .zip (shapefile), .kml, atau .kmz (bisa lebih dari 1)",
    type=["zip", "kml", "kmz"],
    accept_multiple_files=True
)

all_gdfs = []
per_shp_zips = []
per_file_zips = []
all_zip_buffer = BytesIO()

if uploaded_files:
    with tempfile.TemporaryDirectory() as shpdir:
        with zipfile.ZipFile(all_zip_buffer, "w") as zf_all:
            for uploaded_file in uploaded_files:
                fname, ext = os.path.splitext(uploaded_file.name)
                ext = ext.lower()
                try:
                    with tempfile.TemporaryDirectory() as tmpdir:
                        # --- ZIP ---
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
                            try:
                                with zipfile.ZipFile(kmz_path, "r") as kmz_ref:
                                    kmz_ref.extractall(tmpdir)
                                kml_files = [f for f in os.listdir(tmpdir) if f.endswith(".kml")]
                                if not kml_files:
                                    st.error(f"❌ Tidak ada .kml dalam {uploaded_file.name}")
                                    continue
                                gdf = gpd.read_file(os.path.join(tmpdir, kml_files[0]), driver="KML")
                            except zipfile.BadZipFile:
                                st.error(f"❌ {uploaded_file.name} bukan KMZ yang valid")
                                continue
                        else:
                            st.error(f"❌ Format {ext} belum didukung")
                            continue

                        # Tambahkan kolom sumber
                        gdf["source_file"] = uploaded_file.name
                        all_gdfs.append(gdf)

                        # --- Info ringkasan ---
                        st.markdown(f"### 📂 Konversi ke Shapefile")
                        geom_summary = gdf.geometry.geom_type.value_counts().to_dict()
                        for geom, count in geom_summary.items():
                            st.write(f"- {geom}: {count} fitur")
                        st.success(f"✅ {uploaded_file.name} berhasil diproses")

                        # --- Pilihan zona UTM ---
                        st.markdown("**📐 Hitung Luas (m² dan Ha)**")
                        col1, col2 = st.columns(2)
                        with col1:
                            utm_zone = st.number_input("Zona UTM", min_value=1, max_value=60, value=48)
                        with col2:
                            hemisphere = st.selectbox("Belahan", ["S", "N"], index=0)

                        if hemisphere == "N":
                            utm_crs = f"EPSG:326{utm_zone:02d}"
                        else:
                            utm_crs = f"EPSG:327{utm_zone:02d}"

                        try:
                            gdf_utm = gdf.to_crs(utm_crs)
                            gdf["Luas_m2"] = gdf_utm.area
                            gdf["Luas_Ha"] = gdf["Luas_m2"] / 10000
                            st.dataframe(gdf[["source_file", "Luas_m2", "Luas_Ha"]])
                        except Exception as e:
                            st.warning(f"⚠️ Gagal menghitung luas: {e}")

                        # --- Simpan shapefile per geometry ---
                        geom_types = {
                            "polygon": ["Polygon", "MultiPolygon"],
                            "line": ["LineString", "MultiLineString"],
                            "point": ["Point", "MultiPoint"],
                        }

                        file_zip_buffer = BytesIO()
                        with zipfile.ZipFile(file_zip_buffer, "w") as zf_file:
                            for gname, gtypes in geom_types.items():
                                gdf_sub = gdf[gdf.geometry.geom_type.isin(gtypes)]
                                if not gdf_sub.empty:
                                    shp_path = os.path.join(shpdir, f"{fname}_{gname}.shp")
                                    gdf_sub.to_file(shp_path)

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
    st.subheader("📥 Download Hasil Konversi")

    with st.expander("📦 Download Per Shapefile"):
        for shp_name, shp_zip in per_shp_zips:
            st.download_button(
                label=f"⬇️ {shp_name}.zip",
                data=shp_zip,
                file_name=f"{shp_name}.zip",
                mime="application/zip"
            )

    with st.expander("📂 Download Per File"):
        for fname, file_zip in per_file_zips:
            st.download_button(
                label=f"⬇️ {fname}.zip",
                data=file_zip,
                file_name=f"{fname}.zip",
                mime="application/zip"
            )

    if len(uploaded_files) > 1:
        with st.expander("📦 Download Semua):
            st.download_button(
                label="⬇️ Download all_files.zip",
                data=all_zip_buffer.getvalue(),
                file_name="all_files.zip",
                mime="application/zip"
            )

# ===============================
# Shapefile Referensi
# ===============================
st.subheader("📂 Shapefile Referensi")
REFERENSI_DIR = "referensi"
os.makedirs(REFERENSI_DIR, exist_ok=True)

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

# Fitur hapus shapefile referensi
if shp_files:
    file_to_delete = st.selectbox("🗑️ Hapus shapefile referensi?", ["-"] + shp_files)
    if file_to_delete != "-":
        if st.button("Hapus File"):
            basename = os.path.splitext(file_to_delete)[0]
            for f in os.listdir(REFERENSI_DIR):
                if f.startswith(basename):
                    os.remove(os.path.join(REFERENSI_DIR, f))
            st.warning(f"❌ {file_to_delete} berhasil dihapus. Silakan refresh halaman.")

    if st.button("🗑️ Hapus Semua Shapefile Referensi"):
        for f in os.listdir(REFERENSI_DIR):
            os.remove(os.path.join(REFERENSI_DIR, f))
        st.warning("❌ Semua shapefile referensi berhasil dihapus. Silakan refresh halaman.")

# Load referensi terpilih
gdf_refs = []
for ref_file in selected_refs:
    ref_path = os.path.join(REFERENSI_DIR, ref_file)
    if os.path.exists(ref_path):
        gdf_refs.append(gpd.read_file(ref_path))

# ===============================
# Hitung overlap
# ===============================
if all_gdfs and gdf_refs:
    st.markdown("### 📐 Luas Overlap dengan Referensi")
    gdf_proyek = gpd.GeoDataFrame(pd.concat(all_gdfs, ignore_index=True), crs=all_gdfs[0].crs)
    for i, gdf_ref in enumerate(gdf_refs):
        try:
            if gdf_ref.crs != gdf_proyek.crs:
                gdf_ref = gdf_ref.to_crs(gdf_proyek.crs)
            overlap = gpd.overlay(gdf_proyek, gdf_ref, how="intersection")
            if not overlap.empty:
                utm_zone = 48
                hemisphere = "S"
                utm_crs = f"EPSG:{326 if hemisphere=='N' else 327}{utm_zone:02d}"
                overlap_utm = overlap.to_crs(utm_crs)
                overlap["Luas_m2"] = overlap_utm.area
                overlap["Luas_Ha"] = overlap["Luas_m2"] / 10000
                st.write(f"Referensi {i+1}: {selected_refs[i]}")
                st.dataframe(overlap[["Luas_m2", "Luas_Ha"]])
            else:
                st.info(f"Tidak ada overlap dengan {selected_refs[i]}")
        except Exception as e:
            st.warning(f"⚠️ Gagal menghitung overlap dengan {selected_refs[i]}: {e}")

# ===============================
# Peta Interaktif
# ===============================
if all_gdfs:
    gdf_proyek = gpd.GeoDataFrame(pd.concat(all_gdfs, ignore_index=True), crs=all_gdfs[0].crs)
    bounds = gdf_proyek.to_crs(epsg=4326).total_bounds  # [minx, miny, maxx, maxy]
    center = [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2]

    st.subheader("🗺️ Peta Interaktif")
    basemap_choice = st.selectbox(
        "Pilih basemap",
        ["OpenStreetMap", "CartoDB Positron", "CartoDB DarkMatter", "Esri Satellite"]
    )

    m = folium.Map(location=center, zoom_start=8)

    if basemap_choice == "CartoDB Positron":
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
    else:
        folium.TileLayer("OpenStreetMap").add_to(m)

    # Proyek
    folium.GeoJson(
        gdf_proyek.to_crs(epsg=4326),
        name="Proyek",
        style_function=lambda x: {"color": "purple", "fillOpacity": 0.5},
    ).add_to(m)

    # Referensi
    for i, gdf_ref in enumerate(gdf_refs):
        folium.GeoJson(
            gdf_ref.to_crs(epsg=4326),
            name=f"Referensi {i+1}",
            style_function=lambda x: {"color": "gray", "fillOpacity": 0},
        ).add_to(m)

    # Zoom ke extent proyek
    m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])

    folium.LayerControl().add_to(m)
    st_folium(m, width=900, height=600)

