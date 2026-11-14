"""Parse a project's pinned dependencies and find version drift against PyPI."""
import re
from dataclasses import dataclass
from pathlib import Path

import requests
from packaging.version import InvalidVersion, Version

REQ_LINE = re.compile(r"^\s*([A-Za-z0-9_.\-]+)\s*==\s*([A-Za-z0-9_.\-]+)")
SKIP = {"pytest", "pip", "setuptools", "wheel"}  # tooling, not runtime deps


@dataclass
class Drift:
    name: str
    current: str
    latest: str
    major_bump: bool

    def as_dict(self):
        return self.__dict__.copy()


def parse_requirements(repo: Path) -> dict[str, str]:
    req = repo / "requirements.txt"
    pins = {}
    if not req.exists():
        return pins
    for line in req.read_text().splitlines():
        m = REQ_LINE.match(line.split("#")[0])
        if m:
            pins[m.group(1).lower()] = m.group(2)
    return pins


def latest_version(name: str) -> str | None:
    try:
        r = requests.get(f"https://pypi.org/pypi/{name}/json", timeout=15)
        r.raise_for_status()
        releases = [v for v in r.json()["releases"] if r.json()["releases"][v]]
        stable = []
        for v in releases:
            try:
                pv = Version(v)
            except InvalidVersion:
                continue
            if not pv.is_prerelease and not pv.is_devrelease:
                stable.append(pv)
        return str(max(stable)) if stable else r.json()["info"]["version"]
    except Exception:
        return None


def find_drift(repo: Path) -> list[Drift]:
    drifts = []
    for name, current in parse_requirements(repo).items():
        if name in SKIP:
            continue
        latest = latest_version(name)
        if not latest:
            continue
        try:
            cur, new = Version(current), Version(latest)
        except InvalidVersion:
            continue
        if new > cur:
            major = new.major > cur.major or (cur.major == 0 and new.minor > cur.minor)
            drifts.append(Drift(name, current, latest, major))
    return drifts


def upgraded_requirements(repo: Path, drifts: list[Drift]) -> str:
    """requirements.txt text with drifted packages bumped to latest."""
    bump = {d.name: d.latest for d in drifts}
    out = []
    for line in (repo / "requirements.txt").read_text().splitlines():
        m = REQ_LINE.match(line.split("#")[0])
        if m and m.group(1).lower() in bump:
            out.append(f"{m.group(1)}=={bump[m.group(1).lower()]}")
        else:
            out.append(line)
    return "\n".join(out) + "\n"
