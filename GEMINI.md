# GEMINI.md – AI Agent Instructions for `doc-builder`

## 1. Project Overview & Core Philosophy

This project, `doc-builder`, is a generic, template-driven tool for generating richly formatted MS Word documents. It is designed to be flexible and adaptable, using a configuration file (`report.json`) and a `.docx` template to combine narrative text, data, and images into a final report.

**Core Philosophy:**
- **Configuration-Driven:** Each report is defined by a `report.json` file, giving the user full control over the document's structure and content.
- **Template-Based:** The presentation is separated from the data. A user creates a `.docx` template with Jinja2-style placeholders, which the tool populates with data.
- **Extensibility:** The tool is designed to be generic. Adding new reports is a matter of creating a new study directory with a `report.json` and the necessary data files.

## 2. Core Architecture & Requirements

The system is structured around the following components:

- **Configuration (`report.json`):**
  - Each report is defined by a `report.json` file.
  - This file specifies the `.docx` template to use, the data sources and the configuration for generating images.

- **Template (`.docx`):**
  - A user-created `.docx` file containing placeholders (e.g., `{{ variable }}`) 

- **Source Code Location:**
  - The main script is `src/document_generator.py`.
  - The project is packaged using `pyproject.toml`.

- **CLI Tool (`doc-builder`):**
  - The primary entry point is the `doc-builder` command.
  - It takes the path to a study directory as its main argument.
  - Example: `doc-builder path/to/my_study`

## 3. Key Technologies

- **Primary Language:** Python 3.8+
- **Document Generation:** `docxtpl` (which uses `python-docx` and `Jinja2`)
- **Data Analysis & Plotting:** Pandas, NumPy, Seaborn, Matplotlib
- **CLI Interface:** Typer

## 4. Directory Structure (Developer View)

```
├── .gitignore
├── GEMINI.md
├── Makefile
├── README.md
├── pyproject.toml
├── src/
│   └── document_generator.py
├── templates/
│   └── report_template.docx
└── tests/
    ├── data/
    │   └── Study1/
    │       ├── report.json
    │       └── ...
    ├── expected_output/
    │   └── Study1_report.docx
    └── test_generator.py
```

## 5. Development Workflow & Testing

### ✅ Pre-Commit Requirements

Before any PR or commit, developers MUST run the following:

1.  **Install dependencies in editable mode:**
    ```bash
    make install
    ```
2.  **Run the test suite:**
    ```bash
    make test
    ```

### Testing Strategy

The project uses `pytest` for regression testing. The core test (`test_generator.py`) performs the following:
-   It creates a temporary project directory and runs the `doc-builder` on the test data.
-   It compares the generated `.docx` file's text content against a "golden master" checkpoint in `tests/expected_output`.
-   It performs a strict, bit-for-bit binary comparison of any generated images against their checkpoints.

### Updating the Test Checkpoint

If intentional changes are made to the output, the checkpoint must be updated:
```bash
# This command cleans the old checkpoint and regenerates it with the latest output
make regenerate-checkpoint 
```

