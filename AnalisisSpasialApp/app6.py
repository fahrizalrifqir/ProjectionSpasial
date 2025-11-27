import streamlit as st
from PyPDF2 import PdfReader, PdfWriter
import fitz  # PyMuPDF
from PIL import Image
import io, os

st.set_page_config(page_title="PDF Split + Preview", page_icon="📄", layout="centered")

st.title("📄 PDF Split + Preview Halaman")
st.write("Unggah PDF untuk melihat preview dan melakukan split.")
st.code("Contoh rentang: 1-1,2-12", language="text")

# ===================== UPLOAD FILE ======================
uploaded_file = st.file_uploader("📤 Upload file PDF", type=["pdf"])

# Reset jika user klik ❌
if uploaded_file is None and "last_uploaded" in st.session_state:
    st.session_state.clear()

if uploaded_file:
    # Baca PDF
    pdf_bytes = uploaded_file.read()
    pdf_reader = PdfReader(io.BytesIO(pdf_bytes))
    total_pages = len(pdf_reader.pages)

    pdf_name = os.path.splitext(uploaded_file.name)[0]

    st.success(f"File terbaca: **{uploaded_file.name}** dengan {total_pages} halaman.")

    # ======================================================
    # 1️⃣ PREVIEW HALAMAN PDF
    # ======================================================
    st.subheader("👁 Preview Halaman PDF")

    pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    # Fix slider jika halaman cuma 1 (streamlit tidak boleh min=max)
    if total_pages == 1:
        page_num = st.slider(
            "Pilih halaman:",
            1, 2, 1,
            help="PDF ini hanya memiliki 1 halaman."
        )
        page_num = 1  # force tetap halaman 1
    else:
        page_num = st.slider(
            "Pilih halaman:",
            1, total_pages, 1
        )

    try:
        page = pdf_doc[page_num - 1]
        pix = page.get_pixmap(matrix=fitz.Matrix(0.7, 0.7))
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        st.image(img, caption=f"Halaman {page_num}", use_column_width=True)

    except Exception as e:
        st.error(f"Gagal menampilkan preview: {e}")

    st.markdown("---")

    # ======================================================
    # 2️⃣ FITUR SPLIT TETAP ADA & TIDAK DIHILANGKAN
    # ======================================================
    st.subheader("✂️ Split PDF Berdasarkan Rentang Halaman")

    if "last_uploaded" not in st.session_state or st.session_state["last_uploaded"] != uploaded_file.name:
        st.session_state["split_results"] = []
        st.session_state["last_uploaded"] = uploaded_file.name

    default_range = f"1-1,2-{total_pages}" if total_pages > 1 else "1-1"

    rentang_input = st.text_input(
        "Masukkan rentang halaman:",
        value=default_range
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

            for i, (start, end) in enumerate(splits):
                writer = PdfWriter()

                for p in range(start - 1, end):
                    if 0 <= p < total_pages:
                        writer.add_page(pdf_reader.pages[p])

                buf = io.BytesIO()
                writer.write(buf)
                buf.seek(0)

                if i == 0:
                    file_name = f"{pdf_name}.pdf"
                else:
                    file_name = f"RPD_{pdf_name}_hal_{start}_sampai_{end}.pdf"

                output_files.append((file_name, buf))

            st.session_state["split_results"] = output_files
            st.success("✅ Split berhasil! Silakan unduh di bawah ini:")

        except Exception as e:
            st.error(f"Terjadi kesalahan saat split: {e}")

    # ===================== DOWNLOAD HASIL SPLIT ======================
    if st.session_state.get("split_results"):
        for name, buf in st.session_state["split_results"]:
            st.download_button(
                f"⬇️ Unduh {name}",
                data=buf,
                file_name=name,
                mime="application/pdf",
                key=name
            )

else:
    st.info("Silakan upload PDF untuk memulai.")
