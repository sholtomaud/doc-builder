import json
import logging
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import markdown
import pandas as pd
import typer
from docx.shared import Inches
from docxtpl import DocxTemplate, InlineImage
from typing_extensions import Annotated

from analysis import run_analysis
from plotting import generate_plot

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

app = typer.Typer()


class ReportGenerator:
    """Handles report generation with docxtpl templates."""

    def __init__(self, study_dir: Path, template_dir: Path, output_dir: Path):
        self.study_dir = study_dir
        self.template_dir = template_dir
        self.output_dir = output_dir
        self.temp_image_dir = output_dir / "tmp_images"
        self.temp_image_dir.mkdir(exist_ok=True)

        # Load configuration
        config_path = study_dir / "report.json"
        if not config_path.exists():
            raise FileNotFoundError(f"report.json not found in {study_dir}")

        with open(config_path) as f:
            self.config = json.load(f)

        # Initialize template
        template_path = template_dir / self.config["template"]
        self.doc = DocxTemplate(template_path)

        # Load data once
        data_path = study_dir / self.config["data_source"]
        self.data = pd.read_csv(data_path) if data_path.exists() else pd.DataFrame()

    def build_context(self) -> Dict[str, Any]:
        """Builds the complete context for template rendering."""
        context = self._build_basic_context()
        context.update(self._build_sections_context())
        context.update(self._build_computations_context())
        context.update(self._build_images_context())
        return context

    def _build_basic_context(self) -> Dict[str, Any]:
        """Builds basic metadata context."""
        return {
            "study_name": self.study_dir.name,
            "author": self.config.get("author", "N/A"),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "data_source": self.config.get("data_source", "N/A"),
        }

    def _build_sections_context(self) -> Dict[str, Any]:
        """Builds context from markdown sections."""
        context = {}
        for key, rel_path in self.config.get("sections", {}).items():
            md_path = self.study_dir / rel_path
            html = markdown.markdown(
                self._read_and_strip_markdown_heading(md_path)
            )
            context[key] = html.replace("<p>", "").replace("</p>", "")
        return context

    def _build_computations_context(self) -> Dict[str, Any]:
        """Builds context from computations and statistical analyses."""
        context = {
            'stats': {},
            'computed': {}
        }

        # New analysis pipeline
        analyses = self.config.get("analyses", {})

        if not analyses:
            # Legacy computations (for backward compatibility)
            context.update(self._run_legacy_computations())

        # Legacy top-level 'computations' block
        if "computations" in self.config and isinstance(
            self.config["computations"], dict
        ):
            for key, formula in self.config['computations'].items():
                comp_config = {"key": key, "type": "custom_formula", "formula": formula}
                try:
                    result = self._run_computation(comp_config)
                    # Check if the result is a dictionary with an error key
                    if isinstance(result, dict) and 'error' in result:
                        context['computed'][key] = 0.0  # Provide a default value
                        logging.error(
                            f"Failed to run legacy computation '{key}': "
                            f"{result['error']}"
                        )
                    else:
                        context['computed'][key] = result
                        logging.info(f"Completed legacy computation '{key}': {result}")
                except Exception as e:
                    logging.error(f"Failed to run legacy computation '{key}': {e}")
                    context['computed'][key] = {"error": str(e)}

        # New analysis pipeline
        analyses = self.config.get("analyses", {})

        # Run statistical analyses
        for stat_config in analyses.get("stats", []):
            stat_key = stat_config["key"]
            try:
                result = run_analysis(stat_config, self.data)
                context['stats'][stat_key] = result
                logging.info(f"Completed analysis '{stat_key}': {result}")
            except Exception as e:
                logging.error(f"Failed to run analysis '{stat_key}': {e}")
                context['stats'][stat_key] = {"error": str(e)}

        # Run custom computations defined in config
        for comp_config in analyses.get("computations", []):
            comp_key = comp_config["key"]
            try:
                result = self._run_computation(comp_config)
                context['computed'][comp_key] = result
                logging.info(f"Completed computation '{comp_key}': {result}")
            except Exception as e:
                logging.error(f"Failed to run computation '{comp_key}': {e}")
                context['computed'][comp_key] = {"error": str(e)}

        return context

    def _run_computation(self, comp_config: Dict[str, Any]) -> Dict[str, Any]:
        """Runs a single computation based on configuration."""
        comp_type = comp_config.get("type")

        if comp_type == "descriptive_stats":
            return self._compute_descriptive_stats(comp_config)
        elif comp_type == "correlation":
            return self._compute_correlation(comp_config)
        elif comp_type == "custom_formula":
            return self._compute_custom_formula(comp_config)
        else:
            raise ValueError(f"Unknown computation type: {comp_type}")

    def _compute_descriptive_stats(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Computes descriptive statistics for specified columns."""
        columns = config.get("columns", [])
        if not columns or self.data.empty:
            return {}

        stats = {}
        for col in columns:
            if col in self.data.columns:
                series = self.data[col]
                stats[f"{col}_mean"] = float(series.mean())
                stats[f"{col}_std"] = float(series.std())
                stats[f"{col}_min"] = float(series.min())
                stats[f"{col}_max"] = float(series.max())
                stats[f"{col}_median"] = float(series.median())

        return stats

    def _compute_correlation(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Computes correlation between two variables."""
        var1, var2 = config.get("variables", [])
        if var1 not in self.data.columns or var2 not in self.data.columns:
            return {"error": f"Variables {var1}, {var2} not found in data"}

        correlation = self.data[var1].corr(self.data[var2])
        return {
            "correlation": float(correlation),
            "variables": [var1, var2]
        }

    def _compute_custom_formula(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluates a custom formula on the data."""
        formula = config.get("formula")
        if not formula:
            return {"error": "No formula specified"}

        try:
            # Create a safe namespace with data columns
            namespace = {col: self.data[col] for col in self.data.columns}
            namespace.update({'pd': pd})  # Add pandas for operations

            result = eval(formula, {"__builtins__": {}}, namespace)

            # Handle different result types
            if hasattr(result, 'mean'):  # Series-like
                return {
                    "value": float(result.mean()),
                    "type": "series_mean"
                }
            else:  # Scalar
                return {
                    "value": float(result),
                    "type": "scalar"
                }
        except Exception as e:
            return {"error": f"Formula evaluation failed: {str(e)}"}

    def _run_legacy_computations(self) -> Dict[str, Any]:
        """
        Runs legacy computations for backward compatibility.
        This method is kept for older report.json formats and provides default
        values to avoid breaking templates that expect these keys.
        """
        context = {
            "avg_flow_rate": 0.0,
            "max_efficiency": 0.0,
            "power_output": 0.0,
        }

        if not self.data.empty:
            if "flow_rate" in self.data.columns:
                context["avg_flow_rate"] = float(self.data["flow_rate"].mean())
            if "efficiency" in self.data.columns:
                context["max_efficiency"] = float(self.data["efficiency"].max() * 100)
            if "power_output" in self.data.columns:
                context["power_output"] = float(self.data["power_output"].mean())

        return context

    def _build_images_context(self) -> Dict[str, Any]:
        """Builds context for all images (plots and Rhino)."""
        image_context = {}

        # Generate plots from analyses
        analyses = self.config.get("analyses", {})
        for plot_config in analyses.get("plots", []):
            plot_key = plot_config["key"]
            try:
                plot_path = generate_plot(plot_config, self.data, self.temp_image_dir)
                image_context[plot_key] = InlineImage(
                    self.doc, str(plot_path), width=Inches(6)
                )
                logging.info(f"Generated plot '{plot_key}'")
            except Exception as e:
                logging.error(f"Failed to generate plot '{plot_key}': {e}")

        # Legacy image generation
        for key, image_config in self.config.get("images", {}).items():
            try:
                plot_config = {"key": key, "type": image_config["type"], **image_config}
                plot_data_path = self.study_dir / image_config.get(
                    "data_source", self.config["data_source"]
                )
                plot_data = (
                    pd.read_csv(plot_data_path)
                    if plot_data_path.exists()
                    else self.data
                )

                plot_path = generate_plot(plot_config, plot_data, self.temp_image_dir)
                image_context[key] = InlineImage(
                    self.doc, str(plot_path), width=Inches(6)
                )
            except Exception as e:
                logging.error(f"Failed to generate legacy image '{key}': {e}")

        # Rhino images
        rhino_images = self._process_rhino_images()
        image_context.update(rhino_images)

        return image_context

    def _process_rhino_images(self) -> Dict[str, InlineImage]:
        """Processes Rhino image generation."""
        rhino_executable = self._find_rhino_executable()
        if not rhino_executable:
            logging.warning(
                "Rhino executable not found. Skipping Rhino image generation."
            )
            return {}

        rhino_config = self.config.get("rhino")
        if not rhino_config or not rhino_config.get("enabled", False):
            return {}

        image_context = {}
        for key, image_spec in rhino_config.get("images", {}).items():
            try:
                path = self._generate_rhino_image(image_spec, rhino_executable)
                if path:
                    image_context[key] = InlineImage(
                        self.doc, str(path), width=Inches(4)
                    )
                    logging.info(f"Generated Rhino image '{key}'")
            except Exception as e:
                logging.error(f"Failed to generate Rhino image '{key}': {e}")

        return image_context

    def _generate_rhino_image(
        self, rhino_config: Dict[str, Any], rhino_executable: str
    ) -> Path | None:
        """Generates a single Rhino image."""
        output_filename = f"{self.study_dir.name}_{rhino_config['output_filename']}"
        output_path = self.temp_image_dir / output_filename

        # Execute pre-commands
        for command in rhino_config.get("pre_commands", []):
            self._run_rhinocode_command(rhino_executable, command)

        # Capture image
        capture_command = (
            f'_-ViewCaptureToFile '
            f'"{output_path}" '
            f'Width={rhino_config.get("width", 1920)} '
            f'Height={rhino_config.get("height", 1080)} '
            f'Scale=1 DrawGrid=No DrawAxes=No DrawWorldAxes=No DrawCPlaneAxes=No '
            f'TransparentBackground=Yes '
            f'_Enter'
        )
        self._run_rhinocode_command(rhino_executable, capture_command)
        time.sleep(rhino_config.get("delay", 2))

        # Execute post-commands
        for command in rhino_config.get("post_commands", []):
            self._run_rhinocode_command(rhino_executable, command)

        return output_path if output_path.exists() else None

    def _find_rhino_executable(self) -> str | None:
        """Finds the Rhino executable in common locations."""
        possible_paths = [
            "/Applications/RhinoWIP.app/Contents/Resources/bin/rhinocode",
            "/Applications/Rhino 8.app/Contents/Resources/bin/rhinocode",
        ]
        for path in possible_paths:
            if os.path.exists(path):
                return path
        return None

    def _run_rhinocode_command(self, rhino_executable: str, command: str):
        """Executes a command using the rhinocode executable."""
        cmd = [rhino_executable, "command", command]
        logging.info(f"Executing Rhino command: {command}")
        process = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if process.stdout:
            logging.info(f"  [>] Rhino Stdout: {process.stdout.strip()}")
        if process.stderr:
            logging.warning(f"  [>] Rhino Stderr: {process.stderr.strip()}")
        if process.returncode != 0:
            logging.error(
                f"  [!] Rhino command failed with exit code {process.returncode}"
            )
        return process

    def _read_and_strip_markdown_heading(self, path: Path) -> str:
        """Reads a markdown file and removes the first line if it's a heading."""
        if not path.exists():
            return f"Content for {path.stem} not found."
        lines = path.read_text().splitlines()
        if lines and lines[0].strip().startswith("#"):
            return "\n".join(lines[1:]).strip()
        else:
            return "\n".join(lines).strip()

    def generate(self) -> Path:
        """Generates the report and returns the output path."""
        context = self.build_context()
        self.doc.render(context)

        output_file = self.output_dir / f"{self.study_dir.name}_report.docx"
        self.doc.save(output_file)
        logging.info(f"Successfully generated report: {output_file}")
        return output_file


@app.command()
def generate(
    study_dir: Annotated[
        Path, typer.Argument(help="Directory containing the case study files.")
    ],
    template_dir: Annotated[
        Path,
        typer.Option("--template-dir", help="Directory containing the .docx template."),
    ] = Path("templates"),
    output_dir: Annotated[
        Path,
        typer.Option("--output-dir", help="Directory to save the generated document."),
    ] = Path("generated_studies"),
):
    """Generates a single report from a study directory."""
    output_dir.mkdir(exist_ok=True)
    generator = ReportGenerator(study_dir, template_dir, output_dir)
    generator.generate()


@app.command()
def batch(
    studies_dir: Annotated[
        Path, typer.Argument(help="Directory containing all case study subdirectories.")
    ],
    template_dir: Annotated[
        Path,
        typer.Option("--template-dir", help="Directory containing the .docx template."),
    ] = Path("templates"),
    output_dir: Annotated[
        Path,
        typer.Option("--output-dir", help="Directory to save the generated documents."),
    ] = Path("generated_studies"),
):
    """Generates reports for all studies in a directory."""
    output_dir.mkdir(exist_ok=True)
    for study_dir in studies_dir.iterdir():
        if study_dir.is_dir():
            try:
                generator = ReportGenerator(study_dir, template_dir, output_dir)
                generator.generate()
            except Exception as e:
                logging.error(f"Failed to generate report for {study_dir.name}: {e}")


if __name__ == "__main__":
    app()
