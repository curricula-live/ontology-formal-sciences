"""Fetch the checksum-pinned document from a source checkout."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from pipeline.common import registry
from pipeline.fetch import fetch

if __name__ == "__main__":
    print(fetch(registry()[Path(__file__).parent.name], "--offline" in sys.argv))
