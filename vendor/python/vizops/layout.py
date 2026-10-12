"""Where the nodes go. Pure, deterministic, and testable without a renderer.

One column per class the source declares, in declared order; members centred
within their column, in figure order. The layout *is* the class encoding --
see `palette` on why colour is not allowed to be it.

Coordinates are manim scene units: x to the right, y up, origin centred.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

Point = tuple[float, float]


@dataclass(frozen=True, slots=True)
class Frame:
    """The box the figure is laid out in, inside the title and the stamp."""

    width: float = 10.4
    height: float = 4.8

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("a frame with no area lays nothing out")


def _spread(count: int, extent: float) -> tuple[float, ...]:
    """`count` positions centred on 0 and spanning at most `extent`, ascending."""
    if count == 1:
        return (0.0,)
    step = extent / (count - 1)
    return tuple(-extent / 2 + i * step for i in range(count))


def columns(order: Sequence[str], members: Mapping[str, Sequence[str]], frame: Frame = Frame()) -> Mapping[str, Point]:
    """Node id -> point, one column per entry of `order`.

    Columns run left to right in declared order, members top to bottom in
    figure order.

    `order` is the source's declared class order; `members` maps each class to
    its node ids. A class in `order` with no members is refused rather than
    silently given an empty column: the caller decides what is on the frame,
    and `Figure.populated()` is how it says so.
    """
    missing = [c for c in order if not members.get(c)]
    if missing:
        raise ValueError(f"layout refused: no members for {', '.join(missing)}")
    xs = _spread(len(order), frame.width)
    return {
        node: (x, y)
        for x, cls in zip(xs, order)
        for y, node in zip(reversed(_spread(len(members[cls]), frame.height)), members[cls])
    }


def pitch(members: Mapping[str, Sequence[str]], frame: Frame = Frame()) -> float:
    """The smallest vertical gap between two nodes in any column.

    A scene sizes its boxes from this rather than from a constant, so a column
    with twelve members packs instead of overlapping. Overlapping labels are
    not a cosmetic problem here: an unreadable node is a node the frame claims
    to show and does not.
    """
    counts = [len(ids) for ids in members.values()]
    return min((frame.height / (c - 1) for c in counts if c > 1), default=frame.height)


def column_spacing(count: int, frame: Frame = Frame()) -> float:
    """Distance between two neighbouring columns; the whole width when there
    is only one, since a lone column is not crowded by anything."""
    return frame.width / (count - 1) if count > 1 else frame.width
