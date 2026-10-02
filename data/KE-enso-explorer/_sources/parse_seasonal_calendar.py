#!/usr/bin/env python3
"""Deterministic parse of the JRC ASAP sub-national crop calendar into a
per-county planting/harvest month-segment table for the ENSO Explorer.

Source: JRC ASAP crop_calendar_gaul1.csv (dekad resolution, GAUL admin1).
No LLM/transcription — pure CSV -> arithmetic -> parquet. Dekads are the
36-per-year ASAP convention (3 per month); a dekad d maps to calendar
month ((d-1)//3) % 12 + 1. Harvest windows can wrap the year boundary
(e.g. eos_s=35 Dec -> eos_e=4 Feb); wrapped ranges are split into two
contiguous month segments so a 1-12 month axis needs no wrap logic.
"""
import csv
import sys
import pyarrow as pa
import pyarrow.parquet as pq

SRC = sys.argv[1]
COUNTY_KEY = sys.argv[2]
OUT = sys.argv[3]

# ASAP short name -> our canonical county name (only where they differ).
# ASAP truncates to <=16 chars and uses the older district spellings.
ALIASES = {
    "Keiyo-Marakwet": "Elgeyo Marakwet",
    "Tharaka": "Tharaka Nithi",
}
# rows we cannot / must not place on the canonical 47. "Malindi" is an old
# Coast district now inside Kilifi county — ASAP also carries a separate
# "Kilifi" row, so keeping both would double-count the county; drop Malindi.
DROP = {"Unit unavailable", "Malindi"}


def norm(s):
    return s.lower().replace("-", " ").replace("'", "").strip()


def dekad_to_month(d):
    # ASAP dekads run 1..36 (occasionally >36 when a window wraps); modulo
    # keeps us on 1..12
    return ((int(d) - 1) // 3) % 12 + 1


def month_segments(d_start, d_end):
    """Return a list of (m_start, m_end) contiguous month runs for a dekad
    range, splitting when the range wraps past December."""
    ms, me = dekad_to_month(d_start), dekad_to_month(d_end)
    if ms <= me:
        return [(ms, me)]
    return [(ms, 12), (1, me)]  # wrapped: Dec-tail + Jan-head


# canonical county -> gaul1_code
ck_rows = pq.read_table(COUNTY_KEY).to_pylist()
gaul_by_norm = {norm(r["county"]): (r["county"], r["gaul1_code"]) for r in ck_rows}

out = []
unmatched = set()
with open(SRC, newline="") as f:
    for r in csv.DictReader(f, delimiter=";"):
        if r["name0_shr"] != "Kenya":
            continue
        asap_name = r["name1_shr"]
        if asap_name in DROP:
            continue
        canon_name = ALIASES.get(asap_name, asap_name)
        key = norm(canon_name)
        if key not in gaul_by_norm:
            unmatched.add(asap_name)
            continue
        county, gaul1_code = gaul_by_norm[key]
        # "Maize (Long rains)" -> crop="Maize", season="Long rains"
        cn = r["crop_name"]
        crop, season = cn, ""
        if "(" in cn:
            crop = cn[:cn.index("(")].strip()
            season = cn[cn.index("(") + 1:cn.rindex(")")].strip()
        for stage, ds, de in [("Planting", r["sos_s"], r["sos_e"]),
                              ("Harvest", r["eos_s"], r["eos_e"])]:
            for m_start, m_end in month_segments(ds, de):
                out.append({
                    "county": county,
                    "gaul1_code": gaul1_code,
                    "crop": crop,
                    "season": season,
                    "stage": stage,
                    "m_start": m_start,
                    "m_end": m_end,
                    "dekad_start": int(ds),
                    "dekad_end": int(de),
                })

if unmatched:
    print("UNMATCHED ASAP units (dropped):", sorted(unmatched))
counties = sorted(set(r["county"] for r in out))
print(f"rows={len(out)} counties={len(counties)}")
print("counties:", counties)

schema = pa.schema([
    ("county", pa.string()), ("gaul1_code", pa.float64()),
    ("crop", pa.string()), ("season", pa.string()), ("stage", pa.string()),
    ("m_start", pa.int32()), ("m_end", pa.int32()),
    ("dekad_start", pa.int32()), ("dekad_end", pa.int32()),
])
pq.write_table(pa.Table.from_pylist(out, schema=schema), OUT)
print("wrote", OUT)
