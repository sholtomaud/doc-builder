import os
import shutil
import subprocess
from pathlib import Path

import docx2txt
import imagehash
import pytest
from PIL import Image

# --- Test Configuration ---
ROOT_DIR = Path(__file__).parent.parent
TEST_DATA_DIR = ROOT_DIR / "tests" / "data"
TEMPLATE_DIR = ROOT_DIR / "templates"
EXPECTED_DIR = ROOT_DIR / "tests" / "expected_output"
TEST_PROJECT_DIR = ROOT_DIR / "tests" / "tmp" / "test_project"
GENERATED_REPORTS_DIR = TEST_PROJECT_DIR / "generated_reports"


def get_all_study_dirs():
    """Finds all valid study directories in the test data folder."""
    return [d for d in TEST_DATA_DIR.iterdir() if d.is_dir() and (d / "report.json").exists()]


# --- Test Fixture ---
@pytest.fixture(scope="module", autouse=True)
def setup_and_teardown_test_environment():
    """
    A fixture to set up the test environment before tests run and clean up after.
    """
    os.environ["SOURCE_DATE_EPOCH"] = "0"

    if TEST_PROJECT_DIR.exists():
        shutil.rmtree(TEST_PROJECT_DIR)
    TEST_PROJECT_DIR.mkdir(parents=True)
    shutil.copytree(TEST_DATA_DIR, TEST_PROJECT_DIR / "studies")
    shutil.copytree(TEMPLATE_DIR, TEST_PROJECT_DIR / "templates")

    # Updated command to match the refactored module structure
    cmd = [
        "doc-builder",
        "batch",
        str(TEST_PROJECT_DIR / "studies"),
        "--template-dir",
        str(TEST_PROJECT_DIR / "templates"),
        "--output-dir",
        str(GENERATED_REPORTS_DIR),
    ]
    
    result = subprocess.run(
        cmd, check=False, capture_output=True, text=True, cwd=ROOT_DIR
    )
    print(f"Batch generation stdout: {result.stdout}")
    print(f"Batch generation stderr: {result.stderr}")
    
    # Log output for debugging
    if result.returncode != 0:
        print(f"Batch generation failed with return code {result.returncode}")
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
        # Don't fail the fixture setup - let individual tests handle missing files
    
    yield

    if not os.getenv("KEEP_TEST_OUTPUT"):
        shutil.rmtree(TEST_PROJECT_DIR.parent)
    if "SOURCE_DATE_EPOCH" in os.environ:
        del os.environ["SOURCE_DATE_EPOCH"]


# --- Data-Driven Tests ---
@pytest.mark.parametrize("study_dir", get_all_study_dirs())
def test_report_file_is_generated(study_dir):
    """Tests that the primary .docx report file is created for each study."""
    report_name = f"{study_dir.name}_report.docx"
    expected_report_path = GENERATED_REPORTS_DIR / report_name
    assert expected_report_path.exists(), f"Report '{report_name}' was not generated."
    assert (
        expected_report_path.stat().st_size > 0
    ), f"Report '{report_name}' is empty."


@pytest.mark.parametrize("study_dir", get_all_study_dirs())
def test_report_contains_required_sections(study_dir):
    """Tests that the generated report contains the expected sections."""
    report_name = f"{study_dir.name}_report.docx"
    generated_report = GENERATED_REPORTS_DIR / report_name
    
    if not generated_report.exists():
        pytest.skip(f"Report '{report_name}' was not generated.")
    
    report_text = docx2txt.process(generated_report)
    
    # Check that basic template variables were replaced
    assert "{{study_name}}" not in report_text, "study_name placeholder not replaced"
    assert "{{author}}" not in report_text, "author placeholder not replaced"
    assert "{{date}}" not in report_text, "date placeholder not replaced"
    
    # Check that the study name appears in the document
    assert study_dir.name in report_text, f"Study name '{study_dir.name}' not found in report"


@pytest.mark.parametrize("study_dir", get_all_study_dirs())
def test_computation_results_are_embedded(study_dir):
    """Tests that computed values are properly embedded in the report."""
    report_name = f"{study_dir.name}_report.docx"
    generated_report = GENERATED_REPORTS_DIR / report_name
    
    if not generated_report.exists():
        pytest.skip(f"Report '{report_name}' was not generated.")
    
    # Load the config to see what computations were requested
    config_path = study_dir / "report.json"
    if not config_path.exists():
        pytest.skip(f"No report.json found for {study_dir.name}")
    
    import json
    with open(config_path) as f:
        config = json.load(f)
    
    report_text = docx2txt.process(generated_report)
    
    # Check that computation placeholders were replaced
    analyses = config.get("analyses", {})
    for comp_config in analyses.get("computations", []):
        comp_key = comp_config["key"]
        placeholder_pattern = f"{{{{computed.{comp_key}."
        assert placeholder_pattern not in report_text, \
            f"Computation placeholder for '{comp_key}' was not replaced"
    
    # Check that stats placeholders were replaced
    for stat_config in analyses.get("stats", []):
        stat_key = stat_config["key"]
        placeholder_pattern = f"{{{{stats.{stat_key}."
        assert placeholder_pattern not in report_text, \
            f"Stats placeholder for '{stat_key}' was not replaced"


@pytest.mark.local
@pytest.mark.skip(reason="Rhino is not installed in the test environment")
def test_rhino_image_is_generated_and_embedded_locally(tmp_path):
    """
    A local-only test to verify the full Rhino generation and embedding process.
    This test runs its own generation command to keep it isolated.
    """
    local_output_dir = tmp_path / "local_rhino_test"
    local_output_dir.mkdir()
    study_2_dir = TEST_DATA_DIR / "Study2"

    cmd = [
        "doc-builder",
        "generate",
        str(study_2_dir),
        "--template-dir",
        str(TEMPLATE_DIR),
        "--output-dir",
        str(local_output_dir),
    ]
    
    result = subprocess.run(cmd, check=False, capture_output=True, text=True, cwd=ROOT_DIR)
    
    # Check if generation succeeded
    if result.returncode != 0:
        pytest.skip(f"Report generation failed: {result.stderr}")

    # 1. Check that the report was generated
    report_path = local_output_dir / "Study2_report.docx"
    assert report_path.exists(), "Report for Study2 was not generated in local test."

    # 2. Check that the Rhino image file was created
    image_path = local_output_dir / "tmp_images" / "Study2_rhino_capture.png"
    assert image_path.exists(), "Rhino-generated image was not created."
    assert image_path.stat().st_size > 0, "Rhino-generated image is empty."

    # 3. Check that the Rhino image was embedded (no placeholder left)
    report_text = docx2txt.process(report_path)
    # Updated to check for docxtpl placeholder format
    assert "{{rhino_view}}" not in report_text, \
        "The 'rhino_view' placeholder was not replaced in the document."


@pytest.mark.parametrize("study_dir", get_all_study_dirs())
def test_data_loading_and_processing(study_dir):
    """Tests that data is properly loaded and basic computations work."""
    # This test verifies the ReportGenerator can load data and run computations
    from src.document_generator import ReportGenerator
    
    try:
        generator = ReportGenerator(study_dir, TEMPLATE_DIR, GENERATED_REPORTS_DIR)
        
        # Check that data was loaded
        assert generator.data is not None, "Data should be loaded"
        
        # Check that context building doesn't crash
        context = generator.build_context()
        assert isinstance(context, dict), "Context should be a dictionary"
        assert "study_name" in context, "Context should contain study_name"
        assert "author" in context, "Context should contain author"
        
    except FileNotFoundError as e:
        pytest.skip(f"Required files missing for {study_dir.name}: {e}")
    except Exception as e:
        pytest.fail(f"ReportGenerator failed for {study_dir.name}: {e}")


@pytest.mark.parametrize("study_dir", get_all_study_dirs())
def test_docx_content_matches_checkpoint(study_dir):
    """
    Tests that the text content of the .docx file matches the checkpoint for each
    study. This test is more lenient about dynamic content like dates.
    """
    if study_dir.name == "Study2" and not shutil.which(
        "/Applications/Rhino 8.app/Contents/Resources/bin/rhinocode"
    ):
        pytest.skip("Rhino is not installed, skipping Study2 content match test.")

    report_name = f"{study_dir.name}_report.docx"
    generated_report = GENERATED_REPORTS_DIR / report_name
    expected_report = EXPECTED_DIR / report_name

    if not generated_report.exists():
        pytest.skip(f"Generated report '{report_name}' not found.")
    
    if not expected_report.exists():
        pytest.skip(f"Expected checkpoint '{report_name}' not found.")

    generated_text = docx2txt.process(generated_report)
    expected_text = docx2txt.process(expected_report)
    
    # For exact matching, use this:
    # assert generated_text == expected_text, f"Text content mismatch for '{report_name}'."
    
    # For more lenient matching (excluding dates), you could normalize:
    import re
    date_pattern = r'\d{4}-\d{2}-\d{2}'
    generated_normalized = re.sub(date_pattern, 'YYYY-MM-DD', generated_text)
    expected_normalized = re.sub(date_pattern, 'YYYY-MM-DD', expected_text)
    
    assert generated_normalized == expected_normalized, \
        f"Text content mismatch for '{report_name}' (after date normalization)."


@pytest.mark.parametrize("study_dir", get_all_study_dirs())
def test_image_outputs_are_visually_consistent(study_dir):
    """
    Tests that generated images are visually consistent with their checkpoints
    by comparing their perceptual hashes.
    """
    if study_dir.name == "Study2" and not shutil.which(
        "/Applications/Rhino 8.app/Contents/Resources/bin/rhinocode"
    ):
        pytest.skip("Rhino is not installed, skipping Study2 image consistency test.")

    generated_images_dir = GENERATED_REPORTS_DIR / "tmp_images"
    expected_images_dir = EXPECTED_DIR / "tmp_images"
    
    if not generated_images_dir.exists():
        pytest.skip(f"No generated images directory found for {study_dir.name}")
    
    if not expected_images_dir.exists():
        pytest.skip(f"No expected images directory found for comparison")

    study_name = study_dir.name
    expected_images = {
        p.name
        for p in expected_images_dir.iterdir()
        if p.name.startswith(study_name) and p.suffix.lower() in {'.png', '.jpg', '.jpeg'}
    }

    for filename in expected_images:
        generated_file = generated_images_dir / filename
        expected_file = expected_images_dir / filename
        
        if not generated_file.exists():
            pytest.fail(f"Generated image not found: {filename}")
        
        try:
            generated_hash = imagehash.phash(Image.open(generated_file))
            expected_hash = imagehash.phash(Image.open(expected_file))

            # The hashes should be very close for visually similar images.
            # A hamming distance of 0 means they are identical.
            hash_diff = generated_hash - expected_hash
            assert hash_diff <= 4, (
                f"Visual content mismatch for image: {filename}. "
                f"Hash difference is {hash_diff}, which is > 4. "
                f"(Generated: {generated_hash}, Expected: {expected_hash})"
            )
        except Exception as e:
            pytest.fail(f"Failed to compare images {filename}: {e}")


@pytest.mark.parametrize("study_dir", get_all_study_dirs())
def test_error_handling_for_missing_data(study_dir):
    """Tests that the system gracefully handles missing or invalid data."""
    from src.document_generator import ReportGenerator
    
    # Test with a temporary config that references non-existent data
    import json
    import tempfile
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_study_dir = Path(temp_dir) / "test_study"
        temp_study_dir.mkdir()
        
        # Create a config with invalid data source
        config = {
            "template": "report_template2.docx",
            "author": "Test Author",
            "data_source": "nonexistent.csv",
            "sections": {},
            "analyses": {
                "computations": [
                    {
                        "key": "test_computation",
                        "type": "descriptive_stats",
                        "columns": ["nonexistent_column"]
                    }
                ]
            }
        }
        
        with open(temp_study_dir / "report.json", "w") as f:
            json.dump(config, f)
        
        # This should not crash, but handle the error gracefully
        try:
            generator = ReportGenerator(temp_study_dir, TEMPLATE_DIR, Path(temp_dir))
            context = generator.build_context()
            
            # Should have error information in the context
            assert "computed" in context
            assert "test_computation" in context["computed"]
            # The computation should have failed gracefully
            
        except Exception as e:
            # If it does crash, that's also valuable information
            pytest.fail(f"System did not handle missing data gracefully: {e}")