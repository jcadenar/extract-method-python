"""Data models for Extract Method requests and plans."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExtractMethodRequest:
	"""Input required to compute an Extract Method plan."""

	source: str
	enclosing_function: str
	selection_start_line: int
	selection_end_line: int
	new_method_name: str


@dataclass(frozen=True)
class ExtractionPlan:
	"""Static-analysis result used later to rewrite code safely."""

	enclosing_function: str
	selected_statement_count: int
	input_params: list[str]
	output_values: list[str]
	enclosing_class: str | None = None

