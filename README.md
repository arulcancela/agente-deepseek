# 🤖 Agente DeepSeek — Administrador Autónomo de Linux

Este es un agente administrador autónomo de sistemas Linux potenciado por modelos de DeepSeek. Permite diagnosticar, auditar, configurar y mantener tu sistema interactuando en lenguaje natural.

## 🚀 Características Principales

*   **🔒 Seguridad Reforzada**: Lista negra interna de comandos destructivos y validación automática de comandos encadenados.
*   **🧰 Caja de Herramientas Expandida**:
    *   Ejecución de comandos Linux con timeouts configurables.
    *   Lectura y escritura segura de archivos de configuración.
    *   Búsqueda inteligente de paquetes del sistema (`dpkg` y `apt`).
    *   Extracción estructurada de información del sistema sin ejecuciones manuales.
*   **💾 Historial Persistente**: Carga y continuación de sesiones anteriores guardadas en formato JSON en tu directorio home (`~/.agente_deepseek/historial`).
*   **🎨 Interfaz Enriquecida**: Interfaz de terminal atractiva y profesional usando `rich` con spinners de carga, paneles y tablas.
*   **⚙️ Configuración Flexible**: Configuración mediante archivo JSON (`~/.agente_deepseek/config.json`), variables de entorno y argumentos de línea de comandos.

## 🧪 Tests

```bash
pytest
```

18 tests unitarios del validador de comandos y la configuración. CI con GitHub Actions.

## 📦 Instalación

1.  Asegúrate de estar en el entorno virtual o instálalo en tu entorno global:
    ```bash
    source env/bin/activate  # Si usas venv
    pip install -r requirements.txt
    ```

2.  Configura tu API Key de DeepSeek:
    ```bash
    export DEEPSEEK_API_KEY="tu-api-key-aquí"
    ```

## 🛠️ Uso

### Iniciar el Agente
```bash
python sys_agent.py
```

### Opciones de la Línea de Comandos
*   **Cambiar de modelo**:
    ```bash
    python sys_agent.py --modelo deepseek-chat
    ```
*   **Modo Sandbox (Sin realizar cambios ni ejecutar comandos reales)**:
    ```bash
    python sys_agent.py --sandbox
    ```
*   **Listar sesiones anteriores**:
    ```bash
    python sys_agent.py --sesiones
    ```
*   **Continuar una sesión previa**:
    ```bash
    python sys_agent.py --continuar ultima
    # O por ID específico
    python sys_agent.py --continuar 20260707_171500
    ```
*   **Configurar timeouts**:
    ```bash
    python sys_agent.py --timeout 45
    ```

## ⚙️ Configuración Personalizada
El archivo `~/.agente_deepseek/config.json` se crea automáticamente la primera vez que ejecutas el agente o puedes forzar su creación mediante:
```bash
python sys_agent.py --crear-config
```
Puedes editarlo para añadir comandos a la lista negra personalizada (`comandos_bloqueados`).
