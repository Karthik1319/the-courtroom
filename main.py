# Entry point: runs the full Courtroom loop
# (Prosecutor -> Tavily search -> sandbox exploit -> Defense patch -> sandbox re-test -> Judge verdict)
# on a Python file passed in on the command line.

import sys

from agents import defense, judge, prosecutor


def _print_header(title: str) -> None:
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)


def main():
    if len(sys.argv) != 2:
        print("Usage: python main.py <path_to_python_file>")
        sys.exit(1)

    target_path = sys.argv[1]
    try:
        with open(target_path) as f:
            source_code = f.read()
    except OSError as e:
        print(f"Could not read {target_path}: {e}")
        sys.exit(1)

    print(f"The Courtroom is now in session for: {target_path}")

    _print_header("PROSECUTOR")
    prosecutor_analysis = prosecutor.analyze(source_code)
    print(prosecutor_analysis)

    _print_header("DEFENSE")
    defense_result = defense.patch(source_code, prosecutor_analysis)
    print("Patched code:")
    print(defense_result["patched_code"])
    print()
    print("Explanation:", defense_result["explanation"])
    print()
    print("Sandbox result of re-running the attack:", defense_result["sandbox_result"])

    _print_header("JUDGE'S VERDICT")
    verdict = judge.render_verdict(source_code, prosecutor_analysis, defense_result)
    print(verdict)


if __name__ == "__main__":
    main()
