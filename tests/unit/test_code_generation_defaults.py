from refactor_tool.model.refactor_request import ExtractMethodRequest
from refactor_tool.refactor.extract_method import build_extraction_plan, apply_extraction_to_source


def test_code_generation_preserves_positional_defaults():
    src = """
def foo(a, b=10):
    result = a + b
    return result
"""
    req = ExtractMethodRequest(
        source=src,
        enclosing_function="foo",
        selection_start_line=3,
        selection_end_line=3,
        new_method_name="extracted",
    )
    plan = build_extraction_plan(req)
    new_src = apply_extraction_to_source(req, plan)

    assert "def extracted(a, b=10)" in new_src
    assert "result = extracted(a, b)" in new_src


def test_code_generation_preserves_kwonly_defaults():
    src = """
def foo(a, *, flag=True):
    if flag:
        result = a + 1
    else:
        result = a - 1
    return result
"""
    req = ExtractMethodRequest(
        source=src,
        enclosing_function="foo",
        selection_start_line=3,
        selection_end_line=6,
        new_method_name="extracted",
    )
    plan = build_extraction_plan(req)
    new_src = apply_extraction_to_source(req, plan)

    assert "def extracted(a, *, flag=True)" in new_src
    assert "extracted(a, flag=flag)" in new_src


def test_code_generation_preserves_defaults_varargs_and_kwargs():
    src = """
def foo(a, b=2, *args, **kwargs):
    total = a + b
    if args:
        total += sum(args)
    total += kwargs.get('extra', 0)
    return total
"""
    req = ExtractMethodRequest(
        source=src,
        enclosing_function="foo",
        selection_start_line=3,
        selection_end_line=6,
        new_method_name="extracted",
    )
    plan = build_extraction_plan(req)
    new_src = apply_extraction_to_source(req, plan)

    assert "def extracted(a, b=2, *args, **kwargs)" in new_src
    assert "total = extracted(a, b, *args, **kwargs)" in new_src


def test_code_generation_preserves_global_mutation():
    src = """
COUNTER = 0

def foo():
    global COUNTER
    COUNTER = COUNTER + 1
    return COUNTER
"""
    req = ExtractMethodRequest(
        source=src,
        enclosing_function="foo",
        selection_start_line=5,
        selection_end_line=6,
        new_method_name="extracted",
    )
    plan = build_extraction_plan(req)
    new_src = apply_extraction_to_source(req, plan)

    assert "global COUNTER" in new_src
    assert "COUNTER = COUNTER + 1" in new_src
    assert "extracted()" in new_src
    assert "= extracted()" not in new_src
