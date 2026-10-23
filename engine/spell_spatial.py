"""Explicitly spatial-only XPHB translations; no invented arena benefits.

These declarations load and spend their real casting economy. Their omitted
mechanics require a map, objects, illumination or movement, not a new combat
condition that silently stands in for those mechanics.
"""
from .spell_catalog import base, sources


OMISSIONS = {
    "Dimension Door": "Teleportation, willing companion eligibility and Force damage only on an occupied arrival require destination geometry; mishap damage is not front-loaded.",
    "Passwall": "A temporary passage through an eligible surface, structural support and ejection on expiry require object geometry.",
    "Tree Stride": "Tree entry/exit, eligible trunks and once-per-turn distance-limited tree teleportation require positions and terrain.",
    "Wall of Force": "Wall shape, physical/ethereal blocking, displacement and Disintegrate interaction require barrier geometry; no blanket combat removal or damage immunity is invented.",
    "Wall of Stone": "Stone panels, support/collapse, enclosure-triggered Dexterity saves and reaction escape require objects, geometry and movement; full-duration permanence is environmental.",
}


def translations(level):
    raw = sources()
    result = []
    for name, reason in OMISSIONS.items():
        if raw[name]["level"] != level:
            continue
        spec = base(raw[name])
        spec["unsupported"] = [reason]
        result.append(spec)
    return result
