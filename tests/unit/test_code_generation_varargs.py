from refactor_tool.model.refactor_request import ExtractMethodRequest
from refactor_tool.refactor.extract_method import build_extraction_plan, apply_extraction_to_source


def test_code_generation_varargs():
    src = """
def foo(a, *args, **kwargs):
    print(args)
    total = sum(args)
    extra = kwargs.get('k', 0)
    return total + extra
"""
    # select the middle statements including kwargs usage
    req = ExtractMethodRequest(source=src, enclosing_function="foo", selection_start_line=3, selection_end_line=5, new_method_name="extracted")
    plan = build_extraction_plan(req)
    new_src = apply_extraction_to_source(req, plan)
    assert "def extracted(*args, **kwargs)" in new_src
    assert "extracted(*args, **kwargs)" in new_src
