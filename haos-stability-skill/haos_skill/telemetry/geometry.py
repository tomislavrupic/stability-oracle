from __future__ import annotations

from dataclasses import dataclass

from .contracts import InvalidTelemetry, TelemetryFrame, TelemetrySequence, validate_sequence


@dataclass(frozen=True)
class GeometryEncoderConfig:
    scale: bool = True
    add_first_derivative: bool = True
    add_second_derivative: bool = False
    fixed_pca_components: int | None = None

    def __post_init__(self) -> None:
        if self.fixed_pca_components is not None:
            raise InvalidTelemetry("fixed_pca_components is not supported in StateGeometryEncoder v0")


class StateGeometryEncoder:
    def __init__(self, config: GeometryEncoderConfig | None = None) -> None:
        self.config = config or GeometryEncoderConfig()

    def encode(self, seq: TelemetrySequence) -> TelemetrySequence:
        validate_sequence(seq)
        frames = tuple(seq.frames)
        base_dimension = len(frames[0].state_vector)

        first_derivatives = _first_derivatives(frames) if self.config.add_first_derivative else None
        second_derivatives = _second_derivatives(frames) if self.config.add_second_derivative else None

        encoded_frames = []
        for index, frame in enumerate(frames):
            encoded_vector = list(frame.state_vector)
            if first_derivatives is not None:
                encoded_vector.extend(first_derivatives[index])
            if second_derivatives is not None:
                encoded_vector.extend(second_derivatives[index])
            encoded_frames.append(
                TelemetryFrame(
                    timestamp=frame.timestamp,
                    entity_id=frame.entity_id,
                    state_vector=tuple(encoded_vector),
                    metadata=frame.metadata,
                )
            )

        if self.config.scale:
            encoded_frames = list(_scale_encoded_frames(tuple(encoded_frames)))

        metadata = dict(seq.metadata)
        metadata["geometry_encoder"] = {
            "scale": self.config.scale,
            "add_first_derivative": self.config.add_first_derivative,
            "add_second_derivative": self.config.add_second_derivative,
            "base_feature_dim": base_dimension,
            "encoded_feature_dim": len(encoded_frames[0].state_vector),
        }

        return TelemetrySequence(
            frames=tuple(encoded_frames),
            entity_id=seq.entity_id,
            feature_dim=len(encoded_frames[0].state_vector),
            metadata=metadata,
        )


def _first_derivatives(frames: tuple[TelemetryFrame, ...]) -> tuple[tuple[float, ...], ...]:
    dimension = len(frames[0].state_vector)
    derivatives = [(0.0,) * dimension]
    for previous, current in zip(frames, frames[1:]):
        delta_time = current.timestamp - previous.timestamp
        scale = delta_time if delta_time > 0.0 else 1.0
        derivatives.append(
            tuple(
                round((current.state_vector[index] - previous.state_vector[index]) / scale, 6)
                for index in range(dimension)
            )
        )
    return tuple(derivatives)


def _second_derivatives(frames: tuple[TelemetryFrame, ...]) -> tuple[tuple[float, ...], ...]:
    first = _first_derivatives(frames)
    dimension = len(frames[0].state_vector)
    derivatives = [(0.0,) * dimension]
    for previous, current in zip(first, first[1:]):
        derivatives.append(
            tuple(
                round(current[index] - previous[index], 6)
                for index in range(dimension)
            )
        )
    return tuple(derivatives)


def _scale_encoded_frames(frames: tuple[TelemetryFrame, ...]) -> tuple[TelemetryFrame, ...]:
    dimension = len(frames[0].state_vector)
    scales = []
    for index in range(dimension):
        max_abs = max(abs(frame.state_vector[index]) for frame in frames)
        scales.append(max_abs if max_abs > 0.0 else 1.0)

    return tuple(
        TelemetryFrame(
            timestamp=frame.timestamp,
            entity_id=frame.entity_id,
            state_vector=tuple(
                round(frame.state_vector[index] / scales[index], 6)
                for index in range(dimension)
            ),
            metadata=frame.metadata,
        )
        for frame in frames
    )
