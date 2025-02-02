import glob
from os import path
import subprocess
import argparse


def run_golden_test(script: str, generate: bool) -> bool:
    name = path.splitext(path.basename(script))[0]
    print(f"{name}", end="")
    result = subprocess.run(
        ["python", script], capture_output=True, text=True, check=True
    )
    got = result.stdout

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

    if generate:
        print(f" ... updating expectations")
        with open(expectations_path, "w") as f:
            f.write(got)
    else:
        print(f"\nGot: ======\n{got}\n==========")
    return False


def run_golden_tests(generate: bool) -> bool:
    subjs = glob.glob("examples/*.py")
    assert subjs, "Can't find any examples/*.py"
    print("Running golden tests:")
    return all([run_golden_test(subj, generate=generate) for subj in subjs])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--generate", action="store_true")
    args = parser.parse_args()

    if not run_golden_tests(generate=args.generate):
        exit(1)
    else:
        exit(0)
