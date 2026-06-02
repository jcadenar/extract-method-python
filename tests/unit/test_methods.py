from refactor_tool.model.refactor_request import ExtractMethodRequest
from refactor_tool.refactor.extract_method import build_extraction_plan, apply_extraction_to_source


def test_extract_from_instance_method():
    src = """
class C:
    def method(self, x):
        a = self.helper(x)
        b = a + 1
        return b
"""
    req = ExtractMethodRequest(
        source=src,
        enclosing_function="method",
        selection_start_line=4,
        selection_end_line=5,
        new_method_name="extracted",
    )
    plan = build_extraction_plan(req)
    new_src = apply_extraction_to_source(req, plan)

    assert "def extracted(self, x)" in new_src
    assert "b = self.extracted(x)" in new_src
    assert "def method(self, x)" in new_src
