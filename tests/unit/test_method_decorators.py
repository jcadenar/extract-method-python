from refactor_tool.model.refactor_request import ExtractMethodRequest
from refactor_tool.refactor.extract_method import build_extraction_plan, apply_extraction_to_source


def test_extract_from_classmethod():
    src = """
class C:
    @classmethod
    def method(cls, x):
        a = cls.helper(x)
        b = a + 1
        return b
"""
    req = ExtractMethodRequest(
        source=src,
        enclosing_function="method",
        selection_start_line=5,
        selection_end_line=6,
        new_method_name="extracted",
    )
    plan = build_extraction_plan(req)
    new_src = apply_extraction_to_source(req, plan)

    assert "@classmethod" in new_src
    assert "def extracted(cls, x)" in new_src
    assert "b = cls.extracted(x)" in new_src


def test_extract_from_staticmethod():
    src = """
class C:
    @staticmethod
    def method(x):
        a = helper(x)
        return a
"""
    req = ExtractMethodRequest(
        source=src,
        enclosing_function="method",
        selection_start_line=5,
        selection_end_line=5,
        new_method_name="extracted",
    )
    plan = build_extraction_plan(req)
    new_src = apply_extraction_to_source(req, plan)

    assert "@staticmethod" in new_src
    # staticmethod inside class should be inserted and called via class name
    assert "def extracted(x)" in new_src
    assert "a = C.extracted(x)" in new_src
