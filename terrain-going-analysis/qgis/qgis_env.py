"""Headless PyQGIS bootstrap shared by the build/run scripts in this folder.

Works with the Python that ships with QGIS (OSGeo4W shell on Windows, `python3` with
python3-qgis on Linux, the QGIS.app bundled python on macOS).
"""
import os
import shutil
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from qgis.core import QgsApplication  # noqa: E402

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent

_app = None


def start():
    global _app
    if _app is not None:
        return _app
    QgsApplication.setPrefixPath(os.environ.get("QGIS_PREFIX_PATH", "/usr"), True)
    _app = QgsApplication([], False)
    _app.initQgis()
    plugins = Path(QgsApplication.pkgDataPath()) / "python" / "plugins"
    sys.path.append(str(plugins))
    install_scripts()
    from processing.core.Processing import Processing
    Processing.initialize()
    reg = QgsApplication.processingRegistry()
    if reg.providerById("grass7") is None and reg.providerById("grass") is None:
        try:  # module name differs between QGIS releases
            try:
                from grassprovider.grass_provider import GrassProvider as Provider
            except ImportError:
                from grassprovider.Grass7AlgorithmProvider import Grass7AlgorithmProvider as Provider
            reg.addProvider(Provider())
        except Exception as exc:  # GRASS is only needed for smoothing, TWI and routing
            print("WARNING: GRASS provider not available:", exc)
    return _app


def profile_dir() -> Path:
    return Path(QgsApplication.qgisSettingsDirPath())


def install_scripts():
    """Copy the GOING processing scripts and models into the active QGIS profile."""
    scripts = profile_dir() / "processing" / "scripts"
    models = profile_dir() / "processing" / "models"
    scripts.mkdir(parents=True, exist_ok=True)
    models.mkdir(parents=True, exist_ok=True)
    for f in (HERE / "scripts").glob("*.py"):
        shutil.copy2(f, scripts / f.name)
    for f in (HERE / "models").glob("*.model3"):
        shutil.copy2(f, models / f.name)
    return scripts, models


def grass_id(alg: str) -> str:
    reg = QgsApplication.processingRegistry()
    for prefix in ("grass7", "grass"):
        if reg.algorithmById(f"{prefix}:{alg}") is not None:
            return f"{prefix}:{alg}"
    return f"grass7:{alg}"
