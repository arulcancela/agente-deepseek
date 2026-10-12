"""
Cliente API para conectar con DeepSeek.
Implementa reintentos automáticos y manejo de errores.
"""

import time
import sys
from typing import Any, List, Dict
from openai import OpenAI, APIConnectionError, APITimeoutError, RateLimitError
from agente.config import Config


class ClienteDeepSeek:
    """Wrapper sobre el cliente OpenAI para interactuar de forma robusta con DeepSeek."""

    def __init__(self, config: Config):
        self.config = config
        self.client = OpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout_api
        )

    def enviar_mensaje(
        self,
        mensajes: List[Dict[str, Any]],
        herramientas: List[Dict[str, Any]] | None = None
    ) -> Any:
        """
        Envía una lista de mensajes a la API de DeepSeek con reintentos exponenciales.

        Args:
            mensajes: Historial de mensajes de la conversación.
            herramientas: Lista de definiciones de herramientas opcionales.

        Returns:
            La respuesta (message) de la API.
        """
        intentos = 0
        backoff = 2

        while intentos < self.config.reintentos_api:
            try:
                params = {
                    "model": self.config.modelo,
                    "messages": mensajes,
                }
                if herramientas:
                    params["tools"] = herramientas
                    params["tool_choice"] = "auto"

                respuesta = self.client.chat.completions.create(**params)
                return respuesta.choices[0].message

            except RateLimitError as e:
                intentos += 1
                if intentos >= self.config.reintentos_api:
                    print(f"\n❌ Error de límite de velocidad (Rate Limit) persistente: {e}")
                    raise
                print(f"\n⚠️  Límite de velocidad alcanzado. Reintentando en {backoff}s... (Intento {intentos}/{self.config.reintentos_api})")
                time.sleep(backoff)
                backoff *= 2

            except (APIConnectionError, APITimeoutError) as e:
                intentos += 1
                if intentos >= self.config.reintentos_api:
                    print(f"\n❌ Error de conexión o timeout persistente con la API de DeepSeek: {e}")
                    raise
                print(f"\n⚠️  Error de red o timeout. Reintentando en {backoff}s... (Intento {intentos}/{self.config.reintentos_api})")
                time.sleep(backoff)
                backoff *= 2

            except Exception as e:
                print(f"\n❌ Error inesperado en la llamada a la API: {e}")
                raise

        raise RuntimeError("No se pudo obtener respuesta de la API de DeepSeek después de varios intentos.")
