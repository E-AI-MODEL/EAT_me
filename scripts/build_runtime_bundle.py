import sys
from pathlib import Path as _Path
sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
import shutil
from pathlib import Path
import zipfile

from eatme.parser import dump_eat

RUBRICS = [
    "P_Procesfase",
    "TD_Taakdichtheid",
    "C_CoRegulatie",
    "V_Vaardigheidspotentieel",
    "T_TechnologischeIntegratieVisibility",
    "S_SocialeInteractie",
    "L_LeercontinuiteitTransfer",
    "E_EpistemischeBetrouwbaarheid",
    "B_BiasCorrectieFairness",
]


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    rubrics_dir = root / "rubrics"
    rubrics_dir.mkdir(exist_ok=True)

    for rid in RUBRICS:
        src = root / f"{rid}.eat"
        dst = rubrics_dir / f"{rid}.eat"
        shutil.copy2(src, dst)

    index = {
        "meta": {"version": 2.0, "mode": "runtime", "locked": True},
        "index": {"order": RUBRICS, "files": [f"{r}.eat" for r in RUBRICS]},
    }
    dump_eat(index, rubrics_dir / "index.eat")

    dist = root / "dist"
    dist.mkdir(exist_ok=True)
    zip_path = dist / "EAT_v2_runtime_ready_FULL.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file in sorted(rubrics_dir.glob("*.eat")):
            zf.write(file, f"rubrics/{file.name}")

    print(zip_path)


if __name__ == "__main__":
    main()
