"""Rich terminal UI for displaying multi-account quota status."""
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
import datetime

console = Console()

def get_color_for_pct(pct):
    if pct >= 50:
        return "green"
    elif pct >= 20:
        return "yellow"
    else:
        return "red"

def render_progress_cell(pct, reset_time):
    color = get_color_for_pct(pct)
    # Simple text progress bar: [■■■■■     ]
    filled = int(round(pct / 10))
    bar = "■" * filled + " " * (10 - filled)
    return f"[{color}]{pct:5.1f}% [{bar}][/{color}]\n[dim]{reset_time}[/dim]"

def build_status_table(accounts_data):
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    table = Table(
        title=f"Antigravity Multi-Account Quota Monitor (Checked: {now_str})",
        title_style="bold cyan",
        border_style="dim",
        header_style="bold magenta",
        expand=True,
    )

    table.add_column("Account", style="bold white", min_width=18)
    table.add_column("Plan", style="cyan", min_width=12)
    table.add_column("Gemini 5-Hour", justify="center", min_width=22)
    table.add_column("Gemini Weekly", justify="center", min_width=22)
    table.add_column("Claude/GPT 5-Hour", justify="center", min_width=22)
    table.add_column("Claude/GPT Weekly", justify="center", min_width=22)
    table.add_column("Status", justify="center", min_width=10)

    for item in accounts_data:
        name = item.get("name", "Unknown")
        email = item.get("email", "")
        acc_label = f"{name}\n[dim]{email}[/dim]" if email and email != "local_active_session" else name
        plan = item.get("plan", "Unknown")
        status = item.get("status", "unknown")

        if status != "online":
            err_msg = item.get("error", "Offline")
            table.add_row(
                acc_label,
                plan,
                "[dim]-[/dim]",
                "[dim]-[/dim]",
                "[dim]-[/dim]",
                "[dim]-[/dim]",
                f"[bold red]❌ {err_msg[:18]}[/bold red]"
            )
            continue

        gem = item.get("gemini", {})
        c_gpt = item.get("claude_gpt", {})

        gem_5h = render_progress_cell(gem.get("5h_remaining", 100.0), gem.get("5h_reset", "Ready"))
        gem_wk = render_progress_cell(gem.get("weekly_remaining", 100.0), gem.get("weekly_reset", "Ready"))
        cgpt_5h = render_progress_cell(c_gpt.get("5h_remaining", 100.0), c_gpt.get("5h_reset", "Ready"))
        cgpt_wk = render_progress_cell(c_gpt.get("weekly_remaining", 100.0), c_gpt.get("weekly_reset", "Ready"))

        table.add_row(
            acc_label,
            plan,
            gem_5h,
            gem_wk,
            cgpt_5h,
            cgpt_wk,
            "[bold green]✔ Online[/bold green]"
        )

    return table

def display_status(accounts_data):
    if not accounts_data:
        console.print(Panel("[yellow]No Google accounts configured yet. Run [bold green]python monitor.py add-account[/bold green] to add one.[/yellow]", title="Antigravity Monitor"))
        return
    table = build_status_table(accounts_data)
    console.print(table)
