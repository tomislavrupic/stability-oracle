from __future__ import annotations

from dataclasses import dataclass, field
import math
import re
from typing import Any, List


VECTOR_KEYS = (
    "step_length_norm",
    "confidence_proxy",
    "novelty_vs_prev",
    "self_overlap",
    "contradiction_score",
    "numeric_consistency_score",
    "tool_dependency_score",
    "terminality_score",
)

_TOKEN_RE = re.compile(r"[a-zA-Z]+(?:'[a-z]+)?|\d+(?:\.\d+)?")
_CONFIDENT_TERMS = {
    "therefore",
    "thus",
    "so",
    "final",
    "answer",
    "exactly",
    "correct",
    "hence",
}
_HEDGE_TERMS = {
    "maybe",
    "perhaps",
    "might",
    "guess",
    "possibly",
    "unclear",
    "unsure",
}
_CONTRADICTION_TERMS = {
    "wait",
    "however",
    "but",
    "actually",
    "instead",
    "contradiction",
    "wrong",
    "rethink",
}
_TOOL_TERMS = {
    "tool",
    "calculator",
    "search",
    "lookup",
    "external",
    "browser",
    "python",
}
_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "if",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "then",
    "to",
    "we",
}


@dataclass(frozen=True)
class TelemetryFrame:
    timestamp: float
    entity_id: str
    state_vector: List[float]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TelemetrySequence:
    entity_id: str
    frames: List[TelemetryFrame]


class LLMReasoningAdapter:
    def from_trace(self, trace: list[dict], entity_id: str) -> TelemetrySequence:
        """
        Converts reasoning trace into TelemetrySequence.
        Trace format:
        [
            {"step_index": int,
             "text": str,
             "is_final": bool}
        ]
        """

        if not isinstance(entity_id, str) or not entity_id.strip():
            raise ValueError("entity_id must be a non-empty string")
        if not isinstance(trace, list) or not trace:
            raise ValueError("trace must be a non-empty list")

        frames: List[TelemetryFrame] = []
        prev_tokens: list[str] = []
        prev_numbers: list[str] = []
        prev_terms: set[str] = set()

        for raw_step in trace:
            step_index = int(raw_step["step_index"])
            text = str(raw_step["text"])
            is_final = bool(raw_step.get("is_final", False))

            tokens = _tokenize(text)
            terms = {token for token in tokens if token not in _STOPWORDS}
            numbers = [token for token in tokens if _is_number_token(token)]
            token_count = len(tokens)

            length_norm = _clip(token_count / 24.0)
            confidence_proxy = self._confidence_proxy(tokens)
            similarity = _token_similarity(prev_terms, terms)
            novelty = 0.0 if not frames else _clip(1.0 - similarity)
            self_overlap = 1.0 if not frames else _clip(similarity)
            contradiction = self._contradiction_score(tokens, prev_numbers, numbers, prev_terms, terms)
            numeric_consistency = self._numeric_consistency(prev_numbers, numbers)
            tool_dependency = self._tool_dependency(tokens)
            terminality = self._terminality_score(tokens, is_final)

            vector = [
                _round_metric(length_norm),
                _round_metric(confidence_proxy),
                _round_metric(novelty),
                _round_metric(self_overlap),
                _round_metric(contradiction),
                _round_metric(numeric_consistency),
                _round_metric(tool_dependency),
                _round_metric(terminality),
            ]

            frames.append(
                TelemetryFrame(
                    timestamp=float(step_index),
                    entity_id=entity_id,
                    state_vector=vector,
                    metadata={
                        "step_index": step_index,
                        "text": text,
                        "is_final": is_final,
                        "vector_keys": list(VECTOR_KEYS),
                    },
                )
            )

            prev_tokens = tokens
            prev_numbers = numbers
            prev_terms = terms

        return TelemetrySequence(entity_id=entity_id, frames=frames)

    def _confidence_proxy(self, tokens: list[str]) -> float:
        if not tokens:
            return 0.0
        confident = sum(1 for token in tokens if token in _CONFIDENT_TERMS)
        hedged = sum(1 for token in tokens if token in _HEDGE_TERMS)
        declarative = 1.0 if any(token in {"=", "therefore", "thus", "answer"} for token in tokens) else 0.0
        raw = 0.45 + 0.18 * confident + 0.12 * declarative - 0.20 * hedged
        return _clip(raw)

    def _contradiction_score(
        self,
        tokens: list[str],
        prev_numbers: list[str],
        numbers: list[str],
        prev_terms: set[str],
        terms: set[str],
    ) -> float:
        term_hits = sum(1 for token in tokens if token in _CONTRADICTION_TERMS)
        lexical_flip = 1.0 if {"not", "wrong"} & set(tokens) else 0.0
        numeric_flip = 0.0
        if prev_numbers and numbers:
            overlap = len(set(prev_numbers) & set(numbers)) / len(set(prev_numbers) | set(numbers))
            correction_context = term_hits > 0 or lexical_flip > 0.0 or {"final", "answer"} & set(tokens)
            if correction_context:
                numeric_flip = 1.0 - overlap
        semantic_break = 0.0
        if prev_terms and terms:
            semantic_break = 1.0 - _token_similarity(prev_terms, terms)
        raw = 0.20 * term_hits + 0.22 * lexical_flip + 0.30 * numeric_flip + 0.10 * semantic_break
        return _clip(raw)

    def _numeric_consistency(self, prev_numbers: list[str], numbers: list[str]) -> float:
        if not prev_numbers and not numbers:
            return 0.7
        if prev_numbers and not numbers:
            return 0.35
        if not prev_numbers:
            return 0.75
        overlap = len(set(prev_numbers) & set(numbers)) / len(set(prev_numbers) | set(numbers))
        return _clip(0.55 + 0.45 * overlap)

    def _tool_dependency(self, tokens: list[str]) -> float:
        if not tokens:
            return 0.0
        hits = sum(1 for token in tokens if token in _TOOL_TERMS)
        return _clip(hits / 3.0)

    def _terminality_score(self, tokens: list[str], is_final: bool) -> float:
        terminal_terms = {"answer", "final", "therefore", "thus", "done"}
        lexical_signal = 1.0 if terminal_terms & set(tokens) else 0.0
        if is_final:
            return _clip(0.6 + 0.4 * lexical_signal)
        return _clip(0.2 * lexical_signal)


def _tokenize(text: str) -> list[str]:
    return [token.lower() for token in _TOKEN_RE.findall(text)]


def _token_similarity(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _is_number_token(token: str) -> bool:
    try:
        float(token)
        return True
    except ValueError:
        return False


def _clip(value: float) -> float:
    if math.isnan(value) or math.isinf(value):
        return 0.0
    return max(0.0, min(1.0, float(value)))


def _round_metric(value: float) -> float:
    return round(_clip(value), 4)
