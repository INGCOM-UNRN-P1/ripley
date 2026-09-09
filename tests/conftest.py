import sys
from pathlib import Path

# Agregar dev/tools/*/src a sys.path para resolución de plugins satélites en memoria
tools_root = Path(__file__).resolve().parent.parent.parent
for p in tools_root.glob("*/src"):
    if p.is_dir() and str(p) not in sys.path:
        sys.path.insert(0, str(p))
