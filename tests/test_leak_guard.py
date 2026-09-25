"""Tests for .githooks/leak_guard.py, the pre-commit guard against leaking personal data.

Three layers:

* realistic *synthetic* Garmin artifacts (activity JSON, GPX, OAuth tokens,
  config-local.toml, coordinate CSV) shaped exactly like the real ones must be
  rejected, and their sanitized fixture versions accepted;
* end-to-end commits in a throwaway git repo wired to the real hooks;
* the user's *real* downloaded data (``data/``, ``.auth/``, ``config-local.toml``)
  must all be rejected - skipped on a fresh clone where that data does not exist.
  These tests only assert; they never print the data.

Leak-shaped values are assembled at runtime (kwargs, arithmetic, real Fernet
encryption) so that this file itself passes the guard.
"""
import base64
import glob
import json
import os
import random
import secrets
import shutil
import subprocess
import sys

import pytest
from cryptography.fernet import Fernet

from conftest import PROJECT_ROOT

HOOKS_DIR = os.path.join(PROJECT_ROOT, ".githooks")
sys.path.insert(0, HOOKS_DIR)
import leak_guard  # noqa: E402

AT = "@"


# ---- realistic synthetic Garmin artifacts -----------------------------------

def track(lat0, lon0, points=50, seed=1):
    """A random-walk track with Garmin's full float precision."""
    rnd = random.Random(seed)
    lat, lon, out = lat0, lon0, []
    for _ in range(points):
        lat += rnd.uniform(-0.0004, 0.0004)
        lon += rnd.uniform(-0.0004, 0.0004)
        out.append((lat, lon))
    return out


def activity_json(lat0, lon0, owner=True):
    """Shaped like data/json/*.json as returned by api.get_activity()."""
    start, end = track(lat0, lon0)[0], track(lat0, lon0)[-1]
    activity = dict(
        activityId=17018598242, activityName="Morning Run",
        activityType=dict(typeId=1, typeKey="running", parentTypeId=17),
        startTimeLocal="2024-05-01 07:30:00", distance=5321.4, duration=1830.2,
        startLatitude=start[0], startLongitude=start[1],
        endLatitude=end[0], endLongitude=end[1],
        ownerId=None, ownerDisplayName=None, ownerFullName=None,
        ownerProfileImageUrlSmall=None, deviceId=None,
        activityUUID="00000000-0000-0000-0000-000000000000", userPro=False,
    )
    if owner:
        activity.update(
            ownerId=81234567, ownerDisplayName="c8e1f7a2-5b3d-4e6f-9a1b-2c3d4e5f6a7b",
            ownerFullName="Jan Novák", deviceId=3412345678,
            ownerProfileImageUrlSmall="https://s3.amazonaws.com/garmin-connect-prod/"
                                      "profile_images/abc-prth.png")
    return json.dumps(activity, indent=2)


def garmin_gpx(lat0, lon0):
    """Shaped like data/gpx/*.gpx as exported by Garmin Connect."""
    points = "\n".join(
        '      <trkpt lat="{:.15f}" lon="{:.15f}">\n'
        '        <ele>250.1999969482422</ele>\n'
        '        <time>2024-05-01T05:30:{:02d}.000Z</time>\n'
        '      </trkpt>'.format(lat, lon, i % 60)
        for i, (lat, lon) in enumerate(track(lat0, lon0)))
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<gpx creator="Garmin Connect" version="1.1"\n'
            '  xmlns="http://www.topografix.com/GPX/1/1">\n'
            '  <metadata><time>2024-05-01T05:30:00.000Z</time></metadata>\n'
            '  <trk>\n    <name>Morning Run</name>\n    <type>running</type>\n'
            '    <trkseg>\n' + points + '\n    </trkseg>\n  </trk>\n</gpx>\n')


def coords_csv(lat0, lon0):
    """Shaped like data/coordinates/*.csv (5 decimal places)."""
    return "latitude,longitude\n" + "\n".join(
        "{:.5f},{:.5f}".format(lat, lon) for lat, lon in track(lat0, lon0))


def jwt():
    enc = lambda obj: base64.urlsafe_b64encode(json.dumps(obj).encode()).decode().rstrip("=")
    return "%s.%s.%s" % (enc(dict(alg="RS256", typ="JWT")),
                         enc(dict(sub="81234567", scope=["CONNECT_READ"], exp=1790000000)),
                         "c2lnbmF0dXJlLXNpZ25hdHVyZS1zaWduYXR1cmU")


def oauth1_token():
    """Shaped like .auth/oauth1_token.json."""
    return json.dumps(dict(oauth_token=secrets.token_hex(24),
                           oauth_token_secret=secrets.token_urlsafe(24),
                           mfa_token=None, mfa_expiration_timestamp=None,
                           domain="garmin.com"))


def oauth2_token():
    """Shaped like .auth/oauth2_token.json."""
    return json.dumps(dict(scope="CONNECT_READ CONNECT_WRITE", jti="1c2d3e4f",
                           token_type="Bearer", access_token=jwt(),
                           refresh_token=secrets.token_urlsafe(48),
                           expires_in=3600, expires_at=1790000000))


def config_local(host="ftp.example-home-site.cz"):
    """Shaped like config-local.toml with an encrypted FTP password and API keys."""
    token = Fernet(Fernet.generate_key()).encrypt(b"hunter2").decode()
    return "\n".join([
        "[ftp]", 'host = "%s"' % host, 'user = "janovak"', 'pass = "%s"' % token,
        'remote-path = "/www/activities"', "", "[map-tiles]",
        'mapy-com-api-key = "Xk3F9aLq2Zr7Ws1Ev6Bn"', 'carto-api-key = "cA7rT0kEy5x"', ""])


# written as sums so this file does not contain a literal precise position
PRAGUE = (50 + 0.0213, 14 + 0.5267)  # where a real user might live -> must be caught
NULL_ISLAND = (0.0213, 0.5267)  # synthetic fixture box, open ocean -> allowed


def reasons(path, text, denylist=()):
    return [r for _, _, rs in leak_guard.check_text(path, text, denylist) for r in rs]


# ---- content rules ----------------------------------------------------------

class TestRealisticLeaksAreCaught:
    def test_activity_json_owner_fields(self):
        found = reasons("tests/fixtures/a.json", activity_json(*NULL_ISLAND))
        assert any("owner" in r for r in found)
        assert not any("GPS" in r for r in found)

    def test_activity_json_start_coordinates(self):
        found = reasons("tests/fixtures/a.json", activity_json(*PRAGUE, owner=False))
        assert any("GPS" in r for r in found)

    def test_gpx_track(self):
        assert any("GPS" in r for r in reasons("tests/fixtures/a.xml", garmin_gpx(*PRAGUE)))

    def test_coordinate_csv(self):
        assert any("GPS" in r for r in reasons("tests/fixtures/a.csv", coords_csv(*PRAGUE)))

    def test_southern_and_western_hemispheres(self):
        assert reasons("x.csv", coords_csv(-33 - 0.8568, -151 - 0.2153))

    def test_polyline_in_generated_output(self):
        # output/data/*.json stores tracks as [[lat, lon], ...]
        line = json.dumps([list(p) for p in track(*PRAGUE, points=3)])
        assert any("GPS" in r for r in reasons("x.json", line))

    def test_oauth_tokens(self):
        assert any("OAuth" in r for r in reasons("x.json", oauth1_token()))
        found = reasons("x.json", oauth2_token())
        assert any("JWT" in r for r in found) and any("OAuth" in r for r in found)

    def test_config_local_pasted_into_default(self):
        found = reasons("config-default.toml", config_local())
        assert any("Fernet" in r for r in found)
        assert sum("credential" in r for r in found) == 6  # host, user, pass, path, 2 API keys
        # Fernet token is caught in any file type, not only TOML
        assert any("Fernet" in r for r in reasons("notes.md", config_local()))

    def test_email_address(self):
        assert reasons("README.md", "contact: jan.novak" + AT + "seznam.cz")

    def test_denylist_strings(self):
        assert reasons("README.md", "Map at ftp.example-home-site.cz/www",
                       denylist=["ftp.example-home-site.cz"])

    @pytest.mark.parametrize("line", [
        "author: Zorvak",
        'name = "zorvak"',
        "zorvak.qentin" + AT + "example.com",
        "tracks/zorvak_2024.gpx",
        "by Qentin Zorvak.",
    ])
    def test_denylisted_name_as_whole_word(self, line):
        assert reasons("README.md", line, denylist=["zorvak", "Qentin Zorvak"])

    @pytest.mark.parametrize("line", ["def zorvakify(x):", "unzorvak = 1", "Zorvak2"])
    def test_denylisted_name_inside_longer_word_passes(self, line):
        assert reasons("README.md", line, denylist=["zorvak"]) == []

    def test_non_name_entries_still_match_as_substring(self):
        # a password or key has no word boundaries to rely on
        assert reasons("README.md", "x=abQ7pw9zz;", denylist=["Q7pw9"])


class TestSanitizedFixturesPass:
    def test_null_island_fixtures(self):
        assert reasons("tests/fixtures/a.json", activity_json(*NULL_ISLAND, owner=False)) == []
        assert reasons("tests/fixtures/a.xml", garmin_gpx(*NULL_ISLAND)) == []
        assert reasons("tests/fixtures/a.csv", coords_csv(*NULL_ISLAND)) == []

    def test_round_and_coarse_coordinates(self):
        # round numbers and ~1 km precision are not a location
        assert reasons("docs/a.md", "50.000000,14.000000\n[50.08, 14.44]\n48.0010, 16.0020") == []

    def test_empty_default_config(self):
        with open(os.path.join(PROJECT_ROOT, "config-default.toml"), encoding="utf-8") as f:
            assert reasons("config-default.toml", f.read()) == []

    def test_allowed_emails(self):
        text = "Co-Authored-By: Claude <noreply" + AT + "anthropic.com>\nuser" + AT + "example.com"
        assert reasons("README.md", text) == []

    def test_pragma(self):
        line = coords_csv(*PRAGUE).splitlines()[1] + "  # leak-guard: allow"
        assert reasons("x.py", line) == []


# ---- path rules -------------------------------------------------------------

@pytest.mark.parametrize("path", [
    "data/activities_list.csv", "output/activities_map.html", ".auth/oauth2_token.json",
    "config-local.toml", "sub/config-local.toml", "tests/fixtures/run.gpx", "x/ride.FIT",
    "a.tcx", "2024-05-01_17018598242_running.json", "tests/oauth1_token.json",
])
def test_blocked_paths(path):
    assert leak_guard.check_path(path)


@pytest.mark.parametrize("path", [
    "tests/test_downloader.py", "config-default.toml", "docs/architecture.md",
    "templates/activity_loader_template.html", "images/activity-popup.png",
])
def test_allowed_paths(path):
    assert leak_guard.check_path(path) == []


def test_denylist_loaded_from_config_local_and_git_dir(tmp_path):
    (tmp_path / "config-local.toml").write_text(config_local(), encoding="utf-8")
    (tmp_path / "leak-guard-denylist").write_text("# comment\nJan Novák\n\nab\n", encoding="utf-8")
    entries = leak_guard.load_denylist(str(tmp_path), str(tmp_path))
    assert "ftp.example-home-site.cz" in entries and "janovak" in entries
    assert "Xk3F9aLq2Zr7Ws1Ev6Bn" in entries and "Jan Novák" in entries
    assert "ab" not in entries and not any(e.startswith("#") for e in entries)


# ---- end-to-end: real hooks in a throwaway repo -----------------------------

needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")


@pytest.fixture
def repo(tmp_path):
    def git(*args, check=True):
        return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t" + AT + "example.com",
                               *args], cwd=tmp_path, capture_output=True, text=True, check=check)

    git("init", "-q")
    git("config", "core.hooksPath", HOOKS_DIR)
    (tmp_path / ".gitignore").write_text("data/\nconfig-local.toml\n")
    (tmp_path / "config-local.toml").write_text(config_local(), encoding="utf-8")
    git("add", ".gitignore")
    git("commit", "-q", "-m", "init")

    def commit(path, text, force=False):
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        git("add", *(["-f"] if force else []), path)
        result = git("commit", "-q", "-m", "change " + path, check=False)
        if result.returncode:
            git("reset", "-q")
        return result

    repo = type("Repo", (), {})()
    repo.git, repo.commit, repo.path = git, commit, tmp_path
    return repo


LEAKS = {
    "activity-json": ("tests/fixtures/activity.json", activity_json(*PRAGUE)),
    "garmin-gpx-as-xml": ("tests/fixtures/track.xml", garmin_gpx(*PRAGUE)),
    "oauth2-token": ("notes/tokens.json", oauth2_token()),
    "config-local-in-default": ("config-default.toml", config_local()),
    "config-local-value": ("README.md", "Published at ftp.example-home-site.cz\n"),
}


@needs_git
class TestHookEndToEnd:
    def commit_count(self, repo):
        return int(repo.git("rev-list", "--count", "HEAD").stdout)

    @pytest.mark.parametrize("leak", LEAKS)
    def test_leaks_are_rejected(self, repo, leak):
        path, text = LEAKS[leak]
        result = repo.commit(path, text)
        assert result.returncode != 0 and "leak-guard" in result.stderr
        assert self.commit_count(repo) == 1

    @pytest.mark.parametrize("path", ["data/activities_list.csv", "config-local.toml"])
    def test_force_added_ignored_files_are_rejected(self, repo, path):
        result = repo.commit(path, "date,time\n", force=True)
        assert result.returncode != 0 and path in result.stderr

    def test_sanitized_fixture_is_committed(self, repo):
        result = repo.commit("tests/fixtures/activity.json", activity_json(*NULL_ISLAND, owner=False))
        assert result.returncode == 0, result.stderr
        assert self.commit_count(repo) == 2

    def test_only_added_lines_are_checked(self, repo):
        # content committed before the guard existed must not block unrelated edits
        legacy = coords_csv(*PRAGUE) + "\n"
        (repo.path / "legacy.csv").write_text(legacy)
        repo.git("add", "legacy.csv")
        repo.git("-c", "core.hooksPath=/dev/null", "commit", "-qm", "pre-guard content")
        result = repo.commit("legacy.csv", legacy + "0.0,0.0\n")
        assert result.returncode == 0, result.stderr

    def test_commit_msg_strips_claude_session_trailer(self, repo):
        (repo.path / "a.txt").write_text("a\n")
        repo.git("add", "a.txt")
        repo.git("commit", "-q", "-m", "msg\n\nCo-Authored-By: x\nClaude-Session: https://x/1")
        body = repo.git("log", "-1", "--format=%B").stdout
        assert "Claude-Session" not in body and "Co-Authored-By: x" in body


@needs_git
def test_whole_repo_passes_audit():
    """Every tracked file is clean, so the guard has no false positives here and
    nothing slipped in via --no-verify."""
    if not os.path.isdir(os.path.join(PROJECT_ROOT, ".git")):
        pytest.skip("not a git checkout")
    result = subprocess.run([sys.executable, os.path.join(HOOKS_DIR, "leak_guard.py"), "--all"],
                            cwd=PROJECT_ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


# ---- the user's real downloaded data (local only) ---------------------------

def real_files(pattern, limit=300):
    files = sorted(glob.glob(os.path.join(PROJECT_ROOT, pattern)))
    if not files:
        pytest.skip("no real data at %s (fresh clone)" % pattern)
    step = max(1, len(files) // limit)  # spread the sample across the years
    return files[::step]


def read(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


class TestRealDataIsCaught:
    """Content rules alone (as if the file were renamed into tests/) must catch real data."""

    def assert_all_caught(self, files, has_content=lambda text: True):
        checked, missed = 0, []
        for path in files:
            text = read(path)
            if not has_content(text):
                continue
            checked += 1
            if not any(leak_guard.check_line("tests/fixtures/renamed.txt", line)
                       for line in text.splitlines()):  # stops at the first finding
                missed.append(os.path.basename(path))  # file name only: never echo contents
        assert checked, "no file with content to check"
        assert missed == []

    def test_activity_json(self):
        self.assert_all_caught(real_files("data/json/*.json"))

    def test_gpx_tracks(self):
        self.assert_all_caught(real_files("data/gpx/*.gpx"), lambda t: "<trkpt" in t)

    def test_coordinate_csvs(self):
        self.assert_all_caught(real_files("data/coordinates/*.csv"), lambda t: t.count("\n") > 1)

    def test_generated_map_data(self):
        self.assert_all_caught(real_files("output/data/*_activities.json"))

    def test_auth_tokens(self):
        self.assert_all_caught(real_files(".auth/oauth*_token.json"))

    def test_real_paths_are_blocked(self):
        files = real_files("data/*/*") + real_files(".auth/*")
        rel = [os.path.relpath(f, PROJECT_ROOT).replace(os.sep, "/") for f in files]
        assert [p for p in rel if not leak_guard.check_path(p)] == []

    def test_config_local_values_are_denylisted(self):
        path = os.path.join(PROJECT_ROOT, "config-local.toml")
        if not os.path.exists(path):
            pytest.skip("no config-local.toml")
        denylist = leak_guard.load_denylist(PROJECT_ROOT, os.path.join(PROJECT_ROOT, ".git"))
        # pasted into the committed default, every credential line is caught
        text = read(path)
        secret_lines = [l for l in text.splitlines() if leak_guard.PRIVATE_CONFIG_KEYS.match(l)]
        assert all(leak_guard.check_line("config-default.toml", l, denylist) for l in secret_lines)
