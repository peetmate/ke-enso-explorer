#!/usr/bin/env python3
"""Stage FEWS NET cross-border trade (XBT) for the ENSO Explorer.

Kenya-touching flows only (destination=Kenya -> Import; source=Kenya ->
Export). NATIONAL/border-point resolution, not county — a national supply
context layer for Block 4. No LLM/transcription: pass-through of the
banked CSV's own numeric qty; partner->iso3 is a fixed reference code map
(country codes, not data) so the notebook can join partners to the admin0
topojson and place flow arrows at computed centroids (no typed coords).
"""
import csv
import sys
import pyarrow as pa
import pyarrow.parquet as pq

SRC = sys.argv[1]
OUT = sys.argv[2]

# partner country name (as written in the FEWS file) -> ISO3 (matches the
# admin0 topojson iso3). Reference codes, not analytical values.
ISO3 = {
    "Ethiopia": "ETH", "Uganda": "UGA", "Tanzania": "TZA", "Somalia": "SOM",
    "South Sudan": "SSD", "Sudan": "SDN", "Rwanda": "RWA", "Malawi": "MWI",
    "Zambia": "ZMB", "Democratic Republic of the Congo": "COD",
    "Congo (Brazzaville)": "COG",
}

out = []
skipped_partner = set()
with open(SRC, newline="") as f:
    for r in csv.DictReader(f):
        src, dst = r["source"], r["destination"]
        if dst == "Kenya" and src != "Kenya":
            direction, partner = "Import", src
        elif src == "Kenya" and dst != "Kenya":
            direction, partner = "Export", dst
        else:
            continue  # transit / non-Kenya-touching
        iso3 = ISO3.get(partner)
        if iso3 is None:
            skipped_partner.add(partner)
            continue
        try:
            qty = float(r["qty"])
        except (ValueError, TypeError):
            continue
        out.append({
            "partner": partner, "partner_iso3": iso3, "direction": direction,
            "trade_type": r["trade_type"], "product": r["product"],
            "border_point": r["border_point"], "period_date": r["period_date"],
            "year": int(r["year"]), "month": int(r["period_date"][5:7]),
            "qty": qty, "qty_unit": r["qty_unit"],
        })

if skipped_partner:
    print("skipped partners (no iso3 map):", sorted(skipped_partner))
out.sort(key=lambda d: (d["product"], d["period_date"]))
print(f"rows={len(out)} products={len(set(r['product'] for r in out))} "
      f"partners={sorted(set(r['partner'] for r in out))}")
print("directions:", {d: sum(1 for r in out if r['direction'] == d) for d in ('Import', 'Export')})

schema = pa.schema([
    ("partner", pa.string()), ("partner_iso3", pa.string()), ("direction", pa.string()),
    ("trade_type", pa.string()), ("product", pa.string()), ("border_point", pa.string()),
    ("period_date", pa.string()), ("year", pa.int32()), ("month", pa.int32()),
    ("qty", pa.float64()), ("qty_unit", pa.string()),
])
pq.write_table(pa.Table.from_pylist(out, schema=schema), OUT)
print("wrote", OUT)
