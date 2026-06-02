def procesar_compra_sistema_monolitico(carrito, usuario_id, cupon_descuento=None):
    """
    Función monolítica que hace de todo: valida stock, calcula precios,
    aplica descuentos, procesa el pago simulado y genera un ticket.
    
    IDEAL PARA PROBAR EXTRACT METHOD CON AST.
    """
    print(f"--- Iniciando procesamiento de compra para usuario {usuario_id} ---")
    
    print("Validando disponibilidad de productos...")
    inventario_simulado = {"laptop": 5, "mouse": 10, "teclado": 0}
    
    for item in carrito:
        producto = item["producto"]
        cantidad = item["cantidad"]
        if producto not in inventario_simulado:
            raise ValueError(f"El producto {producto} no existe en el catálogo.")
        if inventario_simulado[producto] < cantidad:
            raise ValueError(f"Stock insuficiente para {producto}. Disponibles: {inventario_simulado[producto]}")
    print("Stock verificado con éxito.")


    print("Calculando costos...")
    subtotal = 0.0
    for item in carrito:
        # Asumiendo precio fijo para la simulación
        precio_unitario = 100.0 if item["producto"] == "mouse" else 800.0
        subtotal += precio_unitario * item["cantidad"]
    
    descuento = 0.0
    if cupon_descuento == "PROMO2026":
        descuento = subtotal * 0.15
        print(f"Cupón aplicado. Descuento: -${descuento}")
    elif cupon_descuento == "BIENVENIDO":
        descuento = 10.0
        print(f"Cupón aplicado. Descuento: -${descuento}")
        
    impuesto = (subtotal - descuento) * 0.16
    total_final = subtotal - descuento + impuesto


    print(f"Conectando con la pasarela de pago para cobrar ${total_final:.2f}...")
    # Simulación de lógica de negocio/comunicación
    if total_final <= 0:
        transaccion_exitosa = False
        codigo_autorizacion = None
    else:
        # Simula una aprobación bancaria exitosa
        transaccion_exitosa = True
        codigo_autorizacion = f"AUTH-{usuario_id}-99"
        print(f"Pago aprobado. Transacción: {codigo_autorizacion}")


    print("Generando comprobante de pago...")
    lineas_recibo = [
        f"=== TICKET DE COMPRA ===",
        f"Cliente ID: {usuario_id}",
        f"Código de Autorización: {codigo_autorizacion}",
        "Detalle de Productos:"
    ]
    for item in carrito:
        lineas_recibo.append(f" - {item['producto']} x{item['cantidad']}")
    lineas_recibo.append(f"TOTAL PAGADO: ${total_final:.2f}")
    lineas_recibo.append("=======================")
    
    recibo_str = "\n".join(lineas_recibo)
    
    # Fin del método monolítico
    print("--- Proceso completado exitosamente ---")
    return recibo_str


# =====================================================================
# Datos de prueba para ejecutar el script antes de pasarlo por tu AST
# =====================================================================
if __name__ == "__main__":
    mi_carrito = [
        {"producto": "mouse", "cantidad": 2},
        {"producto": "laptop", "cantidad": 1}
    ]
    
    # Prueba que el código original funcione perfectamente
    resultado = procesar_compra_sistema_monolitico(mi_carrito, usuario_id=1024, cupon_descuento="PROMO2026")
    print("\nResultado devuelto por la función:")
    print(resultado)