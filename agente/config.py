"""
Gestión de configuración del agente.
Carga desde archivo JSON y argumentos CLI.
"""

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path


DIRECTORIO_DATOS_DEFAULT = Path.home() / ".agente_deepseek"

SYSTEM_PROMPT_DEFAULT = (
    "Eres un agente administrador autónomo para el sistema Linux del usuario. "
    "Tienes acceso a múltiples herramientas para diagnosticar, analizar y solucionar problemas. "
    "Tienes permiso total para ejecutar comandos de lectura y comprobación automáticos (es_cambio=False). "
    "Si necesitas aplicar cambios reales (es_cambio=True), solicita la herramienta y el script pedirá permiso al usuario. "
    "Puedes leer archivos de configuración, obtener información del sistema, y buscar paquetes. "
    "Cuando termines un diagnóstico, conversa con el usuario y pregúntale qué medidas quiere tomar de las sugeridas. "
    "Responde siempre en español. Sé conciso pero completo."
)


@dataclass
class Config:
    """Configuración del agente."""
    modelo: str = "deepseek-chat"
    base_url: str = "https://api.deepseek.com"
    api_key: str = ""
    timeout_comando: int = 30
    timeout_api: int = 120
    reintentos_api: int = 3
    max_tamano_archivo: int = 50_000  # bytes
    log_level: str = "INFO"
    system_prompt: str = SYSTEM_PROMPT_DEFAULT
    directorio_datos: Path = DIRECTORIO_DATOS_DEFAULT
    comandos_bloqueados: list[str] = field(default_factory=list)
    continuar_sesion: str | None = None
    modo_sandbox: bool = False

    def __post_init__(self):
        """Convierte strings a Path y crea directorios necesarios."""
        if isinstance(self.directorio_datos, str):
            self.directorio_datos = Path(self.directorio_datos)

        # Crear directorios necesarios
        self.directorio_datos.mkdir(parents=True, exist_ok=True)
        (self.directorio_datos / "historial").mkdir(exist_ok=True)


def cargar_config_archivo(ruta: Path | None = None) -> dict:
    """Carga configuración desde el archivo JSON."""
    ruta = ruta or (DIRECTORIO_DATOS_DEFAULT / "config.json")
    if ruta.exists():
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️  Advertencia: No se pudo leer {ruta}: {e}")
    return {}


def crear_config_ejemplo():
    """Crea un archivo de configuración de ejemplo si no existe."""
    ruta = DIRECTORIO_DATOS_DEFAULT / "config.json"
    if not ruta.exists():
        DIRECTORIO_DATOS_DEFAULT.mkdir(parents=True, exist_ok=True)
        ejemplo = {
            "modelo": "deepseek-chat",
            "base_url": "https://api.deepseek.com",
            "timeout_comando": 30,
            "timeout_api": 120,
            "reintentos_api": 3,
            "max_tamano_archivo": 50000,
            "log_level": "INFO",
            "comandos_bloqueados": [],
            "modo_sandbox": False
        }
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(ejemplo, f, indent=2, ensure_ascii=False)


def parsear_argumentos() -> argparse.Namespace:
    """Parsea argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(
        description="🤖 Agente DeepSeek — Administrador autónomo de Linux",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Ejemplos:\n"
            "  python sys_agent.py                          # Iniciar agente\n"
            "  python sys_agent.py --modelo deepseek-chat   # Usar modelo específico\n"
            "  python sys_agent.py --continuar ultima       # Continuar última sesión\n"
            "  python sys_agent.py --sandbox                # Modo sandbox (sin ejecutar)\n"
            "  python sys_agent.py --sesiones               # Listar sesiones anteriores\n"
        )
    )
    parser.add_argument("--modelo", type=str, help="Modelo de DeepSeek a usar")
    parser.add_argument("--timeout", type=int, help="Timeout para comandos (segundos)")
    parser.add_argument("--sandbox", action="store_true", help="Modo sandbox: muestra comandos sin ejecutar")
    parser.add_argument("--continuar", type=str, nargs="?", const="ultima",
                        help="Continuar una sesión anterior (ID o 'ultima')")
    parser.add_argument("--sesiones", action="store_true", help="Listar sesiones guardadas")
    parser.add_argument("--config", type=str, help="Ruta a archivo de configuración alternativo")
    parser.add_argument("--crear-config", action="store_true",
                        help="Crear archivo de configuración de ejemplo")
    return parser.parse_args()


def construir_config() -> Config:
    """Construye la configuración final combinando archivo + CLI + env."""
    args = parsear_argumentos()

    # Crear config ejemplo si se pide
    if args.crear_config:
        crear_config_ejemplo()
        print(f"✅ Archivo de configuración creado en: {DIRECTORIO_DATOS_DEFAULT / 'config.json'}")
        sys.exit(0)

    # 1. Cargar desde archivo
    ruta_config = Path(args.config) if args.config else None
    datos_archivo = cargar_config_archivo(ruta_config)

    # 2. Verificar API key
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        print("❌ Error: La variable de entorno DEEPSEEK_API_KEY no está configurada.")
        print("   Ejecuta: export DEEPSEEK_API_KEY='tu-clave-aquí'")
        sys.exit(1)

    # 3. Construir config (prioridad: CLI > archivo > default)
    config = Config(
        api_key=api_key,
        modelo=args.modelo or datos_archivo.get("modelo", Config.modelo),
        base_url=datos_archivo.get("base_url", Config.base_url),
        timeout_comando=args.timeout or datos_archivo.get("timeout_comando", Config.timeout_comando),
        timeout_api=datos_archivo.get("timeout_api", Config.timeout_api),
        reintentos_api=datos_archivo.get("reintentos_api", Config.reintentos_api),
        max_tamano_archivo=datos_archivo.get("max_tamano_archivo", Config.max_tamano_archivo),
        log_level=datos_archivo.get("log_level", Config.log_level),
        system_prompt=datos_archivo.get("system_prompt", SYSTEM_PROMPT_DEFAULT),
        comandos_bloqueados=datos_archivo.get("comandos_bloqueados", []),
        continuar_sesion=args.continuar,
        modo_sandbox=args.sandbox or datos_archivo.get("modo_sandbox", False),
    )

    return config
