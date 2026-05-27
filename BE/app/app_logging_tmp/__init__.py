import sys as _sys
import importlib as _importlib

# Temporarily remove this package so we can load the real stdlib logging
_this_name = __name__  # "app.logging"
_sys.modules.pop(_this_name, None)

# Load the real stdlib logging under a private name
_real_logging = _importlib.import_module("logging")

# Re-register this package as the real logging so any code doing
# `from app.logging.audit_logger import ...` still works,
# while `import logging` in stdlib code gets the real module.
_sys.modules[_this_name] = _real_logging
