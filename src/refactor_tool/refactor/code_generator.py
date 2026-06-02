"""Generate extracted function and rewrite the original source using ast."""

from __future__ import annotations

import ast
from copy import deepcopy
from typing import Iterable
import textwrap

from refactor_tool.model.refactor_request import ExtractMethodRequest, ExtractionPlan
from refactor_tool.parsing.ast_parser import (
    parse_source,
    find_function_and_enclosing_class,
    find_selected_statement_indices,
)


def _make_args_from_function(function_node: ast.FunctionDef, params: Iterable[str]) -> ast.arguments:
    # Build arguments preserving vararg/kwarg and defaults from the original function when possible
    params = list(params)
    fn_args = function_node.args

    # Prepare positional args that are in params and in fn_args.args
    pos_arg_names = [a.arg for a in fn_args.args]
    # keep the original order for positional args
    pos_args_filtered = [name for name in pos_arg_names if name in params]
    pos_args = [ast.arg(arg=name) for name in pos_args_filtered]

    # Map defaults from original function: defaults correspond to last N positional args
    default_map: dict[str, ast.expr] = {}
    if fn_args.defaults:
        num_pos = len(pos_arg_names)
        num_defaults = len(fn_args.defaults)
        defaults_start = num_pos - num_defaults
        for i, d in enumerate(fn_args.defaults):
            arg_name = pos_arg_names[defaults_start + i]
            default_map[arg_name] = d

    # Build defaults list aligned to the trailing positional args of pos_args
    defaults: list[ast.expr] = []
    # walk from end collecting defaults for trailing args that have defaults
    for name in reversed(pos_args_filtered):
        if name in default_map:
            defaults.append(default_map[name])
        else:
            break
    defaults = list(reversed(defaults))

    # vararg and kwarg inclusion
    vararg = fn_args.vararg if (fn_args.vararg and fn_args.vararg.arg in params) else None
    kwarg = fn_args.kwarg if (fn_args.kwarg and fn_args.kwarg.arg in params) else None

    # kwonlyargs: include those in params and preserve their defaults (which may be None)
    kwonly_args_filtered = [a for a in fn_args.kwonlyargs if a.arg in params]
    kwonly_args = [ast.arg(arg=a.arg) for a in kwonly_args_filtered]
    kw_defaults = []
    for a, d in zip(fn_args.kwonlyargs, fn_args.kw_defaults):
        if a.arg in params:
            kw_defaults.append(d)

    return ast.arguments(
        posonlyargs=[],
        args=pos_args,
        vararg=ast.arg(arg=vararg.arg) if vararg is not None else None,
        kwonlyargs=kwonly_args,
        kw_defaults=kw_defaults,
        kwarg=ast.arg(arg=kwarg.arg) if kwarg is not None else None,
        defaults=defaults,
    )


def _make_call_text(name: str, arg_names: Iterable[str], function_node: ast.FunctionDef) -> str:
    # Build a textual call that orders arguments according to the original function signature
    arg_set = set(arg_names)
    parts = []
    # positional args (in original order)
    for a in function_node.args.args:
        if a.arg in arg_set:
            parts.append(a.arg)
    # vararg
    if function_node.args.vararg and function_node.args.vararg.arg in arg_set:
        parts.append(f"*{function_node.args.vararg.arg}")
    # keyword-only args: pass as name=name
    for a in function_node.args.kwonlyargs:
        if a.arg in arg_set:
            parts.append(f"{a.arg}={a.arg}")
    # kwarg
    if function_node.args.kwarg and function_node.args.kwarg.arg in arg_set:
        parts.append(f"**{function_node.args.kwarg.arg}")

    return f"{name}({', '.join(parts)})"


def apply_extraction(request: ExtractMethodRequest, plan: ExtractionPlan) -> str:
    """Return a new source string with the extracted function appended at module level and the call in place."""
    # We'll perform a textual replacement to preserve original formatting and comments.
    module = parse_source(request.source)
    fn, class_node = find_function_and_enclosing_class(module, request.enclosing_function)
    start_idx, end_idx = find_selected_statement_indices(fn, request.selection_start_line, request.selection_end_line)

    # Determine lineno range for selected statements
    sel_first = fn.body[start_idx]
    sel_last = fn.body[end_idx - 1]
    sel_start_line = getattr(sel_first, "lineno")
    sel_end_line = getattr(sel_last, "end_lineno", getattr(sel_last, "lineno"))

    lines = request.source.splitlines(keepends=True)

    # Compute indentation from the first selected line
    first_line = lines[sel_start_line - 1]
    indent = ""
    for ch in first_line:
        if ch.isspace():
            indent += ch
        else:
            break

    # Build call text (with proper assignment if outputs) using function signature info
    # Detect method kind and build an appropriate call and signature.
    first_arg_name = fn.args.args[0].arg if fn.args.args else None
    # detect decorators
    def _decorator_name(d: ast.expr) -> str | None:
        if isinstance(d, ast.Name):
            return d.id
        if isinstance(d, ast.Attribute):
            return d.attr
        return None

    is_classmethod = any(_decorator_name(d) == "classmethod" for d in fn.decorator_list)
    is_staticmethod = any(_decorator_name(d) == "staticmethod" for d in fn.decorator_list)
    is_method = class_node is not None and not is_staticmethod

    class_name = class_node.name if class_node is not None else None

    # Choose receiver for method calls: 'self' for instance methods, 'cls' or class name for classmethods, class name for staticmethods
    receiver = None
    if is_classmethod:
        receiver = first_arg_name if first_arg_name == "cls" else class_name
    elif is_staticmethod:
        receiver = class_name
    elif is_method:
        receiver = first_arg_name

    if receiver:
        arg_names_for_call = [p for p in plan.input_params if p != receiver]
        call_code = _make_call_text(f"{receiver}.{request.new_method_name}", arg_names_for_call, fn)
    else:
        call_code = _make_call_text(request.new_method_name, plan.input_params, fn)
    if not plan.output_values:
        replacement_code = indent + call_code + "\n"
    elif len(plan.output_values) == 1:
        replacement_code = indent + f"{plan.output_values[0]} = {call_code}\n"
    else:
        targets = ", ".join(plan.output_values)
        replacement_code = indent + f"{targets} = {call_code}\n"

    # Replace the selected source region with the replacement
    new_lines_repl: list[str] = []
    new_lines_repl.extend(lines[: sel_start_line - 1])
    new_lines_repl.append(replacement_code)
    new_lines_repl.extend(lines[sel_end_line:])

    # Build extracted function source using ast.unparse on the new function node
    selected = deepcopy(fn.body[start_idx:end_idx])
    # Ensure the new function's args include the appropriate receiver when extracting into a class
    params_for_new_fn = list(plan.input_params)
    if is_classmethod:
        if "cls" not in params_for_new_fn:
            params_for_new_fn.insert(0, "cls")
    elif is_method and not is_staticmethod:
        if first_arg_name and first_arg_name not in params_for_new_fn:
            params_for_new_fn.insert(0, first_arg_name)

    # Build decorator list for the extracted function if needed
    new_decorators: list[ast.expr] = []
    if is_classmethod:
        new_decorators.append(ast.Name(id="classmethod", ctx=ast.Load()))
    if is_staticmethod:
        new_decorators.append(ast.Name(id="staticmethod", ctx=ast.Load()))

    new_fn = ast.FunctionDef(
        name=request.new_method_name,
        args=_make_args_from_function(fn, params_for_new_fn),
        body=selected[:],
        decorator_list=new_decorators,
        returns=None,
    )
    if plan.output_values:
        if len(plan.output_values) == 1:
            ret = ast.Return(value=ast.Name(id=plan.output_values[0], ctx=ast.Load()))
        else:
            ret = ast.Return(value=ast.Tuple(elts=[ast.Name(id=n, ctx=ast.Load()) for n in plan.output_values], ctx=ast.Load()))
        new_fn.body.append(ret)

    ast.fix_missing_locations(new_fn)

    # Try to preserve the original selected source (including comments) when building
    # the extracted function. If libcst is available we could use it; otherwise fall
    # back to using the original textual slice and embed it as the function body.
    original_body_text = "".join(lines[sel_start_line - 1:sel_end_line])

    try:
        import libcst as cst  # type: ignore
        from libcst.metadata import PositionProvider, MetadataWrapper

        # Parse and wrap to obtain position metadata
        module_cst = cst.parse_module(request.source)
        wrapper = MetadataWrapper(module_cst)

        # Find the CST FunctionDef that corresponds to the AST function (match by start line)
        target_fn_cst: cst.FunctionDef | None = None

        class FnFinder(cst.CSTVisitor):
            def __init__(self, wrapper: MetadataWrapper):
                self._wrapper = wrapper
                self.found: cst.FunctionDef | None = None

            def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
                try:
                    pos = self._wrapper.get_metadata(PositionProvider, node)
                except Exception:
                    return
                if pos.start.line == getattr(fn, "lineno", None):
                    self.found = node

        finder = FnFinder(wrapper)
        wrapper.visit(finder)
        target_fn_cst = finder.found

        if target_fn_cst is None:
            # couldn't locate corresponding CST function; fall back
            raise RuntimeError("could not locate function in libcst AST")

        # Collect CST statements within the selected line range
        selected_cst_nodes: list[cst.CSTNode] = []
        for stmt in target_fn_cst.body.body:
            try:
                pos = wrapper.get_metadata(PositionProvider, stmt)
            except Exception:
                continue
            if pos.start.line >= sel_start_line and pos.end.line <= sel_end_line:
                selected_cst_nodes.append(stmt)

        if not selected_cst_nodes:
            # nothing selected according to CST metadata; fall back
            raise RuntimeError("no CST statements matched selection")

        # Use libcst to get the exact source for each selected statement (preserving comments)
        parts: list[str] = []
        for node in selected_cst_nodes:
            try:
                parts.append(module_cst.code_for_node(node))
            except Exception:
                # fallback to textual slice of the node's lines
                try:
                    pos = wrapper.get_metadata(PositionProvider, node)
                    lines_slice = lines[pos.start.line - 1 : pos.end.line]
                    parts.append("".join(lines_slice))
                except Exception:
                    pass

        body_text = "".join(parts)
        # Dedent the captured body to normalize indentation
        dedented = textwrap.dedent(body_text)

        # If outputs were computed, append a return statement to the preserved body
        if plan.output_values:
            if len(plan.output_values) == 1:
                dedented = dedented.rstrip("\n") + f"\nreturn {plan.output_values[0]}\n"
            else:
                joined = ", ".join(plan.output_values)
                dedented = dedented.rstrip("\n") + f"\nreturn {joined}\n"

        # Build decorators text
        decorators_text = ""
        for d in new_decorators:
            try:
                decorators_text += f"@{ast.unparse(d)}\n"
            except Exception:
                if isinstance(d, ast.Name):
                    decorators_text += f"@{d.id}\n"

        # Build function header from ast function signature
        try:
            fn_text = ast.unparse(new_fn)
            header, _sep, _rest = fn_text.partition(":\n")
        except Exception:
            args_sig = ", ".join(params_for_new_fn)
            header = f"def {request.new_method_name}({args_sig})"

        # Prepare indented body for module-level function (4-space indent)
        indented_body = "".join(("    " + l if l.strip() else "\n") for l in dedented.splitlines(True))
        extracted_src = decorators_text + header + ":\n" + indented_body.rstrip("\n")
    except Exception:
        # Fallback: dedent the original selected text and re-indent as function body
        dedented = textwrap.dedent(original_body_text)
        body_lines = dedented.splitlines()
        indented_body = "".join(("    " + l if l.strip() else "\n") + "\n" if False else "" for l in [])
        # Build indented body preserving blank lines and comments
        indented_parts: list[str] = []
        for l in body_lines:
            if l.strip():
                indented_parts.append("    " + l + "\n")
            else:
                indented_parts.append("\n")
        indented_body = "".join(indented_parts)

        # Build decorators text
        decorators_text = ""
        for d in new_decorators:
            try:
                decorators_text += f"@{ast.unparse(d)}\n"
            except Exception:
                # fallback simple name
                if isinstance(d, ast.Name):
                    decorators_text += f"@{d.id}\n"

        # If outputs were computed, append a return statement to the preserved body
        if plan.output_values:
            if len(plan.output_values) == 1:
                indented_body = indented_body + f"    return {plan.output_values[0]}\n"
            else:
                joined = ", ".join(plan.output_values)
                indented_body = indented_body + f"    return {joined}\n"

        # Use ast.unparse on the function header to get a reliable signature, then
        # replace the body with the preserved text.
        try:
            fn_text = ast.unparse(new_fn)
            header, _sep, _rest = fn_text.partition(":\n")
            extracted_src = decorators_text + header + ":\n" + indented_body.rstrip("\n")
        except Exception:
            # As a last resort, construct a simple signature from params_for_new_fn
            args_sig = ", ".join(params_for_new_fn)
            extracted_src = decorators_text + f"def {request.new_method_name}({args_sig}):\n" + indented_body.rstrip("\n")

    # If extracting into a class, insert the method into the class body (keeping indentation);
    # otherwise append the extracted function at module level.
    if is_method and class_node is not None:
        # We already applied the replacement to produce source text; parse it
        source_after_repl = "".join(new_lines_repl)
        module2 = ast.parse(source_after_repl)
        # find the class by name in the reparsed module
        class2: ast.ClassDef | None = None
        for n in ast.walk(module2):
            if isinstance(n, ast.ClassDef) and n.name == class_node.name:
                class2 = n
                break

        if class2 is None:
            # fallback: append at module level
            lines2 = source_after_repl.splitlines(keepends=True)
            if not lines2 or not lines2[-1].endswith("\n"):
                lines2.append("\n")
            lines2.append("\n")
            lines2.append(extracted_src + "\n")
            return "".join(lines2)

        # Determine insertion index (after class2.body last node)
        class_end = getattr(class2, "end_lineno", None)
        if class_end is None:
            lines2 = source_after_repl.splitlines(keepends=True)
            insert_idx = len(lines2)
            class_indent = "    "
        else:
            lines2 = source_after_repl.splitlines(keepends=True)
            insert_idx = class_end
            # Determine class body indentation from first member
            if class2.body:
                first_member = class2.body[0]
                member_line = lines2[getattr(first_member, "lineno") - 1]
                class_indent = "".join(ch for ch in member_line if ch.isspace())
            else:
                class_indent = "    "

        # Indent the extracted_src by the class indentation
        indented_lines = []
        for line in extracted_src.splitlines(keepends=True):
            if line.strip():
                indented_lines.append(class_indent + line)
            else:
                indented_lines.append(line)

        # Insert with blank lines around
        if insert_idx > 0 and not lines2[insert_idx - 1].endswith("\n"):
            lines2.insert(insert_idx, "\n")
            insert_idx += 1

        lines2[insert_idx:insert_idx] = ["\n"] + indented_lines + ["\n"]

        return "".join(lines2)
    else:
        # Append extracted function to the end, preserving a trailing newline
        if not new_lines_repl or not new_lines_repl[-1].endswith("\n"):
            new_lines_repl.append("\n")
        new_lines_repl.append("\n")
        new_lines_repl.append(extracted_src + "\n")

        return "".join(new_lines_repl)
