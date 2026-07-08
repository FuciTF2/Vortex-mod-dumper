# dump_vortex_mods.py

Reads mods from local files created by the [Vortex](https://www.nexusmods.com/about/vortex/) mod manager and dumps your **currently enabled mod list** to a `.txt` file, without having to click through the Vortex UI.

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

### Other options

```bash
python dump_vortex_mods.py --game skyrimse --all              # include disabled mods too
python dump_vortex_mods.py --game skyrimse --profile <id>     # pick a specific profile
python dump_vortex_mods.py --game skyrimse --csv mods.csv     # also export as CSV
python dump_vortex_mods.py --game skyrimse --no-txt           # console only, skip the .txt file
python dump_vortex_mods.py --game skyrimse --txt myfile.txt   # custom output filename/location
python dump_vortex_mods.py --vortex-dir "C:\ProgramData\Vortex"  # for "Shared" multi-user mode installs
```

## How it works

Vortex keeps its internal state (installed mods, profiles, which mods are enabled) as JSON. This script reads that JSON directly — it never touches Vortex's UI or process, and it's read-only, so it can't break your setup.

It looks in, in order of preference:
1. `%APPDATA%\Vortex\temp\state_backups_full\` — the newest backup file here (these are less likely to be caught mid-write than the live file)
2. `%APPDATA%\Vortex\state.json` — the live state file, as a fallback
3. `%ProgramData%\Vortex\...` — if you pass `--vortex-dir` pointing there (needed for "Shared" multi-user mode)

## Known limitations / troubleshooting

- **Undocumented format:** Vortex doesn't publish this JSON structure as a stable public API. This script's parsing (`persistent.mods`, `persistent.profiles`, `modState.enabled`) was based on Vortex's own docs/wiki and cross-checked against how other community tools read the same files — but a future Vortex update could rename a field and break this. If that happens, it should fail with a clear error rather than doing anything destructive, since it only ever reads files.
- **Windows only.** No plans to support Linux/Mac since Vortex itself doesn't run there natively (Proton/Steam Deck users: point `--vortex-dir` at the Vortex folder inside your compatdata prefix, e.g. something like `.../compatdata/<id>/pfx/drive_c/ProgramData/vortex`).
- **"Shared" mode:** if you set Vortex to Shared multi-user mode, pass `--vortex-dir "C:\ProgramData\Vortex"` explicitly — auto-detection only checks the default paths.

If something breaks, please open an issue with the error message and (if you're comfortable sharing it) a redacted snippet of your `persistent.mods` or `persistent.profiles` structure from your state.json — that's enough to patch the parsing without needing your actual mod list.

## License

MIT — do whatever you want with it.