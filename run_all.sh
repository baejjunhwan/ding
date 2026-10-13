#!/usr/bin/env bash
# Reproduce every number and figure in the paper (v3). Run from the repository root.
set -euo pipefail
cd "$(dirname "$0")"
python3 analysis/01_build_grid_master.py
python3 analysis/02_grid_models.py
python3 analysis/03_build_oa_master.py
python3 analysis/04_oa_models_and_tracks.py
python3 analysis/05_figures.py
