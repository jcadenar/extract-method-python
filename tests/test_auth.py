def autenticar_usuario(username, password, ip_origen, recurso_solicitado):
    """
    Pipeline monolítico de autenticación de usuario.
    Valida credenciales, verifica permisos, registra el acceso
    y genera un token de sesión firmado.

    IDEAL PARA PROBAR EXTRACT METHOD CON AST.
    """
    print(f"--- Iniciando autenticación para '{username}' desde {ip_origen} ---")

    # Validar formato de credenciales
    if not username or not isinstance(username, str):
        raise ValueError("El nombre de usuario no puede estar vacío.")
    if len(password) < 6:
        raise ValueError("La contraseña debe tener al menos 6 caracteres.")
    ips_bloqueadas = ["192.168.0.99", "10.0.0.5"]
    if ip_origen in ips_bloqueadas:
        raise PermissionError(f"La IP {ip_origen} está bloqueada.")
    print("Formato de credenciales válido.")


    # Verificar credenciales contra base de datos simulada
    usuarios_db = {
        "admin":    {"password": "admin123", "rol": "administrador"},
        "juancho":  {"password": "juancho456", "rol": "editor"},
        "invitado": {"password": "guest000", "rol": "lector"},
    }
    if username not in usuarios_db:
        raise PermissionError(f"Usuario '{username}' no encontrado.")
    if usuarios_db[username]["password"] != password:
        raise PermissionError("Contraseña incorrecta.")
    rol = usuarios_db[username]["rol"]
    print(f"Credenciales verificadas. Rol asignado: {rol}")


    # Verificar permisos sobre el recurso solicitado
    permisos = {
        "administrador": ["leer", "escribir", "eliminar", "configurar"],
        "editor":        ["leer", "escribir"],
        "lector":        ["leer"],
    }
    acciones_recurso = {
        "dashboard":    "leer",
        "reportes":     "leer",
        "articulos":    "escribir",
        "configuracion":"configurar",
        "papelera":     "eliminar",
    }
    if recurso_solicitado not in acciones_recurso:
        raise ValueError(f"Recurso '{recurso_solicitado}' no reconocido.")
    accion_requerida = acciones_recurso[recurso_solicitado]
    if accion_requerida not in permisos[rol]:
        raise PermissionError(
            f"El rol '{rol}' no tiene permiso para '{accion_requerida}' en '{recurso_solicitado}'."
        )
    print(f"Permiso concedido: '{accion_requerida}' sobre '{recurso_solicitado}'.")


    # Registrar el acceso en el log de auditoría
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entrada_log = (
        f"[{timestamp}] LOGIN OK | usuario={username} | rol={rol} "
        f"| ip={ip_origen} | recurso={recurso_solicitado}"
    )
    log_auditoria = []
    log_auditoria.append(entrada_log)
    print(f"Acceso registrado en auditoría: {entrada_log}")


    # Generar token de sesión
    import hashlib
    raw_token = f"{username}:{rol}:{ip_origen}:{timestamp}"
    token = hashlib.sha256(raw_token.encode()).hexdigest()
    sesion = {
        "token": token,
        "username": username,
        "rol": rol,
        "ip": ip_origen,
        "recurso": recurso_solicitado,
        "expira_en": "3600s",
    }
    print(f"Token de sesión generado: {token[:16]}...")
    print("--- Autenticación completada exitosamente ---")
    return sesion


# =====================================================================
# Datos de prueba para ejecutar el script antes de pasarlo por tu AST
# =====================================================================
if __name__ == "__main__":
    resultado = autenticar_usuario(
        username="juancho",
        password="juancho456",
        ip_origen="192.168.1.10",
        recurso_solicitado="articulos",
    )
    print("\nSesión generada:")
    for k, v in resultado.items():
        print(f"  {k}: {v}")