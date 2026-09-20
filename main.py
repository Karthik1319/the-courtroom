# Entry point: runs the full Courtroom loop
# (Prosecutor -> Tavily search -> sandbox exploit -> Defense patch -> sandbox re-test -> Judge verdict)
# on a Python file passed in on the command line.

import sys


def main():
    if len(sys.argv) != 2:
        print("Usage: python main.py <path_to_python_file>")
        sys.exit(1)

    target_path = sys.argv[1]
    print(f"The Courtroom is now in session for: {target_path}")
    # TODO: wire up Prosecutor -> Defense -> Judge loop here (Phase 3)


if __name__ == "__main__":
    main()
