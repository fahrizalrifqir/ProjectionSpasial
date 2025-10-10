import streamlit as st
from PyPDF2 import PdfReader, PdfWriter
import io

st.set_page_config(page_title="PDF Splitter", page_icon="📄", layout="centered")

st.title("📄 PDF Splitter")
st.write("Pisahkan file PDF berdasarkan rentang halaman yang kamu tentukan!")

uploaded_file = st.file_uploader("📤 Upload file PDF", type=["pdf"])

if uploaded_file is not None:
    # Baca PDF
    reader = PdfReader(uploaded_file)
    total_pages = len(reader.pages)
    st.success(f"File berhasil dibaca! Jumlah halaman: **{total_pages}**")

    rentang = st.text_input(
        "Masukkan rentang halaman (contoh: 1-3,4-5)",
        placeholder="contoh: 1-1,2-5"
    )

    if st.button("🔪 Split PDF"):
        if rentang.strip() == "":
            st.error("⚠️ Harap isi rentang halaman terlebih dahulu.")
        else:
            try:
                # Parsing rentang halaman
                splits = []
                for r in rentang.split(","):
                    start, end = map(int, r.split("-"))
                    splits.append((start, end))

                # Proses splitting
                output_files = []
                for idx, (start, end) in enumerate(splits, start=1):
                    writer = PdfWriter()
                    for i in range(start - 1, end):
                        if i < total_pages:
                            writer.add_page(reader.pages[i])
                    output_buffer = io.BytesIO()
                    writer.write(output_buffer)
                    output_buffer.seek(0)
                    output_files.append((f"part_{idx}_hal_{start}_sampai_{end}.pdf", output_buffer))

                # Tampilkan hasil unduhan
                st.success("✅ Split berhasil! Unduh hasil di bawah ini:")
                for name, buf in output_files:
                    st.download_button(
                        label=f"⬇️ Unduh {name}",
                        data=buf,
                        file_name=name,
                        mime="application/pdf"
                    )

            except Exception as e:
                st.error(f"Terjadi kesalahan: {e}")
else:
    st.info("Unggah file PDF terlebih dahulu untuk memulai.")
