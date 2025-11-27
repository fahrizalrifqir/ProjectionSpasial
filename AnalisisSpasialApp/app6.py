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

    # ----------------------------------------------------
    # 1️⃣ Jika total_pages = 1 → buat slider aman (1 sampai 2)
    #    Streamlit TIDAK BOLEH punya slider min=max
    # ----------------------------------------------------
    if total_pages == 1:
        st.warning("PDF hanya memiliki 1 halaman. Slider tetap ditampilkan.")

        page_num = st.slider(
            "Pilih halaman:",
            min_value=1,
            max_value=2,     # Harus > min_value
            value=1,
            step=1,
            help="PDF ini hanya memiliki 1 halaman."
        )

        # Halaman harus tetap 1
        page_num = 1

    # ----------------------------------------------------
    # 2️⃣ Jika halaman > 1 → slider normal
    # ----------------------------------------------------
    else:
        page_num = st.slider(
            "Pilih halaman:",
            min_value=1,
            max_value=total_pages,
            value=1,
            step=1
        )

    # ----------------------------------------------------
    # 3️⃣ Render halaman
    # ----------------------------------------------------
    try:
        page = pdf_doc[page_num - 1]
        pix = page.get_pixmap(matrix=fitz.Matrix(0.8, 0.8))
        img = Image.open(io.BytesIO(pix.tobytes("png")))

        st.image(img, caption=f"Halaman {page_num}", use_column_width=True)

        # Download tombol
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        st.download_button(
            label=f"Download halaman {page_num}",
            data=buf.getvalue(),
            file_name=f"halaman_{page_num}.png",
            mime="image/png"
        )

    except Exception as e:
        st.error(f"Terjadi error saat render halaman: {e}")
