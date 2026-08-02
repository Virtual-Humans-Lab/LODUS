from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = (
    ROOT
    / "data_input"
    / "enumeration_area"
    / "Routine-POA-EnumArea-PopularTimes-LevyV2.json"
)


def _action(group: str, hours: list[int]) -> dict:
    return {
        "cycle_step": hours,
        "action": {
            "name": f"levy_walk_v2_{group}_global_routine",
            "type": "levy_walk_v2",
            "population_template": {
                "traceable_characteristics": {},
                "sampled_characteristics": {"occupation": [group]},
            },
            "values": {"group": group, "node_type": ["home"]},
        },
    }


def build_routine() -> dict:
    return {
        "global_routine": [
            _action("worker", list(range(24))),
            _action("student", [8, 13, 19]),
        ],
        "routines": {},
    }


def main():
    OUTPUT.write_text(
        json.dumps(build_routine(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf8",
    )
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
