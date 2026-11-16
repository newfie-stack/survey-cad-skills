"""Publish prepared review artifacts exclusively, rolling back owned outputs."""
from __future__ import annotations

import os
from pathlib import Path
import tempfile


def _remove_owned(path: Path, identity: tuple[int, int]) -> None:
    try:
        current = path.lstat()
    except FileNotFoundError:
        return
    if (current.st_dev, current.st_ino) == identity:
        path.unlink()


def publish_artifacts(artifacts: dict[Path, bytes]) -> None:
    """Stage complete byte payloads and link them into fresh destination names.

    Each final file is created without replacement. An ordinary publication
    failure removes only this call's outputs, preserving competing writers.
    Staging and destination files share a directory/filesystem. This is not a
    crash-recovery transaction across independent filesystems.
    """
    if not isinstance(artifacts, dict) or not artifacts:
        raise ValueError('At least one prepared artifact is required')
    selected = []
    seen = set()
    for name, payload in artifacts.items():
        if not isinstance(payload, bytes):
            raise TypeError('Prepared artifact contents must be bytes')
        path = Path(name)
        if path.exists() or path.is_symlink():
            raise FileExistsError('Review output already exists')
        destination = path.resolve()
        if destination in seen:
            raise ValueError('Review output paths must be distinct')
        seen.add(destination)
        if not destination.parent.is_dir():
            raise ValueError('Review output parent directory must already exist')
        selected.append((destination, payload))

    staged = []
    published = []
    try:
        for destination, payload in selected:
            fd, name = tempfile.mkstemp(prefix='.cpa-review-', suffix='.tmp',
                                        dir=destination.parent)
            stage = Path(name)
            stat = os.fstat(fd)
            identity = (stat.st_dev, stat.st_ino)
            staged.append((stage, destination, identity))
            with os.fdopen(fd, 'wb') as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
        for stage, destination, identity in staged:
            os.link(stage, destination, follow_symlinks=False)
            published.append((destination, identity))
    except BaseException:
        for destination, identity in reversed(published):
            _remove_owned(destination, identity)
        raise
    finally:
        for stage, _, identity in staged:
            _remove_owned(stage, identity)
