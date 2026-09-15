#!/usr/bin/env python3
"""Launcher & CLI Dispatcher for Antigravity Quota Monitor.
- No args: Launches the native standalone desktop webapp window.
- With args: Executes CLI commands (status, watch, list, add-account, etc.).
"""
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

APP_DIR = Path(__file__).parent.parent
BACKEND_DIR = APP_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))

USER_DATA_DIR = Path.home() / ".config" / "antigravity-quota-webapp-profile"
PORT = 8999
WM_CLASS = "AntigravityQuota"

def check_already_running():
    """Focus existing window if already open."""
    try:
        out = subprocess.check_output(
            ["wmctrl", "-l", "-x"],
            text=True,
            env={**os.environ, "DISPLAY": os.environ.get("DISPLAY", ":0")},
            stderr=subprocess.DEVNULL
        )
        for line in out.splitlines():
            if WM_CLASS in line or "antigravity-quota" in line.lower():
                print("Antigravity Quota is already running. Focusing existing window...")
                subprocess.call(
                    ["wmctrl", "-x", "-a", WM_CLASS],
                    env={**os.environ, "DISPLAY": os.environ.get("DISPLAY", ":0")}
                )
                return True
    except Exception:
        pass
    return False

def is_backend_alive():
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{PORT}/api/ping", headers={"User-Agent": "AntigravityLauncher"})
        with urllib.request.urlopen(req, timeout=1) as resp:
            return resp.status == 200
    except Exception:
        return False

def ensure_backend_running():
    if is_backend_alive():
        return None

    print("Starting Antigravity Quota backend service...")
    venv_py = APP_DIR / ".venv" / "bin" / "python3"
    python_bin = str(venv_py) if venv_py.exists() else sys.executable

    server_script = BACKEND_DIR / "server.py"
    proc = subprocess.Popen(
        [python_bin, str(server_script)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=str(BACKEND_DIR),
        start_new_session=True
    )

    start = time.time()
    while time.time() - start < 5:
        if is_backend_alive():
            return proc
        time.sleep(0.1)

    print("Warning: Backend took longer than expected to start.")
    return proc

def get_screen_size():
    try:
        out = subprocess.check_output(
            ["xwininfo", "-root"],
            text=True,
            env={**os.environ, "DISPLAY": os.environ.get("DISPLAY", ":0")}
        )
        w = int(re.search(r"Width:\s+(\d+)", out).group(1))
        h = int(re.search(r"Height:\s+(\d+)", out).group(1))
        return w, h
    except Exception:
        return 1920, 1080

def find_chromium_bin():
    for b in ["chromium", "chromium-browser", "google-chrome-stable", "google-chrome", "brave-browser"]:
        try:
            path = subprocess.check_output(["which", b], text=True).strip()
            if path and os.path.exists(path):
                return path
        except Exception:
            continue
    return "chromium"

def handle_cli_commands():
    """Handle CLI subcommands if arguments are passed."""
    import argparse
    from auth_manager import load_accounts, start_interactive_oauth, add_active_local_account, rename_account, remove_account
    from quota_fetcher import fetch_all_accounts_quota
    from terminal_ui import display_status, build_status_table
    from rich.console import Console
    from rich.live import Live

    console = Console()
    parser = argparse.ArgumentParser(description="Antigravity Multi-Account Quota Monitor CLI")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("status", help="Show current quota for all accounts")
    p_watch = subparsers.add_parser("watch", help="Live refreshing terminal dashboard")
    p_watch.add_argument("--interval", "-i", type=int, default=30, help="Refresh interval in seconds")

    p_add = subparsers.add_parser("add-account", help="Add Google account via OAuth browser login")
    p_add.add_argument("--name", "-n", type=str, help="Optional friendly name")

    p_rename = subparsers.add_parser("rename", help="Rename an account")
    p_rename.add_argument("identifier", help="Current name or email")
    p_rename.add_argument("new_name", help="New display name")

    subparsers.add_parser("list", help="List registered accounts")
    p_rem = subparsers.add_parser("remove", help="Remove an account")
    p_rem.add_argument("identifier", help="Account name or email to remove")

    args = parser.parse_args()

    if args.command == "status":
        with console.status("[bold green]Fetching quota...[/bold green]"):
            data = fetch_all_accounts_quota()
        display_status(data)
    elif args.command == "watch":
        initial_data = fetch_all_accounts_quota()
        table = build_status_table(initial_data)
        with Live(table, console=console, refresh_per_second=2) as live:
            try:
                while True:
                    time.sleep(args.interval)
                    live.update(build_status_table(fetch_all_accounts_quota()))
            except KeyboardInterrupt:
                console.print("\n[yellow]Watch stopped.[/yellow]")
    elif args.command == "add-account":
        start_interactive_oauth(name=args.name)
    elif args.command == "rename":
        if rename_account(args.identifier, args.new_name):
            console.print(f"[green]Successfully renamed '{args.identifier}' to '{args.new_name}'.[/green]")
        else:
            console.print(f"[red]Could not find account '{args.identifier}'.[/red]")
    elif args.command == "list":
        accounts = load_accounts()
        console.print(f"[bold]Configured Accounts ({len(accounts)}):[/bold]")
        for i, acc in enumerate(accounts, 1):
            console.print(f" {i}. [bold cyan]{acc.get('name')}[/bold cyan] ({acc.get('email')}) - [dim]{acc.get('type')}[/dim]")
    elif args.command == "remove":
        if remove_account(args.identifier):
            console.print(f"[green]Removed '{args.identifier}'.[/green]")
        else:
            console.print(f"[red]Account '{args.identifier}' not found.[/red]")

def main():
    # If arguments provided, run CLI command
    if len(sys.argv) > 1:
        handle_cli_commands()
        return

    # No arguments -> Launch Desktop GUI Window
    if check_already_running():
        sys.exit(0)

    server_proc = ensure_backend_running()

    screen_w, screen_h = get_screen_size()
    win_w, win_h = 1040, 760
    left = max(0, (screen_w - win_w) // 2)
    top = max(0, (screen_h - win_h) // 2 - 30)

    chromium_bin = find_chromium_bin()

    chromium_args = [
        chromium_bin,
        f"--user-data-dir={USER_DATA_DIR}",
        f"--class={WM_CLASS}",
        f"--app=http://127.0.0.1:{PORT}",
        f"--window-size={win_w},{win_h}",
        f"--window-position={left},{top}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-component-update",
        "--password-store=basic",
    ]

    print("Launching Antigravity Quota desktop window...")
    try:
        chrome_proc = subprocess.Popen(
            chromium_args,
            env={**os.environ, "DISPLAY": os.environ.get("DISPLAY", ":0")}
        )
        chrome_proc.wait()
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
