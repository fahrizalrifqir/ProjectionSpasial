import streamlit as st
import geopandas as gpd
import matplotlib.pyplot as plt
import contextily as ctx
import io
from streamlit_folium import st_folium
import folium

st.set_page_config(layout="wide")
st.title("🗺️ Analisis Spasial Interaktif + Download Peta")

# Contoh data (ganti dengan load shapefile kamu)
gdf = gpd.read_file(gpd.datasets.get_path("naturalearth_lowres"))
gdf = gdf.to_crs(epsg=3857)

# ========================
# 1. Peta Interaktif (Folium)
# ========================
st.subheader("🌍 Peta Interaktif (bisa digeser/zoom)")
m = folium.Map(location=[0, 120], zoom_start=4, tiles="Esri.WorldImagery")

folium.GeoJson(
    gdf,
    name="Data",
    style_function=lambda x: {"color": "purple", "fillOpacity": 0.4}
).add_to(m)

folium.LayerControl().add_to(m)
st_folium(m, width=900, height=600)

# ========================
# 2. Peta Statis (Matplotlib)
# ========================
st.subheader("🖼️ Peta Statis untuk Download")

fig, ax = plt.subplots(figsize=(8, 8))
gdf.plot(ax=ax, color="purple", alpha=0.5)
ctx.add_basemap(ax, crs=gdf.crs, source=ctx.providers.Esri.WorldImagery)
ax.set_axis_off()
st.pyplot(fig)

# ========================
# 3. Tombol Download
# ========================
# Simpan ke buffer
img_buffer = io.BytesIO()
fig.savefig(img_buffer, format="png", dpi=300, bbox_inches="tight")
img_buffer.seek(0)

# Download sebagai PNG
st.download_button(
    label="📥 Download Peta (PNG)",
    data=img_buffer,
    file_name="peta.png",
    mime="image/png"
)

# Download sebagai JPEG
img_buffer_jpg = io.BytesIO()
fig.savefig(img_buffer_jpg, format="jpeg", dpi=300, bbox_inches="tight")
img_buffer_jpg.seek(0)
st.download_button(
    label="📥 Download Peta (JPEG)",
    data=img_buffer_jpg,
    file_name="peta.jpeg",
    mime="image/jpeg"
)

# Download sebagai PDF
pdf_buffer = io.BytesIO()
fig.savefig(pdf_buffer, format="pdf", dpi=300, bbox_inches="tight")
pdf_buffer.seek(0)
st.download_button(
    label="📥 Download Peta (PDF)",
    data=pdf_buffer,
    file_name="peta.pdf",
    mime="application/pdf"
)
