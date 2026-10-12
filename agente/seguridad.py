"""
Módulo de seguridad: validación de comandos y auditoría.
Bloquea comandos peligrosos y registra toda la actividad.
"""

import re
from datetime import datetime
from pathlib import Path


# Patrones de comandos peligrosos (regex)
PATRONES_PELIGROSOS = [
    # Eliminación masiva
    (r"rm\s+(-[a-zA-Z]*f[a-zA-Z]*\s+)?(-[a-zA-Z]*r[a-zA-Z]*\s+)?\s*/\s*$", "Eliminación recursiva de /"),
    (r"rm\s+(-[a-zA-Z]*r[a-zA-Z]*\s+)?(-[a-zA-Z]*f[a-zA-Z]*\s+)?\s*/\s*$", "Eliminación recursiva de /"),
    (r"rm\s+-[a-zA-Z]*rf\s+/\s*$", "Eliminación recursiva forzada de /"),
    (r"rm\s+-[a-zA-Z]*rf\s+/[a-z]+\s*$", "Eliminación de directorio del sistema"),

    # Formateo de disco
    (r"mkfs\.", "Formateo de sistema de archivos"),
    (r"wipefs", "Borrado de firmas de sistema de archivos"),

    # Escritura destructiva en dispositivos
    (r"dd\s+.*if=/dev/(zero|urandom|random).*of=/dev/[sh]d", "Escritura destructiva en disco"),
    (r"dd\s+.*of=/dev/[sh]d", "Escritura directa a disco"),

    # Fork bomb y similares
    (r":\(\)\s*\{\s*:\|:\s*&\s*\}\s*;:", "Fork bomb"),
    (r"\.+/dev/sd", "Escritura a dispositivo de bloque"),

    # Modificación de boot/kernel
    (r"mv\s+.*\s+/boot", "Modificación del directorio boot"),
    (r"rm\s+.*\s+/boot", "Eliminación en directorio boot"),

    # Cambio de permisos peligroso
    (r"chmod\s+(-R\s+)?777\s+/\s*$", "Permisos 777 en /"),
    (r"chmod\s+(-R\s+)?000\s+/", "Eliminación de todos los permisos en /"),
    (r"chown\s+-R\s+.*\s+/\s*$", "Cambio de propietario recursivo en /"),

    # Descarga y ejecución ciega
    (r"curl\s+.*\|\s*(ba)?sh", "Descarga y ejecución ciega de script"),
    (r"wget\s+.*\|\s*(ba)?sh", "Descarga y ejecución ciega de script"),
    (r"curl\s+.*\|\s*python", "Descarga y ejecución ciega de Python"),

    # Modificación de passwd/shadow
    (r">\s*/etc/passwd", "Sobrescritura de /etc/passwd"),
    (r">\s*/etc/shadow", "Sobrescritura de /etc/shadow"),

    # Apagado/reinicio (necesita confirmación especial)
    (r"shutdown\s+(-h\s+)?now", "Apagado inmediato del sistema"),
    (r"reboot\s*$", "Reinicio del sistema"),
    (r"init\s+0", "Apagado del sistema"),
    (r"halt\s*$", "Apagado del sistema"),

    # Iptables flush (puede bloquear acceso)
    (r"iptables\s+-F\s*$", "Flush de todas las reglas de firewall"),
]


def validar_comando(comando: str, comandos_bloqueados_extra: list[str] | None = None) -> tuple[bool, str]:
    """
    Valida si un comando es seguro para ejecutar.

    Args:
        comando: El comando a validar.
        comandos_bloqueados_extra: Lista adicional de patrones bloqueados del config.

    Returns:
        Tupla (es_seguro, razón).
        Si es_seguro es False, razón explica por qué está bloqueado.
    """
    comando_limpio = comando.strip()

    # Verificar contra patrones peligrosos internos
    for patron, descripcion in PATRONES_PELIGROSOS:
        if re.search(patron, comando_limpio):
            return False, f"🚫 BLOQUEADO: {descripcion} — Patrón detectado: '{patron}'"

    # Verificar contra patrones bloqueados del usuario
    if comandos_bloqueados_extra:
        for patron_extra in comandos_bloqueados_extra:
            if re.search(patron_extra, comando_limpio):
                return False, f"🚫 BLOQUEADO por configuración del usuario: Patrón '{patron_extra}'"

    # Verificar si el comando intenta encadenar comandos peligrosos
    # Detectar ; | && || que podrían ocultar comandos
    partes = re.split(r'[;|]|&&|\|\|', comando_limpio)
    if len(partes) > 1:
        for parte in partes:
            parte = parte.strip()
            if parte:
                seguro, razon = validar_comando(parte, comandos_bloqueados_extra)
                if not seguro:
                    return False, f"{razon} (detectado en comando encadenado)"

    return True, "✅ Comando permitido"


def registrar_accion(
    mensaje: str,
    directorio_datos: Path,
    nivel: str = "INFO"
):
    """
    Registra una acción en el archivo de auditoría.

    Args:
        mensaje: Mensaje a registrar.
        directorio_datos: Directorio base de datos del agente.
        nivel: Nivel del log (INFO, WARNING, ERROR, SECURITY).
    """
    archivo_log = directorio_datos / "audit.log"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linea = f"[{timestamp}] [{nivel}] {mensaje}\n"

    try:
        with open(archivo_log, "a", encoding="utf-8") as f:
            f.write(linea)
    except IOError:
        pass  # No fallar si no se puede escribir el log


def registrar_comando(
    comando: str,
    resultado: str,
    autorizado: bool,
    es_cambio: bool,
    directorio_datos: Path
):
    """Registra la ejecución de un comando con su resultado."""
    estado = "AUTORIZADO" if autorizado else "RECHAZADO"
    tipo = "CAMBIO" if es_cambio else "LECTURA"
    # Limitar longitud del resultado en el log
    resultado_corto = resultado[:500] + "..." if len(resultado) > 500 else resultado
    resultado_corto = resultado_corto.replace("\n", " | ")

    registrar_accion(
        f"[{estado}] [{tipo}] Comando: {comando} | Resultado: {resultado_corto}",
        directorio_datos,
        nivel="SECURITY" if es_cambio else "INFO"
    )
