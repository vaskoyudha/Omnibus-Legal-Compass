# Data Schema - peraturan.go.id Indonesian Legal Documents

## Overview
- **Total Documents**: 5,817 legal texts
- **Total Segments**: 541,445 text chunks
- **Date Range**: 2001-2025
- **Document Types**: perban, permen, perda, uu, pp, perpres, perppu

## Document Structure

Each legal document is split into chunks with the following fields:

### Metadata Fields
- **jenis_dokumen** (string): Document type
  - `UU` - Undang-Undang (Law)
  - `PP` - Peraturan Pemerintah (Government Regulation)
  - `Perpres` - Peraturan Presiden (Presidential Regulation)
  - `Permen` - Peraturan Menteri (Ministerial Regulation)
  - `Perda` - Peraturan Daerah (Regional Regulation)
  - `Perppu` - Peraturan Pemerintah Pengganti Undang-Undang (Government Regulation in Lieu of Law)
  - `Perban` - Peraturan Bank Indonesia (Bank Indonesia Regulation)
  
- **nomor** (string): Regulation number
  - Example: "11", "24", "5"
  
- **tahun** (integer): Year of issuance
  - Example: 2020, 2019, 2024
  
- **judul** (string): Full title of the regulation
  - Example: "Cipta Kerja", "Perlindungan Data Pribadi"
  
- **tentang** (string): Subject matter
  - Example: "Penciptaan Lapangan Kerja", "Perlindungan Data Pribadi"

### Content Fields
- **bab** (string, optional): Chapter number
  - Example: "III", "IV", "V"
  
- **bagian** (string, optional): Section name
  - Example: "Ketentuan Umum", "Larangan"
  
- **pasal** (string): Article number
  - Example: "1", "2", "5", "33"
  
- **ayat** (string, optional): Paragraph number within article
  - Example: "1", "2", "(1)", "(2)"
  
- **text** (string): The actual legal text content
  - 300-500 tokens per chunk
  - In Bahasa Indonesia

### Vector Fields (for embedding)
- **embedding** (array of 1536 floats): Vector representation using text-embedding-3-large
- **chunk_id** (string): Unique identifier for the chunk
- **document_id** (string): Reference to parent document

## Sample Document Structure

```json
{
  "jenis_dokumen": "UU",
  "nomor": "11",
  "tahun": 2020,
  "judul": "Cipta Kerja",
  "tentang": "Penciptaan Lapangan Kerja",
  "bab": "III",
  "pasal": "5",
  "ayat": "1",
  "text": "Setiap penanam modal berhak mendapatkan kemudahan dan perlindungan untuk menanamkan modalnya di Indonesia...",
  "chunk_id": "uu_11_2020_pasal_5_ayat_1",
  "document_id": "uu_11_2020"
}
```

## Document Hierarchy

```
UU No. 11 Tahun 2020 (Cipta Kerja)
├── Bab I - Ketentuan Umum
│   ├── Pasal 1
│   ├── Pasal 2
│   └── Pasal 3
├── Bab II - Asas dan Tujuan
│   └── Pasal 4
├── Bab III - Penanaman Modal
│   ├── Pasal 5
│   │   ├── Ayat (1)
│   │   ├── Ayat (2)
│   │   └── Ayat (3)
│   └── Pasal 6
└── ...
```

## Citation Format

Standard citation format for responses:
```
Berdasarkan [JENIS_DOKUMEN] No. [NOMOR] Tahun [TAHUN], Pasal [PASAL][, Ayat [AYAT]]
```

Examples:
- `Berdasarkan UU No. 11 Tahun 2020, Pasal 5`
- `Berdasarkan PP No. 24 Tahun 2018, Pasal 10 Ayat (2)`
- `Berdasarkan Perpres No. 49 Tahun 2021, Pasal 3`

## Data Source

Original data from:
- Repository: https://github.com/Open-Technology-Foundation/peraturan.go.id
- Live site: https://peraturan.go.id/
- Data extracted from: JDIHN (Jaringan Dokumentasi dan Informasi Hukum Nasional)

## Processing Pipeline

1. **Export**: Extract from MySQL and text files to `embed_data.text/`
2. **Chunking**: Split documents into 300-500 token segments
3. **Embedding**: Generate vectors using text-embedding-3-large (1536 dimensions)
4. **Storage**: SQLite database (1.1GB) + FAISS index (6.1GB)

## Usage Notes

- Chunks maintain hierarchical context (article numbers, chapter references)
- Full text is preserved in each chunk for context
- Metadata enables filtering by document type, year, or regulation number
- Embeddings enable semantic search across legal concepts
