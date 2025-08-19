# DataXR Study Folder Creator

A command-line tool for creating standardized research folder structures with automated policy management for CropXR projects.

## Features

- Creates standardized folder structures with consistent naming conventions
- Generates FOLDER_POLICY.md files with access control and data handling guidelines
- Supports both JSON configuration files and direct CLI arguments
- Automatic email notification generation for stakeholders
- Configurable investigation folder creation
- Custom folder structure support via JSON files

## Installation

Install the dataxr package using pip:

```bash
pip install dataxr-tools
```

No additional dependencies required - uses only Python standard library modules.

## Usage

### Using JSON Configuration File (Recommended)

```bash
dataxr-create-study-folder --study-config study_config.json
```

### Using CLI Arguments

```bash
dataxr-create-study-folder -i CXRP001 -s CXRS001 --workpackage WP001 --study_title "Plant Stress Response Study"
```

### With Investigation Folder

```bash
dataxr-create-study-folder --study-config study_config.json --create-investigation-folder
```

## Command Line Arguments

| Argument | Description | Required |
|----------|-------------|----------|
| `--study-config` | JSON file containing complete study configuration | When not using CLI args |
| `-i, --investigation` | Investigation label | When not using config file |
| `-s, --study` | Study label | When not using config file |
| `--workpackage` | Workpackage identifier | When not using config file |
| `--study_title` | Study title | Optional |
| `-t, --target` | Target path (default: current directory) | Optional |
| `--folder-name` | Custom folder name (overrides default pattern) | Optional |
| `--sensitivity` | Data sensitivity level (PUBLIC/INTERNAL/CONFIDENTIAL/RESTRICTED) | Optional |
| `--pi-name` | Principal Investigator name | Optional |
| `--pi-email` | Principal Investigator email | Optional |
| `--structure-file` | JSON file with custom folder structure | Optional |
| `--overwrite` | Overwrite existing FOLDER_POLICY.md file | Optional |
| `--create-investigation-folder` | Create investigation folder level | Optional |
| `--no-email-notification` | Skip printing email notification text | Optional |

## Configuration Files

### Study Configuration JSON Example

```json
{
    "accession_code": "CXRS001",
    "security_level": "internal",
    "investigation_title": "Plant stress response analysis under controlled conditions",
    "investigation_accession_code": "CXRP001",
    "investigation_work_package": "WP001",
    "principal_investigator": {
        "first_name": "John",
        "last_name": "Smith",
        "email": "j.smith@example.org"
    },
    "dataset_administrator": {
        "first_name": "Jane",
        "last_name": "Doe",
        "email": "j.doe@example.org"
    },
    "title": "Comprehensive analysis of plant stress response mechanisms",
    "slug": "plant-stress-response-analysis",
    "description": "Multi-omics analysis including RNA-sequencing and metabolite profiling performed over multiple time points to study plant stress response mechanisms under controlled laboratory conditions."
}
```

### Custom Folder Structure JSON Example

```json
{
    "raw": {
        "rnaseq": null,
        "metabolomics": null,
        "phenotyping": null
    },
    "processed": {
        "rnaseq": ["counts", "normalized", "differential"],
        "metabolomics": ["identified", "quantified"],
        "integrated": null
    },
    "analysis": {
        "scripts": null,
        "results": null,
        "figures": null
    },
    "metadata": null,
    "documentation": null
}
```

## Generated Folder Structure

### Default Structure
When using the example study config above, the script creates:

```
s_WP001-CXRP001-CXRS001_plant-stress-response-analysis/
├── CXRP001-CXRS001_raw/
├── CXRP001-CXRS001_processed/
├── CXRP001-CXRS001_metadata/
└── FOLDER_POLICY.md
```

### With Investigation Folder
When using `--create-investigation-folder`:

```
i_WP001_CXRP001/
└── s_WP001-CXRP001-CXRS001_plant-stress-response-analysis/
    ├── CXRP001-CXRS001_raw/
    ├── CXRP001-CXRS001_processed/
    ├── CXRP001-CXRS001_metadata/
    └── FOLDER_POLICY.md
```

### With Custom Structure
Using the custom structure JSON example above:

```
s_WP001-CXRP001-CXRS001_plant-stress-response-analysis/
├── CXRP001-CXRS001_raw/
│   ├── rnaseq/
│   ├── metabolomics/
│   └── phenotyping/
├── CXRP001-CXRS001_processed/
│   ├── rnaseq/
│   │   ├── counts/
│   │   ├── normalized/
│   │   └── differential/
│   ├── metabolomics/
│   │   ├── identified/
│   │   └── quantified/
│   └── integrated/
├── CXRP001-CXRS001_analysis/
│   ├── scripts/
│   ├── results/
│   └── figures/
├── CXRP001-CXRS001_metadata/
├── CXRP001-CXRS001_documentation/
└── FOLDER_POLICY.md
```

## Naming Conventions

### Folder Names
- **Investigation folders**: `i_{WORKPACKAGE}_{INVESTIGATION_LABEL}`
- **Study folders**: `s_{WORKPACKAGE}-{INVESTIGATION_LABEL}-{STUDY_LABEL}_{STUDY_SLUG}`
- **Data folders**: `{INVESTIGATION_LABEL}-{STUDY_LABEL}_{FOLDER_TYPE}`

### Examples
- Investigation: `i_WP001_CXRP001`
- Study: `s_WP001-CXRP001-CXRS001_plant-stress-response-analysis`
- Raw data: `CXRP001-CXRS001_raw`
- Processed data: `CXRP001-CXRS001_processed`

## User Access Management

The script automatically assigns READ-WRITE-SHARE access to:
- **Principal Investigator** (from `principal_investigator` object)
- **Dataset Administrator** (from `dataset_administrator` object)

Both users are included in the FOLDER_POLICY.md file and email notifications.

## Data Sensitivity Levels

| Level | Description |
|-------|-------------|
| **PUBLIC** | Data that can be freely shared with the public |
| **INTERNAL** | Data that can be shared within the organization (CropXR) but not externally |
| **CONFIDENTIAL** | Highly sensitive data with strictly controlled access and not listed in data catalogue |
| **RESTRICTED** | Sensitive data with limited access even within the organization |

## Output Files

### FOLDER_POLICY.md
Contains:
- Study information and metadata
- Data sensitivity classification
- Access control table
- Folder naming conventions
- Data handling policies
- Contact information for support

### Email Notification
Automatically generated text suitable for notifying stakeholders about folder creation, including:
- Study details
- Access rights summary
- Important policy reminders
- Contact information

## Example Commands

### Basic Usage with Config File
```bash
dataxr-create-study-folder --study-config plant_study.json -t /data/projects
```

### With Investigation Folder and Custom Target
```bash
dataxr-create-study-folder --study-config plant_study.json --create-investigation-folder -t /research/cropxr
```

### With Custom Structure and No Email
```bash
dataxr-create-study-folder --study-config plant_study.json --structure-file custom_structure.json --no-email-notification
```

### Overwrite Existing Policy
```bash
dataxr-create-study-folder --study-config plant_study.json --overwrite
```

### Get Help
```bash
dataxr-create-study-folder --help
```

## Safety Features

- **Never deletes existing folders** - Only creates missing directories
- **Backup existing policies** - Creates timestamped backups when overwriting FOLDER_POLICY.md
- **Validation** - Checks for required fields and valid paths
- **Error handling** - Graceful handling of missing files or invalid configurations

## Support

For questions or issues with folder creation:
- Data Engineering Team: dataxr@cropxr.org

For questions about this tool:
- Check the generated FOLDER_POLICY.md file for project-specific policies
- Review command line help: `dataxr-create-study-folder --help`
