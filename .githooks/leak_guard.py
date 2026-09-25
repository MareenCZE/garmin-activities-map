#!/usr/bin/env python3
"""Pre-commit guard that keeps personal data and secrets out of this public repo.

Run by ``.githooks/pre-commit`` on every commit (enable once per clone with
``git config core.hooksPath .githooks``). It inspects what is being committed
and rejects the commit when it finds:

* paths that hold personal data or credentials: ``data/``, ``output/``,
  ``.auth/``, ``config-local.toml``, GPS track files, Garmin-named activity files;
* secrets: Fernet tokens (encrypted FTP password), OAuth tokens/JWTs, non-empty
  credential values in TOML config;
* personal data: Garmin owner fields, e-mail addresses, precise GPS coordinates;
* any string listed as private: the credential values in ``config-local.toml``
  plus the lines of ``.git/leak-guard-denylist`` (never committable, per clone).

Only *added* lines are checked, so pre-existing content never blocks a commit.
Coordinates inside the synthetic box around (0, 0) ("Null Island", open ocean)
are allowed so test fixtures can use realistic-looking tracks. A line containing
``leak-guard: allow`` is skipped - use it sparingly and only for real false
positives.

Standalone use: ``python3 .githooks/leak_guard.py --all`` audits every tracked
file. Keep this file compatible with the macOS system Python (3.9): no tomllib.
"""
import os
import re
import subprocess
import sys

ALLOW_PRAGMA = "leak-guard: allow"
SYNTHETIC_BOX = 1.0  # |lat| and |lon| at most this many degrees from (0, 0)

BLOCKED_DIRS = ("data/", "output/", ".auth/", "venv/")
BLOCKED_NAMES = ("config-local.toml", ".env")
BLOCKED_EXTENSIONS = (".gpx", ".fit", ".tcx", ".kml", ".kmz")
# the downloader's per-activity file stem: <date>_<activity id>_<type>
GARMIN_ACTIVITY_FILE = re.compile(r"\d{4}-\d{2}-\d{2}_\d{6,}_\w+\.\w+$")
TOKEN_FILE = re.compile(r"(^|/)oauth\d?_token\.json$")

FERNET_TOKEN = re.compile(r"gAAAAA[A-Za-z0-9_-]{40,}")
JWT = re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.")
OAUTH_FIELD = re.compile(
    r"""["']?(oauth_token_secret|oauth_token|access_token|refresh_token|mfa_token)["']?"""
    r"""\s*[:=]\s*["'][^"']{12,}["']""")
OWNER_FIELD = re.compile(
    r"""["'](owner(Id|DisplayName|FullName|ProfileImageUrl\w*)|userProfileId|userProfilePk|profileId|deviceId)["']"""
    r"""\s*:\s*(?!null\b|None\b)[^\s,}]""")
# "[_]" keeps this source line from matching itself
GARMIN_PROFILE_URL = re.compile(r"garmin-connect-prod/profile[_]images")
# TOML key = "non-empty value" for keys that must stay empty in committed config
TOML_SECRET = re.compile(
    r"""^\s*(pass|password|user|host|remote-path|[\w-]*api-key)\s*=\s*["'][^"']+["']""")
EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@([A-Za-z0-9-]+\.)+[A-Za-z]{2,}\b")
EMAIL_ALLOWED_DOMAINS = ("example.com", "example.org", "example.net",
                         "users.noreply.github.com", "anthropic.com", "github.com")

_NUM = r"-?\d{1,3}\.\d{4,}"  # 4+ decimals is ~11 m: enough to find a front door
COORD_PAIR = re.compile(r"(?<![\d.])(%s)\s*,\s*(%s)(?![\d.])" % (_NUM, _NUM))
COORD_FIELD = re.compile(
    r"""(?i)\b(lat|lon|lng|latitude|longitude|\w+latitude|\w+longitude)["']?\s*[:=]\s*["']?(%s)""" % _NUM)

# config-local.toml keys whose values are private wherever they appear
PRIVATE_CONFIG_KEYS = re.compile(r"^\s*(host|user|pass|remote-path|[\w-]*api-key)\s*=\s*[\"']([^\"']{4,})[\"']")


def check_path(path):
    """Return the reasons why this repo-relative path must never be committed."""
    reasons = []
    name = path.rsplit("/", 1)[-1]
    if path.startswith(BLOCKED_DIRS):
        reasons.append("lives in a git-ignored personal-data directory")
    if name in BLOCKED_NAMES:
        reasons.append("is a private config file")
    if name.lower().endswith(BLOCKED_EXTENSIONS):
        reasons.append("is a GPS track file")
    if GARMIN_ACTIVITY_FILE.search(name):
        reasons.append("is named like a downloaded Garmin activity")
    if TOKEN_FILE.search(path):
        reasons.append("is a Garmin OAuth token file")
    return reasons


def _is_precise(value):
    # trailing zeros carry no location: 50.000000 is a round number, not a position
    return len(value.split(".")[1].rstrip("0")) >= 4


def _leaks_location(*values):
    return (any(_is_precise(v) for v in values)
            and any(abs(float(v)) > SYNTHETIC_BOX for v in values))


def _denylist_hit(secret, lowered_line):
    """Names (letters and spaces only) match as whole words so that a short surname is not
    found inside ordinary words; anything else (passwords, hosts, keys) matches as a substring."""
    secret = secret.lower()
    if not all(c.isalpha() or c.isspace() for c in secret):
        return secret in lowered_line
    # a "word" character here is a letter or digit; "_", ".", "@" and spaces separate words
    return re.search(r"(?<![^\W_])%s(?![^\W_])" % re.escape(secret), lowered_line) is not None


def check_line(path, line, denylist=()):
    """Return the reasons why this added line must not be committed."""
    if ALLOW_PRAGMA in line:
        return []
    reasons = []
    if FERNET_TOKEN.search(line):
        reasons.append("Fernet token (encrypted password)")
    if JWT.search(line):
        reasons.append("JWT / OAuth access token")
    if OAUTH_FIELD.search(line):
        reasons.append("OAuth token value")
    if OWNER_FIELD.search(line) or GARMIN_PROFILE_URL.search(line):
        reasons.append("Garmin account/owner data (use null in fixtures)")
    if path.endswith(".toml") and TOML_SECRET.search(line):
        reasons.append("non-empty credential in committed config (belongs in config-local.toml)")
    for m in EMAIL.finditer(line):
        domain = m.group(0).split("@", 1)[1].lower()
        if not any(domain == d or domain.endswith("." + d) for d in EMAIL_ALLOWED_DOMAINS):
            reasons.append("e-mail address %s" % m.group(0))
    precise = [(m.group(1), m.group(2)) for m in COORD_PAIR.finditer(line)]
    precise += [(m.group(2),) for m in COORD_FIELD.finditer(line)]
    if any(_leaks_location(*vals) for vals in precise):
        reasons.append("precise GPS coordinates (fixtures must stay within %g deg of 0,0)" % SYNTHETIC_BOX)
    lowered = line.lower()
    for secret in denylist:
        if _denylist_hit(secret, lowered):
            reasons.append("private string from denylist/config-local.toml")
            break
    return reasons


def check_text(path, text, denylist=()):
    """Check every line of text; return (line number, line, reasons) findings."""
    findings = []
    for number, line in enumerate(text.splitlines(), 1):
        reasons = check_line(path, line, denylist)
        if reasons:
            findings.append((number, line, reasons))
    return findings


def load_denylist(repo_root, git_dir):
    """Private strings: credential values in config-local.toml + the local denylist file."""
    entries = []
    try:
        with open(os.path.join(repo_root, "config-local.toml"), encoding="utf-8") as f:
            for line in f:
                m = PRIVATE_CONFIG_KEYS.match(line)
                if m:
                    entries.append(m.group(2))
    except OSError:
        pass
    try:
        with open(os.path.join(git_dir, "leak-guard-denylist"), encoding="utf-8") as f:
            entries += [l.strip() for l in f if l.strip() and not l.lstrip().startswith("#")]
    except OSError:
        pass
    return [e for e in entries if len(e) >= 4]


def _git(*args):
    return subprocess.run(("git",) + args, check=True, stdout=subprocess.PIPE).stdout


def staged_additions():
    """Yield (path, [(line number, added line)]) for every staged file."""
    names = _git("diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z").decode()
    diff = _git("diff", "--cached", "--diff-filter=ACMR", "-U0", "--no-color",
                "--no-ext-diff", "--no-renames").decode("utf-8", "replace")
    added = {name: [] for name in names.split("\0") if name}
    path, number = None, 0
    for line in diff.splitlines():
        if line.startswith("+++ "):
            path = line[6:] if line.startswith("+++ b/") else None
        elif line.startswith("@@"):
            number = int(re.match(r"@@ -\S+ \+(\d+)", line).group(1))
        elif line.startswith("+") and path is not None:
            added.setdefault(path, []).append((number, line[1:]))
            number += 1
    return added.items()


def tracked_files():
    """Yield (path, [(line number, line)]) for every tracked file (for --all)."""
    for path in _git("ls-files", "-z").decode().split("\0"):
        if not path:
            continue
        try:
            with open(path, encoding="utf-8") as f:
                lines = list(enumerate(f.read().splitlines(), 1))
        except (OSError, UnicodeDecodeError):
            lines = []  # binary files are covered by the path rules
        yield path, lines


def main(argv):
    repo_root = _git("rev-parse", "--show-toplevel").decode().strip()
    git_dir = os.path.abspath(_git("rev-parse", "--git-dir").decode().strip())
    os.chdir(repo_root)
    denylist = load_denylist(repo_root, git_dir)
    source = tracked_files() if "--all" in argv else staged_additions()

    problems = []
    for path, lines in source:
        for reason in check_path(path):
            problems.append("%s: %s" % (path, reason))
        for number, line in lines:
            for reason in check_line(path, line, denylist):
                problems.append("%s:%d: %s" % (path, number, reason))

    if problems:
        sys.stderr.write("leak-guard: refusing to commit personal data or secrets "
                         "(this repo is public):\n")
        for p in problems:
            sys.stderr.write("  " + p + "\n")
        sys.stderr.write("Unstage the file, or replace the value with synthetic data. "
                         "For a genuine false positive add '%s' to the line.\n" % ALLOW_PRAGMA)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
