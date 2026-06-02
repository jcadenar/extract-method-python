from refactor_tool.model.refactor_request import ExtractMethodRequest
from refactor_tool.refactor.extract_method import build_extraction_plan, apply_extraction_to_source


def test_code_generation_multiple_outputs():
    src = """
def foo(a):
    x = a + 1
    y = x * 2
    z = x + y
    return z
"""
    req = ExtractMethodRequest(
        source=src,
        enclosing_function="foo",
        selection_start_line=3,
        selection_end_line=4,
        new_method_name="extracted",
    )
    plan = build_extraction_plan(req)
    new_src = apply_extraction_to_source(req, plan)

    assert "def extracted(a)" in new_src
    assert "x, y = extracted(a)" in new_src
    assert "return x, y" in new_src or "return (x, y)" in new_src
