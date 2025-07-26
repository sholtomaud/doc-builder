import json
import logging
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

import markdown
import pandas as pd
import typer
from docx.shared import Inches
from docxtpl import DocxTemplate, InlineImage
from typing_extensions import Annotated

from .plotting import generate_plot
from .statistics import run_analysis

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

app = typer.Typer()


def read_and_strip_markdown_heading(path: Path) -> str:
    """Reads a markdown file and removes the first line if it's a heading."""
    if not path.exists():
        return f"Content for {path.stem} not found."
    lines = path.read_text().splitlines()
    if lines and lines[0].strip().startswith("#"):
        return "\n".join(lines[1:]).strip()
    else:
        return "\n".join(lines).strip()


def find_rhino_executable():
    """Finds the Rhino executable in common locations."""
    possible_paths = [
        "/Applications/RhinoWIP.app/Contents/Resources/bin/rhinocode",
        "/Applications/Rhino 8.app/Contents/Resources/bin/rhinocode",
    ]
    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None


def run_rhinocode_command(rhino_executable: str, command: str):
    """Executes a command using the rhinocode executable."""
    if not rhino_executable:
        logging.error("Rhino executable not found.")
        return None
    cmd = [rhino_executable, "command", command]
    logging.info(f"Executing Rhino command: {command}")
    process = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if process.stdout:
        logging.info(f"  [>] Rhino Stdout: {process.stdout.strip()}")
    if process.stderr:
        logging.warning(f"  [>] Rhino Stderr: {process.stderr.strip()}")
    if process.returncode != 0:
        logging.error(f"  [!] Rhino command failed with exit code {process.returncode}")
    return process


def generate_rhino_image(
    rhino_config: dict, study_name: str, temp_dir: Path, rhino_executable: str
) -> Path | None:
    """Generates an image using Rhino."""
    output_filename = f"{study_name}_{rhino_config['output_filename']}"
    output_path = temp_dir.resolve() / output_filename
    output_path.parent.mkdir(parents=True, exist_ok=True)
    for command in rhino_config.get("pre_commands", []):
        run_rhinocode_command(rhino_executable, command)
    capture_command = (
        f'_-ViewCaptureToFile '
        f'"{output_path}" '
        f'Width={rhino_config.get("width", 1920)} '
        f'Height={rhino_config.get("height", 1080)} '
        f'Scale=1 DrawGrid=No DrawAxes=No DrawWorldAxes=No DrawCPlaneAxes=No '
        f'TransparentBackground=Yes '
        f'_Enter'
    )
    run_rhinocode_command(rhino_executable, capture_command)
    time.sleep(rhino_config.get("delay", 2))
    for command in rhino_config.get("post_commands", []):
        run_rhinocode_command(rhino_executable, command)
    if output_path.exists():
        logging.info(f"Successfully generated Rhino image: {output_path}")
        return output_path
    else:
        logging.error(f"ERROR: Rhino image not found at {output_path}")
        return None


def process_rhino_images(
    config: dict, study_name: str, temp_dir: Path, doc: DocxTemplate
) -> dict:
    """Processes all Rhino image configurations and returns a context dict."""
    rhino_executable = find_rhino_executable()
    if not rhino_executable:
        logging.warning("Rhino executable not found. Skipping Rhino image generation.")
        return {}

    rhino_config = config.get("rhino")
    if not rhino_config or not rhino_config.get("enabled", False):
        return {}

    image_context = {}
    for key, image_spec in rhino_config.get("images", {}).items():
        path = generate_rhino_image(image_spec, study_name, temp_dir, rhino_executable)
        if path:
            image_context[key] = InlineImage(doc, str(path), width=Inches(4))
    return image_context


def generate_single_report(study_dir: Path, template_dir: Path, output_dir: Path):
    """
    Generates a single report from a study directory.
    """
    temp_image_dir = output_dir / "tmp_images"
    temp_image_dir.mkdir(exist_ok=True)

    config_path = study_dir / "report.json"
    if not config_path.exists():
        logging.warning(f"Warning: report.json not found in {study_dir}, skipping.")
        return

    with open(config_path) as f:
        config = json.load(f)

    template_path = template_dir / config["template"]
    doc = DocxTemplate(template_path)

    # --- Basic Context ---
    context = {
        "study_name": study_dir.name,
        "author": config.get("author", "N/A"),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "avg_flow_rate": 0,
        "max_efficiency": 0,
        "power_output": 0,
    }

    # --- Markdown Sections ---
    for key, rel_path in config.get("sections", {}).items():
        md_path = study_dir / rel_path
        context[key] = markdown.markdown(read_and_strip_markdown_heading(md_path))

    # --- Data Loading ---
    data_path = study_dir / config["data_source"]
    data = pd.read_csv(data_path) if data_path.exists() else pd.DataFrame()

    # --- Legacy Data Calculation ---
    required_cols = ["flow_rate", "efficiency", "power_output"]
    if not data.empty and all(col in data.columns for col in required_cols):
        context["avg_flow_rate"] = data["flow_rate"].mean()
        context["max_efficiency"] = data["efficiency"].max() * 100
        context["power_output"] = data["power_output"].mean()

    # --- New Analysis Pipeline ---
    context['stats'] = {}
    image_context = {}
    analyses = config.get("analyses", {})

    # Generate plots
    for plot_config in analyses.get("plots", []):
        plot_key = plot_config["key"]
        try:
            plot_path = generate_plot(plot_config, data, temp_image_dir)
            image_context[plot_key] = InlineImage(doc, str(plot_path), width=Inches(6))
        except Exception as e:
            logging.error(f"Failed to generate plot '{plot_key}': {e}")

    # Run statistical analyses
    for stat_config in analyses.get("stats", []):
        stat_key = stat_config["key"]
        try:
            result = run_analysis(stat_config, data)
            context['stats'][stat_key] = result
        except Exception as e:
            logging.error(f"Failed to run analysis '{stat_key}': {e}")

    # --- Image Generation ---
    # Process Rhino images and add them to the context
    rhino_image_context = process_rhino_images(
        config, study_dir.name, temp_image_dir, doc
    )
    image_context.update(rhino_image_context)

    # Add all generated images to the main context
    context.update(image_context)

    # --- Rendering ---
    doc.render(context)
    output_file = output_dir / f"{study_dir.name}_report.docx"
    doc.save(output_file)
    logging.info(f"Successfully generated report: {output_file}")


@app.command()
def generate(
    study_dir: Annotated[
        Path, typer.Argument(help="Directory containing the case study files.")
    ],
    template_dir: Annotated[
        Path,
        typer.Option(
            "--template-dir", help="Directory containing the .docx template."
        ),
    ] = Path("templates"),
    output_dir: Annotated[
        Path,
        typer.Option("--output-dir", help="Directory to save the generated document."),
    ] = Path("generated_studies"),
):
    """Generates a single report from a study directory."""
    output_dir.mkdir(exist_ok=True)
    generate_single_report(study_dir, template_dir, output_dir)


@app.command()
def batch(
    studies_dir: Annotated[
        Path,
        typer.Argument(help="Directory containing all case study subdirectories."),
    ],
    template_dir: Annotated[
        Path,
        typer.Option(
            "--template-dir", help="Directory containing the .docx template."
        ),
    ] = Path("templates"),
    output_dir: Annotated[
        Path,
        typer.Option(
            "--output-dir", help="Directory to save the generated documents."
        ),
    ] = Path("generated_studies"),
):
    """Generates reports for all studies in a directory."""
    output_dir.mkdir(exist_ok=True)
    for study_dir in studies_dir.iterdir():
        if study_dir.is_dir():
            generate_single_report(study_dir, template_dir, output_dir)


if __name__ == "__main__":
    app()
