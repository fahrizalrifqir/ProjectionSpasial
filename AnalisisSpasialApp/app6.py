import streamlit as st
from PyPDF2 import PdfReader, PdfWriter
import fitz  # PyMuPDF
import io, os
from PIL import Image

st.set_page_config(page_title="PDF Split + Preview", page_icon="📄", layout="wide")

st.title("📄 PDF Split + Slider Preview (Dua Kolom)")

st.write("Unggah PDF, lihat preview halaman dengan slider di kiri, dan split PDF di kanan.")
st.code("Contoh rentang split: 1-2,3-5", language="text")

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

    # ===================== LAYOUT DUA KOLOM ======================
    col1, col2 = st.columns(2)

    # --------------------- KOLOM KIRI: PREVIEW ---------------------
    with col1:
        st.subheader("🔹 Preview Halaman PDF")
        st.write("Gunakan slider untuk memilih halaman yang ingin dilihat.")

        if total_pages == 1:
            page_num = st.slider(
                "Pilih halaman:",
                min_value=1,
                max_value=2,
                value=1,
                step=1,
                help="PDF ini hanya memiliki 1 halaman."
            )
            page_num = 1
        else:
            page_num = st.slider(
                "Pilih halaman:",
                min_value=1,
                max_value=total_pages,
                value=1,
                step=1
            )

        try:
            page = pdf_doc[page_num - 1]
            pix = page.get_pixmap(matrix=fitz.Matrix(0.6, 0.6))  # ukuran preview lebih kecil
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            st.image(img, caption=f"Halaman {page_num}", use_column_width=True)
        except Exception as e:
            st.error(f"Gagal menampilkan preview halaman: {e}")

    # --------------------- KOLOM KANAN: SPLIT ---------------------
    with col2:
        st.subheader("✂️ Split PDF Berdasarkan Rentang Halaman")

        default_range = f"1-2,3-{total_pages}" if total_pages > 2 else "1-1"
        rentang_input = st.text_input(
            "Masukkan rentang halaman (contoh: 1-2,3-5):",
            value=default_range
        )

        if "last_uploaded" not in st.session_state or st.session_state["last_uploaded"] != uploaded_file.name:
            st.session_state["split_results"] = []
            st.session_state["last_uploaded"] = uploaded_file.name

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
    st.info("Silakan upload PDF untuk memulai preview dan split.")
