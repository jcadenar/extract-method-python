"""AST parsing helpers for Python source code."""

from __future__ import annotations

import ast


class ParsingError(ValueError):
	"""Raised when the input source cannot be parsed."""


def parse_source(source: str) -> ast.Module:
	"""Parse source code into an AST module."""

	try:
		return ast.parse(source)
	except SyntaxError as exc:
		raise ParsingError(str(exc)) from exc


def get_function_by_name(module: ast.Module, function_name: str) -> ast.FunctionDef:
	"""Return the first FunctionDef with the given name found in the module (including methods and nested functions)."""

	for node in ast.walk(module):
		if isinstance(node, ast.FunctionDef) and node.name == function_name:
			return node
	raise ValueError(f"Function '{function_name}' was not found in module")


def find_function_and_enclosing_class(module: ast.Module, function_name: str) -> tuple[ast.FunctionDef, ast.ClassDef | None]:
	"""Find a FunctionDef by name and return it together with its enclosing ClassDef (if any)."""

	for node in ast.walk(module):
		if isinstance(node, ast.FunctionDef) and node.name == function_name:
			# Search for a ClassDef that contains this FunctionDef
			for parent in module.body:
				if isinstance(parent, ast.ClassDef):
					for child in parent.body:
						if child is node:
							return node, parent
			return node, None
	raise ValueError(f"Function '{function_name}' was not found in module")


def find_selected_statement_indices(
	function_node: ast.FunctionDef,
	start_line: int,
	end_line: int,
) -> tuple[int, int]:
	"""Locate selected statement indices [start, end) inside a function body."""

	if start_line > end_line:
		raise ValueError("selection_start_line must be <= selection_end_line")

	start_idx: int | None = None
	end_idx: int | None = None

	for index, stmt in enumerate(function_node.body):
		stmt_start = getattr(stmt, "lineno", None)
		stmt_end = getattr(stmt, "end_lineno", stmt_start)
		if stmt_start is None or stmt_end is None:
			continue
		if stmt_start >= start_line and stmt_end <= end_line:
			if start_idx is None:
				start_idx = index
			end_idx = index + 1

	if start_idx is None or end_idx is None:
		raise ValueError("Selection does not fully cover complete statements")

	return start_idx, end_idx

