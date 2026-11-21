"""Progress of a long host command, for the Mesh Editor to show while it waits.

The editor only hears from the host when a command ends. A command that bakes
textures can take minutes, so it writes its current step to
``host-progress.json`` in the session folder; the editor reads that file while
the request is pending. The file is removed when the command ends.
"""

from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
import threading
import time

from cdmw.core.atomic_file import atomic_write_text

HOST_PROGRESS_FILE = "host-progress.json"
# The bake's own messages, in order; each material passes all of them.
BAKE_STAGES = (
    "Reading source textures...",
    "Decoding source textures...",
    "Combining material layers...",
    "Compressing colour texture...",
    "Compressing normal map...",
    "Compressing surface map...",
)
_ALIASES = {"Checking prepared textures...": 0, "Reusing prepared textures.": len(BAKE_STAGES)}
_local = threading.local()


@contextmanager
def host_progress(root: Path | str | None):
    """Let this thread's bakes report into ``root``; clear it when done."""

    path = Path(root) / HOST_PROGRESS_FILE if root else None
    previous = getattr(_local, "path", None)
    _local.path = path
    try:
        yield
    finally:
        _local.path = previous
        if path is not None:
            try:
                path.unlink()
            except OSError:
                pass


def report_bake_progress(index: int, total: int, detail: str) -> None:
    """Record one bake message; ``detail`` ends with one of ``BAKE_STAGES``."""

    path = getattr(_local, "path", None)
    if path is None:
        return
    stage = next((number for number, text in enumerate(BAKE_STAGES) if detail.endswith(text)),
                 next((number for text, number in _ALIASES.items() if detail.endswith(text)), None))
    if stage is None:
        return
    total = max(int(total), 1)
    fraction = min((int(index) * len(BAKE_STAGES) + stage) / (total * len(BAKE_STAGES)), 1.0)
    payload = {"kind": "bake", "material": int(index) + 1, "materials": total,
               "stage": min(stage, len(BAKE_STAGES) - 1), "fraction": fraction, "time": time.time()}
    try:
        atomic_write_text(path, json.dumps(payload))
    except OSError:
        pass  # Progress is a courtesy; the bake goes on.
