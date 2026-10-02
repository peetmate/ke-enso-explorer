#!/usr/bin/env python3
"""Build data/KE-enso-explorer/provenance.json — the ONE generated projection the
KE-ENSO Explorer renders provenance from (drawer + Section 6 tab-methods).

Contract: hazards_prototype/HANDOVER_2026-09-18_provenance-drawer-and-metadata-gaps.md
  §1a  the notebook renders from a generated projection and never becomes a third copy
  §1b  the projection shape, and the two orthogonal axes `state` and `hosting`
  §1c  which fields are always visible / never collapsed / collapsible
  §1e  no Atlas asset link for a dataset whose bytes are not ours; never paraphrase `note`

Inputs (read-only; nothing in hazards_prototype is written):
  metadata/cdh/*.yaml            authoritative outward-facing records (CDH v0.3.0)
  metadata/cdh/draft/*.yaml      records that only pass `validate-yaml.js --draft`
  metadata/catalogue/*.json      internal host/transfer inventory (issue #29)
  metadata/cdh/README.md         cdh-catalog PR number + submission state per record
  _sources/provenance_keymap.json  notebook handle -> record id routing (ids only)

`state` is PROBED, not assumed: when a cdh-metadata-standard checkout is available the
real validator decides authored vs draft. Point CDH_STD at it, or let the script find
/tmp/cdh-std. Without it every record falls back to a schema-version probe and each
entry records `state_basis: "version-probe"` so a soft check never masquerades as a
hard one.

Usage
  uv run --with pyyaml python data/KE-enso-explorer/_sources/provenance_build.py
  CDH_STD=/path/to/cdh-metadata-standard  ... (optional, enables strict validation)
  PROVENANCE_GATE_STATUS=/path/to/gates.json ... (optional, see GATES below)

GATES: a JSON object {"<key>": {"name": ..., "result": "PASS|FAIL", "value": ...,
"ref": ...}}. Merged verbatim into entry.gates[]. This is how a live QA gate (e.g.
R/checks/vop_align_live_gate.R) reaches the drawer without anyone re-typing its verdict
into the notebook.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
NB_REPO = HERE.parents[2]                       # atlas_notebooks worktree root
KEYMAP = HERE / "provenance_keymap.json"
OUT = HERE.parent / "provenance.json"

CDH_CATALOG = "https://github.com/CGIAR-Climate-Data-Hub/cdh-catalog"

# Licences that oblige the reuser to attribute at all.
ATTRIBUTION_REQUIRED = ("CC-BY", "ODbL", "LicenseRef-Copernicus", "LicenseRef-KNBS")
# Licences that mandate a SPECIFIC wording. The drawer must show these verbatim, and a
# record that carries one of these licences without the string is a real gap.
VERBATIM_ATTRIBUTION = ("ODbL", "LicenseRef-Copernicus", "LicenseRef-KNBS")

# Ordered, deliberately narrow: each pattern anchors on an explicit attribution lead-in
# so the captured group is the mandated wording and not the next quoted phrase in the
# note. Whatever is captured is passed through byte-for-byte.
ATTRIBUTION_RES = (
    re.compile(r'[Rr]equired attribution[^"]{0,90}"([^"]+)"'),
    re.compile(r'[Aa]ttribution required:\s*"([^"]+)"'),
    re.compile(r'attribution\s+"([^"]+)"'),
)


# --------------------------------------------------------------------------- io

def die(msg: str) -> None:
    sys.stderr.write(f"provenance_build: {msg}\n")
    raise SystemExit(1)


def load_keymap() -> dict:
    km = json.loads(KEYMAP.read_text())
    root = (KEYMAP.parent / km["hazards_prototype_root"]).resolve()
    if not (root / "metadata" / "cdh").is_dir():
        die(
            f"hazards_prototype metadata not found at {root}.\n"
            f"  Fix hazards_prototype_root in {KEYMAP.name} or clone the pipeline repo "
            f"beside this one."
        )
    km["_root"] = root
    return km


def find_validator() -> Path | None:
    for cand in (os.environ.get("CDH_STD"), "/tmp/cdh-std"):
        if not cand:
            continue
        p = Path(cand) / "scripts" / "validate-yaml.js"
        if p.is_file() and (Path(cand) / "node_modules").is_dir():
            return p
    return None


def validate(validator: Path, record: Path, draft: bool) -> tuple[bool, list[str]]:
    """Run the real cdh-metadata-standard validator. Returns (ok, errors)."""
    profile = validator.parent.parent / "spec" / "schemas" / "profiles" / "cdh.schema.json"
    cmd = ["node", str(validator), "--profile", str(profile)]
    if draft:
        cmd.append("--draft")
    cmd.append(str(record))
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as exc:       # node missing / hung
        return False, [f"validator could not run: {exc}"]
    out = (r.stdout + r.stderr).strip()
    if r.returncode == 0:
        return True, []
    errs = [ln.strip() for ln in out.splitlines() if ln.strip() and not ln.startswith("FAIL")]
    return False, errs


def parse_catalog_prs(root: Path) -> dict[str, dict]:
    """Read the PR / submission-state table out of metadata/cdh/README.md.

    The manifest is the upstream store's own record of where each YAML sits in
    cdh-catalog. Parsing it keeps that fact out of the notebook.
    """
    readme = root / "metadata" / "cdh" / "README.md"
    if not readme.is_file():
        return {}
    prs: dict[str, dict] = {}
    row = re.compile(
        r"^\|\s*([a-z0-9_.-]+)\s*\|\s*\[#(\d+)\]\((https://[^)]+)\)\s*\|\s*([^|]+?)\s*\|"
    )
    for line in readme.read_text().splitlines():
        m = row.match(line)
        if m:
            prs[m.group(1)] = {
                "number": int(m.group(2)),
                "url": m.group(3),
                "submission_state": m.group(4).strip(),
            }
    return prs


# ------------------------------------------------------------------ projection

def paragraphs(text: str | None) -> list[str]:
    """Split `note` into paragraphs VERBATIM. Never reflowed, never truncated.

    CDH notes are YAML folded scalars (`>`), so a blank source line survives as a
    single \\n. Splitting on newlines therefore recovers the authored paragraphs
    and changes not one character inside them.
    """
    if not text:
        return []
    return [p.strip() for p in str(text).split("\n") if p.strip()]


def attribution_of(rec: dict) -> tuple[str | None, bool, bool]:
    """Pull the attribution string verbatim out of `note`.

    Returns (string, attribution_required, verbatim_required).
    """
    lic = str(rec.get("license") or "")
    required = any(lic.startswith(p) for p in ATTRIBUTION_REQUIRED)
    verbatim = any(lic.startswith(p) for p in VERBATIM_ATTRIBUTION)
    note = str(rec.get("note") or "")
    for pat in ATTRIBUTION_RES:
        m = pat.search(note)
        if m:
            return m.group(1), required, verbatim
    return None, required, verbatim


def licence_link(rec: dict) -> str | None:
    for link in rec.get("additional_links") or []:
        if link.get("rel") == "license":
            return link.get("url")
    return None


def render_citation(rec: dict) -> dict | None:
    c = rec.get("citation")
    dois = [p["doi"] for p in (rec.get("related_publications") or []) if p.get("doi")]
    if not c:
        if rec.get("doi"):
            return {"text": None, "url": f"https://doi.org/{rec['doi']}", "dois": dois}
        return {"text": None, "url": None, "dois": dois} if dois else None
    authors = c.get("authors") or []
    bits = []
    if authors:
        bits.append("; ".join(authors))
    if c.get("date"):
        bits.append(f"({c['date']})")
    if c.get("title"):
        bits.append(str(c["title"]).rstrip(".") + ".")
    if c.get("publisher"):
        bits.append(str(c["publisher"]).rstrip(".") + ".")
    return {"text": " ".join(bits) or None, "url": c.get("url"), "dois": dois}


def render_coverage(rec: dict) -> dict:
    sp = rec.get("spatial") or {}
    geo = ", ".join(sp.get("geography") or []) or None
    res = None
    for r in sp.get("resolution") or []:
        res = r.get("label") or (
            f"{r.get('value')} {r.get('unit')}".strip() if r.get("value") is not None else None
        )
        if res:
            break
    spatial = " — ".join(x for x in (geo, res) if x) or None

    tm = rec.get("temporal") or {}
    if tm.get("date"):
        temporal = str(tm["date"])
    elif tm.get("start_date"):
        end = tm.get("end_date")
        temporal = f"{tm['start_date']} to {end if end else 'present (open-ended)'}"
    else:
        temporal = None
    return {
        "spatial": spatial,
        "temporal": temporal,
        "crs": sp.get("crs"),
        "bbox": sp.get("bbox"),
    }


def render_assets(rec: dict) -> list[dict]:
    out = []
    for a in rec.get("data") or []:
        https = s3 = None
        others = []
        for loc in a.get("locations") or []:
            url = loc.get("url")
            if not url:
                continue
            if url.startswith("s3://") and s3 is None:
                s3 = url
            elif url.startswith("http") and https is None:
                https = url
            else:
                others.append(url)
        out.append({
            "name": a.get("name"),
            "description": a.get("description"),
            "https": https,
            "s3": s3,
            "other_locations": others,
            "media_type": a.get("media_type"),
            "href_template": a.get("href_template"),
            "file_size": a.get("file_size"),
            "nodata": a.get("nodata"),
            "processing_steps": a.get("processing_steps") or [],
        })
    return out


def render_processing(rec: dict) -> tuple[list[dict], list[dict]]:
    steps, upstream, seen = [], [], set()
    for p in rec.get("processing") or []:
        code = p.get("code") or {}
        steps.append({
            "id": p.get("id"),
            "description": p.get("description"),
            "date": p.get("date"),
            "code": code.get("version"),
            "code_url": code.get("url"),
            "derived_from": p.get("derived_from") or [],
        })
        for d in p.get("derived_from") or []:
            k = (d.get("title"), d.get("url"))
            if k not in seen:
                seen.add(k)
                upstream.append({"title": d.get("title"), "url": d.get("url")})
    return steps, upstream


def hosting_of(rec: dict | None, cat: dict | None) -> tuple[str, list[str]]:
    """`hosting` = whose bytes the reader is about to fetch (contract §1b)."""
    urls: list[str] = []
    if rec:
        for a in rec.get("data") or []:
            urls += [l.get("url", "") for l in (a.get("locations") or [])]
    atlas_urls = [u for u in urls if "digital-atlas" in u]
    if atlas_urls:
        return "atlas", atlas_urls
    if rec and urls:
        return "federated", []
    if cat and (cat.get("atlas_s3") or {}).get("prefix"):
        return "atlas", [cat["atlas_s3"]["prefix"]]
    return "unknown", []


def build_entry(spec: dict, root: Path, validator: Path | None,
                prs: dict, gates: dict) -> dict:
    key = spec["key"]
    cdh_id, cat_id = spec.get("cdh"), spec.get("catalogue")

    cdh_path = draft_path = None
    if cdh_id:
        p = root / "metadata" / "cdh" / f"{cdh_id}.yaml"
        d = root / "metadata" / "cdh" / "draft" / f"{cdh_id}.yaml"
        if p.is_file():
            cdh_path = p
        elif d.is_file():
            cdh_path = draft_path = d

    rec = yaml.safe_load(cdh_path.read_text()) if cdh_path else None
    cat = None
    if cat_id:
        cp = root / "metadata" / "catalogue" / f"{cat_id}.json"
        if cp.is_file():
            cat = json.loads(cp.read_text())

    gaps: list[str] = []
    state_basis = "no-record"
    errors: list[str] = []

    # ---- state: how mature the metadata is (probed, never assumed) -----------
    if rec is None:
        state = "catalogue-only" if cat else "undocumented"
        if cdh_id:
            gaps.append(f"Keymap points at CDH record '{cdh_id}' but no such file exists.")
        elif state == "catalogue-only":
            gaps.append("No CDH record: licence, citation and caveats are not authored yet.")
        else:
            gaps.append("No CDH record and no catalogue record — provenance not documented.")
    else:
        ver = str(rec.get("cdh_schema_version") or "")
        if draft_path:
            state, state_basis = "draft", "draft-directory"
            gaps.append("Held as a draft record; not submitted to cdh-catalog.")
        elif ver != "v0.3.0":
            state, state_basis = "draft", "version-probe"
            gaps.append(f"CDH record is schema {ver or 'unversioned'}, not v0.3.0.")
        elif validator:
            ok, errors = validate(validator, cdh_path, draft=False)
            if ok:
                state, state_basis = "authored", "validator-strict"
            else:
                ok_d, _ = validate(validator, cdh_path, draft=True)
                state = "draft" if ok_d else "invalid"
                state_basis = "validator-draft" if ok_d else "validator-failed"
                gaps.append(
                    "CDH record does not pass strict validation: " + "; ".join(errors[:6])
                )
        else:
            state, state_basis = "authored", "version-probe"

    # ---- hosting: whose bytes (orthogonal to state) --------------------------
    hosting, atlas_urls = hosting_of(rec, cat)

    assets = render_assets(rec) if rec else []
    # §1e — never show an Atlas link for something the Atlas does not publish.
    if hosting != "atlas":
        for a in assets:
            for f in ("https", "s3"):
                if a[f] and "digital-atlas" in a[f]:
                    gaps.append(
                        f"Asset '{a['name']}' declared a digital-atlas location on a "
                        f"{hosting} dataset; link withheld (contract §1e)."
                    )
                    a[f] = None

    steps, upstream = render_processing(rec) if rec else ([], [])
    attribution, attribution_required, verbatim_required = (
        attribution_of(rec) if rec else (None, False, False)
    )
    if verbatim_required and not attribution:
        gaps.append(
            "Licence mandates a specific attribution wording, but no quoted attribution "
            "string was found in `note` — the drawer has nothing verbatim to show."
        )

    if cat:
        gaps += list(cat.get("gaps") or [])
        if cat.get("status") and cat["status"] != "current":
            gaps.append(f"Catalogue status: {cat['status']}.")

    title = (rec or {}).get("title") or (cat or {}).get("title") or spec.get("label")
    title_source = (
        "cdh" if (rec or {}).get("title")
        else "catalogue" if (cat or {}).get("title")
        else "notebook-label"
    )
    if title is None:
        title, title_source = key, "key"

    usage = ((rec or {}).get("cdh") or {}).get("usage") or {}
    pr = prs.get(cdh_id) if cdh_id else None

    entry = {
        "key": key,
        "aliases": spec.get("aliases") or [],
        "title": title,
        "title_source": title_source,
        "category": spec.get("category"),
        "state": state,
        "state_basis": state_basis,
        "hosting": hosting,
        "settled": state == "authored",
        "summary": (rec or {}).get("description") or (cat or {}).get("description"),

        "licence": {
            "id": (rec or {}).get("license") or (cat or {}).get("origin", {}).get("license"),
            "url": licence_link(rec) if rec else (cat or {}).get("origin", {}).get("url"),
            "attribution": attribution,
            "attribution_required": attribution_required,
            "attribution_verbatim_required": verbatim_required,
            "access": (rec or {}).get("access", "public" if rec else None),
            "access_note": (rec or {}).get("access_note"),
        },
        "producer": [
            {
                "organization": c.get("organization"),
                "name": c.get("name"),
                "url": c.get("url"),
                "email": c.get("email"),
                "roles": c.get("roles") or [],
            }
            for c in ((rec or {}).get("contact") or [])
        ],
        "citation": render_citation(rec) if rec else None,

        # NEVER collapsed, never paraphrased, never truncated (contract §1c).
        "caveats": paragraphs((rec or {}).get("note")),
        "avoid": usage.get("not_recommended_for") or [],
        "intended_uses": usage.get("intended_uses") or [],

        "coverage": render_coverage(rec) if rec else {
            "spatial": None, "temporal": None, "crs": None, "bbox": None
        },
        "assets": assets,
        "upstream": upstream,
        "processing": steps,
        "technical": {
            "dimensions": (rec or {}).get("dimensions") or [],
            "variables": (rec or {}).get("variables") or [],
            "joins": (rec or {}).get("joins") or [],
            "resource_type": (rec or {}).get("resource_type"),
            "keywords": (rec or {}).get("keywords") or [],
            "domain": ((rec or {}).get("cdh") or {}).get("domain") or [],
            "schema_version": (rec or {}).get("cdh_schema_version"),
            "created": (rec or {}).get("created"),
            "updated": (rec or {}).get("updated"),
        },
        "record": {
            "cdh": str(cdh_path.relative_to(root)) if cdh_path else None,
            "catalogue": f"metadata/catalogue/{cat_id}.json" if cat else None,
            "catalog_pr": (pr or {}).get("url"),
            "catalog_pr_state": (pr or {}).get("submission_state"),
            "published_record": (
                f"{CDH_CATALOG}/blob/main/records/{cdh_id}/{cdh_id}.yaml"
                if pr and "merged" in str(pr.get("submission_state", "")).lower() else None
            ),
        },
        "notebook": {
            "files": spec.get("notebook_files") or [],
            "built_by": spec.get("built_by"),
            "related": spec.get("related") or [],
            "search_terms": spec.get("search_terms"),
        },
        "gates": gates.get(key, []) if isinstance(gates.get(key), list) else (
            [gates[key]] if key in gates else []
        ),
        "gaps": gaps,
    }
    return entry


def main() -> None:
    km = load_keymap()
    root: Path = km["_root"]
    validator = find_validator()
    prs = parse_catalog_prs(root)

    gates = {}
    gp = os.environ.get("PROVENANCE_GATE_STATUS")
    if gp and Path(gp).is_file():
        gates = json.loads(Path(gp).read_text())

    entries = [build_entry(s, root, validator, prs, gates) for s in km["entries"]]

    # Alias collisions would make openMethodDrawer() resolve to the wrong dataset —
    # exactly the live bug this projection replaces. Fail the build instead.
    seen: dict[str, str] = {}
    for e in entries:
        for name in [e["key"], *e["aliases"]]:
            if name in seen:
                die(f"duplicate key/alias '{name}' on '{e['key']}' and '{seen[name]}'")
            seen[name] = e["key"]
    for e in entries:
        for r in e["notebook"]["related"]:
            if r not in seen:
                die(f"entry '{e['key']}' relates to unknown key '{r}'")

    doc = {
        "generated_by": "data/KE-enso-explorer/_sources/provenance_build.py",
        "contract": "hazards_prototype/HANDOVER_2026-09-18_provenance-drawer-and-metadata-gaps.md §1",
        "sources": {
            "cdh": "hazards_prototype/metadata/cdh/",
            "catalogue": "hazards_prototype/metadata/catalogue/",
            "validator": str(validator) if validator else None,
        },
        "state_values": ["authored", "draft", "invalid", "catalogue-only", "undocumented"],
        "hosting_values": ["atlas", "federated", "unknown"],
        "aliases": seen,
        "categories": km["categories"],
        "entries": entries,
    }
    OUT.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")

    tally: dict[str, int] = {}
    for e in entries:
        tally[e["state"]] = tally.get(e["state"], 0) + 1
    print(f"wrote {OUT.relative_to(NB_REPO)}  ({len(entries)} entries)")
    print(f"  validator: {validator or 'NOT FOUND — state is a version probe only'}")
    print("  state: " + ", ".join(f"{k}={v}" for k, v in sorted(tally.items())))
    undoc = [e["key"] for e in entries if e["state"] in ("undocumented", "catalogue-only")]
    if undoc:
        print("  needs a CDH record: " + ", ".join(undoc))


if __name__ == "__main__":
    main()
