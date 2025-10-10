import streamlit as st
from PyPDF2 import PdfReader, PdfWriter
import io
import os

st.set_page_config(page_title="PDF Splitter (Fleksibel)", page_icon="📄", layout="centered")

st.title("📄 PDF Splitter — Pisahkan PDF Berdasarkan Rentang Halaman")
st.write("Unggah PDF dan tentukan rentang halaman yang ingin dipisahkan, misalnya:")
st.code("1-1,2-12", language="text")
st.markdown("- 📘 Rentang pertama → nama file asli\n- 📗 Rentang berikutnya → diberi awalan **RPD_**")

uploaded_file = st.file_uploader("📤 Upload file PDF", type=["pdf"])

if uploaded_file is not None:
    original_name = os.path.splitext(uploaded_file.name)[0]
    reader = PdfReader(uploaded_file)
    total_pages = len(reader.pages)
    st.success(f"File terbaca: **{uploaded_file.name}** dengan {total_pages} halaman.")

    rentang_input = st.text_input(
        "Masukkan rentang halaman (contoh: 1-1,2-12)",
        value="1-1,2-{}".format(total_pages)
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
                output_buffer = io.BytesIO()
                writer.write(output_buffer)
                output_buffer.seek(0)

                # Penamaan file
                if idx == 0:
                    output_name = f"{original_name}.pdf"
                else:
                    output_name = f"RPD_{original_name}_hal_{start}_sampai_{end}.pdf"

                output_files.append((output_name, output_buffer))

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
    st.info("Unggah file PDF untuk memulai proses pemisahan.")
