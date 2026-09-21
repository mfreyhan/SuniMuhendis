"""Pin upstream provenance and prepare local-only loss data for phase-2 probes."""
import hashlib
import importlib.metadata as metadata
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UPSTREAM = ROOT / "build/throughflow_research/turbo-design"
EXPECTED_SHA = "23c2b0bf781b4b030014f458ecfde872896777a2"
REPORTS = ROOT / "reports/throughflow_phase_0_2"
ASSETS = ROOT / "build/throughflow_research/isolated_home/.cache/TD3_LossModels"


def main():
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=UPSTREAM, text=True).strip()
    if sha != EXPECTED_SHA:
        raise RuntimeError("Upstream SHA changed: {}".format(sha))
    changed = subprocess.check_output(["git", "diff", "--name-only", "HEAD"], cwd=UPSTREAM, text=True).splitlines()
    if changed:
        raise RuntimeError("Upstream has tracked modifications: {}".format(changed))
    ASSETS.mkdir(parents=True, exist_ok=True)
    records = []
    for source in sorted((UPSTREAM / "references/Turbines").rglob("*.pkl")):
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        target = ASSETS / source.name
        temp = target.with_suffix(".partial")
        shutil.copyfile(source, temp)
        assert hashlib.sha256(temp.read_bytes()).hexdigest() == digest
        temp.replace(target)
        records.append({"path": source.relative_to(UPSTREAM).as_posix(), "sha256": digest,
                        "bytes": source.stat().st_size, "redistributed_in_sunimuhendis": False})
    packages = []
    for dist in sorted(metadata.distributions(), key=lambda d: d.metadata["Name"].lower()):
        packages.append({"name": dist.metadata["Name"], "version": dist.version,
                         "requires_python": dist.metadata.get("Requires-Python"),
                         "license_expression": dist.metadata.get("License-Expression"),
                         "license_summary": (dist.metadata.get("License") or "").splitlines()[:1],
                         "license_classifiers": [v for v in dist.metadata.get_all("Classifier", []) if v.startswith("License")],
                         "project_urls": dist.metadata.get_all("Project-URL", [])})
    payload = {"upstream": "https://github.com/nasa/turbo-design", "sha": sha,
               "python": sys.version, "platform": platform.platform(),
               "license_files": [p.relative_to(UPSTREAM).as_posix() for p in UPSTREAM.rglob("*")
                                 if p.is_file() and p.name.lower().startswith(("license", "copying", "notice")) and ".git" not in p.parts],
               "loss_assets": records, "packages": packages,
               "scope": "Research installation only; no NASA code or loss tables shipped in this repository."}
    suffix = "py{}{}".format(sys.version_info.major, sys.version_info.minor)
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / ("backend_manifest_" + suffix + ".json")).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    locked = ["# Windows research lock; upstream is separately pinned to " + sha,
              "# Install pinned upstream with --no-deps after these packages."]
    locked += ["{}=={}".format(p["name"], p["version"]) for p in packages if p["name"].lower() != "turbo-design"]
    (REPORTS / ("requirements_" + suffix + ".txt")).write_text("\n".join(locked) + "\n", encoding="utf-8")
    print(sha, len(records), "pinned assets;", len(packages), "packages; license files:", payload["license_files"])


if __name__ == "__main__":
    main()
