"""Auto-extract logical blocks inside a given function.

Usage: python scripts/auto_extract_fn.py path/to/file.py function_name [--output out.py]

This script finds the function `function_name` in the file using the project's
AST parser, splits its body into blocks separated by blank lines, and extracts
each block into a new helper function. It processes blocks from bottom to top
to avoid shifting line numbers.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import List, Tuple

from refactor_tool.parsing.ast_parser import parse_source, get_function_by_name, find_selected_statement_indices
from refactor_tool.model.refactor_request import ExtractMethodRequest
from refactor_tool.refactor.extract_method import build_extraction_plan, apply_extraction_to_source


def split_into_blocks(lines: List[str], start: int, end: int) -> List[Tuple[int, int]]:
    """Return list of (start_line, end_line) 1-based within [start,end].

    Split by blank lines inside the function body. start/end are 1-based inclusive
    line numbers for the function body (typically function_node.lineno+1 .. end_lineno).
    """
    blocks: List[Tuple[int, int]] = []
    cur_start = None
    for i in range(start - 1, end):
        if lines[i].strip() == "":
            if cur_start is not None:
                blocks.append((cur_start, i))
                cur_start = None
        else:
            if cur_start is None:
                cur_start = i + 1
    if cur_start is not None:
        blocks.append((cur_start, end))
    return blocks


def adjust_to_statements(fn_node, start: int, end: int) -> Tuple[int, int]:
    """Adjust start/end to fully cover complete statements using helper.

    Returns adjusted (start, end) or raises ValueError if cannot.
    """
    # try expanding outward until selection covers complete statements
    max_expand = 50
    s, e = start, end
    for _ in range(max_expand):
        try:
            si, ei = find_selected_statement_indices(fn_node, s, e)
            # convert statement indices back to line numbers using body
            first_stmt = fn_node.body[si]
            last_stmt = fn_node.body[ei - 1]
            return getattr(first_stmt, "lineno"), getattr(last_stmt, "end_lineno", getattr(last_stmt, "lineno"))
        except ValueError:
            # expand: try move s up if possible, otherwise e down
            if s > fn_node.body[0].lineno:
                s = max(fn_node.body[0].lineno, s - 1)
            elif e < fn_node.end_lineno:
                e = min(fn_node.end_lineno, e + 1)
            else:
                break
    raise ValueError("Could not adjust selection to full statements")


def auto_extract_function(path: Path, function_name: str, out: Path | None = None) -> Path:
    src = path.read_text(encoding="utf-8")
    lines = src.splitlines()
    module = parse_source(src)
    fn = get_function_by_name(module, function_name)
    if fn is None:
        raise SystemExit(f"Function {function_name} not found in {path}")

    # function body bounds
    body_start = fn.body[0].lineno
    body_end = getattr(fn, "end_lineno", fn.body[-1].lineno)

    blocks = split_into_blocks(lines, body_start, body_end)
    if not blocks:
        raise SystemExit("No logical blocks found inside function")

    new_src = src
    # process bottom-up
    for idx, (bstart, bend) in enumerate(reversed(blocks), 1):
        # adjust selection to full statements
        module = parse_source(new_src)
        fn = get_function_by_name(module, function_name)
        if fn is None:
            raise SystemExit(f"Function {function_name} disappeared after extraction")

        adj_start, adj_end = adjust_to_statements(fn, bstart, bend)
        name = f"extracted_block_{len(blocks) - idx + 1}"
        req = ExtractMethodRequest(
            source=new_src,
            enclosing_function=function_name,
            selection_start_line=adj_start,
            selection_end_line=adj_end,
            new_method_name=name,
        )
        plan = build_extraction_plan(req)
        new_src = apply_extraction_to_source(req, plan)

    out_path = out or path.with_name(path.stem + "_extracted" + path.suffix)
    out_path.write_text(new_src, encoding="utf-8")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("file", type=Path)
    parser.add_argument("function", help="Function name to break into blocks")
    parser.add_argument("--output", type=Path, help="Output file path")
    args = parser.parse_args()
    out = auto_extract_function(args.file, args.function, args.output)
    print(f"Wrote extracted file to: {out}")


if __name__ == "__main__":
    main()
