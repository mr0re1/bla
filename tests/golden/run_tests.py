import glob
from os import path
import subprocess
import argparse


def run_golden_test(script: str, update: bool) -> bool:
    name = path.splitext(path.basename(script))[0]
    print(f"{name}", end="")
    result = subprocess.run(
        ["python", script], capture_output=True, text=True, check=False
    )
    got = result.stdout + result.stderr
    if result.returncode:
        print(f" - FAILED with error:\n{got}")
        exit(1)

    expectations_path = f"tests/golden/expectations/{name}.out"
    try:
        with open(expectations_path) as f:
            expectations = f.read()
    except FileNotFoundError:
        print(f" - FAIL: {expectations_path} is not found", end="")
    else:
        if expectations == got:
            print(" - PASS")
            return True
        else:
            print(" - FAIL: mismatch", end="")

    if update:
        print(f" ... updating")
        with open(expectations_path, "w") as f:
            f.write(got)
    else:
        print(f"\nGot: ======\n{got}\n==========")
    return False


def run_golden_tests(update: bool) -> bool:
    subjs = glob.glob("examples/*.py")
    assert subjs, "Can't find any examples/*.py"
    print("Running golden tests:")
    return all([run_golden_test(subj, update=update) for subj in subjs])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--update", action="store_true", help="Update expectations")
    args = parser.parse_args()

    if not run_golden_tests(update=args.update):
        exit(1)
    else:
        exit(0)
