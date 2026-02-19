import json
import re
from collections import defaultdict


def normalize_reg(s: str):
    if not s: return None
    return re.sub(r"\s+", " ", s.strip()).upper()


def main():
    # load covered regs
    with open('tests/deepeval/golden_qa.json', 'r', encoding='utf-8') as f:
        golden = json.load(f)
    covered = set()
    for qa in golden:
        regs = qa.get('regulations') or []
        for r in regs:
            rnorm = normalize_reg(r)
            if not rnorm: continue
            # normalize forms like 'UU 40/2007' keep as-is
            covered.add(rnorm)

    # load corpus
    with open('data/external/azzindani/converted.json', 'r', encoding='utf-8') as f:
        corpus = json.load(f)

    groups = defaultdict(list)

    for entry in corpus:
        jenis = (entry.get('jenis_dokumen') or '').strip()
        nomor = str(entry.get('nomor') or '').strip()
        tahun = entry.get('tahun')
        # build reg key only when jenis and nomor and tahun present
        if not jenis or not nomor or not tahun:
            continue
        # normalize nomor (remove non-breaking spaces)
        nomor_norm = nomor
        reg_key = f"{jenis} {nomor_norm}/{int(tahun)}" if isinstance(tahun, int) else f"{jenis} {nomor_norm}/{tahun}"
        groups[reg_key].append(entry)

    # filter and collect
    regs = []
    for reg_key, entries in groups.items():
        # parse reg_key
        m = re.match(r"^(?P<jenis>\S+)\s+(?P<nomor>[^/]+)/(?P<tahun>\d{4})$", reg_key)
        if not m:
            continue
        jenis = m.group('jenis')
        nomor = m.group('nomor').strip()
        tahun = int(m.group('tahun'))

        # exclude malformed nomor (must be numeric)
        if not re.fullmatch(r"\d+", nomor):
            continue

        # exclude covered regs
        if normalize_reg(reg_key) in covered:
            continue

        chunks = [e.get('text','').strip() for e in entries if e.get('text')]
        # remove empty chunks
        chunks = [c for c in chunks if c]
        if len(chunks) < 5:
            continue

        # pick judul and tentang from first entry with those fields
        judul = next((e.get('judul') for e in entries if e.get('judul')), '')
        tentang = next((e.get('tentang') for e in entries if e.get('tentang')), '')

        regs.append({
            'reg_key': f"{jenis} {nomor}/{tahun}",
            'jenis_dokumen': jenis,
            'nomor': nomor,
            'tahun': tahun,
            'judul': judul or '',
            'tentang': tentang or '',
            'chunk_count': len(chunks),
            'chunks': chunks,
        })

    # rank by chunk_count desc
    regs.sort(key=lambda x: x['chunk_count'], reverse=True)

    # desired distribution
    targets = {'PP':25, 'UU':15, 'Perda':20}
    # clamp targets to 60 total
    total_target = 60
    # selection: first pass try to satisfy targets by picking top regs while respecting per-type target
    selected = []
    counts = defaultdict(int)

    for reg in regs:
        typ = reg['jenis_dokumen']
        want = targets.get(typ, 0)
        if want > counts[typ] and len(selected) < total_target:
            selected.append(reg)
            counts[typ] += 1

    # second pass: fill up to 60 ignoring type limits
    if len(selected) < total_target:
        for reg in regs:
            if reg in selected: continue
            if len(selected) >= total_target: break
            selected.append(reg)

    # ensure at least 56 regs
    if len(selected) < 56:
        # try to add more if available
        for reg in regs:
            if reg in selected: continue
            selected.append(reg)
            if len(selected) >= 56:
                break

    # final write
    out = selected[:total_target]
    with open('priority_regulations.json', 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(out)} regs to priority_regulations.json")


if __name__ == '__main__':
    main()
