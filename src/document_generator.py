import json
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import typer
from docx.shared import Inches
from docxtpl import DocxTemplate
from typing_extensions import Annotated

app = typer.Typer()


def generate_image(
    image_config: dict, study_name: str, data_path: Path, temp_dir: Path
) -> Path:
    """Generates an image based on the provided configuration."""
    image_path = temp_dir / f"{study_name}_{image_config['type']}.png"
    plt.figure()

    if image_config["type"] == "pairplot":
        data = pd.read_csv(data_path)
        sns.pairplot(data)
    elif image_config["type"] == "placeholder":
        text = image_config.get("text", "Placeholder").replace(
            "{{ study_name }}", study_name
        )
        plt.text(0.5, 0.5, text, ha="center", va="center")

    plt.savefig(image_path)
    plt.close()
    return image_path


def read_and_strip_markdown_heading(path: Path) -> str:
    """Reads a markdown file and removes the first line if it's a heading."""
    if not path.exists():
        return f"Content for {path.stem} not found."

    lines = path.read_text().splitlines()

    if lines and lines[0].strip().startswith("#"):
        return "\n".join(lines[1:]).strip()
    else:
        return "\n".join(lines).strip()


def replace_image_placeholders(doc, image_paths):
    """
    Finds image placeholders like '{$ img:key $}' in the document and replaces them
    with the actual images.
    """
    for key, path in image_paths.items():
        placeholder = f"{{$ img:{key} $}}"
        for paragraph in doc.paragraphs:
            if placeholder in paragraph.text:
                # If the placeholder is found, clear the paragraph and add the picture.
                # This avoids issues with leftover text if the placeholder is not alone.
                if paragraph.text.strip() == placeholder:
                    paragraph.clear()
                    run = paragraph.add_run()
                    run.add_picture(str(path), width=Inches(6)) # Standard width
                else:
                    # If there's other text, do a simple replacement
                    # This is less robust but preserves surrounding text.
                    text_before, _, text_after = paragraph.text.partition(placeholder)
                    paragraph.text = text_before
                    run = paragraph.add_run()
                    run.add_picture(str(path), width=Inches(6))
                    paragraph.add_run(text_after)


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
        print("ERROR: Rhino executable not found.")
        return None

    cmd = [rhino_executable, "command", command]
    print(f"Executing Rhino command: {command}")
    process = subprocess.run(cmd, capture_output=True, text=True, check=False)

    # Always print stdout and stderr for debugging purposes
    if process.stdout:
        print(f"  [>] Rhino Stdout: {process.stdout.strip()}")
    if process.stderr:
        print(f"  [>] Rhino Stderr: {process.stderr.strip()}")

    if process.returncode != 0:
        print(f"  [!] Rhino command failed with exit code {process.returncode}")

    return process


def generate_rhino_image(
    rhino_config: dict, study_name: str, temp_dir: Path, rhino_executable: str
) -> Path | None:
    """Generates an image using Rhino."""
    output_filename = f"{study_name}_{rhino_config['output_filename']}"
    # Resolve to an absolute path to avoid issues with CWD
    output_path = temp_dir.resolve() / output_filename

    # Ensure the output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Run pre-commands if any
    for command in rhino_config.get("pre_commands", []):
        run_rhinocode_command(rhino_executable, command)

    # The main view capture command
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

    # Give Rhino a moment to write the file
    time.sleep(rhino_config.get("delay", 2))

    # Run post-commands if any
    for command in rhino_config.get("post_commands", []):
        run_rhinocode_command(rhino_executable, command)

    if output_path.exists():
        print(f"Successfully generated Rhino image: {output_path}")
        return output_path
    else:
        print(f"ERROR: Rhino image not found at {output_path}")
        return None


def process_rhino_images(config: dict, study_name: str, temp_dir: Path) -> dict:
    """Processes all Rhino image configurations."""
    rhino_executable = find_rhino_executable()
    if not rhino_executable:
        print("Warning: Rhino executable not found. Skipping Rhino image generation.")
        return {}

    rhino_config = config.get("rhino")
    if not rhino_config or not rhino_config.get("enabled", False):
        return {}

    image_paths = {}
    for key, image_spec in rhino_config.get("images", {}).items():
        path = generate_rhino_image(image_spec, study_name, temp_dir, rhino_executable)
        if path:
            image_paths[key] = path
    return image_paths




def generate_single_report(study_dir: Path, template_dir: Path, output_dir: Path):
    """
    Generates a single report from a study directory.
    """
    temp_image_dir = output_dir / "tmp_images"
    temp_image_dir.mkdir(exist_ok=True)

    config_path = study_dir / "report.json"
    if not config_path.exists():
        print(f"Warning: report.json not found in {study_dir}, skipping.")
        return

    with open(config_path) as f:
        config = json.load(f)

    template_path = template_dir / config["template"]
    doc = DocxTemplate(template_path)

    context = {
        "study_name": study_dir.name,
        "author": config.get("author", "N/A"),
        "date": datetime.now().strftime("%Y-%m-%d"),
    }

    for key, rel_path in config.get("sections", {}).items():
        md_path = study_dir / rel_path
        context[key] = read_and_strip_markdown_heading(md_path)

    data_path = study_dir / config["data_source"]
    if data_path.exists():
        data = pd.read_csv(data_path)
        context["avg_flow_rate"] = data["flow_rate"].mean()
        context["max_efficiency"] = data["efficiency"].max() * 100
        context["power_output"] = data["power_output"].mean()

    doc.render(context)

    # Generate standard images
    image_paths = {}
    for key, image_config in config.get("images", {}).items():
        image_paths[key] = generate_image(
            image_config, study_dir.name, data_path, temp_image_dir
        )

    # Generate Rhino images
    rhino_image_paths = process_rhino_images(config, study_dir.name, temp_image_dir)
    image_paths.update(rhino_image_paths)

    replace_image_placeholders(doc.docx, image_paths)

    output_file = output_dir / f"{study_dir.name}_report.docx"
    doc.save(output_file)
    print(f"Successfully generated report: {output_file}")


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
