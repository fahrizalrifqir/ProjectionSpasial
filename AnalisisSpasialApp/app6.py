import streamlit as st
from PyPDF2 import PdfReader, PdfWriter
import io
import os

st.set_page_config(page_title="PDF Splitter (Fleksibel)", page_icon="📄", layout="centered")

st.title("📄 PDF Splitter — Pisahkan PDF Berdasarkan Rentang Halaman")
st.write("Unggah PDF dan tentukan rentang halaman yang ingin dipisahkan, misalnya:")
st.code("1-1,2-12", language="text")
st.markdown("- 📘 Rentang pertama → nama file asli\n- 📗 Rentang berikutnya → diberi awalan **RPD_**")

# --- Upload File ---
uploaded_file = st.file_uploader("📤 Upload file PDF", type=["pdf"])

# --- Jika ada file diupload ---
if uploaded_file is not None:
    original_name = os.path.splitext(uploaded_file.name)[0]
    reader = PdfReader(uploaded_file)
    total_pages = len(reader.pages)
    st.success(f"File terbaca: **{uploaded_file.name}** dengan {total_pages} halaman.")

    rentang_input = st.text_input(
        "Masukkan rentang halaman (contoh: 1-1,2-12)",
        value=f"1-1,2-{total_pages}"
    )

    # --- Tombol Split ---
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

                # Penamaan file
                if idx == 0:
                    output_name = f"{original_name}.pdf"
                else:
                    output_name = f"RPD_{original_name}_hal_{start}_sampai_{end}.pdf"

                output_files.append((output_name, buffer))

            # Simpan hasil ke session_state agar tidak hilang setelah rerun
            st.session_state["split_results"] = output_files
            st.session_state["total_pages"] = total_pages

        except Exception as e:
            st.error(f"Terjadi kesalahan: {e}")

    # --- Jika hasil split tersimpan, tampilkan tombol download ---
    if "split_results" in st.session_state:
        st.success("✅ Split berhasil! Unduh hasil di bawah ini:")
        for name, buf in st.session_state["split_results"]:
            st.download_button(
                label=f"⬇️ Unduh {name}",
                data=buf,
                file_name=name,
                mime="application/pdf",
                key=name  # penting agar setiap tombol unik
            )
else:
    st.info("Unggah file PDF untuk memulai proses pemisahan.")
