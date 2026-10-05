#!/usr/bin/env python3
"""Set up Garmin Activities Map: from a fresh clone to your first map in one command.

    python3 install.py        (on Windows: py install.py)

It runs in two steps. The first runs under any Python 3 and uses only the standard
library: it finds Python 3.12 or newer, creates venv/ and installs requirements.txt.
The second restarts inside venv/ and asks a few questions (background map keys, FTP
publishing), saves the answers to config-local.toml, logs in to Garmin Connect and
downloads the activities. Running it again is safe: it reuses the venv, offers the
saved answers as defaults and skips the login while the token is valid.

Keep this file parseable by old Python 3 versions (no walrus, no match, no `X | Y`
annotations), so that an old interpreter gets the "you need Python 3.12" message
rather than a SyntaxError.
"""
import argparse
import getpass
import json
import os
import platform
import re
import shutil
import subprocess
import sys

MIN_PYTHON = (3, 12)
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
LOCAL_CONFIG = "config-local.toml"
LOCAL_CONFIG_HEADER = "# Put your personal configuration and overrides of default config into this file\n"
IS_WINDOWS = os.name == "nt"


# ##########################################################
# Console helpers
# ##########################################################

def say(text=""):
    print(text, flush=True)


def heading(text):
    say()
    say(text)
    say("-" * len(text))


def ask(question, default=""):
    """Ask for a value; Enter keeps the default shown in brackets."""
    shown = f" [{default}]" if default else ""
    answer = input(f"{question}{shown}: ").strip()
    return answer or default


def ask_yes_no(question, default=True):
    hint = "Y/n" if default else "y/N"
    while True:
        answer = input(f"{question} [{hint}]: ").strip().lower()
        if not answer:
            return default
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        say("Please answer y or n.")


def ask_optional(question, has_saved=False, secret=False):
    """Ask for a value that may be left out. Return None on Enter, which skips it or keeps the saved one."""
    hint = "Enter keeps the saved one" if has_saved else "Enter to skip"
    hint = f" (hidden as you type; {hint})" if secret else f" ({hint})"
    prompt = getpass.getpass if secret else input
    answer = prompt(f"{question}{hint}: ").strip()
    return answer or None


# ##########################################################
# Step 1: Python, venv and libraries (standard library only)
# ##########################################################

def python_version(command):
    """Return (major, minor) of the interpreter started by `command`, or None if it does not run."""
    try:
        output = subprocess.run(command + ["-c", "import sys; print(sys.version_info[0], sys.version_info[1])"],
                                capture_output=True, text=True, timeout=30).stdout
        major, minor = output.split()
        return int(major), int(minor)
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def python_candidates():
    if IS_WINDOWS:
        return [["py", f"-3.{minor}"] for minor in range(20, MIN_PYTHON[1] - 1, -1)] + [["py", "-3"], ["python"]]
    return [[f"python3.{minor}"] for minor in range(20, MIN_PYTHON[1] - 1, -1)] + [["python3"], ["python"]]


def find_python():
    """Return the command of a Python >= MIN_PYTHON: this one, or the newest one on PATH; None if there is none."""
    if sys.version_info[:2] >= MIN_PYTHON:
        return [sys.executable]
    for command in python_candidates():
        if shutil.which(command[0]) is None:
            continue
        version = python_version(command)
        if version is not None and version >= MIN_PYTHON:
            return command
    return None


def python_install_hint():
    required = "%d.%d" % MIN_PYTHON
    system = platform.system()
    if system == "Darwin":
        how = (f"  brew install python@{required}\n"
               "or download the installer from https://www.python.org/downloads/")
    elif system == "Windows":
        how = (f"  winget install Python.Python.{required}\n"
               "or download the installer from https://www.python.org/downloads/")
    else:
        how = (f"  sudo apt install python{required} python{required}-venv    (Debian, Ubuntu)\n"
               f"  sudo dnf install python{required}                       (Fedora)\n"
               "or use your distribution's package manager")
    return (f"Garmin Activities Map needs Python {required} or newer, and none was found.\n"
            f"Install it, e.g. with\n{how}\n"
            "and then run this installer again.")


def venv_python(venv_dir):
    if IS_WINDOWS:
        return os.path.join(venv_dir, "Scripts", "python.exe")
    return os.path.join(venv_dir, "bin", "python")


def venv_is_usable(venv_dir):
    python = venv_python(venv_dir)
    if not os.path.exists(python):
        return False
    version = python_version([python])
    return version is not None and version >= MIN_PYTHON


def ensure_venv(python_command, venv_dir):
    """Create the venv, or reuse a working one. Return False if there is none at the end."""
    if venv_is_usable(venv_dir):
        say(f"Using the existing virtual environment in {venv_dir}")
        return True
    if os.path.exists(venv_dir):
        say(f"{venv_dir} exists, but it does not work here (wrong Python version, or made on another computer).")
        if not ask_yes_no(f"Delete {venv_dir} and create it again?"):
            say("Stopped. Or pick a different directory with --venv.")
            return False
        shutil.rmtree(venv_dir)
    say(f"Creating a virtual environment in {venv_dir} ...")
    result = subprocess.run(python_command + ["-m", "venv", venv_dir], capture_output=True, text=True)
    if result.returncode != 0:
        say(result.stdout + result.stderr)
        say("Creating the virtual environment failed.")
        if platform.system() == "Linux":
            say("On Debian and Ubuntu, install the venv module first: sudo apt install python%d.%d-venv" % MIN_PYTHON)
        return False
    return True


def install_requirements(venv_dir):
    say("Installing the libraries the tool needs (this takes a minute) ...")
    result = subprocess.run([venv_python(venv_dir), "-m", "pip", "install", "--disable-pip-version-check",
                             "-q", "-r", os.path.join(PROJECT_ROOT, "requirements.txt")],
                            capture_output=True, text=True)
    if result.returncode != 0:
        say(result.stdout + result.stderr)
        say("Installing the libraries failed; the output above says why. Check your internet connection and "
            "run the installer again.")
        return False
    return True


def set_up_environment(venv_dir):
    heading("1/4  Python and libraries")
    python_command = find_python()
    if python_command is None:
        say(python_install_hint())
        return False
    say("Found Python %d.%d" % python_version(python_command))
    return ensure_venv(python_command, venv_dir) and install_requirements(venv_dir)


# ##########################################################
# Editing config-local.toml
# ##########################################################

def toml_string(value):
    # JSON string escapes are valid in TOML basic strings, and \uXXXX covers control characters
    return json.dumps(value, ensure_ascii=False)


def set_toml_value(text, section, key, value):
    """Set `key = "value"` in [section] of TOML `text`, keeping everything else (comments included) as it is.

    Replaces the key's line if the section has it, adds the line at the end of the section if not,
    and appends the section if the file has none. Handles one-line string values only.
    """
    line = f"{key} = {toml_string(value)}"
    lines = text.splitlines()
    header = re.compile(r"^\s*\[\s*" + re.escape(section) + r"\s*\]\s*(#.*)?$")
    start = next((i for i, current in enumerate(lines) if header.match(current)), None)
    if start is None:
        if lines and lines[-1].strip():
            lines.append("")
        lines += [f"[{section}]", line]
        return "\n".join(lines) + "\n"
    end = next((i for i in range(start + 1, len(lines)) if lines[i].lstrip().startswith("[")), len(lines))
    key_line = re.compile(r"^\s*(" + re.escape(key) + r'|"' + re.escape(key) + r'")\s*=')
    for i in range(start + 1, end):
        if key_line.match(lines[i]):
            lines[i] = line
            return "\n".join(lines) + "\n"
    last = end
    while last > start + 1 and not lines[last - 1].strip():
        last -= 1
    lines.insert(last, line)
    return "\n".join(lines) + "\n"


def apply_settings(text, settings):
    """Apply {(section, key): value} to the TOML text, then check that the result parses and reads back right."""
    import tomllib
    for (section, key), value in settings.items():
        text = set_toml_value(text, section, key, value)
    parsed = tomllib.loads(text)
    for (section, key), value in settings.items():
        if parsed.get(section, {}).get(key) != value:
            raise ValueError(f"[{section}] {key} did not end up in {LOCAL_CONFIG} as expected")
    return text


# ##########################################################
# Step 2: questions, Garmin login and the first run (inside the venv)
# ##########################################################

def read_local_config():
    """Return (text, parsed) of config-local.toml; an empty one if it does not exist yet."""
    import tomllib
    if not os.path.exists(LOCAL_CONFIG):
        return LOCAL_CONFIG_HEADER, {}
    with open(LOCAL_CONFIG, encoding="utf-8") as file:
        text = file.read()
    try:
        return text, tomllib.loads(text)
    except tomllib.TOMLDecodeError as err:
        raise SystemExit(f"{LOCAL_CONFIG} is not valid TOML ({err}). Fix or remove it and run the installer again.")


def load_default_config():
    import tomllib
    with open("config-default.toml", "rb") as file:
        return tomllib.load(file)


def ask_map_keys(local):
    heading("2/4  Background maps")
    say("OpenStreetMap works as it is. Two more providers need a free API key each; press Enter to skip.")
    say("  CARTO (Light, Dark and Voyager): get a key at https://carto.com/basemaps/apikey/")
    say("    Without one, these maps show an \"API KEY REQUIRED\" watermark.")
    say("  Mapy.com (detailed outdoor and winter maps): get a key at")
    say("    https://developer.mapy.com/en/rest-api-mapy-cz/api-key/  Without one, they are left out.")
    tiles = local.get("map-tiles", {})
    settings = {}
    for key, label in (("carto-api-key", "CARTO API key"), ("mapy-com-api-key", "Mapy.com API key")):
        value = ask_optional(label, has_saved=bool(tiles.get(key)))
        if value:
            settings[("map-tiles", key)] = value
    return settings


def ask_ftp(local):
    """Ask about publishing. Return (settings, plain-text password or None)."""
    heading("3/4  Publishing (optional)")
    say("The map is a set of static files. The tool can upload them to your own website over FTPS after each run.")
    ftp = local.get("ftp", {})
    if not ask_yes_no("Publish the map to a website?", default=bool(ftp.get("host"))):
        say("The map stays on this computer. You can set up publishing later by running this installer again.")
        return {("mode", "uploader"): "OFF"}, None

    settings = {
        ("mode", "uploader"): "ON",
        ("ftp", "host"): ask("Server (host name, e.g. ftp.example.com)", ftp.get("host", "")),
        ("ftp", "user"): ask("User name", ftp.get("user", "")),
    }
    password = ask_optional("Password", has_saved=bool(ftp.get("pass")), secret=True)
    if password is None and not ftp.get("pass"):
        say("No password given; set it later by running this installer again.")
    if ask_yes_no("Does the server support FTPS (encrypted FTP)? Most do.", ftp.get("protocol", "FTPS") != "FTP"):
        settings[("ftp", "protocol")] = "FTPS"
    else:
        say("Plain FTP sends the password and the files unencrypted.")
        settings[("ftp", "protocol")] = "FTP"
    settings[("ftp", "remote-path")] = ask("Directory on the server for the map, e.g. /www/map",
                                           ftp.get("remote-path", ""))
    settings[("ftp", "remote-filename")] = ask("File name of the map page", ftp.get("remote-filename", "index.html"))
    return settings, password


def reload_project_config(text):
    """Make the project's shared config dict match the new config-local.toml.

    Modules hold `config` by reference (from common import config), so it is refreshed in place.
    """
    import tomllib
    import common
    fresh = common.recursive_update(load_default_config(), tomllib.loads(text))
    common.config.clear()
    common.config.update(fresh)


def encrypt_ftp_password(password):
    """Encrypt with the per-machine key in the token store (created on first use), as ENCRYPT_FTP_PASSWORD does."""
    from cryptography.fernet import Fernet
    import ftpuploader
    return Fernet(ftpuploader.load_key(create=True)).encrypt(password.encode()).decode()


def test_ftp_connection():
    import ftpuploader
    from common import config
    say("Connecting ...")
    try:
        ftp_config = ftpuploader.FtpConfig.create_config(config)
        ftp = ftpuploader.connect(ftp_config)
        try:
            if ftp_config.remote_path:
                ftp.cwd(ftp_config.remote_path)
        finally:
            ftpuploader.close_ftp(ftp)
    except Exception as err:  # any failure is reported, and the user decides what to do
        say(f"The connection failed: {err}")
        say("Check the answers and run the installer again; the rest of the setup does not depend on it.")
        return False
    say("Connected, and the directory exists.")
    return True


def log_in_to_garmin():
    import common
    heading("4/4  Garmin Connect")
    token_file = os.path.join(common.config["storage"]["directory-token-store"], "garmin_tokens.json")
    if not os.path.exists(token_file):
        say("Log in with your Garmin Connect e-mail and password (and a one-time code if your account uses MFA).")
        say(f"They are used once: the tool keeps a self-renewing login token in {token_file}, not the password.")
    while common.init_api() is None:
        if not ask_yes_no("The login did not work. Try again?"):
            return False
    say("Logged in to Garmin Connect.")
    return True


def count_stored_activities():
    import storage
    return len(storage.load_activities_from_csv(False))


def run_tool(arguments):
    return subprocess.run([sys.executable, "activities-map.py"] + arguments).returncode == 0


def first_run(publish):
    from common import config
    say()
    say("Your settings are ready. The first run downloads your activities from Garmin Connect and builds the map.")
    say("With years of activities this takes a while; it can be stopped with Ctrl+C and continues where it stopped.")
    if not ask_yes_no("Download your activities and build the map now?"):
        return False
    batch = config["activities"]["max-number-of-activities"]
    while True:
        before = count_stored_activities()
        if not run_tool(["--downloader", "ON", "--map-creator", "ON", "--uploader", "ON" if publish else "OFF",
                         "--utility-mode", "OFF"]):
            say("The run failed; the messages above say why. Fix it and run the installer again: "
                "what has been downloaded is kept.")
            return False
        added = count_stored_activities() - before
        say(f"Downloaded {added} activities.")
        # Each run takes at most `batch` activities, oldest first, so a full batch means there may be more
        if added < batch or not ask_yes_no(f"Garmin may have more than {batch}. Download the next batch?"):
            return True


def open_map():
    import pathlib
    import webbrowser
    from common import config
    path = pathlib.Path(config["output"]["map-filename"]).resolve()
    if path.exists() and ask_yes_no("Open the map in your browser?"):
        webbrowser.open(path.as_uri())


def configure():
    os.chdir(PROJECT_ROOT)
    text, local = read_local_config()
    if not os.path.exists(LOCAL_CONFIG):
        # The project's modules create it on import otherwise, with a log line that would only confuse here
        with open(LOCAL_CONFIG, "w", encoding="utf-8") as file:
            file.write(text)
    reload_project_config(text)
    settings = ask_map_keys(local)
    ftp_settings, password = ask_ftp(local)
    settings.update(ftp_settings)
    if password is not None:
        settings[("ftp", "pass")] = encrypt_ftp_password(password)
    text = apply_settings(text, settings)
    with open(LOCAL_CONFIG, "w", encoding="utf-8") as file:
        file.write(text)
    reload_project_config(text)
    say(f"Saved your answers to {LOCAL_CONFIG}.")

    publish = settings[("mode", "uploader")] == "ON"
    if publish and ask_yes_no("Test the connection to the server now?"):
        test_ftp_connection()
    if log_in_to_garmin() and first_run(publish):
        open_map()
    print_summary(publish)
    return True


def print_summary(publish):
    from common import config
    python = os.path.relpath(sys.executable, PROJECT_ROOT) if sys.executable.startswith(PROJECT_ROOT) else sys.executable
    heading("Done")
    say("To update the map with your new activities, run:")
    say(f"  {python} activities-map.py")
    say(f"The map is in {config['output']['map-filename']}" + (", and is uploaded to your server." if publish else "."))
    say(f"To change these settings, run this installer again. All the other options are in {LOCAL_CONFIG}")
    say("(config-default.toml lists them) and in the README.")
    if publish:
        say(f"Back up {LOCAL_CONFIG} together with {config['storage']['directory-token-store']}ftp.key: "
            "the password cannot be decrypted without the key.")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Install Garmin Activities Map and set it up.")
    parser.add_argument("--venv", default="venv",
                        help="directory of the virtual environment, relative to the project (default: venv)")
    parser.add_argument("--configure", action="store_true", help=argparse.SUPPRESS)  # step 2, run inside the venv
    return parser.parse_args(argv)


STOPPED = "\nStopped. Run the installer again to continue; answers already saved are kept."


def main(argv=None):
    args = parse_args(argv)
    if args.configure:
        try:
            return 0 if configure() else 1
        except (KeyboardInterrupt, EOFError):
            say(STOPPED)
            return 1

    say("Garmin Activities Map setup")
    say("This installs the libraries, asks a few questions and downloads your activities.")
    say("Press Enter to accept the answer in [brackets]; Ctrl+C stops at any time.")
    venv_dir = os.path.join(PROJECT_ROOT, args.venv)
    try:
        if not set_up_environment(venv_dir):
            return 1
    except (KeyboardInterrupt, EOFError):
        say(STOPPED)
        return 1
    # Step 2 needs the installed libraries, so it runs on the venv's Python. It reports Ctrl+C itself.
    try:
        return subprocess.run([venv_python(venv_dir), os.path.abspath(__file__), "--configure"]).returncode
    except KeyboardInterrupt:
        return 1


if __name__ == "__main__":
    sys.exit(main())
