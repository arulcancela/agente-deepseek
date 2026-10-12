#!/usr/bin/env python
"""
Punto de entrada principal para el Agente DeepSeek.
Orquesta la configuración, la interfaz de usuario, las herramientas y la seguridad.
"""

import sys
import json
from pathlib import Path

from agente.config import construir_config, Config
from agente.cliente import ClienteDeepSeek
from agente.seguridad import validar_comando, registrar_comando, registrar_accion
from agente.historial import HistorialManager
from agente.interfaz import Interfaz, RICH_DISPONIBLE
from agente.herramientas import DEFINICIONES_HERRAMIENTAS, ejecutar_herramienta


def main():
    # 1. Cargar Configuración e Interfaz
    config = construir_config()
    ui = Interfaz(usar_rich=True)

    # 2. Inicializar Historial
    historial_dir = config.directorio_datos / "historial"
    historial = HistorialManager(historial_dir)

    # Si se pide listar sesiones, mostrar y salir
    if config.continuar_sesion == "sesiones" or getattr(config, "listar_sesiones", False):
        ui.listar_sesiones(historial.listar_sesiones())
        sys.exit(0)

    # Comprobar argumento `--sesiones` procesado por argparse indirectamente
    # (El parser tiene --sesiones como flag booleano. Si se activa, salimos rápido)
    import argparse
    from agente.config import parsear_argumentos
    args = parsear_argumentos()
    if args.sesiones:
        ui.listar_sesiones(historial.listar_sesiones())
        sys.exit(0)

    # 3. Cargar o crear sesión de mensajes
    mensajes = []
    sesion_id = None

    # Seleccionar modelo de forma interactiva si no se especificó en los argumentos
    if "--modelo" not in sys.argv:
        modelo_seleccionado = ui.pedir_seleccion_modelo(config.modelo)
        config.modelo = modelo_seleccionado
        ui.info(f"Modelo configurado para esta sesión: [bold cyan]{config.modelo}[/bold cyan]")

    if config.continuar_sesion:
        if config.continuar_sesion == "ultima":
            sesion_id, mensajes_cargados = historial.ultima_sesion()
            if mensajes_cargados:
                ui.exito(f"Continuando última sesión: {sesion_id}")
                mensajes = mensajes_cargados
            else:
                ui.advertencia("No se encontró ninguna sesión anterior. Iniciando una nueva.")
        else:
            mensajes_cargados = historial.cargar_sesion(config.continuar_sesion)
            if mensajes_cargados:
                sesion_id = config.continuar_sesion
                ui.exito(f"Continuando sesión: {sesion_id}")
                mensajes = mensajes_cargados
            else:
                ui.error(f"No se pudo cargar la sesión '{config.continuar_sesion}'.")
                sys.exit(1)
    elif "--continuar" not in sys.argv and "--sesiones" not in sys.argv:
        sesiones_guardadas = historial.listar_sesiones()
        if sesiones_guardadas:
            sesion_id_elegido, mensajes_cargados = ui.pedir_seleccion_sesion(sesiones_guardadas, historial)
            if mensajes_cargados:
                sesion_id = sesion_id_elegido
                mensajes = mensajes_cargados
                ui.exito(f"Continuando sesión: {sesion_id}")

    if not mensajes:
        sesion_id = historial.nueva_sesion_id()
        mensajes = [
            {"role": "system", "content": config.system_prompt}
        ]

    # 4. Inicializar cliente API
    cliente = ClienteDeepSeek(config)

    # Mostrar pantalla de bienvenida si es nueva sesión o está vacía
    if len(mensajes) <= 1:
        ui.bienvenida(version="2.0", sandbox=config.modo_sandbox)
        primer_mensaje = ui.pedir_input("¿Qué necesitas que haga?")
        while not primer_mensaje:
            ui.advertencia("No has escrito nada. Por favor escribe tu consulta o 'salir' para terminar.")
            primer_mensaje = ui.pedir_input("¿Qué necesitas que haga?")
        if primer_mensaje.lower() in ['salir', 'exit', 'quit']:
            ui.despedida()
            sys.exit(0)
        mensajes.append({"role": "user", "content": primer_mensaje})
    else:
        ui.info(f"Sesión cargada. Total mensajes en historial: {len(mensajes) - 1}")
        # Mostrar el último trozo de conversación si el usuario reanuda
        ui.separador("Últimos mensajes de la conversación")
        for m in mensajes[-3:]:
            rol = m.get("role")
            contenido = m.get("content")
            if (rol == "user" or rol == "assistant") and contenido:
                ui.mostrar_mensaje_historico(rol, contenido)

    # Registrar el inicio en la auditoría
    registrar_accion(
        f"Sesión iniciada. ID: {sesion_id}. Modelo: {config.modelo}. Modo Sandbox: {config.modo_sandbox}",
        config.directorio_datos
    )

    # Bucle interactivo principal
    try:
        while True:
            # Llamar a la API de DeepSeek
            with ui.spinner("El agente está analizando el sistema..."):
                try:
                    mensaje_ia = cliente.enviar_mensaje(mensajes, herramientas=DEFINICIONES_HERRAMIENTAS)
                except Exception as e:
                    ui.error(f"Error al comunicarse con DeepSeek: {e}")
                    # Sanitizar mensajes por si la API falló por desajuste de tool_calls
                    mensajes, _ = historial._sanitizar_mensajes(mensajes)
                    historial.guardar_sesion(mensajes, sesion_id, historial.generar_resumen(mensajes))
                    
                    ui.info("Puedes pulsar ENTER para reintentar, escribir otra consulta o 'salir' para terminar.")
                    respuesta_reintento = ui.pedir_input("Tú (ENTER para reintentar)")
                    if respuesta_reintento.lower() in ['salir', 'exit', 'quit']:
                        break
                    elif respuesta_reintento:
                        mensajes.append({"role": "user", "content": respuesta_reintento})
                    continue

            mensajes.append(mensaje_ia)

            # Caso A: El agente solicita llamar a herramientas
            if mensaje_ia.tool_calls:
                for tool_call in mensaje_ia.tool_calls:
                    nombre_funcion = tool_call.function.name
                    argumentos = json.loads(tool_call.function.arguments)

                    # Procesar logs y auditoría
                    razon = argumentos.get("razon", "Sin razón provista")

                    # Lógica especial de seguridad para comandos de terminal
                    if nombre_funcion == "proponer_comando_linux":
                        comando = argumentos.get("comando", "")
                        es_cambio = argumentos.get("es_cambio", False)

                        # 1. Validar comando contra lista negra
                        es_seguro, razon_seguridad = validar_comando(comando, config.comandos_bloqueados)

                        if not es_seguro:
                            ui.comando_bloqueado(comando, razon_seguridad)
                            registrar_comando(comando, razon_seguridad, autorizado=False, es_cambio=es_cambio, directorio_datos=config.directorio_datos)
                            resultado_tool = razon_seguridad
                        else:
                            # 2. Confirmación o ejecución
                            autorizado = False
                            if config.modo_sandbox:
                                ui.comando_sandbox(comando, razon)
                                resultado_tool = "[SANDBOX] Comando simulado con éxito."
                            else:
                                ui.propuesta_comando(comando, razon, es_cambio)

                                if es_cambio:
                                    autorizado = ui.pedir_confirmacion("¿Autorizas la ejecución de este cambio?")
                                else:
                                    # Auto-comprobación
                                    autorizado = True

                                if autorizado:
                                    # Ejecutar
                                    resultado_tool = ejecutar_herramienta(
                                        nombre_funcion,
                                        argumentos,
                                        timeout_cmd=config.timeout_comando,
                                        max_tamano_archivo=config.max_tamano_archivo
                                    )
                                    ui.resultado_comando(resultado_tool, exitoso="[ERROR]" not in resultado_tool)
                                else:
                                    resultado_tool = "[RECHAZADO POR EL USUARIO] El usuario no autorizó la ejecución de este comando."
                                    ui.error("Ejecución denegada por el usuario.")

                            # Guardar en log de auditoría
                            registrar_comando(comando, resultado_tool, autorizado=autorizado, es_cambio=es_cambio, directorio_datos=config.directorio_datos)

                    # Lógica para otras herramientas (leer_archivo, escribir_archivo, buscar_paquetes, info_sistema)
                    else:
                        # Para escribir archivo, también pedimos confirmación explícita
                        if nombre_funcion == "escribir_archivo":
                            ruta_archivo = argumentos.get("ruta")
                            razon_escritura = argumentos.get("razon", "Sin razón")
                            if config.modo_sandbox:
                                ui.info(f"[SANDBOX] Escribir archivo simulado en: {ruta_archivo}")
                                resultado_tool = "[SANDBOX] Escritura simulada correctamente."
                            else:
                                ui.separador("Escribir archivo")
                                ui.info(f"Ruta: {ruta_archivo}")
                                ui.info(f"Razón: {razon_escritura}")
                                autorizado = ui.pedir_confirmacion(f"¿Autorizas escribir este archivo?")

                                if autorizado:
                                    resultado_tool = ejecutar_herramienta(
                                        nombre_funcion,
                                        argumentos,
                                        timeout_cmd=config.timeout_comando,
                                        max_tamano_archivo=config.max_tamano_archivo
                                    )
                                else:
                                    resultado_tool = "[RECHAZADO POR EL USUARIO] El usuario no autorizó la escritura de este archivo."
                        else:
                            # Otras herramientas de lectura/diagnóstico se ejecutan automáticamente (o simuladas en sandbox)
                            if config.modo_sandbox:
                                resultado_tool = f"[SANDBOX] Simulación de la herramienta {nombre_funcion} con éxito."
                            else:
                                ui.procesando(f"Ejecutando herramienta: {nombre_funcion}...")
                                resultado_tool = ejecutar_herramienta(
                                    nombre_funcion,
                                    argumentos,
                                    timeout_cmd=config.timeout_comando,
                                    max_tamano_archivo=config.max_tamano_archivo
                                )

                    # Agregar respuesta de la herramienta
                    mensajes.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": nombre_funcion,
                        "content": resultado_tool
                    })

                # Guardar sesión en disco tras completar herramientas
                resumen_sesion = historial.generar_resumen(mensajes)
                historial.guardar_sesion(mensajes, sesion_id, resumen_sesion)

            # Caso B: El agente responde conversacionalmente
            else:
                ui.respuesta_ia(mensaje_ia.content)

                # Esperar respuesta del usuario
                respuesta_usuario = ui.pedir_input("Tú (escribe 'salir' para terminar)")

                while not respuesta_usuario:
                    ui.advertencia("No has escrito nada. Escribe tu consulta o 'salir' para terminar.")
                    respuesta_usuario = ui.pedir_input("Tú (escribe 'salir' para terminar)")

                if respuesta_usuario.lower() in ['salir', 'exit', 'quit']:
                    break

                mensajes.append({"role": "user", "content": respuesta_usuario})

                # Guardar sesión en disco
                resumen_sesion = historial.generar_resumen(mensajes)
                historial.guardar_sesion(mensajes, sesion_id, resumen_sesion)

    except KeyboardInterrupt:
        ui.separador()
        ui.info("Interrupción detectada (Ctrl+C). Guardando estado...")
    finally:
        # Guardar sesión de forma defensiva antes de salir
        resumen_sesion = historial.generar_resumen(mensajes)
        historial.guardar_sesion(mensajes, sesion_id, resumen_sesion)
        registrar_accion(f"Sesión finalizada. ID: {sesion_id}", config.directorio_datos)
        ui.despedida()


if __name__ == "__main__":
    main()
