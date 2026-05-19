"""Server entry point.

Re-exports the main FastAPI app so package entry points, deployment configs,
and local `python main.py` runs expose the same API surface.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app, main  # noqa: F401


if __name__ == "__main__":
    main()
