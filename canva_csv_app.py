import streamlit as st
import pandas as pd
import io
import re

# ==========================================
# KONFIGURASI APLIKASI
# ==========================================
st.set_page_config(page_title="Canva CSV Fast", page_icon="⚡", layout="centered")

st.title("⚡ Canva CSV Fast")
st.markdown("**Format Otomatis untuk Canva Bulk Create**")
st.markdown("Aplikasi ini membantu mengubah daftar nama file atau teks biasa menjadi format CSV yang siap di-upload ke Canva.")

# Input text area
raw_text = st.text_area("Tempel teks atau daftar nama file di sini...", height=250)

if st.button("🚀 Proses Sekarang", type="primary"):
    if not raw_text.strip():
        st.warning("Teks masih kosong. Silakan tempel teks terlebih dahulu.")
    else:
        try:
            # Jika sudah mengandung koma dan lebih dari 1 baris, anggap sudah CSV
            if "," in raw_text and len(raw_text.split('\n')) > 1:
                result_csv = raw_text
                st.success("✓ CSV Terdeteksi! (Data langsung diteruskan)")
            else:
                lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
                
                data = []
                for line in lines:
                    # Hilangkan ekstensi file (misal .jpg, .png)
                    title = re.sub(r'\.[^/.]+$', '', line)
                    # Ganti underscore dan strip dengan spasi
                    title = re.sub(r'[_-]', ' ', title)
                    
                    # Buat keywords (pisahkan judul berdasarkan spasi, gabung dengan koma)
                    keywords = ",".join(title.split(' '))
                    
                    data.append({
                        "filename": line,
                        "title": title,
                        "keywords": keywords
                    })
                
                df = pd.DataFrame(data)
                # Convert DataFrame to CSV string
                result_csv = df.to_csv(index=False)
                st.success("✓ Berhasil Konversi Teks menjadi CSV Canva!")

            # Sediakan tombol download
            st.download_button(
                label="📥 Download CSV",
                data=result_csv,
                file_name="canva_upload_ready.csv",
                mime="text/csv"
            )
            
        except Exception as e:
            st.error(f"Terjadi kesalahan saat memproses data: {e}")

st.markdown("---")
st.caption("Universal - Ready for Cloud | Sama seperti aplikasi sebelumnya, bisa langsung di-deploy ke Streamlit Cloud!")
