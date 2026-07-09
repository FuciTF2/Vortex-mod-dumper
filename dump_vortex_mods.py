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
- Each mod also gets a Nexus Mods URL. If Vortex recorded a Nexus mod id for
  it (i.e. it was installed from Nexus), that's a direct link to the exact
  mod page. Otherwise it falls back to a Nexus site-search link for that
  mod's name, labeled "(search link, not confirmed)".
- Use --txt <path> to pick a custom name/location, --no-txt to skip writing
  a file, or --no-links to drop the Nexus URLs entirely.
- After the dump, you'll be asked whether to open all the links in your
  default browser (one tab per mod). Use --open to skip the prompt and just
  open them, or --no-open-prompt to never ask (e.g. for scripting/cron).

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
import time
import webbrowser
from pathlib import Path
from typing import Optional
from urllib.parse import quote

# Vortex's internal game id doesn't always match the URL slug Nexus uses.
# Confirmed against live nexusmods.com URLs where possible; if a game_id
# isn't listed here, we assume the Vortex id IS the Nexus domain (true for
# most games, e.g. fallout4, witcher3, stardewvalley, cyberpunk2077).
NEXUS_DOMAIN_OVERRIDES = {
    "skyrimse": "skyrimspecialedition",
    "falloutnv": "newvegas",
    "skyrimvr": "skyrimspecialedition",
    "fallout4vr": "fallout4",
    "teso": "elderscrollsonline",
}


def nexus_domain(game_id: str) -> str:
    return NEXUS_DOMAIN_OVERRIDES.get(game_id, game_id)


def build_nexus_url(game_id: str, attrs: dict, display_name: str) -> str:
    """Prefer a direct link using the Nexus mod id Vortex already stored.
    Falls back to a Nexus site-search URL if we don't have one (e.g. the
    mod wasn't installed from Nexus)."""
    domain = nexus_domain(game_id)
    nexus_mod_id = attrs.get("modId")
    source = (attrs.get("source") or "").lower()
    if nexus_mod_id and source == "nexus":
        return f"https://www.nexusmods.com/{domain}/mods/{nexus_mod_id}"
    # Fallback: a general Nexus site-search link (not a scraped/guessed result,
    # just points you at the search you'd otherwise type in yourself)
    return f"https://www.nexusmods.com/search/?gsearch={quote(display_name)}&gsearchtype=mods"


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


def open_links(rows, delay=0.4):
    urls = [r["nexus_url"] for r in rows if r.get("nexus_url")]
    for i, url in enumerate(urls, 1):
        webbrowser.open_new_tab(url)
        print(f"  opened {i}/{len(urls)}: {url}", file=sys.stderr)
        if i < len(urls):
            time.sleep(delay)


BANNER_UNICODE = r"""
██╗    ██╗██████╗ ██████╗
██║    ██║██╔══██╗██╔══██╗
██║ █╗ ██║██║  ██║██████╔╝
██║███╗██║██║  ██║██╔══██╗
╚███╔███╔╝██████╔╝██████╔╝
 ╚══╝╚══╝ ╚═════╝ ╚═════╝
     Vortex Mod Dumper
"""

BANNER_ASCII = r"""
 __        ______  ____
 \ \      / /  _ \| __ )
  \ \ /\ / /| | | |  _ \
   \ V  V / | |_| | |_) |
    \_/\_/  |____/|____/
     Vortex Mod Dumper
"""


def print_banner():
    # Classic cmd.exe (non-UTF8 codepage) chokes on the box-drawing
    # characters, so fall back to a plain-ASCII version if that happens.
    try:
        print(BANNER_UNICODE, file=sys.stderr)
    except UnicodeEncodeError:
        print(BANNER_ASCII, file=sys.stderr)


def main():
    # Peek at sys.argv directly so the banner can be suppressed before
    # argparse (and its own --help output) even runs.
    if "--no-banner" not in sys.argv:
        print_banner()

    ap = argparse.ArgumentParser(description="Dump Vortex's active mod list.")
    ap.add_argument("--no-banner", action="store_true", help="Skip the ASCII banner on launch")
    ap.add_argument("--vortex-dir", type=str, help="Path to Vortex's data folder (contains state.json)")
    ap.add_argument("--game", type=str, help="Game id as Vortex names it internally (e.g. skyrimse, fallout4, cyberpunk2077)")
    ap.add_argument("--profile", type=str, help="Profile id to use (if a game has multiple profiles)")
    ap.add_argument("--all", action="store_true", help="Include disabled mods too (default: enabled only)")
    ap.add_argument("--csv", type=str, help="Also write output to this CSV path")
    ap.add_argument("--txt", type=str, help="Path for the .txt dump (default: <game>_<profile>_mods.txt next to this script)")
    ap.add_argument("--no-txt", action="store_true", help="Skip writing the .txt file, just print to console")
    ap.add_argument("--no-links", action="store_true", help="Skip Nexus URLs, just list mod names/versions")
    ap.add_argument("--open", action="store_true", help="Open all links in your browser without prompting")
    ap.add_argument("--no-open-prompt", action="store_true", help="Never open links or ask to (e.g. for scripting/cron)")
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
        name = mod_display_name(mod_id, attrs)
        is_direct_link = bool(attrs.get("modId")) and (attrs.get("source") or "").lower() == "nexus"
        rows.append({
            "name": name,
            "mod_id": mod_id,
            "version": attrs.get("version", ""),
            "enabled": enabled,
            "source": attrs.get("source", ""),
            "author": attrs.get("author", ""),
            "nexus_url": "" if args.no_links else build_nexus_url(game_id, attrs, name),
            "link_type": "" if args.no_links else ("direct" if is_direct_link else "search"),
        })

    rows.sort(key=lambda r: r["name"].lower())

    label = "all" if args.all else "enabled"
    print(f"\n{len(rows)} {label} mod(s) for game='{game_id}' profile='{profile_id}':\n")
    for r in rows:
        flag = "on " if r["enabled"] else "off"
        ver = f" v{r['version']}" if r["version"] else ""
        print(f"  [{flag}] {r['name']}{ver}")
        if not args.no_links:
            marker = "" if r["link_type"] == "direct" else "  (search link, not confirmed)"
            print(f"        {r['nexus_url']}{marker}")

    if args.csv:
        import csv
        with open(args.csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["name", "mod_id", "version", "enabled", "source", "author", "nexus_url", "link_type"])
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
                if not args.no_links:
                    marker = "" if r["link_type"] == "direct" else "  (search link, not confirmed)"
                    f.write(f"      {r['nexus_url']}{marker}\n")

        print(f"\nWrote text dump to {txt_path}", file=sys.stderr)

    # Offer to open the links in a browser
    linked_rows = [r for r in rows if r.get("nexus_url")]
    if linked_rows and not args.no_open_prompt:
        if args.open:
            should_open = True
        else:
            count = len(linked_rows)
            direct_count = sum(1 for r in linked_rows if r["link_type"] == "direct")
            search_count = count - direct_count
            prompt = (
                f"\nOpen all {count} link(s) in your browser? "
                f"({direct_count} direct, {search_count} search fallback) "
                f"This will open {count} browser tab(s). [y/N] "
            )
            answer = input(prompt).strip().lower()
            should_open = answer in ("y", "yes")

        if should_open:
            print(f"\nOpening {len(linked_rows)} link(s)...", file=sys.stderr)
            open_links(linked_rows)
        else:
            print("\nSkipped opening links.", file=sys.stderr)


if __name__ == "__main__":
    main()