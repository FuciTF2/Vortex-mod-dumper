#!/usr/bin/env python3
"""
open_modlist_links.py

Companion to dump_vortex_mods.py. Reads a .txt modlist and gets you Nexus
Mods links for everything in it, with an option to open them all in your
browser.

Works with two kinds of input:
1. A file produced by dump_vortex_mods.py — already has URLs on the line
   below each mod name, so those exact URLs are reused as-is.
2. A plain list of mod names, one per line (e.g. hand-typed, or exported
   from somewhere else) — for these, a Nexus site-search link is built for
   each name, since there's no stored mod ID to link to directly.

Usage:
    python open_modlist_links.py mods.txt
    python open_modlist_links.py mods.txt --out links.txt
    python open_modlist_links.py mods.txt --open              # skip the prompt, just open
    python open_modlist_links.py mods.txt --batch-size 5       # open 5 at a time instead of 10
    python open_modlist_links.py mods.txt --no-open-prompt     # never ask/open
    python open_modlist_links.py mods.txt --no-banner
"""

import argparse
import re
import sys
import time
import webbrowser
from pathlib import Path

BANNER_UNICODE = r"""
██╗    ██╗██████╗ ██████╗
██║    ██║██╔══██╗██╔══██╗
██║ █╗ ██║██║  ██║██████╔╝
██║███╗██║██║  ██║██╔══██╗
╚███╔███╔╝██████╔╝██████╔╝
 ╚══╝╚══╝ ╚═════╝ ╚═════╝
    Modlist Link Opener
"""

BANNER_ASCII = r"""
 __        ______  ____
 \ \      / /  _ \| __ )
  \ \ /\ / /| | | |  _ \
   \ V  V / | |_| | |_) |
    \_/\_/  |____/|____/
    Modlist Link Opener
"""


def print_banner():
    try:
        print(BANNER_UNICODE, file=sys.stderr)
    except UnicodeEncodeError:
        print(BANNER_ASCII, file=sys.stderr)


URL_RE = re.compile(r"(https?://\S+)")
NAME_LINE_RE = re.compile(r"^\[(on|off)\s*\]\s*(.+)$", re.IGNORECASE)
TRAILING_VERSION_RE = re.compile(r"\s+v[\d][\w.\-]*$")
SKIP_LINE_SUBSTRINGS = ("mod(s) for game=", "Source state file:")


def build_search_url(name: str) -> str:
    """Nexus's own /search page does NOT read search terms from the URL
    (confirmed via their support forum — it's driven by a backend API call,
    not a URL param), so a "prefilled Nexus search" link isn't actually
    possible. A Google site-search scoped to nexusmods.com is the reliable
    alternative."""
    from urllib.parse import quote
    return f"https://www.google.com/search?q=site:nexusmods.com+{quote(name)}"


DIRECT_URL_RE = re.compile(r"nexusmods\.com/[^/]+/mods/\d+/?$")


def classify_url(url: str) -> str:
    return "direct" if DIRECT_URL_RE.search(url) else "search"


def parse_modlist(path: Path):
    """Returns a list of {name, url, link_type} dicts."""
    entries = []
    current = None

    with open(path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue
            if any(skip in line for skip in SKIP_LINE_SUBSTRINGS):
                continue

            url_match = URL_RE.search(line)
            if line.startswith("http") and url_match:
                # This is a URL line belonging to the previous mod name line
                if current is not None and current["url"] is None:
                    current["url"] = url_match.group(1)
                    current["link_type"] = classify_url(url_match.group(1))
                continue

            # Otherwise treat as a mod name line
            name_match = NAME_LINE_RE.match(line)
            name = name_match.group(2) if name_match else line
            name = TRAILING_VERSION_RE.sub("", name).strip()
            if not name:
                continue

            current = {"name": name, "url": None, "link_type": None}
            entries.append(current)

    # Fill in search-fallback links for anything that didn't have a URL line
    for e in entries:
        if e["url"] is None:
            e["url"] = build_search_url(e["name"])
            e["link_type"] = "search"

    return entries


def open_links(entries, batch_size=10, delay=0.4):
    urls = [e["url"] for e in entries]
    total = len(urls)
    opened = 0
    idx = 0
    while idx < total:
        batch = urls[idx: idx + batch_size]
        for j, url in enumerate(batch, 1):
            webbrowser.open_new_tab(url)
            opened += 1
            print(f"  opened {opened}/{total}: {url}", file=sys.stderr)
            if j < len(batch):
                time.sleep(delay)
        idx += batch_size
        if idx < total:
            next_count = min(batch_size, total - idx)
            answer = input(f"\nOpened {opened}/{total}. Open next {next_count}? [Y/n] ").strip().lower()
            if answer in ("n", "no"):
                print(f"Stopped after opening {opened}/{total} link(s).", file=sys.stderr)
                return


def main():
    if "--no-banner" not in sys.argv:
        print_banner()

    ap = argparse.ArgumentParser(description="Resolve and optionally open Nexus links from a modlist .txt file.")
    ap.add_argument("file", type=str, help="Path to the .txt modlist to read")
    ap.add_argument("--out", type=str, help="Write the resolved name+URL list to this file")
    ap.add_argument("--open", action="store_true", help="Open all links in your browser without prompting")
    ap.add_argument("--no-open-prompt", action="store_true", help="Never open links or ask to")
    ap.add_argument("--batch-size", type=int, default=10, help="How many links to open before asking to continue (default: 10)")
    ap.add_argument("--no-banner", action="store_true", help="Skip the ASCII banner on launch")
    args = ap.parse_args()

    in_path = Path(args.file)
    if not in_path.exists():
        sys.exit(f"File not found: {in_path}")

    entries = parse_modlist(in_path)
    if not entries:
        sys.exit(f"No mod names found in {in_path} — check the file has one mod per line.")

    direct_count = sum(1 for e in entries if e["link_type"] == "direct")
    search_fallback = len(entries) - direct_count

    print(f"\nFound {len(entries)} mod(s) in {in_path.name} "
          f"({direct_count} direct links, {search_fallback} search fallback):\n")
    for e in entries:
        marker = "" if e["link_type"] == "direct" else "  (search link, not confirmed)"
        print(f"  - {e['name']}")
        print(f"      {e['url']}{marker}")

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            for e in entries:
                marker = "" if e["link_type"] == "direct" else "  (search link, not confirmed)"
                f.write(f"{e['name']}\n      {e['url']}{marker}\n")
        print(f"\nWrote resolved links to {args.out}", file=sys.stderr)

    if not args.no_open_prompt:
        if args.open:
            should_open = True
        else:
            prompt = (
                f"\nOpen all {len(entries)} link(s) in your browser? "
                f"({direct_count} direct, {search_fallback} search fallback) "
                f"Opens in batches of {args.batch_size}, confirming between each. [y/N] "
            )
            answer = input(prompt).strip().lower()
            should_open = answer in ("y", "yes")

        if should_open:
            print(f"\nOpening {len(entries)} link(s)...", file=sys.stderr)
            open_links(entries, batch_size=args.batch_size)
        else:
            print("\nSkipped opening links.", file=sys.stderr)


if __name__ == "__main__":
    main()