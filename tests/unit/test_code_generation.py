from refactor_tool.model.refactor_request import ExtractMethodRequest
from refactor_tool.refactor.extract_method import build_extraction_plan, apply_extraction_to_source


def test_code_generation_basic():
    src = """
def foo(a, b):
    x = a + 1
    y = x + b
    return y
"""
    req = ExtractMethodRequest(source=src, enclosing_function="foo", selection_start_line=3, selection_end_line=4, new_method_name="extracted")
    plan = build_extraction_plan(req)
    new_src = apply_extraction_to_source(req, plan)
    assert "def extracted" in new_src
    assert "extracted(" in new_src
    # original function should still exist
    assert "def foo(" in new_src
