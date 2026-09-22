"""Pinned, hash-verified external data used by NASA loss correlations."""

import argparse
import hashlib
from pathlib import Path
from typing import Dict
from urllib.request import urlopen


NASA_REVISION = "23c2b0bf781b4b030014f458ecfde872896777a2"
NASA_LOSS_ASSETS: Dict[str, Dict[str, str]] = {
    "kackerokapuu.pkl": {
        "sha256": "3ea35e852544a7d16b783b76c5770887fb16efc887261878cc1d143e5204424f",
        "path": "references/Turbines/KackerOkapuu/kackerokapuu.pkl",
    },
    "ainleymathieson.pkl": {
        "sha256": "7178538526cd4bb8d64ef8c51a07af875d50d4fb158325f688ab84b224020d9a",
        "path": "references/Turbines/AinleyMathieson/ainleymathieson.pkl",
    },
}


def nasa_asset_cache() -> Path:
    return Path.home() / ".cache" / "TD3_LossModels"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_nasa_asset(filename: str) -> Path:
    spec = NASA_LOSS_ASSETS[filename]
    path = nasa_asset_cache() / filename
    if not path.is_file():
        raise RuntimeError(
            "missing pinned NASA loss asset {}; run sunimuhendis-setup-throughflow".format(
                filename
            )
        )
    actual = file_sha256(path)
    if actual != spec["sha256"]:
        raise RuntimeError(
            "NASA loss asset {} failed SHA-256 verification; rerun sunimuhendis-setup-throughflow --replace".format(
                filename
            )
        )
    return path


def install_nasa_asset(filename: str, replace: bool = False) -> Path:
    spec = NASA_LOSS_ASSETS[filename]
    destination = nasa_asset_cache() / filename
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and not replace and file_sha256(destination) == spec["sha256"]:
        return destination

    url = "https://raw.githubusercontent.com/nasa/turbo-design/{}/{}".format(
        NASA_REVISION, spec["path"]
    )
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    with urlopen(url, timeout=60) as response, temporary.open("wb") as output:
        output.write(response.read())
    actual = file_sha256(temporary)
    if actual != spec["sha256"]:
        temporary.unlink(missing_ok=True)
        raise RuntimeError(
            "SHA-256 mismatch for {}: expected {}, got {}".format(
                filename, spec["sha256"], actual
            )
        )
    temporary.replace(destination)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()
    for filename in NASA_LOSS_ASSETS:
        print(install_nasa_asset(filename, replace=args.replace))


if __name__ == "__main__":
    main()
