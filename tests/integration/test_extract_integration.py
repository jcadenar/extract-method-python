import json
from pathlib import Path

from refactor_tool.model.refactor_request import ExtractMethodRequest
from refactor_tool.refactor.extract_method import build_extraction_plan


DATA_DIR = Path(__file__).resolve().parents[2] / "examples"


def test_examples_match_expected():
    input_dir = DATA_DIR / "input"
    expected_dir = DATA_DIR / "expected"

    for py_file in input_dir.glob("*.py"):
        name = py_file.stem
        expected_file = expected_dir / (name + ".json")
        assert expected_file.exists(), f"Missing expected file for {name}"

        src = py_file.read_text(encoding="utf-8")
        expected = json.loads(expected_file.read_text(encoding="utf-8"))

        req = ExtractMethodRequest(
            source=src,
            enclosing_function=expected["enclosing_function"],
            selection_start_line=expected["selection_start_line"],
            selection_end_line=expected["selection_end_line"],
            new_method_name=expected.get("new_method_name", "extracted"),
        )

        plan = build_extraction_plan(req)

        assert plan.enclosing_function == expected["enclosing_function"]
        assert plan.selected_statement_count == expected["selected_statement_count"]
        assert plan.input_params == expected["input_params"]
        assert plan.output_values == expected["output_values"]
