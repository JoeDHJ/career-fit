"""Packaged read-only resources used by installed Career Fit distributions."""

from __future__ import annotations

from importlib.resources import files


def read_resource_text(name: str) -> str:
    """Read a bundled JSON resource without depending on a source checkout."""

    return files(__package__).joinpath(name).read_text(encoding="utf-8")
