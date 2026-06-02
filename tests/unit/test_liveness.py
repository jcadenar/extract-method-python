import ast

from refactor_tool.parsing.ast_parser import parse_source, get_function_by_name, find_selected_statement_indices
from refactor_tool.analysis.liveness import infer_inputs_outputs


def test_infer_inputs_outputs_simple():
    src = """
def foo(a, b):
    x = a + 1
    y = x + b
    return y
"""
    module = parse_source(src)
    fn = get_function_by_name(module, "foo")
    start, end = find_selected_statement_indices(fn, 3, 4)
    inputs, outputs, selected = infer_inputs_outputs(module, fn, start, end)
    assert inputs == ["a", "b"]
    assert outputs == ["y"]


def test_infer_inputs_outputs_ignores_module_globals_and_builtins():
    src = """
VALUE = 10

def foo(x):
    total = sum([x, VALUE])
    return total
"""
    module = parse_source(src)
    fn = get_function_by_name(module, "foo")
    start, end = find_selected_statement_indices(fn, 5, 5)
    inputs, outputs, selected = infer_inputs_outputs(module, fn, start, end)

    assert inputs == ["x"]
    assert outputs == ["total"]


def test_infer_inputs_outputs_ignores_global_directive_and_assignment():
    src = """
COUNTER = 0

def foo():
    global COUNTER
    COUNTER = COUNTER + 1
    return COUNTER
"""
    module = parse_source(src)
    fn = get_function_by_name(module, "foo")
    start, end = find_selected_statement_indices(fn, 5, 6)
    inputs, outputs, selected = infer_inputs_outputs(module, fn, start, end)

    assert inputs == []
    assert outputs == []


def test_infer_inputs_outputs_ignores_nonlocal_directive_and_assignment():
    src = """
def outer():
    x = 0

    def foo():
        nonlocal x
        x = x + 1
        return x

    return foo
"""
    module = parse_source(src)
    fn = next(
        node
        for node in ast.walk(module)
        if isinstance(node, ast.FunctionDef) and node.name == "foo"
    )
    start, end = find_selected_statement_indices(fn, 5, 6)
    inputs, outputs, selected = infer_inputs_outputs(module, fn, start, end)

    assert inputs == []
    assert outputs == []
