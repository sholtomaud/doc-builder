import json
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
                paragraph.text = paragraph.text.replace(placeholder, "")
                run = paragraph.add_run()
                run.add_picture(str(path), width=Inches(5))


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

    image_paths = {}
    for key, image_config in config.get("images", {}).items():
        image_paths[key] = generate_image(
            image_config, study_dir.name, data_path, temp_image_dir
        )

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
