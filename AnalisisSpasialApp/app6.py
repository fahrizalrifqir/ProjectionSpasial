import streamlit as st
from PyPDF2 import PdfReader, PdfWriter
import fitz  # PyMuPDF
import io, os

st.set_page_config(page_title="PDF Splitter (Fleksibel)", page_icon="📄", layout="centered")

st.title("📄 Split PDF Berdasarkan Rentang Halaman")
st.write("Unggah PDF dan tentukan rentang halaman yang ingin dipisahkan, misalnya:")
st.code("1-1,2-12", language="text")

# ====== UPLOAD FILE ======
uploaded_file = st.file_uploader("📤 Upload file PDF", type=["pdf"])

# ====== DETEKSI FILE DIHAPUS ======
if uploaded_file is None and "last_uploaded" in st.session_state:
    st.session_state.clear()

# ====== JIKA FILE ADA ======
if uploaded_file is not None:
    original_name = os.path.splitext(uploaded_file.name)[0]

    # Reset hasil lama jika file baru diunggah
    if "last_uploaded" not in st.session_state or st.session_state["last_uploaded"] != uploaded_file.name:
        st.session_state["split_results"] = []
        st.session_state["last_uploaded"] = uploaded_file.name

    # PyPDF2 membaca PDF
    reader = PdfReader(uploaded_file)
    total_pages = len(reader.pages)
    st.success(f"File terbaca: **{uploaded_file.name}** dengan {total_pages} halaman.")

    # ===========================================================
    #                🔍 PREVIEW MODE SELECTOR
    # ===========================================================
    st.subheader("🔍 Preview PDF")
    mode = st.radio(
        "Pilih mode preview:",
        ["Thumbnail Grid", "Single Page Slider"],
        horizontal=True
    )

    pdf_bytes = uploaded_file.getvalue()
    pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    # ===========================================================
    #                 🖼️ MODE 1: THUMBNAIL GRID
    # ===========================================================
    if mode == "Thumbnail Grid":
        cols = st.columns(3)
        for i in range(len(pdf_doc)):
            try:
                pix = pdf_doc[i].get_pixmap(matrix=fitz.Matrix(0.4, 0.4))
                img_bytes = pix.tobytes("png")

                with cols[i % 3]:
                    st.image(img_bytes, caption=f"Halaman {i+1}")
            except:
                st.warning(f"Gagal memuat halaman {i+1}")

    # ===========================================================
    #                📄 MODE 2: SLIDER PER HALAMAN
    # ===========================================================
    if mode == "Single Page Slider":
        page_num = st.slider("Pilih halaman:", 1, total_pages, 1)

        page = pdf_doc[page_num - 1]
        pix = page.get_pixmap(matrix=fitz.Matrix(1.2, 1.2))  # lebih besar
        img_bytes = pix.tobytes("png")

        st.image(img_bytes, caption=f"Halaman {page_num}", use_container_width=True)

    # ===========================================================

    rentang_input = st.text_input(
        "Masukkan rentang halaman (contoh: 1-1,2-12)",
        value=f"1-1,2-{total_pages}"
    )

    if st.button("🔪 Split Sekarang"):
        try:
            splits = []
            for r in rentang_input.split(","):
                if "-" in r:
                    start, end = map(int, r.split("-"))
                else:
                    start = end = int(r)
                splits.append((start, end))

            output_files = []
            for idx, (start, end) in enumerate(splits):
                writer = PdfWriter()
                for i in range(start - 1, end):
                    if i < total_pages:
                        writer.add_page(reader.pages[i])

                buffer = io.BytesIO()
                writer.write(buffer)
                buffer.seek(0)

                if idx == 0:
                    output_name = f"{original_name}.pdf"
                else:
                    output_name = f"RPD_{original_name}_hal_{start}_sampai_{end}.pdf"

                output_files.append((output_name, buffer))

            st.session_state["split_results"] = output_files
            st.success("✅ Split berhasil! Unduh hasil di bawah ini:")

        except Exception as e:
            st.error(f"Terjadi kesalahan: {e}")

    # ====== DOWNLOAD HASIL ======
    if st.session_state.get("split_results"):
        for name, buf in st.session_state["split_results"]:
            st.download_button(
                label=f"⬇️ Unduh {name}",
                data=buf,
                file_name=name,
                mime="application/pdf",
                key=name
            )

else:
    st.info("Unggah file PDF untuk memulai proses pemisahan.")
