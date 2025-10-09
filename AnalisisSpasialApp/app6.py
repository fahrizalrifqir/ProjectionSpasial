import streamlit as st
import geopandas as gpd
import pandas as pd
import io, os, zipfile, shutil, re
from shapely.geometry import Point, Polygon
import folium
from streamlit_folium import st_folium
import pdfplumber
import matplotlib.pyplot as plt
import contextily as ctx
import matplotlib.patches as mpatches
import matplotlib.lines as mlines
from folium.plugins import Fullscreen
import xyzservices.providers as xyz

# ======================
# === Konfigurasi App ===
# ======================
st.set_page_config(page_title="PKKPR → SHP & Overlay (Mode UTM)", layout="wide")
st.title("PKKPR → Shapefile Converter & Overlay Tapak Proyek (Mode UTM)")
# Peringatan diubah, mengindikasikan asumsi 53S
st.warning("Mode ini secara eksplisit mengasumsikan koordinat input adalah **UTM WGS 84 Zona 53S** (EPSG:32753), yang paling sering memperbaiki masalah plot 'di tengah laut' untuk data Indonesia.")

# ======================
# === Fungsi Helper ===
# ======================
def get_utm_info(lon, lat):
    # Dapatkan EPSG UTM berdasarkan Lintang/Bujur (digunakan setelah konversi ke 4326)
    zone = int((lon + 180) / 6) + 1
    if lat >= 0:
        epsg = 32600 + zone
        zone_label = f"{zone}N"
    else:
        epsg = 32700 + zone
        zone_label = f"{zone}S"
    return epsg, zone_label


def save_shapefile(gdf, folder_name, zip_name):
    if os.path.exists(folder_name):
        shutil.rmtree(folder_name)
    os.makedirs(folder_name, exist_ok=True)
    shp_path = os.path.join(folder_name, "data.shp")
    # Pastikan GeoDataFrame dalam 4326 untuk kompatibilitas SHP standar
    gdf.to_file(shp_path)
    zip_path = f"{zip_name}.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for file in os.listdir(folder_name):
            zf.write(os.path.join(folder_name, file), arcname=file)
    return zip_path


def parse_luas_from_text(text):
    """Cari dan ubah nilai luas dengan format Indonesia"""
    text_clean = re.sub(r"\s+", " ", (text or "").lower())
    m = re.search(r"luas\s*tanah\s*yang\s*(disetujui|dimohon)\s*[:\-]?\s*([\d\.,]+)", text_clean)
    if not m:
        return None, None
    label = m.group(1)
    num_str = m.group(2)

    num_str = re.sub(r"[^\d\.,]", "", num_str)
    if "." in num_str and "," in num_str:
        num_str = num_str.replace(".", "").replace(",", ".")
    elif "," in num_str and "." not in num_str:
        num_str = num_str.replace(",", ".")
    elif num_str.count(".") > 1:
        parts = num_str.split(".")
        num_str = "".join(parts[:-1]) + "." + parts[-1]

    try:
        return float(num_str), label
    except:
        return None, label


def format_angka_id(value):
    """Format angka gaya Indonesia"""
    try:
        return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return str(value)

# ======================
# === Upload PKKPR ===
# ======================
col1, col2 = st.columns([0.7, 0.3])
with col1:
    uploaded_pkkpr = st.file_uploader("📂 Upload PKKPR (PDF koordinat UTM atau Shapefile ZIP)", type=["pdf", "zip"])

coords, gdf_points, gdf_polygon = [], None, None
luas_pkkpr_doc, luas_pkkpr_doc_label = None, None

# --- KONFIGURASI UTM KHUSUS UNTUK HALTIM ---
# ***PERUBAHAN KRITIS: Mengubah 53N (32653) menjadi 53S (32753)***
UTM_CRS_INPUT = "EPSG:32753"  # WGS 84 / UTM Zone 53S

if uploaded_pkkpr:
    if uploaded_pkkpr.name.endswith(".pdf"):
        coords_mentah = [] 
        full_text = ""
        
        with pdfplumber.open(uploaded_pkkpr) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                full_text += "\n" + text

                # 1. Pembacaan dari teks biasa
                for line in text.split("\n"):
                    mline = re.findall(r"[-+]?\d+\.\d+", line)
                    if len(mline) >= 2:
                        try:
                            # mline[0] = Lintang (Y), mline[1] = Bujur (X)
                            y_coord, x_coord = float(mline[0]), float(mline[1])
                            # HANYA tambahkan jika angka-angkanya besar (khas UTM)
                            if y_coord > 1000 and x_coord < 1000000:
                                # ***PENTING: Simpan sebagai (X, Y) = (Bujur, Lintang)***
                                coords_mentah.append((x_coord, y_coord)) 
                        except:
                            pass

                # 2. Pembacaan dari tabel
                tables = page.extract_tables()
                if tables:
                    for tb in tables:
                        for row in tb:
                            if not row:
                                continue
                            row_join = " ".join([str(x) for x in row if x])
                            nums = re.findall(r"[-+]?\d+\.\d+", row_join)
                            if len(nums) >= 2:
                                try:
                                    # nums[0] = Lintang (Y), nums[1] = Bujur (X)
                                    y_coord, x_coord = float(nums[0]), float(nums[1])
                                    if y_coord > 1000 and x_coord < 1000000:
                                        # ***PENTING: Simpan sebagai (X, Y) = (Bujur, Lintang)***
                                        coords_mentah.append((x_coord, y_coord)) 
                                except:
                                    pass

        luas_pkkpr_doc, luas_pkkpr_doc_label = parse_luas_from_text(full_text)

        # Hapus duplikasi dan pastikan urutan (X, Y)
        coords_mentah = list(dict.fromkeys(coords_mentah))
        coords_mentah_xy = [(x, y) for x, y in coords_mentah]
        
        if coords_mentah_xy:
            # Tutup poligon jika titik awal tidak sama dengan titik akhir
            if coords_mentah_xy[0] != coords_mentah_xy[-1]:
                coords_mentah_xy.append(coords_mentah_xy[0])

            # Buat GeoDataFrame Titik dengan CRS UTM (EPSG:32753)
            gdf_points_utm = gpd.GeoDataFrame(
                pd.DataFrame(coords_mentah_xy, columns=["Easting", "Northing"]),
                geometry=[Point(xy) for xy in coords_mentah_xy],
                crs=UTM_CRS_INPUT
            )
            
            # Konversi GeoDataFrame Titik ke Lintang/Bujur (4326) untuk plotting
            gdf_points = gdf_points_utm.to_crs(epsg=4326)

            # Buat Polygon dari titik-titik yang sudah dikonversi ke 4326
            polygon_wgs84 = Polygon([p.coords[0] for p in gdf_points.geometry])
            gdf_polygon = gpd.GeoDataFrame(geometry=[polygon_wgs84], crs="EPSG:4326")
            
            with col2:
                label_display = luas_pkkpr_doc_label or "disetujui (UTM)"
                count_display = len(coords_mentah_xy) if coords_mentah_xy else 0
                st.markdown(f"<p style='color: green; font-weight: bold; padding-top: 3.5rem;'>✅ {count_display} titik ({label_display}) dikonversi dari {UTM_CRS_INPUT}</p>", unsafe_allow_html=True)
        else:
            with col2:
                st.markdown("<p style='color: red; font-weight: bold; padding-top: 3.5rem;'>❌ Tidak ada koordinat UTM yang ditemukan.</p>", unsafe_allow_html=True)


    elif uploaded_pkkpr.name.endswith(".zip"):
        # Logika pembacaan Shapefile (ZIP) tetap sama
        if os.path.exists("pkkpr_shp"):
            shutil.rmtree("pkkpr_shp")
        with zipfile.ZipFile(uploaded_pkkpr, "r") as z:
            z.extractall("pkkpr_shp")
        gdf_polygon = gpd.read_file("pkkpr_shp")
        if gdf_polygon.crs is None or not gdf_polygon.crs.to_epsg() == 4326:
            gdf_polygon = gdf_polygon.to_crs(epsg=4326)
        with col2:
            st.markdown("<p style='color: green; font-weight: bold; padding-top: 3.5rem;'>✅ Shapefile dibaca</p>", unsafe_allow_html=True)

# === Ekspor SHP PKKPR ===
if gdf_polygon is not None:
    # Simpan sebagai 4326 (standar web mapping)
    zip_pkkpr_only = save_shapefile(gdf_polygon.to_crs(epsg=4326), "out_pkkpr_only", "PKKPR_Hasil_Konversi_UTM")
    with open(zip_pkkpr_only, "rb") as f:
        st.download_button("⬇️ Download SHP PKKPR (ZIP)", f, file_name="PKKPR_Hasil_Konversi_UTM.zip", mime="application/zip")

# ======================
# === Analisis PKKPR Sendiri ===
# ======================
if gdf_polygon is not None:
    # Karena sudah di konversi ke 4326, kita bisa mendapatkan centroid
    centroid = gdf_polygon.geometry.centroid.iloc[0]
    utm_epsg, utm_zone = get_utm_info(centroid.x, centroid.y)
    
    # Hitung ulang luas di proyeksi UTM yang benar berdasarkan centroid 
    gdf_polygon_utm_calc = gdf_polygon.to_crs(epsg=utm_epsg)
    luas_pkkpr_hitung = gdf_polygon_utm_calc.area.sum()
    gdf_polygon_3857 = gdf_polygon.to_crs(epsg=3857)
    luas_pkkpr_mercator = gdf_polygon_3857.area.sum()

    luas_doc_str = f"{format_angka_id(luas_pkkpr_doc)} Ha ({luas_pkkpr_doc_label})" if luas_pkkpr_doc else "-"
    st.info(f"""
    **Analisis Proyeksi Awal:**
    - Proyeksi Input yang Digunakan: **{UTM_CRS_INPUT} (UTM 53S)**
    
    **Analisis Luas:**
    - Luas PKKPR (dokumen): **{luas_doc_str}** (Luas yang dimohon adalah **20.763 Ha** )
    - Luas PKKPR (UTM Zona {utm_zone} - hasil hitungan): {format_angka_id(luas_pkkpr_hitung)} m²
    - Luas PKKPR (proyeksi WGS 84 / Mercator): {format_angka_id(luas_pkkpr_mercator)} m²
    """)
    st.markdown("---")

# ================================
# === Upload Tapak Proyek (SHP) ===
# ================================
col1, col2 = st.columns([0.7, 0.3])
with col1:
    uploaded_tapak = st.file_uploader("📂 Upload Shapefile Tapak Proyek (ZIP)", type=["zip"])

if uploaded_tapak:
    try:
        if os.path.exists("tapak_shp"):
            shutil.rmtree("tapak_shp")
        with zipfile.ZipFile(uploaded_tapak, "r") as z:
            z.extractall("tapak_shp")
        gdf_tapak = gpd.read_file("tapak_shp")
        if gdf_tapak.crs is None or not gdf_tapak.crs.to_epsg() == 4326:
            gdf_tapak = gdf_tapak.to_crs(epsg=4326)
        with col2:
            st.markdown("<p style='color: green; font-weight: bold; padding-top: 3.5rem;'>✅</p>", unsafe_allow_html=True)
    except Exception as e:
        gdf_tapak = None
        with col2:
            st.markdown("<p style='color: red; font-weight: bold; padding-top: 3.5rem;'>❌ Gagal dibaca</p>", unsafe_allow_html=True)
        st.error(f"Error: {e}")
else:
    gdf_tapak = None

# ======================
# === Analisis Overlay ===
# ======================
if gdf_polygon is not None and gdf_tapak is not None:
    st.subheader("📊 Analisis Overlay PKKPR & Tapak Proyek")
    
    # Gunakan EPSG UTM yang terdeteksi dari centroid untuk perhitungan yang akurat
    centroid = gdf_polygon.geometry.centroid.iloc[0]
    utm_epsg, utm_zone = get_utm_info(centroid.x, centroid.y)
    
    gdf_tapak_utm = gdf_tapak.to_crs(epsg=utm_epsg)
    gdf_polygon_utm = gdf_polygon.to_crs(epsg=utm_epsg)
    
    luas_tapak = gdf_tapak_utm.area.sum()
    luas_pkkpr_hitung = gdf_polygon_utm.area.sum()
    luas_overlap = gdf_tapak_utm.overlay(gdf_polygon_utm, how="intersection").area.sum()
    luas_outside = luas_tapak - luas_overlap
    
    luas_doc_str = f"{format_angka_id(luas_pkkpr_doc)} Ha ({luas_pkkpr_doc_label})" if luas_pkkpr_doc else "-"
    st.info(f"""
    **Analisis Luas Tapak Proyek (Dalam Proyeksi UTM Zona {utm_zone}) :**
    - Total Luas Tapak Proyek: {format_angka_id(luas_tapak)} m²
    - Luas PKKPR (dokumen): {luas_doc_str}
    - Luas PKKPR (UTM {utm_zone}): {format_angka_id(luas_pkkpr_hitung)} m²
    - Luas Tapak Proyek UTM di dalam PKKPR: **{format_angka_id(luas_overlap)} m²**
    - Luas Tapak Proyek UTM di luar PKKPR: **{format_angka_id(luas_outside)} m²**
    """)
    st.markdown("---")

# ======================
# === Preview Interaktif ===
# ======================
if gdf_polygon is not None:
    st.subheader("🌍 Preview Peta Interaktif")

    centroid = gdf_polygon.geometry.centroid.iloc[0]
    m = folium.Map(location=[centroid.y, centroid.x], zoom_start=17)
    Fullscreen(position="bottomleft").add_to(m)

    folium.TileLayer(
        tiles="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        attr="© OpenStreetMap contributors",
        name="OpenStreetMap"
    ).add_to(m)

    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles © Esri",
        name="Esri World Imagery"
    ).add_to(m)

    folium.TileLayer(
        tiles="https://cartodb-basemaps-a.global.ssl.fastly.net/light_all/{z}/{x}/{y}.png",
        attr="© CartoDB",
        name="CartoDB Positron"
    ).add_to(m)

    folium.TileLayer(
        tiles="https://stamen-tiles.a.ssl.fastly.net/terrain/{z}/{x}/{y}.png",
        attr="Map tiles © Stamen Design, CC BY 3.0 — Map data © OpenStreetMap contributors",
        name="Stamen Terrain"
    ).add_to(m)

    folium.GeoJson(
        gdf_polygon, # Sudah dalam 4326
        name="PKKPR",
        style_function=lambda x: {"color": "yellow", "weight": 2, "fillOpacity": 0}
    ).add_to(m)

    if 'gdf_tapak' in locals() and gdf_tapak is not None:
        folium.GeoJson(
            gdf_tapak, # Sudah dalam 4326
            name="Tapak Proyek",
            style_function=lambda x: {"color": "red", "weight": 1, "fillColor": "red", "fillOpacity": 0.4}
        ).add_to(m)

    if gdf_points is not None:
        for i, row in gdf_points.iterrows():
            folium.CircleMarker(
                location=[row.geometry.y, row.geometry.x],
                radius=5,
                color="black",
                fill=True,
                fill_color="orange",
                fill_opacity=1,
                popup=f"Titik {i+1}"
            ).add_to(m)

    folium.LayerControl(collapsed=True, position="topright").add_to(m)
    st_folium(m, width=900, height=600)
    st.markdown("---")

# ======================
# === Layout Peta PNG ===
# ======================
if gdf_polygon is not None:
    st.subheader("🖼️ Layout Peta (PNG) - Auto Size")
    out_png = "layout_peta_utm.png"
    gdf_poly_3857 = gdf_polygon.to_crs(epsg=3857)
    xmin, ymin, xmax, ymax = gdf_poly_3857.total_bounds
    width = xmax - xmin
    height = ymax - ymin
    figsize = (14, 10) if width > height else (10, 14)

    fig, ax = plt.subplots(figsize=figsize, dpi=150)
    gdf_poly_3857.plot(ax=ax, facecolor="none", edgecolor="yellow", linewidth=2)

    if 'gdf_tapak' in locals() and gdf_tapak is not None:
        gdf_tapak_3857 = gdf_tapak.to_crs(epsg=3857)
        gdf_tapak_3857.plot(ax=ax, facecolor="red", alpha=0.4, edgecolor="red")

    if gdf_points is not None:
        gdf_points_3857 = gdf_points.to_crs(epsg=3857)
        gdf_points_3857.plot(ax=ax, color="orange", edgecolor="black", markersize=25)

    ctx.add_basemap(ax, crs=3857, source=ctx.providers.Esri.WorldImagery, attribution=False)
    dx, dy = width * 0.05, height * 0.05
    ax.set_xlim(xmin - dx, xmax + dx)
    ax.set_ylim(ymin - dy, ymax + dy)

    legend_elements = [
        mlines.Line2D([], [], color="orange", marker="o", markeredgecolor="black", linestyle="None", markersize=5, label="PKKPR (Titik)"),
        mpatches.Patch(facecolor="none", edgecolor="yellow", linewidth=1.5, label="PKKPR (Polygon)"),
        mpatches.Patch(facecolor="red", edgecolor="red", alpha=0.4, label="Tapak Proyek"),
    ]
    leg = ax.legend(handles=legend_elements, title="Legenda", loc="upper right",
                    bbox_to_anchor=(0.98, 0.98), fontsize=8, title_fontsize=9,
                    markerscale=0.8, labelspacing=0.3, frameon=True, facecolor="white")
    leg.get_frame().set_alpha(0.7)
    ax.set_title("Peta Kesesuaian Tapak Proyek dengan PKKPR (Asumsi UTM 53S)", fontsize=14, weight="bold")
    ax.set_axis_off()
    plt.savefig(out_png, dpi=300, bbox_inches="tight")

    with open(out_png, "rb") as f:
        st.download_button("⬇️ Download Layout Peta (PNG, Auto)", f, "layout_peta_utm.png", mime="image/png")

    st.pyplot(fig)
