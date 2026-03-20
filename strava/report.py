"""report.py — Rich terminal report (+ plain fallback)."""
from __future__ import annotations
from datetime import datetime
from .utils import hms, pace
from . import benchmarks as bm


def print_report(data: dict, athlete: dict) -> None:
    try:
        from rich.console import Console, Group
        from rich.table import Table
        from rich.panel import Panel
        from rich.text import Text
        from rich.columns import Columns
        from rich import box as rbox
    except ImportError:
        print("Install rich for a beautiful report:  pip install rich")
        _print_plain(data, athlete)
        return

    console = Console()
    name = f"{athlete.get('firstname', '')} {athlete.get('lastname', '')}".strip()

    # ── Header ────────────────────────────────────────────────────────────────
    header = Text(justify="center")
    header.append("STRAVA FITNESS ANALYSIS\n", style="bold white")
    header.append(name, style="bold cyan")
    header.append(f"\n{datetime.now().strftime('%Y-%m-%d %H:%M')}", style="dim")
    console.print()
    console.print(Panel(header, box=rbox.HEAVY_HEAD, style="bold cyan", padding=(1, 4)))
    console.print()

    # ── Overview ──────────────────────────────────────────────────────────────
    ov = data["overview"]
    ov_table = Table(box=None, show_header=False, padding=(0, 2), expand=True)
    ov_table.add_column(style="dim", ratio=1)
    ov_table.add_column(style="bold white", ratio=1)
    ov_table.add_row("Total Activities", str(ov["total"]))
    ov_table.add_row("Total Distance",   f"{ov['total_km']:,.0f} km")
    ov_table.add_row("Moving Time",      hms(ov["total_h"] * 3600))
    ov_table.add_row("Weekly Average",   f"{ov['avg_km_week']:.1f} km  ·  {ov['avg_h_week']:.1f} h")

    sport_text = Text()
    sport_text.append(f"  {ov['runs']} runs",   style="bold green")
    sport_text.append("   ·   ",                 style="dim")
    sport_text.append(f"{ov['rides']} rides",    style="bold yellow")
    sport_text.append("   ·   ",                 style="dim")
    sport_text.append(f"{ov['swims']} swims",    style="bold blue")
    if ov["other"]:
        sport_text.append(f"   ·   {ov['other']} other", style="dim")

    console.print(Panel(
        Group(ov_table, Text(""), sport_text),
        title="[bold cyan]OVERVIEW[/bold cyan]",
        box=rbox.ROUNDED, padding=(0, 1),
    ))
    console.print()

    # ── Weekly Volume ─────────────────────────────────────────────────────────
    wk    = data["weekly"]
    mx_km = max(wk["km"]) if wk["km"] else 1

    vol_table = Table(box=rbox.SIMPLE_HEAD, padding=(0, 1), header_style="bold cyan")
    vol_table.add_column("Week",   style="dim",     width=7)
    vol_table.add_column("km",     justify="right", width=6)
    vol_table.add_column("h",      justify="right", style="dim", width=5)
    vol_table.add_column("Load",   justify="right", style="dim", width=6)
    vol_table.add_column("Volume", width=24)

    for i, (label, wkm, wh, wt) in enumerate(
            zip(wk["labels"], wk["km"], wk["hours"], wk["trimp"])):
        is_now  = i == 15
        bar_len = int(wkm / mx_km * 22) if mx_km else 0
        bar = Text()
        if wkm == 0:
            bar.append("·" * 22, style="dim")
        else:
            color = "bright_green" if is_now else "green"
            bar.append("█" * bar_len,        style=color)
            bar.append("░" * (22 - bar_len), style="dim")
        if is_now:
            bar.append(" ◄", style="bold bright_green")
        km_style = "bold bright_green" if is_now else ("white" if wkm > 0 else "dim")
        vol_table.add_row(
            label,
            f"[{km_style}]{wkm:.1f}[/{km_style}]",
            f"{wh:.1f}" if wh > 0 else "—",
            f"{wt:.0f}" if wt > 0 else "—",
            bar,
        )

    t_pct = wk["trend_pct"]
    if t_pct > 3:
        trend_line = Text(f"  Trend  ↑ +{t_pct:.1f}%/wk — building volume", style="green")
    elif t_pct < -3:
        trend_line = Text(f"  Trend  ↓ {t_pct:.1f}%/wk — volume declining", style="yellow")
    else:
        trend_line = Text(f"  Trend  → flat ({t_pct:.1f}%/wk)", style="dim")

    extras = [vol_table, trend_line]
    if wk["zero_weeks"]:
        extras.append(Text(f"  ⚠  {wk['zero_weeks']}/16 weeks with zero activity", style="bold yellow"))

    console.print(Panel(
        Group(*extras),
        title="[bold cyan]WEEKLY VOLUME  ·  16 weeks[/bold cyan]",
        box=rbox.ROUNDED, padding=(0, 1),
    ))
    console.print()

    # ── Training Load ─────────────────────────────────────────────────────────
    ld = data["load"]
    form_colors = {
        "fresh": "bold green", "neutral": "yellow",
        "tired": "bold yellow", "overreached": "bold red",
    }
    fc = form_colors[ld["form_status"]]

    load_table = Table(box=None, show_header=False, padding=(0, 2))
    load_table.add_column(style="dim", width=30)
    load_table.add_column(style="bold white")

    tsb_style = "green" if ld["tsb"] > 10 else "red" if ld["tsb"] < -10 else "yellow"
    load_table.add_row("CTL  (fitness / 42-day avg)", f"{ld['ctl']:.1f}")
    load_table.add_row("ATL  (fatigue / 7-day avg)",  f"{ld['atl']:.1f}")
    load_table.add_row("TSB  (form = CTL − ATL)",     f"[{tsb_style}]{ld['tsb']:+.1f}[/{tsb_style}]")
    load_table.add_row("", "")
    load_table.add_row("Current Form", f"[{fc}]{ld['form_label']}[/{fc}]")
    load_table.add_row("",             f"[dim]{ld['form_msg']}[/dim]")
    load_table.add_row("", "")

    cd = ld["ctl_delta"]
    cd_style = "green" if cd > 2 else ("yellow" if cd < -2 else "dim")
    cd_label = "building" if cd > 2 else ("declining" if cd < -2 else "flat")
    load_table.add_row("CTL change (6 weeks)", f"[{cd_style}]{cd:+.1f}  ({cd_label})[/{cd_style}]")

    console.print(Panel(
        load_table,
        title="[bold cyan]TRAINING LOAD  ·  CTL / ATL / TSB[/bold cyan]",
        box=rbox.ROUNDED, padding=(0, 1),
    ))
    console.print()

    # ── Heart Rate Trends ─────────────────────────────────────────────────────
    hr_table = Table(box=rbox.SIMPLE_HEAD, padding=(0, 1), header_style="bold cyan")
    hr_table.add_column("Sport",     style="bold white", width=6)
    hr_table.add_column("Early HR",  justify="right",    width=9)
    hr_table.add_column("Recent HR", justify="right",    width=10)
    hr_table.add_column("Δ",         justify="right",    width=5)
    hr_table.add_column("Aerobic Efficiency")
    hr_table.add_column("Max HR",    justify="right",    width=8)

    for entry in data["hr"]:
        if entry.get("insufficient"):
            hr_table.add_row(entry["sport"], "[dim]< 5 activities with HR[/dim]", "", "", "", "")
            continue
        delta   = entry["avg_hr_late"] - entry["avg_hr_early"]
        d_style = "green" if delta < -2 else ("red" if delta > 2 else "dim")
        ec      = entry["eff_change"]
        if entry["eff_dir"] == "improving":
            eff_text = f"[green]✓ improving  ({ec:.1f}%)[/green]"
        elif entry["eff_dir"] == "declining":
            eff_text = f"[red]✗ declining  ({ec:+.1f}%)[/red]"
        else:
            eff_text = "[dim]→ flat[/dim]"
        hr_table.add_row(
            entry["sport"],
            f"{entry['avg_hr_early']:.0f} bpm",
            f"{entry['avg_hr_late']:.0f} bpm",
            f"[{d_style}]{delta:+.0f}[/{d_style}]",
            eff_text,
            f"{entry['max_hr']} bpm" if entry["max_hr"] else "—",
        )

    console.print(Panel(
        hr_table,
        title="[bold cyan]HEART RATE TRENDS[/bold cyan]",
        box=rbox.ROUNDED, padding=(0, 1),
    ))
    console.print()

    # ── Intensity Distribution ────────────────────────────────────────────────
    zd = data["zones"]
    if zd["no_data"]:
        zone_content = Text("  No HR data available for zone analysis.", style="dim")
    else:
        zone_table = Table(box=rbox.SIMPLE_HEAD, padding=(0, 1), header_style="bold cyan")
        zone_table.add_column("Zone",     style="bold white", width=4)
        zone_table.add_column("Label",    style="dim",        width=14)
        zone_table.add_column("Sessions", justify="right",    width=9)
        zone_table.add_column("Time",     justify="right",    width=8)
        zone_table.add_column("Distribution", width=32)

        zone_colors = {"Z1": "blue", "Z2": "cyan", "Z3": "yellow", "Z4": "dark_orange", "Z5": "red"}
        for z in ["Z1", "Z2", "Z3", "Z4", "Z5"]:
            if z not in zd["zone_counts"]: continue
            pct     = zd["zone_time"][z] / zd["total_z_time"] * 100
            color   = zone_colors[z]
            bar_len = int(pct / 3.5)
            bar = Text()
            bar.append("█" * bar_len, style=color)
            bar.append(f"  {pct:.0f}%", style="dim")
            zone_table.add_row(z, zd["zone_labels"][z], str(zd["zone_counts"][z]),
                               hms(zd["zone_time"][z] * 60), bar)

        summary = Text("\n")
        summary.append("  Easy Z1+Z2  ", style="dim")
        summary.append(f"{zd['z1z2_pct']:.0f}%", style="green bold")
        summary.append("   Tempo Z3  ", style="dim")
        summary.append(f"{zd['z3_pct']:.0f}%", style="yellow bold")
        summary.append("   Hard Z4+Z5  ", style="dim")
        summary.append(f"{zd['z4z5_pct']:.0f}%", style="red bold")
        summary.append("\n  Polarized optimum: ~80% easy · ~5% tempo · ~15% hard", style="dim")

        warn_lines = [zone_table, summary]
        for sev, msg in zd["warnings"]:
            if sev == "good":
                warn_lines.append(Text(f"\n  ✓  {msg}", style="green"))
            else:
                warn_lines.append(Text(f"\n  ⚠  {msg}", style="yellow"))
        zone_content = Group(*warn_lines)

    console.print(Panel(
        zone_content,
        title="[bold cyan]INTENSITY DISTRIBUTION[/bold cyan]",
        box=rbox.ROUNDED, padding=(0, 1),
    ))
    console.print()

    # ── Sport Metrics ─────────────────────────────────────────────────────────
    sport_panels = []

    if data["running"]:
        r  = data["running"]
        rt = Table(box=None, show_header=False, padding=(0, 2))
        rt.add_column(style="dim",   width=16)
        rt.add_column(style="white")
        rt.add_row("Total",    f"{r['total_km']:.0f} km   {r['count']} runs")
        rt.add_row("Avg run",  f"{r['avg_km']:.1f} km")
        rt.add_row("Avg long", f"{r['avg_long_km']:.1f} km  (top 5)")
        rt.add_row("Pace",     r["overall_pace"] or "—")
        pc   = r["pace_change_pct"]
        pc_s = "green" if pc > 2 else ("red" if pc < -2 else "dim")
        pc_l = "faster ✓" if pc > 2 else ("slower ✗" if pc < -2 else "flat")
        rt.add_row("Pace trend", f"[{pc_s}]{pc:+.1f}%  {pc_l}[/{pc_s}]")
        if r["cadence"]:
            cs = "green" if r["cadence"] >= 85 else "yellow"
            cn = "✓" if r["cadence"] >= 85 else "⚠ target ≥ 85 spm"
            rt.add_row("Cadence", f"[{cs}]{r['cadence']:.0f} spm  {cn}[/{cs}]")
        sport_panels.append(Panel(rt, title="[bold green]RUNNING[/bold green]", box=rbox.ROUNDED))

    if data["cycling"]:
        c  = data["cycling"]
        ct = Table(box=None, show_header=False, padding=(0, 2))
        ct.add_column(style="dim",   width=16)
        ct.add_column(style="white")
        ct.add_row("Total",    f"{c['total_km']:.0f} km   {c['count']} rides")
        ct.add_row("Avg ride", f"{c['avg_km']:.1f} km")
        if c["avg_speed"]:
            ct.add_row("Avg speed", f"{c['avg_speed']:.1f} km/h")
        if c["avg_watts"]:
            ct.add_row("Avg power", f"{c['avg_watts']:.0f} W")
        sport_panels.append(Panel(ct, title="[bold yellow]CYCLING[/bold yellow]", box=rbox.ROUNDED))

    if data["swimming"]:
        sw  = data["swimming"]
        swt = Table(box=None, show_header=False, padding=(0, 2))
        swt.add_column(style="dim",   width=16)
        swt.add_column(style="white")
        swt.add_row("Total", f"{sw['total_km']:.1f} km   {sw['count']} sessions")
        sport_panels.append(Panel(swt, title="[bold blue]SWIMMING[/bold blue]", box=rbox.ROUNDED))

    if sport_panels:
        console.print(Columns(sport_panels, equal=True, expand=True) if len(sport_panels) > 1 else sport_panels[0])
        console.print()

    # ── Consistency ───────────────────────────────────────────────────────────
    con = data["consistency"]
    cons_table = Table(box=None, show_header=False, padding=(0, 2))
    cons_table.add_column(style="dim", width=30)
    cons_table.add_column(style="bold white")

    aw   = con["active_weeks"]
    aw_s = "green" if aw >= 10 else ("yellow" if aw >= 6 else "red")
    cons_table.add_row("Active weeks  (last 12)", f"[{aw_s}]{aw} / 12[/{aw_s}]")
    cons_table.add_row("Longest consecutive days", str(con["max_streak"]))
    if con["avg_gap"]:
        cons_table.add_row("Avg days between sessions", f"{con['avg_gap']:.1f}")
    if con["max_gap"]:
        mg_s = "yellow" if con["max_gap"] > 14 else "dim"
        mg_n = "  ⚠ big gap" if con["max_gap"] > 14 else ""
        cons_table.add_row("Longest gap (days)", f"[{mg_s}]{con['max_gap']}{mg_n}[/{mg_s}]")
    if con["monotony"] is not None:
        m   = con["monotony"]
        m_s = "yellow" if m > 2 else "dim"
        m_n = "⚠ high — vary sessions more" if m > 2 else "✓ ok"
        cons_table.add_row("Training monotony", f"[{m_s}]{m:.2f}  {m_n}[/{m_s}]")

    console.print(Panel(
        cons_table,
        title="[bold cyan]CONSISTENCY & RECOVERY[/bold cyan]",
        box=rbox.ROUNDED, padding=(0, 1),
    ))
    console.print()

    # ── Apple Health ──────────────────────────────────────────────────────────
    ah = data["apple_health"]
    if ah:
        ah_table = Table(box=None, show_header=False, padding=(0, 2))
        ah_table.add_column(style="dim", width=30)
        ah_table.add_column(style="bold white")

        if ah["rhr_recent"]:
            rhr_s = "green"
            rhr_extra = ""
            if ah["rhr_prior"] and ah["rhr_recent"] > ah["rhr_prior"] + 3:
                rhr_s = "yellow"
                rhr_extra = f"  ⚠ +{ah['rhr_recent']-ah['rhr_prior']:.0f} vs prior month"
            ah_table.add_row("Resting HR  (last 30d)", f"[{rhr_s}]{ah['rhr_recent']:.0f} bpm{rhr_extra}[/{rhr_s}]")

        if ah["hrv_recent"]:
            hrv_s = "green"
            hrv_extra = ""
            if ah["hrv_prior"] and ah["hrv_recent"] < ah["hrv_prior"] * 0.85:
                hrv_s = "yellow"
                hrv_extra = "  ⚠ declining"
            ah_table.add_row("HRV SDNN  (last 30d)", f"[{hrv_s}]{ah['hrv_recent']:.0f} ms{hrv_extra}[/{hrv_s}]")

        if ah["vo2max"]:
            ah_table.add_row("VO2max  (Apple Watch est.)", f"{ah['vo2max']:.1f} mL/kg/min")

        if ah["weight_recent"]:
            w_delta = ""
            if ah["weight_prior"]:
                diff    = ah["weight_recent"] - ah["weight_prior"]
                w_delta = f"  ({diff:+.1f} kg vs prior month)"
            ah_table.add_row("Body Weight  (last 14d avg)", f"{ah['weight_recent']:.1f} kg{w_delta}")

        if ah["sleep_avg_h"] and ah["sleep_nights"] > 3:
            sl_s = "green" if ah["sleep_avg_h"] >= 7.5 else ("yellow" if ah["sleep_avg_h"] >= 6.5 else "red")
            ah_table.add_row(
                f"Sleep duration  ({ah['sleep_nights']} nights)",
                f"[{sl_s}]{ah['sleep_avg_h']:.1f} h/night[/{sl_s}]",
            )
        if ah.get("sleep_avg_score"):
            sc   = ah["sleep_avg_score"]
            sc_s = "green" if sc >= 75 else ("yellow" if sc >= 55 else "red")
            sc_g = "Good" if sc >= 75 else ("Fair" if sc >= 55 else "Poor")
            ah_table.add_row("Sleep score  (0–100)", f"[{sc_s}]{sc:.0f}  {sc_g}[/{sc_s}]")
        if ah.get("sleep_avg_deep") and ah["sleep_avg_deep"] > 0:
            dp_s = "green" if ah["sleep_avg_deep"] >= 15 else "yellow"
            rp_s = "green" if (ah.get("sleep_avg_rem") or 0) >= 18 else "yellow"
            stages = f"[{dp_s}]Deep {ah['sleep_avg_deep']:.0f}%[/{dp_s}]"
            if ah.get("sleep_avg_rem"):
                stages += f"   [{rp_s}]REM {ah['sleep_avg_rem']:.0f}%[/{rp_s}]"
            if ah.get("sleep_avg_eff"):
                eff_s   = "green" if ah["sleep_avg_eff"] >= 85 else "yellow"
                stages += f"   [{eff_s}]Eff {ah['sleep_avg_eff']:.0f}%[/{eff_s}]"
            ah_table.add_row("Sleep stages  (avg)", stages)

        console.print(Panel(
            ah_table,
            title="[bold magenta]APPLE HEALTH[/bold magenta]",
            box=rbox.ROUNDED, padding=(0, 1),
        ))
        console.print()
    else:
        console.print(Panel(
            Text(
                "  No Apple Health data found.\n\n"
                "  To enable: iPhone Health app → profile → Export All Health Data\n"
                "  Then place export.zip in this folder or ~/Downloads/",
                style="dim",
            ),
            title="[dim]APPLE HEALTH[/dim]",
            box=rbox.ROUNDED, padding=(0, 1),
        ))
        console.print()

    # ── Benchmarks & Norms ────────────────────────────────────────────────────
    ratings = data.get("benchmarks") or {}
    recs    = data.get("sport_recs") or []
    if ratings or recs:
        bm_table = Table(box=None, show_header=False, padding=(0, 2))
        bm_table.add_column(style="dim",        width=28)
        bm_table.add_column(style="bold white", width=16)
        bm_table.add_column()

        RATING_COLORS = {
            "Excellent": "green", "Athlete": "green", "Good": "green",
            "Above Average": "cyan", "Average": "yellow",
            "Below Average": "yellow", "Poor": "red", "Very Poor": "red",
            "Fair": "yellow",
        }

        for _, info in ratings.items():
            color = RATING_COLORS.get(info["rating"], "white")
            bm_table.add_row(
                info["label"],
                f"{info['value']:.0f} {info['unit']}",
                f"[{color}]{info['rating']}[/{color}]",
            )

        items: list = [bm_table]

        if recs:
            items.append(Text("\n  Top sport recommendations:", style="bold white"))
            for rec in recs:
                r     = rec["readiness"]
                color = "green" if r >= 80 else ("yellow" if r >= 60 else "red")
                bar   = Text()
                bar.append(f"  {rec['label']:26s}", style="dim")
                bar.append("█" * int(r / 5), style=color)
                bar.append("░" * (20 - int(r / 5)), style="dim")
                bar.append(f"  [{color}]{r}%[/{color}]")
                items.append(bar)
            items.append(Text("\n  Tip: run  python analyze.py --chat  to get a detailed verdict", style="dim italic"))

        console.print(Panel(
            Group(*items),
            title="[bold cyan]BENCHMARKS & SPORT READINESS[/bold cyan]",
            box=rbox.ROUNDED, padding=(0, 1),
        ))
        console.print()

    # ── Verdict ───────────────────────────────────────────────────────────────
    verdict_items = []
    for sev, msg in data["verdict"]:
        if sev == "critical":
            verdict_items.append(Text(f"  ⚡ {msg}", style="bold red"))
        elif sev == "warning":
            verdict_items.append(Text(f"  ⚠  {msg}", style="yellow"))
        else:
            verdict_items.append(Text(f"  ✓  {msg}", style="bold green"))

    console.print(Panel(
        Group(*verdict_items),
        title="[bold white]VERDICT[/bold white]",
        box=rbox.HEAVY, style="white", padding=(0, 1),
    ))
    console.print()


def _print_plain(data: dict, athlete: dict) -> None:
    """Minimal fallback when rich is unavailable."""
    W    = 70
    name = f"{athlete.get('firstname', '')} {athlete.get('lastname', '')}".strip()
    print("\n" + "═" * W)
    print(f"  STRAVA FITNESS ANALYSIS — {name}")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("═" * W)

    ov = data["overview"]
    print(f"\n  {ov['total']} activities · {ov['total_km']:.0f} km · {hms(ov['total_h']*3600)}")
    print(f"  {ov['runs']} runs · {ov['rides']} rides · {ov['swims']} swims")
    print(f"  Avg/week: {ov['avg_km_week']:.1f} km · {ov['avg_h_week']:.1f} h")

    print(f"\n{'─'*W}\n  VERDICT")
    print(f"{'─'*W}")
    for sev, msg in data["verdict"]:
        icon = "⚡" if sev == "critical" else ("⚠" if sev == "warning" else "✓")
        print(f"  {icon} {msg}")
    print("\n" + "═" * W + "\n")
