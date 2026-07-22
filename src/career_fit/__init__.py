"""Career Fit public API.

The legacy ``skillbundle`` namespace remains available for compatibility while
the product and documentation use Career Fit.
"""

from skillbundle.career import analyze_fit, evidence_from_text
from skillbundle.requirements import extract_requirements

__version__ = "0.2.0"

__all__ = ["analyze_fit", "evidence_from_text", "extract_requirements"]
