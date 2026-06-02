"""Simple CLI entry point for extraction planning."""

from __future__ import annotations

import argparse
import pathlib

from refactor_tool.model.refactor_request import ExtractMethodRequest
from refactor_tool.refactor.extract_method import build_extraction_plan


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plan an Extract Method refactor")
    parser.add_argument("file", type=pathlib.Path, help="Python source file")
    parser.add_argument("function", help="Name of function containing the selection")
    parser.add_argument("start_line", type=int, help="Selection start line (1-based)")
    parser.add_argument("end_line", type=int, help="Selection end line (1-based)")
    parser.add_argument("new_method", help="Name for extracted method")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    source = args.file.read_text(encoding="utf-8")
    request = ExtractMethodRequest(
        source=source,
        enclosing_function=args.function,
        selection_start_line=args.start_line,
        selection_end_line=args.end_line,
        new_method_name=args.new_method,
    )
    plan = build_extraction_plan(request)
    print("Function:", plan.enclosing_function)
    print("Selected statements:", plan.selected_statement_count)
    print("Inputs:", ", ".join(plan.input_params) or "(none)")
    print("Outputs:", ", ".join(plan.output_values) or "(none)")


if __name__ == "__main__":
    main()
