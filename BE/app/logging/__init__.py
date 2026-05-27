import sys as _sys
import sysconfig as _sysconfig
import importlib.util as _util
import os as _os

# Find the real stdlib logging by locating it in the stdlib path
_stdlib = _sysconfig.get_path("stdlib")
_logging_init = _os.path.join(_stdlib, "logging", "__init__.py")

_spec = _util.spec_from_file_location("logging", _logging_init)
_real = _util.module_from_spec(_spec)
_sys.modules["logging"] = _real
_spec.loader.exec_module(_real)

# Make this package behave like the real logging module
from logging import *  # noqa: F401, F403
