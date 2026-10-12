"""Tests del módulo de configuración (agente/config.py)."""

from __future__ import annotations

import sys

sys.path.insert(0, ".")

from agente.config import Config  # noqa: E402


def test_config_valores_por_defecto() -> None:
    cfg = Config()
    assert cfg.modelo == "deepseek-chat"
    assert cfg.base_url == "https://api.deepseek.com"
    assert cfg.timeout_comando == 30


def test_config_api_key_vacia_por_defecto() -> None:
    """La config NO debe traer una API key hardcodeada."""
    cfg = Config()
    assert cfg.api_key == ""


def test_config_crea_directorio_datos(tmp_path) -> None:
    """Al instanciar, se crean los directorios de datos necesarios."""
    cfg = Config(directorio_datos=tmp_path / "datos_test")
    assert cfg.directorio_datos.exists()
    assert (cfg.directorio_datos / "historial").exists()


def test_config_modo_sandbox_default_false() -> None:
    assert Config().modo_sandbox is False


def test_system_prompt_no_vacio() -> None:
    assert len(Config().system_prompt) > 20
