# Bauernkiste Mushroom Availability Tracker

This repository contains a small CLI utility to track availability changes for Pom-Pilz mushrooms sold through Bauernkiste regions. It starts with **10 units per region** for Kräuterseitling, Austernseitling, and Nameko, then lets you record new availability snapshots to infer sales.

## Quick start

```bash
python tracker.py init
```

You can also pass `--path` after the command if you want to store data elsewhere:

```bash
python tracker.py init --path /tmp/availability.json
```

This creates `data/availability.json` with 10 units per mushroom per region.

## Record availability updates

When you check the availability on bauernkiste.at, update the counts with `record`:

```bash
python tracker.py record \
  --set "Region 1" "Kräuterseitling" 8 \
  --set "Region 2" "Austernseitling" 9 \
  --set "Region 3" "Nameko" 10
```

The tracker will print the deltas (sold/restocked) compared to the previous snapshot.

## Review status and sales

```bash
python tracker.py status
python tracker.py report
```

- `status` shows the latest availability snapshot.
- `report` shows the changes between the last two snapshots.

## Custom regions or starting units

```bash
python tracker.py init --regions Wien Graz Linz --units 10
```

## Data file

All snapshots are stored in `data/availability.json` so you can keep appending daily/weekly updates.
