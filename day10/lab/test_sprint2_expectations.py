#!/usr/bin/env python3
"""
Test expectations for Sprint 2 (Member 2)
Running without heavy ML dependencies - simulating pipeline output
"""
import csv
import json
import sys
from pathlib import Path
from datetime import datetime, timezone
import hashlib

# Add imports
sys.path.insert(0, str(Path.cwd()))
from quality.expectations import run_expectations

# Load the raw CSV
raw_path = Path("data/raw/policy_export_dirty.csv")
print(f"Loading raw CSV: {raw_path}")

rows = []
with raw_path.open(encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    for r in reader:
        rows.append({k: (v or "").strip() for k, v in r.items()})

print(f"Loaded {len(rows)} raw rows")

# Simulate basic cleaning operations (without full pipeline)
cleaned = []
quarantine = []

ALLOWED_DOC_IDS = frozenset({"policy_refund_v4", "sla_p1_2026", "it_helpdesk_faq", "hr_leave_policy"})

for i, row in enumerate(rows):
    # Check: doc_id must be in allowlist
    if row.get("doc_id") not in ALLOWED_DOC_IDS:
        quarantine.append(row)
        continue
        
    # Check: empty chunk_text
    if not row.get("chunk_text"):
        quarantine.append(row)
        continue
        
    # Generate chunk_id for idempotency
    doc_id = row.get("doc_id", "")
    chunk_text = row.get("chunk_text", "")
    h = hashlib.sha256(f"{doc_id}|{chunk_text}|{i}".encode("utf-8")).hexdigest()[:16]
    row["chunk_id"] = f"{doc_id}_{i}_{h}"
    
    cleaned.append(row)

print(f"After basic clean: {len(cleaned)} cleaned, {len(quarantine)} quarantine")

# Run expectations on cleaned data
results, halt = run_expectations(cleaned)

print("\n" + "="*70)
print("EXPECTATION RESULTS (Sprint 2 - Member 2)")
print("="*70)

for r in results:
    sym = "PASS" if r.passed else "FAIL"
    print(f"  [{sym}] [{r.severity.upper():4}]  {r.name:40} :: {r.detail}")

print("\n" + "="*70)
halt_status = "HALT" if halt else "OK"
print(f"Pipeline Status: {halt_status}")
if halt:
    print("⚠  EXPECTATION FAILED - Pipeline would halt at this point")
print("="*70)

# Create artifacts directory
art_dir = Path("artifacts")
log_dir = art_dir / "logs"
man_dir = art_dir / "manifests"
clean_dir = art_dir / "cleaned"
quar_dir = art_dir / "quarantine"

for d in [log_dir, man_dir, clean_dir, quar_dir]:
    d.mkdir(parents=True, exist_ok=True)

# Write logs
run_id = "sprint2_member2"
log_file = log_dir / f"run_{run_id}.log"
with log_file.open("w", encoding="utf-8") as f:
    f.write(f"run_id={run_id}\n")
    f.write(f"run_timestamp={datetime.now(timezone.utc).isoformat()}\n")
    f.write(f"raw_records={len(rows)}\n")
    f.write(f"cleaned_records={len(cleaned)}\n")
    f.write(f"quarantine_records={len(quarantine)}\n")
    f.write(f"cleaned_csv=artifacts/cleaned/cleaned_{run_id}.csv\n")
    f.write(f"quarantine_csv=artifacts/quarantine/quarantine_{run_id}.csv\n")
    f.write("\n# Expectation Results:\n")
    for r in results:
        sym = "OK" if r.passed else "FAIL"
        f.write(f"expectation[{r.name}] {sym} ({r.severity}) :: {r.detail}\n")
    pipeline_status = "PIPELINE_OK" if not halt else "PIPELINE_HALT"
    f.write(f"{pipeline_status}\n")

print(f"✓ Log written: artifacts/logs/run_{run_id}.log")

# Write manifest
manifest = {
    "run_id": run_id,
    "run_timestamp": datetime.now(timezone.utc).isoformat(),
    "raw_path": "data/raw/policy_export_dirty.csv",
    "raw_records": len(rows),
    "cleaned_records": len(cleaned),
    "quarantine_records": len(quarantine),
    "cleaned_csv": "artifacts/cleaned/cleaned_{}.csv".format(run_id),
    "quarantine_csv": "artifacts/quarantine/quarantine_{}.csv".format(run_id),
    "expectations_total": len(results),
    "expectations_passed": sum(1 for r in results if r.passed),
    "expectations_failed": sum(1 for r in results if not r.passed),
    "halt": halt,
    "chroma_collection": "day10_kb",
}
man_file = man_dir / f"manifest_{run_id}.json"
man_file.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"✓ Manifest written: artifacts/manifests/manifest_{run_id}.json")

# Write cleaned CSV
if cleaned:
    fieldnames = list(cleaned[0].keys())
    with (clean_dir / f"cleaned_{run_id}.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in cleaned:
            writer.writerow(row)
    print(f"✓ Cleaned CSV written: {len(cleaned)} rows to artifacts/cleaned/cleaned_{run_id}.csv")

if quarantine:
    fieldnames = list(quarantine[0].keys())
    with (quar_dir / f"quarantine_{run_id}.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in quarantine:
            writer.writerow(row)
    print(f"✓ Quarantine CSV written: {len(quarantine)} rows to artifacts/quarantine/quarantine_{run_id}.csv")

print("\n✓ Sprint 2 test complete!")
sys.exit(0 if not halt else 2)
