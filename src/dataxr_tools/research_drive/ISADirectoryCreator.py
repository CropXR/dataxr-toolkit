import argparse
import os
import re
import sys
from datetime import datetime

import yaml


class ISADirectoryCreator:
    """Creates directory structures for ISA (Investigation, Study, Assay) model projects.

    Supports README files and templating with custom labels.
    """

    def __init__(
        self,
        yaml_file_path,
        target_path=".",
        investigation_label="My Investigation",
        study_label="My Study",
        assay_label="My Assay",
    ):
        """Initialize the ISADirectoryCreator.

        Args:
            yaml_file_path (str): Path to the YAML file containing structure
            target_path (str): Target path where to create the structure
            investigation_label (str): Label for the investigation
            study_label (str): Label for the study
            assay_label (str): Label for the assay
        """
        self.yaml_file_path = yaml_file_path
        self.target_path = target_path
        self.investigation_label = investigation_label
        self.study_label = study_label
        self.assay_label = assay_label
        self.structure = None

    def parse_yaml_file(self):
        """Parse the YAML file and return the structure.

        Returns:
            dict: The parsed YAML structure
        """
        try:
            with open(self.yaml_file_path, encoding="utf-8") as file:
                yaml_content = file.read()
                # Replace template variables with actual values
                yaml_content = yaml_content.replace("${INVESTIGATION_LABEL}", self.investigation_label)
                yaml_content = yaml_content.replace("${STUDY_LABEL}", self.study_label)
                yaml_content = yaml_content.replace("${ASSAY_LABEL}", self.assay_label)
                # Additional interpolation for file and directory names
                yaml_content = self._interpolate_keys(yaml_content)

                self.structure = yaml.safe_load(yaml_content)
            return self.structure
        except Exception as e:
            print("Error reading or parsing YAML file:", str(e))
            sys.exit(1)

    def _interpolate_keys(self, yaml_content):
        """Interpolate template variables in YAML keys (not just values).

        Args:
            yaml_content (str): The raw YAML content as string

        Returns:
            str: YAML content with interpolated keys
        """
        # Replace variables in keys for connected IDs
        investigation_slug = f"i_{self.investigation_label}"
        study_slug = f"s_{self.investigation_label}{self.study_label}"
        assay_slug = f"a_{self.investigation_label}{self.study_label}{self.assay_label}"

        yaml_content = yaml_content.replace("INVESTIGATION_LABEL_SLUG", investigation_slug)
        yaml_content = yaml_content.replace("STUDY_LABEL_SLUG", study_slug)
        return yaml_content.replace("ASSAY_LABEL_SLUG", assay_slug)

    def _to_slug(self, text):
        """Convert text to a slug format.

        For ID-based labels, just returns the ID.

        Args:
            text (str): The text to convert

        Returns:
            str: Slug version of the text or the ID as is
        """
        # For ID-based labels like CXC123, preserve the format without modification
        if re.match(r"^[A-Z0-9]+$", text):
            return text

        # For descriptive labels, convert to lowercase, replace spaces with hyphens
        return re.sub(r"[^a-z0-9-]", "", text.lower().replace(" ", "-"))

    def create_directory_structure(self, base_path, structure):
        """Create directories and files recursively.

        Args:
            base_path (str): Base path for current level
            structure (dict): Structure to create
        """
        # Create the base directory if it doesn't exist
        os.makedirs(base_path, exist_ok=True)
        print("Created directory:", base_path)

        # Process each item in the structure
        for key, value in structure.items():
            current_path = os.path.join(base_path, key)

            if isinstance(value, dict):
                # If value is a dictionary, it's a directory with contents

                # Create the directory
                os.makedirs(current_path, exist_ok=True)
                print("Created directory:", current_path)

                # Check if there's a README or description for this directory
                if "_readme" in value:
                    readme_path = os.path.join(current_path, "README.md")
                    with open(readme_path, "w", encoding="utf-8") as file:
                        file.write(value["_readme"])
                    print("Created README:", readme_path)

                    # Remove the _readme property before processing the rest
                    structure_without_readme = {k: v for k, v in value.items() if k != "_readme"}
                    self.create_directory_structure(current_path, structure_without_readme)
                else:
                    self.create_directory_structure(current_path, value)
            elif isinstance(value, str):
                # If value is a string, it could be a file with content
                if "." in key:
                    # It's a file
                    with open(current_path, "w", encoding="utf-8") as file:
                        file.write(value)
                    print("Created file:", current_path)
                else:
                    # It's a directory with a description
                    os.makedirs(current_path, exist_ok=True)
                    print("Created directory:", current_path)

                    # Create a README.md in this directory with the description
                    readme_path = os.path.join(current_path, "README.md")
                    with open(readme_path, "w", encoding="utf-8") as file:
                        file.write(value)
                    print("Created README:", readme_path)
            elif value is None:
                # It's an empty directory
                os.makedirs(current_path, exist_ok=True)
                print("Created directory:", current_path)

    def add_project_readme(self):
        """Add an overall project README to the root directory."""
        readme_path = os.path.join(self.target_path, "README.md")
        timestamp = datetime.now().strftime("%Y-%m-%d")

        # Create a top-level README with the project label
        readme_content = f"# {self.investigation_label}\n\n"
        readme_content += f"ISA model project generated on {timestamp}.\n\n"
        readme_content += f"## Investigation\n\n{self.investigation_label}\n\n"
        readme_content += f"## Study\n\n{self.study_label}\n\n"
        readme_content += f"## Assay\n\n{self.assay_label}\n\n"
        readme_content += "## Structure Overview\n\n"
        readme_content += self.generate_structure_overview(self.structure, 0)

        with open(readme_path, "w", encoding="utf-8") as file:
            file.write(readme_content)
        print("Created project README:", readme_path)

    def generate_structure_overview(self, structure, level):
        """Generate a markdown overview of the structure.

        Args:
            structure (dict): Structure to describe
            level (int): Current nesting level

        Returns:
            str: Markdown formatted structure overview
        """
        overview = ""
        indent = "  " * level

        for key, value in structure.items():
            # Skip _readme entries
            if key == "_readme":
                continue

            # Add this item to the overview
            overview += f"{indent}- `{key}`"

            # Add description if available
            if isinstance(value, str) and "." not in key:
                overview += " - Directory with README"
            elif "." in key:
                overview += " - File"
            elif isinstance(value, dict):
                overview += " - Directory"
                # Add README note if it has one
                if "_readme" in value:
                    overview += " with README"

            overview += "\n"

            # Recursively add children if it's a directory
            if isinstance(value, dict):
                overview += self.generate_structure_overview(value, level + 1)

        return overview

    def execute(self):
        """Execute the directory structure creation."""
        print("Creating ISA model directory structure for", repr(self.investigation_label), "at", self.target_path)
        self.parse_yaml_file()
        self.create_directory_structure(self.target_path, self.structure)
        self.add_project_readme()
        print("ISA model directory structure for", repr(self.investigation_label), "created successfully")


def main():
    """Command line entry point."""
    parser = argparse.ArgumentParser(description="Generate ISA model directory structures from YAML files")
    parser.add_argument("yaml_file", help="YAML file containing the directory structure")
    parser.add_argument(
        "-t", "--target", default=".", help="Target path to create the structure (default: current directory)"
    )
    parser.add_argument(
        "-i",
        "--investigation",
        default="My Investigation",
        help='Label for the investigation (default: "My Investigation")',
    )
    parser.add_argument("-s", "--study", default="My Study", help='Label for the study (default: "My Study")')
    parser.add_argument("-a", "--assay", default="My Assay", help='Label for the assay (default: "My Assay")')

    args = parser.parse_args()

    # Create and execute the directory creator
    creator = ISADirectoryCreator(args.yaml_file, args.target, args.investigation, args.study, args.assay)
    creator.execute()


if __name__ == "__main__":
    main()
