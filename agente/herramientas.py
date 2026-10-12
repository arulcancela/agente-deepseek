"""
Definición e implementación de las herramientas del agente.
"""

import subprocess
import sys
import os
import platform
import shutil
from pathlib import Path
from typing import Any, Dict, List

# Herramientas expuestas para la API de DeepSeek
DEFINICIONES_HERRAMIENTAS = [
    {
        "type": "function",
        "function": {
            "name": "proponer_comando_linux",
            "description": "Ejecuta un comando en la terminal de Linux para diagnosticar, optimizar o solucionar problemas.",
            "parameters": {
                "type": "object",
                "properties": {
                    "comando": {
                        "type": "string",
                        "description": "El comando exacto de Linux a ejecutar."
                    },
                    "razon": {
                        "type": "string",
                        "description": "Explicación detallada de por qué se necesita ejecutar este comando."
                    },
                    "es_cambio": {
                        "type": "boolean",
                        "description": "True si el comando modifica el sistema (instala, borra, altera servicios/configuración). False si es de solo lectura o diagnóstico."
                    }
                },
                "required": ["comando", "razon", "es_cambio"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "leer_archivo",
            "description": "Lee el contenido de un archivo del sistema de forma segura (e.g. configuraciones en /etc, logs).",
            "parameters": {
                "type": "object",
                "properties": {
                    "ruta": {
                        "type": "string",
                        "description": "Ruta absoluta del archivo a leer."
                    },
                    "razon": {
                        "type": "string",
                        "description": "Explicación de por qué necesitas leer este archivo."
                    }
                },
                "required": ["ruta", "razon"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "escribir_archivo",
            "description": "Crea o sobrescribe un archivo (generalmente de configuración). Requiere aprobación del usuario.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ruta": {
                        "type": "string",
                        "description": "Ruta absoluta del archivo a escribir."
                    },
                    "contenido": {
                        "type": "string",
                        "description": "Contenido completo a escribir en el archivo."
                    },
                    "razon": {
                        "type": "string",
                        "description": "Explicación de los cambios que se van a aplicar."
                    }
                },
                "required": ["ruta", "contenido", "razon"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "buscar_paquetes",
            "description": "Busca paquetes de software utilizando apt-cache.",
            "parameters": {
                "type": "object",
                "properties": {
                    "termino": {
                        "type": "string",
                        "description": "Nombre o término de búsqueda del paquete (ej. 'nginx', 'python3')."
                    },
                    "solo_instalados": {
                        "type": "boolean",
                        "description": "Si es True, busca únicamente entre los paquetes ya instalados en el sistema.",
                        "default": False
                    }
                },
                "required": ["termino"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "info_sistema",
            "description": "Obtiene información básica y estructurada del sistema operativo, hardware y recursos sin ejecutar comandos manuales.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    }
]


def ejecutar_comando_sistema(comando: str, timeout: int = 15) -> str:
    """Ejecuta un comando en la terminal de Linux y captura su salida."""
    try:
        resultado = subprocess.run(
            comando,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        if resultado.returncode == 0:
            salida = resultado.stdout if resultado.stdout else "[Comando ejecutado con éxito sin salida de texto]"
            return f"[ÉXITO] Salida:\n{salida}"
        else:
            return f"[ERROR] Código de retorno {resultado.returncode}:\n{resultado.stderr}"
    except subprocess.TimeoutExpired:
        return f"[ERROR]: El comando expiró tras {timeout} segundos."
    except Exception as e:
        return f"[ERROR EXCEPCIÓN]: {str(e)}"


def leer_archivo(ruta: str, max_tamano: int = 50000) -> str:
    """Lee un archivo de forma segura."""
    try:
        path = Path(ruta)
        if not path.exists():
            return f"[ERROR]: El archivo '{ruta}' no existe."
        if not path.is_file():
            return f"[ERROR]: '{ruta}' no es un archivo regular."

        tamano = path.stat().st_size
        if tamano > max_tamano:
            return f"[ERROR]: El archivo es demasiado grande ({tamano} bytes). El límite es de {max_tamano} bytes."

        with open(path, 'r', errors='replace', encoding='utf-8') as f:
            contenido = f.read()
        return f"[ÉXITO] Contenido de {ruta}:\n{contenido}"
    except PermissionError:
        # Intentar leer con sudo si falla por permisos
        return ejecutar_comando_sistema(f"sudo cat '{ruta}'")
    except Exception as e:
        return f"[ERROR EXCEPCIÓN]: {str(e)}"


def escribir_archivo(ruta: str, contenido: str) -> str:
    """Escribe un archivo. Si requiere permisos elevados, lo hace a través de un archivo temporal y sudo mv."""
    try:
        path = Path(ruta)
        # Asegurar que el directorio padre existe
        path.parent.mkdir(parents=True, exist_ok=True)

        # Probar si tenemos permisos de escritura directa
        with open(path, 'w', encoding='utf-8') as f:
            f.write(contenido)
        return f"[ÉXITO]: Archivo escrito correctamente en '{ruta}'"
    except PermissionError:
        # Si falla, escribir a un archivo temporal local y luego moverlo con sudo
        try:
            path = Path(ruta)
            temp_path = Path.home() / ".agente_deepseek" / f"temp_{path.name}"
            temp_path.parent.mkdir(parents=True, exist_ok=True)
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(contenido)

            # Usar sudo para copiar y limpiar el temporal
            cmd = f"sudo mkdir -p '{path.parent}' && sudo cp '{temp_path}' '{ruta}' && rm '{temp_path}'"
            return ejecutar_comando_sistema(cmd)
        except Exception as e:
            return f"[ERROR EXCEPCIÓN AL ESCRIBIR CON SUDO]: {str(e)}"
    except Exception as e:
        return f"[ERROR EXCEPCIÓN]: {str(e)}"


def buscar_paquetes(termino: str, solo_instalados: bool = False) -> str:
    """Busca paquetes en el sistema."""
    if solo_instalados:
        cmd = f"dpkg -l | grep -i '{termino}'"
    else:
        cmd = f"apt-cache search '{termino}' | head -n 40"
    return ejecutar_comando_sistema(cmd)


def obtener_info_sistema() -> str:
    """Obtiene datos estáticos y dinámicos del sistema sin comandos complejos."""
    info = []
    info.append(f"Sistema Operativo: {platform.system()} {platform.release()}")
    info.append(f"Arquitectura: {platform.machine()}")
    info.append(f"Hostname: {platform.node()}")

    # Distribución Linux detallada si está disponible
    if os.path.exists("/etc/os-release"):
        try:
            with open("/etc/os-release", "r") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME="):
                        info.append(f"Distribución: {line.split('=')[1].strip().strip(chr(34))}")
        except Exception:
            pass

    # CPU
    info.append(f"Procesador: {platform.processor() or 'Desconocido'}")

    # Memoria RAM libre/total
    if shutil.which("free"):
        ram_info = ejecutar_comando_sistema("free -h")
        info.append(f"\nUso de Memoria (RAM):\n{ram_info}")

    # Espacio en disco
    total, used, free = shutil.disk_usage("/")
    info.append(f"\nEspacio en Disco (/):\n  Total: {total // (2**30)} GB\n  Usado: {used // (2**30)} GB\n  Libre: {free // (2**30)} GB")

    # Uptime
    if os.path.exists("/proc/uptime"):
        try:
            with open("/proc/uptime", "r") as f:
                uptime_segundos = float(f.readline().split()[0])
                uptime_horas = uptime_segundos / 3600
                info.append(f"Uptime del sistema: {uptime_horas:.2f} horas")
        except Exception:
            pass

    return "\n".join(info)


def ejecutar_herramienta(nombre: str, argumentos: Dict[str, Any], timeout_cmd: int = 30, max_tamano_archivo: int = 50000) -> str:
    """
    Enruta una llamada de herramienta de la IA a la función correspondiente.

    Args:
        nombre: Nombre de la función de la herramienta.
        argumentos: Parámetros provistos por el modelo.
        timeout_cmd: Timeout para comandos de sistema.
        max_tamano_archivo: Límite para lectura de archivos.
    """
    try:
        if nombre == "proponer_comando_linux":
            cmd = argumentos.get("comando")
            return ejecutar_comando_sistema(cmd, timeout=timeout_cmd)

        elif nombre == "leer_archivo":
            ruta = argumentos.get("ruta")
            return leer_archivo(ruta, max_tamano=max_tamano_archivo)

        elif nombre == "escribir_archivo":
            ruta = argumentos.get("ruta")
            contenido = argumentos.get("contenido")
            return escribir_archivo(ruta, contenido)

        elif nombre == "buscar_paquetes":
            termino = argumentos.get("termino")
            solo_inst = argumentos.get("solo_instalados", False)
            return buscar_paquetes(termino, solo_instalados=solo_inst)

        elif nombre == "info_sistema":
            return obtener_info_sistema()

        else:
            return f"[ERROR]: Herramienta '{nombre}' no reconocida."
    except Exception as e:
        return f"[ERROR EN EJECUCIÓN DE HERRAMIENTA {nombre}]: {str(e)}"
