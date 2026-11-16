"""Inspect distribution contents and execute installed offline cases in clean envs."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import venv
import zipfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    directory = args.directory.resolve()
    files = [next(directory.glob("*.whl")), next(directory.glob("*.tar.gz"))]
    for package in files:
        if package.suffix == ".whl":
            with zipfile.ZipFile(package) as archive:
                names = archive.namelist()
        else:
            with tarfile.open(package) as archive:
                names = archive.getnames()
        for suffix in ("skillbundle/resources/DejaVu-LICENSE.txt", "skillbundle/resources/THIRD_PARTY_NOTICES.txt", "skillbundle/resources/public_context.json", "skillbundle/resources/capital.html", "skillbundle/resources/investment_demo.json"):
            assert any(n.endswith(suffix) for n in names), (package, suffix)
        assert not any("output-unicode-test" in n or n.startswith("output/") or "/output/" in n for n in names)
        with tempfile.TemporaryDirectory(prefix="career-fit-clean-") as folder:
            root = Path(folder)
            venv.EnvBuilder(with_pip=True).create(root / "env")
            scripts = root / "env" / ("Scripts" if sys.platform == "win32" else "bin")
            python = scripts / ("python.exe" if sys.platform == "win32" else "python")
            subprocess.run([str(python), "-m", "pip", "install", "--quiet", str(package)], check=True, cwd=root)
            def run(*argv):
                return subprocess.check_output([str(python), "-m", "career_fit.cli", *argv], cwd=root, text=True, encoding="utf-8")
            investment = json.loads(run("invest"))
            workforce = json.loads(run("workforce"))
            assert investment["best_plan"]["cash_cost"] == 320
            assert workforce["scenarios"]["hybrid"]["economic_cost"] == 3016
            assert len(json.loads(run("market", "--occupation-id", "15-2031"))["skills"]) == 35
            for command in ("career-fit", "skillbundle"):
                executable = scripts / (command + (".exe" if sys.platform == "win32" else ""))
                subprocess.run([str(executable), "taxonomy"], cwd=root, stdout=subprocess.DEVNULL, check=True)
            check = "from importlib.metadata import version; import career_fit, skillbundle; from skillbundle.resources import read_resource_text; from skillbundle.reports import build_pdf_plan; assert version('career-fit') == career_fit.__version__ == skillbundle.__version__ == '0.7.0'; assert 'Bitstream' in read_resource_text('DejaVu-LICENSE.txt'); assert build_pdf_plan({}).startswith(b'%PDF')"
            subprocess.run([str(python), "-c", check], cwd=root, check=True)
        print("PASS clean installation and offline runtime:", package.name)


if __name__ == "__main__":
    main()
