#!/usr/bin/env python3
"""Stage the Atlas per-county value-of-production (VoP) layer for Block 1.

Source: Atlas hub combined exposure (MapSPAM 2020 crops + GLW4 livestock),
harmonized to the canonical counties in the D409 store. No LLM/
transcription: pass-through of the hub's own VoP values; the only logic is
filtering + a deterministic species-zone merge for readable labels.

Filter to the county (adm1) VoP snapshot in constant international dollars:
  exposure = 'vop', unit = 'intld15', gaul2_code blank (adm1),
  tech = 'all'  (crops — the all-technology aggregate)
    OR tech = '' (livestock — GLW4 carries no technology dimension),
  excluding the 'total-*' livestock roll-ups (would double-count).
Livestock species are then merged across the highland/tropical agro-zones
to one commodity (Cattle, Goats, ...) so the chart reads by commodity.
"""
import csv
import sys
import pyarrow as pa
import pyarrow.parquet as pq

SRC = sys.argv[1]
COUNTY_KEY = sys.argv[2]
OUT = sys.argv[3]

LIVESTOCK = {"cattle", "goats", "sheep", "pigs", "poultry"}


def norm(s):
    return s.lower().replace("-", " ").replace("'", "").strip()


def species(crop):
    # 'cattle-tropical' / 'cattle-highland' -> ('cattle', True); crops -> (crop, False)
    if "-" in crop:
        head, tail = crop.rsplit("-", 1)
        if tail in ("highland", "tropical") and head in LIVESTOCK:
            return head, True
    return crop, False


def label(commodity, is_live):
    return commodity[:1].upper() + commodity[1:].replace("-", " ")


# canonical county -> gaul1_code
ck_rows = pq.read_table(COUNTY_KEY).to_pylist()
gaul_by_norm = {norm(r["county"]): (r["county"], r["gaul1_code"]) for r in ck_rows}

# accumulate VoP per (county, commodity)
acc = {}
unmatched = set()
with open(SRC, newline="") as f:
    for r in csv.DictReader(f):
        if r["exposure"] != "vop" or r["unit"] != "intld15" or r["gaul2_code"]:
            continue
        crop = r["crop"]
        comm, is_live = species(crop)
        if is_live:
            if r["tech"] != "":
                continue
        else:
            if r["tech"] != "all":
                continue
        if comm.startswith("total"):
            continue
        try:
            val = float(r["value"])
        except (ValueError, TypeError):
            continue
        key = norm(r["county"])
        if key not in gaul_by_norm:
            unmatched.add(r["county"])
            continue
        county, gaul1 = gaul_by_norm[key]
        k = (county, gaul1, comm, is_live)
        acc[k] = acc.get(k, 0.0) + val

out = [{"county": c, "gaul1_code": g, "commodity": label(comm, live),
        "kind": "Livestock" if live else "Crop", "vop_intld15": round(v, 2)}
       for (c, g, comm, live), v in acc.items() if v > 0]

if unmatched:
    print("UNMATCHED counties (dropped):", sorted(unmatched))
out.sort(key=lambda d: (d["county"], -d["vop_intld15"]))
print(f"rows={len(out)} counties={len(set(r['county'] for r in out))} "
      f"commodities={len(set(r['commodity'] for r in out))}")

schema = pa.schema([
    ("county", pa.string()), ("gaul1_code", pa.float64()),
    ("commodity", pa.string()), ("kind", pa.string()), ("vop_intld15", pa.float64()),
])
pq.write_table(pa.Table.from_pylist(out, schema=schema), OUT)
print("wrote", OUT)
