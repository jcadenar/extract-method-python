from refactor_tool.model.refactor_request import ExtractMethodRequest
from refactor_tool.refactor.extract_method import build_extraction_plan, apply_extraction_to_source


def test_preserve_decorator_and_comments():
    src = """
class C:
    @staticmethod  # this is a staticmethod
    def m(x):
        # initial comment
        a = x + 1
        return a
"""

    req = ExtractMethodRequest(
        source=src,
        enclosing_function="m",
        selection_start_line=5,
        selection_end_line=6,
        new_method_name="extracted",
    )
    plan = build_extraction_plan(req)
    new_src = apply_extraction_to_source(req, plan)

    # decorator comment should remain in context and method body comments preserved
    assert "# this is a staticmethod" in new_src
    assert "# initial comment" in new_src
