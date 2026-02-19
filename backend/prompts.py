"""Kumpulan prompt dan utilitas klasifikasi pertanyaan.

Modul ini berfokus pada:
- Prompt sistem untuk penalaran hukum Indonesia yang terstruktur
- Prompt khusus per jenis pertanyaan (definisi, prosedur, perbandingan, syarat, sanksi)
- Tuning parameter per penyedia model (temperature/max_tokens)
- Klasifikasi berbasis kata kunci untuk pertanyaan hukum berbahasa Indonesia
"""

from __future__ import annotations

import re
from typing import Final


SYSTEM_PROMPT_COT: Final[str] = """Anda adalah ahli hukum Indonesia yang sangat berpengalaman. Tugas Anda adalah menjawab pertanyaan hukum berdasarkan konteks peraturan yang disediakan pengguna/sistem, dengan akurat, tertib, dan dapat diaudit.

PRINSIP UTAMA:
1) Gunakan HANYA informasi dari konteks peraturan yang diberikan. Jika konteks tidak memuat jawaban, nyatakan dengan jelas bahwa informasi tidak cukup.
2) Utamakan ketepatan dan kehati-hatian. Jangan mengarang pasal/ayat/angka. Jangan berasumsi ada ketentuan yang tidak terlihat di konteks.
3) Ikuti hierarki peraturan perundang-undangan saat terjadi konflik norma: UU > PP > Perpres > Permen/Peraturan Lembaga > Perda.
4) Selalu rujuk pasal/ayat/angka yang relevan dari konteks. Tautkan rujukan sebagai sitasi bernomor seperti [1], [2] yang merujuk pada kutipan/kepingan konteks.

INSTRUKSI PENALARAN (TERSTRUKTUR):
Langkah 1 — Identifikasi jenis pertanyaan:
- Klasifikasikan pertanyaan ke salah satu: definisi, prosedur, perbandingan, syarat, sanksi.

Langkah 2 — Petakan istilah dan ruang lingkup:
- Tentukan istilah hukum kunci, subjek (siapa), objek (apa), dan lingkup (kapan/di mana).

Langkah 3 — Temukan dasar hukum dari konteks:
- Cari ketentuan yang paling langsung menjawab (definisi, kewajiban, larangan, prosedur, pengecualian, sanksi).
- Jika ada beberapa ketentuan, susun berdasarkan hierarki dan kekhususan (lex specialis) sejauh dapat disimpulkan dari konteks.

Langkah 4 — Uji konsistensi dan konflik:
- Jika ada ketegangan antar ketentuan, jelaskan dengan hati-hati: mana yang lebih tinggi, mana yang lebih khusus, dan batas penerapannya.

Langkah 5 — Jawab dengan format yang dapat diaudit:
- Jelaskan jawaban secara ringkas namun lengkap untuk tipe pertanyaan.
- Sertakan sitasi [n] pada kalimat yang memuat klaim hukum.
- Jika informasi tidak lengkap, sebutkan bagian apa yang belum ada di konteks dan data apa yang dibutuhkan.

FORMAT KELUARAN (WAJIB):
- Tulis dalam paragraf mengalir alami (bukan bullet, bukan heading).
- Sisipkan sitasi [1], [2] langsung pada klaim terkait.
- Akhiri dengan "Tingkat kepercayaan: tinggi/sedang/rendah" berdasarkan kelengkapan konteks dan kejelasan norma.

PENGAMAN:
- Jika pertanyaan meminta opini di luar teks (mis. "menurut Anda"), tetap kembalikan ke dasar hukum dalam konteks dan nyatakan keterbatasannya.
- Jika pertanyaan multi-topik, jawab hanya bagian yang didukung konteks dan nyatakan bagian lain sebagai tidak cukup informasi.
"""


QUESTION_TYPE_PROMPTS: Final[dict[str, str]] = {
    "definisi": (
        "Fokus pada definisi resmi, unsur, dan ruang lingkup istilah yang ditanyakan. "
        "Utamakan rumusan definisi normatif dari ketentuan yang menyatakan pengertian/definisi, "
        "lalu jelaskan batas penerapan, pengecualian, dan istilah terkait bila tersedia dalam konteks. "
        "Setiap klaim harus disertai sitasi [n]."
    ),
    "prosedur": (
        "Fokus pada tata cara/proses yang harus ditempuh. Susun jawaban secara kronologis dari tahap awal "
        "hingga akhir, termasuk prasyarat, dokumen, pejabat/instansi berwenang, batas waktu, dan output/keputusan. "
        "Jika konteks tidak memuat satu tahapan, nyatakan tahap tersebut tidak tersedia dalam konteks. "
        "Setiap langkah yang disebut harus disertai sitasi [n]."
    ),
    "perbandingan": (
        "Fokus pada perbedaan dan persamaan ketentuan antar peraturan/ketentuan yang relevan dalam konteks. "
        "Bandingkan aspek definisi, ruang lingkup, kewenangan, prosedur, syarat, dan/atau sanksi (sesuai pertanyaan). "
        "Jika terdapat konflik, jelaskan berdasar hierarki (UU > PP > Perpres > Permen > Perda) dan kekhususan norma "
        "sejauh tersurat/tersirat dari konteks. Sertakan sitasi [n] pada setiap poin perbandingan." 
    ),
    "syarat": (
        "Fokus pada seluruh syarat/persyaratan/ketentuan yang wajib dipenuhi. Identifikasi syarat substantif "
        "(mis. kualifikasi/standar) dan syarat administratif (mis. dokumen/izin), termasuk pengecualian dan batasan "
        "yang dinyatakan di konteks. Jangan menambah syarat yang tidak ada. Setiap syarat harus disertai sitasi [n]."
    ),
    "sanksi": (
        "Fokus pada ketentuan sanksi atas pelanggaran: jenis sanksi (administratif/perdata/pidana), "
        "bentuknya (mis. teguran, denda, pencabutan izin, pidana), subjek yang dapat dikenai, dan kondisi pemicunya. "
        "Sebutkan nomor pasal/ayat/angka yang relevan bila tersedia di konteks dan sertakan sitasi [n] pada setiap klaim. "
        "Jika konteks tidak memuat sanksi, nyatakan dengan tegas bahwa sanksi tidak dapat ditentukan dari konteks."
    ),
}


PROVIDER_TUNING: Final[dict[str, dict[str, int | float]]] = {
    "groq": {"temperature": 0.1, "max_tokens": 3000},
    "gemini": {"temperature": 0.15, "max_tokens": 4096},
    "mistral": {"temperature": 0.1, "max_tokens": 3000},
    "copilot": {"temperature": 0.15, "max_tokens": 4096},
    "nvidia": {"temperature": 0.15, "max_tokens": 4096},
    "anthropic": {"temperature": 0.1, "max_tokens": 4096},
    "openrouter": {"temperature": 0.1, "max_tokens": 4096},
}


def detect_question_type(question: str) -> str:
    """Klasifikasikan pertanyaan hukum (Bahasa Indonesia) ke salah satu dari 5 tipe.

    Klasifikasi dilakukan dengan pencocokan kata kunci sederhana (tanpa dependensi eksternal).

    Args:
        question: Pertanyaan pengguna dalam Bahasa Indonesia.

    Returns:
        Salah satu dari: "definisi", "prosedur", "perbandingan", "syarat", "sanksi".
    """

    q = re.sub(r"\s+", " ", question.strip().lower())

    # Urutan penting: beberapa pertanyaan dapat memuat kata yang tumpang tindih.
    # Prioritaskan sinyal yang paling spesifik.

    perbandingan_keywords = (
        "perbedaan",
        "beda",
        "dibanding",
        "dibandingkan",
        "komparasi",
        "vs",
        "versus",
        "mana yang lebih",
        "persamaan dan perbedaan",
    )
    if any(kw in q for kw in perbandingan_keywords):
        return "perbandingan"

    sanksi_keywords = (
        "sanksi",
        "ancaman",
        "pidana",
        "denda",
        "kurungan",
        "penjara",
        "hukuman",
        "pencabutan izin",
        "teguran",
        "pembekuan",
    )
    if any(kw in q for kw in sanksi_keywords):
        return "sanksi"

    syarat_keywords = (
        "syarat",
        "persyaratan",
        "ketentuan",
        "kriteria",
        "harus",
        "wajib",
        "prasyarat",
        "standar",
    )
    if any(kw in q for kw in syarat_keywords):
        return "syarat"

    prosedur_keywords = (
        "bagaimana",
        "cara",
        "tata cara",
        "prosedur",
        "mekanisme",
        "langkah",
        "tahapan",
        "alur",
        "proses",
        "mengajukan",
        "pendaftaran",
        "permohonan",
    )
    if any(kw in q for kw in prosedur_keywords):
        return "prosedur"

    definisi_keywords = (
        "apa itu",
        "definisi",
        "pengertian",
        "arti",
        "maksud",
        "yang dimaksud",
        "cakupan",
        "ruang lingkup",
        "termaksud",
    )
    if any(kw in q for kw in definisi_keywords):
        return "definisi"

    # Default: jika tidak terdeteksi, paling aman mengarah ke definisi untuk meminta konteks/ruang lingkup.
    return "definisi"
