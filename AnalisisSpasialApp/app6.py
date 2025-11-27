import streamlit as st
from PyPDF2 import PdfReader, PdfWriter
import fitz  # PyMuPDF
import io, os

st.set_page_config(page_title="PDF Split + Preview", page_icon="📄", layout="centered")

st.title("📄 PDF Split + Preview Halaman")
st.write("Unggah PDF, lihat preview thumbnail, dan split berdasarkan rentang halaman.")
st.code("Contoh rentang: 1-2,3-5", language="text")

# ===================== UPLOAD FILE ======================
uploaded_file = st.file_uploader("📤 Upload file PDF", type=["pdf"])

if uploaded_file is None and "last_uploaded" in st.session_state:
    st.session_state.clear()

if uploaded_file:
    pdf_bytes = uploaded_file.read()
    pdf_name = os.path.splitext(uploaded_file.name)[0]

    # ===================== BACA PDF ======================
    try:
        pdf_reader = PdfReader(io.BytesIO(pdf_bytes))
        total_pages = len(pdf_reader.pages)
        pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except:
        st.error("❌ Gagal membaca PDF. File mungkin corrupt atau terenkripsi.")
        st.stop()

    if total_pages < 1:
        st.error("PDF tidak memiliki halaman atau tidak bisa dibaca.")
        st.stop()

    st.success(f"File terbaca: **{uploaded_file.name}** dengan {total_pages} halaman.")

    # ===================== PREVIEW THUMBNAIL ======================
    st.subheader("🔹 Preview Thumbnail PDF")

    cols = st.columns(5)  # grid 5 kolom
    for i in range(total_pages):
        try:
            pix = pdf_doc[i].get_pixmap(matrix=fitz.Matrix(0.3, 0.3))  # thumbnail lebih kecil
            img_bytes = pix.tobytes("png")
            with cols[i % 5]:
                st.image(img_bytes, caption=f"{i+1}", use_column_width=True)
        except:
            st.warning(f"Gagal memuat halaman {i+1}")

    st.markdown("---")

    # ===================== INPUT RENTANG HALAMAN UNTUK SPLIT ======================
    st.subheader("✂️ Split PDF Berdasarkan Rentang Halaman")
    default_range = f"1-2,3-{total_pages}" if total_pages > 2 else "1-1"
    rentang_input = st.text_input(
        "Masukkan rentang halaman (contoh: 1-2,3-5):",
        value=default_range
    )

    if "last_uploaded" not in st.session_state or st.session_state["last_uploaded"] != uploaded_file.name:
        st.session_state["split_results"] = []
        st.session_state["last_uploaded"] = uploaded_file.name

    # ===================== SPLIT PDF ======================
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
                for p in range(start - 1, end):
                    if 0 <= p < total_pages:
                        writer.add_page(pdf_reader.pages[p])

                buf = io.BytesIO()
                writer.write(buf)
                buf.seek(0)

                if idx == 0:
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
    st.info("Silakan upload PDF untuk memulai proses preview dan split.")
