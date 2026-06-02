"""Extract Method planning pipeline."""

from __future__ import annotations

from refactor_tool.analysis.liveness import infer_inputs_outputs
from refactor_tool.model.refactor_request import ExtractionPlan, ExtractMethodRequest
from refactor_tool.parsing.ast_parser import (
	find_selected_statement_indices,
	find_function_and_enclosing_class,
	parse_source,
)
from refactor_tool.refactor.code_generator import apply_extraction


def build_extraction_plan(request: ExtractMethodRequest) -> ExtractionPlan:
	"""Compute a safe extraction plan before doing source rewriting."""

	module = parse_source(request.source)
	function_node, class_node = find_function_and_enclosing_class(module, request.enclosing_function)
	start_index, end_index = find_selected_statement_indices(
		function_node,
		request.selection_start_line,
		request.selection_end_line,
	)
	inputs, outputs, selected = infer_inputs_outputs(module, function_node, start_index, end_index)
	enclosing_class_name = class_node.name if class_node is not None else None
	return ExtractionPlan(
		enclosing_function=request.enclosing_function,
		selected_statement_count=len(selected),
		input_params=inputs,
		output_values=outputs,
		enclosing_class=enclosing_class_name,
	)


def apply_extraction_to_source(request: ExtractMethodRequest, plan: ExtractionPlan) -> str:
	"""Apply the previously computed plan and return the modified source code."""
	return apply_extraction(request, plan)

