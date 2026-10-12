"""
Interfaz de terminal enriquecida con Rich.
Paneles, colores, spinners y formateo visual.
"""

from contextlib import contextmanager

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.table import Table
    from rich.markdown import Markdown
    from rich.prompt import Prompt, Confirm
    from rich.spinner import Spinner
    from rich.live import Live
    from rich.rule import Rule
    from rich.theme import Theme
    RICH_DISPONIBLE = True
except ImportError:
    RICH_DISPONIBLE = False


class Interfaz:
    """Interfaz de terminal con rich (con fallback a texto plano)."""

    def __init__(self, usar_rich: bool = True):
        self._usar_rich = usar_rich and RICH_DISPONIBLE
        if self._usar_rich:
            tema = Theme({
                "info": "cyan",
                "warning": "yellow",
                "error": "bold red",
                "success": "bold green",
                "command": "bold magenta",
                "agent": "bold blue",
            })
            self.console = Console(theme=tema)
        else:
            self.console = None

    def bienvenida(self, version: str = "2.0", sandbox: bool = False):
        """Muestra la pantalla de bienvenida."""
        if self._usar_rich:
            titulo = Text("🤖 Agente DeepSeek", style="bold cyan")
            subtitulo = f"Administrador Autónomo de Linux — v{version}"
            if sandbox:
                subtitulo += " [MODO SANDBOX]"
            panel = Panel(
                Text.from_markup(
                    f"[bold]{subtitulo}[/bold]\n\n"
                    f"[dim]Escribe tu solicitud y el agente analizará tu sistema.[/dim]\n"
                    f"[dim]Ejemplos: 'analiza mi sistema', 'optimiza la memoria', 'revisa updates'[/dim]\n"
                    f"[dim]Escribe [bold]'salir'[/bold] para terminar.[/dim]"
                ),
                title=titulo,
                border_style="cyan",
                padding=(1, 2),
            )
            self.console.print()
            self.console.print(panel)
            self.console.print()
        else:
            print(f"\n🤖 Agente DeepSeek v{version}")
            if sandbox:
                print("   ⚠️  MODO SANDBOX — No se ejecutarán comandos")
            print("   Escribe tu solicitud y el agente analizará tu sistema.")
            print("   Ejemplos: 'analiza mi sistema', 'optimiza la memoria', 'revisa updates'")
            print("   Escribe 'salir' para terminar.\n")

    def pedir_input(self, prompt: str = "Tú") -> str:
        """Pide input al usuario."""
        if self._usar_rich:
            return Prompt.ask(f"[bold green]✍️  {prompt}[/bold green]").strip()
        else:
            return input(f"✍️  {prompt}: ").strip()

    def pedir_confirmacion(self, mensaje: str) -> bool:
        """Pide confirmación sí/no al usuario."""
        if self._usar_rich:
            return Confirm.ask(f"[bold yellow]{mensaje}[/bold yellow]")
        else:
            resp = input(f"{mensaje} (s/n): ").strip().lower()
            return resp in ("s", "si", "sí", "y", "yes")

    def respuesta_ia(self, texto: str):
        """Muestra la respuesta del agente IA."""
        if self._usar_rich:
            self.console.print()
            panel = Panel(
                Markdown(texto),
                title="[bold blue]🤖 Agente IA[/bold blue]",
                border_style="blue",
                padding=(1, 2),
            )
            self.console.print(panel)
        else:
            print("\n🤖 ================= AGENTE IA =================")
            print(texto)
            print("================================================")

    def propuesta_comando(self, comando: str, razon: str, es_cambio: bool):
        """Muestra un comando propuesto por la IA."""
        if self._usar_rich:
            estilo = "red" if es_cambio else "cyan"
            icono = "⚠️  CAMBIO EN EL SISTEMA" if es_cambio else "⚙️  Comprobación automática"

            tabla = Table(show_header=False, border_style=estilo, padding=(0, 1))
            tabla.add_column("Campo", style="bold")
            tabla.add_column("Valor")
            tabla.add_row("Tipo", f"[bold {estilo}]{icono}[/bold {estilo}]")
            tabla.add_row("Comando", f"[bold magenta]{comando}[/bold magenta]")
            tabla.add_row("Razón", razon)

            self.console.print()
            self.console.print(Panel(tabla, border_style=estilo))
        else:
            if es_cambio:
                print("\n" + "⚠️ " * 20)
                print(f"🤖 EL AGENTE SOLICITA REALIZAR UN CAMBIO EN EL SISTEMA.")
                print(f"💡 Razón: {razon}")
                print(f"⚡ Comando: {comando}")
                print("⚠️ " * 20)
            else:
                print(f"\n⚙️  [Auto-Comprobación] Ejecutando: {comando}")

    def comando_sandbox(self, comando: str, razon: str):
        """Muestra un comando que se ejecutaría en modo sandbox."""
        if self._usar_rich:
            self.console.print(
                Panel(
                    f"[dim]Se ejecutaría:[/dim] [bold magenta]{comando}[/bold magenta]\n"
                    f"[dim]Razón:[/dim] {razon}",
                    title="[yellow]🏖️  SANDBOX — No ejecutado[/yellow]",
                    border_style="yellow",
                )
            )
        else:
            print(f"\n🏖️  [SANDBOX] Se ejecutaría: {comando}")
            print(f"   Razón: {razon}")

    def resultado_comando(self, resultado: str, exitoso: bool = True):
        """Muestra el resultado de un comando ejecutado."""
        if self._usar_rich:
            estilo = "green" if exitoso else "red"
            icono = "✅" if exitoso else "❌"
            self.console.print(
                Panel(
                    resultado,
                    title=f"{icono} Resultado",
                    border_style=estilo,
                    padding=(0, 1),
                )
            )
        else:
            print(resultado)

    def comando_bloqueado(self, comando: str, razon: str):
        """Muestra que un comando fue bloqueado por seguridad."""
        if self._usar_rich:
            self.console.print(
                Panel(
                    f"[bold red]Comando:[/bold red] {comando}\n"
                    f"[bold red]Razón:[/bold red] {razon}",
                    title="[bold red]🛡️  COMANDO BLOQUEADO POR SEGURIDAD[/bold red]",
                    border_style="red",
                )
            )
        else:
            print(f"\n🛡️  BLOQUEADO: {comando}")
            print(f"   Razón: {razon}")

    def error(self, mensaje: str):
        """Muestra un mensaje de error."""
        if self._usar_rich:
            self.console.print(f"[error]❌ {mensaje}[/error]")
        else:
            print(f"❌ {mensaje}")

    def exito(self, mensaje: str):
        """Muestra un mensaje de éxito."""
        if self._usar_rich:
            self.console.print(f"[success]✅ {mensaje}[/success]")
        else:
            print(f"✅ {mensaje}")

    def info(self, mensaje: str):
        """Muestra un mensaje informativo."""
        if self._usar_rich:
            self.console.print(f"[info]ℹ️  {mensaje}[/info]")
        else:
            print(f"ℹ️  {mensaje}")

    def advertencia(self, mensaje: str):
        """Muestra un mensaje de advertencia."""
        if self._usar_rich:
            self.console.print(f"[warning]⚠️  {mensaje}[/warning]")
        else:
            print(f"⚠️  {mensaje}")

    def procesando(self, mensaje: str = "El agente está procesando..."):
        """Muestra un mensaje de procesamiento."""
        if self._usar_rich:
            self.console.print(f"[dim]🧠 {mensaje}[/dim]")
        else:
            print(f"🧠 {mensaje}")

    @contextmanager
    def spinner(self, mensaje: str = "Pensando..."):
        """Context manager que muestra un spinner animado."""
        if self._usar_rich:
            with Live(
                Panel(
                    Text.from_markup(f"[cyan]{mensaje}[/cyan]"),
                    title="🧠",
                    border_style="dim",
                ),
                console=self.console,
                refresh_per_second=10,
                transient=True,
            ):
                yield
        else:
            print(f"🧠 {mensaje}")
            yield

    def separador(self, texto: str = ""):
        """Muestra una línea separadora."""
        if self._usar_rich:
            self.console.print(Rule(texto, style="dim"))
        else:
            print(f"\n{'─' * 50} {texto}")

    def despedida(self):
        """Muestra el mensaje de despedida."""
        if self._usar_rich:
            self.console.print()
            self.console.print(
                Panel(
                    "[bold]👋 ¡Hasta luego![/bold]\n[dim]Sesión guardada automáticamente.[/dim]",
                    border_style="green",
                )
            )
        else:
            print("\n👋 ¡Hasta luego! Sesión guardada automáticamente.")

    def listar_sesiones(self, sesiones: list[dict]):
        """Muestra una tabla con las sesiones guardadas."""
        if not sesiones:
            self.info("No hay sesiones guardadas.")
            return

        if self._usar_rich:
            tabla = Table(title="📋 Sesiones Guardadas", border_style="cyan")
            tabla.add_column("ID", style="bold")
            tabla.add_column("Fecha", style="cyan")
            tabla.add_column("Mensajes", justify="right")
            tabla.add_column("Resumen", style="dim")

            for s in sesiones:
                tabla.add_row(
                    s.get("id", "?"),
                    s.get("fecha", "?"),
                    str(s.get("num_mensajes", 0)),
                    s.get("resumen", "")[:60],
                )
            self.console.print()
            self.console.print(tabla)
        else:
            print("\n📋 Sesiones Guardadas:")
            for s in sesiones:
                print(f"  [{s.get('id', '?')}] {s.get('fecha', '?')} — {s.get('num_mensajes', 0)} msgs — {s.get('resumen', '')[:60]}")

    def pedir_seleccion_modelo(self, modelo_defecto: str) -> str:
        """Pide al usuario que seleccione qué modelo de DeepSeek desea usar."""
        if not self._usar_rich:
            print("\n🤖 Modelos de DeepSeek disponibles:")
            print(f"  1. deepseek-chat (por defecto)")
            print(f"  2. deepseek-reasoner")
            print(f"  3. Otro modelo (especificar nombre)")
            opcion = input(f"Selecciona un modelo [1]: ").strip()
            if opcion == "2":
                return "deepseek-reasoner"
            elif opcion == "3":
                custom = input("Escribe el nombre del modelo: ").strip()
                return custom if custom else modelo_defecto
            return modelo_defecto

        self.console.print(Panel(
            "[bold cyan]Selecciona el modelo de DeepSeek para esta sesión:[/bold cyan]\n\n"
            "[bold green]1.[/bold green] [bold]deepseek-chat[/bold] (DeepSeek-V3: Rápido, ideal para chat e info general)\n"
            "[bold green]2.[/bold green] [bold]deepseek-reasoner[/bold] (DeepSeek-R1: Razonamiento profundo/Pensamiento)\n"
            "[bold green]3.[/bold green] [dim]Ingresar nombre de modelo personalizado[/dim]",
            border_style="cyan"
        ))
        
        opcion = Prompt.ask("Selecciona una opción", choices=["1", "2", "3"], default="1")
        if opcion == "1":
            return "deepseek-chat"
        elif opcion == "2":
            return "deepseek-reasoner"
        else:
            return Prompt.ask("Introduce el nombre del modelo deseado").strip()

    def pedir_seleccion_sesion(self, sesiones: list[dict], historial_manager) -> tuple[str | None, list[dict] | None]:
        """
        Pregunta al usuario si desea continuar una sesión anterior o iniciar una nueva.
        
        Returns:
            Tupla de (sesion_id, mensajes_cargados) o (None, None) para nueva sesión.
        """
        if not sesiones:
            return None, None

        ultima = sesiones[-1]
        ultima_resumen = ultima.get("resumen", "Sin resumen")
        ultima_fecha = ultima.get("fecha", "Desconocida")
        # Formatear la fecha para hacerla legible
        try:
            if "T" in ultima_fecha:
                ultima_fecha = ultima_fecha.split(".")[0].replace("T", " ")
        except Exception:
            pass

        if not self._usar_rich:
            print(f"\n📋 Se ha encontrado una sesión anterior ({ultima_fecha}):")
            print(f"   Resumen: '{ultima_resumen}'")
            print("\nOpciones:")
            print("  1. Iniciar una nueva conversación (por defecto)")
            print("  2. Continuar con la última conversación")
            print("  3. Listar historial detallado y elegir otra sesión")
            opcion = input("Selecciona una opción [1]: ").strip()
            if opcion == "2":
                return ultima["id"], historial_manager.cargar_sesion(ultima["id"])
            elif opcion == "3":
                self.listar_sesiones(sesiones)
                idx = input("\nIntroduce el ID de la sesión que quieres continuar: ").strip()
                if idx:
                    msg = historial_manager.cargar_sesion(idx)
                    if msg:
                        return idx, msg
                    else:
                        print("❌ No se encontró esa sesión. Iniciando nueva conversación.")
            return None, None

        self.console.print(Panel(
            f"[bold cyan]Se ha detectado una sesión anterior:[/bold cyan]\n"
            f"[dim]Fecha:[/dim] {ultima_fecha}\n"
            f"[dim]Resumen:[/dim] [yellow]{ultima_resumen}[/yellow]\n\n"
            f"[bold green]1.[/bold green] Iniciar una [bold]nueva[/bold] conversación (por defecto)\n"
            f"[bold green]2.[/bold green] Continuar la [bold]última[/bold] conversación\n"
            f"[bold green]3.[/bold green] Ver [bold]todas[/bold] las sesiones anteriores para elegir una",
            border_style="cyan"
        ))

        opcion = Prompt.ask("Selecciona una opción", choices=["1", "2", "3"], default="1")
        if opcion == "1":
            return None, None
        elif opcion == "2":
            return ultima["id"], historial_manager.cargar_sesion(ultima["id"])
        else:
            self.listar_sesiones(sesiones)
            ids_validos = [s["id"] for s in sesiones]
            opciones_id = ids_validos + ["salir"]
            seleccion = Prompt.ask(
                "\nIntroduce el [bold]ID de la sesión[/bold] que deseas continuar (o 'salir')",
                choices=opciones_id,
                default="salir"
            )
            if seleccion == "salir":
                return None, None
            return seleccion, historial_manager.cargar_sesion(seleccion)

    def mostrar_mensaje_historico(self, rol: str, contenido: str):
        """
        Muestra un mensaje del historial formateado y seguro ante problemas de codificación.
        """
        import sys
        nombre = "Tú" if rol == "user" else "Agente"
        color = "green" if rol == "user" else "blue"
        
        if self._usar_rich:
            self.console.print(f"[bold {color}]{nombre}:[/bold {color}] {contenido}")
        else:
            try:
                print(f"{nombre}: {contenido}")
            except UnicodeEncodeError:
                # Fallback seguro codificando y reemplazando caracteres inválidos
                encoding = sys.stdout.encoding or 'utf-8'
                safe_content = contenido.encode(encoding, errors='replace').decode(encoding)
                print(f"{nombre}: {safe_content}")
