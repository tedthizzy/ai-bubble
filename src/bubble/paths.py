"""Resolve saved artifact paths after relocating the archived checkout."""

from __future__ import annotations

from pathlib import Path

_ARCHIVED_CHECKOUT_ROOT = Path("/Users/ted/Documents/dev-archive/bubble")
_CHECKOUT_ROOT = Path(__file__).resolve().parents[2]


def resolve_local_path(recorded: str | Path, *, root: Path | None = None) -> Path:
    """Keep saved provenance intact while locating files in the current checkout."""
    path = Path(recorded)
    try:
        relative = path.relative_to(_ARCHIVED_CHECKOUT_ROOT)
    except ValueError:
        return path
    if ".." in relative.parts:
        return path
    return (root.resolve() if root is not None else _CHECKOUT_ROOT) / relative
