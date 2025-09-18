import streamlit as st
import geopandas as gpd
import geodatasets
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pyproj import CRS

st.set_page_config(page_title="Analisis Spasial", layout="wide")

st.title("🌍 Peta Interaktif Analisis Spasial")

# --- Upload file shapefile tapak ---
uploaded_file = st.file_uploader("Upload Shapefile Tapak (.shp, .zip)", type=["shp", "zip"])

# --- Pilihan shapefile referensi (contoh naturalearth dari geodatasets) ---
use_world = st.checkbox("Gunakan Referensi Natural Earth (World Boundaries)")
if use_world:
    ref_gdf = gpd.read_file(geodatasets.get_path("naturalearth.land"))
else:
    ref_gdf = None

# --- Fungsi untuk CRS otomatis ke UTM ---
def auto_utm(gdf):
    try:
        return gdf.to_crs(gdf.estimate_utm_crs())
    except Exception:
        return gdf  # fallback

if uploaded_file is not None:
    try:
        tapak = gpd.read_file(uploaded_file)

        # Reproject ke UTM agar centroid & luas benar
        tapak_proj = auto_utm(tapak)
        if ref_gdf is not None:
            ref_proj = auto_utm(ref_gdf)
        else:
            ref_proj = None

        # Hitung centroid
        center = [
            tapak_proj.geometry.centroid.y.mean(),
            tapak_proj.geometry.centroid.x.mean()
        ]

        # Hitung luas overlay (jika ada referensi)
        luas_overlay = 0
        if ref_proj is not None:
            overlay = gpd.overlay(tapak_proj, ref_proj, how="intersection")
            luas_overlay = overlay.area.sum()

        st.write(f"**Centroid (approx):** {center}")
        st.write(f"**Luas Overlay (m²):** {luas_overlay:,.2f}")

        # Plot statis dengan legend manual
        fig, ax = plt.subplots(figsize=(8, 6))
        tapak_proj.plot(ax=ax, color="red", alpha=0.5)

        legend_items = [mpatches.Patch(color="red", alpha=0.5, label="Tapak")]

        if ref_proj is not None:
            ref_proj.plot(ax=ax, facecolor="none", edgecolor="black")
            legend_items.append(mpatches.Patch(facecolor="none", edgecolor="black", label="Referensi"))

        ax.legend(handles=legend_items)
        st.pyplot(fig)

    except Exception as e:
        st.error(f"Terjadi error saat membaca shapefile: {e}")
else:
    st.info("Silakan unggah file shapefile untuk mulai analisis.")
