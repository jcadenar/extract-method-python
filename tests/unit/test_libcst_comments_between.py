from refactor_tool.model.refactor_request import ExtractMethodRequest
from refactor_tool.refactor.extract_method import build_extraction_plan, apply_extraction_to_source


def test_preserve_comments_between_statements():
    src = """
def foo(a):
    x = a + 1
    # a lone comment about the next line

    y = x + 2
    return y
"""
    # select covering the assignment, the comment-only line, and the next assignment
    req = ExtractMethodRequest(
        source=src,
        enclosing_function="foo",
        selection_start_line=2,
        selection_end_line=4,
        new_method_name="extracted",
    )
    plan = build_extraction_plan(req)
    new_src = apply_extraction_to_source(req, plan)

    assert "# a lone comment about the next line" in new_src
    assert "y = x + 2" in new_src
