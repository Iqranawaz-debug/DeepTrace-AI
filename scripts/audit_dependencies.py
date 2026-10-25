"""Offline installed-package license inventory and notice preservation.

Run with backend/.venv/Scripts/python.exe from any directory after npm ci.
Does not alter any third-party files or perform network operations.
"""

import importlib.metadata as metadata
import json
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APPROVED_MPL = {"certifi", "pathspec", "axe-core", "@axe-core/playwright"}
ALLOWED = {
    "MIT", "MIT-0", "ISC", "BSD-2-Clause", "BSD-3-Clause", "0BSD",
    "Apache-2.0", "Apache-2.0 OR BSD-2-Clause", "PSF-2.0", "OFL-1.1",
    "BlueOak-1.0.0", "CC0-1.0", "CC-BY-4.0", "MPL-2.0",
}


def normalized(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def check_license(name, license_id):
    if license_id not in ALLOWED:
        raise RuntimeError(f"Review required: {name}: {license_id}")
    if license_id == "MPL-2.0" and not (
        name in APPROVED_MPL or name == "lightningcss" or name.startswith("lightningcss-")
    ):
        raise RuntimeError(f"Separate copyleft approval required: {name}")


def legal_file(path):
    return path.name.lower().startswith(("license", "licence", "copying", "notice"))


def section(name, version, license_id, files):
    content = [f"\n{'=' * 72}\n{name} {version} — {license_id}\n"]
    for path in sorted(files):
        content.append(f"\n--- {path.name} ---\n{path.read_text(encoding='utf-8', errors='replace')}")
    return "\n".join(content)


def main():
    inventory = []
    notices = ["DeepTrace AI dependency notices. Original application code: Apache-2.0.\n"
               "Third-party files retain the licenses below. Generated from installed artifacts.\n"]
    frontend_notices = [notices[0]]
    lock = json.loads((ROOT / "frontend/package-lock.json").read_text(encoding="utf-8"))
    for relative, package in sorted(lock["packages"].items()):
        if not relative:
            continue
        name = relative.rsplit("node_modules/", 1)[1]
        license_id = package.get("license", "UNKNOWN")
        check_license(name, license_id)
        directory = ROOT / "frontend" / relative
        installed = (directory / "package.json").exists()
        if installed:
            actual = json.loads((directory / "package.json").read_text(encoding="utf-8"))
            if actual["version"] != package["version"]:
                raise RuntimeError(f"Lock mismatch: {name}")
        inventory.append({"ecosystem": "npm", "name": name, "version": package["version"],
                          "license": license_id, "development": package.get("dev", False),
                          "installed": installed, "path": relative,
                          "artifact": package.get("resolved"), "integrity": package.get("integrity")})
        if installed:
            files = [p for p in directory.iterdir() if p.is_file() and legal_file(p)]
            if name == "react-remove-scroll-bar":
                files.append(ROOT / "docs/licenses/react-remove-scroll-bar-2.3.8.txt")
            notice = section(name, package["version"], license_id, files)
            notices.append(notice)
            if not package.get("dev", False):
                frontend_notices.append(notice)

    lock = tomllib.loads((ROOT / "backend/uv.lock").read_text(encoding="utf-8"))
    locked = {normalized(p["name"]): p for p in lock["package"]}
    runtime = set()
    pending = ["deeptrace"]
    while pending:
        name = pending.pop()
        if name in runtime:
            continue
        runtime.add(name)
        pending.extend(normalized(d["name"]) for d in locked[name].get("dependencies", []))
    for dist in sorted(metadata.distributions(), key=lambda d: d.metadata["Name"].lower()):
        name = normalized(dist.metadata["Name"])
        if name == "deeptrace":
            continue
        if name not in locked or dist.version != locked[name]["version"]:
            raise RuntimeError(f"Python lock mismatch: {name}")
        license_id = dist.metadata.get("License-Expression") or dist.metadata.get("License")
        # Old metadata uses classifiers; verified against the included license files.
        if not license_id:
            license_id = {"colorama": "BSD-3-Clause", "pathspec": "MPL-2.0"}.get(name, "UNKNOWN")
        check_license(name, license_id)
        files = [Path(dist.locate_file(f)) for f in (dist.files or []) if legal_file(Path(f))]
        inventory.append({"ecosystem": "pypi", "name": name, "version": dist.version,
                          "license": license_id, "development": name not in runtime,
                          "installed": True, "source": locked[name].get("sdist", {}).get("url")})
        notices.append(section(name, dist.version, license_id, files))
    (ROOT / "docs/dependency-inventory.json").write_text(
        json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
    (ROOT / "docs/THIRD_PARTY_NOTICES.txt").write_text("\n".join(notices), encoding="utf-8")
    (ROOT / "frontend/public/THIRD_PARTY_NOTICES.txt").write_text(
        "\n".join(frontend_notices), encoding="utf-8")
    installed_count = sum(p["installed"] for p in inventory)
    print(f"License audit passed: {len(inventory)} locked artifacts; {installed_count} installed.")
    print("Only approved MPL families found; no GPL/AGPL/LGPL or unknown license identifiers.")


if __name__ == "__main__":
    main()
