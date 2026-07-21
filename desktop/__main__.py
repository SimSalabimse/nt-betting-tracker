import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
import nt_bootstrap  # noqa: F401

from desktop.app import main

if __name__ == "__main__":
    main()
