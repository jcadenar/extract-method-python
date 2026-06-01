# Refactor Method Tool

Herramienta de refactorización automática para Python 3 enfocada en la operación **Extract Method** usando `ast` y análisis estático.

## Estructura

- `src/refactor_tool/parsing`: análisis y recorrido del AST
- `src/refactor_tool/analysis`: tabla de símbolos, ámbitos y variables vivas
- `src/refactor_tool/refactor`: lógica de extracción y reescritura
- `src/refactor_tool/model`: modelos de datos internos
- `src/refactor_tool/utils`: utilidades compartidas
- `tests/unit`: pruebas unitarias
- `tests/integration`: pruebas de integración
- `examples/input`: ejemplos de entrada
- `examples/expected`: resultados esperados
- `docs`: documentación del proyecto
