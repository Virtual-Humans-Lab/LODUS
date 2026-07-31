"""Import historical LODUS-Health data into canonical inpatient care inputs."""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import unicodedata
from collections import defaultdict
from pathlib import Path


EXPECTED = {
    "rows": 253,
    "hospitals": 28,
    "regions": 22,
    "total_beds": 7529,
    "sus_beds": 4689,
}
SCENARIO_FILES = {
    "reference_demand.original.json": "config-simulacao1.json",
    "high_demand.original.json": "config-10abril20242.json",
    "two_facility.original.json": "config-HAHAHA.json",
}
REGION_ALIASES = {
    "Centro": "Centro Histórico",
    "Menino Deus": "Menino-Deus",
}


def _slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "_", ascii_value.lower()).strip("_")


def import_capacity(source: Path, output_dir: Path):
    with source.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    canonical = [
        {
            "hospital": row["HOSPITAL"].strip(),
            "region": REGION_ALIASES.get(
                row["REGIAO"].strip(), row["REGIAO"].strip()
            ),
            "longitude": float(row["LONG"]),
            "latitude": float(row["LAT"]),
            "specialty": row["DESCRICAO"].strip(),
            "bed_type": row["TIPO"].strip(),
            "total_beds": int(row["TOTAL"]),
            "sus_beds": int(row["SUS"]),
        }
        for row in rows
    ]
    actual = {
        "rows": len(canonical),
        "hospitals": len({row["hospital"] for row in canonical}),
        "regions": len({row["region"] for row in canonical}),
        "total_beds": sum(row["total_beds"] for row in canonical),
        "sus_beds": sum(row["sus_beds"] for row in canonical),
    }
    if actual != EXPECTED:
        raise ValueError(
            f"Unexpected hospital dataset totals: {actual}; expected {EXPECTED}"
        )

    capacity_path = output_dir / "inpatient_capacity.csv"
    with capacity_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "hospital",
                "region",
                "longitude",
                "latitude",
                "specialty",
                "bed_type",
                "total_beds",
                "sus_beds",
            ],
        )
        writer.writeheader()
        writer.writerows(canonical)

    hospital_rows = {}
    for row in canonical:
        key = row["hospital"]
        identity = (
            row["region"],
            row["longitude"],
            row["latitude"],
        )
        previous = hospital_rows.setdefault(key, identity)
        if previous != identity:
            raise ValueError(f"Inconsistent location for hospital {key}")

    regions = defaultdict(list)
    for hospital, (region, longitude, latitude) in hospital_rows.items():
        regions[region].append(
            {
                "poi_type": "hospital",
                "unique_name": f"hospital_{_slug(hospital)}",
                "lng_lat": [longitude, latitude],
                "attributes": {
                    "hospital_name": hospital,
                    "capacity_source": "CNES January 2024",
                },
            }
        )
    overlay = {
        "regions": [
            {
                "name": region,
                "points_of_interest": sorted(
                    hospitals,
                    key=lambda item: item["attributes"]["hospital_name"],
                ),
            }
            for region, hospitals in sorted(regions.items())
        ]
    }
    (output_dir / "Environment-Hospitals-POA.json").write_text(
        json.dumps(overlay, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def import_provenance(health_root: Path, output_dir: Path):
    provenance = output_dir / "provenance"
    provenance.mkdir(parents=True, exist_ok=True)
    for target, source in SCENARIO_FILES.items():
        shutil.copyfile(
            health_root / "Application" / "outputs" / source,
            provenance / target,
        )


def import_legacy_cid(source: Path, output_dir: Path):
    with source.open(encoding="latin-1", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if sum(int(row["QUANTIDADE"]) for row in rows) != 915:
        raise ValueError("Historical CID fixture no longer totals 915")
    with (output_dir / "legacy_cid_counts.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "REGIAO_HOSPITAL",
                "MES_INTER",
                "DIAG_PRINC",
                "QUANTIDADE",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("health_root", type=Path)
    parser.add_argument(
        "--lodus-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    args = parser.parse_args()
    output_dir = args.lodus_root / "data_input" / "inpatient_care"
    output_dir.mkdir(parents=True, exist_ok=True)
    import_capacity(
        args.health_root / "leitos-hospitais-especialidade.csv",
        output_dir,
    )
    import_provenance(args.health_root, output_dir)
    import_legacy_cid(
        args.lodus_root
        / "legacy"
        / "legacy_data_input"
        / "region_month_2022.csv",
        output_dir,
    )


if __name__ == "__main__":
    main()
