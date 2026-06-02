from refactor_tool.parsing.ast_parser import parse_source, get_function_by_name, find_selected_statement_indices


def test_find_selected_statement_indices_single_statement():
    src = """
def foo(a, b):
    x = a + 1
    y = x + b
    return y
"""
    module = parse_source(src)
    fn = get_function_by_name(module, "foo")
    start, end = find_selected_statement_indices(fn, 3, 3)
    assert (start, end) == (0, 1)
