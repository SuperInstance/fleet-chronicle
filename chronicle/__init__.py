"""Chronicle — a shared reporting office for every agent in the fleet.

Each agent gets a folder in this repo. File reports, view web chronicle,
auto-summarization of old entries. Works with or without PLATO.

Usage:
    from chronicle import Chronicle, PlatoChronicle

    c = Chronicle("oracle1")
    c.check_in("GL(9) fix deployed")

    pc = PlatoChronicle("https://localhost:8847", "oracle1-checkin")
    pc.report("AutoResearch completed")
"""

from .core import Chronicle
from .plato import PlatoChronicle

__version__ = "0.1.0"
