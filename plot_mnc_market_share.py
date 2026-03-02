"""
plot_mnc_market_share.py

Plots the market share of Mobile Network Operators (MNOs) based on the
MCC/MNC pairs captured in database/imsi.db, resolved to operator and
country names via mcc-mnc.json.

Produces a pie chart showing each operator's share, labelled with both
the network name and its country.
"""

import json
import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# Paths (relative to this script's location)
# ---------------------------------------------------------------------------
BASE_DIR  = Path(__file__).parent
DB_PATH   = BASE_DIR / "database" / "imsi.db"
JSON_PATH = BASE_DIR / "mcc-mnc.json"

# ---------------------------------------------------------------------------
# 1. Load MCC/MNC → network name lookup from mcc-mnc.json
# ---------------------------------------------------------------------------
with open(JSON_PATH, "r", encoding="utf-8") as fh:
    mnc_data = json.load(fh)

# Key: (mcc_str_zero_padded, mnc_str_zero_padded) → (network, country)
mnc_lookup: dict[tuple[str, str], tuple[str, str]] = {}
for entry in mnc_data["data"]:
    mcc = str(entry["mcc"]).zfill(3)
    mnc = str(entry["mnc"]).zfill(2)
    network = entry.get("network") or entry.get("country", "Unknown")
    country = entry.get("country", "")
    mnc_lookup[(mcc, mnc)] = (network, country)

# ---------------------------------------------------------------------------
# 2. Query capture counts from imsi.db
# ---------------------------------------------------------------------------
if not DB_PATH.exists():
    raise FileNotFoundError(f"Database not found: {DB_PATH}")

conn = sqlite3.connect(DB_PATH)
rows = conn.execute(
    "SELECT mcc, mnc, COUNT(*) AS cnt "
    "FROM imsi_data "
    "GROUP BY mcc, mnc "
    "ORDER BY cnt DESC"
).fetchall()
conn.close()

if not rows:
    print("No IMSI records found in the database – nothing to plot.")
    raise SystemExit(0)

# ---------------------------------------------------------------------------
# 3. Resolve operator names
# ---------------------------------------------------------------------------
labels: list[str] = []
counts: list[int] = []

for mcc_raw, mnc_raw, cnt in rows:
    mcc = str(mcc_raw).zfill(3)
    mnc = str(mnc_raw).zfill(2)
    entry = mnc_lookup.get((mcc, mnc))
    if entry is None:
        # Try with zero-padded MNC of length 3
        mnc3 = str(mnc_raw).zfill(3)
        entry = mnc_lookup.get((mcc, mnc3))
    if entry is not None:
        network, country = entry
        name = f"{network}\n({country})" if country else network
    else:
        name = f"MCC {mcc} / MNC {mnc}"
    labels.append(name)
    counts.append(cnt)

total = sum(counts)

# ---------------------------------------------------------------------------
# 4. Create figures
# ---------------------------------------------------------------------------
fig, ax_pie = plt.subplots(1, 1, figsize=(9, 7))
fig.suptitle("MNO Market Share in GSM Capture", fontsize=16, fontweight="bold")

# If there are many small slices, group them into "Other"
THRESHOLD_PCT = 2.0          # operators below this % are grouped
THRESHOLD     = THRESHOLD_PCT / 100 * total

main_labels, main_counts, other_count = [], [], 0
for lbl, cnt in zip(labels, counts):
    if cnt / total * 100 < THRESHOLD_PCT and len(counts) > 6:
        other_count += cnt
    else:
        main_labels.append(lbl)
        main_counts.append(cnt)

if other_count:
    main_labels.append(f"Other (< {THRESHOLD_PCT:.0f}%)")
    main_counts.append(other_count)

wedge_props = {"edgecolor": "white", "linewidth": 1.5}
wedges, texts, autotexts = ax_pie.pie(
    main_counts,
    labels=main_labels,
    autopct=lambda p: f"{p:.1f}%" if p >= 1 else "",
    startangle=140,
    wedgeprops=wedge_props,
    pctdistance=0.80,
)
for at in autotexts:
    at.set_fontsize(9)
for t in texts:
    t.set_fontsize(9)

ax_pie.set_title(f"Share by operator\n(total captures: {total:,})", fontsize=12)

# ---------------------------------------------------------------------------
# 5. Save & show
# ---------------------------------------------------------------------------
plt.tight_layout()
out_path = BASE_DIR / "mnc_market_share.png"
plt.savefig(out_path, dpi=150, bbox_inches="tight")
print(f"Plot saved to: {out_path}")
plt.show()
