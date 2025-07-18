import argparse
import json
import os
import re
import shutil
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
    create_investigation_folder=False,
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
        create_investigation_folder: Whether to create the investigation folder level (default: False)

    Returns:
        Path to the created main folder
    """
    print(f"DEBUG: create_folder_structure called with create_investigation_folder={create_investigation_folder}")

    # Verify target path exists
    if not os.path.exists(target_path):
        error_msg = f"Target directory does not exist: {target_path}"
        raise FileNotFoundError(error_msg)

    # Generate folder name using default pattern if not provided or handle custom folder name
    if folder_name is None:
        if not all([investigation_label, study_label, study_slug]):
            error_msg = "Either folder_name must be provided, or all of investigation_label, study_label, and study_slug must be provided"
            raise ValueError(error_msg)

        if not workpackage:
            error_msg = "workpackage must be provided for folder name generation"
            raise ValueError(error_msg)

        if create_investigation_folder:
            # Create investigation folder and study folder within it
            investigation_folder = f"i_{workpackage}_{investigation_label}"
            study_folder = f"s_{workpackage}-{investigation_label}-{study_label}_{study_slug}"

            # Create investigation folder first
            investigation_path = os.path.join(target_path, investigation_folder)
            if not os.path.exists(investigation_path):
                os.makedirs(investigation_path, exist_ok=True)
                print(f"Created investigation folder: {investigation_path}")
            else:
                print(f"Note: Investigation folder already exists: {investigation_path}")

            # Set the main folder path to be inside the investigation folder
            main_folder_path = os.path.join(investigation_path, study_folder)
            print(f"DEBUG: Generated folder path with investigation: {main_folder_path}")
        else:
            # Create study folder directly in target path
            study_folder = f"s_{workpackage}-{investigation_label}-{study_label}_{study_slug}"
            main_folder_path = os.path.join(target_path, study_folder)
            print(f"DEBUG: Generated folder path without investigation: {main_folder_path}")
    else:
        # Handle custom folder name - respect create_investigation_folder flag
        if create_investigation_folder:
            # If folder_name contains investigation folder path, use it as-is
            # Otherwise, treat it as the study folder name and create investigation folder
            if folder_name.startswith("i_") and "/" in folder_name:
                # Custom folder name already includes investigation path
                main_folder_path = os.path.join(target_path, folder_name)
                print(f"DEBUG: Using custom folder path with investigation: {main_folder_path}")
            else:
                # Create investigation folder and put custom folder inside it
                if not all([workpackage, investigation_label]):
                    error_msg = "workpackage and investigation_label required when create_investigation_folder=True"
                    raise ValueError(error_msg)

                investigation_folder = f"i_{workpackage}_{investigation_label}"
                investigation_path = os.path.join(target_path, investigation_folder)
                if not os.path.exists(investigation_path):
                    os.makedirs(investigation_path, exist_ok=True)
                    print(f"Created investigation folder: {investigation_path}")
                else:
                    print(f"Note: Investigation folder already exists: {investigation_path}")

                main_folder_path = os.path.join(investigation_path, folder_name)
                print(f"DEBUG: Using custom folder inside investigation: {main_folder_path}")
        else:
            # Extract study folder name from custom folder_name if it contains investigation path
            if "/" in folder_name and folder_name.startswith("i_"):
                # Extract just the study folder part (after the last /)
                # But ensure it follows proper naming convention
                study_folder_name = folder_name.split("/")[-1]

                # If the extracted study folder doesn't start with s_{workpackage}, rebuild it properly
                if not study_folder_name.startswith(f"s_{workpackage}-"):
                    if not all([workpackage, investigation_label, study_label, study_slug]):
                        error_msg = "workpackage, investigation_label, study_label, and study_slug required to rebuild study folder name"
                        raise ValueError(error_msg)
                    study_folder_name = f"s_{workpackage}-{investigation_label}-{study_label}_{study_slug}"
                    print(f"DEBUG: Rebuilt study folder name: {study_folder_name}")

                main_folder_path = os.path.join(target_path, study_folder_name)
                print(f"DEBUG: Extracted study folder from custom path: {main_folder_path}")
            else:
                # Use custom folder name directly in target path
                main_folder_path = os.path.join(target_path, folder_name)
                print(f"DEBUG: Using custom folder directly: {main_folder_path}")

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
            "raw": None,
            "processed": None,
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
    project_name=None,  # noqa: ARG001
    investigation_label=None,
    study_label=None,
    study_title=None,
    sensitivity_level=None,
    authorized_users=None,
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
        project_name: Name of the project (unused, kept for backwards compatibility)
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
    if authorized_users is None:
        authorized_users = []

    # Filter to show only owners and PIs with READ-WRITE-SHARE access
    filtered_users = filter_owners_and_pis_with_write_share_access(authorized_users)

    # Prepare read and write access tables
    access_rows = []

    for user in filtered_users:
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
    today = datetime.now().strftime("%Y-%m-%d")

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
The following individuals or groups have READ-WRITE-SHARE access to this folder structure:

| Name | Role | Access Level | Expiration Date |
|------|------|--------------|-----------------|
{chr(10).join(access_rows)}

## Folder Naming Convention
All folders within this project follow a strict naming convention:

- All first-level folders are prefixed with: **{inv_label}-{study_lab}_**
- Examples:
  - Raw data folder: **{inv_label}-{study_lab}_raw**
  - Processed data folder: **{inv_label}-{study_lab}_processed**
  - Metadata folder: **{inv_label}-{study_lab}_metadata**
  - Analysis folder: **{inv_label}-{study_lab}_analysis**
  - Documentation folder: **{inv_label}-{study_lab}_documentation**

## Data Handling Policies

### Raw Data
- Raw data must never be modified
- All raw data files must be stored in the **{inv_label}-{study_lab}_raw** folder

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
                shutil.copy2(policy_path, backup_path)
                print(f"Backed up existing policy file to: {backup_path}")
            except Exception as e:
                print(f"Warning: Could not backup existing policy file: {e}")

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
                print(f"Error writing policy file: {e}")
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
        print(f"Error loading users file: {e}")
        sys.exit(1)


def filter_owners_and_pis_with_write_share_access(authorized_users):
    """Filter users to show only owners and principal investigators with READ-WRITE-SHARE access.

    Args:
        authorized_users: List of user dictionaries with access information

    Returns:
        List of filtered user dictionaries containing only owners and PIs
        with READ-WRITE-SHARE rights
    """
    # Define target roles (case-insensitive)
    target_roles = {"owner", "principal investigator", "pi", "principal_investigator"}

    # Define target access level - specifically READ-WRITE-SHARE
    target_access = "READ-WRITE-SHARE"

    filtered_users = []

    for user in authorized_users:
        user_role = user.get("role", "").lower()
        user_access = user.get("access_level", "").upper()

        # Check if user has target role and READ-WRITE-SHARE access
        if user_role in target_roles and user_access == target_access:
            filtered_users.append(user)

    return filtered_users


def parse_users_from_study_json(study_data):
    """Parse user information from study JSON data.

    Args:
        study_data: Dictionary containing study information

    Returns:
        List of user dictionaries with name, role, and access_level
    """
    users = []

    # Add owners with READ-WRITE-SHARE access
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
                    "access_level": "READ-WRITE-SHARE",
                    "expiration": "PERMANENT",
                }
            )
        else:
            users.append({"name": owner, "role": "Owner", "access_level": "READ-WRITE-SHARE", "expiration": "PERMANENT"})

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
            users.append({"name": contributor, "role": "Contributor", "access_level": "READ", "expiration": "PERMANENT"})

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

    # Add Principal Investigator with READ-WRITE-SHARE access
    pi_name = study_data.get("effective_principal_investigator_name")
    pi_email = study_data.get("effective_principal_investigator_email")

    if pi_name:
        pi_display_name = f"{pi_name} ({pi_email})" if pi_email else pi_name

        # Check if PI is not already in owners list
        pi_already_added = any(pi_display_name.lower() in user["name"].lower() for user in users)

        if not pi_already_added:
            users.append({"name": pi_display_name, "role": "Principal Investigator", "access_level": "READ-WRITE-SHARE", "expiration": "PERMANENT"})

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
        print(f"Error loading study config file: {e}")
        sys.exit(1)


def generate_notification_email(study_title, investigation_label, study_label, workpackage, folder_path, authorized_users, pi_name, pi_email, sensitivity_level):
    """Generate email notification text for owners and PIs about folder creation.

    Args:
        study_title: Title of the study
        investigation_label: Label for the investigation
        study_label: Label for the study
        workpackage: Workpackage identifier
        folder_path: Path to the created folder
        authorized_users: List of user dictionaries with access information
        pi_name: Name of the Principal Investigator
        pi_email: Contact email of the Principal Investigator
        sensitivity_level: Data sensitivity level

    Returns:
        String containing the email notification text
    """
    # Filter to get only owners and PIs with READ-WRITE-SHARE access
    write_share_users = filter_owners_and_pis_with_write_share_access(authorized_users)

    # Create user list for email body
    user_list = []
    for user in write_share_users:
        name = user.get("name", "")
        role = user.get("role", "")
        # Extract email from "Name (email)" format
        if "(" in name and name.endswith(")"):
            name_part = name.split("(")[0].strip()
            email_part = name.split("(")[1].rstrip(")").strip()
            user_list.append(f"  - {name_part} ({email_part}) ({role})")
        else:
            user_list.append(f"  - {name} ({role})")

    user_list_text = "\n".join(user_list) if user_list else "  - No users with READ-WRITE-SHARE access found"

    # Extract just the folder name from the full path
    folder_name = os.path.basename(folder_path)

    today = datetime.now().strftime("%Y-%m-%d")

    return f"""Dear Researchers,

Your study folder has been successfully created in the CropXR Research Drive.

Study Details:
- Study Title: {study_title or "N/A"}
- Investigation Label: {investigation_label or "N/A"}
- Study Label: {study_label or "N/A"}
- Workpackage: {workpackage or "N/A"}
- Folder Name: {folder_name}
- Date Created: {today}
- Principal Investigator: {pi_name or "N/A"}
- Contact Email: {pi_email or "N/A"}
- Data Sensitivity Level: {sensitivity_level or "Not specified"}

Access Rights:
The following users have been granted READ-WRITE-SHARE access to this folder:
{user_list_text}

Important Notes:
- Please review the FOLDER_POLICY.md file in your study folder for detailed access control and data handling policies
- Raw data must never be modified and should be stored in the designated raw data folder
- All folder naming follows the convention: {investigation_label or "LABEL1"}-{study_label or "LABEL2"}_[FOLDER_TYPE]
- For any questions or support, contact the Data Engineering Team at dataxr@cropxr.org

Best regards,
CropXR Data Management Team"""


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
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing FOLDER_POLICY.md file (folders are never deleted)")
    parser.add_argument("--create-investigation-folder", action="store_true", help="Create investigation folder level (default: False)")
    parser.add_argument("--no-email-notification", action="store_true", help="Skip printing email notification text")

    args = parser.parse_args()

    # DEBUG: Print the create_investigation_folder value
    print(f"DEBUG: args.create_investigation_folder = {args.create_investigation_folder}")

    # If study-config is provided, extract values from it
    if args.study_config:
        study_data = load_study_config(args.study_config)

        # Extract values from JSON, allowing CLI args to override
        folder_name = args.folder_name or study_data.get("folder_name")

        # Use individual fields directly from study data
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

        # Get PI information - always prefer effective fields
        pi_name = args.pi_name or study_data.get("effective_principal_investigator_name")
        pi_email = args.pi_email or study_data.get("effective_principal_investigator_email")

        # Parse users from study data unless users-file is specified
        authorized_users = load_users_from_file(args.users_file) if args.users_file else parse_users_from_study_json(study_data)

        # Check if study config specifies investigation folder creation
        # CLI argument takes precedence over JSON config
        create_investigation_folder = args.create_investigation_folder
        print(f"DEBUG: final create_investigation_folder = {create_investigation_folder}")

    else:
        # Use CLI arguments (original behavior)
        # workpackage is always required for folder name generation
        if not all([args.investigation, args.study, args.workpackage]):
            error_msg = "When not using --study-config, -i/--investigation, -s/--study, and --workpackage are required"
            parser.error(error_msg)

        investigation_label = args.investigation
        study_label = args.study
        study_title = args.study_title
        workpackage = args.workpackage
        folder_name = args.folder_name
        sensitivity_level = args.sensitivity
        pi_name = args.pi_name
        pi_email = args.pi_email
        create_investigation_folder = args.create_investigation_folder

        # Generate study_slug from title if provided, otherwise use study label
        study_slug = re.sub(r"[^a-z0-9-]", "", study_title.lower().replace(" ", "-")) if study_title else study_label.lower()

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
            print(f"Error loading structure file: {e}")
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
            create_investigation_folder=create_investigation_folder,
        )

        print(f"Successfully created folder structure in: {created_folder}")

        # Generate and print email notification unless disabled
        if not args.no_email_notification:
            print("\n" + "=" * 80)
            email_notification = generate_notification_email(
                study_title=study_title,
                investigation_label=investigation_label,
                study_label=study_label,
                workpackage=workpackage,
                folder_path=created_folder,
                authorized_users=authorized_users,
                pi_name=pi_name,
                pi_email=pi_email,
                sensitivity_level=sensitivity_level,
            )
            print(email_notification)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
