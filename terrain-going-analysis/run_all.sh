#!/usr/bin/env bash
# Rebuild every deliverable from configuration: pipeline -> QGIS models -> QGIS project/layouts -> briefing.
set -euo pipefail
cd "$(dirname "$0")"
export QT_QPA_PLATFORM=offscreen

python3 run_pipeline.py "$@"
if python3 -c "import qgis.core" 2>/dev/null; then
  PYTHONNOUSERSITE=1 python3 qgis/build_models.py
  PYTHONNOUSERSITE=1 python3 qgis/run_models.py
  PYTHONNOUSERSITE=1 python3 qgis/build_project.py
else
  echo "PyQGIS not found - skipping QGIS model run and project build (run from the OSGeo4W/QGIS Python)."
fi
python3 presentation/build_briefing.py
