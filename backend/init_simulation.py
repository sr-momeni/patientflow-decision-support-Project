"""Initialize the validated research model without overwriting application models.

The former hourly/default-state feature builder has been retired. Training now
uses the same causal simulator state as inference and an independent validation
split. The application model is not automatically replaced by research output.
"""
from pathlib import Path
import subprocess
import sys


def initialize_simulation():
    root=Path(__file__).resolve().parents[1]
    subprocess.run([sys.executable,'-m','backend.optimization.validate_simulation',
                    '--phase','develop'],cwd=root,check=True)


if __name__=='__main__':
    initialize_simulation()
