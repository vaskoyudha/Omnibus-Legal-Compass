import pytest

from backend.scripts import ingest


def test_extracts_ayat_from_prefix_when_missing():
    text = "(1)Jenis..."
    result = ingest.extract_ayat_from_text(text, None)
    assert result == "1"


def test_does_not_extract_when_no_prefix():
    text = "Dalam Undang tentang ..."
    result = ingest.extract_ayat_from_text(text, None)
    assert result is None


def test_preserves_existing_ayat():
    text = "(2)Contoh teks..."
    result = ingest.extract_ayat_from_text(text, "3")
    assert result == "3"
