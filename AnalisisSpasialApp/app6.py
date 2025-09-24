import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import os
import zipfile
import tempfile
from io import BytesIO
import pandas as pd
import subprocess

st.set_page_config(page_title="Analisis Spasial Interaktif", layout="wide")
st.title("🌍 Analisis Spasial Interaktif")

# ===============================
# Upload Shapefile/KML/KMZ/DWG
# ===============================
st.subheader("📂 Upload Shapefile (ZIP), KML, KMZ, atau DWG")

uploaded_files = st.file_uploader(
    "Upload file .zip (shapefile), .kml, .kmz, atau .dwg (bisa lebih dari 1)",
    type=["zip", "kml", "kmz", "dwg"],
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
                        gdf = None

                        # --- SHAPEFILE ZIP ---
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

                        # --- DWG ---
                        elif ext == ".dwg":
                            dwg_path = os.path.join(tmpdir, uploaded_file.name)
                            with open(dwg_path, "wb") as f:
                                f.write(uploaded_file.read())

                            shp_path = os.path.join(tmpdir, f"{fname}.shp")
                            try:
                                subprocess.run([
                                    "ogr2ogr", "-f", "ESRI Shapefile", shp_path, dwg_path
                                ], check=True)

                                gdf = gpd.read_file(shp_path)
                            except Exception as e:
                                st.error(f"❌ Gagal konversi DWG: {e}")
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
        with st.expander("📦 Download Semua"):
            all_zip_buffer.seek(0)
            st.download_button(
                label="⬇️ Download all_files.zip",
                data=all_zip_buffer.getvalue(),
                file_name="all_files.zip",
                mime="application/zip"
            )
