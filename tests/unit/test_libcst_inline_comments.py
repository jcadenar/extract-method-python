from refactor_tool.model.refactor_request import ExtractMethodRequest
from refactor_tool.refactor.extract_method import build_extraction_plan, apply_extraction_to_source


def test_preserve_inline_comments():
    src = """
def foo(a, b):
    x = a + b  # compute x
    y = x * 2  # double
    return y
"""
    # select the two statements that have inline comments
    req = ExtractMethodRequest(
        source=src,
        enclosing_function="foo",
        selection_start_line=2,
        selection_end_line=3,
        new_method_name="extracted",
    )
    plan = build_extraction_plan(req)
    new_src = apply_extraction_to_source(req, plan)

    assert "# compute x" in new_src
    assert "# double" in new_src
