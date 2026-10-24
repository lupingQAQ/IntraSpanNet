"""GDNet V5: byte-level traffic classification for security product discovery."""

from .inference import Ensemble
from .labels import PRODUCTS, describe

__version__ = "1.0.0"
__all__ = ["Ensemble", "PRODUCTS", "describe", "__version__"]
