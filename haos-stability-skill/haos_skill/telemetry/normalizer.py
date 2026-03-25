from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .contracts import InvalidTelemetry, TelemetryFrame, TelemetrySequence, validate_sequence


@dataclass(frozen=True)
class TemporalNormalizerConfig:
    resample: bool = False
    target_cadence: float | None = None
    add_gap_markers: bool = True
    difference_order: int = 0
    scale_vectors: bool = True

    def __post_init__(self) -> None:
        if self.resample:
            raise InvalidTelemetry("resampling is not supported in TemporalNormalizer v0")
        if self.target_cadence is not None and self.target_cadence <= 0.0:
            raise InvalidTelemetry("target_cadence must be greater than zero when provided")
        if self.difference_order not in (0, 1):
            raise InvalidTelemetry("difference_order must be 0 or 1 in TemporalNormalizer v0")


class TemporalNormalizer:
    def __init__(self, config: TemporalNormalizerConfig | None = None) -> None:
        self.config = config or TemporalNormalizerConfig()

    def normalize(self, seq: TelemetrySequence) -> TelemetrySequence:
        validate_sequence(seq)
        frames = tuple(seq.frames)
        metadata = dict(seq.metadata)

        if self.config.scale_vectors:
            frames = _scale_frames(frames)

        if self.config.difference_order == 1:
            frames = _difference_frames(frames)

        if self.config.add_gap_markers:
            metadata["gap_markers"] = _gap_markers(frames)

        metadata["normalizer"] = {
            "resample": self.config.resample,
            "target_cadence": self.config.target_cadence,
            "add_gap_markers": self.config.add_gap_markers,
            "difference_order": self.config.difference_order,
            "scale_vectors": self.config.scale_vectors,
        }

        return TelemetrySequence(
            frames=frames,
            entity_id=seq.entity_id,
            feature_dim=len(frames[0].state_vector),
            metadata=metadata,
        )


def _scale_frames(frames: tuple[TelemetryFrame, ...]) -> tuple[TelemetryFrame, ...]:
    dimension = len(frames[0].state_vector)
    scales = []
    for index in range(dimension):
        max_abs = max(abs(frame.state_vector[index]) for frame in frames)
        scales.append(max_abs if max_abs > 0.0 else 1.0)

    normalized_frames = []
    for frame in frames:
        normalized_vector = tuple(
            round(frame.state_vector[index] / scales[index], 6)
            for index in range(dimension)
        )
        normalized_frames.append(
            TelemetryFrame(
                timestamp=frame.timestamp,
                entity_id=frame.entity_id,
                state_vector=normalized_vector,
                metadata=frame.metadata,
            )
        )
    return tuple(normalized_frames)


def _difference_frames(frames: tuple[TelemetryFrame, ...]) -> tuple[TelemetryFrame, ...]:
    if len(frames) < 2:
        raise InvalidTelemetry("difference_order=1 requires at least two frames")

    dimension = len(frames[0].state_vector)
    differenced_frames = [
        TelemetryFrame(
            timestamp=frames[0].timestamp,
            entity_id=frames[0].entity_id,
            state_vector=(0.0,) * dimension,
            metadata={**frames[0].metadata, "difference_origin": "baseline"},
        )
    ]

    for previous, current in zip(frames, frames[1:]):
        differenced_vector = tuple(
            round(current.state_vector[index] - previous.state_vector[index], 6)
            for index in range(dimension)
        )
        differenced_frames.append(
            TelemetryFrame(
                timestamp=current.timestamp,
                entity_id=current.entity_id,
                state_vector=differenced_vector,
                metadata={**current.metadata, "difference_origin": "first_order"},
            )
        )
    return tuple(differenced_frames)


def _gap_markers(frames: tuple[TelemetryFrame, ...]) -> list[bool]:
    if len(frames) < 2:
        return [False] * len(frames)
    deltas = [
        round(current.timestamp - previous.timestamp, 6)
        for previous, current in zip(frames, frames[1:])
    ]
    positive_deltas = [delta for delta in deltas if delta > 0.0]
    baseline = min(positive_deltas) if positive_deltas else 0.0
    markers = [False]
    for delta in deltas:
        markers.append(bool(baseline > 0.0 and delta > baseline))
    return markers
