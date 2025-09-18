import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Analisis Spasial Interaktif", layout="wide")

st.title("🌍 Analisis Spasial Interaktif")

# Upload shapefile
tapak_file = st.file_uploader("Upload Shapefile Tapak (ZIP)", type=["zip"])
ref_file = st.file_uploader("Upload Shapefile Referensi (ZIP)", type=["zip"])

# Pilihan basemap
basemap_choice = st.selectbox(
    "Pilih Basemap",
    ["OpenStreetMap", "ESRI Satelit"]
)

if tapak_file and ref_file:
    # Baca shapefile
    tapak = gpd.read_file(f"zip://{tapak_file.name}")
    referensi = gpd.read_file(f"zip://{ref_file.name}")

    # Overlay
    overlay = gpd.overlay(tapak, referensi, how="intersection")

    # Titik tengah
    center = [tapak.geometry.centroid.y.mean(), tapak.geometry.centroid.x.mean()]

    # Peta folium
    m = folium.Map(
        location=center,
        zoom_start=12,
        tiles="OpenStreetMap" if basemap_choice=="OpenStreetMap" else None
    )

    if basemap_choice == "ESRI Satelit":
        folium.TileLayer("Esri.WorldImagery").add_to(m)

    folium.GeoJson(tapak, name="Tapak", style_function=lambda x: {"color":"purple"}).add_to(m)
    folium.GeoJson(referensi, name="Referensi", style_function=lambda x: {"color":"black"}).add_to(m)
    if not overlay.empty:
        folium.GeoJson(overlay, name="Overlay", style_function=lambda x: {"color":"red"}).add_to(m)

    folium.LayerControl().add_to(m)

    st.subheader("🗺️ Peta Interaktif")
    st_folium(m, width=900, height=600)
