import importlib.util
import sys
from pathlib import Path

_kolibri_dist_spec = importlib.util.find_spec("kolibri.dist")

if _kolibri_dist_spec and _kolibri_dist_spec.has_location:
    kolibri_dist_path = Path(_kolibri_dist_spec.origin).parent
    sys.path.append(kolibri_dist_path.as_posix())
