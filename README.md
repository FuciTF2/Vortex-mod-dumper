# dump_vortex_mods.py

Reads mods from local files created by the [Vortex](https://www.nexusmods.com/about/vortex/) mod manager and dumps your **currently enabled mod list** to a `.txt` file — complete with a Nexus Mods link for each mod — without having to click through the Vortex UI.

## Requirements

- **Windows** (Vortex itself is Windows-only, so this only supports Windows paths)
- **Python 3.8+** — no extra packages needed, everything used is in the standard library
- Vortex must have been run at least once so it has written its state files

## Usage

```bash
python dump_vortex_mods.py --game <gameId>
```

That's it. It'll auto-detect your Vortex data folder, find the most recent state backup, and write a `.txt` file next to the script (e.g. `skyrimse_<profileId>_mods.txt`) listing every enabled mod.

Don't know your game's id? Just run it with no `--game` flag — it'll print every game id it finds mods for in your install, so you can copy the right one:

```bash
python dump_vortex_mods.py
```

### Common Vortex game IDs

Vortex uses its own internal slug for each game, which doesn't always match the display name. Some common ones:

| Game                     | Vortex game id     |
|--------------------------|---------------------|
| Skyrim Special Edition   | `skyrimse`          |
| Skyrim (original)        | `skyrim`            |
| Fallout 4                | `fallout4`          |
| Fallout: New Vegas       | `falloutnv`         |
| Fallout 3                | `fallout3`          |
| Oblivion                 | `oblivion`          |
| Cyberpunk 2077           | `cyberpunk2077`     |
| The Witcher 3            | `witcher3`          |
| Stardew Valley           | `stardewvalley`     |
| Starfield                | `starfield`         |
| Baldur's Gate 3          | `baldursgate3`      |
| Bannerlord               | `mountandblade2bannerlord` |

⚠️ These are correct as of when this README was written, but Vortex occasionally renames game ids after updates. **If a game id above doesn't work, trust the script's own auto-detected list over this table** — run it with no `--game` flag and copy the id it prints for your install.

Note: Vortex's internal game id and Nexus Mods' URL slug aren't always the same string (e.g. Vortex calls Skyrim SE `skyrimse`, but its Nexus URL is `skyrimspecialedition`). The script has a small built-in mapping for the mismatches it knows about; for everything else it assumes the Vortex id and Nexus slug match, which is true for most games.

### Other options

```bash
python dump_vortex_mods.py --game skyrimse --all              # include disabled mods too
python dump_vortex_mods.py --game skyrimse --profile <id>     # pick a specific profile
python dump_vortex_mods.py --game skyrimse --csv mods.csv     # also export as CSV
python dump_vortex_mods.py --game skyrimse --no-txt           # console only, skip the .txt file
python dump_vortex_mods.py --game skyrimse --txt myfile.txt   # custom output filename/location
python dump_vortex_mods.py --game skyrimse --no-links         # skip Nexus URLs, just names/versions
python dump_vortex_mods.py --game skyrimse --open             # open all links without asking
python dump_vortex_mods.py --game skyrimse --no-open-prompt   # never ask/open (e.g. for scripting)
python dump_vortex_mods.py --game skyrimse --no-banner        # skip the ASCII banner
python dump_vortex_mods.py --vortex-dir "C:\ProgramData\Vortex"  # for "Shared" multi-user mode installs
```

## Nexus Mods links

Each mod in the dump gets a Nexus Mods URL:

- **Direct link** — if the mod was installed from Nexus, Vortex already stores the exact numeric mod ID internally, so the script builds a direct link straight to that mod's page (e.g. `nexusmods.com/skyrimspecialedition/mods/3863`). No searching or guessing involved.
- **Search fallback** — if a mod wasn't sourced from Nexus (manually installed, from another site, etc.), there's no ID to link to, so instead it builds a Nexus site-search URL for that mod's name, clearly labeled `(search link, not confirmed)` in the output so you know it's not guaranteed accurate.

After the dump, the script will ask if you want to open every link in your browser (one tab per mod, with a short delay between each so it doesn't flood your browser). Skip the prompt with `--open` (open automatically) or `--no-open-prompt` (never ask). If you have a large modlist, consider answering "no" and opening links selectively from the `.txt` file instead — 100+ mods means 100+ tabs.

## How it works

Vortex keeps its internal state (installed mods, profiles, which mods are enabled) as JSON. This script reads that JSON directly — it never touches Vortex's UI or process, and it's read-only, so it can't break your setup.

It looks in, in order of preference:
1. `%APPDATA%\Vortex\temp\state_backups_full\` — the newest backup file here (these are less likely to be caught mid-write than the live file)
2. `%APPDATA%\Vortex\state.json` — the live state file, as a fallback
3. `%ProgramData%\Vortex\...` — if you pass `--vortex-dir` pointing there (needed for "Shared" multi-user mode)

## Known limitations / troubleshooting

- **Undocumented format:** Vortex doesn't publish this JSON structure as a stable public API. This script's parsing (`persistent.mods`, `persistent.profiles`, `modState.enabled`) was based on Vortex's own docs/wiki and cross-checked against how other community tools read the same files — but a future Vortex update could rename a field and break this. If that happens, it should fail with a clear error rather than doing anything destructive, since it only ever reads files.
- **Nexus links:** direct links are only as good as the `modId`/`source` Vortex recorded — if those are missing or wrong for some mod, you'll get a search-fallback link instead, which is labeled as such. Domain-slug mismatches (Vortex id vs. Nexus URL slug) are only handled for the games explicitly listed in the script's mapping table; anything else assumes they match.
- **Windows only.** No plans to support Linux/Mac since Vortex itself doesn't run there natively (Proton/Steam Deck users: point `--vortex-dir` at the Vortex folder inside your compatdata prefix, e.g. something like `.../compatdata/<id>/pfx/drive_c/ProgramData/vortex`).
- **"Shared" mode:** if you set Vortex to Shared multi-user mode, pass `--vortex-dir "C:\ProgramData\Vortex"` explicitly — auto-detection only checks the default paths.

If something breaks, please open an issue with the error message and (if you're comfortable sharing it) a redacted snippet of your `persistent.mods` or `persistent.profiles` structure from your state.json — that's enough to patch the parsing without needing your actual mod list.

## License

MIT — do whatever you want with it.