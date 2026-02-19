"""Unit tests for detect_question_type in backend.prompts.

Follows patterns from existing tests: small, focused, pytest style.
All questions are in Bahasa Indonesia and cover: definisi, prosedur,
perbandingan, syarat, sanksi, plus edge cases.
"""

import pytest

from backend.prompts import detect_question_type


class TestQuestionTypeDetection:
    """Comprehensive detection tests for each question type.

    Each test uses multiple realistic Indonesian legal questions and
    checks that detect_question_type returns the expected label.
    """

    # ------------------------------------------------------------------
    # Definisi
    # ------------------------------------------------------------------
    @pytest.mark.parametrize(
        "q",
        [
            "Apa itu PT?",
            "Definisi perusahaan menurut UU Perseroan Terbatas",
            "Pengertian merger dalam UU Perseroan",
            "Arti 'usaha mikro' dalam peraturan daerah",
        ],
    )
    def test_detect_definisi(self, q):
        assert (
            detect_question_type(q) == "definisi"
        ), f"Expected 'definisi' for question: {q!r}"

    # ------------------------------------------------------------------
    # Prosedur
    # ------------------------------------------------------------------
    @pytest.mark.parametrize(
        "q",
        [
            "Bagaimana cara mendirikan PT di Indonesia?",
            "Tata cara mengajukan izin lingkungan untuk pabrik baru",
            "Prosedur pendaftaran merek dagang di Direktorat Jenderal",
            "Langkah untuk mengajukan izin impor?",
        ],
    )
    def test_detect_prosedur(self, q):
        assert (
            detect_question_type(q) == "prosedur"
        ), f"Expected 'prosedur' for question: {q!r}"

    # ------------------------------------------------------------------
    # Perbandingan
    # ------------------------------------------------------------------
    @pytest.mark.parametrize(
        "q",
        [
            "Perbedaan PT dan CV dalam hal tanggung jawab pemegang saham",
            "Apa beda kontrak kerja tetap vs kontrak kerja waktu tertentu?",
            "UU Cipta Kerja dibandingkan dengan UU Ketenagakerjaan lama",
            "Komparasi antara izin prinsip dan izin usaha tetap",
        ],
    )
    def test_detect_perbandingan(self, q):
        assert (
            detect_question_type(q) == "perbandingan"
        ), f"Expected 'perbandingan' for question: {q!r}"

    # ------------------------------------------------------------------
    # Syarat
    # ------------------------------------------------------------------
    @pytest.mark.parametrize(
        "q",
        [
            "Syarat pendirian PT di Indonesia",
            "Persyaratan untuk mengajukan Nomor Induk Berusaha (NIB)",
            "Ketentuan apa yang menjadi kriteria wajib untuk izin lingkungan?",
            "Prasyarat administrasi sebelum mendapatkan izin edar obat",
        ],
    )
    def test_detect_syarat(self, q):
        assert (
            detect_question_type(q) == "syarat"
        ), f"Expected 'syarat' for question: {q!r}"

    # ------------------------------------------------------------------
    # Sanksi
    # ------------------------------------------------------------------
    @pytest.mark.parametrize(
        "q",
        [
            "Sanksi bagi perusahaan yang membuang limbah sembarangan",
            "Ancaman pidana untuk tindak penyuapan menurut KUHP",
            "Berapa denda untuk pelanggaran peraturan perpajakan?",
            "Apakah pencabutan izin dapat dikenakan sebagai sanksi administratif?",
        ],
    )
    def test_detect_sanksi(self, q):
        assert (
            detect_question_type(q) == "sanksi"
        ), f"Expected 'sanksi' for question: {q!r}"

    # ------------------------------------------------------------------
    # Edge cases and mixed keywords
    # ------------------------------------------------------------------
    def test_empty_and_nonlegal_default(self):
        # Empty string should default to 'definisi' per implementation
        assert (
            detect_question_type("") == "definisi"
        ), "Empty question should default to 'definisi'"

        # Non-legal casual question should default to 'definisi'
        casual = "Siapa pemain sepak bola favoritmu?"
        assert (
            detect_question_type(casual) == "definisi"
        ), f"Non-legal question should default to 'definisi' but got {detect_question_type(casual)!r}"

    def test_mixed_keywords_priority(self):
        # Contains both 'sanksi' and 'bagaimana' — sanksi has higher priority
        q1 = "Bagaimana sanksi administratif jika perusahaan tidak mendaftar?"
        assert (
            detect_question_type(q1) == "sanksi"
        ), f"Expected 'sanksi' due to keyword priority in question: {q1!r}"

        # Contains 'perbedaan' and 'cara' — perbandingan should win
        q2 = "Perbedaan tata cara pengajuan izin dan tata cara pencabutan izin"
        assert (
            detect_question_type(q2) == "perbandingan"
        ), f"Expected 'perbandingan' for mixed keywords in: {q2!r}"

        # Contains 'wajib' and 'cara' — 'syarat' should win because of keyword order
        q3 = "Apakah wajib mengikuti prosedur khusus sebelum mendaftar?"
        # The implementation treats 'wajib' -> syarat
        assert (
            detect_question_type(q3) == "syarat"
        ), f"Expected 'syarat' for mixed keywords in: {q3!r}"
