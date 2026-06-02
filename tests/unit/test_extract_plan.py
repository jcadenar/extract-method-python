from refactor_tool.model.refactor_request import ExtractMethodRequest
from refactor_tool.refactor.extract_method import build_extraction_plan


def test_build_extraction_plan_basic():
    src = """
def foo(a, b):
    x = a + 1
    y = x + b
    return y
"""
    req = ExtractMethodRequest(source=src, enclosing_function="foo", selection_start_line=3, selection_end_line=4, new_method_name="extracted")
    plan = build_extraction_plan(req)
    assert plan.enclosing_function == "foo"
    assert plan.selected_statement_count == 2
    assert plan.input_params == ["a", "b"]
    assert plan.output_values == ["y"]
