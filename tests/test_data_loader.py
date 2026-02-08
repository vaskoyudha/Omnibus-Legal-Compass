"""Tests for data loading functionality."""
import json
import pytest
from pathlib import Path


def test_load_sample_data():
    """Test that sample data can be loaded and has expected structure."""
    sample_path = Path("data/peraturan/sample.json")
    
    # Check file exists
    assert sample_path.exists(), "Sample data file should exist"
    
    # Load data
    with open(sample_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Check data is a list
    assert isinstance(data, list), "Data should be a list"
    
    # Check we have data
    assert len(data) > 0, "Should have at least one record"
    
    # Check first record has required fields
    first_record = data[0]
    required_fields = ['jenis_dokumen', 'nomor', 'tahun', 'judul', 'pasal', 'text']
    
    for field in required_fields:
        assert field in first_record, f"Record should have '{field}' field"
    
    # Check data types
    assert isinstance(first_record['jenis_dokumen'], str)
    assert isinstance(first_record['nomor'], str)
    assert isinstance(first_record['tahun'], int)
    assert isinstance(first_record['judul'], str)
    assert isinstance(first_record['pasal'], str)
    assert isinstance(first_record['text'], str)


def test_sample_data_content():
    """Test that sample data has valid Indonesian legal content."""
    sample_path = Path("data/peraturan/sample.json")
    
    with open(sample_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Check for specific document types
    doc_types = set(record['jenis_dokumen'] for record in data)
    expected_types = {'UU', 'PP', 'Perpres'}
    
    assert doc_types & expected_types, f"Should have at least one of {expected_types}"
    
    # Check text is in Indonesian (contains common Indonesian words)
    indonesian_words = ['dan', 'yang', 'untuk', 'dengan', 'dalam']
    
    for record in data:
        text = record['text'].lower()
        has_indonesian = any(word in text for word in indonesian_words)
        assert has_indonesian, f"Text should contain Indonesian words: {record['text'][:50]}"


def test_schema_documentation_exists():
    """Test that data schema documentation exists."""
    schema_path = Path("data/DATA_SCHEMA.md")
    
    assert schema_path.exists(), "Schema documentation should exist"
    
    content = schema_path.read_text(encoding='utf-8')
    
    # Check for key sections
    assert "jenis_dokumen" in content
    assert "nomor" in content
    assert "tahun" in content
    assert "pasal" in content


def test_sample_data_count():
    """Test that we have reasonable sample size."""
    sample_path = Path("data/peraturan/sample.json")
    
    with open(sample_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Should have at least 10 records for meaningful testing
    assert len(data) >= 10, f"Should have at least 10 records, got {len(data)}"
