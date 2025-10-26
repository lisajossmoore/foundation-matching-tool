import subprocess
from pathlib import Path
import pandas as pd

def test_unweighted_and_weighted_runs():
    data_dir = Path("data")
    out_dir = Path("outputs")
    out_dir.mkdir(exist_ok=True)

    foundations = data_dir / "test_foundations.xlsx"
    faculty = data_dir / "test_faculty.xlsx"
    out_unweighted = out_dir / "test_smoke_unweighted.xlsx"
    out_weighted = out_dir / "test_smoke_weighted.xlsx"

    # Run unweighted
    cmd_unweighted = [
        "python", "main.py",
        "--foundations", str(foundations),
        "--faculty", str(faculty),
        "--out", str(out_unweighted),
        "--score-threshold", "0"
    ]
    subprocess.run(cmd_unweighted, check=True)

    # Run weighted
    cmd_weighted = [
        "python", "main.py",
        "--foundations", str(foundations),
        "--faculty", str(faculty),
        "--out", str(out_weighted),
        "--score-threshold", "0",
        "--use-weights"
    ]
    subprocess.run(cmd_weighted, check=True)

    # Confirm both files exist and are readable
    for path in [out_unweighted, out_weighted]:
        assert path.exists(), f"{path} not found"
        df = pd.read_excel(path)
        assert not df.empty, f"{path} is empty"
        print(f"✅ {path} has {df.shape[0]} rows and {df.shape[1]} columns")

if __name__ == "__main__":
    test_unweighted_and_weighted_runs()
