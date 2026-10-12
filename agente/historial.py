"""
Gestión de historial persistente de conversaciones.
Guarda y carga sesiones en formato JSON.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class HistorialManager:
    """Gestiona el historial de sesiones del agente."""

    def __init__(self, directorio_historial: Path):
        """
        Args:
            directorio_historial: Directorio donde guardar las sesiones.
        """
        self.directorio = directorio_historial
        self.directorio.mkdir(parents=True, exist_ok=True)
        self._sesion_actual_id: str | None = None

    @property
    def sesion_actual_id(self) -> str | None:
        return self._sesion_actual_id

    def nueva_sesion_id(self) -> str:
        """Genera un nuevo ID de sesión basado en timestamp."""
        self._sesion_actual_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        return self._sesion_actual_id

    def guardar_sesion(
        self,
        mensajes: list[dict[str, Any]],
        sesion_id: str | None = None,
        resumen: str = ""
    ):
        """
        Guarda una sesión completa en disco.

        Args:
            mensajes: Lista de mensajes de la conversación.
            sesion_id: ID de la sesión. Si None, usa el actual.
            resumen: Resumen breve de la sesión.
        """
        sesion_id = sesion_id or self._sesion_actual_id or self.nueva_sesion_id()

        # Serializar mensajes (limpiar objetos no serializables)
        mensajes_serializables = self._serializar_mensajes(mensajes)

        datos = {
            "id": sesion_id,
            "fecha": datetime.now().isoformat(),
            "num_mensajes": len(mensajes_serializables),
            "resumen": resumen,
            "mensajes": mensajes_serializables,
        }

        ruta = self.directorio / f"sesion_{sesion_id}.json"
        try:
            with open(ruta, "w", encoding="utf-8") as f:
                json.dump(datos, f, indent=2, ensure_ascii=False, default=str)
        except IOError as e:
            print(f"⚠️  No se pudo guardar la sesión: {e}")

    def cargar_sesion(self, sesion_id: str) -> list[dict[str, Any]] | None:
        """
        Carga una sesión desde disco y la sanitiza para garantizar coherencia.

        Args:
            sesion_id: ID de la sesión a cargar.

        Returns:
            Lista de mensajes (sanitizada) o None si no existe.
        """
        ruta = self.directorio / f"sesion_{sesion_id}.json"
        if not ruta.exists():
            return None

        try:
            with open(ruta, "r", encoding="utf-8") as f:
                datos = json.load(f)
            self._sesion_actual_id = sesion_id
            mensajes = datos.get("mensajes", [])
            mensajes, reparados = self._sanitizar_mensajes(mensajes)
            if reparados:
                print(
                    "⚠️  La sesión tenía llamadas a herramientas sin respuesta "
                    "(el agente se interrumpió a mitad de una operación). "
                    "Se han completado automáticamente para reanudar con normalidad."
                )
            return mensajes
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️  No se pudo cargar la sesión {sesion_id}: {e}")
            return None

    def _sanitizar_mensajes(
        self, mensajes: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], bool]:
        """
        Repara secuencias incompletas de tool_calls al final del historial.

        Cuando el agente se interrumpe en mitad de un ciclo de herramientas,
        el historial puede quedar con un mensaje 'assistant' que tiene
        tool_calls pero sin todas (o ninguna) de sus respuestas 'tool'
        correspondientes. La API de DeepSeek rechaza esto con un error 400.

        Estrategia:
          - Para cada mensaje 'assistant' con tool_calls, se comprueba que todos
            sus tool_call_id tengan una respuesta 'tool' posterior.
          - Los tool_call_id sin respuesta reciben un mensaje sintético de error
            que informa al modelo de que la operación fue interrumpida.

        Returns:
            Tupla (mensajes_reparados, hubo_reparacion).
        """
        if not mensajes:
            return mensajes, False

        reparado = False

        # Construir un set de todos los tool_call_id que SÍ tienen respuesta
        tool_ids_con_respuesta: set[str] = set()
        for msg in mensajes:
            if isinstance(msg, dict) and msg.get("role") == "tool":
                tid = msg.get("tool_call_id")
                if tid:
                    tool_ids_con_respuesta.add(tid)

        # Buscar mensajes assistant con tool_calls incompletos y añadir respuestas
        mensajes_extra: list[dict[str, Any]] = []
        for msg in mensajes:
            if not isinstance(msg, dict):
                continue
            if msg.get("role") != "assistant":
                continue
            tool_calls = msg.get("tool_calls")
            if not tool_calls:
                continue

            for tc in tool_calls:
                tid = tc.get("id") if isinstance(tc, dict) else getattr(tc, "id", None)
                nombre = (
                    tc.get("function", {}).get("name", "desconocida")
                    if isinstance(tc, dict)
                    else getattr(getattr(tc, "function", None), "name", "desconocida")
                )
                if tid and tid not in tool_ids_con_respuesta:
                    # Insertar respuesta sintética de cancelación
                    mensajes_extra.append({
                        "role": "tool",
                        "tool_call_id": tid,
                        "name": nombre,
                        "content": (
                            "[OPERACIÓN INTERRUMPIDA] El agente se cerró antes de "
                            "completar esta herramienta. Por favor, retoma la tarea "
                            "desde donde quedó o repite la acción si es necesario."
                        ),
                    })
                    tool_ids_con_respuesta.add(tid)
                    reparado = True

        if mensajes_extra:
            mensajes = list(mensajes) + mensajes_extra

        return mensajes, reparado

    def ultima_sesion(self) -> tuple[str | None, list[dict[str, Any]] | None]:
        """
        Carga la última sesión guardada.

        Returns:
            Tupla (session_id, mensajes) o (None, None) si no hay sesiones.
        """
        sesiones = self.listar_sesiones()
        if not sesiones:
            return None, None

        ultima = sesiones[-1]
        sesion_id = ultima["id"]
        mensajes = self.cargar_sesion(sesion_id)
        return sesion_id, mensajes

    def listar_sesiones(self) -> list[dict[str, Any]]:
        """
        Lista todas las sesiones guardadas.

        Returns:
            Lista de diccionarios con metadatos de cada sesión.
        """
        sesiones = []
        for archivo in sorted(self.directorio.glob("sesion_*.json")):
            try:
                with open(archivo, "r", encoding="utf-8") as f:
                    datos = json.load(f)
                sesiones.append({
                    "id": datos.get("id", archivo.stem),
                    "fecha": datos.get("fecha", "?"),
                    "num_mensajes": datos.get("num_mensajes", 0),
                    "resumen": datos.get("resumen", ""),
                })
            except (json.JSONDecodeError, IOError):
                continue

        return sesiones

    def _serializar_mensajes(self, mensajes: list) -> list[dict]:
        """Convierte mensajes a formato serializable en JSON."""
        resultado = []
        for msg in mensajes:
            if isinstance(msg, dict):
                resultado.append(msg)
            elif hasattr(msg, "model_dump"):
                # Objeto Pydantic (como los de OpenAI SDK)
                resultado.append(msg.model_dump(exclude_none=True))
            elif hasattr(msg, "__dict__"):
                resultado.append({k: v for k, v in msg.__dict__.items() if v is not None})
            else:
                resultado.append({"role": "unknown", "content": str(msg)})
        return resultado

    def generar_resumen(self, mensajes: list[dict]) -> str:
        """Genera un resumen simple de la sesión basado en el primer mensaje del usuario."""
        for msg in mensajes:
            contenido = ""
            if isinstance(msg, dict):
                if msg.get("role") == "user":
                    contenido = msg.get("content", "")
            elif hasattr(msg, "role") and msg.role == "user":
                contenido = getattr(msg, "content", "")

            if contenido:
                # Truncar a 80 caracteres
                return contenido[:80] + ("..." if len(contenido) > 80 else "")

        return "Sesión sin resumen"
