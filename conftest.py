"""Shared pytest fixtures and test bootstrap.

Importing ``common`` runs ``load_config()`` at module import time, which reads
``config-default.toml`` (and merges ``config-local.toml``) relative to the
current working directory. To make the test suite runnable from anywhere, we
chdir into the project root here, before any test module imports ``common``.

The project's ``config`` dict is a single object shared by reference across all
modules. Fixtures below mutate it in place (pointing storage at a tmp dir, etc.)
and restore the originals on teardown so tests stay isolated.
"""
import copy
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECT_ROOT)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest

import common


@pytest.fixture
def config():
    """Yield the shared config dict, restoring it fully after the test.

    Any test that mutates config values should use this fixture so changes do
    not leak into other tests (config is a process-wide shared object).
    """
    snapshot = copy.deepcopy(common.config)
    try:
        yield common.config
    finally:
        common.config.clear()
        common.config.update(snapshot)


@pytest.fixture
def storage_env(config, tmp_path):
    """Point all storage paths at an isolated tmp directory.

    Returns an object with the tmp paths and the (still empty) directories
    created. Storage functions read these config values at call time, so this
    redirects reads/writes away from the real ``data/`` tree.
    """
    json_dir = tmp_path / "json"
    gpx_dir = tmp_path / "gpx"
    coords_dir = tmp_path / "coordinates"
    for d in (json_dir, gpx_dir, coords_dir):
        d.mkdir()

    db_path = tmp_path / "activities_list.csv"

    config["storage"]["directory-json"] = str(json_dir)
    config["storage"]["directory-gpx"] = str(gpx_dir)
    config["storage"]["directory-coordinates"] = str(coords_dir)
    config["storage"]["activities-database"] = str(db_path)

    class Env:
        pass

    env = Env()
    env.tmp_path = tmp_path
    env.json_dir = json_dir
    env.gpx_dir = gpx_dir
    env.coords_dir = coords_dir
    env.db_path = db_path
    return env


def make_activity(storage_module, **overrides):
    """Build a storage.Activity with sensible defaults for tests."""
    kwargs = dict(
        activity_id=1,
        distance=5.0,
        duration=30.0,
        date="2024-05-01",
        time="07:30",
        filename="2024-05-01_1_running",
        has_gps_data=False,
        activity_type="running",
        name="Test Run",
    )
    kwargs.update(overrides)
    return storage_module.Activity(**kwargs)
