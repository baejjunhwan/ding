#!/usr/bin/env bash
# 논문 수치와 그림을 다시 만듭니다. 저장소 최상위에서 실행합니다.
set -euo pipefail
cd "$(dirname "$0")"

# 1. 격자 모형, 집계구 모형, Track 1, 그림
#    (04·05의 집계구판 Track 2와 두 트랙 중첩은 1차 투고본 전용 결과입니다)
python3 analysis/01_build_grid_master.py
python3 analysis/02_grid_models.py
python3 analysis/03_build_oa_master.py
python3 analysis/04_oa_models_and_tracks.py
python3 analysis/05_figures.py

# 2. 수정본 3.2절: ΔNDBI 부호 차이 점검(상위 10% 비교, 스케일 분해)
python3 analysis/06_ndbi_scale_check.py

# 3. 수정본 Track 2 격자판(100 m 격자, 건물 지붕 면적, 재건축·신개발 격자 분리)
python3 track2_grid/00_build_grid_table.py
python3 track2_grid/01_scores_and_robustness.py
python3 track2_grid/02_export_table.py
python3 track2_grid/03_component_checks.py
python3 track2_grid/04_map_figure.py

# 수정본 그림: Fig. 1 흐름도, Fig. 3 Track 1(평가 미실시 67개 표시), Fig. 4 Track 2 격자(영문)
python3 analysis/07_revision_figures.py

# 4. 수정본 Track 1 강건성: 거주지 기준 노출
python3 track1_residential/01_join.py
python3 track1_residential/02_compare.py
