import streamlit as st
from PyPDF2 import PdfReader, PdfWriter
import fitz  # PyMuPDF
import io, os
from PIL import Image
import img2pdf

st.set_page_config(page_title="PDF Tools", page_icon="📄", layout="wide")
st.title("📄 PDF Tools: Preview + Split + Compress")
st.write("Unggah PDF, lihat preview halaman, split PDF, dan lihat perkiraan ukuran compress PDF.")

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
        st.error("❌ Gagal membaca PDF.")
        st.stop()

    st.success(f"File terbaca: **{uploaded_file.name}** dengan {total_pages} halaman.")

    # ===================== LAYOUT DUA KOLOM ======================
    col1, col2 = st.columns([1,1])

    # --------------------- KOLOM KIRI: PREVIEW ---------------------
    with col1:
        st.subheader("🔹 Preview Halaman PDF")
        page_num = st.slider("Pilih halaman:", min_value=1, max_value=total_pages, value=1, step=1)
        try:
            page = pdf_doc[page_num - 1]
            pix = page.get_pixmap(matrix=fitz.Matrix(0.8, 0.8))
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            st.image(img, caption=f"Halaman {page_num}", use_column_width=True)
        except Exception as e:
            st.error(f"Gagal menampilkan preview: {e}")

    # --------------------- KOLOM KANAN: SPLIT & COMPRESS ---------------------
    with col2:
        st.subheader("✂️ Split PDF")
        default_range = f"1-2,3-{total_pages}" if total_pages > 2 else "1-1"
        rentang_input = st.text_input("Masukkan rentang halaman (contoh: 1-2,3-5):", value=default_range)

        if "last_uploaded" not in st.session_state or st.session_state["last_uploaded"] != uploaded_file.name:
            st.session_state["split_results"] = []
            st.session_state["last_uploaded"] = uploaded_file.name

        # SPLIT PDF
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

                    file_name = f"{pdf_name}.pdf" if idx==0 else f"RPD_{pdf_name}_hal_{start}_sampai_{end}.pdf"
                    output_files.append((file_name, buf))

                st.session_state["split_results"] = output_files
                st.success("✅ Split berhasil!")
            except Exception as e:
                st.error(f"Error split: {e}")

        # Download hasil split
        if st.session_state.get("split_results"):
            for name, buf in st.session_state["split_results"]:
                st.download_button(f"⬇️ Unduh {name}", data=buf, file_name=name, mime="application/pdf", key=name)

        st.markdown("---")
        st.subheader("🗜 Compress PDF (perkiraan ukuran file)")

        # ===================== PRE-COMPRESS SIMULASI ======================
        quality_map = {"Rendah":0.3, "Sedang":0.5, "Tinggi":0.8}
        compressed_files = {}
        for q, scale in quality_map.items():
            images = []
            for page in pdf_doc:
                pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale))
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='PNG')
                images.append(img_byte_arr.getvalue())
            # Buat PDF sementara di memory
            pdf_buffer = io.BytesIO()
            pdf_buffer.write(img2pdf.convert(images))
            pdf_buffer.seek(0)
            compressed_files[q] = pdf_buffer

        # Tampilkan ukuran file hasil compress
        st.write("Perkiraan ukuran file setelah compress:")
        for q, buf in compressed_files.items():
            size_kb = len(buf.getbuffer()) / 1024
            st.write(f"- {q}: {size_kb:.2f} KB")
            st.download_button(f"⬇️ Unduh PDF {q}", data=buf, file_name=f"{pdf_name}_compressed_{q}.pdf", mime="application/pdf", key=f"comp_{q}")

else:
    st.info("Silakan upload PDF untuk memulai preview, split, dan compress.")
