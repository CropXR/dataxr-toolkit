import argparse
import json
import os
import re
import sys
from datetime import datetime


def create_folder_structure(
    target_path,
    folder_name=None,
    investigation_label=None,
    study_label=None,
    study_title=None,
    study_slug=None,
    sensitivity_level=None,
    authorized_users=None,
    pi_name=None,
    pi_email=None,
    workpackage=None,
    structure=None,
    overwrite_existing=False,
):
    """Create a folder structure with focus on data organization by type.

    NOTE: This function NEVER deletes existing folders. It only creates missing
    folders and can optionally overwrite the FOLDER_POLICY.md file.

    Args:
        target_path: The base directory where the new folder will be created
        folder_name: Optional custom folder name (if not provided, uses default pattern)
        investigation_label: Label for the investigation (LABEL1)
        study_label: Label for the study (LABEL2)
        study_title: Title of the study
        study_slug: Slug version of study title
        sensitivity_level: Data sensitivity level (PUBLIC/INTERNAL/CONFIDENTIAL/RESTRICTED)
        authorized_users: List of dictionaries with user access information
        pi_name: Name of the Principal Investigator
        pi_email: Contact email of the Principal Investigator
        workpackage: Workpackage identifier
        structure: A nested dictionary defining the folder structure
        overwrite_existing: Whether to overwrite existing FOLDER_POLICY.md file (folders are never deleted)

    Returns:
        Path to the created main folder
    """
    # Verify target path exists
    if not os.path.exists(target_path):
        error_msg = f"Target directory does not exist: {target_path}"
        raise FileNotFoundError(error_msg)

    # Generate folder name using default pattern if not provided
    if folder_name is None:
        if not all([workpackage, investigation_label, study_label, study_slug]):
            error_msg = (
                "Either folder_name must be provided, or all of workpackage, "
                "investigation_label, study_label, and study_slug must be provided"
            )
            raise ValueError(error_msg)
        folder_name = f"i_{workpackage}_{investigation_label}/s_{investigation_label}-{study_label}_{study_slug}"

    # Create the main folder
    main_folder_path = os.path.join(target_path, folder_name)

    # Check if main folder already exists
    if os.path.exists(main_folder_path):
        print(f"Note: Main folder already exists: {main_folder_path}")
    else:
        os.makedirs(main_folder_path, exist_ok=True)
        print(f"Created main folder: {main_folder_path}")

    if authorized_users is None:
        authorized_users = []

    # Define a simplified structure if not provided
    if structure is None:
        # Generic structure that works for multiple data types
        structure = {
            "raw_data": None,
            "processed_data": None,
            "metadata": None,
        }

    # Apply labels to all first-level folders if provided
    if investigation_label and study_label:
        new_structure = {}
        for folder_name_key, folder_content in structure.items():
            # Create new labeled folder name
            labeled_folder = f"{investigation_label}-{study_label}_{folder_name_key}"
            new_structure[labeled_folder] = folder_content

        # Replace original structure with labeled structure
        structure = new_structure

    # Function to recursively create the folder structure
    def create_subfolders(parent_path, struct, parent_path_desc=""):
        if struct is None:
            # This is a leaf folder, no subfolders
            return

        if isinstance(struct, list):
            # Create multiple empty subfolders
            for subfolder in struct:
                subfolder_path = os.path.join(parent_path, subfolder)

                if os.path.exists(subfolder_path):
                    print(f"Note: Subfolder already exists: {subfolder_path}")
                else:
                    os.makedirs(subfolder_path)
                    print(f"Created subfolder: {subfolder_path}")

        elif isinstance(struct, dict):
            # Create subfolder structure based on dict
            for subfolder_name, substructure in struct.items():
                subfolder_path = os.path.join(parent_path, subfolder_name)

                if os.path.exists(subfolder_path):
                    print(f"Note: Subfolder already exists: {subfolder_path}")
                else:
                    os.makedirs(subfolder_path)
                    print(f"Created subfolder: {subfolder_path}")

                # Recursively create subfolders
                path_key = f"{parent_path_desc}.{subfolder_name}" if parent_path_desc else subfolder_name
                create_subfolders(subfolder_path, substructure, path_key)

    # Create the folder structure
    create_subfolders(main_folder_path, structure)

    # Create FOLDER_POLICY.md file - only for the main folder
    create_folder_policy(
        main_folder_path,
        folder_name,
        investigation_label,
        study_label,
        study_title,
        sensitivity_level,
        authorized_users,
        pi_name,
        pi_email,
        workpackage,
        overwrite_existing,
    )

    return main_folder_path


def create_folder_policy(
    folder_path,
    investigation_label,
    study_label,
    study_title,
    sensitivity_level,
    authorized_users,
    pi_name=None,
    pi_email=None,
    workpackage=None,
    overwrite_existing=False,
):
    """Create a FOLDER_POLICY.md file focused on data organization.

    NOTE: This function only creates/updates the FOLDER_POLICY.md file. It never
    deletes or modifies any folders or other files.

    Args:
        folder_path: Path where the policy file will be created
        investigation_label: Label for the investigation
        study_label: Label for the study
        study_title: Title of the study
        sensitivity_level: Data sensitivity level
        authorized_users: List of dictionaries with user access information
        pi_name: Name of the Principal Investigator
        pi_email: Contact email of the Principal Investigator
        workpackage: Workpackage identifier
        overwrite_existing: Whether to overwrite existing FOLDER_POLICY.md file

    Returns:
        Path to the created policy file
    """
    today = datetime.now().strftime("%Y-%m-%d")

    # Prepare read and write access tables
    access_rows = []

    for user in authorized_users:
        name = user.get("name", "[Name]")
        role = user.get("role", "[Role]")
        access_level = user.get("access_level", "READ")
        expiration = user.get("expiration", "PERMANENT")

        access_rows.append(f"| {name} | {role} | {access_level} | {expiration} |")

    # Default rows if no users provided
    if not access_rows:
        access_rows = ["| [Name] | [Role] | [READ/READ-WRITE] | [YYYY-MM-DD or PERMANENT] |"]

    inv_label = investigation_label or "[LABEL1]"
    study_lab = study_label or "[LABEL2]"

    policy_content = f"""# FOLDER POLICY

## Study Information
- **Study Title**: {study_title or "[Study Title]"}
- **Investigation Label**: {inv_label}
- **Study Label**: {study_lab}
- **Workpackage**: {workpackage or "[Workpackage ID]"}
- **Date Created**: {today}
- **Project Lead**: {pi_name or "[Name]"}
- **Contact Email**: {pi_email or "[Email]"}

## Data Sensitivity Classification
**Current Sensitivity Level**: {sensitivity_level or "[SELECT ONE: PUBLIC / INTERNAL / CONFIDENTIAL / RESTRICTED]"}

### Sensitivity Level Definitions
- **PUBLIC**: Data that can be freely shared with the public.
- **INTERNAL**: Data that can be shared within the organization (CropXR) but not externally.
- **RESTRICTED**: Sensitive data with limited access even within the organization.
- **CONFIDENTIAL**: Highly sensitive data with strictly controlled access and not listed in data catalogue.

## Access Control

### Access
The following individuals or groups have read access to this folder structure:

| Name | Role | Department | Access Level | Expiration Date |
|------|------|------------|--------------|-----------------|
{chr(10).join(access_rows)}

## Folder Naming Convention
All folders within this project follow a strict naming convention:

- All first-level folders are prefixed with: **{inv_label}-{study_lab}_**
- Examples:
  - Raw data folder: **{inv_label}-{study_lab}_raw_data**
  - Processed data folder: **{inv_label}-{study_lab}_processed_data**
  - Metadata folder: **{inv_label}-{study_lab}_metadata**
  - Analysis folder: **{inv_label}-{study_lab}_analysis**
  - Documentation folder: **{inv_label}-{study_lab}_documentation**

## Data Handling Policies

### Raw Data
- Raw data must never be modified
- All raw data files must be stored in the **{inv_label}-{study_lab}_raw_data** folder

### Other Data Folders
- All first-level folders follow the naming convention **{inv_label}-{study_lab}_[FOLDER_TYPE]**
- Files within these folders should maintain consistent naming where applicable
- Cross-references between folders should maintain traceability to original data sources

## Metadata Guidelines
- Metadata should be comprehensive and follow applicable standards
- All metadata should be stored in the metadata folder
- File naming should maintain consistency with data files

## Questions and Support
For questions regarding this policy or data management assistance, please contact:
- Data Engineering Team: dataxr@cropxr.org

"""

    # Check for existing policy file
    policy_path = os.path.join(folder_path, "FOLDER_POLICY.md")

    if os.path.exists(policy_path) and not overwrite_existing:
        print(f"Note: Policy file already exists and overwrite_existing=False. Skipping: {policy_path}")
    else:
        # Backup existing file if overwriting and it exists
        if os.path.exists(policy_path) and overwrite_existing:
            backup_path = f"{policy_path}.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            try:
                # Use copy instead of rename to preserve original during backup creation
                import shutil

                shutil.copy2(policy_path, backup_path)
                print(f"Backed up existing policy file to: {backup_path}")
            except Exception as e:
                print(f"Warning: Could not backup existing policy file: {e!s}")

        # Write the policy file (overwrite if overwrite_existing=True)
        if overwrite_existing or not os.path.exists(policy_path):
            try:
                with open(policy_path, "w", encoding="utf-8") as f:
                    f.write(policy_content)
                if os.path.exists(policy_path):
                    print(f"Updated policy file: {policy_path}")
                else:
                    print(f"Created policy file: {policy_path}")
            except Exception as e:
                print(f"Error writing policy file: {e!s}")
    return policy_path


def load_users_from_file(users_file):
    """Load authorized users from JSON file.

    Args:
        users_file: Path to JSON file containing user information

    Returns:
        List of user dictionaries
    """
    try:
        with open(users_file, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading users file: {e!s}")
        sys.exit(1)


def parse_users_from_study_json(study_data):
    """Parse user information from study JSON data.

    Args:
        study_data: Dictionary containing study information

    Returns:
        List of user dictionaries with name, role, and access_level
    """
    users = []

    # Add owners with READ-WRITE access
    owners = study_data.get("owners", [])
    for owner in owners:
        # Parse "Name (email)" format
        if "(" in owner and owner.endswith(")"):
            name_part = owner.split("(")[0].strip()
            email_part = owner.split("(")[1].rstrip(")").strip()
            users.append(
                {
                    "name": f"{name_part} ({email_part})",
                    "role": "Owner",
                    "access_level": "READ-WRITE",
                    "expiration": "PERMANENT",
                }
            )
        else:
            users.append({"name": owner, "role": "Owner", "access_level": "READ-WRITE", "expiration": "PERMANENT"})

    # Add contributors with READ access
    contributors = study_data.get("contributors", [])
    for contributor in contributors:
        # Parse "Name (email)" format
        if "(" in contributor and contributor.endswith(")"):
            name_part = contributor.split("(")[0].strip()
            email_part = contributor.split("(")[1].rstrip(")").strip()
            users.append(
                {
                    "name": f"{name_part} ({email_part})",
                    "role": "Contributor",
                    "access_level": "READ",
                    "expiration": "PERMANENT",
                }
            )
        else:
            users.append(
                {"name": contributor, "role": "Contributor", "access_level": "READ", "expiration": "PERMANENT"}
            )

    # Add readers with READ access
    readers = study_data.get("readers", [])
    for reader in readers:
        # Parse "Name (email)" format
        if "(" in reader and reader.endswith(")"):
            name_part = reader.split("(")[0].strip()
            email_part = reader.split("(")[1].rstrip(")").strip()
            users.append(
                {
                    "name": f"{name_part} ({email_part})",
                    "role": "Reader",
                    "access_level": "READ",
                    "expiration": "PERMANENT",
                }
            )
        else:
            users.append({"name": reader, "role": "Reader", "access_level": "READ", "expiration": "PERMANENT"})

    return users


def load_study_config(config_file):
    """Load study configuration from JSON file.

    Args:
        config_file: Path to JSON file containing study configuration

    Returns:
        Dictionary containing study configuration
    """
    try:
        with open(config_file, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading study config file: {e!s}")
        sys.exit(1)


def extract_labels_from_folder_name(folder_name):
    """Extract investigation and study labels from folder name.

    Args:
        folder_name: Folder name in format like
            "i_WPC2_CXRP4/s_CXRP4-CXRS30_temperature-hormone-gene-networks-arabidopsis"

    Returns:
        Tuple of (workpackage, investigation_label, study_label)
    """
    # Split by '/' to get investigation and study parts
    parts = folder_name.split("/")

    if len(parts) != 2:
        error_msg = f"Invalid folder name format: {folder_name}"
        raise ValueError(error_msg)

    investigation_part = parts[0]  # e.g., "i_WPC2_CXRP4"
    study_part = parts[1]  # e.g., "s_CXRP4-CXRS30_temperature-hormone-gene-networks-arabidopsis"

    # Extract from investigation part: "i_WPC2_CXRP4"
    if not investigation_part.startswith("i_"):
        error_msg = f"Investigation part should start with 'i_': {investigation_part}"
        raise ValueError(error_msg)

    inv_parts = investigation_part[2:].split("_", 1)  # Remove "i_" and split once
    if len(inv_parts) != 2:
        error_msg = f"Invalid investigation format: {investigation_part}"
        raise ValueError(error_msg)

    workpackage = inv_parts[0]  # e.g., "WPC2"
    investigation_label = inv_parts[1]  # e.g., "CXRP4"

    # Extract from study part: "s_CXRP4-CXRS30_temperature-hormone-gene-networks-arabidopsis"
    if not study_part.startswith("s_"):
        error_msg = f"Study part should start with 's_': {study_part}"
        raise ValueError(error_msg)

    study_content = study_part[2:]  # Remove "s_"

    # Find the first underscore after the labels to separate labels from slug
    # Format is "CXRP4-CXRS30_slug"
    underscore_pos = study_content.find("_")
    if underscore_pos == -1:
        error_msg = f"Invalid study format, missing underscore: {study_part}"
        raise ValueError(error_msg)

    labels_part = study_content[:underscore_pos]  # e.g., "CXRP4-CXRS30"

    # Split labels by hyphen
    if "-" not in labels_part:
        error_msg = f"Invalid labels format, missing hyphen: {labels_part}"
        raise ValueError(error_msg)

    label_parts = labels_part.split("-", 1)  # Split once on first hyphen
    expected_investigation = label_parts[0]  # Should match investigation_label
    study_label = label_parts[1]  # e.g., "CXRS30"

    # Validate that investigation labels match
    if expected_investigation != investigation_label:
        error_msg = f"Investigation label mismatch: {expected_investigation} vs {investigation_label}"
        raise ValueError(error_msg)

    return workpackage, investigation_label, study_label


def main():
    """Command line entry point."""
    parser = argparse.ArgumentParser(description="Create research folder structures with policy management")

    # Add new argument for study config JSON
    parser.add_argument("--study-config", help="JSON file containing complete study configuration")

    # Keep existing arguments but make some optional when using study-config
    parser.add_argument("-i", "--investigation", help="Investigation label")
    parser.add_argument("-s", "--study", help="Study label")
    parser.add_argument("--study_title", help="Study title (also used to generate study_slug)")
    parser.add_argument("--workpackage", help="Workpackage identifier")
    parser.add_argument("-t", "--target", default=".", help="Target path (default: current directory)")
    parser.add_argument("--folder-name", help="Custom folder name (overrides default pattern)")
    parser.add_argument(
        "--sensitivity",
        choices=["PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED"],
        help="Data sensitivity level",
    )
    parser.add_argument("--pi-name", help="Principal Investigator name")
    parser.add_argument("--pi-email", help="Principal Investigator email")
    parser.add_argument("--users-file", help="JSON file with authorized users")
    parser.add_argument("--structure-file", help="JSON file with custom folder structure")
    parser.add_argument(
        "--overwrite", action="store_true", help="Overwrite existing FOLDER_POLICY.md file (folders are never deleted)"
    )

    args = parser.parse_args()

    # If study-config is provided, extract values from it
    if args.study_config:
        study_data = load_study_config(args.study_config)

        # Extract values from JSON, allowing CLI args to override
        folder_name = args.folder_name or study_data.get("folder_name")

        if folder_name:
            # Extract labels from folder name
            try:
                workpackage, investigation_label, study_label = extract_labels_from_folder_name(folder_name)
            except ValueError as e:
                print(f"Error parsing folder name: {e!s}")
                sys.exit(1)
        else:
            # Use individual fields
            workpackage = args.workpackage or study_data.get("investigation_work_package")
            investigation_label = args.investigation or study_data.get("investigation_accession_code")
            study_label = args.study or study_data.get("accession_code")

        study_title = args.study_title or study_data.get("title")
        study_slug = study_data.get("slug")

        # Map security_level to sensitivity
        security_level = study_data.get("security_level", "").upper()
        sensitivity_map = {
            "PUBLIC": "PUBLIC",
            "INTERNAL": "INTERNAL",
            "CONFIDENTIAL": "CONFIDENTIAL",
            "RESTRICTED": "RESTRICTED",
        }
        sensitivity_level = args.sensitivity or sensitivity_map.get(security_level)

        # Get PI information - prefer effective over regular
        pi_name = (
            args.pi_name
            or study_data.get("effective_principal_investigator_name")
            or study_data.get("principal_investigator_name")
        )
        pi_email = (
            args.pi_email
            or study_data.get("effective_principal_investigator_email")
            or study_data.get("principal_investigator_email")
        )

        # Parse users from study data unless users-file is specified
        if args.users_file:
            authorized_users = load_users_from_file(args.users_file)
        else:
            authorized_users = parse_users_from_study_json(study_data)

    else:
        # Use CLI arguments (original behavior)
        if not all([args.investigation, args.study, args.workpackage]):
            parser.error(
                "When not using --study-config, -i/--investigation, -s/--study, and --workpackage are required"
            )

        investigation_label = args.investigation
        study_label = args.study
        study_title = args.study_title
        workpackage = args.workpackage
        folder_name = args.folder_name
        sensitivity_level = args.sensitivity
        pi_name = args.pi_name
        pi_email = args.pi_email

        # Generate study_slug from title if provided, otherwise use study label
        if study_title:
            # Convert title to slug: lowercase, replace spaces with hyphens, remove special chars
            study_slug = re.sub(r"[^a-z0-9-]", "", study_title.lower().replace(" ", "-"))
        else:
            study_slug = study_label.lower()

        # Load users if file provided
        authorized_users = []
        if args.users_file:
            authorized_users = load_users_from_file(args.users_file)

    # Load custom structure if file provided
    structure = None
    if args.structure_file:
        try:
            with open(args.structure_file, encoding="utf-8") as f:
                structure = json.load(f)
        except Exception as e:
            print(f"Error loading structure file: {e!s}")
            sys.exit(1)

    try:
        created_folder = create_folder_structure(
            target_path=args.target,
            folder_name=folder_name,
            investigation_label=investigation_label,
            study_label=study_label,
            study_title=study_title,
            study_slug=study_slug,
            sensitivity_level=sensitivity_level,
            authorized_users=authorized_users,
            pi_name=pi_name,
            pi_email=pi_email,
            workpackage=workpackage,
            structure=structure,
            overwrite_existing=args.overwrite,
        )

        print(f"Successfully created folder structure in: {created_folder}")
    except Exception as e:
        print(f"Error: {e!s}")
        sys.exit(1)


if __name__ == "__main__":
    main()
