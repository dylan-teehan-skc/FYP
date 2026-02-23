"""workflow-analysis — trace reconstruction, pattern detection, optimal path discovery."""

__version__ = "0.1.0"

from analysis.models import AnalysisResult, OptimalPath, Suggestion
from analysis.pipeline import run_analysis

__all__ = ["AnalysisResult", "OptimalPath", "Suggestion", "run_analysis"]
