from refactor_tool.model.refactor_request import ExtractMethodRequest
from refactor_tool.refactor.extract_method import build_extraction_plan, apply_extraction_to_source


def test_preserve_comments_in_selection():
    src = """
def foo(a):
    # leading comment
    x = a + 1  # x comment
    # mid comment
    y = x + 2
    return y
"""
    # select from the leading comment line to the y assignment
    req = ExtractMethodRequest(
        source=src,
        enclosing_function="foo",
        selection_start_line=2,
        selection_end_line=5,
        new_method_name="extracted",
    )
    plan = build_extraction_plan(req)
    new_src = apply_extraction_to_source(req, plan)

    # extracted function should contain the comments and trailing comment
    assert "# leading comment" in new_src
    assert "# mid comment" in new_src
    assert "x = a + 1  # x comment" in new_src
