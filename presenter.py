# Theatrical presenter for The Courtroom: Appeals.
#
# Pure presentation: renders a finished CaseResult (and optional JudgePanel)
# with `rich`, for the demo video. It reads only the scoreboard-level facts the
# plain output already shows — it never prints attack scripts — so it is just a
# prettier, paced view of main.py's results. No model or sandbox calls here.

import time

from rich import box
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

console = Console()

_SEVERITY_STYLE = {
    "CRITICAL": "bold white on red",
    "HIGH": "bold red",
    "MEDIUM": "bold yellow",
    "LOW": "bold cyan",
    "NONE": "bold green",
}


def _verdict_style(verdict: str) -> str:
    v = verdict.upper()
    if v.startswith("NOT GUILTY") or v.startswith("NO CASE"):
        return "green"
    if "UNFIXED" in v:
        return "yellow"
    if v.startswith("GUILTY"):
        return "red"
    return "white"


def _pause(pace: float) -> None:
    if pace > 0:
        time.sleep(pace)


def present_trial(result, panel=None, precedent=None, pace: float = 0.6) -> None:
    """Render a completed case theatrically. `pace` = seconds between reveals."""
    console.print()
    console.rule("[bold cyan]⚖  THE COURTROOM: APPEALS  ⚖[/bold cyan]", style="cyan")
    console.print()

    table = Table(title="Trial Record", box=box.ROUNDED, header_style="bold cyan")
    for col in ("Round", "Attacks", "Worked", "New", "Patches", "Accepted", "Winning model"):
        table.add_column(col, justify="center")

    # Grow the scoreboard a round at a time for the "trial unfolding" effect.
    with Live(table, console=console, refresh_per_second=12):
        for r in result.rounds:
            accepted = "[green]yes[/green]" if r.patch_accepted else "[red]no[/red]"
            table.add_row(
                str(r.number), str(r.attacks_tried), str(r.attacks_worked),
                str(r.new_exploits), str(r.patches_tried), accepted,
                r.winning_model or "—",
            )
            _pause(pace)

    console.print()
    _pause(pace)

    style = _verdict_style(result.verdict)
    console.print(Panel(
        f"[bold {style}]{result.verdict}[/bold {style}]",
        title="VERDICT",
        subtitle=f"status: {result.status}   •   exploits confirmed: {len(result.exploit_suite)}",
        border_style=style,
        box=box.DOUBLE,
    ))

    if precedent and precedent.get("query"):
        _pause(pace)
        _present_precedent(precedent)

    if panel is not None:
        _pause(pace)
        _present_panel(panel, pace)


def _present_panel(panel, pace: float) -> None:
    console.print()
    console.rule("[bold magenta]SUPREME COURT — SEVERITY PANEL[/bold magenta]", style="magenta")
    console.print()

    sev_style = _SEVERITY_STYLE.get(panel.majority_severity, "white")
    console.print(Panel(
        f"[{sev_style}]{panel.majority_severity}[/{sev_style}]\n\n{panel.majority_opinion}",
        title="Majority opinion", border_style="green",
    ))
    _pause(pace)

    if panel.dissent is not None:
        d_style = _SEVERITY_STYLE.get(panel.dissent.severity, "white")
        console.print(Panel(
            f"[{d_style}]{panel.dissent.severity}[/{d_style}]\n\n{panel.dissent.opinion}",
            title=f"Dissent — {panel.dissent.model}", border_style="magenta",
        ))
        _pause(pace)
    else:
        console.print("[dim]Dissent: none (unanimous)[/dim]")

    votes = Table(title="Panel votes", box=box.SIMPLE, header_style="bold")
    votes.add_column("Justice (model)")
    votes.add_column("Severity", justify="center")
    for o in panel.opinions:
        s_style = _SEVERITY_STYLE.get(o.severity, "white")
        votes.add_row(o.model, f"[{s_style}]{o.severity}[/{s_style}]")
    console.print(votes)


def _present_precedent(precedent) -> None:
    body = []
    if precedent.get("answer"):
        body.append(precedent["answer"])
    for s in (precedent.get("sources") or [])[:3]:
        body.append(f"[dim]•[/dim] {s.get('title', '')} — {s.get('url', '')}")
    console.print(Panel(
        "\n".join(body) if body else "(no precedent returned)",
        title=f"Real-world precedent via Tavily — query: {precedent.get('query', '')}",
        border_style="blue",
    ))
