# Indonesian Legal Regulation Data Sources

This document tracks all external data sources used in the Omnibus Legal Compass corpus expansion.

## Data Provenance

### 1. HuggingFace: Azzindani/ID_REG_Parsed

**Source**: [Azzindani/ID_REG_Parsed](https://huggingface.co/datasets/Azzindani/ID_REG_Parsed)

**License**: Apache 2.0 ✅ (commercial use allowed)

**Downloaded**: [YYYY-MM-DD] (to be filled by download script)

**Statistics**:
- Total rows: 3,630,000+ records
- Coverage: UU, PP, Perpres, Permen, Perda
- Format: Parquet (via HuggingFace datasets library)

**Schema Mapping**:
| Source Field | Internal Field | Transformation |
|--------------|----------------|----------------|
| `Regulation Name` | `jenis_dokumen` | Parse regex: `^(UU\|PP\|Perpres\|Permen\|Perda)` |
| `Regulation Number` | `nomor` | Direct mapping |
| `Year` | `tahun` | Cast to string |
| `About` | `judul` | Direct mapping |
| `Chapter` | `bab` | Direct mapping (optional) |
| `Article` | `pasal` | Direct mapping (optional) |
| `Content` | `isi` | Direct mapping, validate ≥50 chars |

**Known Issues**:
- Some records have empty `Content` field → rejected by validation
- `jenis_dokumen` parsing requires regex matching on `Regulation Name`
- Duplicate detection needed: Some regulations appear multiple times

**Validation Results**:
- Schema conformance: Run `python -m backend.scripts.validate_data_sources --source huggingface`
- Duplicate count: To be measured after download
- Content quality: Records with <50 chars are rejected
- Encoding issues: Mojibake detection flags U+FFFD and Ã-prefix patterns

---

### 2. Open-Technology-Foundation: peraturan.go.id

**Source**: [Open-Technology-Foundation/peraturan.go.id](https://github.com/Open-Technology-Foundation/peraturan.go.id)

**License**: GPL-3.0 ⚠️ (derivative works must be GPL-3.0, MIT incompatible)

**Downloaded**: [YYYY-MM-DD] (to be filled by download script)

**Statistics**:
- Total files: 5,817 markdown files
- Total segments: 541,445 pre-chunked text segments
- Coverage: Comprehensive Indonesian regulations
- Format: Markdown with YAML frontmatter

**Schema Mapping**:
| Source Field | Internal Field | Transformation |
|--------------|----------------|----------------|
| Frontmatter: `type` | `jenis_dokumen` | Direct mapping |
| Frontmatter: `number` | `nomor` | Cast to string |
| Frontmatter: `year` | `tahun` | Cast to string |
| Frontmatter: `title` | `judul` | Direct mapping |
| Markdown body | `isi` | Strip YAML frontmatter, validate ≥50 chars |

**Known Issues**:
- **License Conflict**: GPL-3.0 requires derivative works to be GPL-3.0, but this project is MIT
- **Resolution**: Use only as supplementary reference data, NOT ingested into main corpus
- Alternative: Extract regulation identifiers only, fetch original PDFs from peraturan.go.id

**Validation Results**:
- File count: Run `python -m backend.scripts.validate_data_sources --source otf`
- Content quality: Sample validation on first 100 files
- Encoding: UTF-8 compliance checked

---

### 3. Manual Curation: regulations.json

**Source**: Manual curation by project team

**License**: MIT (project license)

**Created**: Initial project setup

**Statistics**:
- Total documents: 135 entries
- Coverage: 13 regulations (UU 11/2020, PP 24/2018, etc.)
- Format: JSON

**Schema Mapping**:
| Source Field | Internal Field | Transformation |
|--------------|----------------|----------------|
| `jenis_dokumen` | `jenis_dokumen` | Direct mapping |
| `nomor` | `nomor` | Cast to string if needed |
| `tahun` | `tahun` | Cast to string |
| `judul` | `judul` | Direct mapping |
| `text` | `isi` | Rename field |
| `tentang` | (dropped) | Redundant with `judul` |
| `bab` | `bab` | Direct mapping (optional) |
| `pasal` | `pasal` | Direct mapping (optional) |
| `ayat` | `ayat` | Direct mapping (optional) |

**Known Issues**:
- Schema evolved: `text` → `isi`, `tentang` dropped
- `ManualAdapter` in `format_converter.py` handles transformation

**Validation Results**:
- Schema conformance: Run `python -m backend.scripts.validate_data_sources --source manual`
- Duplicate count: To be measured
- Content quality: All records ≥50 chars
- Encoding: UTF-8 validated

---

## Usage Notes

### Incremental Ingestion

All sources use deduplication based on composite key:
```
(jenis_dokumen, nomor, tahun, pasal, ayat)
```

### Source Tracking

Every ingested chunk includes:
- `source`: `"huggingface_azzindani"` | `"otf_peraturan"` | `"manual"`
- `ingested_at`: ISO 8601 timestamp (UTC)

### Validation Workflow

```bash
# 1. Download data
python -m backend.scripts.download_datasets --source all

# 2. Validate data quality
python -m backend.scripts.validate_data_sources --source all

# 3. Ingest with deduplication
python -m backend.scripts.ingest \
  --json-path data/external/azzindani/converted.json \
  --source huggingface_azzindani
```

---

## License Compliance

| Source | License | Commercial Use | Derivative Works | Ingestion Status |
|--------|---------|----------------|------------------|------------------|
| Azzindani | Apache 2.0 | ✅ Yes | ✅ Allowed | ✅ Active |
| OTF Peraturan | GPL-3.0 | ✅ Yes | ⚠️ Must be GPL | ⚠️ Reference only |
| Manual | MIT | ✅ Yes | ✅ Allowed | ✅ Active |

---

## Update Log

- **2026-02-16**: Initial documentation created
- **[Date]**: HuggingFace Azzindani downloaded (X.XXM rows)
- **[Date]**: OTF Peraturan cloned (X,XXX files)
- **[Date]**: First incremental ingestion completed
