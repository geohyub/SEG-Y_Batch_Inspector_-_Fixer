"""Command-line interface for SEG-Y Batch Inspector & Fixer."""

from __future__ import annotations

from pathlib import Path

import click

from segy_toolbox import __version__


@click.group()
@click.version_option(__version__, prog_name="segy-toolbox")
def cli():
    """SEG-Y Batch Inspector & Fixer -- validate and edit SEG-Y file headers."""


@cli.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--output", "-o", default=None, help="Output Excel report path")
def validate(path: str, output: str | None):
    """Validate SEG-Y file(s) integrity."""
    from segy_toolbox.core.engine import SegyEngine
    from segy_toolbox.reporting.excel_report import write_validation_report
    from segy_toolbox.models import BatchResult

    engine = SegyEngine()
    p = Path(path)

    if p.is_file():
        files = [str(p)]
    elif p.is_dir():
        files = sorted(
            str(f) for f in p.iterdir()
            if f.suffix.lower() in {".segy", ".sgy", ".seg"}
        )
    else:
        click.echo(f"Error: '{path}' is not a valid file or directory", err=True)
        return

    if not files:
        click.echo("No SEG-Y files found.", err=True)
        return

    results: list[BatchResult] = []
    for filepath in files:
        name = Path(filepath).name
        click.echo(f"Validating: {name}...")
        try:
            info = engine.load_file(filepath)
            val = engine.validate(info)

            status_color = {"PASS": "green", "FAIL": "red", "WARNING": "yellow"}.get(
                val.overall_status, "white"
            )
            click.echo(
                f"  Result: {click.style(val.overall_status, fg=status_color)} "
                f"({len(val.checks)} checks)"
            )

            for check in val.checks:
                icon = {"PASS": "+", "FAIL": "X", "WARNING": "!"}.get(check.status, "?")
                click.echo(f"    [{icon}] {check.name}: {check.message}")
                if check.details:
                    click.echo(f"        {check.details}")

            results.append(BatchResult(
                filename=name,
                status=val.overall_status,
                message=f"{len(val.checks)} checks",
                validation_before=val,
            ))
        except Exception as e:
            click.echo(f"  Error: {e}", err=True)
            results.append(BatchResult(filename=name, status="FAILURE", message=str(e)))

    # Export report
    if output:
        write_validation_report(results, output)
        click.echo(f"\nReport saved: {output}")
    elif len(files) > 1:
        default_output = "validation_report.xlsx"
        write_validation_report(results, default_output)
        click.echo(f"\nReport saved: {default_output}")


@cli.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--config", "-c", type=click.Path(exists=True), required=True,
              help="YAML configuration file")
@click.option("--dry-run", is_flag=True, help="Preview changes without writing")
@click.option("--output-dir", "-o", default=None, help="Output directory")
def edit(path: str, config: str, dry_run: bool, output_dir: str | None):
    """Apply edits defined in a YAML config to SEG-Y file(s)."""
    from segy_toolbox.config import EditConfig
    from segy_toolbox.core.engine import SegyEngine
    from segy_toolbox.reporting.changelog import write_changelog_csv

    cfg = EditConfig.load(config)
    if dry_run:
        cfg.dry_run = True
    if output_dir:
        cfg.output_dir = output_dir

    engine = SegyEngine(cfg)
    job = cfg.build_edit_job()
    p = Path(path)

    if p.is_file():
        files = [str(p)]
    elif p.is_dir():
        files = sorted(
            str(f) for f in p.iterdir()
            if f.suffix.lower() in {".segy", ".sgy", ".seg"}
        )
    else:
        click.echo(f"Error: '{path}' is not valid", err=True)
        return

    if not files:
        click.echo("No SEG-Y files found.", err=True)
        return

    n_edits = len(job.ebcdic_edits) + len(job.binary_edits) + len(job.trace_edits)
    click.echo(f"Config: {n_edits} edit operations")
    click.echo(f"Files: {len(files)}")
    click.echo(f"Mode: {'DRY RUN' if dry_run else 'APPLY'}")
    click.echo()

    if dry_run:
        for filepath in files:
            name = Path(filepath).name
            click.echo(f"--- Dry Run: {name} ---")
            preview = engine.preview(filepath, job)

            if preview.get("binary_preview"):
                for p_item in preview["binary_preview"]:
                    click.echo(
                        f"  Binary: {p_item['field']} "
                        f"{p_item['before']} -> {p_item['after']}"
                    )

            if preview.get("trace_preview"):
                for df in preview["trace_preview"]:
                    changed = df[df["changed"] == True]
                    click.echo(f"  Trace Header: {len(changed)} traces would change")
        return

    # Apply edits
    engine.set_callbacks(
        on_log=lambda msg: click.echo(f"  {msg}"),
    )
    results = engine.run_batch(files, job)

    # Summary
    click.echo()
    click.echo("=== Summary ===")
    all_changes = []
    for r in results:
        color = {"SUCCESS": "green", "FAILURE": "red", "SKIPPED": "yellow"}.get(
            r.status, "white"
        )
        click.echo(
            f"  {r.filename}: {click.style(r.status, fg=color)} "
            f"({len(r.changes)} changes, {r.duration_seconds:.1f}s)"
        )
        all_changes.extend(r.changes)

    if all_changes:
        changelog_path = "changelog.csv"
        write_changelog_csv(all_changes, changelog_path)
        click.echo(f"\nChangelog saved: {changelog_path}")


@cli.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--show", is_flag=True, help="Display EBCDIC header text")
@click.option("--template", default=None, type=click.Path(exists=True),
              help="Apply EBCDIC template file")
@click.option("--output", "-o", default=None, help="Output file path")
def ebcdic(path: str, show: bool, template: str | None, output: str | None):
    """View or edit the EBCDIC textual header."""
    from segy_toolbox.io.reader import SegyFileReader
    from segy_toolbox.io.ebcdic import format_lines_display

    reader = SegyFileReader()
    info = reader.open(path)

    if show or (not template):
        click.echo(f"File: {info.filename}")
        click.echo(f"Encoding: {info.ebcdic_encoding}")
        click.echo()
        click.echo(format_lines_display(info.ebcdic_lines))
        return

    if template:
        from segy_toolbox.core.ebcdic_editor import EbcdicEditor
        from segy_toolbox.io.writer import SegyFileWriter
        from segy_toolbox.models import EbcdicEdit, EditJob

        edit = EbcdicEdit(mode="template", template_path=template)
        job = EditJob(ebcdic_edits=[edit])

        writer = SegyFileWriter()
        out_path = output or path
        if out_path != path:
            import shutil
            shutil.copy2(path, out_path)

        changes = writer.apply_edits(out_path, job, filename=Path(path).name)
        click.echo(f"EBCDIC header updated: {len(changes)} lines changed")
        click.echo(f"Output: {out_path}")


@cli.command()
def gui():
    """Launch the GUI application."""
    from segy_toolbox.gui.app import main
    main()


if __name__ == "__main__":
    cli()
