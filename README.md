# Document Builder (`doc-builder`)

[![Python CI](https://github.com/YOUR_USERNAME/YOUR_REPOSITORY/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/YOUR_REPOSITORY/actions/workflows/ci.yml)

`doc-builder` is a flexible, template-based command-line tool to generate richly formatted MS Word documents from various data sources. It uses a `.docx` template file and a `report.json` configuration to give you full control over your document's structure and content.

## Installation

You can install the tool directly from this GitHub repository.

```bash
git clone https://github.com/sholtomaud/doc-builder.git
cd doc-builder
pip install .
```
This will install the `doc-builder` command, making it available in your terminal.

## How to Use

### 1. Project Structure

Your project should be structured as follows:
```
my_project/
├── templates/
│   └── report_template.docx
├── studies/
│   └── MyFirstReport/
│       ├── report.json
│       ├── introduction.md
│       ├── discussion.md
│       ├── data.csv
│       └── ...
└── generated_reports/
    └── (This will be created automatically)
```

### 2. Create a `.docx` Template

Create a `report_template.docx` file in your `templates` directory. This file will contain the boilerplate text for your report, along with Jinja2-style placeholders for your data.

**Example Placeholders:**
*   `{{ study_name }}`: For simple text replacement.
*   `{{ avg_flow_rate | round(2) }}`: Use Jinja2 filters to format your data.
*   `{{ image_placeholder }}`: For images. The script will replace this with an image.

### 3. Create a `report.json` Configuration

For each report you want to generate, create a `report.json` file. This file tells `doc-builder` how to assemble your document.

**Example `report.json`:**
```json
{
  "template": "report_template.docx",
  "author": "Your Name",
  "data_source": "data.csv",
  "sections": {
    "introduction": "introduction.md",
    "discussion": "discussion.md"
  },
  "images": {
    "image_placeholder": {
      "type": "pairplot",
      "data_source": "data.csv"
    }
  }
}
```

### 4. Run the Generator

Navigate to your project directory and run the `doc-builder` command, pointing it to your report's directory.
```bash
doc-builder studies/MyFirstReport
```
The generated report will be saved in the `generated_reports` directory.

## For Developers

If you want to contribute to the development of this tool, you can install it in editable mode.

1.  **Clone the repository and install:**
    ```bash
    git clone https://github.com/your-username/doc-builder.git
    cd doc-builder
    make install
    ```
    This installs the package and all test dependencies.
2.  **Run tests:**
    ```bash
    # Run tests and automatically clean up
    make test

    # Run tests and keep the output for inspection
    make test-debug
    ```
    When you use `make test-debug`, the generated files will be left in the `tests/tmp` directory for you to review.