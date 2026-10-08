"""Keep failed observations visible on Pages, but fail Actions after publishing."""
import json
from pathlib import Path
import sys

def main():
    receipt = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    passed = receipt["overall"] == "ok"
    print("Result:", "PASS" if passed else "FAIL; see the public dashboard")
    return 0 if passed else 1

if __name__ == "__main__":
    sys.exit(main())
