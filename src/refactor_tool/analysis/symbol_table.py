"""Name collection utilities for static analysis."""

from __future__ import annotations

import ast


class _NameCollector(ast.NodeVisitor):
	def __init__(self) -> None:
		self.loaded: set[str] = set()
		self.stored: set[str] = set()

	def visit_Name(self, node: ast.Name) -> None:
		if isinstance(node.ctx, ast.Load):
			self.loaded.add(node.id)
		elif isinstance(node.ctx, (ast.Store, ast.Del)):
			self.stored.add(node.id)
		self.generic_visit(node)


def collect_loaded_names(nodes: list[ast.stmt]) -> set[str]:
	collector = _NameCollector()
	for node in nodes:
		collector.visit(node)
	return collector.loaded


def collect_stored_names(nodes: list[ast.stmt]) -> set[str]:
	collector = _NameCollector()
	for node in nodes:
		collector.visit(node)
	return collector.stored


def function_argument_names(function_node: ast.FunctionDef) -> set[str]:
	args = function_node.args
	names: set[str] = set()
	names.update(arg.arg for arg in args.posonlyargs)
	names.update(arg.arg for arg in args.args)
	names.update(arg.arg for arg in args.kwonlyargs)
	if args.vararg is not None:
		names.add(args.vararg.arg)
	if args.kwarg is not None:
		names.add(args.kwarg.arg)
	return names


def collect_module_level_names(module: ast.Module) -> set[str]:
	"""Collect top-level names defined at module scope (functions, classes, assigns, imports)."""
	names: set[str] = set()
	for node in module.body:
		if isinstance(node, ast.FunctionDef):
			names.add(node.name)
		elif isinstance(node, ast.ClassDef):
			names.add(node.name)
		elif isinstance(node, ast.Assign):
			for target in node.targets:
				if isinstance(target, ast.Name):
					names.add(target.id)
		elif isinstance(node, ast.Import):
			for alias in node.names:
				names.add(alias.asname or alias.name.split(".")[0])
		elif isinstance(node, ast.ImportFrom):
			for alias in node.names:
				names.add(alias.asname or alias.name)
	return names


def collect_global_names(nodes: list[ast.stmt]) -> set[str]:
	"""Collect names declared with `global` in a direct statement list."""
	names: set[str] = set()
	for node in nodes:
		if isinstance(node, ast.Global):
			names.update(node.names)
	return names


def collect_nonlocal_names(nodes: list[ast.stmt]) -> set[str]:
	"""Collect names declared with `nonlocal` in a direct statement list."""
	names: set[str] = set()
	for node in nodes:
		if isinstance(node, ast.Nonlocal):
			names.update(node.names)
	return names

