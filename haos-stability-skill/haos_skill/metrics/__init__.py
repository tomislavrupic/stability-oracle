"""Metric interfaces and default structural metrics."""

from .base import MetricRegistry, StabilityMetric
from .causal_deformation import CausalDeformationMetric
from .geometric_integrity import GeometricIntegrityMetric
from .structural_retention import StructuralRetentionMetric
from .temporal_consistency import TemporalConsistencyMetric


def build_default_metric_registry() -> MetricRegistry:
    return MetricRegistry(
        (
            StructuralRetentionMetric(),
            TemporalConsistencyMetric(),
            CausalDeformationMetric(),
            GeometricIntegrityMetric(),
        )
    )

__all__ = [
    "CausalDeformationMetric",
    "GeometricIntegrityMetric",
    "MetricRegistry",
    "StabilityMetric",
    "StructuralRetentionMetric",
    "TemporalConsistencyMetric",
    "build_default_metric_registry",
]
