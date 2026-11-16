"""Workarounds for Python 3.15 lazy imports (PEP 810).

On Python 3.15 the standard library declares ``lazy from .thread import
ThreadPoolExecutor`` inside ``concurrent.futures``. On some 3.15 builds the
attribute can be handed back as an unresolved ``lazy_import`` placeholder, and
MediaPipe's ``concurrent.futures.ThreadPoolExecutor(max_workers=1)`` then fails
with ``TypeError: 'lazy_import' object is not callable``.

Importing the real classes from their submodules (a normal, eager import) and
writing them back onto ``concurrent.futures`` replaces any placeholder.
Harmless on Python 3.12 - 3.14.
"""
import concurrent.futures as _futures


def _is_lazy(obj):
    return type(obj).__name__ == "lazy_import"


def apply():
    from concurrent.futures.thread import ThreadPoolExecutor
    _futures.ThreadPoolExecutor = ThreadPoolExecutor
    try:
        from concurrent.futures.process import ProcessPoolExecutor
        _futures.ProcessPoolExecutor = ProcessPoolExecutor
    except Exception:
        pass  # process pools are not needed by AirControl

    leftovers = [name for name, value in vars(_futures).items() if _is_lazy(value)]
    for name in leftovers:
        try:
            delattr(_futures, name)  # let normal attribute lookup re-resolve it
        except Exception:
            pass


apply()
