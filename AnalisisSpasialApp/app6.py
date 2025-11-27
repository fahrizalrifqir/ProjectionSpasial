import streamlit as st
from PyPDF2 import PdfReader, PdfWriter, PdfMerger
import fitz
import io, os
from PIL import Image
import img2pdf

st.set_page_config(page_title="PDF Tools", page_icon="📄", layout="wide")
st.title("📄 PDF Tools: Preview + Split + Compress + Merge")

# ===== PILIH FITUR =====
fitur = st.selectbox("Pilih fitur yang ingin digunakan:", ["Split PDF", "Compress PDF", "Merge PDF"])

# ===================== SPLIT / COMPRESS ======================
if fitur in ["Split PDF", "Compress PDF"]:
    uploaded_file = st.file_uploader("📤 Upload file PDF", type=["pdf"])
    
    if uploaded_file:
        # Hapus data lama
        if "last_uploaded" in st.session_state and st.session_state["last_uploaded"] != uploaded_file.name:
            keys_to_clear = ["split_results", "compressed_files", "last_uploaded"]
            for k in keys_to_clear:
                if k in st.session_state:
                    del st.session_state[k]

        pdf_bytes = uploaded_file.read()
        pdf_name = os.path.splitext(uploaded_file.name)[0]
        st.session_state["last_uploaded"] = uploaded_file.name

        try:
            pdf_reader = PdfReader(io.BytesIO(pdf_bytes))
            total_pages = len(pdf_reader.pages)
            pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        except:
            st.error("❌ Gagal membaca PDF.")
            st.stop()

        st.success(f"File terbaca: **{uploaded_file.name}** dengan {total_pages} halaman.")

        col1, col2 = st.columns([1,1])

        with col1:
            st.subheader("🔹 Preview Halaman PDF")
            page_num = st.slider("Pilih halaman:", 1, total_pages, 1)
            try:
                page = pdf_doc[page_num - 1]
                pix = page.get_pixmap(matrix=fitz.Matrix(0.8, 0.8))
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                st.image(img, caption=f"Halaman {page_num}", use_column_width=True)
            except Exception as e:
                st.error(f"Gagal menampilkan preview: {e}")

        with col2:
            if fitur == "Split PDF":
                st.subheader("✂️ Split PDF")
                default_range = f"1-2,3-{total_pages}" if total_pages>2 else "1-1"
                rentang_input = st.text_input("Masukkan rentang halaman (contoh: 1-2,3-5):", value=default_range)

                if "split_results" not in st.session_state:
                    st.session_state["split_results"] = []

                if st.button("🔪 Split Sekarang"):
                    try:
                        splits = []
                        for r in rentang_input.split(","):
                            if "-" in r:
                                start, end = map(int, r.split("-"))
                            else:
                                start = end = int(r)
                            splits.append((start,end))

                        output_files = []
                        for idx,(start,end) in enumerate(splits):
                            writer = PdfWriter()
                            for p in range(start-1,end):
                                if 0<=p<total_pages:
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

                # Tombol download split (2 kolom)
                split_files = st.session_state.get("split_results", [])
                for i in range(0,len(split_files),2):
                    cols = st.columns(2)
                    for j,col in enumerate(cols):
                        if i+j<len(split_files):
                            name, buf = split_files[i+j]
                            col.download_button(f"⬇️ {name}", data=buf, file_name=name, mime="application/pdf", key=f"split_{i+j}")

            elif fitur == "Compress PDF":
                st.subheader("🗜 Compress PDF (perkiraan ukuran file + download)")
                if "compressed_files" not in st.session_state:
                    st.session_state["compressed_files"] = {}

                if st.button("Proses Compress"):
                    st.session_state["compressed_files"] = {}
                    quality_map = {
                        "Sangat Rendah":{"scale":0.5,"jpeg_quality":50},
                        "Rendah":{"scale":0.6,"jpeg_quality":65},
                        "Sedang":{"scale":0.7,"jpeg_quality":80},
                        "Tinggi":{"scale":0.8,"jpeg_quality":90},
                    }
                    for q, settings in quality_map.items():
                        scale = settings["scale"]
                        jpeg_q = settings["jpeg_quality"]
                        images = []
                        for page in pdf_doc:
                            pix = page.get_pixmap(matrix=fitz.Matrix(scale,scale))
                            img = Image.open(io.BytesIO(pix.tobytes("png")))
                            img_byte_arr = io.BytesIO()
                            img.save(img_byte_arr, format='JPEG', quality=jpeg_q)
                            images.append(img_byte_arr.getvalue())
                        pdf_buffer = io.BytesIO()
                        pdf_buffer.write(img2pdf.convert(images))
                        pdf_buffer.seek(0)
                        st.session_state["compressed_files"][q] = pdf_buffer
                    st.success("✅ Compress selesai!")

                # Tombol download compress (2 kolom)
                compressed_files = list(st.session_state.get("compressed_files", {}).items())
                for i in range(0,len(compressed_files),2):
                    cols = st.columns(2)
                    for j,col in enumerate(cols):
                        if i+j<len(compressed_files):
                            q, buf = compressed_files[i+j]
                            size_kb = len(buf.getbuffer())/1024
                            size_str = f"{size_kb:.2f} KB" if size_kb<1024 else f"{size_kb/1024:.2f} MB"
                            col.download_button(f"⬇️ {q} : {size_str}", data=buf, file_name=f"{pdf_name}_compressed_{q}.pdf", mime="application/pdf", key=f"comp_{q}")

# ===================== MERGE ======================
elif fitur=="Merge PDF":
    uploaded_merge_files = st.file_uploader(
        "📤 Upload hingga 5 file PDF untuk merge",
        type="pdf",
        accept_multiple_files=True,
        key="merge_uploader"
    )

    if uploaded_merge_files:
        if len(uploaded_merge_files)>5:
            st.error("❌ Maksimal 5 file untuk merge!")
        else:
            st.subheader("Atur urutan file PDF sebelum merge")
            file_names = [f.name for f in uploaded_merge_files]
            urutan = []
            for i, fname in enumerate(file_names):
                order = st.number_input(f"Urutan '{fname}'", min_value=1, max_value=len(file_names), value=i+1, step=1, key=f"order_{i}")
                urutan.append((order, i))
            
            # Sort file sesuai urutan
            urutan.sort(key=lambda x: x[0])
            sorted_files = [uploaded_merge_files[i] for _,i in urutan]

            if st.button("🔗 Merge PDF"):
                merger = PdfMerger()
                for f in sorted_files:
                    merger.append(f)
                buf = io.BytesIO()
                merger.write(buf)
                buf.seek(0)
                st.download_button("⬇️ Unduh PDF Hasil Merge", data=buf, file_name="merged.pdf", mime="application/pdf")
