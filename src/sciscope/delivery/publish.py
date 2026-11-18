"""Private same-filesystem staging and rollback for the two delivery outputs."""

from __future__ import annotations

import os
import shutil
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


def _cleanup(path: Path) -> None:
    """Remove only a caller-owned temporary or installed path, best effort."""
    try:
        if path.is_symlink():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink(missing_ok=True)
    except Exception:
        # Cleanup must never replace the original sanitized failure.
        pass


@contextmanager
def _staging(parent: Path) -> Iterator[Path]:
    """Create a sibling stage and clean exactly that invocation's directory."""
    parent.mkdir(parents=True, exist_ok=True)
    staged = Path(
        tempfile.mkdtemp(prefix=".sciscope-delivery-stage-", dir=parent)
    )
    try:
        yield staged
    finally:
        _cleanup(staged)


def _backup_name(parent: Path) -> Path:
    """Allocate a unique absent backup name without scanning old siblings."""
    reserved = Path(
        tempfile.mkdtemp(prefix=".sciscope-delivery-backup-", dir=parent)
    )
    try:
        reserved.rmdir()
    except Exception:
        _cleanup(reserved)
        raise
    return reserved


def _stage_copy(parent: Path, content: bytes) -> Path:
    """Stage the committed file with its handle closed before publication."""
    parent.mkdir(parents=True, exist_ok=True)
    staged: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=".sciscope-delivery-stage-",
            dir=parent,
            delete=False,
        ) as stream:
            staged = Path(stream.name)
            stream.write(content)
        return staged
    except Exception:
        if staged is not None:
            _cleanup(staged)
        raise


def _publish(
    staged: Path, content: bytes, output: Path, committed: Path
) -> None:
    """Publish four forward moves, retaining both predecessors until success.

    On caught failure restore both artifacts independently. A persistent OS
    denial may prevent restoration; preserve a surviving backup in that case.
    Only paths allocated or installed by this invocation are cleaned.
    """
    copy_stage = _stage_copy(committed.parent, content)
    backups: dict[Path, Path] = {}
    installed: set[Path] = set()
    retained: set[Path] = set()
    try:
        for target, source in ((output, staged), (committed, copy_stage)):
            if target.exists():
                backup = _backup_name(target.parent)
                os.replace(target, backup)
                backups[target] = backup
            os.replace(source, target)
            installed.add(target)
    except Exception:
        for target in (committed, output):
            if target in installed:
                _cleanup(target)
            if target in backups:
                try:
                    os.replace(backups[target], target)
                except Exception:
                    retained.add(backups[target])
        raise
    finally:
        _cleanup(copy_stage)
        for backup in backups.values():
            if backup not in retained:
                _cleanup(backup)
