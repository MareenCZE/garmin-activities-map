# CLAUDE.md

Operating notes for AI agents working in this repo. Human onboarding lives in
[`README.md`](README.md); the deep architecture reference is
[`docs/architecture.md`](docs/architecture.md).

## What this is

A personal, standalone Python tool that downloads Garmin Connect activities,
stores them locally, renders them on a Leaflet/Folium web map, and optionally
uploads the result via FTP to a site you configure. It is a *tool*, not a
polished app — a single user runs it by hand.

## How to run

- Entry point: `python activities-map.py`.
- Behaviour is driven entirely by config. `config-default.toml` is the
  committed, documented baseline; `config-local.toml` (git-ignored) holds
  personal overrides and is merged recursively over the default.
- What runs is controlled by the `[mode]` ON/OFF stage flags plus a separate
  `utility-mode` for one-off maintenance ops (`REDOWNLOAD`,
  `REGENERATE_COORDINATES`, `REGENERATE_CSV`, `RESORT_CSV`,
  `ENCRYPT_FTP_PASSWORD`). These `[mode]` values can be overridden per-run via
  CLI flags (`--downloader`, `--map-creator`, `--uploader`, `--utility-mode`,
  `--activity-id`) for scheduled runs — see `activities-map.py` (`main`/`run`).
- First run prompts for Garmin credentials and caches a ~1-year token under
  `.auth/`.

## Pipeline (each stage is its own module)

1. `downloader.py` — pulls new activities from Garmin Connect, writes per-activity
   JSON + GPX, derives simplified coordinate CSVs.
2. `storage.py` — the local "database": `data/activities_list.csv` index + the
   on-disk file layout.
3. `mapgenerator.py` — builds `output/activities_map.html` plus per-category
   `output/data/*.json` and a `manifest.json`. Client-side JS lives in
   `templates/activity_loader_template.html`.
4. `ftpuploader.py` — uploads HTML + JSON (incremental by default).

`common.py` holds the shared logger, TOML config loading, and Garmin login.

## Gotchas — read before editing

- **Never commit `data/`, `output/`, `.auth/`, or `config-local.toml`** — all
  git-ignored, all contain personal data or credentials. The repo is public.
  `.githooks/pre-commit` (`leak_guard.py`, enabled via
  `git config core.hooksPath .githooks`) enforces this plus content checks. When it
  blocks a commit, fix the content — never bypass it (`--no-verify`, `git add -f`,
  changing `core.hooksPath`), and add `leak-guard: allow` only for a real false
  positive.
- **Test fixtures and docs use synthetic data only**: coordinates within 1° of
  (0, 0) ("Null Island"), Garmin owner fields `null`, made-up names, IDs and
  tokens. Never copy values from `data/`, `.auth/`, or `config-local.toml` into
  tests, docs, or commit messages — imitate the *shape* of real data, not its values.
- The FTP password is Fernet-encrypted in config with a per-machine key generated
  into `ftp.key` in the token-store dir (`.auth/`). Never hard-code a key again:
  the repo is public. `[ftp] protocol` picks FTPS (default) or plain FTP; plain
  FTP still sends the credentials in clear text.
- Incremental FTP upload detects changes by comparing file **size**, so
  same-size content changes can be missed (mitigated only for `manifest.json`,
  which is always re-uploaded). Keep this in mind when touching upload logic.
- `closure-compiler-*.jar` and stray `data/map*.js` are obsolete minification
  leftovers — minification was removed. Don't wire them back in.
- **Tile attribution is a provider ToS requirement, not decoration.** Keep the
  Leaflet attribution control enabled and don't strip the OSM/CARTO attribution
  strings or the client-side Mapy.com logo control
  (`initializeMapyAttribution`). CARTO and Mapy.com (formerly Mapy.cz) tiles
  also each require the user's own API key.

## Deploy coupling

Output is published as static files (HTML + JSON) to an FTP site configured in
`config-local.toml`. This repo owns only the *tool* and its output; the hosting
lives elsewhere. Keep them decoupled — no host- or site-specific logic belongs
here.
