"""Liveness and data-flow analysis helpers."""

from __future__ import annotations

import ast

from refactor_tool.analysis.symbol_table import (
	collect_loaded_names,
	collect_stored_names,
	function_argument_names,
	collect_module_level_names,
	collect_global_names,
	collect_nonlocal_names,
)
import builtins as _builtins


def infer_inputs_outputs(
	module: ast.Module,
	function_node: ast.FunctionDef,
	start_index: int,
	end_index: int,
) -> tuple[list[str], list[str], list[ast.stmt]]:
	"""Infer parameter and return candidates for selected statements."""

	body = function_node.body
	selected = body[start_index:end_index]
	before = body[:start_index]
	after = body[end_index:]

	func_args = function_argument_names(function_node)
	module_names = collect_module_level_names(module)
	directive_names = collect_global_names(body) | collect_nonlocal_names(body)
	available = collect_stored_names(before) | module_names | directive_names
	inputs: set[str] = set()

	builtin_names = set(dir(_builtins))

	for stmt in selected:
		used = collect_loaded_names([stmt])
		for name in used:
			if name in builtin_names:
				continue
			# If name is a module-level name, it's available
			if name in module_names:
				continue
			if name in directive_names:
				continue
			# If name is a function parameter (including vararg/kwarg), include it
			if name in func_args:
				inputs.add(name)
			elif name not in available:
				inputs.add(name)
		available |= collect_stored_names([stmt])

	defined_in_selected = collect_stored_names(selected)
	used_after = collect_loaded_names(after)
	outputs = (defined_in_selected & used_after) - directive_names

	return sorted(inputs), sorted(outputs), selected

