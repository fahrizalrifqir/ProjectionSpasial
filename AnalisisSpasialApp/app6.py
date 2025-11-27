import streamlit as st
import fitz  # PyMuPDF
from PIL import Image
import io

st.title("📄 PDF Slide Viewer – Multi Halaman")

uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])

if uploaded_file:
    # Load PDF
    pdf_bytes = uploaded_file.read()
    pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    total_pages = pdf_doc.page_count

    st.info(f"Total halaman: **{total_pages}**")

    # ------------------------------
    # 1️⃣ Jika hanya 1 halaman → tidak pakai slider
    # ------------------------------
    if total_pages == 1:
        page_num = 1
        st.warning("PDF hanya memiliki 1 halaman (slider disembunyikan).")

    # ------------------------------
    # 2️⃣ Jika lebih dari 1 halaman → tampilkan slider
    # ------------------------------
    else:
        page_num = st.slider(
            "Pilih halaman:",
            min_value=1,
            max_value=total_pages,
            value=1,
            step=1,
        )

    # Render halaman
    page = pdf_doc[page_num - 1]
    pix = page.get_pixmap(matrix=fitz.Matrix(0.8, 0.8))

    img = Image.open(io.BytesIO(pix.tobytes("png")))

    st.image(img, caption=f"Halaman {page_num}", use_column_width=True)

    # Tombol download halamannya
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    st.download_button(
        label=f"Download halaman {page_num}",
        data=buf.getvalue(),
        file_name=f"halaman_{page_num}.png",
        mime="image/png"
    )
