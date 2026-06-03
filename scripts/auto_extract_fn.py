"""Auto-extract logical blocks inside a given function.

Usage: python scripts/auto_extract_fn.py path/to/file.py function_name [--output out.py]

Finds the function `function_name`, splits its body into semantic blocks
(separated by TWO or more consecutive blank lines), skips the docstring,
infers the data-flow between blocks, extracts each block into a helper
function with proper inputs/outputs, and inserts the helpers just before
the enclosing function so the output file is immediately executable.
"""
from __future__ import annotations

import ast
import argparse
from pathlib import Path
from typing import List, Tuple, Dict, Set

from refactor_tool.parsing.ast_parser import (
    parse_source,
    get_function_by_name,
    find_selected_statement_indices,
)
from refactor_tool.analysis.symbol_table import (
    collect_stored_names,
    collect_loaded_names,
    function_argument_names,
    collect_module_level_names,
)
from refactor_tool.model.refactor_request import ExtractMethodRequest
from refactor_tool.refactor.extract_method import build_extraction_plan, apply_extraction_to_source


# ---------------------------------------------------------------------------
# Block detection
# ---------------------------------------------------------------------------

def _is_docstring(stmt: ast.stmt) -> bool:
    return isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str)


def split_into_semantic_blocks(
    fn_node: ast.FunctionDef,
    lines: List[str],
) -> List[List[ast.stmt]]:
    """Group consecutive statements into blocks separated by >= 2 blank lines.

    Returns a list of statement groups. The docstring is always skipped.
    """
    stmts = list(fn_node.body)
    if stmts and _is_docstring(stmts[0]):
        stmts = stmts[1:]
    if not stmts:
        return []

    groups: List[List[ast.stmt]] = []
    current: List[ast.stmt] = [stmts[0]]

    for prev, curr in zip(stmts, stmts[1:]):
        prev_end = getattr(prev, "end_lineno", prev.lineno)
        curr_start = curr.lineno
        blank_count = sum(1 for ln in lines[prev_end: curr_start - 1] if ln.strip() == "")
        if blank_count >= 2:
            groups.append(current)
            current = [curr]
        else:
            current.append(curr)

    if current:
        groups.append(current)

    return groups


# ---------------------------------------------------------------------------
# Cross-block data-flow analysis
# ---------------------------------------------------------------------------

def _get_function_return_names(fn_node: ast.FunctionDef) -> Set[str]:
    """Collect names used in return statements of the function (direct Name returns)."""
    names: Set[str] = set()
    for stmt in fn_node.body:
        if isinstance(stmt, ast.Return) and stmt.value is not None:
            if isinstance(stmt.value, ast.Name):
                names.add(stmt.value.id)
            elif isinstance(stmt.value, ast.Tuple):
                for elt in stmt.value.elts:
                    if isinstance(elt, ast.Name):
                        names.add(elt.id)
    return names


def analyze_block_flows(
    fn_node: ast.FunctionDef,
    groups: List[List[ast.stmt]],
    module: ast.Module,
) -> List[Tuple[List[str], List[str]]]:
    """For each block, return (inputs, outputs) considering cross-block data flow.

    - inputs:  variables used in the block that are NOT defined within it,
               but ARE either function parameters or defined by a previous block.
    - outputs: variables defined in the block that are used by ANY later block
               OR returned by the enclosing function.
    """
    import builtins as _builtins
    builtin_names = set(dir(_builtins))
    module_names = collect_module_level_names(module)
    fn_params = function_argument_names(fn_node)
    fn_returns = _get_function_return_names(fn_node)

    stored: List[Set[str]] = [collect_stored_names(g) for g in groups]
    loaded: List[Set[str]] = [collect_loaded_names(g) for g in groups]

    results: List[Tuple[List[str], List[str]]] = []

    for i, group in enumerate(groups):
        available_before: Set[str] = set(fn_params)
        for j in range(i):
            available_before |= stored[j]

        block_inputs: Set[str] = set()
        for name in loaded[i]:
            if name in builtin_names or name in module_names:
                continue
            if name in stored[i]:
                continue
            if name in available_before:
                block_inputs.add(name)

        later_loaded: Set[str] = set()
        for j in range(i + 1, len(groups)):
            later_loaded |= loaded[j]

        block_outputs: Set[str] = stored[i] & (later_loaded | fn_returns)

        results.append((sorted(block_inputs), sorted(block_outputs)))

    return results


# ---------------------------------------------------------------------------
# Code generation helpers
# ---------------------------------------------------------------------------

def _build_extracted_function(
    name: str,
    inputs: List[str],
    outputs: List[str],
    body_lines: List[str],
    fn_node: ast.FunctionDef,
) -> str:
    """Build source text for an extracted helper function."""
    fn_args = fn_node.args
    pos_arg_names = [a.arg for a in fn_args.args]
    default_map: Dict[str, str] = {}
    if fn_args.defaults:
        num_defaults = len(fn_args.defaults)
        defaults_start = len(pos_arg_names) - num_defaults
        for i, d in enumerate(fn_args.defaults):
            default_map[pos_arg_names[defaults_start + i]] = ast.unparse(d)

    params: List[str] = []
    for p in inputs:
        if p in default_map:
            params.append(f"{p}={default_map[p]}")
        elif fn_args.vararg and fn_args.vararg.arg == p:
            params.append(f"*{p}")
        elif fn_args.kwarg and fn_args.kwarg.arg == p:
            params.append(f"**{p}")
        else:
            params.append(p)

    sig = f"def {name}({', '.join(params)}):"

    import textwrap
    raw_body = "".join(body_lines)
    dedented = textwrap.dedent(raw_body)
    body_indented = ""
    for line in dedented.splitlines(keepends=True):
        if line.strip():
            body_indented += "    " + line
        else:
            body_indented += "\n"

    if outputs:
        body_lines_stripped = dedented.splitlines(keepends=True)
        while body_lines_stripped and body_lines_stripped[-1].strip().startswith("return"):
            body_lines_stripped.pop()
        dedented = "".join(body_lines_stripped)
        body_indented = ""
        for line in dedented.splitlines(keepends=True):
            if line.strip():
                body_indented += "    " + line
            else:
                body_indented += "\n"
        ret_vals = ", ".join(outputs)
        body_indented = body_indented.rstrip("\n") + f"\n    return {ret_vals}\n"

    return sig + "\n" + body_indented


def _make_call_line(
    name: str,
    inputs: List[str],
    outputs: List[str],
    indent: str,
    fn_node: ast.FunctionDef,
) -> str:
    """Build the call statement to replace the extracted block."""
    fn_args = fn_node.args
    vararg_name = fn_args.vararg.arg if fn_args.vararg else None
    kwarg_name = fn_args.kwarg.arg if fn_args.kwarg else None

    parts: List[str] = []
    for p in inputs:
        if p == vararg_name:
            parts.append(f"*{p}")
        elif p == kwarg_name:
            parts.append(f"**{p}")
        else:
            parts.append(p)

    call = f"{name}({', '.join(parts)})"

    if not outputs:
        return indent + call + "\n"
    elif len(outputs) == 1:
        return indent + f"{outputs[0]} = {call}\n"
    else:
        return indent + f"{', '.join(outputs)} = {call}\n"


def _insert_helpers_before_function(
    source: str,
    fn_name: str,
    helper_sources: List[str],
) -> str:
    """Insert helper function definitions just before the enclosing function."""
    module = parse_source(source)
    fn = get_function_by_name(module, fn_name)
    fn_start_line = fn.lineno

    lines = source.splitlines(keepends=True)
    insert_at = fn_start_line - 1

    insertion = ""
    for helper_src in helper_sources:
        insertion += helper_src.rstrip("\n") + "\n\n\n"

    return "".join(lines[:insert_at]) + insertion + "".join(lines[insert_at:])


# ---------------------------------------------------------------------------
# Main extraction logic
# ---------------------------------------------------------------------------

def auto_extract_function(path: Path, function_name: str, out: Path | None = None) -> Path:
    src = path.read_text(encoding="utf-8")
    lines = src.splitlines()

    module = parse_source(src)
    fn = get_function_by_name(module, function_name)
    if fn is None:
        raise SystemExit(f"Function '{function_name}' not found in {path}")

    groups = split_into_semantic_blocks(fn, lines)
    if not groups:
        raise SystemExit("No logical blocks found inside function.")

    flows = analyze_block_flows(fn, groups, module)

    print(f"Found {len(groups)} semantic block(s) to extract:")
    for i, (group, (inputs, outputs)) in enumerate(zip(groups, flows), 1):
        s = group[0].lineno
        e = getattr(group[-1], "end_lineno", group[-1].lineno)
        print(f"  block_{i}: lines {s}-{e}  inputs={inputs}  outputs={outputs}")

    src_lines = src.splitlines(keepends=True)
    helper_sources: List[str] = []
    replacements: List[Tuple[int, int, str]] = []

    for i, (group, (inputs, outputs)) in enumerate(zip(groups, flows)):
        block_num = i + 1
        name = f"_{function_name}_block_{block_num}"

        block_start_line = group[0].lineno
        block_end_line = getattr(group[-1], "end_lineno", group[-1].lineno)

        body_lines = src_lines[block_start_line - 1: block_end_line]
        helper_src = _build_extracted_function(name, inputs, outputs, body_lines, fn)
        helper_sources.append(helper_src)

        first_line = src_lines[block_start_line - 1]
        indent = ""
        for ch in first_line:
            if ch.isspace():
                indent += ch
            else:
                break

        call_line = _make_call_line(name, inputs, outputs, indent, fn)
        replacements.append((block_start_line - 1, block_end_line, call_line))

    # Apply replacements bottom-up
    new_lines = list(src_lines)
    for start_0, end_0, call_line in reversed(replacements):
        new_lines[start_0:end_0] = [call_line]

    # If the original function returned a value defined in the last block,
    # update the return statement to use the last block's call result.
    fn_return_names = _get_function_return_names(fn)
    last_outputs = flows[-1][1] if flows else []
    returned_from_last = [v for v in last_outputs if v in fn_return_names]
    if returned_from_last:
        module_tmp = parse_source("".join(new_lines))
        fn_tmp = get_function_by_name(module_tmp, function_name)
        for stmt in fn_tmp.body:
            if isinstance(stmt, ast.Return):
                ret_line_0 = stmt.lineno - 1
                new_lines[ret_line_0] = ""
                break
        fn_end_0 = fn_tmp.end_lineno - 1
        indent = ""
        for i in range(fn_end_0, -1, -1):
            if new_lines[i].strip():
                for ch in new_lines[i]:
                    if ch.isspace():
                        indent += ch
                    else:
                        break
                break
        ret_val = ", ".join(returned_from_last)
        new_lines.insert(fn_end_0 + 1, f"{indent}return {ret_val}\n")

    new_src = "".join(new_lines)

    # Insert helpers before enclosing function
    new_src = _insert_helpers_before_function(new_src, function_name, helper_sources)

    out_path = out or path.with_name(path.stem + "_extracted" + path.suffix)
    out_path.write_text(new_src, encoding="utf-8")
    return out_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Auto extract logical blocks from a function")
    parser.add_argument("file", type=Path, help="Python source file")
    parser.add_argument("function", help="Function name to refactor")
    parser.add_argument("--output", type=Path, help="Output file (default: <stem>_extracted.py)")
    args = parser.parse_args()
    out = auto_extract_function(args.file, args.function, args.output)
    print(f"\nWrote extracted file to: {out}")


if __name__ == "__main__":
    main()
