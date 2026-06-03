================================================================================
  EXTRACT METHOD TOOL — Manual de compilación y uso
================================================================================

REQUISITOS
----------
  - Python 3.10 o superior
  - pip


INSTALACIÓN
-----------
Desde la raíz del proyecto, instala el paquete en modo editable:

    pip install -e .

Esto instala automáticamente la dependencia requerida (libcst >= 0.4.15)
y deja disponible el paquete `refactor_tool` para importar desde cualquier
script o test.


EJECUTAR LOS TESTS
------------------
Desde la raíz del proyecto:

    python -m pytest tests/

Para ver detalle de cada test:

    python -m pytest tests/ -v


USO POR LÍNEA DE COMANDOS
--------------------------
El CLI principal actúa sobre un archivo Python completo. Se le indica
la función que contiene el bloque a extraer, el rango de líneas y el
nombre del nuevo método:

    python -m refactor_tool.cli <archivo.py> <funcion> <linea_inicio> <linea_fin> <nuevo_nombre>

Sin flags adicionales, solo muestra el plan (parámetros de entrada,
valores de retorno, número de sentencias) sin modificar ningún archivo.

Flags opcionales:

  --apply          Aplica la extracción y muestra el código resultante
                   por pantalla.

  --apply --inplace
                   Aplica la extracción y sobreescribe el archivo original.

  --apply --output <salida.py>
                   Aplica la extracción y escribe el resultado en el
                   archivo indicado.

Ejemplo con el fichero de muestra incluido en el proyecto:

    # Solo ver el plan
    python -m refactor_tool.cli examples/input/simple.py foo 2 3 nuevo_metodo

    # Aplicar y guardar en otro archivo
    python -m refactor_tool.cli examples/input/simple.py foo 2 3 nuevo_metodo \
        --apply --output resultado.py


EXTRACCIÓN AUTOMÁTICA (sin seleccionar líneas)
----------------------------------------------
El script `scripts/auto_extract_fn.py` divide automáticamente una función
en bloques separados por dos o más líneas en blanco consecutivas y extrae
cada bloque como función helper:

    python scripts/auto_extract_fn.py <archivo.py> <funcion> [--output <salida.py>]

Si no se indica --output, el resultado se escribe en
`<nombre_archivo>_extracted.py` junto al archivo original.

EJEMPLOS:

    python scripts/auto_extract_fn.py tests/test.py procesar_compra_sistema_monolitico

    python scripts/auto_extract_fn.py tests/test.py autenticar_usuario


USO COMO LIBRERÍA
-----------------
Se puede integrar directamente en otros scripts de Python:

    from refactor_tool.model.refactor_request import ExtractMethodRequest
    from refactor_tool.refactor.extract_method import (
        build_extraction_plan,
        apply_extraction_to_source,
    )

    source = open("mi_archivo.py").read()

    request = ExtractMethodRequest(
        source=source,
        enclosing_function="mi_funcion",
        selection_start_line=10,
        selection_end_line=18,
        new_method_name="helper_extraido",
    )

    plan = build_extraction_plan(request)
    print("Parámetros:", plan.input_params)
    print("Retorna:   ", plan.output_values)

    nuevo_codigo = apply_extraction_to_source(request, plan)
    open("mi_archivo_refactorizado.py", "w").write(nuevo_codigo)


ESTRUCTURA DEL PROYECTO
-----------------------
  src/refactor_tool/
    model/          Modelos de datos (ExtractMethodRequest, ExtractionPlan)
    parsing/        Parseo del AST y localización de sentencias
    analysis/       Tabla de símbolos y análisis de flujo de datos
    refactor/       Orquestación y generación del código refactorizado
    cli.py          Punto de entrada por línea de comandos

  scripts/
    auto_extract_fn.py   Extracción automática sin selección manual

  tests/
    unit/           Tests unitarios por módulo
    integration/    Tests de integración contra ejemplos en examples/

  examples/
    input/          Archivos Python de entrada de ejemplo
    expected/       Resultados esperados en formato JSON

================================================================================
