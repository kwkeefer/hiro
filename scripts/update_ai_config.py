#!/usr/bin/env python3
"""
Update AI configuration from cookiecutter template.

This script fetches the latest .ai/ and .claude/ configuration from the
cookiecutter template and selectively updates the current project.
"""

import difflib
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt
    from rich.syntax import Syntax
    from rich.text import Text
except ImportError:
    print("❌ This script requires 'rich'. Install with: uv add --dev rich")
    sys.exit(1)

console = Console()

# Configuration
TEMPLATE_REPO = "https://github.com/kwkeefer/cookiecutter-uv"

# File categories
PRESERVE_FILES = [
    ".ai/project-context.md",  # Project-specific, never overwrite
]

AUTO_UPDATE_FILES = [
    ".claude/agents/code-reviewer.md",  # Template improvements, always update
]

DIFF_FILES = [
    ".ai/quick-reference.md",
    ".ai/coding-standards.md",
    ".ai/architecture-decisions.md",
    ".ai/claude-code-instructions.md",
    ".ai/README.md",
]


def extract_project_settings() -> dict[str, str]:
    """Extract project settings from pyproject.toml."""
    pyproject_path = Path("pyproject.toml")
    if not pyproject_path.exists():
        console.print(
            "❌ pyproject.toml not found. Are you in the project root?", style="red"
        )
        sys.exit(1)

    try:
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)

        project_name = data["project"]["name"]
        project_slug = project_name.replace("-", "_")

        console.print(f"📦 Detected project: [green]{project_name}[/green]")
        return {"project_name": project_name, "project_slug": project_slug}

    except Exception as e:
        console.print(f"❌ Error parsing pyproject.toml: {e}", style="red")
        sys.exit(1)


def generate_fresh_template(settings: dict[str, str]) -> Path:
    """Generate fresh cookiecutter template in temp directory."""
    temp_dir = Path(tempfile.mkdtemp())

    console.print("📥 Generating fresh template...")

    try:
        subprocess.run(
            [
                "uvx",
                "cookiecutter",
                "--no-input",
                TEMPLATE_REPO,
                f"project_name={settings['project_name']}",
                f"project_slug={settings['project_slug']}",
                "use_claude_agents=yes",
            ],
            cwd=temp_dir,
            check=True,
            capture_output=True,
        )

        return temp_dir / settings["project_slug"]

    except subprocess.CalledProcessError as e:
        console.print(f"❌ Error generating template: {e}", style="red")
        sys.exit(1)
    except FileNotFoundError:
        console.print(
            "❌ cookiecutter not found. Make sure uvx is available", style="red"
        )
        sys.exit(1)


def show_diff_and_ask(current_file: Path, new_file: Path) -> bool:
    """Show diff between files and ask user if they want to replace."""
    rel_path = str(current_file)

    # New file
    if not current_file.exists():
        console.print(f"➕ [green]New file:[/green] {rel_path}")
        return True

    # File removed from template
    if not new_file.exists():
        console.print(f"⚠️  [yellow]File removed from template:[/yellow] {rel_path}")
        return False

    # Read file contents
    try:
        current_content = current_file.read_text()
        new_content = new_file.read_text()
    except Exception as e:
        console.print(f"❌ Error reading files: {e}", style="red")
        return False

    # No changes
    if current_content == new_content:
        console.print(f"✅ [green]No changes:[/green] {rel_path}")
        return False

    # Show diff
    console.print(f"\n📝 [yellow]Changes detected in:[/yellow] {rel_path}")

    diff_lines = list(
        difflib.unified_diff(
            current_content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=f"current/{rel_path}",
            tofile=f"template/{rel_path}",
            lineterm="",
        )
    )

    # Display diff with syntax highlighting
    diff_text = "".join(diff_lines)
    syntax = Syntax(diff_text, "diff", theme="monokai", line_numbers=False)
    console.print(Panel(syntax, title=f"Diff: {rel_path}"))

    # Ask user
    while True:
        choice = Prompt.ask(
            "What would you like to do?",
            choices=["replace", "skip", "diff"],
            default="skip",
        )

        if choice == "replace":
            console.print(f"✅ [green]Will update:[/green] {rel_path}")
            return True
        elif choice == "skip":
            console.print(f"⏭️  [yellow]Skipped:[/yellow] {rel_path}")
            return False
        elif choice == "diff":
            console.print(syntax)


def safe_copy(src: Path, dest: Path) -> None:
    """Safely copy file, creating directories as needed."""
    if not src.exists():
        return

    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    console.print(f"✅ [green]Updated:[/green] {dest}")


def find_additional_files(template_dir: Path) -> list[Path]:
    """Find additional files in template that aren't in our predefined lists."""
    all_files = set()
    known_files = set(PRESERVE_FILES + AUTO_UPDATE_FILES + DIFF_FILES)

    for ai_dir in [".ai", ".claude"]:
        ai_path = template_dir / ai_dir
        if ai_path.exists():
            for file_path in ai_path.rglob("*"):
                if file_path.is_file():
                    rel_path = str(file_path.relative_to(template_dir))
                    if rel_path not in known_files:
                        all_files.add(Path(rel_path))

    return sorted(all_files)


def main():
    """Main execution function."""
    console.print(
        Panel(
            Text("🔄 Updating AI Configuration", style="bold blue"),
            subtitle="Fetching latest from cookiecutter template",
        )
    )

    # Extract current project settings
    console.print("\n🔍 [blue]Extracting current project settings...[/blue]")
    settings = extract_project_settings()

    # Generate fresh template
    template_dir = generate_fresh_template(settings)

    try:
        console.print("\n🔄 [blue]Processing updates...[/blue]")

        # Auto-update files (no prompts)
        for file_path in AUTO_UPDATE_FILES:
            src = template_dir / file_path
            dest = Path(file_path)
            if src.exists():
                safe_copy(src, dest)

        # Show diffs and ask for approval
        for file_path in DIFF_FILES:
            src = template_dir / file_path
            dest = Path(file_path)

            if show_diff_and_ask(dest, src):
                safe_copy(src, dest)

        # Handle additional files not in predefined lists
        additional_files = find_additional_files(template_dir)
        if additional_files:
            console.print(
                f"\n📁 [blue]Found {len(additional_files)} additional files...[/blue]"
            )
            for file_path in additional_files:
                src = template_dir / file_path
                dest = file_path

                if show_diff_and_ask(dest, src):
                    safe_copy(src, dest)

        # Show summary
        console.print(
            Panel(
                Text("🎉 AI configuration update complete!", style="bold green"),
                subtitle="Files preserved automatically: " + ", ".join(PRESERVE_FILES),
            )
        )

    finally:
        # Cleanup
        shutil.rmtree(template_dir.parent)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n❌ Update cancelled by user", style="red")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n❌ Unexpected error: {e}", style="red")
        sys.exit(1)
