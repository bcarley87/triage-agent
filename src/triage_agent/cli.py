import click


@click.group()
def cli() -> None:
    """Triage Agent CLI."""


@cli.command()
def extract_candidates() -> None:
    """Run the nightly followup candidate extraction job."""
    click.echo("candidate job placeholder")
