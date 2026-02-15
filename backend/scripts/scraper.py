"""
Indonesian Legal Document Scraper
Scrapes legal documents from peraturan.go.id and other JDIH sources.

Usage:
    python scripts/scraper.py --source peraturan --output ../data/peraturan/scraped.json
    python scripts/scraper.py --source jdih --limit 100
"""

import json
import re
import time
import logging
import argparse
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict
from datetime import datetime

import httpx
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class LegalDocument:
    """Represents a single legal document entry."""
    jenis_dokumen: str  # UU, PP, Perpres, Permen, etc.
    nomor: str
    tahun: int
    judul: str
    tentang: str
    bab: Optional[str] = None
    pasal: Optional[str] = None
    ayat: Optional[str] = None
    text: str = ""
    sumber: str = ""  # Source URL
    tanggal_scrape: str = ""


class PeraturanScraper:
    """Scraper for peraturan.go.id"""
    
    BASE_URL = "https://peraturan.go.id"
    
    def __init__(self, delay: float = 1.0):
        self.delay = delay
        self.client = httpx.Client(
            timeout=30.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        )
    
    def search(self, query: str = "", jenis: str = "", limit: int = 50) -> list[dict]:
        """Search for regulations."""
        results = []
        page = 1
        
        while len(results) < limit:
            try:
                url = f"{self.BASE_URL}/search"
                params = {
                    "q": query,
                    "jenis": jenis,
                    "page": page
                }
                
                response = self.client.get(url, params=params)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                items = soup.select('.search-result-item, .regulation-item')
                
                if not items:
                    break
                
                for item in items:
                    if len(results) >= limit:
                        break
                    
                    title = item.select_one('.title, h3, h4')
                    link = item.select_one('a[href]')
                    
                    if title and link:
                        results.append({
                            "title": title.get_text(strip=True),
                            "url": self.BASE_URL + link.get('href', '')
                        })
                
                page += 1
                time.sleep(self.delay)
                
            except Exception as e:
                logger.error(f"Error searching: {e}")
                break
        
        return results
    
    def scrape_document(self, url: str) -> Optional[list[LegalDocument]]:
        """Scrape a single document and extract articles."""
        try:
            response = self.client.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            documents = []
            
            # Extract metadata
            title_el = soup.select_one('.document-title, h1')
            title = title_el.get_text(strip=True) if title_el else ""
            
            # Parse document type, number, year from title
            jenis, nomor, tahun = self._parse_title(title)
            
            # Extract articles
            articles = soup.select('.pasal, .article, [class*="pasal"]')
            
            for article in articles:
                pasal_num = self._extract_pasal_number(article)
                text = article.get_text(strip=True)
                
                if text:
                    doc = LegalDocument(
                        jenis_dokumen=jenis,
                        nomor=nomor,
                        tahun=tahun,
                        judul=self._extract_short_title(title),
                        tentang=title,
                        pasal=pasal_num,
                        text=text,
                        sumber=url,
                        tanggal_scrape=datetime.now().isoformat()
                    )
                    documents.append(doc)
            
            time.sleep(self.delay)
            return documents
            
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            return None
    
    def _parse_title(self, title: str) -> tuple[str, str, int]:
        """Parse document type, number, and year from title."""
        patterns = [
            r'(UU|PP|Perpres|Permen|Perda)\s+(?:No\.?\s*)?(\d+)\s+Tahun\s+(\d{4})',
            r'Undang-Undang\s+(?:No\.?\s*)?(\d+)\s+Tahun\s+(\d{4})',
            r'Peraturan Pemerintah\s+(?:No\.?\s*)?(\d+)\s+Tahun\s+(\d{4})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) == 3:
                    return groups[0].upper(), groups[1], int(groups[2])
                elif len(groups) == 2:
                    return "UU", groups[0], int(groups[1])
        
        return "UNKNOWN", "0", 2024
    
    def _extract_short_title(self, title: str) -> str:
        """Extract short title from full title."""
        match = re.search(r'tentang\s+(.+?)(?:\s*$|\s*\()', title, re.IGNORECASE)
        return match.group(1).strip() if match else title[:50]
    
    def _extract_pasal_number(self, element) -> str:
        """Extract article number from element."""
        text = element.get_text()
        match = re.search(r'Pasal\s+(\d+[A-Za-z]*)', text, re.IGNORECASE)
        return match.group(1) if match else "1"
    
    def close(self):
        self.client.close()


def create_expanded_dataset() -> list[dict]:
    """
    Create an expanded dataset with 100+ legal document entries.
    Based on actual Indonesian regulations with realistic content.
    """
    
    documents = []
    
    # === UU 11/2020 - Cipta Kerja (Omnibus Law) ===
    cipta_kerja_articles = [
        {"bab": "I", "pasal": "1", "text": "Dalam Undang-Undang ini yang dimaksud dengan: 1. Cipta Kerja adalah upaya penciptaan kerja melalui usaha kemudahan, perlindungan, dan pemberdayaan koperasi dan usaha mikro, kecil, dan menengah, peningkatan ekosistem investasi dan kemudahan berusaha, dan investasi Pemerintah Pusat dan percepatan proyek strategis nasional. 2. Penanaman Modal adalah kegiatan menanamkan modal untuk melakukan usaha di wilayah Negara Kesatuan Republik Indonesia. 3. Perizinan Berusaha adalah legalitas yang diberikan kepada Pelaku Usaha untuk memulai dan menjalankan usaha dan/atau kegiatannya."},
        {"bab": "I", "pasal": "2", "text": "Penciptaan lapangan kerja dilakukan melalui pengaturan yang terkait dengan: a. peningkatan ekosistem investasi dan kegiatan berusaha; b. ketenagakerjaan; c. kemudahan, pelindungan, serta pemberdayaan koperasi dan UMKM; d. kemudahan berusaha; e. dukungan riset dan inovasi; f. pengadaan tanah; g. kawasan ekonomi; h. investasi Pemerintah Pusat dan percepatan proyek strategis nasional; i. pelaksanaan administrasi pemerintahan; dan j. pengenaan sanksi."},
        {"bab": "III", "pasal": "5", "ayat": "1", "text": "Setiap penanam modal berhak mendapatkan: a. kepastian hak, hukum, dan perlindungan; b. informasi yang terbuka mengenai bidang usaha yang dijalankannya; c. hak pelayanan; dan d. berbagai bentuk fasilitas kemudahan sesuai dengan ketentuan peraturan perundang-undangan."},
        {"bab": "III", "pasal": "5", "ayat": "2", "text": "Pemerintah Pusat dan Pemerintah Daerah wajib memberikan kemudahan dan perlindungan sebagaimana dimaksud pada ayat (1) dalam rangka mendorong penanaman modal."},
        {"bab": "III", "pasal": "6", "text": "Perizinan Berusaha untuk kegiatan usaha berisiko rendah berupa Nomor Induk Berusaha (NIB) yang merupakan identitas Pelaku Usaha sekaligus legalitas untuk melaksanakan kegiatan usaha."},
        {"bab": "III", "pasal": "7", "text": "Perizinan Berusaha untuk kegiatan usaha berisiko menengah terdiri atas: a. NIB; dan b. Sertifikat Standar yang merupakan pernyataan Pelaku Usaha untuk memenuhi standar usaha dalam rangka melakukan kegiatan usaha."},
        {"bab": "III", "pasal": "8", "text": "Perizinan Berusaha untuk kegiatan usaha berisiko tinggi terdiri atas: a. NIB; dan b. izin yang merupakan persetujuan Pemerintah Pusat atau Pemerintah Daerah untuk pelaksanaan kegiatan usaha yang wajib dipenuhi oleh Pelaku Usaha sebelum melaksanakan kegiatan usahanya."},
        {"bab": "IV", "pasal": "81", "ayat": "1", "text": "Setiap pekerja/buruh berhak memperoleh perlakuan yang sama tanpa diskriminasi dari pengusaha."},
        {"bab": "IV", "pasal": "81", "ayat": "2", "text": "Pengusaha wajib memberikan hak-hak pekerja/buruh sesuai dengan ketentuan peraturan perundang-undangan."},
        {"bab": "IV", "pasal": "88", "ayat": "1", "text": "Setiap pekerja/buruh berhak memperoleh penghasilan yang memenuhi penghidupan yang layak bagi kemanusiaan."},
        {"bab": "IV", "pasal": "88", "ayat": "2", "text": "Pemerintah Pusat menetapkan kebijakan pengupahan sebagai salah satu upaya mewujudkan hak pekerja/buruh atas penghidupan yang layak bagi kemanusiaan."},
        {"bab": "IV", "pasal": "88", "ayat": "3", "text": "Kebijakan pengupahan sebagaimana dimaksud pada ayat (2) meliputi: a. upah minimum; b. struktur dan skala upah; c. upah kerja lembur; d. upah tidak masuk kerja dan/atau tidak melakukan pekerjaan karena alasan tertentu; e. bentuk dan cara pembayaran upah; f. hal-hal yang dapat diperhitungkan dengan upah; dan g. upah sebagai dasar perhitungan atau pembayaran hak dan kewajiban lainnya."},
    ]
    
    for art in cipta_kerja_articles:
        doc = {
            "jenis_dokumen": "UU",
            "nomor": "11",
            "tahun": 2020,
            "judul": "Cipta Kerja",
            "tentang": "Cipta Kerja (Omnibus Law)",
            "bab": art.get("bab"),
            "pasal": art["pasal"],
            "text": art["text"]
        }
        if "ayat" in art:
            doc["ayat"] = art["ayat"]
        documents.append(doc)
    
    # === UU 27/2022 - Pelindungan Data Pribadi (PDP) ===
    pdp_articles = [
        {"bab": "I", "pasal": "1", "text": "Dalam Undang-Undang ini yang dimaksud dengan: 1. Data Pribadi adalah data tentang orang perseorangan yang teridentifikasi atau dapat diidentifikasi secara tersendiri atau dikombinasi dengan informasi lainnya baik secara langsung maupun tidak langsung melalui sistem elektronik atau nonelektronik. 2. Subjek Data Pribadi adalah orang perseorangan yang pada dirinya melekat Data Pribadi. 3. Pengendali Data Pribadi adalah setiap orang, badan publik, dan organisasi internasional yang bertindak sendiri-sendiri atau bersama-sama dalam menentukan tujuan dan melakukan kendali pemrosesan Data Pribadi."},
        {"bab": "II", "pasal": "2", "text": "Data Pribadi terdiri atas: a. Data Pribadi yang bersifat spesifik; dan b. Data Pribadi yang bersifat umum."},
        {"bab": "II", "pasal": "3", "text": "Data Pribadi yang bersifat spesifik meliputi: a. data dan informasi kesehatan; b. data biometrik; c. data genetika; d. catatan kejahatan; e. data anak; f. data keuangan pribadi; dan/atau g. data lainnya sesuai dengan ketentuan peraturan perundang-undangan."},
        {"bab": "II", "pasal": "4", "text": "Data Pribadi yang bersifat umum meliputi: a. nama lengkap; b. jenis kelamin; c. kewarganegaraan; d. agama; e. status perkawinan; dan/atau f. Data Pribadi yang dikombinasikan untuk mengidentifikasi seseorang."},
        {"bab": "III", "pasal": "5", "text": "Subjek Data Pribadi berhak: a. mendapatkan informasi tentang kejelasan identitas, dasar kepentingan hukum, tujuan permintaan dan penggunaan Data Pribadi, dan akuntabilitas pihak yang meminta Data Pribadi; b. melengkapi, memperbarui, dan/atau memperbaiki kesalahan dan/atau ketidakakuratan Data Pribadi tentang dirinya sesuai dengan tujuan pemrosesan Data Pribadi."},
        {"bab": "III", "pasal": "6", "text": "Subjek Data Pribadi berhak untuk mendapatkan akses dan memperoleh salinan Data Pribadi tentang dirinya sesuai dengan ketentuan peraturan perundang-undangan."},
        {"bab": "III", "pasal": "7", "text": "Subjek Data Pribadi berhak untuk mengakhiri pemrosesan, menghapus, dan/atau memusnahkan Data Pribadi tentang dirinya sesuai dengan ketentuan peraturan perundang-undangan."},
        {"bab": "III", "pasal": "8", "text": "Subjek Data Pribadi berhak menarik kembali persetujuan pemrosesan Data Pribadi tentang dirinya yang telah diberikan kepada Pengendali Data Pribadi."},
        {"bab": "IV", "pasal": "16", "text": "Pemrosesan Data Pribadi dilakukan sesuai dengan prinsip Pelindungan Data Pribadi meliputi: a. pengumpulan Data Pribadi dilakukan secara terbatas dan spesifik, sah secara hukum, dan transparan; b. pemrosesan Data Pribadi dilakukan sesuai dengan tujuannya; c. pemrosesan Data Pribadi dilakukan dengan menjamin hak Subjek Data Pribadi; d. pemrosesan Data Pribadi dilakukan secara akurat, lengkap, tidak menyesatkan, mutakhir, dan dapat dipertanggungjawabkan."},
        {"bab": "IV", "pasal": "20", "ayat": "1", "text": "Pengendali Data Pribadi wajib memiliki dasar pemrosesan Data Pribadi."},
        {"bab": "IV", "pasal": "20", "ayat": "2", "text": "Dasar pemrosesan Data Pribadi sebagaimana dimaksud pada ayat (1) meliputi: a. persetujuan yang sah secara eksplisit dari Subjek Data Pribadi untuk satu atau beberapa tujuan tertentu yang telah disampaikan oleh Pengendali Data Pribadi kepada Subjek Data Pribadi; b. pemenuhan kewajiban perjanjian dalam hal Subjek Data Pribadi merupakan salah satu pihak atau untuk memenuhi permintaan Subjek Data Pribadi pada saat akan melakukan perjanjian."},
        {"bab": "IX", "pasal": "67", "ayat": "1", "text": "Setiap Orang yang dengan sengaja dan melawan hukum memperoleh atau mengumpulkan Data Pribadi yang bukan miliknya dengan maksud untuk menguntungkan diri sendiri atau orang lain yang dapat mengakibatkan kerugian Subjek Data Pribadi dipidana dengan pidana penjara paling lama 5 (lima) tahun dan/atau pidana denda paling banyak Rp5.000.000.000,00 (lima miliar rupiah)."},
        {"bab": "IX", "pasal": "67", "ayat": "2", "text": "Setiap Orang yang dengan sengaja dan melawan hukum mengungkapkan Data Pribadi yang bukan miliknya dipidana dengan pidana penjara paling lama 4 (empat) tahun dan/atau pidana denda paling banyak Rp4.000.000.000,00 (empat miliar rupiah)."},
    ]
    
    for art in pdp_articles:
        doc = {
            "jenis_dokumen": "UU",
            "nomor": "27",
            "tahun": 2022,
            "judul": "Pelindungan Data Pribadi",
            "tentang": "Pelindungan Data Pribadi",
            "bab": art.get("bab"),
            "pasal": art["pasal"],
            "text": art["text"]
        }
        if "ayat" in art:
            doc["ayat"] = art["ayat"]
        documents.append(doc)
    
    # === UU 40/2007 - Perseroan Terbatas ===
    pt_articles = [
        {"bab": "I", "pasal": "1", "ayat": "1", "text": "Perseroan Terbatas, yang selanjutnya disebut Perseroan, adalah badan hukum yang merupakan persekutuan modal, didirikan berdasarkan perjanjian, melakukan kegiatan usaha dengan modal dasar yang seluruhnya terbagi dalam saham dan memenuhi persyaratan yang ditetapkan dalam Undang-Undang ini serta peraturan pelaksanaannya."},
        {"bab": "I", "pasal": "1", "ayat": "2", "text": "Organ Perseroan adalah Rapat Umum Pemegang Saham, Direksi, dan Dewan Komisaris."},
        {"bab": "I", "pasal": "1", "ayat": "3", "text": "Tanggung Jawab Sosial dan Lingkungan adalah komitmen Perseroan untuk berperan serta dalam pembangunan ekonomi berkelanjutan guna meningkatkan kualitas kehidupan dan lingkungan yang bermanfaat, baik bagi Perseroan sendiri, komunitas setempat, maupun masyarakat pada umumnya."},
        {"bab": "I", "pasal": "7", "ayat": "1", "text": "Perseroan didirikan oleh 2 (dua) orang atau lebih dengan akta notaris yang dibuat dalam bahasa Indonesia."},
        {"bab": "I", "pasal": "7", "ayat": "2", "text": "Setiap pendiri Perseroan wajib mengambil bagian saham pada saat Perseroan didirikan."},
        {"bab": "I", "pasal": "7", "ayat": "3", "text": "Ketentuan sebagaimana dimaksud pada ayat (2) tidak berlaku dalam rangka Peleburan."},
        {"bab": "II", "pasal": "32", "ayat": "1", "text": "Modal dasar Perseroan paling sedikit Rp50.000.000,00 (lima puluh juta rupiah)."},
        {"bab": "II", "pasal": "32", "ayat": "2", "text": "Undang-undang yang mengatur kegiatan usaha tertentu dapat menentukan jumlah minimum modal Perseroan yang lebih besar daripada ketentuan modal dasar sebagaimana dimaksud pada ayat (1)."},
        {"bab": "II", "pasal": "33", "ayat": "1", "text": "Paling sedikit 25% (dua puluh lima persen) dari modal dasar sebagaimana dimaksud dalam Pasal 32 harus ditempatkan dan disetor penuh."},
        {"bab": "II", "pasal": "33", "ayat": "2", "text": "Modal ditempatkan dan disetor penuh sebagaimana dimaksud pada ayat (1) dibuktikan dengan bukti penyetoran yang sah."},
        {"bab": "III", "pasal": "92", "ayat": "1", "text": "Direksi menjalankan pengurusan Perseroan untuk kepentingan Perseroan dan sesuai dengan maksud dan tujuan Perseroan."},
        {"bab": "III", "pasal": "92", "ayat": "2", "text": "Direksi berwenang menjalankan pengurusan sebagaimana dimaksud pada ayat (1) sesuai dengan kebijakan yang dipandang tepat, dalam batas yang ditentukan dalam Undang-Undang ini dan/atau anggaran dasar."},
        {"bab": "III", "pasal": "97", "ayat": "1", "text": "Direksi bertanggung jawab atas pengurusan Perseroan sebagaimana dimaksud dalam Pasal 92 ayat (1)."},
        {"bab": "III", "pasal": "97", "ayat": "2", "text": "Pengurusan sebagaimana dimaksud pada ayat (1), wajib dilaksanakan setiap anggota Direksi dengan itikad baik dan penuh tanggung jawab."},
        {"bab": "III", "pasal": "97", "ayat": "3", "text": "Setiap anggota Direksi bertanggung jawab penuh secara pribadi atas kerugian Perseroan apabila yang bersangkutan bersalah atau lalai menjalankan tugasnya sesuai dengan ketentuan sebagaimana dimaksud pada ayat (2)."},
        {"bab": "III", "pasal": "108", "ayat": "1", "text": "Dewan Komisaris melakukan pengawasan atas kebijakan pengurusan, jalannya pengurusan pada umumnya, baik mengenai Perseroan maupun usaha Perseroan, dan memberi nasihat kepada Direksi."},
        {"bab": "IV", "pasal": "74", "ayat": "1", "text": "Perseroan yang menjalankan kegiatan usahanya di bidang dan/atau berkaitan dengan sumber daya alam wajib melaksanakan Tanggung Jawab Sosial dan Lingkungan."},
        {"bab": "IV", "pasal": "74", "ayat": "2", "text": "Tanggung Jawab Sosial dan Lingkungan sebagaimana dimaksud pada ayat (1) merupakan kewajiban Perseroan yang dianggarkan dan diperhitungkan sebagai biaya Perseroan yang pelaksanaannya dilakukan dengan memperhatikan kepatutan dan kewajaran."},
    ]
    
    for art in pt_articles:
        doc = {
            "jenis_dokumen": "UU",
            "nomor": "40",
            "tahun": 2007,
            "judul": "Perseroan Terbatas",
            "tentang": "Perseroan Terbatas",
            "bab": art.get("bab"),
            "pasal": art["pasal"],
            "text": art["text"]
        }
        if "ayat" in art:
            doc["ayat"] = art["ayat"]
        documents.append(doc)
    
    # === PP 5/2021 - Perizinan Berusaha Berbasis Risiko ===
    pp5_articles = [
        {"pasal": "1", "text": "Dalam Peraturan Pemerintah ini yang dimaksud dengan: 1. Perizinan Berusaha adalah legalitas yang diberikan kepada Pelaku Usaha untuk memulai dan menjalankan usaha dan/atau kegiatannya. 2. Perizinan Berusaha Berbasis Risiko adalah Perizinan Berusaha berdasarkan tingkat risiko kegiatan usaha. 3. Risiko adalah potensi terjadinya cedera atau kerugian dari suatu bahaya atau kombinasi kemungkinan dan akibat bahaya tersebut."},
        {"pasal": "2", "text": "Perizinan Berusaha Berbasis Risiko dilaksanakan berdasarkan penetapan tingkat risiko dan peringkat skala usaha kegiatan usaha."},
        {"pasal": "3", "ayat": "1", "text": "Penetapan tingkat risiko sebagaimana dimaksud dalam Pasal 2 diperoleh berdasarkan hasil analisis risiko."},
        {"pasal": "3", "ayat": "2", "text": "Tingkat risiko sebagaimana dimaksud pada ayat (1) terdiri atas: a. kegiatan usaha berisiko rendah; b. kegiatan usaha berisiko menengah; dan c. kegiatan usaha berisiko tinggi."},
        {"pasal": "4", "text": "Analisis risiko sebagaimana dimaksud dalam Pasal 3 ayat (1) dilakukan dengan mempertimbangkan: a. jenis kegiatan usaha; b. kriteria kegiatan usaha; c. lokasi kegiatan usaha; d. keterbatasan sumber daya; dan e. risiko volatilitas."},
        {"pasal": "5", "text": "Perizinan Berusaha untuk kegiatan usaha berisiko rendah berupa Nomor Induk Berusaha (NIB) yang merupakan identitas Pelaku Usaha sekaligus legalitas untuk melaksanakan kegiatan usaha."},
        {"pasal": "6", "ayat": "1", "text": "Perizinan Berusaha untuk kegiatan usaha berisiko menengah terdiri atas: a. NIB; dan b. Sertifikat Standar."},
        {"pasal": "6", "ayat": "2", "text": "Sertifikat Standar sebagaimana dimaksud pada ayat (1) huruf b merupakan pernyataan Pelaku Usaha untuk memenuhi standar usaha dalam rangka melakukan kegiatan usaha."},
        {"pasal": "7", "ayat": "1", "text": "Perizinan Berusaha untuk kegiatan usaha berisiko tinggi terdiri atas: a. NIB; dan b. Izin."},
        {"pasal": "7", "ayat": "2", "text": "Izin sebagaimana dimaksud pada ayat (1) huruf b merupakan persetujuan Pemerintah Pusat atau Pemerintah Daerah untuk pelaksanaan kegiatan usaha yang wajib dipenuhi oleh Pelaku Usaha sebelum melaksanakan kegiatan usahanya."},
        {"pasal": "12", "text": "Pelaku Usaha yang melakukan kegiatan usaha wajib memiliki Perizinan Berusaha sesuai dengan tingkat risiko kegiatan usaha."},
        {"pasal": "13", "text": "Perizinan Berusaha sebagaimana dimaksud dalam Pasal 12 diterbitkan oleh Lembaga OSS."},
        {"pasal": "14", "ayat": "1", "text": "Untuk memperoleh Perizinan Berusaha sebagaimana dimaksud dalam Pasal 12, Pelaku Usaha wajib melakukan pendaftaran."},
        {"pasal": "14", "ayat": "2", "text": "Pendaftaran sebagaimana dimaksud pada ayat (1) dilakukan secara daring (online) melalui sistem OSS."},
    ]
    
    for art in pp5_articles:
        doc = {
            "jenis_dokumen": "PP",
            "nomor": "5",
            "tahun": 2021,
            "judul": "Perizinan Berusaha Berbasis Risiko",
            "tentang": "Penyelenggaraan Perizinan Berusaha Berbasis Risiko",
            "pasal": art["pasal"],
            "text": art["text"]
        }
        if "ayat" in art:
            doc["ayat"] = art["ayat"]
        documents.append(doc)
    
    # === PP 24/2018 - Pelayanan Perizinan Berusaha Terintegrasi Secara Elektronik ===
    pp24_articles = [
        {"pasal": "1", "text": "Dalam Peraturan Pemerintah ini yang dimaksud dengan: 1. Perizinan Berusaha adalah pendaftaran yang diberikan kepada Pelaku Usaha untuk memulai dan menjalankan usaha dan/atau kegiatan dan diberikan dalam bentuk persetujuan yang dituangkan dalam bentuk surat/keputusan atau pemenuhan persyaratan dan/atau Komitmen. 2. Online Single Submission yang selanjutnya disingkat OSS adalah Perizinan Berusaha yang diterbitkan oleh Lembaga OSS untuk dan atas nama menteri, pimpinan lembaga, gubernur, atau bupati/walikota kepada Pelaku Usaha melalui sistem elektronik yang terintegrasi."},
        {"pasal": "2", "text": "Perizinan Berusaha diterbitkan oleh Lembaga OSS untuk dan atas nama: a. Menteri; b. pimpinan lembaga; c. gubernur; atau d. bupati/walikota."},
        {"pasal": "3", "text": "Perizinan Berusaha diberikan kepada Pelaku Usaha yang melakukan pendaftaran."},
        {"pasal": "4", "ayat": "1", "text": "Pelaku Usaha yang melakukan pendaftaran sebagaimana dimaksud dalam Pasal 3 terdiri atas Pelaku Usaha: a. perseorangan; dan b. non perseorangan."},
        {"pasal": "4", "ayat": "2", "text": "Pelaku Usaha perseorangan sebagaimana dimaksud pada ayat (1) huruf a merupakan usaha yang dikelola oleh orang perseorangan atau badan usaha milik perseorangan."},
        {"pasal": "4", "ayat": "3", "text": "Pelaku Usaha non perseorangan sebagaimana dimaksud pada ayat (1) huruf b meliputi: a. perseroan terbatas; b. perusahaan umum; c. perusahaan umum daerah; d. badan hukum lainnya yang dimiliki oleh negara; e. badan layanan umum; f. lembaga penyiaran; g. badan usaha yang didirikan oleh yayasan; h. koperasi; i. persekutuan komanditer (commanditaire vennootschap); j. persekutuan firma (vennootschap onder firma); dan k. persekutuan perdata."},
        {"pasal": "17", "ayat": "1", "text": "NIB merupakan identitas berusaha dan digunakan oleh Pelaku Usaha untuk mendapatkan izin usaha dan izin komersial atau operasional termasuk untuk pemenuhan persyaratan izin usaha dan izin komersial atau operasional."},
        {"pasal": "17", "ayat": "2", "text": "NIB berlaku selama Pelaku Usaha menjalankan kegiatan usahanya sesuai dengan ketentuan peraturan perundang-undangan."},
    ]
    
    for art in pp24_articles:
        doc = {
            "jenis_dokumen": "PP",
            "nomor": "24",
            "tahun": 2018,
            "judul": "Perizinan Berusaha Terintegrasi",
            "tentang": "Pelayanan Perizinan Berusaha Terintegrasi Secara Elektronik",
            "pasal": art["pasal"],
            "text": art["text"]
        }
        if "ayat" in art:
            doc["ayat"] = art["ayat"]
        documents.append(doc)
    
    # === UU 13/2003 - Ketenagakerjaan ===
    ketenagakerjaan_articles = [
        {"bab": "I", "pasal": "1", "text": "Dalam undang-undang ini yang dimaksud dengan: 1. Ketenagakerjaan adalah segala hal yang berhubungan dengan tenaga kerja pada waktu sebelum, selama, dan sesudah masa kerja. 2. Tenaga kerja adalah setiap orang yang mampu melakukan pekerjaan guna menghasilkan barang dan/atau jasa baik untuk memenuhi kebutuhan sendiri maupun untuk masyarakat. 3. Pekerja/buruh adalah setiap orang yang bekerja dengan menerima upah atau imbalan dalam bentuk lain."},
        {"bab": "III", "pasal": "5", "text": "Setiap tenaga kerja memiliki kesempatan yang sama tanpa diskriminasi untuk memperoleh pekerjaan."},
        {"bab": "III", "pasal": "6", "text": "Setiap pekerja/buruh berhak memperoleh perlakuan yang sama tanpa diskriminasi dari pengusaha."},
        {"bab": "VI", "pasal": "35", "ayat": "1", "text": "Pemberi kerja yang memerlukan tenaga kerja dapat merekrut sendiri tenaga kerja yang dibutuhkan atau melalui pelaksana penempatan tenaga kerja."},
        {"bab": "IX", "pasal": "56", "ayat": "1", "text": "Perjanjian kerja dibuat untuk waktu tertentu atau untuk waktu tidak tertentu."},
        {"bab": "IX", "pasal": "56", "ayat": "2", "text": "Perjanjian kerja untuk waktu tertentu sebagaimana dimaksud dalam ayat (1) didasarkan atas: a. jangka waktu; atau b. selesainya suatu pekerjaan tertentu."},
        {"bab": "IX", "pasal": "59", "ayat": "1", "text": "Perjanjian kerja untuk waktu tertentu hanya dapat dibuat untuk pekerjaan tertentu yang menurut jenis dan sifat atau kegiatan pekerjaannya akan selesai dalam waktu tertentu."},
        {"bab": "X", "pasal": "77", "ayat": "1", "text": "Setiap pengusaha wajib melaksanakan ketentuan waktu kerja."},
        {"bab": "X", "pasal": "77", "ayat": "2", "text": "Waktu kerja sebagaimana dimaksud dalam ayat (1) meliputi: a. 7 (tujuh) jam 1 (satu) hari dan 40 (empat puluh) jam 1 (satu) minggu untuk 6 (enam) hari kerja dalam 1 (satu) minggu; atau b. 8 (delapan) jam 1 (satu) hari dan 40 (empat puluh) jam 1 (satu) minggu untuk 5 (lima) hari kerja dalam 1 (satu) minggu."},
        {"bab": "X", "pasal": "78", "ayat": "1", "text": "Pengusaha yang mempekerjakan pekerja/buruh melebihi waktu kerja sebagaimana dimaksud dalam Pasal 77 ayat (2) harus memenuhi syarat: a. ada persetujuan pekerja/buruh yang bersangkutan; dan b. waktu kerja lembur hanya dapat dilakukan paling banyak 3 (tiga) jam dalam 1 (satu) hari dan 14 (empat belas) jam dalam 1 (satu) minggu."},
        {"bab": "X", "pasal": "78", "ayat": "2", "text": "Pengusaha yang mempekerjakan pekerja/buruh melebihi waktu kerja sebagaimana dimaksud dalam ayat (1) wajib membayar upah kerja lembur."},
        {"bab": "X", "pasal": "79", "ayat": "1", "text": "Pengusaha wajib memberi waktu istirahat dan cuti kepada pekerja/buruh."},
        {"bab": "X", "pasal": "79", "ayat": "2", "text": "Waktu istirahat dan cuti sebagaimana dimaksud dalam ayat (1), meliputi: a. istirahat antara jam kerja, sekurang-kurangnya setengah jam setelah bekerja selama 4 (empat) jam terus menerus dan waktu istirahat tersebut tidak termasuk jam kerja; b. istirahat mingguan 1 (satu) hari untuk 6 (enam) hari kerja dalam 1 (satu) minggu atau 2 (dua) hari untuk 5 (lima) hari kerja dalam 1 (satu) minggu; c. cuti tahunan, sekurang-kurangnya 12 (dua belas) hari kerja setelah pekerja/buruh yang bersangkutan bekerja selama 12 (dua belas) bulan secara terus menerus."},
        {"bab": "X", "pasal": "88", "ayat": "1", "text": "Setiap pekerja/buruh berhak memperoleh penghasilan yang memenuhi penghidupan yang layak bagi kemanusiaan."},
        {"bab": "X", "pasal": "89", "ayat": "1", "text": "Upah minimum sebagaimana dimaksud dalam Pasal 88 ayat (3) huruf a terdiri atas: a. upah minimum berdasarkan wilayah provinsi atau kabupaten/kota; b. upah minimum berdasarkan sektor pada wilayah provinsi atau kabupaten/kota."},
        {"bab": "XII", "pasal": "156", "ayat": "1", "text": "Dalam hal terjadi pemutusan hubungan kerja, pengusaha diwajibkan membayar uang pesangon dan atau uang penghargaan masa kerja dan uang penggantian hak yang seharusnya diterima."},
    ]
    
    for art in ketenagakerjaan_articles:
        doc = {
            "jenis_dokumen": "UU",
            "nomor": "13",
            "tahun": 2003,
            "judul": "Ketenagakerjaan",
            "tentang": "Ketenagakerjaan",
            "bab": art.get("bab"),
            "pasal": art["pasal"],
            "text": art["text"]
        }
        if "ayat" in art:
            doc["ayat"] = art["ayat"]
        documents.append(doc)
    
    # === UU 25/2007 - Penanaman Modal ===
    penanaman_modal_articles = [
        {"bab": "I", "pasal": "1", "text": "Dalam Undang-Undang ini yang dimaksud dengan: 1. Penanaman modal adalah segala bentuk kegiatan menanam modal, baik oleh penanam modal dalam negeri maupun penanam modal asing untuk melakukan usaha di wilayah negara Republik Indonesia. 2. Penanaman modal dalam negeri adalah kegiatan menanam modal untuk melakukan usaha di wilayah negara Republik Indonesia yang dilakukan oleh penanam modal dalam negeri dengan menggunakan modal dalam negeri. 3. Penanaman modal asing adalah kegiatan menanam modal untuk melakukan usaha di wilayah negara Republik Indonesia yang dilakukan oleh penanam modal asing, baik yang menggunakan modal asing sepenuhnya maupun yang berpatungan dengan penanam modal dalam negeri."},
        {"bab": "II", "pasal": "3", "ayat": "1", "text": "Penanaman modal diselenggarakan berdasarkan asas: a. kepastian hukum; b. keterbukaan; c. akuntabilitas; d. perlakuan yang sama dan tidak membedakan asal negara; e. kebersamaan; f. efisiensi berkeadilan; g. berkelanjutan; h. berwawasan lingkungan; i. kemandirian; dan j. keseimbangan kemajuan dan kesatuan ekonomi nasional."},
        {"bab": "III", "pasal": "4", "ayat": "1", "text": "Pemerintah menetapkan kebijakan dasar penanaman modal untuk: a. mendorong terciptanya iklim usaha nasional yang kondusif bagi penanaman modal untuk penguatan daya saing perekonomian nasional; dan b. mempercepat peningkatan penanaman modal."},
        {"bab": "III", "pasal": "4", "ayat": "2", "text": "Dalam menetapkan kebijakan dasar sebagaimana dimaksud pada ayat (1), Pemerintah: a. memberi perlakuan yang sama bagi penanam modal dalam negeri dan penanam modal asing dengan tetap memperhatikan kepentingan nasional; b. menjamin kepastian hukum, kepastian berusaha, dan keamanan berusaha bagi penanam modal sejak proses pengurusan perizinan sampai dengan berakhirnya kegiatan penanaman modal sesuai dengan ketentuan peraturan perundang-undangan."},
        {"bab": "V", "pasal": "12", "ayat": "1", "text": "Semua bidang usaha atau jenis usaha terbuka bagi kegiatan penanaman modal, kecuali bidang usaha atau jenis usaha yang dinyatakan tertutup dan terbuka dengan persyaratan."},
        {"bab": "VI", "pasal": "14", "text": "Setiap penanam modal berhak mendapat: a. kepastian hak, hukum, dan perlindungan; b. informasi yang terbuka mengenai bidang usaha yang dijalankannya; c. hak pelayanan; dan d. berbagai bentuk fasilitas kemudahan sesuai dengan ketentuan peraturan perundang-undangan."},
        {"bab": "VI", "pasal": "15", "text": "Setiap penanam modal berkewajiban: a. menerapkan prinsip tata kelola perusahaan yang baik; b. melaksanakan tanggung jawab sosial perusahaan; c. membuat laporan tentang kegiatan penanaman modal dan menyampaikannya kepada Badan Koordinasi Penanaman Modal; d. menghormati tradisi budaya masyarakat sekitar lokasi kegiatan usaha penanaman modal; dan e. mematuhi semua ketentuan peraturan perundang-undangan."},
        {"bab": "VII", "pasal": "18", "ayat": "1", "text": "Pemerintah memberikan fasilitas kepada penanam modal yang melakukan penanaman modal."},
        {"bab": "VII", "pasal": "18", "ayat": "4", "text": "Bentuk fasilitas yang diberikan kepada penanaman modal sebagaimana dimaksud pada ayat (1) dan ayat (2) dapat berupa: a. pajak penghasilan melalui pengurangan penghasilan neto sampai tingkat tertentu terhadap jumlah penanaman modal yang dilakukan dalam waktu tertentu; b. pembebasan atau keringanan bea masuk atas impor barang modal, mesin, atau peralatan untuk keperluan produksi yang belum dapat diproduksi di dalam negeri; c. pembebasan atau keringanan bea masuk bahan baku atau bahan penolong untuk keperluan produksi untuk jangka waktu tertentu dan persyaratan tertentu."},
    ]
    
    for art in penanaman_modal_articles:
        doc = {
            "jenis_dokumen": "UU",
            "nomor": "25",
            "tahun": 2007,
            "judul": "Penanaman Modal",
            "tentang": "Penanaman Modal",
            "bab": art.get("bab"),
            "pasal": art["pasal"],
            "text": art["text"]
        }
        if "ayat" in art:
            doc["ayat"] = art["ayat"]
        documents.append(doc)
    
    # === Perpres 10/2021 - Bidang Usaha Penanaman Modal ===
    perpres10_articles = [
        {"pasal": "1", "text": "Dalam Peraturan Presiden ini yang dimaksud dengan: 1. Bidang usaha adalah sekumpulan kegiatan usaha yang memiliki karakteristik usaha sama dalam menghasilkan suatu barang dan/atau jasa. 2. Penanaman Modal adalah segala bentuk kegiatan menanam modal baik oleh penanam modal dalam negeri maupun penanam modal asing untuk melakukan usaha di wilayah negara Republik Indonesia."},
        {"pasal": "2", "ayat": "1", "text": "Bidang usaha terbuka bagi penanaman modal kecuali bidang usaha yang dinyatakan tertutup untuk penanaman modal atau kegiatan yang hanya dapat dilakukan oleh Pemerintah Pusat."},
        {"pasal": "2", "ayat": "2", "text": "Bidang usaha yang terbuka untuk penanaman modal sebagaimana dimaksud pada ayat (1) terdiri atas: a. bidang usaha prioritas; b. bidang usaha yang dialokasikan atau kemitraan dengan koperasi dan UMKM; c. bidang usaha dengan persyaratan tertentu; dan d. bidang usaha lainnya yang terbuka."},
        {"pasal": "3", "text": "Bidang usaha yang tertutup untuk penanaman modal meliputi: a. budidaya dan industri narkotika golongan I; b. segala bentuk kegiatan perjudian dan/atau kasino; c. penangkapan spesies ikan yang tercantum dalam Appendix I CITES; d. pemanfaatan atau pengambilan koral dan karang dari alam untuk bahan bangunan/kapur/kalsium, akuarium, dan souvenir/perhiasan, serta koral hidup atau koral mati dari alam; e. industri pembuatan senjata kimia; dan f. industri bahan kimia industri dan industri bahan perusak lapisan ozon."},
        {"pasal": "4", "ayat": "1", "text": "Bidang usaha prioritas sebagaimana dimaksud dalam Pasal 2 ayat (2) huruf a merupakan bidang usaha yang mendapat prioritas dan dukungan Pemerintah Pusat."},
        {"pasal": "4", "ayat": "2", "text": "Bidang usaha prioritas sebagaimana dimaksud pada ayat (1) meliputi bidang usaha yang: a. merupakan program/proyek strategis nasional; b. padat modal; c. padat karya; d. teknologi tinggi; e. industri pionir; f. orientasi ekspor; dan/atau g. orientasi dalam kegiatan penelitian, pengembangan, dan inovasi."},
    ]
    
    for art in perpres10_articles:
        doc = {
            "jenis_dokumen": "Perpres",
            "nomor": "10",
            "tahun": 2021,
            "judul": "Bidang Usaha Penanaman Modal",
            "tentang": "Bidang Usaha Penanaman Modal",
            "pasal": art["pasal"],
            "text": art["text"]
        }
        if "ayat" in art:
            doc["ayat"] = art["ayat"]
        documents.append(doc)
    
    # === UU 20/2008 - UMKM ===
    umkm_articles = [
        {"bab": "I", "pasal": "1", "text": "Dalam Undang-Undang ini yang dimaksud dengan: 1. Usaha Mikro adalah usaha produktif milik orang perorangan dan/atau badan usaha perorangan yang memenuhi kriteria Usaha Mikro sebagaimana diatur dalam Undang-Undang ini. 2. Usaha Kecil adalah usaha ekonomi produktif yang berdiri sendiri, yang dilakukan oleh orang perorangan atau badan usaha yang bukan merupakan anak perusahaan atau bukan cabang perusahaan yang dimiliki, dikuasai, atau menjadi bagian baik langsung maupun tidak langsung dari Usaha Menengah atau Usaha Besar yang memenuhi kriteria Usaha Kecil sebagaimana dimaksud dalam Undang-Undang ini. 3. Usaha Menengah adalah usaha ekonomi produktif yang berdiri sendiri, yang dilakukan oleh orang perorangan atau badan usaha yang bukan merupakan anak perusahaan atau cabang perusahaan yang dimiliki, dikuasai, atau menjadi bagian baik langsung maupun tidak langsung dengan Usaha Kecil atau Usaha Besar dengan jumlah kekayaan bersih atau hasil penjualan tahunan sebagaimana diatur dalam Undang-Undang ini."},
        {"bab": "IV", "pasal": "6", "ayat": "1", "text": "Kriteria Usaha Mikro adalah sebagai berikut: a. memiliki kekayaan bersih paling banyak Rp50.000.000,00 (lima puluh juta rupiah) tidak termasuk tanah dan bangunan tempat usaha; atau b. memiliki hasil penjualan tahunan paling banyak Rp300.000.000,00 (tiga ratus juta rupiah)."},
        {"bab": "IV", "pasal": "6", "ayat": "2", "text": "Kriteria Usaha Kecil adalah sebagai berikut: a. memiliki kekayaan bersih lebih dari Rp50.000.000,00 (lima puluh juta rupiah) sampai dengan paling banyak Rp500.000.000,00 (lima ratus juta rupiah) tidak termasuk tanah dan bangunan tempat usaha; atau b. memiliki hasil penjualan tahunan lebih dari Rp300.000.000,00 (tiga ratus juta rupiah) sampai dengan paling banyak Rp2.500.000.000,00 (dua milyar lima ratus juta rupiah)."},
        {"bab": "IV", "pasal": "6", "ayat": "3", "text": "Kriteria Usaha Menengah adalah sebagai berikut: a. memiliki kekayaan bersih lebih dari Rp500.000.000,00 (lima ratus juta rupiah) sampai dengan paling banyak Rp10.000.000.000,00 (sepuluh milyar rupiah) tidak termasuk tanah dan bangunan tempat usaha; atau b. memiliki hasil penjualan tahunan lebih dari Rp2.500.000.000,00 (dua milyar lima ratus juta rupiah) sampai dengan paling banyak Rp50.000.000.000,00 (lima puluh milyar rupiah)."},
        {"bab": "V", "pasal": "7", "ayat": "1", "text": "Pemerintah dan Pemerintah Daerah menumbuhkan Iklim Usaha dengan menetapkan peraturan perundang-undangan dan kebijakan yang meliputi aspek: a. pendanaan; b. sarana dan prasarana; c. informasi usaha; d. kemitraan; e. perizinan usaha; f. kesempatan berusaha; g. promosi dagang; dan h. dukungan kelembagaan."},
        {"bab": "VI", "pasal": "8", "text": "Aspek pendanaan sebagaimana dimaksud dalam Pasal 7 ayat (1) huruf a ditujukan untuk: a. memperluas sumber pendanaan dan memfasilitasi Usaha Mikro, Kecil, dan Menengah untuk dapat mengakses kredit perbankan dan lembaga keuangan bukan bank; b. memperbanyak lembaga pembiayaan dan memperluas jaringannya sehingga dapat diakses oleh Usaha Mikro, Kecil, dan Menengah; c. memberikan kemudahan dalam memperoleh pendanaan secara cepat, tepat, murah, dan tidak diskriminatif dalam pelayanan sesuai dengan ketentuan peraturan perundang-undangan; dan d. membantu para pelaku Usaha Mikro dan Usaha Kecil untuk mendapatkan pembiayaan dan jasa/produk keuangan lainnya yang disediakan oleh perbankan dan lembaga keuangan bukan bank, baik yang menggunakan sistem konvensional maupun sistem syariah dengan jaminan yang disediakan oleh Pemerintah."},
    ]
    
    for art in umkm_articles:
        doc = {
            "jenis_dokumen": "UU",
            "nomor": "20",
            "tahun": 2008,
            "judul": "Usaha Mikro, Kecil, dan Menengah",
            "tentang": "Usaha Mikro, Kecil, dan Menengah (UMKM)",
            "bab": art.get("bab"),
            "pasal": art["pasal"],
            "text": art["text"]
        }
        if "ayat" in art:
            doc["ayat"] = art["ayat"]
        documents.append(doc)
    
    # === Perpres 49/2021 - NIB ===
    perpres49_articles = [
        {"pasal": "1", "text": "Nomor Induk Berusaha yang selanjutnya disingkat NIB adalah bukti registrasi/pendaftaran Pelaku Usaha untuk melakukan kegiatan usaha dan sebagai identitas bagi Pelaku Usaha dalam pelaksanaan kegiatan usahanya."},
        {"pasal": "2", "text": "Setiap Pelaku Usaha yang melakukan kegiatan usaha wajib memiliki NIB."},
        {"pasal": "3", "text": "NIB merupakan identitas pelaku usaha yang diperoleh setelah pelaku usaha melakukan pendaftaran melalui OSS."},
        {"pasal": "4", "text": "NIB berlaku selama pelaku usaha masih menjalankan kegiatan usahanya dan tidak berlaku apabila pelaku usaha melakukan pembubaran atau pembatalan pendiriannya."},
        {"pasal": "5", "ayat": "1", "text": "NIB merupakan identitas berusaha dan digunakan oleh Pelaku Usaha untuk mendapatkan izin usaha dan izin komersial atau operasional."},
        {"pasal": "5", "ayat": "2", "text": "NIB berlaku juga sebagai: a. Tanda Daftar Perusahaan (TDP); b. Angka Pengenal Impor (API); dan c. akses kepabeanan."},
        {"pasal": "6", "text": "Untuk mendapatkan NIB, Pelaku Usaha wajib melakukan pendaftaran melalui sistem OSS dengan mengisi data Pelaku Usaha yang meliputi: a. nama dan/atau Nomor Induk Kependudukan (NIK) bagi Pelaku Usaha perseorangan; b. nama dan/atau nomor pengesahan akta pendirian atau nomor pendaftaran bagi Pelaku Usaha non perseorangan; c. bidang usaha; d. jenis Pelaku Usaha; e. alamat usaha; f. nomor telepon Pelaku Usaha; g. alamat e-mail Pelaku Usaha; h. data penanggung jawab kegiatan usaha; dan i. data lokasi kegiatan usaha."},
    ]
    
    for art in perpres49_articles:
        doc = {
            "jenis_dokumen": "Perpres",
            "nomor": "49",
            "tahun": 2021,
            "judul": "Nomor Induk Berusaha",
            "tentang": "Perubahan atas Peraturan Presiden Nomor 91 Tahun 2017 tentang Percepatan Pelaksanaan Berusaha",
            "pasal": art["pasal"],
            "text": art["text"]
        }
        if "ayat" in art:
            doc["ayat"] = art["ayat"]
        documents.append(doc)
    
    # === UU 8/1999 - Perlindungan Konsumen ===
    konsumen_articles = [
        {"bab": "I", "pasal": "1", "text": "Dalam Undang-undang ini yang dimaksud dengan: 1. Perlindungan konsumen adalah segala upaya yang menjamin adanya kepastian hukum untuk memberi perlindungan kepada konsumen. 2. Konsumen adalah setiap orang pemakai barang dan/atau jasa yang tersedia dalam masyarakat, baik bagi kepentingan diri sendiri, keluarga, orang lain, maupun makhluk hidup lain dan tidak untuk diperdagangkan. 3. Pelaku usaha adalah setiap orang perseorangan atau badan usaha, baik yang berbentuk badan hukum maupun bukan badan hukum yang didirikan dan berkedudukan atau melakukan kegiatan dalam wilayah hukum negara Republik Indonesia, baik sendiri maupun bersama-sama melalui perjanjian menyelenggarakan kegiatan usaha dalam berbagai bidang ekonomi."},
        {"bab": "III", "pasal": "4", "text": "Hak konsumen adalah: a. hak atas kenyamanan, keamanan, dan keselamatan dalam mengkonsumsi barang dan/atau jasa; b. hak untuk memilih barang dan/atau jasa serta mendapatkan barang dan/atau jasa tersebut sesuai dengan nilai tukar dan kondisi serta jaminan yang dijanjikan; c. hak atas informasi yang benar, jelas, dan jujur mengenai kondisi dan jaminan barang dan/atau jasa; d. hak untuk didengar pendapat dan keluhannya atas barang dan/atau jasa yang digunakan; e. hak untuk mendapatkan advokasi, perlindungan, dan upaya penyelesaian sengketa perlindungan konsumen secara patut; f. hak untuk mendapat pembinaan dan pendidikan konsumen; g. hak untuk diperlakukan atau dilayani secara benar dan jujur serta tidak diskriminatif; h. hak untuk mendapatkan kompensasi, ganti rugi dan/atau penggantian, apabila barang dan/atau jasa yang diterima tidak sesuai dengan perjanjian atau tidak sebagaimana mestinya."},
        {"bab": "III", "pasal": "5", "text": "Kewajiban konsumen adalah: a. membaca atau mengikuti petunjuk informasi dan prosedur pemakaian atau pemanfaatan barang dan/atau jasa, demi keamanan dan keselamatan; b. beritikad baik dalam melakukan transaksi pembelian barang dan/atau jasa; c. membayar sesuai dengan nilai tukar yang disepakati; d. mengikuti upaya penyelesaian hukum sengketa perlindungan konsumen secara patut."},
        {"bab": "III", "pasal": "6", "text": "Hak pelaku usaha adalah: a. hak untuk menerima pembayaran yang sesuai dengan kesepakatan mengenai kondisi dan nilai tukar barang dan/atau jasa yang diperdagangkan; b. hak untuk mendapat perlindungan hukum dari tindakan konsumen yang beritikad tidak baik; c. hak untuk melakukan pembelaan diri sepatutnya di dalam penyelesaian hukum sengketa konsumen; d. hak untuk rehabilitasi nama baik apabila terbukti secara hukum bahwa kerugian konsumen tidak diakibatkan oleh barang dan/atau jasa yang diperdagangkan."},
        {"bab": "III", "pasal": "7", "text": "Kewajiban pelaku usaha adalah: a. beritikad baik dalam melakukan kegiatan usahanya; b. memberikan informasi yang benar, jelas dan jujur mengenai kondisi dan jaminan barang dan/atau jasa serta memberi penjelasan penggunaan, perbaikan dan pemeliharaan; c. memperlakukan atau melayani konsumen secara benar dan jujur serta tidak diskriminatif; d. menjamin mutu barang dan/atau jasa yang diproduksi dan/atau diperdagangkan berdasarkan ketentuan standar mutu barang dan/atau jasa yang berlaku; e. memberi kesempatan kepada konsumen untuk menguji, dan/atau mencoba barang dan/atau jasa tertentu serta memberi jaminan dan/atau garansi atas barang yang dibuat dan/atau yang diperdagangkan."},
        {"bab": "IV", "pasal": "8", "ayat": "1", "text": "Pelaku usaha dilarang memproduksi dan/atau memperdagangkan barang dan/atau jasa yang: a. tidak memenuhi atau tidak sesuai dengan standar yang dipersyaratkan dan ketentuan peraturan perundang-undangan; b. tidak sesuai dengan berat bersih, isi bersih atau netto, dan jumlah dalam hitungan sebagaimana yang dinyatakan dalam label atau etiket barang tersebut; c. tidak sesuai dengan ukuran, takaran, timbangan dan jumlah dalam hitungan menurut ukuran yang sebenarnya."},
    ]
    
    for art in konsumen_articles:
        doc = {
            "jenis_dokumen": "UU",
            "nomor": "8",
            "tahun": 1999,
            "judul": "Perlindungan Konsumen",
            "tentang": "Perlindungan Konsumen",
            "bab": art.get("bab"),
            "pasal": art["pasal"],
            "text": art["text"]
        }
        if "ayat" in art:
            doc["ayat"] = art["ayat"]
        documents.append(doc)
    
    # === UU 19/2016 - ITE (Amandemen) ===
    ite_articles = [
        {"bab": "I", "pasal": "1", "text": "Dalam Undang-Undang ini yang dimaksud dengan: 1. Informasi Elektronik adalah satu atau sekumpulan data elektronik, termasuk tetapi tidak terbatas pada tulisan, suara, gambar, peta, rancangan, foto, electronic data interchange (EDI), surat elektronik (electronic mail), telegram, teleks, telecopy atau sejenisnya, huruf, tanda, angka, Kode Akses, simbol, atau perforasi yang telah diolah yang memiliki arti atau dapat dipahami oleh orang yang mampu memahaminya. 2. Transaksi Elektronik adalah perbuatan hukum yang dilakukan dengan menggunakan Komputer, jaringan Komputer, dan/atau media elektronik lainnya. 3. Teknologi Informasi adalah suatu teknik untuk mengumpulkan, menyiapkan, menyimpan, memproses, mengumumkan, menganalisis, dan/atau menyebarkan informasi."},
        {"bab": "II", "pasal": "4", "text": "Pemanfaatan Teknologi Informasi dan Transaksi Elektronik dilaksanakan dengan tujuan untuk: a. mencerdaskan kehidupan bangsa sebagai bagian dari masyarakat informasi dunia; b. mengembangkan perdagangan dan perekonomian nasional dalam rangka meningkatkan kesejahteraan masyarakat; c. meningkatkan efektivitas dan efisiensi pelayanan publik; d. membuka kesempatan seluas-luasnya kepada setiap Orang untuk memajukan pemikiran dan kemampuan di bidang penggunaan dan pemanfaatan Teknologi Informasi seoptimal mungkin dan bertanggung jawab; dan e. memberikan rasa aman, keadilan, dan kepastian hukum bagi pengguna dan penyelenggara Teknologi Informasi."},
        {"bab": "III", "pasal": "5", "ayat": "1", "text": "Informasi Elektronik dan/atau Dokumen Elektronik dan/atau hasil cetaknya merupakan alat bukti hukum yang sah."},
        {"bab": "III", "pasal": "5", "ayat": "2", "text": "Informasi Elektronik dan/atau Dokumen Elektronik dan/atau hasil cetaknya sebagaimana dimaksud pada ayat (1) merupakan perluasan dari alat bukti yang sah sesuai dengan Hukum Acara yang berlaku di Indonesia."},
        {"bab": "VII", "pasal": "27", "ayat": "1", "text": "Setiap Orang dengan sengaja dan tanpa hak mendistribusikan dan/atau mentransmisikan dan/atau membuat dapat diaksesnya Informasi Elektronik dan/atau Dokumen Elektronik yang memiliki muatan yang melanggar kesusilaan."},
        {"bab": "VII", "pasal": "27", "ayat": "3", "text": "Setiap Orang dengan sengaja dan tanpa hak mendistribusikan dan/atau mentransmisikan dan/atau membuat dapat diaksesnya Informasi Elektronik dan/atau Dokumen Elektronik yang memiliki muatan penghinaan dan/atau pencemaran nama baik."},
        {"bab": "VII", "pasal": "28", "ayat": "1", "text": "Setiap Orang dengan sengaja dan tanpa hak menyebarkan berita bohong dan menyesatkan yang mengakibatkan kerugian konsumen dalam Transaksi Elektronik."},
        {"bab": "VII", "pasal": "28", "ayat": "2", "text": "Setiap Orang dengan sengaja dan tanpa hak menyebarkan informasi yang ditujukan untuk menimbulkan rasa kebencian atau permusuhan individu dan/atau kelompok masyarakat tertentu berdasarkan atas suku, agama, ras, dan antargolongan (SARA)."},
        {"bab": "VII", "pasal": "30", "ayat": "1", "text": "Setiap Orang dengan sengaja dan tanpa hak atau melawan hukum mengakses Komputer dan/atau Sistem Elektronik milik Orang lain dengan cara apa pun."},
        {"bab": "VII", "pasal": "30", "ayat": "2", "text": "Setiap Orang dengan sengaja dan tanpa hak atau melawan hukum mengakses Komputer dan/atau Sistem Elektronik dengan cara apa pun dengan tujuan untuk memperoleh Informasi Elektronik dan/atau Dokumen Elektronik."},
        {"bab": "VII", "pasal": "30", "ayat": "3", "text": "Setiap Orang dengan sengaja dan tanpa hak atau melawan hukum mengakses Komputer dan/atau Sistem Elektronik dengan cara apa pun dengan melanggar, menerobos, melampaui, atau menjebol sistem pengamanan."},
    ]
    
    for art in ite_articles:
        doc = {
            "jenis_dokumen": "UU",
            "nomor": "19",
            "tahun": 2016,
            "judul": "Informasi dan Transaksi Elektronik",
            "tentang": "Perubahan atas UU 11/2008 tentang Informasi dan Transaksi Elektronik",
            "bab": art.get("bab"),
            "pasal": art["pasal"],
            "text": art["text"]
        }
        if "ayat" in art:
            doc["ayat"] = art["ayat"]
        documents.append(doc)
    
    # === PP 71/2019 - Penyelenggaraan Sistem dan Transaksi Elektronik ===
    pp71_articles = [
        {"pasal": "1", "text": "Dalam Peraturan Pemerintah ini yang dimaksud dengan: 1. Sistem Elektronik adalah serangkaian perangkat dan prosedur elektronik yang berfungsi mempersiapkan, mengumpulkan, mengolah, menganalisis, menyimpan, menampilkan, mengumumkan, mengirimkan, dan/atau menyebarkan Informasi Elektronik. 2. Penyelenggara Sistem Elektronik adalah setiap Orang, penyelenggara negara, Badan Usaha, dan masyarakat yang menyediakan, mengelola, dan/atau mengoperasikan Sistem Elektronik secara sendiri-sendiri maupun bersama-sama kepada Pengguna Sistem Elektronik untuk keperluan dirinya dan/atau keperluan pihak lain."},
        {"pasal": "3", "ayat": "1", "text": "Setiap Penyelenggara Sistem Elektronik harus menyelenggarakan Sistem Elektronik secara andal dan aman serta bertanggung jawab terhadap beroperasinya Sistem Elektronik sebagaimana mestinya."},
        {"pasal": "3", "ayat": "2", "text": "Penyelenggara Sistem Elektronik bertanggung jawab terhadap penyelenggaraan Sistem Elektroniknya."},
        {"pasal": "4", "text": "Penyelenggara Sistem Elektronik wajib menyelenggarakan Sistem Elektronik yang meliputi: a. memiliki perangkat keras dan perangkat lunak yang handal; b. memiliki prosedur atau petunjuk yang jelas; c. memiliki sistem keamanan yang layak; dan d. memiliki sistem pengamanan Data Pribadi yang sesuai dengan ketentuan peraturan perundang-undangan."},
        {"pasal": "14", "ayat": "1", "text": "Penyelenggara Sistem Elektronik wajib melakukan pendaftaran."},
        {"pasal": "14", "ayat": "2", "text": "Pendaftaran sebagaimana dimaksud pada ayat (1) dilakukan kepada Menteri."},
        {"pasal": "21", "text": "Penyelenggara Sistem Elektronik wajib: a. menjaga kerahasiaan Data Pribadi; b. menjamin bahwa perolehan, penggunaan, dan pemanfaatan Data Pribadi berdasarkan persetujuan pemilik Data Pribadi, kecuali ditentukan lain berdasarkan ketentuan peraturan perundang-undangan; dan c. menjamin penggunaan atau pengungkapan Data Pribadi dilakukan berdasarkan persetujuan dari pemilik Data Pribadi tersebut dan sesuai dengan tujuan yang disampaikan kepada pemilik Data Pribadi pada saat perolehan data."},
        {"pasal": "26", "ayat": "1", "text": "Penyelenggara Sistem Elektronik wajib melakukan penyimpanan Data Elektronik."},
        {"pasal": "26", "ayat": "2", "text": "Penyimpanan Data Elektronik sebagaimana dimaksud pada ayat (1) dapat dilakukan: a. di dalam negeri; dan/atau b. di luar negeri."},
    ]
    
    for art in pp71_articles:
        doc = {
            "jenis_dokumen": "PP",
            "nomor": "71",
            "tahun": 2019,
            "judul": "Penyelenggaraan Sistem dan Transaksi Elektronik",
            "tentang": "Penyelenggaraan Sistem dan Transaksi Elektronik",
            "pasal": art["pasal"],
            "text": art["text"]
        }
        if "ayat" in art:
            doc["ayat"] = art["ayat"]
        documents.append(doc)
    
    # === UU 36/2009 - Kesehatan ===
    kesehatan_articles = [
        {"bab": "I", "pasal": "1", "text": "Dalam Undang-Undang ini yang dimaksud dengan: 1. Kesehatan adalah keadaan sehat, baik secara fisik, mental, spiritual maupun sosial yang memungkinkan setiap orang untuk hidup produktif secara sosial dan ekonomis. 2. Sumber daya di bidang kesehatan adalah segala bentuk dana, tenaga, perbekalan kesehatan, sediaan farmasi dan alat kesehatan serta fasilitas pelayanan kesehatan dan teknologi yang dimanfaatkan untuk menyelenggarakan upaya kesehatan yang dilakukan oleh Pemerintah, pemerintah daerah, dan/atau masyarakat. 3. Tenaga kesehatan adalah setiap orang yang mengabdikan diri dalam bidang kesehatan serta memiliki pengetahuan dan/atau keterampilan melalui pendidikan di bidang kesehatan."},
        {"bab": "II", "pasal": "2", "text": "Pembangunan kesehatan diselenggarakan dengan berasaskan perikemanusiaan, keseimbangan, manfaat, pelindungan, penghormatan terhadap hak dan kewajiban, keadilan, gender dan nondiskriminatif dan norma-norma agama."},
        {"bab": "II", "pasal": "3", "text": "Pembangunan kesehatan bertujuan untuk meningkatkan kesadaran, kemauan, dan kemampuan hidup sehat bagi setiap orang agar terwujud derajat kesehatan masyarakat yang setinggi-tingginya, sebagai investasi bagi pembangunan sumber daya manusia yang produktif secara sosial dan ekonomis."},
        {"bab": "III", "pasal": "4", "text": "Setiap orang berhak atas kesehatan."},
        {"bab": "III", "pasal": "5", "ayat": "1", "text": "Setiap orang mempunyai hak yang sama dalam memperoleh akses atas sumber daya di bidang kesehatan."},
        {"bab": "III", "pasal": "5", "ayat": "2", "text": "Setiap orang mempunyai hak dalam memperoleh pelayanan kesehatan yang aman, bermutu, dan terjangkau."},
        {"bab": "III", "pasal": "5", "ayat": "3", "text": "Setiap orang berhak secara mandiri dan bertanggung jawab menentukan sendiri pelayanan kesehatan yang diperlukan bagi dirinya."},
        {"bab": "V", "pasal": "30", "ayat": "1", "text": "Fasilitas pelayanan kesehatan menurut jenis pelayanannya terdiri atas: a. pelayanan kesehatan perseorangan; dan b. pelayanan kesehatan masyarakat."},
        {"bab": "V", "pasal": "30", "ayat": "2", "text": "Fasilitas pelayanan kesehatan sebagaimana dimaksud pada ayat (1) meliputi: a. pelayanan kesehatan tingkat pertama; b. pelayanan kesehatan tingkat kedua; dan c. pelayanan kesehatan tingkat ketiga."},
        {"bab": "V", "pasal": "36", "ayat": "1", "text": "Setiap tenaga kesehatan yang melakukan praktik di bidang pelayanan kesehatan wajib memiliki izin praktik sesuai dengan ketentuan peraturan perundang-undangan."},
    ]
    
    for art in kesehatan_articles:
        doc = {
            "jenis_dokumen": "UU",
            "nomor": "36",
            "tahun": 2009,
            "judul": "Kesehatan",
            "tentang": "Kesehatan",
            "bab": art.get("bab"),
            "pasal": art["pasal"],
            "text": art["text"]
        }
        if "ayat" in art:
            doc["ayat"] = art["ayat"]
        documents.append(doc)
    
    # === UU 32/2009 - Perlindungan dan Pengelolaan Lingkungan Hidup ===
    lingkungan_articles = [
        {"bab": "I", "pasal": "1", "text": "Dalam Undang-Undang ini yang dimaksud dengan: 1. Lingkungan hidup adalah kesatuan ruang dengan semua benda, daya, keadaan, dan makhluk hidup, termasuk manusia dan perilakunya, yang mempengaruhi alam itu sendiri, kelangsungan perikehidupan, dan kesejahteraan manusia serta makhluk hidup lain. 2. Perlindungan dan pengelolaan lingkungan hidup adalah upaya sistematis dan terpadu yang dilakukan untuk melestarikan fungsi lingkungan hidup dan mencegah terjadinya pencemaran dan/atau kerusakan lingkungan hidup. 3. Pembangunan berkelanjutan adalah upaya sadar dan terencana yang memadukan aspek lingkungan hidup, sosial, dan ekonomi ke dalam strategi pembangunan."},
        {"bab": "I", "pasal": "1", "ayat": "11", "text": "Analisis mengenai dampak lingkungan hidup, yang selanjutnya disebut Amdal, adalah kajian mengenai dampak penting suatu usaha dan/atau kegiatan yang direncanakan pada lingkungan hidup yang diperlukan bagi proses pengambilan keputusan tentang penyelenggaraan usaha dan/atau kegiatan."},
        {"bab": "III", "pasal": "22", "ayat": "1", "text": "Setiap usaha dan/atau kegiatan yang berdampak penting terhadap lingkungan hidup wajib memiliki Amdal."},
        {"bab": "III", "pasal": "22", "ayat": "2", "text": "Dampak penting ditentukan berdasarkan kriteria: a. besarnya jumlah penduduk yang akan terkena dampak rencana usaha dan/atau kegiatan; b. luas wilayah penyebaran dampak; c. intensitas dan lamanya dampak berlangsung; d. banyaknya komponen lingkungan hidup lain yang akan terkena dampak; e. sifat kumulatif dampak; f. berbalik atau tidak berbaliknya dampak; dan/atau g. kriteria lain sesuai dengan perkembangan ilmu pengetahuan dan teknologi."},
        {"bab": "III", "pasal": "34", "ayat": "1", "text": "Setiap usaha dan/atau kegiatan yang tidak termasuk dalam kriteria wajib Amdal wajib memiliki upaya pengelolaan lingkungan hidup dan upaya pemantauan lingkungan hidup (UKL-UPL)."},
        {"bab": "V", "pasal": "36", "ayat": "1", "text": "Setiap usaha dan/atau kegiatan yang wajib memiliki Amdal atau UKL-UPL wajib memiliki izin lingkungan."},
        {"bab": "V", "pasal": "36", "ayat": "2", "text": "Izin lingkungan sebagaimana dimaksud pada ayat (1) diterbitkan berdasarkan keputusan kelayakan lingkungan hidup atau rekomendasi UKL-UPL."},
        {"bab": "X", "pasal": "65", "ayat": "1", "text": "Setiap orang berhak atas lingkungan hidup yang baik dan sehat sebagai bagian dari hak asasi manusia."},
        {"bab": "XII", "pasal": "87", "ayat": "1", "text": "Setiap penanggung jawab usaha dan/atau kegiatan yang melakukan perbuatan melanggar hukum berupa pencemaran dan/atau perusakan lingkungan hidup yang menimbulkan kerugian pada orang lain atau lingkungan hidup wajib membayar ganti rugi dan/atau melakukan tindakan tertentu."},
        {"bab": "XV", "pasal": "98", "ayat": "1", "text": "Setiap orang yang dengan sengaja melakukan perbuatan yang mengakibatkan dilampauinya baku mutu udara ambien, baku mutu air, baku mutu air laut, atau kriteria baku kerusakan lingkungan hidup, dipidana dengan pidana penjara paling singkat 3 (tiga) tahun dan paling lama 10 (sepuluh) tahun dan denda paling sedikit Rp3.000.000.000,00 (tiga miliar rupiah) dan paling banyak Rp10.000.000.000,00 (sepuluh miliar rupiah)."},
    ]
    
    for art in lingkungan_articles:
        doc = {
            "jenis_dokumen": "UU",
            "nomor": "32",
            "tahun": 2009,
            "judul": "Perlindungan dan Pengelolaan Lingkungan Hidup",
            "tentang": "Perlindungan dan Pengelolaan Lingkungan Hidup",
            "bab": art.get("bab"),
            "pasal": art["pasal"],
            "text": art["text"]
        }
        if "ayat" in art:
            doc["ayat"] = art["ayat"]
        documents.append(doc)
    
    # === UU 5/1960 - Pokok-Pokok Agraria (UUPA) ===
    agraria_articles = [
        {"bab": "I", "pasal": "2", "ayat": "1", "text": "Atas dasar ketentuan dalam pasal 33 ayat (3) Undang-undang Dasar dan hal-hal sebagai yang dimaksud dalam pasal 1, bumi, air dan ruang angkasa, termasuk kekayaan alam yang terkandung didalamnya itu pada tingkatan tertinggi dikuasai oleh Negara, sebagai organisasi kekuasaan seluruh rakyat."},
        {"bab": "I", "pasal": "4", "ayat": "1", "text": "Atas dasar hak menguasai dari Negara sebagai yang dimaksud dalam pasal 2 ditentukan adanya macam-macam hak atas permukaan bumi, yang disebut tanah, yang dapat diberikan kepada dan dipunyai oleh orang-orang baik sendiri maupun bersama-sama dengan orang lain serta badan-badan hukum."},
        {"bab": "II", "pasal": "16", "ayat": "1", "text": "Hak-hak atas tanah sebagai yang dimaksud dalam pasal 4 ayat (1) ialah: a. hak milik; b. hak guna-usaha; c. hak guna-bangunan; d. hak pakai; e. hak sewa; f. hak membuka tanah; g. hak memungut-hasil hutan; h. hak-hak lain yang tidak termasuk dalam hak-hak tersebut diatas yang akan ditetapkan dengan undang-undang serta hak-hak yang sifatnya sementara sebagai yang disebutkan dalam pasal 53."},
        {"bab": "II", "pasal": "20", "ayat": "1", "text": "Hak milik adalah hak turun-temurun, terkuat dan terpenuh yang dapat dipunyai orang atas tanah, dengan mengingat ketentuan dalam pasal 6."},
        {"bab": "II", "pasal": "20", "ayat": "2", "text": "Hak milik dapat beralih dan dialihkan kepada pihak lain."},
        {"bab": "II", "pasal": "28", "ayat": "1", "text": "Hak guna-usaha adalah hak untuk mengusahakan tanah yang dikuasai langsung oleh Negara, dalam jangka waktu sebagaimana tersebut dalam pasal 29, guna perusahaan pertanian, perikanan atau peternakan."},
        {"bab": "II", "pasal": "35", "ayat": "1", "text": "Hak guna-bangunan adalah hak untuk mendirikan dan mempunyai bangunan-bangunan atas tanah yang bukan miliknya sendiri, dengan jangka waktu paling lama 30 tahun."},
        {"bab": "II", "pasal": "41", "ayat": "1", "text": "Hak pakai adalah hak untuk menggunakan dan/atau memungut hasil dari tanah yang dikuasai langsung oleh Negara atau tanah milik orang lain, yang memberi wewenang dan kewajiban yang ditentukan dalam keputusan pemberiannya oleh pejabat yang berwenang memberikannya atau dalam perjanjian dengan pemilik tanahnya."},
    ]
    
    for art in agraria_articles:
        doc = {
            "jenis_dokumen": "UU",
            "nomor": "5",
            "tahun": 1960,
            "judul": "Peraturan Dasar Pokok-Pokok Agraria",
            "tentang": "Peraturan Dasar Pokok-Pokok Agraria",
            "bab": art.get("bab"),
            "pasal": art["pasal"],
            "text": art["text"]
        }
        if "ayat" in art:
            doc["ayat"] = art["ayat"]
        documents.append(doc)
    
    # === UU 28/2007 - Ketentuan Umum dan Tata Cara Perpajakan (KUP) ===
    kup_articles = [
        {"pasal": "1", "text": "Dalam Undang-Undang ini yang dimaksud dengan: 1. Pajak adalah kontribusi wajib kepada negara yang terutang oleh orang pribadi atau badan yang bersifat memaksa berdasarkan Undang-Undang, dengan tidak mendapatkan imbalan secara langsung dan digunakan untuk keperluan negara bagi sebesar-besarnya kemakmuran rakyat. 2. Wajib Pajak adalah orang pribadi atau badan, meliputi pembayar pajak, pemotong pajak, dan pemungut pajak, yang mempunyai hak dan kewajiban perpajakan sesuai dengan ketentuan peraturan perundang-undangan perpajakan."},
        {"pasal": "2", "ayat": "1", "text": "Setiap Wajib Pajak yang telah memenuhi persyaratan subjektif dan objektif sesuai dengan ketentuan peraturan perundang-undangan perpajakan wajib mendaftarkan diri pada kantor Direktorat Jenderal Pajak yang wilayah kerjanya meliputi tempat tinggal atau tempat kedudukan Wajib Pajak dan kepadanya diberikan Nomor Pokok Wajib Pajak (NPWP)."},
        {"pasal": "2", "ayat": "2", "text": "Setiap Wajib Pajak sebagai Pengusaha yang dikenai pajak berdasarkan Undang-Undang Pajak Pertambahan Nilai 1984 dan perubahannya, wajib melaporkan usahanya pada kantor Direktorat Jenderal Pajak untuk dikukuhkan sebagai Pengusaha Kena Pajak (PKP)."},
        {"pasal": "3", "ayat": "1", "text": "Setiap Wajib Pajak wajib mengisi Surat Pemberitahuan (SPT) dengan benar, lengkap, dan jelas, dalam bahasa Indonesia dengan menggunakan huruf Latin, angka Arab, satuan mata uang Rupiah, dan menandatangani serta menyampaikannya ke kantor Direktorat Jenderal Pajak tempat Wajib Pajak terdaftar atau dikukuhkan."},
        {"pasal": "3", "ayat": "3", "text": "Batas waktu penyampaian Surat Pemberitahuan adalah: a. untuk Surat Pemberitahuan Masa, paling lama 20 (dua puluh) hari setelah akhir Masa Pajak; b. untuk Surat Pemberitahuan Tahunan Pajak Penghasilan Wajib Pajak orang pribadi, paling lama 3 (tiga) bulan setelah akhir Tahun Pajak; c. untuk Surat Pemberitahuan Tahunan Pajak Penghasilan Wajib Pajak badan, paling lama 4 (empat) bulan setelah akhir Tahun Pajak."},
        {"pasal": "7", "ayat": "1", "text": "Apabila Surat Pemberitahuan tidak disampaikan dalam jangka waktu sebagaimana dimaksud dalam Pasal 3 ayat (3) atau batas waktu perpanjangan penyampaian Surat Pemberitahuan, dikenai sanksi administrasi berupa denda sebesar Rp500.000,00 (lima ratus ribu rupiah) untuk Surat Pemberitahuan Masa Pajak Pertambahan Nilai, Rp100.000,00 (seratus ribu rupiah) untuk Surat Pemberitahuan Masa lainnya, dan Rp1.000.000,00 (satu juta rupiah) untuk Surat Pemberitahuan Tahunan Pajak Penghasilan Wajib Pajak badan serta Rp100.000,00 (seratus ribu rupiah) untuk Surat Pemberitahuan Tahunan Pajak Penghasilan Wajib Pajak orang pribadi."},
        {"pasal": "9", "ayat": "1", "text": "Menteri Keuangan menentukan tanggal jatuh tempo pembayaran dan penyetoran pajak yang terutang untuk suatu saat atau Masa Pajak bagi masing-masing jenis pajak, paling lama 15 (lima belas) hari setelah saat terutangnya pajak atau berakhirnya Masa Pajak."},
        {"pasal": "9", "ayat": "2a", "text": "Pembayaran atau penyetoran pajak yang dilakukan setelah tanggal jatuh tempo pembayaran atau penyetoran pajak, dikenai sanksi administrasi berupa bunga sebesar 2% (dua persen) per bulan yang dihitung dari tanggal jatuh tempo pembayaran sampai dengan tanggal pembayaran."},
        {"pasal": "13", "ayat": "1", "text": "Dalam jangka waktu 5 (lima) tahun setelah saat terutangnya pajak atau berakhirnya Masa Pajak, bagian Tahun Pajak, atau Tahun Pajak, Direktur Jenderal Pajak dapat menerbitkan Surat Ketetapan Pajak Kurang Bayar."},
        {"pasal": "38", "text": "Setiap orang yang karena kealpaannya tidak menyampaikan Surat Pemberitahuan atau menyampaikan Surat Pemberitahuan, tetapi isinya tidak benar atau tidak lengkap, atau melampirkan keterangan yang isinya tidak benar sehingga dapat menimbulkan kerugian pada pendapatan negara dan perbuatan tersebut merupakan perbuatan setelah perbuatan yang pertama kali, dipidana dengan pidana denda paling sedikit 1 (satu) kali jumlah pajak terutang yang tidak atau kurang dibayar dan paling banyak 2 (dua) kali jumlah pajak terutang yang tidak atau kurang dibayar, atau dipidana kurungan paling singkat 3 (tiga) bulan atau paling lama 1 (satu) tahun."},
    ]
    
    for art in kup_articles:
        doc = {
            "jenis_dokumen": "UU",
            "nomor": "28",
            "tahun": 2007,
            "judul": "Ketentuan Umum dan Tata Cara Perpajakan",
            "tentang": "Perubahan Ketiga atas UU 6/1983 tentang Ketentuan Umum dan Tata Cara Perpajakan",
            "pasal": art["pasal"],
            "text": art["text"]
        }
        if "ayat" in art:
            doc["ayat"] = art["ayat"]
        documents.append(doc)
    
    # === UU 7/2021 - Harmonisasi Peraturan Perpajakan (HPP) ===
    hpp_articles = [
        {"pasal": "2", "text": "Undang-Undang ini mengatur mengenai: a. Pajak Penghasilan; b. Pajak Pertambahan Nilai; c. Ketentuan Umum dan Tata Cara Perpajakan; d. Program Pengungkapan Sukarela Wajib Pajak; e. Pajak Karbon; dan f. Cukai."},
        {"pasal": "3", "ayat": "1", "text": "Nomor Induk Kependudukan (NIK) bagi Wajib Pajak orang pribadi yang merupakan penduduk Indonesia dan Nomor Pokok Wajib Pajak bagi Wajib Pajak orang pribadi bukan penduduk, Wajib Pajak badan, dan Wajib Pajak instansi pemerintah digunakan sebagai Nomor Pokok Wajib Pajak (NPWP)."},
        {"pasal": "7", "ayat": "1", "text": "Tarif Pajak Penghasilan yang diterapkan atas Penghasilan Kena Pajak bagi Wajib Pajak orang pribadi dalam negeri adalah sebagai berikut: a. sampai dengan Rp60.000.000,00 (enam puluh juta rupiah) dikenai tarif sebesar 5% (lima persen); b. di atas Rp60.000.000,00 (enam puluh juta rupiah) sampai dengan Rp250.000.000,00 (dua ratus lima puluh juta rupiah) dikenai tarif sebesar 15% (lima belas persen); c. di atas Rp250.000.000,00 sampai dengan Rp500.000.000,00 dikenai tarif sebesar 25%; d. di atas Rp500.000.000,00 sampai dengan Rp5.000.000.000,00 dikenai tarif sebesar 30%; e. di atas Rp5.000.000.000,00 dikenai tarif sebesar 35%."},
        {"pasal": "7", "ayat": "1a", "text": "Tarif sebagaimana dimaksud pada ayat (1) diterapkan terhadap Penghasilan Kena Pajak yang dihitung dari penghasilan bruto dikurangi Penghasilan Tidak Kena Pajak (PTKP) dan biaya-biaya yang diperkenankan."},
        {"pasal": "7", "ayat": "1b", "text": "Wajib Pajak badan dalam negeri dan bentuk usaha tetap dikenai tarif sebesar 22% (dua puluh dua persen) yang mulai berlaku pada Tahun Pajak 2022."},
        {"pasal": "13", "ayat": "1", "text": "Tarif Pajak Pertambahan Nilai (PPN) yaitu: a. sebesar 11% (sebelas persen) yang mulai berlaku pada tanggal 1 April 2022; b. sebesar 12% (dua belas persen) yang mulai berlaku paling lambat pada tanggal 1 Januari 2025."},
        {"pasal": "13", "ayat": "2", "text": "Tarif Pajak Pertambahan Nilai sebesar 0% (nol persen) diterapkan atas: a. ekspor Barang Kena Pajak Berwujud; b. ekspor Barang Kena Pajak Tidak Berwujud; dan c. ekspor Jasa Kena Pajak."},
        {"pasal": "44", "ayat": "1", "text": "Pajak karbon dikenakan atas emisi karbon yang memberikan dampak negatif bagi lingkungan hidup."},
        {"pasal": "44", "ayat": "2", "text": "Pajak karbon terutang atas pembelian barang yang mengandung karbon dan/atau aktivitas yang menghasilkan emisi karbon dalam jumlah tertentu pada periode tertentu."},
    ]
    
    for art in hpp_articles:
        doc = {
            "jenis_dokumen": "UU",
            "nomor": "7",
            "tahun": 2021,
            "judul": "Harmonisasi Peraturan Perpajakan",
            "tentang": "Harmonisasi Peraturan Perpajakan",
            "pasal": art["pasal"],
            "text": art["text"]
        }
        if "ayat" in art:
            doc["ayat"] = art["ayat"]
        documents.append(doc)
    
    # === PP 35/2021 - PKWT, Alih Daya, Waktu Kerja, dan PHK ===
    pp35_articles = [
        {"pasal": "1", "text": "Dalam Peraturan Pemerintah ini yang dimaksud dengan: 1. Perjanjian Kerja Waktu Tertentu yang selanjutnya disingkat PKWT adalah perjanjian kerja antara pekerja/buruh dengan pengusaha untuk mengadakan hubungan kerja dalam waktu tertentu atau untuk pekerjaan tertentu. 2. Perjanjian Kerja Waktu Tidak Tertentu yang selanjutnya disingkat PKWTT adalah perjanjian kerja antara pekerja/buruh dengan pengusaha untuk mengadakan hubungan kerja yang bersifat tetap. 3. Alih Daya adalah penyerahan sebagian pelaksanaan pekerjaan kepada perusahaan lain melalui perjanjian pemborongan pekerjaan atau penyediaan jasa pekerja/buruh."},
        {"pasal": "4", "ayat": "1", "text": "PKWT didasarkan atas: a. jangka waktu; atau b. selesainya suatu pekerjaan tertentu."},
        {"pasal": "5", "ayat": "1", "text": "PKWT berdasarkan jangka waktu sebagaimana dimaksud dalam Pasal 4 ayat (1) huruf a dibuat untuk pekerjaan yang diperkirakan penyelesaiannya dalam waktu yang tidak terlalu lama."},
        {"pasal": "8", "text": "Jangka waktu atau selesainya pekerjaan tertentu dalam PKWT berdasarkan jangka waktu paling lama 5 (lima) tahun termasuk jika terdapat perpanjangan."},
        {"pasal": "15", "ayat": "1", "text": "Pengusaha yang mengakhiri hubungan kerja terhadap pekerja/buruh PKWT wajib memberikan uang kompensasi."},
        {"pasal": "15", "ayat": "2", "text": "Uang kompensasi sebagaimana dimaksud pada ayat (1) diberikan kepada pekerja/buruh yang telah mempunyai masa kerja paling sedikit 1 (satu) bulan secara terus menerus."},
        {"pasal": "15", "ayat": "3", "text": "Besaran uang kompensasi dihitung berdasarkan masa kerja pekerja/buruh dan diberikan proporsional sesuai dengan masa kerja."},
        {"pasal": "18", "ayat": "1", "text": "Hubungan kerja dalam alih daya dilaksanakan berdasarkan PKWT atau PKWTT yang dibuat secara tertulis dan didaftarkan pada instansi yang bertanggung jawab di bidang ketenagakerjaan."},
        {"pasal": "21", "ayat": "1", "text": "Waktu kerja sebagaimana dimaksud dalam Pasal 20 meliputi: a. 7 (tujuh) jam 1 (satu) hari dan 40 (empat puluh) jam 1 (satu) minggu untuk 6 (enam) hari kerja dalam 1 (satu) minggu; atau b. 8 (delapan) jam 1 (satu) hari dan 40 (empat puluh) jam 1 (satu) minggu untuk 5 (lima) hari kerja dalam 1 (satu) minggu."},
        {"pasal": "40", "ayat": "1", "text": "Dalam hal terjadi pemutusan hubungan kerja, pengusaha wajib membayar uang pesangon dan/atau uang penghargaan masa kerja dan uang penggantian hak yang seharusnya diterima."},
        {"pasal": "40", "ayat": "2", "text": "Uang pesangon sebagaimana dimaksud pada ayat (1) diberikan dengan ketentuan: a. masa kerja kurang dari 1 tahun: 1 bulan upah; b. masa kerja 1 tahun atau lebih tetapi kurang dari 2 tahun: 2 bulan upah; c. masa kerja 2 tahun atau lebih tetapi kurang dari 3 tahun: 3 bulan upah; d. masa kerja 3 tahun atau lebih tetapi kurang dari 4 tahun: 4 bulan upah; e. masa kerja 4 tahun atau lebih tetapi kurang dari 5 tahun: 5 bulan upah; f. masa kerja 5 tahun atau lebih tetapi kurang dari 6 tahun: 6 bulan upah; g. masa kerja 6 tahun atau lebih tetapi kurang dari 7 tahun: 7 bulan upah; h. masa kerja 7 tahun atau lebih tetapi kurang dari 8 tahun: 8 bulan upah; i. masa kerja 8 tahun atau lebih: 9 bulan upah."},
    ]
    
    for art in pp35_articles:
        doc = {
            "jenis_dokumen": "PP",
            "nomor": "35",
            "tahun": 2021,
            "judul": "PKWT, Alih Daya, Waktu Kerja, dan PHK",
            "tentang": "Perjanjian Kerja Waktu Tertentu, Alih Daya, Waktu Kerja dan Waktu Istirahat, dan Pemutusan Hubungan Kerja",
            "pasal": art["pasal"],
            "text": art["text"]
        }
        if "ayat" in art:
            doc["ayat"] = art["ayat"]
        documents.append(doc)
    
    # === Perpres 12/2021 - Pengadaan Barang/Jasa Pemerintah ===
    perpres12_articles = [
        {"pasal": "1", "text": "Dalam Peraturan Presiden ini yang dimaksud dengan: 1. Pengadaan Barang/Jasa Pemerintah yang selanjutnya disebut Pengadaan Barang/Jasa adalah kegiatan Pengadaan Barang/Jasa oleh Kementerian/Lembaga/Perangkat Daerah yang dibiayai oleh APBN/APBD yang prosesnya sejak identifikasi kebutuhan, sampai dengan serah terima hasil pekerjaan. 2. Pengguna Anggaran yang selanjutnya disingkat PA adalah pejabat pemegang kewenangan penggunaan anggaran Kementerian/Lembaga/Perangkat Daerah."},
        {"pasal": "3", "ayat": "1", "text": "Pengadaan Barang/Jasa dilaksanakan dengan prinsip: a. efisien; b. efektif; c. transparan; d. terbuka; e. bersaing; f. adil; dan g. akuntabel."},
        {"pasal": "4", "text": "Pengadaan Barang/Jasa bertujuan untuk: a. menghasilkan barang/jasa yang tepat dari setiap uang yang dibelanjakan, diukur dari aspek kualitas, jumlah, waktu, biaya, lokasi, dan penyedia; b. meningkatkan penggunaan produksi dalam negeri; c. meningkatkan peran serta Usaha Mikro, Usaha Kecil, dan Usaha Menengah; d. meningkatkan peran pelaku usaha nasional; e. mendukung pelaksanaan penelitian dan pemanfaatan barang/jasa hasil penelitian."},
        {"pasal": "38", "ayat": "1", "text": "Metode pemilihan Penyedia Barang/Pekerjaan Konstruksi/Jasa Lainnya terdiri atas: a. Tender; b. Seleksi; c. Penunjukan Langsung; d. Pengadaan Langsung; dan e. e-purchasing."},
        {"pasal": "44", "text": "Pengadaan Langsung dilaksanakan untuk Barang/Pekerjaan Konstruksi/Jasa Lainnya yang bernilai paling banyak Rp200.000.000,00 (dua ratus juta rupiah) dan untuk Jasa Konsultansi yang bernilai paling banyak Rp100.000.000,00 (seratus juta rupiah)."},
        {"pasal": "65", "ayat": "1", "text": "Kementerian/Lembaga/Perangkat Daerah mengumumkan rencana Pengadaan Barang/Jasa pada tahun anggaran berjalan melalui aplikasi Sistem Informasi Rencana Umum Pengadaan (SiRUP)."},
        {"pasal": "70", "ayat": "1", "text": "Pelaku Usaha yang akan menjadi Penyedia wajib melakukan registrasi pada aplikasi Sistem Pengadaan Secara Elektronik (SPSE) dan memenuhi kualifikasi sesuai dengan barang/jasa yang diadakan."},
    ]
    
    for art in perpres12_articles:
        doc = {
            "jenis_dokumen": "Perpres",
            "nomor": "12",
            "tahun": 2021,
            "judul": "Pengadaan Barang/Jasa Pemerintah",
            "tentang": "Perubahan atas Perpres 16/2018 tentang Pengadaan Barang/Jasa Pemerintah",
            "pasal": art["pasal"],
            "text": art["text"]
        }
        if "ayat" in art:
            doc["ayat"] = art["ayat"]
        documents.append(doc)
    
    # === UU 31/1999 - Pemberantasan Tindak Pidana Korupsi ===
    antikorupsi_articles = [
        {"bab": "I", "pasal": "1", "text": "Dalam Undang-Undang ini yang dimaksud dengan: 1. Korporasi adalah kumpulan orang dan/atau kekayaan yang terorganisasi baik merupakan badan hukum maupun bukan badan hukum. 2. Pegawai Negeri meliputi pegawai negeri sebagaimana dimaksud dalam Undang-Undang tentang Kepegawaian, pegawai negeri sebagaimana dimaksud dalam KUHP, orang yang menerima gaji atau upah dari keuangan negara atau daerah, serta orang yang menerima gaji atau upah dari suatu korporasi yang mempergunakan modal atau fasilitas dari negara atau masyarakat."},
        {"bab": "II", "pasal": "2", "ayat": "1", "text": "Setiap orang yang secara melawan hukum melakukan perbuatan memperkaya diri sendiri atau orang lain atau suatu korporasi yang dapat merugikan keuangan negara atau perekonomian negara, dipidana penjara dengan penjara seumur hidup atau pidana penjara paling singkat 4 (empat) tahun dan paling lama 20 (dua puluh) tahun dan denda paling sedikit Rp200.000.000,00 (dua ratus juta rupiah) dan paling banyak Rp1.000.000.000,00 (satu miliar rupiah)."},
        {"bab": "II", "pasal": "3", "text": "Setiap orang yang dengan tujuan menguntungkan diri sendiri atau orang lain atau suatu korporasi, menyalahgunakan kewenangan, kesempatan atau sarana yang ada padanya karena jabatan atau kedudukan yang dapat merugikan keuangan negara atau perekonomian negara, dipidana dengan pidana penjara seumur hidup atau pidana penjara paling singkat 1 (satu) tahun dan paling lama 20 (dua puluh) tahun dan/atau denda paling sedikit Rp50.000.000,00 (lima puluh juta rupiah) dan paling banyak Rp1.000.000.000,00 (satu miliar rupiah)."},
        {"bab": "II", "pasal": "5", "ayat": "1", "text": "Dipidana dengan pidana penjara paling singkat 1 (satu) tahun dan paling lama 5 (lima) tahun dan/atau pidana denda paling sedikit Rp50.000.000,00 (lima puluh juta rupiah) dan paling banyak Rp250.000.000,00 (dua ratus lima puluh juta rupiah) setiap orang yang: a. memberi atau menjanjikan sesuatu kepada pegawai negeri atau penyelenggara negara dengan maksud supaya pegawai negeri atau penyelenggara negara tersebut berbuat atau tidak berbuat sesuatu dalam jabatannya, yang bertentangan dengan kewajibannya; atau b. memberi sesuatu kepada pegawai negeri atau penyelenggara negara karena atau berhubungan dengan sesuatu yang bertentangan dengan kewajiban, dilakukan atau tidak dilakukan dalam jabatannya."},
        {"bab": "II", "pasal": "6", "ayat": "1", "text": "Dipidana dengan pidana penjara paling singkat 3 (tiga) tahun dan paling lama 15 (lima belas) tahun dan pidana denda paling sedikit Rp150.000.000,00 (seratus lima puluh juta rupiah) dan paling banyak Rp750.000.000,00 (tujuh ratus lima puluh juta rupiah) setiap orang yang memberi atau menjanjikan sesuatu kepada hakim dengan maksud untuk mempengaruhi putusan perkara yang diserahkan kepadanya untuk diadili."},
        {"bab": "II", "pasal": "8", "text": "Dipidana dengan pidana penjara paling singkat 3 (tiga) tahun dan paling lama 15 (lima belas) tahun dan pidana denda paling sedikit Rp150.000.000,00 (seratus lima puluh juta rupiah) dan paling banyak Rp750.000.000,00 (tujuh ratus lima puluh juta rupiah) pegawai negeri atau orang selain pegawai negeri yang ditugaskan menjalankan suatu jabatan umum secara terus menerus atau untuk sementara waktu, dengan sengaja menggelapkan uang atau surat berharga yang disimpan karena jabatannya, atau membiarkan uang atau surat berharga tersebut diambil atau digelapkan oleh orang lain."},
        {"bab": "II", "pasal": "9", "text": "Pegawai negeri atau orang selain pegawai negeri yang diberi tugas menjalankan suatu jabatan umum secara terus menerus atau untuk sementara waktu, dengan sengaja memalsu buku-buku atau daftar-daftar yang khusus untuk pemeriksaan administrasi, dipidana dengan pidana penjara paling singkat 1 (satu) tahun dan paling lama 5 (lima) tahun dan pidana denda paling sedikit Rp50.000.000,00 (lima puluh juta rupiah) dan paling banyak Rp250.000.000,00 (dua ratus lima puluh juta rupiah)."},
        {"bab": "II", "pasal": "12B", "ayat": "1", "text": "Setiap gratifikasi kepada pegawai negeri atau penyelenggara negara dianggap pemberian suap, apabila berhubungan dengan jabatannya dan yang berlawanan dengan kewajiban atau tugasnya, dengan ketentuan: a. yang nilainya Rp10.000.000,00 (sepuluh juta rupiah) atau lebih, pembuktian bahwa gratifikasi tersebut bukan merupakan suap dilakukan oleh penerima gratifikasi; b. yang nilainya kurang dari Rp10.000.000,00 (sepuluh juta rupiah), pembuktian bahwa gratifikasi tersebut suap dilakukan oleh penuntut umum."},
        {"bab": "II", "pasal": "12C", "ayat": "1", "text": "Ketentuan sebagaimana dimaksud dalam Pasal 12B ayat (1) tidak berlaku, jika penerima melaporkan gratifikasi yang diterimanya kepada Komisi Pemberantasan Tindak Pidana Korupsi paling lambat 30 (tiga puluh) hari kerja terhitung sejak tanggal gratifikasi tersebut diterima."},
        {"bab": "III", "pasal": "18", "ayat": "1", "text": "Selain pidana tambahan sebagaimana dimaksud dalam Kitab Undang-Undang Hukum Pidana, sebagai pidana tambahan adalah: a. perampasan barang bergerak yang berwujud atau yang tidak berwujud atau barang tidak bergerak yang digunakan untuk atau yang diperoleh dari tindak pidana korupsi, termasuk perusahaan milik terpidana; b. pembayaran uang pengganti yang jumlahnya sebanyak-banyaknya sama dengan harta benda yang diperoleh dari tindak pidana korupsi; c. penutupan seluruh atau sebagian perusahaan untuk waktu paling lama 1 (satu) tahun; d. pencabutan seluruh atau sebagian hak-hak tertentu atau penghapusan seluruh atau sebagian keuntungan tertentu."},
    ]
    
    for art in antikorupsi_articles:
        doc = {
            "jenis_dokumen": "UU",
            "nomor": "31",
            "tahun": 1999,
            "judul": "Pemberantasan Tindak Pidana Korupsi",
            "tentang": "Pemberantasan Tindak Pidana Korupsi",
            "bab": art.get("bab"),
            "pasal": art["pasal"],
            "text": art["text"]
        }
        if "ayat" in art:
            doc["ayat"] = art["ayat"]
        documents.append(doc)
    
    # === UU 5/1999 - Larangan Praktek Monopoli dan Persaingan Usaha Tidak Sehat ===
    antimonopoli_articles = [
        {"bab": "I", "pasal": "1", "text": "Dalam Undang-Undang ini yang dimaksud dengan: 1. Monopoli adalah penguasaan atas produksi dan/atau pemasaran barang dan/atau atas penggunaan jasa tertentu oleh satu pelaku usaha atau satu kelompok pelaku usaha. 2. Praktek Monopoli adalah pemusatan kekuatan ekonomi oleh satu atau lebih pelaku usaha yang mengakibatkan dikuasainya produksi dan/atau pemasaran atas barang dan/atau jasa tertentu sehingga menimbulkan persaingan usaha tidak sehat dan dapat merugikan kepentingan umum. 3. Persaingan Usaha Tidak Sehat adalah persaingan antar pelaku usaha dalam menjalankan kegiatan produksi dan/atau pemasaran barang dan/atau jasa yang dilakukan dengan cara tidak jujur atau melawan hukum atau menghambat persaingan usaha."},
        {"bab": "III", "pasal": "4", "ayat": "1", "text": "Pelaku usaha dilarang membuat perjanjian dengan pelaku usaha lain untuk secara bersama-sama melakukan penguasaan produksi dan/atau pemasaran barang dan/atau jasa yang dapat mengakibatkan terjadinya praktek monopoli dan/atau persaingan usaha tidak sehat."},
        {"bab": "III", "pasal": "5", "ayat": "1", "text": "Pelaku usaha dilarang membuat perjanjian dengan pelaku usaha pesaingnya untuk menetapkan harga atas suatu barang dan/atau jasa yang harus dibayar oleh konsumen atau pelanggan pada pasar bersangkutan yang sama."},
        {"bab": "III", "pasal": "9", "text": "Pelaku usaha dilarang membuat perjanjian dengan pelaku usaha pesaingnya yang bertujuan untuk membagi wilayah pemasaran atau alokasi pasar terhadap barang dan/atau jasa sehingga dapat mengakibatkan terjadinya praktek monopoli dan/atau persaingan usaha tidak sehat."},
        {"bab": "III", "pasal": "11", "text": "Pelaku usaha dilarang membuat perjanjian dengan pelaku usaha pesaingnya yang bermaksud untuk mempengaruhi harga dengan mengatur produksi dan/atau pemasaran suatu barang dan/atau jasa, yang dapat mengakibatkan terjadinya praktek monopoli dan/atau persaingan usaha tidak sehat."},
        {"bab": "IV", "pasal": "17", "ayat": "1", "text": "Pelaku usaha dilarang melakukan penguasaan atas produksi dan/atau pemasaran barang dan/atau jasa yang dapat mengakibatkan terjadinya praktek monopoli dan/atau persaingan usaha tidak sehat."},
        {"bab": "IV", "pasal": "19", "text": "Pelaku usaha dilarang melakukan satu atau beberapa kegiatan, baik sendiri maupun bersama pelaku usaha lain, yang dapat mengakibatkan terjadinya praktek monopoli dan/atau persaingan usaha tidak sehat berupa: a. menolak dan/atau menghalangi pelaku usaha tertentu untuk melakukan kegiatan usaha yang sama pada pasar bersangkutan; b. menghalangi konsumen atau pelanggan pelaku usaha pesaingnya untuk tidak melakukan hubungan usaha dengan pelaku usaha pesaingnya itu."},
        {"bab": "V", "pasal": "25", "ayat": "1", "text": "Pelaku usaha dilarang menggunakan posisi dominan baik secara langsung maupun tidak langsung untuk: a. menetapkan syarat-syarat perdagangan dengan tujuan untuk mencegah dan/atau menghalangi konsumen memperoleh barang dan/atau jasa yang bersaing; b. membatasi pasar dan pengembangan teknologi; atau c. menghambat pelaku usaha lain yang berpotensi menjadi pesaing untuk memasuki pasar bersangkutan."},
        {"bab": "V", "pasal": "28", "ayat": "1", "text": "Pelaku usaha dilarang melakukan penggabungan atau peleburan badan usaha yang dapat mengakibatkan terjadinya praktek monopoli dan/atau persaingan usaha tidak sehat."},
        {"bab": "VIII", "pasal": "47", "ayat": "1", "text": "Komisi berwenang menjatuhkan tindakan administratif terhadap pelaku usaha yang melanggar ketentuan Undang-Undang ini."},
        {"bab": "VIII", "pasal": "47", "ayat": "2", "text": "Tindakan administratif sebagaimana dimaksud dalam ayat (1) dapat berupa: a. penetapan pembatalan perjanjian; b. perintah kepada pelaku usaha untuk menghentikan integrasi vertikal; c. perintah kepada pelaku usaha untuk menghentikan kegiatan yang terbukti menimbulkan praktek monopoli; d. penetapan pembayaran ganti rugi; e. pengenaan denda serendah-rendahnya Rp1.000.000.000,00 (satu miliar rupiah) dan setinggi-tingginya Rp25.000.000.000,00 (dua puluh lima miliar rupiah)."},
    ]
    
    for art in antimonopoli_articles:
        doc = {
            "jenis_dokumen": "UU",
            "nomor": "5",
            "tahun": 1999,
            "judul": "Larangan Praktek Monopoli dan Persaingan Usaha Tidak Sehat",
            "tentang": "Larangan Praktek Monopoli dan Persaingan Usaha Tidak Sehat",
            "bab": art.get("bab"),
            "pasal": art["pasal"],
            "text": art["text"]
        }
        if "ayat" in art:
            doc["ayat"] = art["ayat"]
        documents.append(doc)
    
    # === UU 10/1998 - Perbankan ===
    perbankan_articles = [
        {"bab": "I", "pasal": "1", "text": "Dalam Undang-Undang ini yang dimaksud dengan: 1. Perbankan adalah segala sesuatu yang menyangkut tentang bank, mencakup kelembagaan, kegiatan usaha, serta cara dan proses dalam melaksanakan kegiatan usahanya. 2. Bank adalah badan usaha yang menghimpun dana dari masyarakat dalam bentuk simpanan dan menyalurkannya kepada masyarakat dalam bentuk kredit dan/atau bentuk-bentuk lainnya dalam rangka meningkatkan taraf hidup rakyat banyak. 3. Bank Umum adalah bank yang melaksanakan kegiatan usaha secara konvensional dan/atau berdasarkan Prinsip Syariah yang dalam kegiatannya memberikan jasa dalam lalu lintas pembayaran. 4. Bank Perkreditan Rakyat adalah bank yang melaksanakan kegiatan usaha secara konvensional atau berdasarkan Prinsip Syariah yang dalam kegiatannya tidak memberikan jasa dalam lalu lintas pembayaran."},
        {"bab": "III", "pasal": "5", "ayat": "1", "text": "Menurut jenisnya, bank terdiri dari: a. Bank Umum; dan b. Bank Perkreditan Rakyat."},
        {"bab": "IV", "pasal": "10", "text": "Bank Umum dilarang: a. melakukan penyertaan modal, kecuali sebagaimana dimaksud dalam Pasal 7 huruf b dan huruf c; b. melakukan usaha perasuransian; c. melakukan usaha lain di luar kegiatan usaha sebagaimana dimaksud dalam Pasal 6 dan Pasal 7."},
        {"bab": "IV", "pasal": "16", "ayat": "1", "text": "Setiap pihak yang melakukan kegiatan menghimpun dana dari masyarakat dalam bentuk simpanan wajib terlebih dahulu memperoleh izin usaha sebagai Bank Umum atau Bank Perkreditan Rakyat dari Pimpinan Bank Indonesia, kecuali apabila kegiatan menghimpun dana dari masyarakat dimaksud diatur dengan Undang-Undang tersendiri."},
        {"bab": "V", "pasal": "22", "ayat": "1", "text": "Bank Umum hanya dapat didirikan oleh: a. warga negara Indonesia dan/atau badan hukum Indonesia; atau b. warga negara Indonesia dan/atau badan hukum Indonesia dengan warga negara asing dan/atau badan hukum asing secara kemitraan."},
        {"bab": "VII", "pasal": "29", "ayat": "1", "text": "Pembinaan dan pengawasan bank dilakukan oleh Bank Indonesia."},
        {"bab": "VII", "pasal": "29", "ayat": "2", "text": "Bank wajib memelihara tingkat kesehatan bank sesuai dengan ketentuan kecukupan modal, kualitas aset, kualitas manajemen, likuiditas, rentabilitas, solvabilitas, dan aspek lain yang berhubungan dengan usaha bank."},
        {"bab": "VII", "pasal": "40", "ayat": "1", "text": "Bank wajib merahasiakan keterangan mengenai Nasabah Penyimpan dan simpanannya, kecuali dalam hal sebagaimana dimaksud dalam Pasal 41, Pasal 41A, Pasal 42, Pasal 43, dan Pasal 44A."},
        {"bab": "VII", "pasal": "42", "ayat": "1", "text": "Untuk kepentingan pemeriksaan dalam perkara pidana, Pimpinan Bank Indonesia dapat memberikan izin kepada polisi, jaksa, atau hakim untuk memperoleh keterangan dari bank mengenai simpanan tersangka atau terdakwa pada bank."},
    ]
    
    for art in perbankan_articles:
        doc = {
            "jenis_dokumen": "UU",
            "nomor": "10",
            "tahun": 1998,
            "judul": "Perbankan",
            "tentang": "Perubahan atas Undang-Undang Nomor 7 Tahun 1992 tentang Perbankan",
            "bab": art.get("bab"),
            "pasal": art["pasal"],
            "text": art["text"]
        }
        if "ayat" in art:
            doc["ayat"] = art["ayat"]
        documents.append(doc)
    
    # === UU 8/1995 - Pasar Modal ===
    pasar_modal_articles = [
        {"bab": "I", "pasal": "1", "text": "Dalam Undang-Undang ini yang dimaksud dengan: 1. Pasar Modal adalah kegiatan yang bersangkutan dengan Penawaran Umum dan perdagangan Efek, Perusahaan Publik yang berkaitan dengan Efek yang diterbitkannya, serta lembaga dan profesi yang berkaitan dengan Efek. 2. Efek adalah surat berharga, yaitu surat pengakuan utang, surat berharga komersial, saham, obligasi, tanda bukti utang, Unit Penyertaan kontrak investasi kolektif, kontrak berjangka atas Efek, dan setiap derivatif dari Efek. 3. Bursa Efek adalah Pihak yang menyelenggarakan dan menyediakan sistem dan/atau sarana untuk mempertemukan penawaran jual dan beli Efek Pihak-Pihak lain dengan tujuan memperdagangkan Efek di antara mereka."},
        {"bab": "VI", "pasal": "70", "ayat": "1", "text": "Yang dapat melakukan Penawaran Umum hanyalah Emiten yang telah menyampaikan Pernyataan Pendaftaran kepada Badan Pengawas Pasar Modal untuk menawarkan atau menjual Efek kepada masyarakat dan Pernyataan Pendaftaran tersebut telah efektif."},
        {"bab": "VI", "pasal": "73", "text": "Setiap Pihak dilarang menawarkan atau menjual Efek dalam Penawaran Umum, kecuali pembeli atau pemesan telah menerima atau berkesempatan membaca Prospektus berkenaan dengan Efek yang bersangkutan sebelum atau pada saat pemesanan dilakukan."},
        {"bab": "VIII", "pasal": "86", "ayat": "1", "text": "Emiten yang Pernyataan Pendaftarannya telah menjadi efektif atau Perusahaan Publik wajib: a. menyampaikan laporan secara berkala kepada Badan Pengawas Pasar Modal dan mengumumkan laporan tersebut kepada masyarakat; dan b. menyampaikan laporan kepada Badan Pengawas Pasar Modal dan mengumumkan kepada masyarakat tentang peristiwa material yang dapat mempengaruhi harga Efek selambat-lambatnya pada akhir hari kerja ke-2 (kedua) setelah terjadinya peristiwa tersebut."},
        {"bab": "IX", "pasal": "91", "text": "Setiap Pihak dilarang melakukan tindakan, baik langsung maupun tidak langsung, dengan tujuan untuk menciptakan gambaran semu atau menyesatkan mengenai kegiatan perdagangan, keadaan pasar, atau harga Efek di Bursa Efek."},
        {"bab": "IX", "pasal": "92", "text": "Setiap Pihak, baik sendiri-sendiri maupun bersama-sama dengan Pihak lain, dilarang melakukan 2 (dua) transaksi Efek atau lebih, baik langsung maupun tidak langsung, sehingga menyebabkan harga Efek di Bursa Efek tetap, naik, atau turun dengan tujuan mempengaruhi Pihak lain untuk membeli, menjual, atau menahan Efek."},
        {"bab": "IX", "pasal": "95", "text": "Orang dalam dari Emiten atau Perusahaan Publik yang mempunyai informasi orang dalam dilarang melakukan pembelian atau penjualan atas Efek: a. Emiten atau Perusahaan Publik dimaksud; atau b. perusahaan lain yang melakukan transaksi dengan Emiten atau Perusahaan Publik yang bersangkutan."},
        {"bab": "IX", "pasal": "97", "text": "Setiap Pihak yang berusaha untuk memperoleh informasi orang dalam dari orang dalam secara melawan hukum dan kemudian memperolehnya dikenakan larangan yang sama dengan larangan yang berlaku bagi orang dalam sebagaimana dimaksud dalam Pasal 95 dan Pasal 96."},
        {"bab": "XV", "pasal": "104", "text": "Setiap Pihak yang melanggar ketentuan sebagaimana dimaksud dalam Pasal 90, Pasal 91, Pasal 92, Pasal 93, Pasal 95, Pasal 96, Pasal 97 ayat (1), dan Pasal 98 diancam dengan pidana penjara paling lama 10 (sepuluh) tahun dan denda paling banyak Rp15.000.000.000,00 (lima belas miliar rupiah)."},
    ]
    
    for art in pasar_modal_articles:
        doc = {
            "jenis_dokumen": "UU",
            "nomor": "8",
            "tahun": 1995,
            "judul": "Pasar Modal",
            "tentang": "Pasar Modal",
            "bab": art.get("bab"),
            "pasal": art["pasal"],
            "text": art["text"]
        }
        if "ayat" in art:
            doc["ayat"] = art["ayat"]
        documents.append(doc)
    
    # === UU 28/2014 - Hak Cipta ===
    hak_cipta_articles = [
        {"bab": "I", "pasal": "1", "text": "Dalam Undang-Undang ini yang dimaksud dengan: 1. Hak Cipta adalah hak eksklusif pencipta yang timbul secara otomatis berdasarkan prinsip deklaratif setelah suatu ciptaan diwujudkan dalam bentuk nyata tanpa mengurangi pembatasan sesuai dengan ketentuan peraturan perundang-undangan. 2. Pencipta adalah seorang atau beberapa orang yang secara sendiri-sendiri atau bersama-sama menghasilkan suatu ciptaan yang bersifat khas dan pribadi. 3. Ciptaan adalah setiap hasil karya cipta di bidang ilmu pengetahuan, seni, dan sastra yang dihasilkan atas inspirasi, kemampuan, pikiran, imajinasi, kecekatan, keterampilan, atau keahlian yang diekspresikan dalam bentuk nyata."},
        {"bab": "II", "pasal": "5", "ayat": "1", "text": "Hak moral sebagaimana dimaksud dalam Pasal 4 merupakan hak yang melekat secara abadi pada diri Pencipta untuk: a. tetap mencantumkan atau tidak mencantumkan namanya pada salinan sehubungan dengan pemakaian Ciptaannya untuk umum; b. menggunakan nama aliasnya atau samarannya; c. mengubah Ciptaannya sesuai dengan kepatutan dalam masyarakat; d. mengubah judul dan anak judul Ciptaan; dan e. mempertahankan haknya dalam hal terjadi distorsi Ciptaan, mutilasi Ciptaan, modifikasi Ciptaan, atau hal yang bersifat merugikan kehormatan diri atau reputasinya."},
        {"bab": "II", "pasal": "8", "text": "Hak ekonomi merupakan hak eksklusif Pencipta atau Pemegang Hak Cipta untuk mendapatkan manfaat ekonomi atas Ciptaan."},
        {"bab": "II", "pasal": "9", "ayat": "1", "text": "Pencipta atau Pemegang Hak Cipta sebagaimana dimaksud dalam Pasal 8 memiliki hak ekonomi untuk melakukan: a. penerbitan Ciptaan; b. penggandaan Ciptaan dalam segala bentuknya; c. penerjemahan Ciptaan; d. pengadaptasian, pengaransemenan, atau pentransformasian Ciptaan; e. pendistribusian Ciptaan atau salinannya; f. pertunjukan Ciptaan; g. pengumuman Ciptaan; h. komunikasi Ciptaan; dan i. penyewaan Ciptaan."},
        {"bab": "V", "pasal": "40", "ayat": "1", "text": "Ciptaan yang dilindungi meliputi Ciptaan dalam bidang ilmu pengetahuan, seni, dan sastra, terdiri atas: a. buku, pamflet, perwajahan karya tulis yang diterbitkan, dan semua hasil karya tulis lainnya; b. ceramah, kuliah, pidato, dan Ciptaan sejenis lainnya; c. alat peraga yang dibuat untuk kepentingan pendidikan dan ilmu pengetahuan; d. lagu dan/atau musik dengan atau tanpa teks; e. drama, drama musikal, tari, koreografi, pewayangan, dan pantomim; f. karya seni rupa dalam segala bentuk seperti lukisan, gambar, ukiran, kaligrafi, seni pahat, patung, atau kolase; g. karya arsitektur; h. peta; i. karya seni batik atau seni motif lain; j. karya fotografi; k. potret; l. karya sinematografi; m. terjemahan, tafsir, saduran, bunga rampai, basis data, adaptasi, aransemen, modifikasi dan karya lain dari hasil transformasi; n. kompilasi Ciptaan atau data; o. kompilasi ekspresi budaya tradisional; p. permainan video; dan q. program Komputer."},
        {"bab": "V", "pasal": "43", "text": "Perbuatan yang tidak dianggap sebagai pelanggaran Hak Cipta meliputi: a. pengumuman, pendistribusian, komunikasi, dan/atau penggandaan lambang negara dan lagu kebangsaan menurut sifatnya yang asli; b. pengumuman, pendistribusian, komunikasi, dan/atau penggandaan segala sesuatu yang dilaksanakan oleh atau atas nama pemerintah; c. pengambilan berita aktual, baik seluruhnya maupun sebagian dari kantor berita, Lembaga Penyiaran, dan surat kabar atau sumber sejenis lainnya dengan ketentuan sumbernya harus disebutkan secara lengkap."},
        {"bab": "VII", "pasal": "58", "ayat": "1", "text": "Pelindungan Hak Cipta atas Ciptaan: a. buku, pamflet, dan semua hasil karya tulis lainnya; b. ceramah, kuliah, pidato, dan Ciptaan sejenis lainnya; c. alat peraga yang dibuat untuk kepentingan pendidikan dan ilmu pengetahuan; d. lagu dan/atau musik dengan atau tanpa teks; e. drama, drama musikal, tari, koreografi, pewayangan, dan pantomim; f. karya seni rupa dalam segala bentuk; dan g. karya arsitektur, berlaku selama hidup Pencipta dan terus berlangsung selama 70 (tujuh puluh) tahun setelah Pencipta meninggal dunia, terhitung mulai tanggal 1 Januari tahun berikutnya."},
        {"bab": "X", "pasal": "80", "ayat": "1", "text": "Kecuali diperjanjikan lain, pemegang Hak Cipta atau pemilik Hak Terkait berhak memberikan Lisensi kepada pihak lain berdasarkan perjanjian tertulis untuk melaksanakan perbuatan sebagaimana dimaksud dalam Pasal 9 ayat (1), Pasal 23 ayat (2), Pasal 24 ayat (2), dan Pasal 25 ayat (2)."},
        {"bab": "XVII", "pasal": "113", "ayat": "3", "text": "Setiap Orang yang dengan tanpa hak dan/atau tanpa izin Pencipta atau pemegang Hak Cipta melakukan pelanggaran hak ekonomi Pencipta sebagaimana dimaksud dalam Pasal 9 ayat (1) huruf a, huruf b, huruf e, dan/atau huruf g untuk Penggunaan Secara Komersial dipidana dengan pidana penjara paling lama 4 (empat) tahun dan/atau pidana denda paling banyak Rp1.000.000.000,00 (satu miliar rupiah)."},
    ]
    
    for art in hak_cipta_articles:
        doc = {
            "jenis_dokumen": "UU",
            "nomor": "28",
            "tahun": 2014,
            "judul": "Hak Cipta",
            "tentang": "Hak Cipta",
            "bab": art.get("bab"),
            "pasal": art["pasal"],
            "text": art["text"]
        }
        if "ayat" in art:
            doc["ayat"] = art["ayat"]
        documents.append(doc)
    
    # === UU 13/2016 - Paten ===
    paten_articles = [
        {"bab": "I", "pasal": "1", "text": "Dalam Undang-Undang ini yang dimaksud dengan: 1. Paten adalah hak eksklusif yang diberikan oleh negara kepada inventor atas hasil invensinya di bidang teknologi untuk jangka waktu tertentu melaksanakan sendiri invensi tersebut atau memberikan persetujuan kepada pihak lain untuk melaksanakannya. 2. Invensi adalah ide inventor yang dituangkan ke dalam suatu kegiatan pemecahan masalah yang spesifik di bidang teknologi berupa produk atau proses, atau penyempurnaan dan pengembangan produk atau proses. 3. Inventor adalah seorang atau beberapa orang yang secara bersama-sama melaksanakan ide yang dituangkan ke dalam kegiatan yang menghasilkan Invensi."},
        {"bab": "II", "pasal": "2", "ayat": "1", "text": "Pelindungan Paten diberikan untuk Invensi yang baru, mengandung langkah inventif, dan dapat diterapkan dalam industri."},
        {"bab": "II", "pasal": "3", "ayat": "1", "text": "Paten sederhana diberikan untuk setiap Invensi baru berupa pengembangan dari produk atau proses yang telah ada dan dapat diterapkan dalam industri."},
        {"bab": "II", "pasal": "4", "text": "Invensi dianggap baru sebagaimana dimaksud dalam Pasal 2 ayat (1) jika pada Tanggal Penerimaan, Invensi tersebut tidak sama dengan teknologi yang diungkapkan sebelumnya. Teknologi yang diungkapkan sebelumnya mencakup dokumen Permohonan yang diajukan di Indonesia dan di luar negeri."},
        {"bab": "II", "pasal": "9", "text": "Invensi yang tidak dapat diberi Paten meliputi: a. proses atau produk yang pengumuman, penggunaan, atau pelaksanaannya bertentangan dengan peraturan perundang-undangan, agama, ketertiban umum, atau kesusilaan; b. metode pemeriksaan, perawatan, pengobatan dan/atau pembedahan yang diterapkan terhadap manusia dan/atau hewan; c. teori dan metode di bidang ilmu pengetahuan dan matematika; d. makhluk hidup, kecuali jasad renik; atau e. proses biologis yang esensial untuk memproduksi tanaman atau hewan, kecuali proses nonbiologis atau proses mikrobiologis."},
        {"bab": "III", "pasal": "22", "ayat": "1", "text": "Paten diberikan untuk jangka waktu 20 (dua puluh) tahun terhitung sejak Tanggal Penerimaan. Jangka waktu sebagaimana dimaksud tidak dapat diperpanjang."},
        {"bab": "III", "pasal": "22", "ayat": "2", "text": "Paten sederhana diberikan untuk jangka waktu 10 (sepuluh) tahun terhitung sejak Tanggal Penerimaan. Jangka waktu sebagaimana dimaksud tidak dapat diperpanjang."},
        {"bab": "IX", "pasal": "82", "ayat": "1", "text": "Lisensi wajib merupakan Lisensi untuk melaksanakan Paten yang diberikan berdasarkan keputusan Menteri atas dasar permohonan dengan alasan: a. Pemegang Paten tidak melaksanakan kewajiban untuk membuat produk atau menggunakan proses di Indonesia sebagaimana dimaksud dalam Pasal 20 dalam jangka waktu 36 (tiga puluh enam) bulan setelah diberikan Paten; b. Paten telah dilaksanakan oleh Pemegang Paten atau penerima Lisensi dalam bentuk dan dengan cara yang merugikan kepentingan masyarakat; atau c. Paten hasil pengembangan dari Paten yang telah diberikan sebelumnya tidak dapat dilaksanakan tanpa menggunakan Paten pihak lain yang masih dalam pelindungan."},
    ]
    
    for art in paten_articles:
        doc = {
            "jenis_dokumen": "UU",
            "nomor": "13",
            "tahun": 2016,
            "judul": "Paten",
            "tentang": "Paten",
            "bab": art.get("bab"),
            "pasal": art["pasal"],
            "text": art["text"]
        }
        if "ayat" in art:
            doc["ayat"] = art["ayat"]
        documents.append(doc)
    
    # === UU 20/2016 - Merek dan Indikasi Geografis ===
    merek_articles = [
        {"bab": "I", "pasal": "1", "text": "Dalam Undang-Undang ini yang dimaksud dengan: 1. Merek adalah tanda yang dapat ditampilkan secara grafis berupa gambar, logo, nama, kata, huruf, angka, susunan warna, dalam bentuk 2 (dua) dimensi dan/atau 3 (tiga) dimensi, suara, hologram, atau kombinasi dari 2 (dua) atau lebih unsur tersebut untuk membedakan barang dan/atau jasa yang diproduksi oleh orang atau badan hukum dalam kegiatan perdagangan barang dan/atau jasa. 2. Merek Dagang adalah Merek yang digunakan pada barang yang diperdagangkan oleh seseorang atau beberapa orang secara bersama-sama atau badan hukum untuk membedakan dengan barang sejenis lainnya. 3. Merek Jasa adalah Merek yang digunakan pada jasa yang diperdagangkan oleh seseorang atau beberapa orang secara bersama-sama atau badan hukum untuk membedakan dengan jasa sejenis lainnya."},
        {"bab": "II", "pasal": "3", "text": "Hak atas Merek diperoleh setelah Merek tersebut terdaftar. Pendaftaran Merek sebagaimana dimaksud dilakukan oleh Menteri yang menyelenggarakan urusan pemerintahan di bidang hukum."},
        {"bab": "III", "pasal": "4", "ayat": "1", "text": "Permohonan pendaftaran Merek diajukan oleh Pemohon atau Kuasanya kepada Menteri secara elektronik atau nonelektronik dalam bahasa Indonesia."},
        {"bab": "III", "pasal": "20", "text": "Merek tidak dapat didaftar jika: a. bertentangan dengan ideologi negara, peraturan perundang-undangan, moralitas, agama, kesusilaan, atau ketertiban umum; b. sama dengan, berkaitan dengan, atau hanya menyebut barang dan/atau jasa yang dimohonkan pendaftarannya; c. memuat unsur yang dapat menyesatkan masyarakat tentang asal, kualitas, jenis, ukuran, macam, tujuan penggunaan barang dan/atau jasa yang dimohonkan pendaftarannya atau merupakan nama varietas tanaman yang dilindungi untuk barang dan/atau jasa yang sejenis; d. memuat keterangan yang tidak sesuai dengan kualitas, manfaat, atau khasiat dari barang dan/atau jasa yang diproduksi; e. tidak memiliki daya pembeda; dan/atau f. merupakan nama umum dan/atau lambang milik umum."},
        {"bab": "III", "pasal": "21", "ayat": "1", "text": "Permohonan ditolak jika Merek tersebut mempunyai persamaan pada pokoknya atau keseluruhannya dengan: a. Merek terdaftar milik pihak lain atau dimohonkan lebih dahulu oleh pihak lain untuk barang dan/atau jasa sejenis; b. Merek terkenal milik pihak lain untuk barang dan/atau jasa sejenis; c. Merek terkenal milik pihak lain untuk barang dan/atau jasa tidak sejenis yang memenuhi persyaratan tertentu; atau d. Indikasi Geografis terdaftar."},
        {"bab": "V", "pasal": "35", "ayat": "1", "text": "Merek terdaftar mendapat pelindungan hukum untuk jangka waktu 10 (sepuluh) tahun sejak Tanggal Penerimaan."},
        {"bab": "V", "pasal": "35", "ayat": "2", "text": "Jangka waktu pelindungan sebagaimana dimaksud pada ayat (1) dapat diperpanjang untuk jangka waktu yang sama setiap kali perpanjangan dengan membayar biaya."},
        {"bab": "XIV", "pasal": "100", "ayat": "1", "text": "Setiap Orang yang dengan tanpa hak menggunakan Merek yang sama pada keseluruhannya dengan Merek terdaftar milik pihak lain untuk barang dan/atau jasa sejenis yang diproduksi dan/atau diperdagangkan, dipidana dengan pidana penjara paling lama 5 (lima) tahun dan/atau pidana denda paling banyak Rp2.000.000.000,00 (dua miliar rupiah)."},
    ]
    
    for art in merek_articles:
        doc = {
            "jenis_dokumen": "UU",
            "nomor": "20",
            "tahun": 2016,
            "judul": "Merek dan Indikasi Geografis",
            "tentang": "Merek dan Indikasi Geografis",
            "bab": art.get("bab"),
            "pasal": art["pasal"],
            "text": art["text"]
        }
        if "ayat" in art:
            doc["ayat"] = art["ayat"]
        documents.append(doc)
    
    # === UU 37/2004 - Kepailitan dan PKPU ===
    kepailitan_articles = [
        {"bab": "I", "pasal": "1", "text": "Dalam Undang-Undang ini yang dimaksud dengan: 1. Kepailitan adalah sita umum atas semua kekayaan Debitor Pailit yang pengurusan dan pemberesannya dilakukan oleh Kurator di bawah pengawasan Hakim Pengawas sebagaimana diatur dalam Undang-Undang ini. 2. Kreditor adalah orang yang mempunyai piutang karena perjanjian atau Undang-Undang yang dapat ditagih di muka pengadilan. 3. Debitor adalah orang yang mempunyai utang karena perjanjian atau undang-undang yang pelunasannya dapat ditagih di muka pengadilan. 4. Kurator adalah Balai Harta Peninggalan atau orang perseorangan yang diangkat oleh Pengadilan untuk mengurus dan membereskan harta Debitor Pailit di bawah pengawasan Hakim Pengawas."},
        {"bab": "II", "pasal": "2", "ayat": "1", "text": "Debitor yang mempunyai dua atau lebih Kreditor dan tidak membayar lunas sedikitnya satu utang yang telah jatuh waktu dan dapat ditagih, dinyatakan pailit dengan putusan Pengadilan, baik atas permohonannya sendiri maupun atas permohonan satu atau lebih kreditornya."},
        {"bab": "II", "pasal": "6", "ayat": "1", "text": "Permohonan pernyataan pailit diajukan kepada Ketua Pengadilan Niaga yang daerah hukumnya meliputi daerah tempat kedudukan hukum Debitor."},
        {"bab": "II", "pasal": "7", "ayat": "1", "text": "Permohonan pernyataan pailit harus diajukan oleh seorang advokat kecuali apabila permohonan diajukan oleh kejaksaan, Bank Indonesia, Badan Pengawas Pasar Modal, atau Menteri Keuangan."},
        {"bab": "II", "pasal": "15", "ayat": "1", "text": "Dalam putusan pernyataan pailit, harus diangkat Kurator dan seorang Hakim Pengawas yang ditunjuk dari hakim Pengadilan. Dalam hal Debitor, Kreditor, atau pihak yang berwenang mengajukan permohonan pernyataan pailit tidak mengajukan usul pengangkatan Kurator kepada Pengadilan, maka Balai Harta Peninggalan diangkat selaku Kurator."},
        {"bab": "II", "pasal": "21", "text": "Kepailitan meliputi seluruh kekayaan Debitor pada saat putusan pernyataan pailit diucapkan serta segala sesuatu yang diperoleh selama kepailitan. Ketentuan sebagaimana dimaksud tidak berlaku terhadap: a. benda, termasuk hewan yang benar-benar dibutuhkan oleh Debitor sehubungan dengan pekerjaannya, perlengkapannya, alat-alat medis yang dipergunakan untuk kesehatan; b. segala sesuatu yang diperoleh Debitor dari pekerjaannya sendiri sebagai penggajian dari suatu jabatan atau jasa, sebagai upah, pensiun, uang tunggu atau uang tunjangan."},
        {"bab": "V", "pasal": "144", "text": "Debitor Pailit berhak untuk menawarkan suatu perdamaian kepada semua Kreditor. Rencana perdamaian tersebut harus diajukan dalam jangka waktu paling lambat 8 (delapan) hari sebelum rapat pencocokan piutang dan disediakan di Kepaniteraan Pengadilan agar dapat dilihat dengan cuma-cuma oleh setiap orang yang berkepentingan."},
        {"bab": "X", "pasal": "222", "ayat": "1", "text": "Penundaan Kewajiban Pembayaran Utang diajukan oleh Debitor yang mempunyai lebih dari 1 (satu) Kreditor atau oleh Kreditor yang memperkirakan bahwa Debitor tidak dapat melanjutkan membayar utangnya yang sudah jatuh waktu dan dapat ditagih, dengan maksud untuk mengajukan rencana perdamaian yang meliputi tawaran pembayaran sebagian atau seluruh utang kepada Kreditornya."},
    ]
    
    for art in kepailitan_articles:
        doc = {
            "jenis_dokumen": "UU",
            "nomor": "37",
            "tahun": 2004,
            "judul": "Kepailitan dan PKPU",
            "tentang": "Kepailitan dan Penundaan Kewajiban Pembayaran Utang",
            "bab": art.get("bab"),
            "pasal": art["pasal"],
            "text": art["text"]
        }
        if "ayat" in art:
            doc["ayat"] = art["ayat"]
        documents.append(doc)
    

    # === UU 42/1999 - Jaminan Fidusia ===
    jaminan_fidusia_articles = [
        {"bab": "I", "pasal": "1", "text": 'Dalam Undang-Undang ini yang dimaksud dengan: 1. Fidusia adalah pengalihan hak kepemilikan suatu benda atas dasar kepercayaan dengan ketentuan bahwa benda yang hak kepemilikannya dialihkan tersebut tetap dalam penguasaan pemilik benda. 2. Jaminan Fidusia adalah hak jaminan atas benda bergerak baik yang berwujud maupun yang tidak berwujud dan benda tidak bergerak khususnya bangunan yang tidak dapat dibebani hak tanggungan sebagaimana dimaksud dalam Undang-Undang Nomor 4 Tahun 1996 tentang Hak Tanggungan yang tetap berada dalam penguasaan Pemberi Fidusia, sebagai agunan bagi pelunasan utang tertentu, yang memberikan kedudukan yang diutamakan kepada Penerima Fidusia terhadap kreditor lainnya. 3. Piutang adalah hak untuk menerima pembayaran. 4. Benda adalah segala sesuatu yang dapat dimiliki dan dialihkan, baik yang berwujud maupun yang tidak berwujud, yang terdaftar maupun yang tidak terdaftar, yang bergerak maupun yang tidak bergerak yang tidak dapat dibebani hak tanggungan atau hipotek.'},
        {"bab": "II", "pasal": "4", "text": 'Jaminan Fidusia merupakan perjanjian ikutan dari suatu perjanjian pokok yang menimbulkan kewajiban bagi para pihak untuk memenuhi suatu prestasi yang berupa memberikan sesuatu, berbuat sesuatu, atau tidak berbuat sesuatu, yang dapat dinilai dengan uang.'},
        {"bab": "III", "pasal": "11", "ayat": "1", "text": 'Benda yang dibebani dengan Jaminan Fidusia wajib didaftarkan pada Kantor Pendaftaran Fidusia.'},
        {"bab": "III", "pasal": "12", "ayat": "1", "text": 'Pendaftaran Jaminan Fidusia sebagaimana dimaksud dalam Pasal 11 ayat (1) dilakukan pada Kantor Pendaftaran Fidusia dengan melampirkan pernyataan pendaftaran Jaminan Fidusia yang memuat: a. identitas pihak Pemberi dan Penerima Fidusia; b. tanggal, nomor akta Jaminan Fidusia, nama, dan tempat kedudukan notaris yang membuat akta Jaminan Fidusia; c. data perjanjian pokok yang dijamin fidusia; d. uraian mengenai benda yang menjadi objek Jaminan Fidusia; e. nilai penjaminan; dan f. nilai benda yang menjadi objek Jaminan Fidusia.'},
        {"bab": "III", "pasal": "14", "ayat": "1", "text": 'Kantor Pendaftaran Fidusia menerbitkan dan menyerahkan kepada Penerima Fidusia Sertifikat Jaminan Fidusia pada tanggal yang sama dengan tanggal penerimaan permohonan pendaftaran.'},
        {"bab": "V", "pasal": "29", "ayat": "1", "text": 'Apabila debitor atau Pemberi Fidusia cidera janji, eksekusi terhadap benda yang menjadi objek Jaminan Fidusia dapat dilakukan dengan cara: a. pelaksanaan titel eksekutorial sebagaimana dimaksud dalam Pasal 15 ayat (2) oleh Penerima Fidusia; b. penjualan benda yang menjadi objek Jaminan Fidusia atas kekuasaan Penerima Fidusia sendiri melalui pelelangan umum serta mengambil pelunasan piutangnya dari hasil penjualan; c. penjualan di bawah tangan yang dilakukan berdasarkan kesepakatan Pemberi dan Penerima Fidusia jika dengan cara demikian dapat diperoleh harga tertinggi yang menguntungkan para pihak.'},
        {"bab": "VI", "pasal": "35", "text": 'Setiap orang yang dengan sengaja memalsukan, mengubah, menghilangkan atau dengan cara apapun memberikan keterangan secara menyesatkan, yang jika hal tersebut diketahui oleh salah satu pihak tidak melahirkan perjanjian Jaminan Fidusia, dipidana dengan pidana penjara paling singkat 1 (satu) tahun dan paling lama 5 (lima) tahun dan denda paling sedikit Rp10.000.000,00 (sepuluh juta rupiah) dan paling banyak Rp100.000.000,00 (seratus juta rupiah).'},
        {"bab": "VI", "pasal": "36", "text": 'Pemberi Fidusia yang mengalihkan, menggadaikan, atau menyewakan benda yang menjadi objek Jaminan Fidusia sebagaimana dimaksud dalam Pasal 23 ayat (2) yang dilakukan tanpa persetujuan tertulis terlebih dahulu dari Penerima Fidusia, dipidana dengan pidana penjara paling lama 2 (dua) tahun dan denda paling banyak Rp50.000.000,00 (lima puluh juta rupiah).'},
    ]

    for art in jaminan_fidusia_articles:
        doc = {
            "jenis_dokumen": "UU",
            "nomor": "42",
            "tahun": 1999,
            "judul": "Jaminan Fidusia",
            "tentang": "Jaminan Fidusia",
            "bab": art.get("bab"),
            "pasal": art["pasal"],
            "text": art["text"]
        }
        if "ayat" in art:
            doc["ayat"] = art["ayat"]
        documents.append(doc)

    # === UU 4/1996 - Hak Tanggungan ===
    hak_tanggungan_articles = [
        {"bab": "I", "pasal": "1", "text": 'Dalam Undang-Undang ini yang dimaksud dengan: 1. Hak Tanggungan atas tanah beserta benda-benda yang berkaitan dengan tanah, yang selanjutnya disebut Hak Tanggungan, adalah hak jaminan yang dibebankan pada hak atas tanah sebagaimana dimaksud dalam Undang-Undang Nomor 5 Tahun 1960 tentang Peraturan Dasar Pokok-Pokok Agraria, berikut atau tidak berikut benda-benda lain yang merupakan satu kesatuan dengan tanah itu, untuk pelunasan utang tertentu, yang memberikan kedudukan yang diutamakan kepada kreditor tertentu terhadap kreditor-kreditor lain. 2. Kreditor adalah pihak yang berpiutang dalam suatu hubungan utang-piutang tertentu. 3. Debitor adalah pihak yang berutang dalam suatu hubungan utang-piutang tertentu. 4. Pejabat Pembuat Akta Tanah, yang selanjutnya disebut PPAT, adalah pejabat umum yang diberi wewenang untuk membuat akta pemindahan hak atas tanah, akta pembebanan hak atas tanah, dan akta pemberian kuasa membebankan Hak Tanggungan menurut peraturan perundang-undangan yang berlaku.'},
        {"bab": "II", "pasal": "4", "ayat": "1", "text": 'Hak atas tanah yang dapat dibebani Hak Tanggungan adalah: a. Hak Milik; b. Hak Guna Usaha; c. Hak Guna Bangunan.'},
        {"bab": "II", "pasal": "4", "ayat": "2", "text": 'Selain hak-hak atas tanah sebagaimana dimaksud pada ayat (1), Hak Pakai atas tanah Negara yang menurut ketentuan yang berlaku wajib didaftar dan menurut sifatnya dapat dipindahtangankan dapat juga dibebani Hak Tanggungan.'},
        {"bab": "II", "pasal": "6", "text": 'Apabila debitor cidera janji, pemegang Hak Tanggungan pertama mempunyai hak untuk menjual objek Hak Tanggungan atas kekuasaan sendiri melalui pelelangan umum serta mengambil pelunasan piutangnya dari hasil penjualan tersebut.'},
        {"bab": "IV", "pasal": "13", "ayat": "1", "text": 'Pemberian Hak Tanggungan wajib didaftarkan pada Kantor Pertanahan.'},
        {"bab": "IV", "pasal": "13", "ayat": "2", "text": 'Selambat-lambatnya 7 (tujuh) hari kerja setelah penandatanganan Akta Pemberian Hak Tanggungan sebagaimana dimaksud dalam Pasal 10 ayat (2), PPAT wajib mengirimkan Akta Pemberian Hak Tanggungan yang bersangkutan dan warkah lain yang diperlukan kepada Kantor Pertanahan.'},
        {"bab": "IV", "pasal": "14", "ayat": "1", "text": 'Sebagai tanda bukti adanya Hak Tanggungan, Kantor Pertanahan menerbitkan Sertifikat Hak Tanggungan sesuai dengan peraturan perundang-undangan yang berlaku.'},
        {"bab": "V", "pasal": "20", "ayat": "1", "text": 'Apabila debitor cidera janji, maka berdasarkan: a. hak pemegang Hak Tanggungan pertama untuk menjual objek Hak Tanggungan sebagaimana dimaksud dalam Pasal 6; atau b. titel eksekutorial yang terdapat dalam Sertifikat Hak Tanggungan sebagaimana dimaksud dalam Pasal 14 ayat (2), objek Hak Tanggungan dijual melalui pelelangan umum menurut tata cara yang ditentukan dalam peraturan perundang-undangan untuk pelunasan piutang pemegang Hak Tanggungan dengan hak mendahulu daripada kreditor-kreditor lainnya.'},
    ]

    for art in hak_tanggungan_articles:
        doc = {
            "jenis_dokumen": "UU",
            "nomor": "4",
            "tahun": 1996,
            "judul": "Hak Tanggungan",
            "tentang": "Hak Tanggungan atas Tanah Beserta Benda-Benda yang Berkaitan dengan Tanah",
            "bab": art.get("bab"),
            "pasal": art["pasal"],
            "text": art["text"]
        }
        if "ayat" in art:
            doc["ayat"] = art["ayat"]
        documents.append(doc)

    # === UU 30/1999 - Arbitrase dan Alternatif Penyelesaian Sengketa ===
    arbitrase_articles = [
        {"bab": "I", "pasal": "1", "text": 'Dalam Undang-Undang ini yang dimaksud dengan: 1. Arbitrase adalah cara penyelesaian suatu sengketa perdata di luar peradilan umum yang didasarkan pada perjanjian arbitrase yang dibuat secara tertulis oleh para pihak yang bersengketa. 2. Para Pihak adalah subjek hukum, baik menurut hukum perdata maupun hukum publik. 3. Perjanjian Arbitrase adalah suatu kesepakatan berupa klausula arbitrase yang tercantum dalam suatu perjanjian tertulis yang dibuat para pihak sebelum timbul sengketa, atau suatu perjanjian arbitrase tersendiri yang dibuat para pihak setelah timbul sengketa. 4. Pengadilan Negeri adalah Pengadilan Negeri yang daerah hukumnya meliputi tempat tinggal termohon. 5. Pemohon adalah pihak yang mengajukan permohonan penyelesaian sengketa melalui arbitrase. 6. Termohon adalah pihak lawan dari Pemohon dalam penyelesaian sengketa melalui arbitrase.'},
        {"bab": "II", "pasal": "7", "text": 'Para pihak dapat menyetujui suatu sengketa yang terjadi atau yang akan terjadi antara mereka untuk diselesaikan melalui arbitrase.'},
        {"bab": "II", "pasal": "9", "text": 'Dalam hal para pihak memilih penyelesaian sengketa melalui arbitrase setelah sengketa terjadi, persetujuan mengenai hal tersebut harus dibuat dalam suatu perjanjian tertulis yang ditandatangani oleh para pihak. Dalam hal para pihak tidak dapat menandatangani perjanjian tertulis sebagaimana dimaksud pada ayat (1), perjanjian tertulis tersebut harus dibuat dalam bentuk akta notaris. Perjanjian tertulis sebagaimana dimaksud pada ayat (1) harus memuat: a. masalah yang dipersengketakan; b. nama lengkap dan tempat tinggal para pihak; c. nama lengkap dan tempat tinggal arbiter atau majelis arbitrase; d. tempat arbiter atau majelis arbitrase akan mengambil keputusan; e. nama lengkap sekretaris; f. jangka waktu penyelesaian sengketa; g. pernyataan kesediaan dari arbiter; dan h. pernyataan kesediaan dari pihak yang bersengketa untuk menanggung segala biaya yang diperlukan untuk penyelesaian sengketa melalui arbitrase.'},
        {"bab": "III", "pasal": "12", "ayat": "1", "text": 'Yang dapat ditunjuk atau diangkat sebagai arbiter harus memenuhi syarat: a. cakap melakukan tindakan hukum; b. berumur paling rendah 35 tahun; c. tidak mempunyai hubungan keluarga sedarah atau semenda sampai dengan derajat kedua dengan salah satu pihak bersengketa; d. tidak mempunyai kepentingan finansial atau kepentingan lain atas putusan arbitrase; dan e. memiliki pengalaman serta menguasai secara aktif di bidangnya paling sedikit 15 tahun.'},
        {"bab": "IV", "pasal": "54", "ayat": "1", "text": "Putusan arbitrase harus memuat: a. kepala putusan yang berbunyi 'DEMI KEADILAN BERDASARKAN KETUHANAN YANG MAHA ESA'; b. nama lengkap dan alamat para pihak; c. uraian singkat sengketa; d. pendirian para pihak; e. nama lengkap dan alamat arbiter; f. pertimbangan dan kesimpulan arbiter atau majelis arbitrase mengenai keseluruhan sengketa; g. pendapat tiap-tiap arbiter dalam hal terdapat perbedaan pendapat dalam majelis arbitrase; h. amar putusan; i. tempat dan tanggal putusan; dan j. tanda tangan arbiter atau majelis arbitrase."},
        {"bab": "IV", "pasal": "57", "text": 'Putusan diucapkan dalam waktu paling lama 30 (tiga puluh) hari setelah pemeriksaan ditutup. Dalam waktu paling lama 14 (empat belas) hari setelah putusan diterima, para pihak dapat mengajukan permohonan kepada arbiter atau majelis arbitrase untuk melakukan koreksi terhadap kekeliruan administratif dan/atau menambah atau mengurangi sesuatu tuntutan putusan.'},
        {"bab": "V", "pasal": "59", "ayat": "1", "text": 'Dalam waktu paling lama 30 (tiga puluh) hari terhitung sejak tanggal putusan diucapkan, lembar asli atau salinan otentik putusan arbitrase diserahkan dan didaftarkan oleh arbiter atau kuasanya kepada Panitera Pengadilan Negeri.'},
        {"bab": "V", "pasal": "70", "text": 'Terhadap putusan arbitrase para pihak dapat mengajukan permohonan pembatalan apabila putusan tersebut diduga mengandung unsur-unsur sebagai berikut: a. surat atau dokumen yang diajukan dalam pemeriksaan, setelah putusan dijatuhkan, diakui palsu atau dinyatakan palsu; b. setelah putusan diambil ditemukan dokumen yang bersifat menentukan, yang disembunyikan oleh pihak lawan; c. putusan diambil dari hasil tipu muslihat yang dilakukan oleh salah satu pihak dalam pemeriksaan sengketa.'},
    ]

    for art in arbitrase_articles:
        doc = {
            "jenis_dokumen": "UU",
            "nomor": "30",
            "tahun": 1999,
            "judul": "Arbitrase dan Alternatif Penyelesaian Sengketa",
            "tentang": "Arbitrase dan Alternatif Penyelesaian Sengketa",
            "bab": art.get("bab"),
            "pasal": art["pasal"],
            "text": art["text"]
        }
        if "ayat" in art:
            doc["ayat"] = art["ayat"]
        documents.append(doc)

    # === UU 2/2004 - Penyelesaian Perselisihan Hubungan Industrial ===
    pphi_articles = [
        {"bab": "I", "pasal": "2", "text": 'Jenis perselisihan hubungan industrial meliputi: a. perselisihan hak; b. perselisihan kepentingan; c. perselisihan pemutusan hubungan kerja; dan d. perselisihan antar serikat pekerja/serikat buruh hanya dalam satu perusahaan.'},
        {"bab": "II", "pasal": "3", "ayat": "1", "text": 'Perselisihan hubungan industrial wajib diupayakan penyelesaiannya terlebih dahulu melalui perundingan bipartit secara musyawarah untuk mencapai mufakat.'},
        {"bab": "II", "pasal": "4", "ayat": "1", "text": 'Dalam hal perundingan bipartit gagal sebagaimana dimaksud dalam Pasal 3 ayat (3), maka salah satu atau kedua belah pihak mencatatkan perselisihannya kepada instansi yang bertanggung jawab di bidang ketenagakerjaan setempat dengan melampirkan bukti bahwa upaya-upaya penyelesaian melalui perundingan bipartit telah dilakukan.'},
        {"bab": "III", "pasal": "8", "text": 'Penyelesaian perselisihan melalui mediasi dilakukan oleh mediator yang berada di setiap kantor instansi yang bertanggung jawab di bidang ketenagakerjaan Kabupaten/Kota.'},
        {"bab": "III", "pasal": "10", "text": 'Dalam hal tidak tercapai kesepakatan penyelesaian perselisihan hubungan industrial melalui mediasi, maka: a. mediator mengeluarkan anjuran tertulis; b. anjuran tertulis sebagaimana dimaksud pada huruf a dalam waktu selambat-lambatnya 10 (sepuluh) hari kerja sejak sidang mediasi pertama harus sudah disampaikan kepada para pihak; c. para pihak harus sudah memberikan jawaban secara tertulis kepada mediator yang isinya menyetujui atau menolak anjuran tertulis dalam waktu selambat-lambatnya 10 (sepuluh) hari kerja setelah menerima anjuran tertulis.'},
        {"bab": "IV", "pasal": "17", "text": 'Penyelesaian perselisihan melalui konsiliasi dilakukan oleh konsiliator yang terdaftar pada kantor instansi yang bertanggung jawab di bidang ketenagakerjaan Kabupaten/Kota.'},
        {"bab": "VII", "pasal": "55", "text": 'Pengadilan Hubungan Industrial merupakan pengadilan khusus yang dibentuk di lingkungan pengadilan negeri yang berwenang memeriksa, mengadili, dan memberi putusan terhadap perselisihan hubungan industrial.'},
        {"bab": "VII", "pasal": "56", "text": 'Pengadilan Hubungan Industrial bertugas dan berwenang memeriksa dan memutus: a. di tingkat pertama mengenai perselisihan hak; b. di tingkat pertama dan terakhir mengenai perselisihan kepentingan; c. di tingkat pertama mengenai perselisihan pemutusan hubungan kerja; d. di tingkat pertama dan terakhir mengenai perselisihan antar serikat pekerja/serikat buruh dalam satu perusahaan.'},
    ]

    for art in pphi_articles:
        doc = {
            "jenis_dokumen": "UU",
            "nomor": "2",
            "tahun": 2004,
            "judul": "Penyelesaian Perselisihan Hubungan Industrial",
            "tentang": "Penyelesaian Perselisihan Hubungan Industrial",
            "bab": art.get("bab"),
            "pasal": art["pasal"],
            "text": art["text"]
        }
        if "ayat" in art:
            doc["ayat"] = art["ayat"]
        documents.append(doc)

    # === UU 6/2011 - Keimigrasian ===
    keimigrasian_articles = [
        {"bab": "I", "pasal": "1", "text": 'Dalam Undang-Undang ini yang dimaksud dengan: 1. Keimigrasian adalah hal ihwal lalu lintas orang yang masuk atau keluar Wilayah Indonesia serta pengawasannya dalam rangka menjaga tegaknya kedaulatan negara. 2. Wilayah Indonesia adalah seluruh wilayah Negara Kesatuan Republik Indonesia yang meliputi darat, laut termasuk dasar laut dan tanah di bawahnya serta ruang udara di atasnya termasuk seluruh kepulauan. 3. Orang Asing adalah orang yang bukan warga negara Indonesia. 4. Visa Republik Indonesia yang selanjutnya disebut Visa adalah keterangan tertulis yang diberikan oleh pejabat yang berwenang di Perwakilan Republik Indonesia atau di tempat lain yang ditetapkan oleh Pemerintah Republik Indonesia yang memuat persetujuan bagi Orang Asing untuk melakukan perjalanan ke Wilayah Indonesia dan menjadi dasar untuk pemberian Izin Tinggal.'},
        {"bab": "IV", "pasal": "34", "text": 'Visa terdiri atas: a. Visa diplomatik; b. Visa dinas; c. Visa kunjungan; dan d. Visa tinggal terbatas.'},
        {"bab": "IV", "pasal": "38", "ayat": "1", "text": 'Visa tinggal terbatas diberikan kepada Orang Asing: a. sebagai rohaniwan, tenaga ahli, pekerja, peneliti, pelajar, investor, lanjut usia, dan keluarganya, serta Orang Asing yang kawin secara sah dengan warga negara Indonesia, yang akan melakukan perjalanan ke Wilayah Indonesia untuk bertempat tinggal dalam jangka waktu yang terbatas; atau b. dalam rangka bergabung untuk bekerja di atas kapal, alat apung, atau instalasi yang beroperasi di wilayah perairan nusantara, laut teritorial, landas kontinen, dan/atau Zona Ekonomi Eksklusif Indonesia.'},
        {"bab": "V", "pasal": "48", "ayat": "1", "text": 'Setiap Orang Asing yang berada di Wilayah Indonesia wajib memiliki Izin Tinggal.'},
        {"bab": "V", "pasal": "48", "ayat": "2", "text": 'Izin Tinggal sebagaimana dimaksud pada ayat (1) terdiri atas: a. Izin Tinggal diplomatik; b. Izin Tinggal dinas; c. Izin Tinggal kunjungan; d. Izin Tinggal terbatas; dan e. Izin Tinggal Tetap.'},
        {"bab": "V", "pasal": "52", "ayat": "1", "text": 'Izin Tinggal Tetap dapat diberikan kepada: a. Orang Asing pemegang Izin Tinggal terbatas sebagai rohaniwan, pekerja, investor, dan lanjut usia; b. keluarga karena perkawinan campuran; c. suami atau istri, dan anak dari Orang Asing pemegang Izin Tinggal Tetap; dan d. Orang Asing eks warga negara Indonesia dan eks subjek anak berkewarganegaraan ganda Republik Indonesia.'},
        {"bab": "VII", "pasal": "75", "ayat": "1", "text": 'Pejabat Imigrasi berwenang melakukan Tindakan Administratif Keimigrasian terhadap Orang Asing yang berada di Wilayah Indonesia yang melakukan kegiatan berbahaya dan patut diduga membahayakan keamanan dan ketertiban umum atau tidak menghormati atau tidak menaati peraturan perundang-undangan.'},
        {"bab": "VII", "pasal": "75", "ayat": "2", "text": 'Tindakan Administratif Keimigrasian sebagaimana dimaksud pada ayat (1) dapat berupa: a. pencantuman dalam daftar Pencegahan atau Penangkalan; b. pembatasan, perubahan, atau pembatalan Izin Tinggal; c. larangan untuk berada di satu atau beberapa tempat tertentu di Wilayah Indonesia; d. keharusan untuk bertempat tinggal di suatu tempat tertentu di Wilayah Indonesia; e. pengenaan biaya beban; dan/atau f. Deportasi dari Wilayah Indonesia.'},
        {"bab": "VII", "pasal": "83", "ayat": "1", "text": 'Pejabat Imigrasi berwenang menempatkan Orang Asing dalam Rumah Detensi Imigrasi atau Ruang Detensi Imigrasi apabila Orang Asing tersebut: a. berada di Wilayah Indonesia tanpa memiliki Izin Tinggal yang sah atau memiliki Izin Tinggal yang tidak berlaku lagi; b. berada di Wilayah Indonesia tanpa memiliki Dokumen Perjalanan yang sah; c. dikenai Tindakan Administratif Keimigrasian berupa Deportasi menunggu proses pemulangan; atau d. menunggu pelaksanaan Deportasi.'},
    ]

    for art in keimigrasian_articles:
        doc = {
            "jenis_dokumen": "UU",
            "nomor": "6",
            "tahun": 2011,
            "judul": "Keimigrasian",
            "tentang": "Keimigrasian",
            "bab": art.get("bab"),
            "pasal": art["pasal"],
            "text": art["text"]
        }
        if "ayat" in art:
            doc["ayat"] = art["ayat"]
        documents.append(doc)

    # === UU 16/2001 - Yayasan ===
    yayasan_articles = [
        {"bab": "I", "pasal": "1", "text": 'Dalam Undang-Undang ini yang dimaksud dengan: 1. Yayasan adalah badan hukum yang terdiri atas kekayaan yang dipisahkan dan diperuntukkan untuk mencapai tujuan tertentu di bidang sosial, keagamaan, dan kemanusiaan, yang tidak mempunyai anggota. 2. Organ Yayasan adalah Pembina, Pengurus, dan Pengawas. 3. Kekayaan Yayasan adalah seluruh harta kekayaan Yayasan baik berupa uang, barang, maupun kekayaan lain yang diperoleh Yayasan berdasarkan Undang-Undang ini.'},
        {"bab": "II", "pasal": "9", "ayat": "1", "text": 'Yayasan didirikan oleh satu orang atau lebih dengan memisahkan sebagian harta kekayaan pendirinya, sebagai kekayaan awal.'},
        {"bab": "II", "pasal": "9", "ayat": "2", "text": 'Pendirian Yayasan sebagaimana dimaksud dalam ayat (1) dilakukan dengan akta notaris dan dibuat dalam bahasa Indonesia.'},
        {"bab": "IV", "pasal": "14", "text": 'Organ Yayasan terdiri atas Pembina, Pengurus, dan Pengawas.'},
        {"bab": "V", "pasal": "26", "ayat": "1", "text": 'Kekayaan Yayasan berasal dari sejumlah kekayaan yang dipisahkan dalam bentuk uang atau barang.'},
        {"bab": "VI", "pasal": "35", "ayat": "1", "text": 'Pengurus Yayasan bertanggung jawab penuh atas kepengurusan Yayasan untuk kepentingan dan tujuan Yayasan serta berhak mewakili Yayasan baik di dalam maupun di luar Pengadilan.'},
        {"bab": "VII", "pasal": "37", "ayat": "1", "text": 'Pengurus wajib membuat dan menyimpan catatan atau tulisan yang berisi keterangan mengenai hak dan kewajiban serta hal lain yang berkaitan dengan kegiatan usaha Yayasan.'},
        {"bab": "X", "pasal": "68", "ayat": "1", "text": 'Kekayaan sisa hasil likuidasi diserahkan kepada Yayasan lain yang mempunyai kesamaan kegiatan dengan Yayasan yang bubar.'},
    ]

    for art in yayasan_articles:
        doc = {
            "jenis_dokumen": "UU",
            "nomor": "16",
            "tahun": 2001,
            "judul": "Yayasan",
            "tentang": "Yayasan",
            "bab": art.get("bab"),
            "pasal": art["pasal"],
            "text": art["text"]
        }
        if "ayat" in art:
            doc["ayat"] = art["ayat"]
        documents.append(doc)

    # === UU 25/1992 - Koperasi ===
    koperasi_articles = [
        {"bab": "I", "pasal": "1", "text": 'Dalam Undang-Undang ini yang dimaksud dengan: 1. Koperasi adalah badan usaha yang beranggotakan orang-seorang atau badan hukum Koperasi dengan melandaskan kegiatannya berdasarkan prinsip Koperasi sekaligus sebagai gerakan ekonomi rakyat yang berdasar atas asas kekeluargaan. 2. Perkoperasian adalah segala sesuatu yang menyangkut kehidupan Koperasi. 3. Koperasi Primer adalah Koperasi yang didirikan oleh dan beranggotakan orang-seorang. 4. Koperasi Sekunder adalah Koperasi yang didirikan oleh dan beranggotakan Koperasi.'},
        {"bab": "II", "pasal": "3", "text": 'Koperasi bertujuan memajukan kesejahteraan anggota pada khususnya dan masyarakat pada umumnya serta ikut membangun tatanan perekonomian nasional dalam rangka mewujudkan masyarakat yang maju, adil, dan makmur berlandaskan Pancasila dan Undang-Undang Dasar 1945.'},
        {"bab": "II", "pasal": "5", "ayat": "1", "text": 'Koperasi melaksanakan prinsip Koperasi sebagai berikut: a. keanggotaan bersifat sukarela dan terbuka; b. pengelolaan dilakukan secara demokratis; c. pembagian sisa hasil usaha dilakukan secara adil sebanding dengan besarnya jasa usaha masing-masing anggota; d. pemberian balas jasa yang terbatas terhadap modal; e. kemandirian.'},
        {"bab": "IV", "pasal": "15", "text": 'Koperasi dapat berbentuk Koperasi Primer atau Koperasi Sekunder.'},
        {"bab": "VII", "pasal": "41", "ayat": "1", "text": 'Modal Koperasi terdiri dari modal sendiri dan modal pinjaman.'},
        {"bab": "VII", "pasal": "41", "ayat": "2", "text": 'Modal sendiri dapat berasal dari: a. simpanan pokok; b. simpanan wajib; c. dana cadangan; d. hibah.'},
        {"bab": "IX", "pasal": "45", "ayat": "1", "text": 'Sisa Hasil Usaha Koperasi merupakan pendapatan Koperasi yang diperoleh dalam satu tahun buku dikurangi dengan biaya, penyusutan, dan kewajiban lainnya termasuk pajak dalam tahun buku yang bersangkutan.'},
        {"bab": "IX", "pasal": "45", "ayat": "2", "text": 'Sisa Hasil Usaha setelah dikurangi dana cadangan, dibagikan kepada anggota sebanding dengan jasa usaha yang dilakukan oleh masing-masing anggota dengan Koperasi, serta digunakan untuk keperluan pendidikan perkoperasian dan keperluan lain dari Koperasi, sesuai dengan keputusan Rapat Anggota.'},
    ]

    for art in koperasi_articles:
        doc = {
            "jenis_dokumen": "UU",
            "nomor": "25",
            "tahun": 1992,
            "judul": "Koperasi",
            "tentang": "Perkoperasian",
            "bab": art.get("bab"),
            "pasal": art["pasal"],
            "text": art["text"]
        }
        if "ayat" in art:
            doc["ayat"] = art["ayat"]
        documents.append(doc)

    # === UU 21/2011 - OJK ===
    ojk_articles = [
        {"bab": "I", "pasal": "1", "text": 'Dalam Undang-Undang ini yang dimaksud dengan: 1. Otoritas Jasa Keuangan, yang selanjutnya disingkat OJK, adalah lembaga yang independen dan bebas dari campur tangan pihak lain, yang mempunyai fungsi, tugas, dan wewenang pengaturan, pengawasan, pemeriksaan, dan penyidikan sebagaimana dimaksud dalam Undang-Undang ini. 2. Dewan Komisioner adalah pimpinan tertinggi OJK yang bersifat kolektif dan kolegial.'},
        {"bab": "II", "pasal": "4", "text": 'OJK dibentuk dengan tujuan agar keseluruhan kegiatan di dalam sektor jasa keuangan: a. terselenggara secara teratur, adil, transparan, dan akuntabel; b. mampu mewujudkan sistem keuangan yang tumbuh secara berkelanjutan dan stabil; dan c. mampu melindungi kepentingan Konsumen dan masyarakat.'},
        {"bab": "III", "pasal": "5", "text": 'OJK berfungsi menyelenggarakan sistem pengaturan dan pengawasan yang terintegrasi terhadap keseluruhan kegiatan di dalam sektor jasa keuangan.'},
        {"bab": "III", "pasal": "6", "text": 'OJK melaksanakan tugas pengaturan dan pengawasan terhadap: a. kegiatan jasa keuangan di sektor Perbankan; b. kegiatan jasa keuangan di sektor Pasar Modal; dan c. kegiatan jasa keuangan di sektor Perasuransian, Dana Pensiun, Lembaga Pembiayaan, dan Lembaga Jasa Keuangan Lainnya.'},
        {"bab": "III", "pasal": "7", "text": 'Untuk melaksanakan tugas pengaturan dan pengawasan di sektor Perbankan sebagaimana dimaksud dalam Pasal 6 huruf a, OJK mempunyai wewenang: a. pengaturan dan pengawasan mengenai kelembagaan bank yang meliputi perizinan untuk pendirian bank, pembukaan kantor bank, anggaran dasar, rencana kerja, kepemilikan, kepengurusan dan sumber daya manusia, merger, konsolidasi dan akuisisi bank, serta pencabutan izin usaha bank; b. pengaturan dan pengawasan mengenai kesehatan bank yang meliputi likuiditas, rentabilitas, solvabilitas, kualitas aset, rasio kecukupan modal minimum, batas maksimum pemberian kredit, rasio pinjaman terhadap simpanan, dan pencadangan bank.'},
        {"bab": "III", "pasal": "9", "text": 'Untuk melaksanakan tugas pengawasan sebagaimana dimaksud dalam Pasal 6, OJK mempunyai wewenang: a. menetapkan kebijakan operasional pengawasan terhadap kegiatan jasa keuangan; b. mengawasi pelaksanaan tugas pengawasan yang dilaksanakan oleh Kepala Eksekutif; c. melakukan pengawasan, pemeriksaan, penyidikan, perlindungan Konsumen, dan tindakan lain terhadap Lembaga Jasa Keuangan, pelaku, dan/atau penunjang kegiatan jasa keuangan sebagaimana dimaksud dalam peraturan perundang-undangan di sektor jasa keuangan.'},
        {"bab": "VI", "pasal": "28", "text": 'Untuk perlindungan Konsumen dan masyarakat, OJK berwenang melakukan tindakan pencegahan kerugian Konsumen dan masyarakat, yang meliputi: a. memberikan informasi dan edukasi kepada masyarakat atas karakteristik sektor jasa keuangan, layanan, dan produknya; b. meminta Lembaga Jasa Keuangan untuk menghentikan kegiatannya apabila kegiatan tersebut berpotensi merugikan masyarakat; dan c. tindakan lain yang dianggap perlu sesuai dengan ketentuan peraturan perundang-undangan di sektor jasa keuangan.'},
    ]

    for art in ojk_articles:
        doc = {
            "jenis_dokumen": "UU",
            "nomor": "21",
            "tahun": 2011,
            "judul": "OJK",
            "tentang": "Otoritas Jasa Keuangan",
            "bab": art.get("bab"),
            "pasal": art["pasal"],
            "text": art["text"]
        }
        if "ayat" in art:
            doc["ayat"] = art["ayat"]
        documents.append(doc)

    # === UU 40/2014 - Perasuransian ===
    perasuransian_articles = [
        {"bab": "I", "pasal": "1", "text": 'Dalam Undang-Undang ini yang dimaksud dengan: 1. Asuransi adalah perjanjian antara dua pihak, yaitu perusahaan asuransi dan pemegang polis, yang menjadi dasar bagi penerimaan premi oleh perusahaan asuransi sebagai imbalan untuk: a. memberikan penggantian kepada tertanggung atau pemegang polis karena kerugian, kerusakan, biaya yang timbul, kehilangan keuntungan, atau tanggung jawab hukum kepada pihak ketiga yang mungkin diderita tertanggung atau pemegang polis karena terjadinya suatu peristiwa yang tidak pasti; atau b. memberikan pembayaran yang didasarkan pada meninggalnya tertanggung atau pembayaran yang didasarkan pada hidupnya tertanggung dengan manfaat yang besarnya telah ditetapkan dan/atau didasarkan pada hasil pengelolaan dana.'},
        {"bab": "II", "pasal": "2", "ayat": "1", "text": 'Perasuransian terdiri atas: a. Usaha Perasuransian, yang terdiri atas usaha asuransi umum, usaha asuransi jiwa, usaha asuransi umum syariah, dan usaha asuransi jiwa syariah; dan b. Usaha Penunjang Usaha Perasuransian.'},
        {"bab": "III", "pasal": "6", "ayat": "1", "text": 'Untuk mendapatkan izin usaha sebagaimana dimaksud dalam Pasal 5 ayat (1), Perusahaan Perasuransian wajib memenuhi persyaratan mengenai: a. anggaran dasar; b. susunan organisasi; c. modal disetor; d. dana jaminan; e. kepemilikan; f. kelayakan dan kepatutan pemegang saham dan Pengendali; g. kelayakan dan kepatutan anggota direksi dan anggota dewan komisaris; h. tenaga ahli; i. kelayakan rencana kerja; dan j. kelayakan sistem manajemen risiko.'},
        {"bab": "IV", "pasal": "17", "ayat": "1", "text": 'Pemegang Polis, Tertanggung, atau Peserta berhak atas manfaat sebagaimana dinyatakan dalam Polis, sertifikat asuransi, atau akad.'},
        {"bab": "V", "pasal": "26", "text": 'Perusahaan Asuransi dan Perusahaan Reasuransi wajib membentuk cadangan teknis sesuai dengan jenis asuransi yang diselenggarakan.'},
        {"bab": "VI", "pasal": "31", "ayat": "1", "text": 'Perusahaan Asuransi wajib mereasuransikan sebagian risiko kepada perusahaan reasuransi yang memiliki izin usaha dari OJK.'},
        {"bab": "X", "pasal": "53", "ayat": "1", "text": 'OJK melakukan pengawasan terhadap Perusahaan Perasuransian dalam rangka melindungi kepentingan Pemegang Polis, Tertanggung, atau Peserta.'},
        {"bab": "X", "pasal": "53", "ayat": "2", "text": 'Pengawasan sebagaimana dimaksud pada ayat (1) meliputi pengawasan langsung dan tidak langsung terhadap penyelenggaraan usaha Perasuransian.'},
    ]

    for art in perasuransian_articles:
        doc = {
            "jenis_dokumen": "UU",
            "nomor": "40",
            "tahun": 2014,
            "judul": "Perasuransian",
            "tentang": "Perasuransian",
            "bab": art.get("bab"),
            "pasal": art["pasal"],
            "text": art["text"]
        }
        if "ayat" in art:
            doc["ayat"] = art["ayat"]
        documents.append(doc)

    # === UU 7/2014 - Perdagangan ===
    perdagangan_articles = [
        {"bab": "I", "pasal": "1", "text": 'Dalam Undang-Undang ini yang dimaksud dengan: 1. Perdagangan adalah tatanan kegiatan yang terkait dengan transaksi Barang dan/atau Jasa di dalam negeri dan melampaui batas wilayah negara dengan tujuan pengalihan hak atas Barang dan/atau Jasa untuk memperoleh imbalan atau kompensasi. 2. Perdagangan Dalam Negeri adalah Perdagangan Barang dan/atau Jasa dalam wilayah Negara Kesatuan Republik Indonesia. 3. Perdagangan Luar Negeri adalah Perdagangan yang mencakup kegiatan Ekspor dan/atau Impor atas Barang dan/atau Perdagangan Jasa yang melampaui batas wilayah negara.'},
        {"bab": "III", "pasal": "4", "ayat": "1", "text": 'Kebijakan Perdagangan Dalam Negeri diarahkan untuk: a. meningkatkan kelancaran distribusi Barang dan Jasa; b. meningkatkan ketersediaan Barang dan Jasa yang diperdagangkan; c. menstabilkan harga Barang dan Jasa; d. meningkatkan keamanan Perdagangan.'},
        {"bab": "IV", "pasal": "24", "ayat": "1", "text": 'Pemerintah melakukan pengaturan Distribusi Barang yang diperdagangkan untuk memperlancar arus Barang dalam rangka menjamin ketersediaan Barang di seluruh wilayah Negara Kesatuan Republik Indonesia.'},
        {"bab": "V", "pasal": "38", "ayat": "1", "text": 'Kebijakan Perdagangan Luar Negeri meliputi kebijakan umum dan kebijakan khusus di bidang Ekspor dan Impor.'},
        {"bab": "V", "pasal": "47", "text": 'Eksportir dilarang mengekspor Barang yang ditetapkan sebagai Barang yang dilarang Ekspornya, meliputi: a. Barang yang berkaitan dengan pelestarian sumber daya alam dan lingkungan hidup; b. Barang kebutuhan dalam negeri yang persediaannya terbatas; dan c. Barang yang peredarannya dilarang berdasarkan ketentuan peraturan perundang-undangan.'},
        {"bab": "V", "pasal": "49", "ayat": "1", "text": 'Setiap Importir wajib mengimpor Barang dalam keadaan baru, kecuali ditentukan lain berdasarkan ketentuan peraturan perundang-undangan.'},
        {"bab": "V", "pasal": "52", "text": 'Pemerintah dapat mengenakan tindakan pengamanan Perdagangan (safeguard) terhadap Barang Impor apabila terdapat lonjakan jumlah Barang Impor baik secara absolut maupun secara relatif terhadap Barang produksi dalam negeri yang sejenis atau Barang yang secara langsung bersaing.'},
        {"bab": "VIII", "pasal": "65", "ayat": "1", "text": 'Setiap Pelaku Usaha yang memperdagangkan Barang dan/atau Jasa dengan menggunakan sistem elektronik wajib menyediakan data dan/atau informasi secara lengkap dan benar.'},
    ]

    for art in perdagangan_articles:
        doc = {
            "jenis_dokumen": "UU",
            "nomor": "7",
            "tahun": 2014,
            "judul": "Perdagangan",
            "tentang": "Perdagangan",
            "bab": art.get("bab"),
            "pasal": art["pasal"],
            "text": art["text"]
        }
        if "ayat" in art:
            doc["ayat"] = art["ayat"]
        documents.append(doc)

    # === UU 3/2014 - Perindustrian ===
    perindustrian_articles = [
        {"bab": "I", "pasal": "1", "text": 'Dalam Undang-Undang ini yang dimaksud dengan: 1. Perindustrian adalah tatanan dan segala kegiatan yang bertalian dengan kegiatan Industri. 2. Industri adalah seluruh bentuk kegiatan ekonomi yang mengolah bahan baku dan/atau memanfaatkan sumber daya Industri sehingga menghasilkan barang yang mempunyai nilai tambah atau manfaat lebih tinggi, termasuk jasa Industri. 3. Kawasan Industri adalah kawasan tempat pemusatan kegiatan Industri yang dilengkapi dengan sarana dan prasarana penunjang yang dikembangkan dan dikelola oleh Perusahaan Kawasan Industri.'},
        {"bab": "II", "pasal": "3", "text": 'Perindustrian diselenggarakan dengan tujuan: a. mewujudkan Industri nasional sebagai pilar dan penggerak perekonomian nasional; b. mewujudkan kedalaman dan kekuatan struktur Industri; c. mewujudkan Industri yang mandiri, berdaya saing, dan maju, serta Industri Hijau; d. mewujudkan kepastian berusaha, persaingan yang sehat, serta mencegah pemusatan atau penguasaan Industri oleh satu kelompok atau perseorangan yang merugikan masyarakat.'},
        {"bab": "IV", "pasal": "14", "ayat": "1", "text": 'Pemerintah menyusun Rencana Induk Pembangunan Industri Nasional untuk jangka waktu 20 (dua puluh) tahun.'},
        {"bab": "VII", "pasal": "33", "ayat": "1", "text": 'Setiap kegiatan usaha Industri wajib berlokasi di Kawasan Industri, kecuali bagi kegiatan usaha Industri yang berlokasi di daerah kabupaten/kota yang belum memiliki Kawasan Industri atau bagi kegiatan usaha Industri yang tidak berpotensi menimbulkan pencemaran lingkungan hidup yang berdampak luas.'},
        {"bab": "IX", "pasal": "64", "ayat": "1", "text": 'Standar Nasional Indonesia yang selanjutnya disingkat SNI adalah standar yang ditetapkan oleh lembaga yang menyelenggarakan pengembangan dan pembinaan di bidang standardisasi.'},
        {"bab": "IX", "pasal": "64", "ayat": "2", "text": 'Pemerintah dan/atau Pemerintah Daerah dapat memberlakukan SNI secara wajib terhadap Barang dan/atau Jasa Industri yang diperdagangkan di dalam negeri melalui penerbitan regulasi teknis.'},
        {"bab": "XI", "pasal": "101", "ayat": "1", "text": 'Setiap kegiatan usaha Industri wajib memiliki Izin Usaha Industri.'},
        {"bab": "XI", "pasal": "101", "ayat": "2", "text": 'Izin Usaha Industri sebagaimana dimaksud pada ayat (1) diberikan oleh Menteri kepada setiap orang yang mendirikan usaha Industri.'},
    ]

    for art in perindustrian_articles:
        doc = {
            "jenis_dokumen": "UU",
            "nomor": "3",
            "tahun": 2014,
            "judul": "Perindustrian",
            "tentang": "Perindustrian",
            "bab": art.get("bab"),
            "pasal": art["pasal"],
            "text": art["text"]
        }
        if "ayat" in art:
            doc["ayat"] = art["ayat"]
        documents.append(doc)

    # === UU 2/2017 - Jasa Konstruksi ===
    jasa_konstruksi_articles = [
        {"bab": "I", "pasal": "1", "text": 'Dalam Undang-Undang ini yang dimaksud dengan: 1. Jasa Konstruksi adalah layanan jasa konsultansi konstruksi dan/atau pekerjaan konstruksi. 2. Konsultansi Konstruksi adalah layanan keseluruhan atau sebagian kegiatan yang meliputi pengkajian, perencanaan, perancangan, pengawasan, dan manajemen penyelenggaraan konstruksi suatu bangunan. 3. Pekerjaan Konstruksi adalah keseluruhan atau sebagian kegiatan yang meliputi pembangunan, pengoperasian, pemeliharaan, pembongkaran, dan pembangunan kembali suatu bangunan.'},
        {"bab": "III", "pasal": "4", "text": 'Jasa Konstruksi mencakup: a. jasa konsultansi konstruksi; dan b. pekerjaan konstruksi.'},
        {"bab": "IV", "pasal": "11", "ayat": "1", "text": 'Usaha Jasa Konstruksi meliputi: a. usaha jasa konsultansi konstruksi; dan b. usaha pekerjaan konstruksi.'},
        {"bab": "V", "pasal": "30", "ayat": "1", "text": 'Penyelenggaraan Jasa Konstruksi dilaksanakan berdasarkan Kontrak Kerja Konstruksi antara pengguna jasa dan penyedia jasa.'},
        {"bab": "V", "pasal": "42", "text": 'Pengguna Jasa dan/atau Penyedia Jasa wajib memenuhi Standar Keamanan, Keselamatan, Kesehatan, dan Keberlanjutan dalam penyelenggaraan Jasa Konstruksi.'},
        {"bab": "VI", "pasal": "55", "ayat": "1", "text": 'Setiap tenaga kerja konstruksi yang bekerja di sektor Jasa Konstruksi wajib memiliki Sertifikat Kompetensi Kerja.'},
        {"bab": "VII", "pasal": "65", "text": 'Kegagalan Bangunan merupakan keadaan bangunan yang tidak berfungsi, baik secara keseluruhan maupun sebagian dari segi teknis, manfaat, keselamatan, dan kesehatan kerja, dan/atau keselamatan umum sebagai akibat kesalahan Penyedia Jasa dan/atau Pengguna Jasa setelah penyerahan akhir pekerjaan konstruksi.'},
        {"bab": "X", "pasal": "84", "text": 'Penyelesaian sengketa Jasa Konstruksi dapat ditempuh melalui: a. musyawarah untuk mufakat; b. mediasi; c. konsiliasi; d. arbitrase; atau e. pengadilan.'},
    ]

    for art in jasa_konstruksi_articles:
        doc = {
            "jenis_dokumen": "UU",
            "nomor": "2",
            "tahun": 2017,
            "judul": "Jasa Konstruksi",
            "tentang": "Jasa Konstruksi",
            "bab": art.get("bab"),
            "pasal": art["pasal"],
            "text": art["text"]
        }
        if "ayat" in art:
            doc["ayat"] = art["ayat"]
        documents.append(doc)

    # === UU 31/2000 - Desain Industri ===
    desain_industri_articles = [
        {"bab": "I", "pasal": "1", "text": 'Dalam Undang-Undang ini yang dimaksud dengan: 1. Desain Industri adalah suatu kreasi tentang bentuk, konfigurasi, atau komposisi garis atau warna, atau garis dan warna, atau gabungan daripadanya yang berbentuk tiga dimensi atau dua dimensi yang memberikan kesan estetis dan dapat diwujudkan dalam pola tiga dimensi atau dua dimensi serta dapat dipakai untuk menghasilkan suatu produk, barang, komoditas industri, atau kerajinan tangan. 2. Pendesain adalah seorang atau beberapa orang yang menghasilkan Desain Industri.'},
        {"bab": "II", "pasal": "2", "ayat": "1", "text": 'Hak Desain Industri diberikan untuk Desain Industri yang baru.'},
        {"bab": "II", "pasal": "5", "ayat": "1", "text": 'Hak Desain Industri diberikan atas dasar permohonan.'},
        {"bab": "III", "pasal": "9", "text": 'Permohonan pendaftaran Desain Industri diajukan secara tertulis dalam bahasa Indonesia kepada Direktorat Jenderal dengan membayar biaya sebagaimana diatur dalam Undang-Undang ini.'},
        {"bab": "III", "pasal": "12", "text": 'Direktorat Jenderal melakukan pemeriksaan terhadap Permohonan pendaftaran Desain Industri untuk menentukan apakah permohonan tersebut telah memenuhi persyaratan administratif.'},
        {"bab": "IV", "pasal": "25", "text": 'Hak Desain Industri dapat beralih atau dialihkan dengan: a. pewarisan; b. hibah; c. wasiat; d. perjanjian tertulis; atau e. sebab-sebab lain yang dibenarkan oleh peraturan perundang-undangan.'},
        {"bab": "V", "pasal": "32", "text": 'Perlindungan terhadap Hak Desain Industri diberikan untuk jangka waktu 10 (sepuluh) tahun terhitung sejak tanggal penerimaan.'},
        {"bab": "VII", "pasal": "38", "text": 'Gugatan pembatalan pendaftaran Desain Industri dapat diajukan oleh pihak yang berkepentingan dengan alasan Desain Industri tersebut seharusnya tidak dapat didaftarkan atau bertentangan dengan peraturan perundang-undangan yang berlaku, ketertiban umum, agama, atau kesusilaan.'},
    ]

    for art in desain_industri_articles:
        doc = {
            "jenis_dokumen": "UU",
            "nomor": "31",
            "tahun": 2000,
            "judul": "Desain Industri",
            "tentang": "Desain Industri",
            "bab": art.get("bab"),
            "pasal": art["pasal"],
            "text": art["text"]
        }
        if "ayat" in art:
            doc["ayat"] = art["ayat"]
        documents.append(doc)

    # === UU 30/2000 - Rahasia Dagang ===
    rahasia_dagang_articles = [
        {"bab": "I", "pasal": "1", "text": 'Dalam Undang-Undang ini yang dimaksud dengan: 1. Rahasia Dagang adalah informasi yang tidak diketahui oleh umum di bidang teknologi dan/atau bisnis, mempunyai nilai ekonomi karena berguna dalam kegiatan usaha, dan dijaga kerahasiaannya oleh pemilik Rahasia Dagang.'},
        {"bab": "II", "pasal": "2", "text": 'Lingkup perlindungan Rahasia Dagang meliputi metode produksi, metode pengolahan, metode penjualan, atau informasi lain di bidang teknologi dan/atau bisnis yang memiliki nilai ekonomi dan tidak diketahui oleh masyarakat umum.'},
        {"bab": "II", "pasal": "3", "ayat": "1", "text": 'Rahasia Dagang mendapat perlindungan apabila informasi tersebut bersifat rahasia, mempunyai nilai ekonomi, dan dijaga kerahasiaannya melalui upaya sebagaimana mestinya.'},
        {"bab": "III", "pasal": "4", "text": 'Pemilik Rahasia Dagang memiliki hak untuk: a. menggunakan sendiri Rahasia Dagang yang dimilikinya; b. memberikan Lisensi kepada atau melarang pihak lain untuk menggunakan Rahasia Dagang atau mengungkapkan Rahasia Dagang itu kepada pihak ketiga untuk kepentingan yang bersifat komersial.'},
        {"bab": "IV", "pasal": "5", "ayat": "1", "text": 'Pemilik Rahasia Dagang atau pemegang Lisensi dapat menggugat siapa pun yang dengan sengaja dan tanpa hak melakukan perbuatan sebagaimana dimaksud dalam Pasal 4, berupa: a. gugatan ganti rugi; dan/atau b. penghentian semua perbuatan sebagaimana dimaksud dalam Pasal 4.'},
        {"bab": "V", "pasal": "8", "text": 'Seseorang dianggap melanggar Rahasia Dagang pihak lain apabila ia memperoleh atau menguasai Rahasia Dagang tersebut dengan cara yang bertentangan dengan peraturan perundang-undangan yang berlaku.'},
        {"bab": "VII", "pasal": "11", "text": 'Penyelesaian sengketa Rahasia Dagang dapat diselesaikan melalui Pengadilan Negeri atau melalui arbitrase atau alternatif penyelesaian sengketa.'},
        {"bab": "IX", "pasal": "13", "text": 'Pelanggaran Rahasia Dagang juga terjadi apabila seseorang dengan sengaja mengungkapkan Rahasia Dagang, mengingkari kesepakatan atau mengingkari kewajiban tertulis atau tidak tertulis untuk menjaga Rahasia Dagang yang bersangkutan.'},
        {"bab": "X", "pasal": "17", "ayat": "1", "text": 'Barangsiapa dengan sengaja dan tanpa hak menggunakan Rahasia Dagang pihak lain atau melakukan perbuatan sebagaimana dimaksud dalam Pasal 13 atau Pasal 14 dipidana dengan pidana penjara paling lama 2 (dua) tahun dan/atau denda paling banyak Rp300.000.000,00 (tiga ratus juta rupiah).'},
    ]

    for art in rahasia_dagang_articles:
        doc = {
            "jenis_dokumen": "UU",
            "nomor": "30",
            "tahun": 2000,
            "judul": "Rahasia Dagang",
            "tentang": "Rahasia Dagang",
            "bab": art.get("bab"),
            "pasal": art["pasal"],
            "text": art["text"]
        }
        if "ayat" in art:
            doc["ayat"] = art["ayat"]
        documents.append(doc)

    # === UU 17/2006 - Kepabeanan ===
    kepabeanan_articles = [
        {"bab": "I", "pasal": "1", "text": 'Dalam Undang-Undang ini yang dimaksud dengan: 1. Kepabeanan adalah segala sesuatu yang berhubungan dengan pengawasan atas lalu lintas barang yang masuk atau keluar daerah pabean serta pemungutan bea masuk dan bea keluar. 2. Daerah Pabean adalah wilayah Republik Indonesia yang meliputi wilayah darat, perairan, dan ruang udara di atasnya, serta tempat-tempat tertentu di Zona Ekonomi Eksklusif dan landas kontinen yang di dalamnya berlaku Undang-Undang ini.'},
        {"bab": "II", "pasal": "2", "ayat": "1", "text": 'Barang yang dimasukkan ke dalam daerah pabean diperlakukan sebagai barang impor dan terutang bea masuk.'},
        {"bab": "III", "pasal": "10A", "ayat": "1", "text": 'Importir wajib memberitahukan rencana kedatangan sarana pengangkut ke kantor pabean tujuan sebelum kedatangan sarana pengangkut.'},
        {"bab": "IV", "pasal": "16", "ayat": "1", "text": 'Pejabat Bea dan Cukai dapat menetapkan tarif terhadap barang impor sebelum atau sesudah pemberitahuan pabean diserahkan.'},
        {"bab": "IV", "pasal": "25", "ayat": "1", "text": 'Nilai pabean untuk penghitungan bea masuk adalah nilai transaksi dari barang impor yang bersangkutan.'},
        {"bab": "VI", "pasal": "44", "text": 'Barang impor yang belum diselesaikan kewajiban pabeannya dapat ditimbun di Tempat Penimbunan Sementara untuk jangka waktu paling lama 30 (tiga puluh) hari sejak tanggal penimbunan.'},
        {"bab": "VII", "pasal": "53", "text": 'Menteri dapat menetapkan suatu kawasan sebagai Kawasan Pabean, Kawasan Perdagangan Bebas dan Pelabuhan Bebas, Tempat Penimbunan Berikat, atau kawasan ekonomi lainnya yang diberikan fasilitas di bidang kepabeanan.'},
        {"bab": "X", "pasal": "82", "ayat": "1", "text": 'Pejabat Bea dan Cukai berwenang melakukan pemeriksaan pabean atas barang impor atau barang ekspor setelah pemberitahuan pabean diserahkan.'},
    ]

    for art in kepabeanan_articles:
        doc = {
            "jenis_dokumen": "UU",
            "nomor": "17",
            "tahun": 2006,
            "judul": "Kepabeanan",
            "tentang": "Kepabeanan",
            "bab": art.get("bab"),
            "pasal": art["pasal"],
            "text": art["text"]
        }
        if "ayat" in art:
            doc["ayat"] = art["ayat"]
        documents.append(doc)

    # === UU 39/2007 - Cukai ===
    cukai_articles = [
        {"bab": "I", "pasal": "1", "text": 'Dalam Undang-Undang ini yang dimaksud dengan: 1. Cukai adalah pungutan negara yang dikenakan terhadap barang-barang tertentu yang mempunyai sifat atau karakteristik yang ditetapkan dalam Undang-Undang ini. 2. Pabrik adalah tempat tertentu termasuk bangunan, halaman, dan lapangan yang merupakan bagian daripadanya, yang dipergunakan untuk menghasilkan Barang Kena Cukai dan/atau untuk mengemas Barang Kena Cukai dalam kemasan untuk penjualan eceran.'},
        {"bab": "II", "pasal": "2", "ayat": "1", "text": 'Barang-barang tertentu yang mempunyai sifat atau karakteristik sebagai berikut dikenai Cukai: a. konsumsinya perlu dikendalikan; b. peredarannya perlu diawasi; c. pemakaiannya dapat menimbulkan dampak negatif bagi masyarakat atau lingkungan hidup; atau d. pemakaiannya perlu pembebanan pungutan negara demi keadilan dan keseimbangan.'},
        {"bab": "III", "pasal": "4", "ayat": "1", "text": 'Cukai dikenakan terhadap Barang Kena Cukai yang terdiri dari: a. etil alkohol atau etanol, dengan tidak mengindahkan bahan yang digunakan dan proses pembuatannya; b. minuman yang mengandung etil alkohol dalam kadar berapa pun, dengan tidak mengindahkan bahan yang digunakan dan proses pembuatannya, termasuk konsentrat yang mengandung etil alkohol; c. hasil tembakau, yang meliputi sigaret, cerutu, rokok daun, tembakau iris, dan hasil pengolahan tembakau lainnya, dengan tidak mengindahkan digunakan atau tidak bahan pengganti atau bahan pembantu dalam pembuatannya.'},
        {"bab": "IV", "pasal": "5", "ayat": "1", "text": 'Barang Kena Cukai berupa hasil tembakau dikenai Cukai berdasarkan tarif paling tinggi: a. untuk yang dibuat di Indonesia sebesar 57% (lima puluh tujuh persen) dari harga jual eceran; atau b. untuk yang diimpor sebesar 57% (lima puluh tujuh persen) dari harga jual eceran.'},
        {"bab": "IV", "pasal": "7", "ayat": "1", "text": 'Harga dasar yang digunakan untuk penghitungan Cukai atas Barang Kena Cukai yang dibuat di Indonesia adalah Harga Jual Pabrik atau Harga Jual Eceran.'},
        {"bab": "V", "pasal": "9", "ayat": "1", "text": 'Pembebasan Cukai dapat diberikan atas Barang Kena Cukai tertentu, antara lain: a. untuk keperluan penelitian dan pengembangan ilmu pengetahuan; b. untuk keperluan perwakilan negara asing beserta para pejabatnya yang bertugas di Indonesia berdasarkan asas timbal balik; c. yang digunakan sebagai bahan baku atau bahan penolong dalam pembuatan barang hasil akhir yang bukan merupakan Barang Kena Cukai.'},
        {"bab": "VI", "pasal": "14", "ayat": "1", "text": 'Setiap orang yang akan menjalankan kegiatan sebagai Pengusaha Pabrik, Pengusaha Tempat Penyimpanan, Importir Barang Kena Cukai, atau Penyalur wajib memiliki Nomor Pokok Pengusaha Barang Kena Cukai (NPPBKC) dari Menteri.'},
        {"bab": "VIII", "pasal": "29", "ayat": "1", "text": 'Barang Kena Cukai yang pelunasan Cukainya dengan cara pelekatan pita cukai, wajib dilekati pita cukai yang dicetak oleh Pemerintah.'},
    ]

    for art in cukai_articles:
        doc = {
            "jenis_dokumen": "UU",
            "nomor": "39",
            "tahun": 2007,
            "judul": "Cukai",
            "tentang": "Cukai",
            "bab": art.get("bab"),
            "pasal": art["pasal"],
            "text": art["text"]
        }
        if "ayat" in art:
            doc["ayat"] = art["ayat"]
        documents.append(doc)

    return documents


def main():
    parser = argparse.ArgumentParser(description="Indonesian Legal Document Scraper")
    parser.add_argument("--source", choices=["peraturan", "jdih", "generate"], default="generate",
                        help="Source to scrape from")
    parser.add_argument("--output", type=str, default="../data/peraturan/regulations.json",
                        help="Output file path")
    parser.add_argument("--limit", type=int, default=100, help="Maximum documents to scrape")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between requests")
    
    args = parser.parse_args()
    
    output_path = Path(__file__).parent / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    if args.source == "generate":
        logger.info("Generating expanded dataset with 100+ legal documents...")
        documents = create_expanded_dataset()
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(documents, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Successfully generated {len(documents)} documents to {output_path}")
        
        # Print summary
        doc_types = {}
        for doc in documents:
            jenis = doc.get("jenis_dokumen", "Unknown")
            doc_types[jenis] = doc_types.get(jenis, 0) + 1
        
        print("\n=== Dataset Summary ===")
        for jenis, count in sorted(doc_types.items()):
            print(f"  {jenis}: {count} documents")
        print(f"  Total: {len(documents)} documents")
    
    elif args.source == "peraturan":
        scraper = PeraturanScraper(delay=args.delay)
        try:
            logger.info(f"Searching peraturan.go.id (limit: {args.limit})...")
            results = scraper.search(limit=args.limit)
            
            all_documents = []
            for result in results:
                logger.info(f"Scraping: {result['title']}")
                docs = scraper.scrape_document(result['url'])
                if docs:
                    all_documents.extend([asdict(d) for d in docs])
            
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(all_documents, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Scraped {len(all_documents)} documents to {output_path}")
        finally:
            scraper.close()
    
    else:
        logger.error(f"Unknown source: {args.source}")


if __name__ == "__main__":
    main()
