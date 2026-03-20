"""interact.py — Interactive REPL for goal assessment (--chat flag)."""
from __future__ import annotations
from .benchmarks import match_sport, evaluate_goal, assess_athlete, sport_recommendations


def run_chat(data: dict, athlete: dict) -> None:
    """Interactive REPL. Invoked via `python analyze.py --chat`."""
    try:
        from rich.console import Console, Group
        from rich.panel import Panel
        from rich.text import Text
        from rich import box as rbox
        _rich = True
    except ImportError:
        _rich = False
        Console = Group = Panel = Text = rbox = None  # type: ignore

    name = f"{athlete.get('firstname', '')} {athlete.get('lastname', '')}".strip()

    if _rich:
        console = Console()
        console.print()
        console.print(Panel(
            Text(
                f"  Hi {name or 'athlete'}! Tell me what you want to do.\n"
                "  Examples:  'I want to run a marathon'  ·  'Can I do an Ironman?'\n"
                "             'show recommendations'  ·  'benchmark me'\n"
                "  Type 'quit' to exit.",
                style="dim",
            ),
            title="[bold cyan]GOAL ASSESSMENT CHAT[/bold cyan]",
            box=rbox.ROUNDED,
        ))
        console.print()
    else:
        console = None
        print(f"\nHi {name or 'athlete'}! Tell me your goal. Type 'quit' to exit.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break
        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q", "bye"):
            print("Goodbye!")
            break

        low = user_input.lower()

        if any(k in low for k in ("recommend", "what should", "best sport", "suggest", "what can")):
            _show_recommendations(data, console)
        elif any(k in low for k in ("benchmark", "norms", "population", "how do i compare", "my fitness", "compare me")):
            _show_benchmarks(data, console)
        elif any(k in low for k in ("help", "what can you do", "commands")):
            _show_help(console)
        else:
            sport = match_sport(user_input)
            if sport:
                verdict = evaluate_goal(sport, data)
                _show_verdict(verdict, console)
            else:
                msg = (
                    "I didn't catch a specific sport goal. Try:\n"
                    "  • 'I want to run a marathon'\n"
                    "  • 'Can I do an Ironman?'\n"
                    "  • 'show recommendations'\n"
                    "  • 'benchmark me'"
                )
                if console:
                    from rich.text import Text as _T
                    from rich.panel import Panel as _P
                    from rich import box as _b
                    console.print(_P(_T(msg, style="dim"), box=_b.SIMPLE))
                else:
                    print(msg)


def _show_verdict(verdict: dict, console) -> None:
    if "error" in verdict:
        msg = verdict["error"]
        if console:
            from rich.text import Text
            console.print(Text(f"  Error: {msg}", style="red"))
        else:
            print(f"Error: {msg}")
        return

    if console:
        from rich.console import Group
        from rich.panel import Panel
        from rich.text import Text
        from rich import box as rbox

        color = verdict["color"]
        rc = {"green": "bold green", "yellow": "bold yellow", "red": "bold red"}.get(color, "white")

        items = []
        r = verdict["readiness"]
        bar_len = int(r / 5)
        bar = Text()
        bar.append("  Readiness  ", style="dim")
        bar.append("█" * bar_len, style=color)
        bar.append("░" * (20 - bar_len), style="dim")
        bar.append(f"  {r}%", style=rc)
        items.append(bar)
        items.append(Text(f"\n  {verdict['timeline']}", style=rc))
        items.append(Text(f"  {verdict['notes']}", style="dim"))

        if verdict["gaps"]:
            items.append(Text("\n  What needs work:", style="bold white"))
            for g in verdict["gaps"]:
                c = "red" if g["urgent"] else "yellow"
                items.append(Text(
                    f"  {'⚡' if g['urgent'] else '⚠ '} {g['metric']}: "
                    f"{g['current']} → need {g['required']}  ({g['gap']})",
                    style=c,
                ))
        else:
            items.append(Text("\n  ✓ No major gaps — you're ready!", style="bold green"))

        console.print(Panel(
            Group(*items),
            title=f"[bold cyan]{verdict['label']}  —  Verdict[/bold cyan]",
            box=rbox.ROUNDED, padding=(0, 1),
        ))
        console.print()
    else:
        print(f"\n{verdict['label']} — Readiness: {verdict['readiness']}%")
        print(f"  {verdict['timeline']}")
        if verdict["gaps"]:
            for g in verdict["gaps"]:
                print(f"  • {g['metric']}: {g['current']} → {g['required']}")
        print()


def _show_recommendations(data: dict, console) -> None:
    recs = sport_recommendations(data)[:5]

    if console:
        from rich.console import Group
        from rich.panel import Panel
        from rich.table import Table
        from rich.text import Text
        from rich import box as rbox

        tbl = Table(box=rbox.SIMPLE_HEAD, padding=(0, 1), header_style="bold cyan")
        tbl.add_column("Sport",     style="bold white", width=24)
        tbl.add_column("Readiness", justify="right",    width=10)
        tbl.add_column("Bar",       width=22)
        tbl.add_column("Notes",     style="dim")

        for rec in recs:
            r = rec["readiness"]
            color = "green" if r >= 80 else ("yellow" if r >= 60 else "red")
            bar = Text()
            bar.append("█" * int(r / 5), style=color)
            bar.append("░" * (20 - int(r / 5)), style="dim")
            tbl.add_row(rec["label"], f"[{color}]{r}%[/{color}]", bar, rec["notes"])

        console.print(Panel(
            tbl,
            title="[bold cyan]TOP SPORT RECOMMENDATIONS[/bold cyan]",
            box=rbox.ROUNDED, padding=(0, 1),
        ))
        console.print()
    else:
        print("\nTop Sport Recommendations:")
        for rec in recs:
            print(f"  {rec['readiness']:3d}%  {rec['label']}")
        print()


def _show_benchmarks(data: dict, console) -> None:
    ratings = assess_athlete(data)
    if not ratings:
        msg = "No Apple Health data available for benchmarking."
        if console:
            from rich.text import Text
            console.print(Text(f"  {msg}", style="dim"))
        else:
            print(msg)
        return

    if console:
        from rich.panel import Panel
        from rich.table import Table
        from rich import box as rbox

        RATING_COLORS = {
            "Excellent": "green", "Athlete": "green", "Good": "green",
            "Above Average": "cyan", "Average": "yellow",
            "Below Average": "yellow", "Poor": "red", "Very Poor": "red",
            "Fair": "yellow",
        }

        tbl = Table(box=None, show_header=False, padding=(0, 2))
        tbl.add_column(style="dim",        width=28)
        tbl.add_column(style="bold white", width=14)
        tbl.add_column()

        for _, info in ratings.items():
            color = RATING_COLORS.get(info["rating"], "white")
            tbl.add_row(
                info["label"],
                f"{info['value']:.0f} {info['unit']}",
                f"[{color}]{info['rating']}[/{color}]",
            )

        console.print(Panel(
            tbl,
            title="[bold cyan]YOUR METRICS vs POPULATION NORMS[/bold cyan]",
            box=rbox.ROUNDED, padding=(0, 1),
        ))
        console.print()
    else:
        print("\nYour Metrics vs Population Norms:")
        for _, info in ratings.items():
            print(f"  {info['label']:30s}  {info['value']:.0f} {info['unit']:10s}  {info['rating']}")
        print()


def _show_help(console) -> None:
    msg = (
        "Commands:\n"
        "  'I want to do a marathon'  — Goal assessment for specific sport\n"
        "  'show recommendations'     — Top sports for your current fitness\n"
        "  'benchmark me'             — Compare your metrics to population norms\n"
        "  'quit'                     — Exit chat"
    )
    if console:
        from rich.panel import Panel
        from rich.text import Text
        from rich import box as rbox
        console.print(Panel(Text(msg, style="dim"), title="[dim]HELP[/dim]", box=rbox.SIMPLE))
    else:
        print(f"\n{msg}\n")
