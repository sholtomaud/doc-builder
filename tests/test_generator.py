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
    return [d for d in TEST_DATA_DIR.iterdir() if d.is_dir()]


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

    cmd = [
        "doc-builder",
        "batch",
        str(TEST_PROJECT_DIR / "studies"),
        "--template-dir",
        str(TEST_PROJECT_DIR / "templates"),
        "--output-dir",
        str(GENERATED_REPORTS_DIR),
    ]
    subprocess.run(
        cmd, check=True, capture_output=True, text=True, cwd=TEST_PROJECT_DIR
    )

    yield

    if not os.getenv("KEEP_TEST_OUTPUT"):
        shutil.rmtree(TEST_PROJECT_DIR.parent)
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
def test_docx_content_matches_checkpoint(study_dir):
    """
    Tests that the text content of the .docx file matches the checkpoint for each
    study.
    """
    report_name = f"{study_dir.name}_report.docx"
    generated_report = GENERATED_REPORTS_DIR / report_name
    expected_report = EXPECTED_DIR / report_name

    assert generated_report.exists(), f"Generated report '{report_name}' not found."
    assert expected_report.exists(), f"Expected checkpoint '{report_name}' not found."

    generated_text = docx2txt.process(generated_report)
    expected_text = docx2txt.process(expected_report)
    assert (
        generated_text == expected_text
    ), f"Text content mismatch for '{report_name}'."


@pytest.mark.parametrize("study_dir", get_all_study_dirs())
def test_image_outputs_are_visually_consistent(study_dir):
    """
    Tests that generated images are visually consistent with their checkpoints
    by comparing their perceptual hashes.
    """
    generated_images_dir = GENERATED_REPORTS_DIR / "tmp_images"
    expected_images_dir = EXPECTED_DIR / "tmp_images"

    study_name = study_dir.name
    expected_images = {
        p.name
        for p in expected_images_dir.iterdir()
        if p.name.startswith(study_name)
    }

    for filename in expected_images:
        generated_file = generated_images_dir / filename
        expected_file = expected_images_dir / filename

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
