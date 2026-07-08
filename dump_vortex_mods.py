#!/usr/bin/env python3
"""
dump_vortex_mods.py

Reads Vortex's local state (state.json or its rolling backups) and prints/exports
the list of mods that are ENABLED for a given game + profile.

Usage:
    python dump_vortex_mods.py                     # interactive: lists games/profiles found
    python dump_vortex_mods.py --game skyrimse
    python dump_vortex_mods.py --game skyrimse --profile <profileId>
    python dump_vortex_mods.py --game skyrimse --all       # include disabled mods too
    python dump_vortex_mods.py --game skyrimse --csv out.csv
    python dump_vortex_mods.py --vortex-dir "D:\\CustomVortexData"

Output:
- By default, a .txt file is written next to this script, named
  "<game>_<profile>_mods.txt" (e.g. cyberpunk2077_abc123_mods.txt).
- Use --txt <path> to pick a custom name/location, or --no-txt to skip
  writing a file and only print to the console.

Notes:
- Vortex must have written state at least once (i.e. has been run). You do NOT
  need to close Vortex first, but if something looks stale/wrong, close Vortex
  and re-run so it flushes a fresh state.json.
- Default data dir is %APPDATA%\\Vortex on Windows. If you used "Shared" mode,
  pass --vortex-dir "C:\\ProgramData\\Vortex" instead.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional


def find_default_vortex_dir() -> Optional[Path]:
    candidates = []
    appdata = os.environ.get("APPDATA")
    if appdata:
        candidates.append(Path(appdata) / "Vortex")
    programdata = os.environ.get("PROGRAMDATA")
    if programdata:
        candidates.append(Path(programdata) / "Vortex")
    for c in candidates:
        if c.exists():
            return c
    return None


def find_state_file(vortex_dir: Path) -> Path:
    """Prefer the most recent full backup (less likely to be mid-write),
    fall back to the live state.json."""
    backup_dir = vortex_dir / "temp" / "state_backups_full"
    candidates = []
    if backup_dir.exists():
        candidates.extend(backup_dir.glob("*.json"))

    live_state = vortex_dir / "state.json"
    if live_state.exists():
        candidates.append(live_state)

    if not candidates:
        sys.exit(
            f"Could not find any Vortex state JSON under {vortex_dir}\n"
            f"Checked: {backup_dir} and {live_state}\n"
            f"Pass --vortex-dir if your data lives somewhere else."
        )

    # Pick newest by mtime
    return max(candidates, key=lambda p: p.stat().st_mtime)


def load_state(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def mod_display_name(mod_id: str, attributes: dict) -> str:
    return (
        attributes.get("customFileName")
        or attributes.get("logicalFileName")
        or attributes.get("name")
        or attributes.get("modName")
        or mod_id
    )


def main():
    ap = argparse.ArgumentParser(description="Dump Vortex's active mod list.")
    ap.add_argument("--vortex-dir", type=str, help="Path to Vortex's data folder (contains state.json)")
    ap.add_argument("--game", type=str, help="Game id as Vortex names it internally (e.g. skyrimse, fallout4, cyberpunk2077)")
    ap.add_argument("--profile", type=str, help="Profile id to use (if a game has multiple profiles)")
    ap.add_argument("--all", action="store_true", help="Include disabled mods too (default: enabled only)")
    ap.add_argument("--csv", type=str, help="Also write output to this CSV path")
    ap.add_argument("--txt", type=str, help="Path for the .txt dump (default: <game>_<profile>_mods.txt next to this script)")
    ap.add_argument("--no-txt", action="store_true", help="Skip writing the .txt file, just print to console")
    args = ap.parse_args()

    vortex_dir = Path(args.vortex_dir) if args.vortex_dir else find_default_vortex_dir()
    if not vortex_dir or not vortex_dir.exists():
        sys.exit(
            "Couldn't locate a Vortex data folder automatically.\n"
            "Pass it explicitly, e.g.:\n"
            r'  python dump_vortex_mods.py --vortex-dir "%APPDATA%\Vortex"' "\n"
        )

    state_path = find_state_file(vortex_dir)
    print(f"Reading: {state_path}", file=sys.stderr)
    state = load_state(state_path)

    persistent = state.get("persistent", {})
    all_mods = persistent.get("mods", {})       # { gameId: { modId: {...} } }
    all_profiles = persistent.get("profiles", {})  # { profileId: {gameId, modState: {...}, name, ...} }

    if not all_mods:
        sys.exit("No 'persistent.mods' section found in state file — unexpected format or empty install.")

    # --game selection
    game_id = args.game
    if not game_id:
        print("No --game specified. Games found in this Vortex install:", file=sys.stderr)
        for g in sorted(all_mods.keys()):
            print(f"  - {g}", file=sys.stderr)
        sys.exit("Re-run with --game <one of the above>")

    if game_id not in all_mods:
        sys.exit(f"Game '{game_id}' not found. Available: {sorted(all_mods.keys())}")

    # --profile selection: find profiles belonging to this game
    matching_profiles = {
        pid: p for pid, p in all_profiles.items() if p.get("gameId") == game_id
    }
    profile_id = args.profile
    if not profile_id:
        if len(matching_profiles) == 1:
            profile_id = next(iter(matching_profiles))
        elif len(matching_profiles) > 1:
            print(f"Multiple profiles found for '{game_id}':", file=sys.stderr)
            for pid, p in matching_profiles.items():
                marker = " (last active)" if p.get("lastActivated") else ""
                print(f"  - {pid}: {p.get('name', '(unnamed)')}{marker}", file=sys.stderr)
            # best-effort: pick the one with the most recent lastActivated timestamp
            profile_id = max(
                matching_profiles,
                key=lambda pid: matching_profiles[pid].get("lastActivated") or 0,
            )
            print(f"Defaulting to most recently active: {profile_id}", file=sys.stderr)
        else:
            sys.exit(f"No profiles found for game '{game_id}'.")

    if profile_id not in all_profiles:
        sys.exit(f"Profile '{profile_id}' not found. Available for {game_id}: {list(matching_profiles.keys())}")

    profile = all_profiles[profile_id]
    mod_state = profile.get("modState", {})  # { modId: {enabled: bool, ...} }
    mods_for_game = all_mods[game_id]        # { modId: {attributes: {...}, ...} }

    rows = []
    for mod_id, mod_info in mods_for_game.items():
        enabled = bool(mod_state.get(mod_id, {}).get("enabled", False))
        if not args.all and not enabled:
            continue
        attrs = mod_info.get("attributes", {})
        rows.append({
            "name": mod_display_name(mod_id, attrs),
            "mod_id": mod_id,
            "version": attrs.get("version", ""),
            "enabled": enabled,
            "source": attrs.get("source", ""),
            "author": attrs.get("author", ""),
        })

    rows.sort(key=lambda r: r["name"].lower())

    label = "all" if args.all else "enabled"
    print(f"\n{len(rows)} {label} mod(s) for game='{game_id}' profile='{profile_id}':\n")
    for r in rows:
        flag = "on " if r["enabled"] else "off"
        ver = f" v{r['version']}" if r["version"] else ""
        print(f"  [{flag}] {r['name']}{ver}")

    if args.csv:
        import csv
        with open(args.csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["name", "mod_id", "version", "enabled", "source", "author"])
            writer.writeheader()
            writer.writerows(rows)
        print(f"\nWrote CSV to {args.csv}", file=sys.stderr)

    if not args.no_txt:
        script_dir = Path(__file__).resolve().parent
        if args.txt:
            txt_path = Path(args.txt)
        else:
            txt_path = script_dir / f"{game_id}_{profile_id}_mods.txt"

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(f"{len(rows)} {label} mod(s) for game='{game_id}' profile='{profile_id}'\n")
            f.write(f"Source state file: {state_path}\n\n")
            for r in rows:
                flag = "on " if r["enabled"] else "off"
                ver = f" v{r['version']}" if r["version"] else ""
                f.write(f"[{flag}] {r['name']}{ver}\n")

        print(f"\nWrote text dump to {txt_path}", file=sys.stderr)


if __name__ == "__main__":
    main()