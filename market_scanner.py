#!/usr/bin/env python3
"""Sim Companies AI Agent Entrypoint (sim-company-agent)"""

import sys, os

# Resolve the project root (the sibling directory containing the `agent` package)
# This works even if the script is invoked from a different cwd.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'GAMES', 'sim-companies'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from agent.cli import main

if __name__ == "__main__":
    main()
