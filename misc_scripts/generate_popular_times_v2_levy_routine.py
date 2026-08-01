from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data_input" / "enumeration_area" / "Routine-POA-EnumArea.json"
OUTPUT = (
    ROOT
    / "data_input"
    / "enumeration_area"
    / "Routine-POA-EnumArea-PopularTimes.json"
)


def build_routine(source: dict) -> dict:
    result = deepcopy(source)
    levy_count = 0
    for scheduled in result.get("global_routine", []):
        action = scheduled.get("action", {})
        if action.get("type") != "levy_walk":
            continue
        action.setdefault("values", {})["node_type"] = ["home"]
        levy_count += 1
    if levy_count == 0:
        raise ValueError("Source routine contains no global levy_walk actions")
    return result


def main():
    source = json.loads(SOURCE.read_text(encoding="utf8"))
    result = build_routine(source)
    OUTPUT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )
    print(f"Wrote {OUTPUT} with home filters on Levy actions")


if __name__ == "__main__":
    main()
