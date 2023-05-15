"""
Additional project specific units
"""
from scmdata.units import UNIT_REGISTRY  # type: ignore

if not hasattr(UNIT_REGISTRY, "hydrogen"):
    UNIT_REGISTRY.define("H = [hydrogen] = H2")
    UNIT_REGISTRY.define("hydrogen = H")
    UNIT_REGISTRY.define("t{symbol} = t * {symbol}".format(symbol="H"))

    UNIT_REGISTRY.define("4/16 * H = CH4")
    UNIT_REGISTRY.define(f"{14 + 2 * 16}H = NOx")
    UNIT_REGISTRY.define("3/17 H = NH3")

__all__ = ["UNIT_REGISTRY"]
