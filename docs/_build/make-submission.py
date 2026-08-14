"""Assemble the SAKAI submission ZIP.

Structure is fixed by Part C of the examination paper: five named PDFs, the links
file, and a Supporting_Files folder. The three documents that are not named there
(effort estimation, API contract, QA report) go into Supporting_Files rather than
being dropped, because the required documents cite all three.

Run from the repo root, after build.py and make-pdfs.js:
    python3 docs/_build/make-submission.py
"""

import shutil
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PDF = REPO / "docs" / "pdf"
BUNDLE = "22424140_SDJ_Editorial_Portal"
STAGE = REPO / "submission" / BUNDLE

REQUIRED = {
    "01-project-documentation.pdf": "Project_Documentation.pdf",
    "02-srs.pdf": "SRS.pdf",
    "06-testing-report.pdf": "Testing_Report.pdf",
    "04-technical-debt-register.pdf": "Technical_Debt_Plan.pdf",
    "07-user-manual.pdf": "User_Manual.pdf",
}

SUPPORTING = {
    "03-effort-estimation.pdf": "Effort_Estimation.pdf",
    "05-api-contract.pdf": "API_Contract.pdf",
    "08-qa-report.pdf": "QA_Report.pdf",
}


def main() -> None:
    if STAGE.parent.exists():
        shutil.rmtree(STAGE.parent)
    (STAGE / "Supporting_Files").mkdir(parents=True)

    for src, dst in REQUIRED.items():
        shutil.copy2(PDF / src, STAGE / dst)
    for src, dst in SUPPORTING.items():
        shutil.copy2(PDF / src, STAGE / "Supporting_Files" / dst)
    shutil.copy2(REPO / "Deployment_and_Source_Links.txt", STAGE)

    archive = REPO / "submission" / f"{BUNDLE}.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(STAGE.rglob("*")):
            if path.is_file():
                z.write(path, path.relative_to(STAGE.parent))

    print(f"{archive.name}  {archive.stat().st_size / 1024 / 1024:.1f} MB\n")
    for path in sorted(STAGE.rglob("*")):
        if path.is_file():
            size = path.stat().st_size / 1024
            print(f"  {path.relative_to(STAGE.parent)}  ({size:.0f} KB)")


if __name__ == "__main__":
    main()
