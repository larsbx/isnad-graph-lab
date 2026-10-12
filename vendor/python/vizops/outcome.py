"""What a render run reports. Three inhabitants, and the third has a name.

A render either produced a file, was refused, or reached no verdict at all.
The third case is not a failure and not a pass: a machine with no OpenGL
context, or no `manimgl` on its PATH, has not shown that a scene is broken and
has not shown that it works. Coercing it to either would be a verdict the run
did not reach, so it carries its own name and its own exit code.

The set is closed. A fourth outcome would have to be declared here, beside the
exit codes, rather than invented at a call site -- so subclassing from outside
this module is refused rather than merely discouraged.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

DIGEST = re.compile(r"^[0-9a-f]{64}$")

#: A verdict per exit code, and no two verdicts share one. `refused` is the
#: failure direction: vizops declined to draw, or the renderer died. 2 is the
#: absence of a verdict, which CI must be able to tell apart from both.
EXIT_CODES = {"rendered": 0, "refused": 1, "inconclusive": 2}

#: When each verdict is reached. This is the source the README and the wiki
#: both render their outcome table from, so the three explanations cannot
#: drift apart into three different stories.
MEANING = {
    "rendered": "A file exists, and the outcome carries its digest.",
    "refused": (
        "The source is missing, empty, of an unknown format, or describes a figure the type "
        "refuses -- or the renderer died. Nothing was drawn, on purpose."
    ),
    "inconclusive": (
        "No verdict was reached: no `manimgl` on PATH (or, for a page, no `pixi`), no GL "
        "context, a timeout, or a clean exit that wrote no file."
    ),
}


class Outcome:
    """Sealed base: `Rendered`, `Refused`, `Inconclusive`, and nothing else."""

    __slots__ = ()

    def __init_subclass__(cls, **kwargs: object) -> None:
        if cls.__module__ != __name__:
            raise TypeError(
                f"{cls.__name__}: the outcome set is closed. A fourth outcome belongs in "
                f"{__name__} beside EXIT_CODES, where CI can be taught what it means."
            )
        super().__init_subclass__(**kwargs)

    @property
    def verdict(self) -> str:
        return type(self).__name__.lower()

    @property
    def exit_code(self) -> int:
        return EXIT_CODES[self.verdict]


def _reason(scene: str, reason: str) -> None:
    if not scene:
        raise ValueError("an outcome names the scene it is about")
    if not reason.strip():
        raise ValueError(f"{scene}: an outcome that is not a render must say why")


@dataclass(frozen=True, slots=True)
class Rendered(Outcome):
    """A file exists, and its digest says which bytes were produced."""

    scene: str
    output: str
    digest: str

    def __post_init__(self) -> None:
        if not self.scene or not self.output:
            raise ValueError("a render names its scene and its output")
        if not DIGEST.fullmatch(self.digest):
            raise ValueError(f"{self.scene}: {self.digest!r} is not a sha256 hex digest")

    def __str__(self) -> str:
        return f"rendered  {self.scene}: {self.output} (sha256:{self.digest[:12]})"


@dataclass(frozen=True, slots=True)
class Refused(Outcome):
    """vizops declined to draw, or the renderer failed. Either way, a verdict."""

    scene: str
    reason: str

    def __post_init__(self) -> None:
        _reason(self.scene, self.reason)

    def __str__(self) -> str:
        return f"refused   {self.scene}: {self.reason}"


@dataclass(frozen=True, slots=True)
class Inconclusive(Outcome):
    """No verdict was reached, and the reason names what was missing."""

    scene: str
    reason: str

    def __post_init__(self) -> None:
        _reason(self.scene, self.reason)

    def __str__(self) -> str:
        return f"inconclusive {self.scene}: {self.reason}"


def worst(outcomes: tuple[Outcome, ...]) -> int:
    """The exit code of a run of scenes: the loudest outcome wins, and a run
    with nothing in it is inconclusive rather than clean."""
    return max((o.exit_code for o in outcomes), default=EXIT_CODES["inconclusive"])
