"""
Code generator for Pocket Option client
Version: 2.0.0
"""

import json
import logging
import pathlib
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional
from datetime import datetime

import jinja2
import pydantic
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint

# Add path
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent))

console = Console()
logger = logging.getLogger(__name__)


class Method(pydantic.BaseModel):
    """Method definition"""
    name: str
    event: str
    doc: Optional[str] = None
    return_type: Optional[str] = None
    pydantic_model: Optional[str] = None
    args: Optional[Dict[str, Any]] = None


class EventsData(pydantic.BaseModel):
    """Events data structure"""
    imports: List[str] = []  # List of additional imports
    on: List[Method]
    emit: List[Method]


class TemplateRenderer:
    """Template renderer using Jinja2"""
    
    def __init__(self, template_dir: pathlib.Path):
        self.template_dir = template_dir
        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_dir),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
            autoescape=False
        )
        
        # Add custom filters
        self.env.filters['indent'] = self.indent_filter
    
    def indent_filter(self, text: str, width: int = 4) -> str:
        """Indent text by specified width"""
        if not text:
            return text
        indent = ' ' * width
        return '\n'.join(indent + line if line.strip() else line for line in text.split('\n'))
    
    def render(self, template_name: str, **kwargs) -> str:
        """Render a template"""
        try:
            template = self.env.get_template(template_name)
            return template.render(**kwargs)
        except Exception as e:
            logger.error(f"Error rendering template {template_name}: {e}")
            raise
    
    def render_string(self, template_string: str, **kwargs) -> str:
        """Render a template string"""
        try:
            template = self.env.from_string(template_string)
            return template.render(**kwargs)
        except Exception as e:
            logger.error(f"Error rendering string: {e}")
            raise


class CodeGenerator:
    """Main code generator"""
    
    def __init__(self):
        self.base_dir = pathlib.Path(__file__).parent
        self.templates_dir = self.base_dir / "templates"
        self.output_dir = self.base_dir.parent  # pocket_trader folder
        
        # Create folders
        self.templates_dir.mkdir(exist_ok=True)
        
        self.renderer = TemplateRenderer(self.templates_dir)
        self.start_time = time.time()
    
    def load_events(self) -> EventsData:
        """Load events from JSON"""
        events_file = self.base_dir / "events.json"
        
        if not events_file.exists():
            events_file = self.templates_dir / "events.json"
        
        logger.info(f"📂 Loading events from {events_file}")
        
        try:
            with open(events_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Ensure imports list exists
            if 'imports' not in data:
                data['imports'] = [
                    "from pocket_trader.types import TypedEventListener"
                ]
            
            # Convert lists to Method objects
            for method in data.get('on', []):
                if 'doc' not in method:
                    method['doc'] = f"Handle {method['name']} event"
                if 'return_type' not in method:
                    method['return_type'] = 'Any'
                if 'pydantic_model' not in method:
                    method['pydantic_model'] = 'null'
            
            for method in data.get('emit', []):
                if 'doc' not in method:
                    method['doc'] = f"Emit {method['name']} event"
            
            # Validate the data
            validated_data = EventsData.model_validate(data)
            
            logger.info(f"✅ Found {len(validated_data.on)} on events and {len(validated_data.emit)} emit events")
            return validated_data
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON in events file: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Error loading events: {e}")
            raise
    
    def generate_client(self, data: EventsData) -> str:
        """Generate client code using templates"""
        logger.info("🔄 Generating client code...")
        
        # Create templates if they don't exist
        self._ensure_templates()
        
        try:
            # Prepare data
            context = {
                'imports': data.imports,
                'on_methods': data.on,
                'emit_methods': data.emit,
                'generated_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'version': '2.0.0'
            }
            
            # Generate code using layout.jinja2
            code = self.renderer.render('layout.jinja2', **context)
            
            logger.info(f"✅ Generated {len(data.on)} on methods and {len(data.emit)} emit methods")
            return code
            
        except Exception as e:
            logger.error(f"❌ Error generating client: {e}")
            # Fallback to manual generation if templates fail
            logger.info("⚠️ Falling back to manual generation...")
            return self._generate_client_manual(data)
    
    def _ensure_templates(self):
        """Create template files if they don't exist"""
        
        # layout.jinja2
        layout_file = self.templates_dir / "layout.jinja2"
        if not layout_file.exists():
            layout_content = '''"""
Generated Pocket Option client
DO NOT EDIT - This file is auto-generated
Generated on: {{ generated_date }}
Version: {{ version }}
"""

import typing
from typing import Optional, Callable, Awaitable

from pocket_trader import models
from pocket_trader.client import BasePocketOptionClient

{% for import_stmt in imports %}
{{ import_stmt }}
{% endfor %}

if typing.TYPE_CHECKING:
    from pocket_trader.types import TypedEventListener

__all__ = ("PocketOptionClient",)


class PocketOptionClientEmit:
    """Emit methods for Pocket Option client"""

    def __init__(self, client: BasePocketOptionClient) -> None:
        self.client = client

{% for method in emit_methods %}
    async def {{ method.name }}(self{% if method.args %}, {{ method.args.name }}: {{ method.args.type }}{% endif %}):
        """{{ method.doc }}"""
        {% if method.args %}
        await self.client.send("{{ method.event }}", {{ method.args.name }})
        {% else %}
        await self.client.send("{{ method.event }}")
        {% endif %}

{% endfor %}

class PocketOptionClientOn:
    """Event handlers for Pocket Option client"""

    def __init__(self, client: BasePocketOptionClient) -> None:
        self.client = client

{% for method in on_methods %}
    @typing.overload
    def {{ method.name }}(self, handler: None = None) -> Callable[[TypedEventListener[{{ method.return_type }}]], None]:
        """Overload for decorator usage"""
        ...

    @typing.overload
    def {{ method.name }}(self, handler: TypedEventListener[{{ method.return_type }}]) -> None:
        """Overload for direct callback"""
        ...

    def {{ method.name }}(self, handler: Optional[TypedEventListener[{{ method.return_type }}]] = None) -> Optional[Callable[[TypedEventListener[{{ method.return_type }}]], None]]:
        """{{ method.doc }}
        
        Args:
            handler: Async or sync callback function
        
        Returns:
            Decorator function if handler is None, otherwise None
        
        Example:
            @client.on.{{ method.name }}
            async def handler(data: {{ method.return_type }}):
                print(data)
        """
        return self.client.add_on(
            "{{ method.event }}",
            handler=handler,
            model={% if method.pydantic_model and method.pydantic_model != "null" %}{{ method.pydantic_model }}{% else %}None{% endif %}
        )

{% endfor %}
class PocketOptionClient(BasePocketOptionClient):
    """Complete Pocket Option client
    
    This is the main client class that combines all functionality.
    Use `on` for event handlers and `emit` for sending events.
    
    Example:
        client = PocketOptionClient()
        await client.connect("wss://api-eu.po.market")
        
        @client.on.update_balance
        async def handle_balance(data):
            print(f"Balance: {data.balance}")
            
        await client.emit.auth(auth_data)
    """

    @property
    def on(self) -> PocketOptionClientOn:
        """Get event handlers namespace"""
        return PocketOptionClientOn(self)

    @property
    def emit(self) -> PocketOptionClientEmit:
        """Get emit methods namespace"""
        return PocketOptionClientEmit(self)
'''
            layout_file.write_text(layout_content, encoding='utf-8')
            logger.info(f"✅ Created template: {layout_file}")
    
    def _generate_client_manual(self, data: EventsData) -> str:
        """Fallback manual generation"""
        lines = []
        
        # Header
        lines.append('"""')
        lines.append('Generated Pocket Option client')
        lines.append('DO NOT EDIT - This file is auto-generated')
        lines.append(f'Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        lines.append('Version: 2.0.0')
        lines.append('"""')
        lines.append('')
        
        # Imports
        lines.append('import typing')
        lines.append('from typing import Optional, Callable, Awaitable, Any')
        lines.append('')
        lines.append('from pocket_trader import models')
        lines.append('from pocket_trader.client import BasePocketOptionClient')
        lines.append('from pocket_trader.types import TypedEventListener')
        lines.append('')
        lines.append('if typing.TYPE_CHECKING:')
        lines.append('    from pocket_trader.types import TypedEventListener')
        lines.append('')
        lines.append('__all__ = ("PocketOptionClient",)')
        lines.append('')
        
        # Emit class
        lines.append('')
        lines.append('class PocketOptionClientEmit:')
        lines.append('    """Emit methods for Pocket Option client"""')
        lines.append('')
        lines.append('    def __init__(self, client: BasePocketOptionClient) -> None:')
        lines.append('        self.client = client')
        lines.append('')
        
        for method in data.emit:
            args_part = f', {method.args["name"]}: {method.args["type"]}' if method.args else ''
            lines.append(f'    async def {method.name}(self{args_part}):')
            lines.append(f'        """{method.doc or "No description"}"""')
            if method.args:
                lines.append(f'        await self.client.send("{method.event}", {method.args["name"]})')
            else:
                lines.append(f'        await self.client.send("{method.event}")')
            lines.append('')
        
        # On class
        lines.append('')
        lines.append('class PocketOptionClientOn:')
        lines.append('    """Event handlers for Pocket Option client"""')
        lines.append('')
        lines.append('    def __init__(self, client: BasePocketOptionClient) -> None:')
        lines.append('        self.client = client')
        lines.append('')
        
        for method in data.on:
            return_type = method.return_type or 'Any'
            model = method.pydantic_model if method.pydantic_model and method.pydantic_model != 'null' else 'None'
            
            lines.append(f'    @typing.overload')
            lines.append(f'    def {method.name}(self, handler: None = None) -> Callable[[TypedEventListener[{return_type}]], None]: ...')
            lines.append(f'')
            lines.append(f'    @typing.overload')
            lines.append(f'    def {method.name}(self, handler: TypedEventListener[{return_type}]) -> None: ...')
            lines.append(f'')
            lines.append(f'    def {method.name}(self, handler: Optional[TypedEventListener[{return_type}]] = None) -> Optional[Callable[[TypedEventListener[{return_type}]], None]]:')
            lines.append(f'        """{method.doc or "No description"}"""')
            lines.append(f'        return self.client.add_on(')
            lines.append(f'            "{method.event}",')
            lines.append(f'            handler=handler,')
            lines.append(f'            model={model}')
            lines.append(f'        )')
            lines.append('')
        
        # Main client
        lines.append('')
        lines.append('class PocketOptionClient(BasePocketOptionClient):')
        lines.append('    """Complete Pocket Option client"""')
        lines.append('')
        lines.append('    @property')
        lines.append('    def on(self) -> PocketOptionClientOn:')
        lines.append('        """Get event handlers namespace"""')
        lines.append('        return PocketOptionClientOn(self)')
        lines.append('')
        lines.append('    @property')
        lines.append('    def emit(self) -> PocketOptionClientEmit:')
        lines.append('        """Get emit methods namespace"""')
        lines.append('        return PocketOptionClientEmit(self)')
        lines.append('')
        
        return '\n'.join(lines)
    
    def save_code(self, code: str) -> pathlib.Path:
        """Save generated code"""
        output_file = self.output_dir / "generated_client.py"
        
        # Backup existing
        if output_file.exists():
            backup = output_file.with_suffix('.py.bak')
            output_file.rename(backup)
            logger.info(f"📦 Backup saved to {backup}")
        
        output_file.write_text(code, encoding='utf-8')
        logger.info(f"💾 Generated client saved to {output_file}")
        
        return output_file
    
    def format_code(self, file_path: pathlib.Path):
        """Format code with ruff or black"""
        logger.info("🎨 Formatting code...")
        
        try:
            # Try black first
            try:
                result = subprocess.run(
                    ["black", str(file_path)], 
                    capture_output=True, 
                    text=True,
                    check=False
                )
                if result.returncode == 0:
                    logger.info("✅ Code formatted with black")
                else:
                    logger.warning(f"⚠️ Black formatting issue: {result.stderr}")
            except FileNotFoundError:
                # Fallback to ruff
                try:
                    result = subprocess.run(
                        ["ruff", "format", str(file_path), "--silent"],
                        capture_output=True,
                        text=True,
                        check=False
                    )
                    if result.returncode == 0:
                        logger.info("✅ Code formatted with ruff")
                    else:
                        logger.warning(f"⚠️ Ruff formatting issue: {result.stderr}")
                except FileNotFoundError:
                    logger.warning("⚠️ No formatter found (install black or ruff)")
        except Exception as e:
            logger.warning(f"⚠️ Formatting skipped: {e}")
    
    def print_summary(self, data: EventsData, output: pathlib.Path):
        """Print generation summary"""
        elapsed = time.time() - self.start_time
        
        # Create summary table
        table = Table(title="📊 Generation Summary", show_header=True, header_style="bold magenta")
        table.add_column("Type", style="cyan")
        table.add_column("Count", justify="right", style="green")
        table.add_column("Description")
        
        table.add_row("On Events", str(len(data.on)), "Event handlers")
        table.add_row("Emit Events", str(len(data.emit)), "Emit methods")
        table.add_row("Total", str(len(data.on) + len(data.emit)), "Total methods")
        table.add_row("Imports", str(len(data.imports)), "Additional imports")
        
        # Print summary
        console.print()
        console.print(Panel(
            table, 
            title="[bold blue]Pocket Option Generator[/bold blue]", 
            border_style="blue",
            padding=(1, 2)
        ))
        
        # Print file info
        file_size = output.stat().st_size
        console.print(f"\n[bold green]✅ Generation complete in {elapsed:.2f}s![/bold green]")
        console.print(f"📁 Output: [cyan]{output}[/cyan]")
        console.print(f"📏 Size: [cyan]{file_size:,} bytes[/cyan]")
        console.print(f"📅 Generated: [cyan]{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/cyan]")
    
    def validate_generated_code(self, file_path: pathlib.Path) -> bool:
        """Validate the generated code syntax"""
        try:
            import ast
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            ast.parse(code)
            logger.info("✅ Generated code syntax is valid")
            return True
        except SyntaxError as e:
            logger.error(f"❌ Generated code has syntax error: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Error validating code: {e}")
            return False
    
    def generate(self):
        """Run full generation"""
        console.rule("[bold blue]Pocket Option Code Generator v2.0.0[/bold blue]")
        
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                console=console
            ) as progress:
                
                task = progress.add_task("Generating...", total=5)
                
                # Step 1: Load events
                progress.update(task, description="📂 Loading events...")
                data = self.load_events()
                progress.advance(task)
                
                # Step 2: Generate code
                progress.update(task, description="🔄 Generating code...")
                code = self.generate_client(data)
                progress.advance(task)
                
                # Step 3: Save code
                progress.update(task, description="💾 Saving code...")
                output = self.save_code(code)
                progress.advance(task)
                
                # Step 4: Validate syntax
                progress.update(task, description="🔍 Validating syntax...")
                is_valid = self.validate_generated_code(output)
                progress.advance(task)
                
                # Step 5: Format code
                if is_valid:
                    progress.update(task, description="🎨 Formatting...")
                    self.format_code(output)
                progress.advance(task)
            
            # Print summary
            self.print_summary(data, output)
            
            # Show next steps
            console.print("\n[bold]📌 Next Steps:[/bold]")
            console.print("1. Review the generated client at [cyan]generated_client.py[/cyan]")
            console.print("2. Import and use in your code: [yellow]from pocket_trader import PocketOptionClient[/yellow]")
            console.print("3. Check the events in [cyan]events.json[/cyan] if you need to add more")
            
        except KeyboardInterrupt:
            console.print("\n[yellow]⚠️ Generation interrupted by user[/yellow]")
            sys.exit(1)
        except Exception as e:
            console.print(f"\n[bold red]❌ Generation failed: {e}[/bold red]")
            logger.exception("Generation failed")
            sys.exit(1)


def main():
    """Main entry point"""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        handlers=[RichHandler(rich_tracebacks=True, show_time=False, markup=True)]
    )
    
    # Create generator and run
    generator = CodeGenerator()
    generator.generate()


if __name__ == "__main__":
    main()