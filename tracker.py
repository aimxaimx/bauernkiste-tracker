#!/usr/bin/env python3
"""Simple availability tracker for Bauernkiste mushroom sales."""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

DEFAULT_MUSHROOMS = ["Kräuterseitling", "Austernseitling", "Nameko"]
DEFAULT_REGIONS = ["Region 1", "Region 2", "Region 3"]
DEFAULT_STARTING_UNITS = 10


@dataclass
class Snapshot:
    timestamp: str
    availability: Dict[str, Dict[str, int]]


@dataclass
class TrackerData:
    regions: List[str]
    mushrooms: List[str]
    history: List[Snapshot]


DATA_PATH = Path("data/availability.json")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_data(path: Path = DATA_PATH) -> TrackerData:
    if not path.exists():
        raise FileNotFoundError(
            f"No data found at {path}. Run 'init' first to create baseline data."
        )
    raw = json.loads(path.read_text(encoding="utf-8"))
    history = [Snapshot(**entry) for entry in raw.get("history", [])]
    return TrackerData(
        regions=raw.get("regions", []),
        mushrooms=raw.get("mushrooms", []),
        history=history,
    )


def save_data(data: TrackerData, path: Path = DATA_PATH) -> None:
    ensure_parent(path)
    payload = {
        "regions": data.regions,
        "mushrooms": data.mushrooms,
        "history": [snapshot.__dict__ for snapshot in data.history],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def build_availability(regions: List[str], mushrooms: List[str], units: int) -> Dict[str, Dict[str, int]]:
    return {
        region: {mushroom: units for mushroom in mushrooms}
        for region in regions
    }


def apply_updates(
    availability: Dict[str, Dict[str, int]],
    updates: List[tuple[str, str, int]],
) -> Dict[str, Dict[str, int]]:
    updated = json.loads(json.dumps(availability))
    for region, mushroom, units in updates:
        if region not in updated:
            raise ValueError(f"Unknown region '{region}'.")
        if mushroom not in updated[region]:
            raise ValueError(f"Unknown mushroom '{mushroom}'.")
        if units < 0:
            raise ValueError("Availability cannot be negative.")
        updated[region][mushroom] = units
    return updated


def summarize_changes(
    previous: Dict[str, Dict[str, int]],
    current: Dict[str, Dict[str, int]],
) -> Dict[str, Dict[str, int]]:
    changes: Dict[str, Dict[str, int]] = {}
    for region, mushrooms in current.items():
        changes[region] = {}
        for mushroom, new_units in mushrooms.items():
            old_units = previous.get(region, {}).get(mushroom, new_units)
            changes[region][mushroom] = old_units - new_units
    return changes


def format_changes(changes: Dict[str, Dict[str, int]]) -> str:
    lines: List[str] = []
    for region, mushrooms in changes.items():
        lines.append(f"{region}:")
        for mushroom, delta in mushrooms.items():
            label = "sold" if delta >= 0 else "restocked"
            lines.append(f"  - {mushroom}: {abs(delta)} {label}")
    return "\n".join(lines)


def cmd_init(args: argparse.Namespace) -> None:
    regions = args.regions or DEFAULT_REGIONS
    mushrooms = args.mushrooms or DEFAULT_MUSHROOMS
    availability = build_availability(regions, mushrooms, args.units)
    data = TrackerData(
        regions=regions,
        mushrooms=mushrooms,
        history=[Snapshot(timestamp=utc_now(), availability=availability)],
    )
    save_data(data, path=Path(args.path))
    print(f"Initialized tracker at {args.path} with {args.units} units per item.")


def cmd_record(args: argparse.Namespace) -> None:
    data = load_data(Path(args.path))
    if not data.history:
        raise ValueError("No baseline snapshot found. Run 'init' first.")
    latest = data.history[-1].availability
    updates = [(update[0], update[1], update[2]) for update in args.set]
    current = apply_updates(latest, updates)
    changes = summarize_changes(latest, current)
    data.history.append(Snapshot(timestamp=utc_now(), availability=current))
    save_data(data, path=Path(args.path))
    print("Recorded new availability snapshot.")
    print("Changes since last snapshot:")
    print(format_changes(changes))


def cmd_report(args: argparse.Namespace) -> None:
    data = load_data(Path(args.path))
    if len(data.history) < 2:
        print("Not enough snapshots to report changes. Add another 'record'.")
        return
    latest = data.history[-1]
    previous = data.history[-2]
    changes = summarize_changes(previous.availability, latest.availability)
    print(f"Latest snapshot: {latest.timestamp}")
    print(format_changes(changes))


def cmd_status(args: argparse.Namespace) -> None:
    data = load_data(Path(args.path))
    latest = data.history[-1]
    print(f"Latest snapshot: {latest.timestamp}")
    for region, mushrooms in latest.availability.items():
        print(region)
        for mushroom, units in mushrooms.items():
            print(f"  - {mushroom}: {units} units")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Track availability changes for Bauernkiste mushroom sales.")
    parser.add_argument(
        "--path",
        default=str(DATA_PATH),
        help="Path to the tracker data JSON file.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create baseline availability data.")
    init_parser.add_argument(
        "--path",
        default=str(DATA_PATH),
        help="Path to the tracker data JSON file.",
    )
    init_parser.add_argument(
        "--regions",
        nargs="+",
        help="Custom region names (default: Region 1/2/3).",
    )
    init_parser.add_argument(
        "--mushrooms",
        nargs="+",
        help="Custom mushroom names (default: Kräuterseitling, Austernseitling, Nameko).",
    )
    init_parser.add_argument(
        "--units",
        type=int,
        default=DEFAULT_STARTING_UNITS,
        help="Starting units per region/mushroom.",
    )
    init_parser.set_defaults(func=cmd_init)

    record_parser = subparsers.add_parser(
        "record", help="Record a new availability snapshot.")
    record_parser.add_argument(
        "--path",
        default=str(DATA_PATH),
        help="Path to the tracker data JSON file.",
    )
    record_parser.add_argument(
        "--set",
        action="append",
        nargs=3,
        metavar=("REGION", "MUSHROOM", "UNITS"),
        type=str,
        default=[],
        help="Set availability for a region/mushroom.",
    )
    record_parser.set_defaults(func=cmd_record)

    report_parser = subparsers.add_parser("report", help="Show changes since last snapshot.")
    report_parser.add_argument(
        "--path",
        default=str(DATA_PATH),
        help="Path to the tracker data JSON file.",
    )
    report_parser.set_defaults(func=cmd_report)

    status_parser = subparsers.add_parser("status", help="Show latest availability snapshot.")
    status_parser.add_argument(
        "--path",
        default=str(DATA_PATH),
        help="Path to the tracker data JSON file.",
    )
    status_parser.set_defaults(func=cmd_status)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "record":
        parsed_set = []
        for region, mushroom, units in args.set:
            try:
                parsed_set.append((region, mushroom, int(units)))
            except ValueError as exc:
                raise ValueError(f"Invalid units '{units}'. Must be an integer.") from exc
        args.set = parsed_set
    args.func(args)


if __name__ == "__main__":
    main()
