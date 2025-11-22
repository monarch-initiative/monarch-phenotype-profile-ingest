"""Command line interface for monarch-phenotype-profile-ingest."""
import logging

from pathlib import Path

from kghub_downloader.download_utils import download_from_yaml
from koza.runner import KozaRunner
from koza.model.formats import OutputFormat
import typer

app = typer.Typer()
logger = logging.getLogger(__name__)


@app.callback()
def callback(version: bool = typer.Option(False, "--version", is_eager=True),
):
    """monarch-phenotype-profile-ingest CLI."""
    if version:
        from monarch_phenotype_profile_ingest import __version__
        typer.echo(f"monarch-phenotype-profile-ingest version: {__version__}")
        raise typer.Exit()


@app.command()
def download(force: bool = typer.Option(False, help="Force download of data, even if it exists")):
    """Download data for monarch-phenotype-profile-ingest."""
    typer.echo("Downloading data for monarch-phenotype-profile-ingest...")
    download_config = Path(__file__).parent / "download.yaml"
    download_from_yaml(yaml_file=download_config, output_dir=".", ignore_cache=force)


@app.command()
def transform(
    output_dir: str = typer.Option("output", help="Output directory for transformed data"),
    row_limit: int = typer.Option(None, help="Number of rows to process"),
    verbose: int = typer.Option(False, help="Whether to be verbose"),
):
    """Run the Koza transform for monarch-phenotype-profile-ingest."""
    typer.echo("Transforming data for monarch-phenotype-profile-ingest...")
    transform_code = Path(__file__).parent / "transform.yaml"
    config, runner = KozaRunner.from_config_file(
        str(transform_code),
        output_dir=output_dir,
        output_format=OutputFormat.tsv,
        row_limit=row_limit,
    )
    runner.run()
    

if __name__ == "__main__":
    app()
