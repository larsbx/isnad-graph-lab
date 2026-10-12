"""Colour, assigned in a fixed order and carrying no meaning on its own.

The hues are the eight categorical slots of the reference palette, stepped for
a dark surface, validated as a set with the palette validator against the
`#1a1a19` surface these scenes use: lightness band, chroma floor, CVD
separation (worst adjacent pair ΔE 8.4 protan), normal-vision floor (19.3) and
contrast all pass for the seven slots the estate's artifacts currently need.

A node graph puts every pair of colours on screen at once, which is a harder
case than an adjacent pairlist, so colour here is deliberately the *third*
encoding and never the carrier: each class gets its own column, every node is
directly labelled, and the legend prints the source's own word for the class.
Removing all colour would cost nothing but speed of reading -- which is the
test of whether colour is being asked to mean something it should not.

Assignment is by declared position, so a class keeps its hue when another class
loses its last member. Colour follows the entity, never its rank.
"""

from __future__ import annotations

from typing import Mapping, Sequence

SURFACE = "#1a1a19"
INK = "#f4f3f0"
MUTED = "#8f8d87"
RULE = "#4d4c47"

#: Fixed order, never cycled. A ninth class is not a generated hue.
RING: tuple[str, ...] = (
    "#3987e5",  # blue
    "#d95926",  # orange
    "#199e70",  # aqua
    "#c98500",  # yellow
    "#d55181",  # magenta
    "#008300",  # green
    "#9085e9",  # violet
    "#e66767",  # red
)


class PaletteError(ValueError):
    """More classes than the palette has hues."""


def assign(terms: Sequence[str]) -> Mapping[str, str]:
    """Term id -> hue, by declared position."""
    if len(terms) > len(RING):
        raise PaletteError(
            f"{len(terms)} classes and {len(RING)} hues: a ninth hue is not generated. "
            "Fold the tail into one class at the source, or facet the figure."
        )
    if len(set(terms)) != len(terms):
        raise PaletteError("the same class twice; colour follows the entity")
    return {term: RING[i] for i, term in enumerate(terms)}


#: Line styles for edge kinds, in the order the source declares them. Two
#: styles only: a third dashed pattern is not distinguishable at this stroke
#: width, so a figure with more kinds than this says so in its key rather than
#: drawing a distinction a reader cannot make.
STYLES = ("solid", "dashed")


def edge_styles(kinds: Sequence[str]) -> Mapping[str, str]:
    """Edge kind -> line style, by declared position; the tail shares the last
    style and the key is what tells a reader so.

    Pass the kinds a figure *uses* (`Figure.used_kinds()`), not every kind its
    source declares: a vocabulary of nine would push both kinds on the frame
    into the shared style and distinguish nothing.
    """
    return {kind: STYLES[min(i, len(STYLES) - 1)] for i, kind in enumerate(kinds)}


def edge_key(kinds: Sequence[str]) -> str:
    """The one line a frame prints so its edges are not read by guess."""
    styles = edge_styles(kinds)
    shared = [k for k in kinds if styles[k] == STYLES[-1]]
    key = " · ".join(f"{styles[k]}: {k}" for k in kinds[: len(STYLES) - 1])
    return f"{key} · {STYLES[-1]}: {', '.join(shared)}" if shared else key
