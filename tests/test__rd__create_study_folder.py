import json
import os
import shutil
import tempfile
from unittest.mock import MagicMock, patch

import pytest

try:
    from dataxr_toolkit.research_drive.create_study_folder import (
        create_folder_policy,
        create_folder_structure,
        load_data,
        main,
        parse_users_from_study_json,
    )
except ImportError as e:
    pytest.skip(f"Could not import module: {e}", allow_module_level=True)


class TestFolderStructureCreation:
    """Test folder structure creation functionality."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        test_dir = tempfile.mkdtemp()
        yield test_dir
        shutil.rmtree(test_dir)

    def test_create_basic_folder_structure(self, temp_dir):
        """Test creating basic folder structure with default settings."""
        result_path = create_folder_structure(
            target_path=temp_dir,
            investigation_label="TEST1",
            study_label="TEST2",
            study_slug="test-study",
            workpackage="WP1",
        )

        expected_main_folder = os.path.join(temp_dir, "i_WP1_TEST1/s_TEST1-TEST2_test-study")
        assert result_path == expected_main_folder
        assert os.path.exists(expected_main_folder)

        # Check default subfolders were created
        expected_subfolders = ["TEST1-TEST2_raw_data", "TEST1-TEST2_processed_data", "TEST1-TEST2_metadata"]

        for subfolder in expected_subfolders:
            subfolder_path = os.path.join(expected_main_folder, subfolder)
            assert os.path.exists(subfolder_path), f"Subfolder {subfolder} should exist"

        # Check policy file was created
        policy_path = os.path.join(expected_main_folder, "FOLDER_POLICY.md")
        assert os.path.exists(policy_path)

    def test_create_folder_structure_with_custom_name(self, temp_dir):
        """Test creating folder structure with custom folder name."""
        custom_name = "custom_project_folder"
        result_path = create_folder_structure(target_path=temp_dir, folder_name=custom_name, investigation_label="TEST1", study_label="TEST2")

        expected_path = os.path.join(temp_dir, custom_name)
        assert result_path == expected_path
        assert os.path.exists(expected_path)

    def test_create_folder_structure_with_custom_structure(self, temp_dir):
        """Test creating folder structure with custom folder structure."""
        custom_structure = {
            "data": {"raw": None, "processed": ["batch1", "batch2"]},
            "analysis": None,
            "docs": ["reports", "protocols"],
        }

        result_path = create_folder_structure(
            target_path=temp_dir,
            investigation_label="TEST1",
            study_label="TEST2",
            study_slug="test-study",
            workpackage="WP1",
            structure=custom_structure,
        )

        # Check custom structure was created with labels
        main_folder = result_path

        # Check labeled folders exist
        expected_folders = ["TEST1-TEST2_data", "TEST1-TEST2_analysis", "TEST1-TEST2_docs"]

        for folder in expected_folders:
            assert os.path.exists(os.path.join(main_folder, folder))

        # Check subfolders
        data_folder = os.path.join(main_folder, "TEST1-TEST2_data")
        assert os.path.exists(os.path.join(data_folder, "raw"))
        assert os.path.exists(os.path.join(data_folder, "processed", "batch1"))
        assert os.path.exists(os.path.join(data_folder, "processed", "batch2"))

        docs_folder = os.path.join(main_folder, "TEST1-TEST2_docs")
        assert os.path.exists(os.path.join(docs_folder, "reports"))
        assert os.path.exists(os.path.join(docs_folder, "protocols"))

    def test_existing_folders_not_deleted(self, temp_dir):
        """Test that existing folders are preserved and not deleted."""
        # Create initial structure
        result_path = create_folder_structure(
            target_path=temp_dir,
            investigation_label="TEST1",
            study_label="TEST2",
            study_slug="test-study",
            workpackage="WP1",
        )

        # Add a file to one of the subfolders
        subfolder_path = os.path.join(result_path, "TEST1-TEST2_raw_data")
        test_file = os.path.join(subfolder_path, "important_data.txt")
        with open(test_file, "w") as f:
            f.write("Important data that should not be lost")

        # Add a new subfolder with files
        user_folder = os.path.join(subfolder_path, "user_created_folder")
        os.makedirs(user_folder)
        user_file = os.path.join(user_folder, "user_file.csv")
        with open(user_file, "w") as f:
            f.write("user,data,values\nuser1,100,200\n")

        # Run folder creation again
        result_path_2 = create_folder_structure(
            target_path=temp_dir,
            investigation_label="TEST1",
            study_label="TEST2",
            study_slug="test-study",
            workpackage="WP1",
        )

        # Verify paths are the same
        assert result_path == result_path_2

        # Verify all user files and folders still exist
        assert os.path.exists(test_file)
        assert os.path.exists(user_folder)
        assert os.path.exists(user_file)

        # Verify file contents are unchanged
        with open(test_file) as f:
            content = f.read()
        assert content == "Important data that should not be lost"

        with open(user_file) as f:
            content = f.read()
        assert "user1,100,200" in content

    def test_existing_files_in_multiple_folders_preserved(self, temp_dir):
        """Test that existing files in multiple folders are preserved."""
        # Create initial structure
        result_path = create_folder_structure(
            target_path=temp_dir,
            investigation_label="TEST1",
            study_label="TEST2",
            study_slug="test-study",
            workpackage="WP1",
        )

        # Add files to multiple subfolders
        test_files = {}

        for folder_type in ["raw_data", "processed_data", "metadata"]:
            folder_path = os.path.join(result_path, f"TEST1-TEST2_{folder_type}")
            test_file = os.path.join(folder_path, f"test_{folder_type}.txt")
            test_content = f"Important {folder_type} content"

            with open(test_file, "w") as f:
                f.write(test_content)

            test_files[test_file] = test_content

        # Run folder creation again
        create_folder_structure(
            target_path=temp_dir,
            investigation_label="TEST1",
            study_label="TEST2",
            study_slug="test-study",
            workpackage="WP1",
        )

        # Verify all files still exist with correct content
        for file_path, expected_content in test_files.items():
            assert os.path.exists(file_path), f"File {file_path} should still exist"
            with open(file_path) as f:
                actual_content = f.read()
            assert actual_content == expected_content, f"Content of {file_path} should be unchanged"

    def test_invalid_target_path_raises_error(self):
        """Test that invalid target path raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="Target directory does not exist"):
            create_folder_structure(
                target_path="/nonexistent/path",
                investigation_label="TEST1",
                study_label="TEST2",
                study_slug="test-study",
                workpackage="WP1",
            )

    def test_missing_required_params_raises_error(self, temp_dir):
        """Test that missing required parameters raise ValueError."""
        with pytest.raises(ValueError, match="Either folder_name must be provided"):
            create_folder_structure(
                target_path=temp_dir,
                # Missing required parameters
                investigation_label=None,
                study_label="TEST2",
                study_slug="test-study",
                workpackage="WP1",
            )


class TestFolderPolicyCreation:
    """Test folder policy file creation."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        test_dir = tempfile.mkdtemp()
        yield test_dir
        shutil.rmtree(test_dir)

    def test_policy_file_created(self, temp_dir):
        """Test that policy file is created."""
        policy_path = create_folder_policy(
            folder_path=temp_dir,
            investigation_label="TEST1",
            study_label="TEST2",
            study_title="Test Study Title",
            sensitivity_level="INTERNAL",
            authorized_users=[],
        )

        expected_path = os.path.join(temp_dir, "FOLDER_POLICY.md")
        assert policy_path == expected_path
        assert os.path.exists(expected_path)
        assert os.path.isfile(expected_path)

    def test_policy_file_overwrite_protection(self, temp_dir):
        """Test that policy file is protected from overwriting unless explicitly allowed."""
        # Create initial policy file
        initial_content = "Initial policy content"
        policy_path = os.path.join(temp_dir, "FOLDER_POLICY.md")
        with open(policy_path, "w") as f:
            f.write(initial_content)

        # Try to create policy without overwrite flag
        create_folder_policy(
            folder_path=temp_dir,
            investigation_label="TEST1",
            study_label="TEST2",
            study_title="New Title",
            sensitivity_level="PUBLIC",
            authorized_users=[],
            overwrite_existing=False,
        )

        # Check original content is preserved
        with open(policy_path) as f:
            content = f.read()
        assert content == initial_content

    def test_policy_file_overwrite_with_backup(self, temp_dir):
        """Test that policy file can be overwritten and backup is created."""
        # Create initial policy file
        initial_content = "Initial policy content"
        policy_path = os.path.join(temp_dir, "FOLDER_POLICY.md")
        with open(policy_path, "w") as f:
            f.write(initial_content)

        # Overwrite with new policy
        create_folder_policy(
            folder_path=temp_dir,
            investigation_label="TEST1",
            study_label="TEST2",
            study_title="New Title",
            sensitivity_level="PUBLIC",
            authorized_users=[],
            overwrite_existing=True,
        )

        # Check new content exists and is different
        with open(policy_path) as f:
            content = f.read()
        assert content != initial_content

        # Check backup file exists
        backup_files = [f for f in os.listdir(temp_dir) if f.startswith("FOLDER_POLICY.md.bak.")]
        assert len(backup_files) == 1

        # Check backup content
        backup_path = os.path.join(temp_dir, backup_files[0])
        assert os.path.exists(backup_path)
        with open(backup_path) as f:
            backup_content = f.read()
        assert backup_content == initial_content


class TestUserParsing:
    """Test user parsing functionality."""

    def test_parse_users_from_study_json(self):
        """Test parsing users from study JSON data."""
        study_data = {
            "owners": ["Dr. Alice Smith (alice@example.org)", "Dr. Bob Jones (bob@example.org)"],
            "contributors": ["Dr. Carol Wilson (carol@example.org)", "Dr. David Brown (david@example.org)"],
            "readers": ["Dr. Eve Davis (eve@example.org)"],
        }

        users = parse_users_from_study_json(study_data)

        # Check correct number of users
        assert len(users) == 5

        # Check owners have correct access level
        owners = [u for u in users if u["role"] == "Owner"]
        assert len(owners) == 2
        for owner in owners:
            assert owner["access_level"] == "READ-WRITE"

        # Check contributors have correct access level
        contributors = [u for u in users if u["role"] == "Contributor"]
        assert len(contributors) == 2
        for contrib in contributors:
            assert contrib["access_level"] == "READ"

        # Check readers have correct access level
        readers = [u for u in users if u["role"] == "Reader"]
        assert len(readers) == 1
        for reader in readers:
            assert reader["access_level"] == "READ"

    def test_parse_users_empty_data(self):
        """Test parsing users from empty data."""
        study_data = {}
        users = parse_users_from_study_json(study_data)
        assert len(users) == 0


class TestConfigLoading:
    """Test configuration loading functionality."""

    def test_load_data_file_not_found(self):
        """Test that missing config file causes system exit."""
        with pytest.raises(SystemExit) as exc_info:
            load_data("nonexistent.json")
        assert exc_info.value.code == 1


class TestIntegrationWithStudyConfig:
    """Integration tests using complete study configuration."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        test_dir = tempfile.mkdtemp()
        yield test_dir
        shutil.rmtree(test_dir)

    @pytest.fixture
    def sample_study_config(self):
        """Sample study configuration data."""
        return {
            "accession_code": "TEST30",
            "investigation_accession_code": "TEST4",
            "investigation_work_package": "WP2",
            "title": ("Study of the influence of environmental factors on biological networks"),
            "slug": "environmental-factors-biological-networks",
            "effective_principal_investigator_name": "Dr. Jane Smith",
            "effective_principal_investigator_email": "jane.smith@example.org",
            "security_level": "internal",
            "owners": ["Dr. John Doe (john.doe@example.org)", "Dr. Alice Johnson (alice.johnson@example.org)"],
            "contributors": ["Dr. Bob Wilson (bob.wilson@example.org)", "Dr. Carol Brown (carol.brown@example.org)"],
            "readers": [],
            "folder_name": "i_WP2_TEST4/s_TEST4-TEST30_environmental-factors-biological-networks",
        }

    def test_integration_creates_structure_and_preserves_files(self, temp_dir, sample_study_config):
        """Test complete integration: creates structure and preserves existing files."""
        # Extract information directly from config (since extract_labels_from_folder_name was removed)
        folder_name = sample_study_config["folder_name"]
        workpackage = sample_study_config["investigation_work_package"]
        investigation_label = sample_study_config["investigation_accession_code"]
        study_label = sample_study_config["accession_code"]

        study_title = sample_study_config["title"]
        study_slug = sample_study_config["slug"]
        sensitivity_level = sample_study_config["security_level"].upper()
        pi_name = sample_study_config["effective_principal_investigator_name"]
        pi_email = sample_study_config["effective_principal_investigator_email"]
        authorized_users = parse_users_from_study_json(sample_study_config)

        # Create folder structure
        result_path = create_folder_structure(
            target_path=temp_dir,
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
        )

        # Verify folder structure was created correctly
        expected_path = os.path.join(temp_dir, folder_name)
        assert result_path == expected_path
        assert os.path.exists(expected_path)

        # Verify policy file exists
        policy_path = os.path.join(expected_path, "FOLDER_POLICY.md")
        assert os.path.exists(policy_path)

        # Add some user files
        raw_data_folder = os.path.join(expected_path, f"{investigation_label}-{study_label}_raw_data")
        user_file1 = os.path.join(raw_data_folder, "experiment_data.csv")
        with open(user_file1, "w") as f:
            f.write("sample,measurement,value\nsample1,temp,25.3\n")

        metadata_folder = os.path.join(expected_path, f"{investigation_label}-{study_label}_metadata")
        user_file2 = os.path.join(metadata_folder, "sample_info.json")
        with open(user_file2, "w") as f:
            f.write('{"sample1": {"location": "greenhouse", "treatment": "control"}}')

        # Run folder creation again
        result_path_2 = create_folder_structure(
            target_path=temp_dir,
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
        )

        # Verify paths are the same
        assert result_path == result_path_2

        # Verify user files are preserved
        assert os.path.exists(user_file1)
        assert os.path.exists(user_file2)

        # Verify file contents are unchanged
        with open(user_file1) as f:
            content = f.read()
        assert "sample1,temp,25.3" in content

        with open(user_file2) as f:
            content = f.read()
        assert "greenhouse" in content
        assert "control" in content


class TestErrorHandling:
    """Test error handling scenarios."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        test_dir = tempfile.mkdtemp()
        yield test_dir
        shutil.rmtree(test_dir)

    @patch("builtins.open", side_effect=PermissionError("Permission denied"))
    def test_policy_file_creation_permission_error(self, mock_open, temp_dir):  # noqa: ARG002
        """Test handling of permission errors when creating policy file."""
        # This should not raise an exception, just print an error
        policy_path = create_folder_policy(
            folder_path=temp_dir,
            investigation_label="TEST1",
            study_label="TEST2",
            study_title="Test Study",
            sensitivity_level="PUBLIC",
            authorized_users=[],
        )
        # The function should still return the expected path even if creation failed
        expected_path = os.path.join(temp_dir, "FOLDER_POLICY.md")
        assert policy_path == expected_path

    @patch("shutil.copy2", side_effect=PermissionError("Permission denied"))
    def test_policy_backup_permission_error(self, mock_copy, temp_dir):  # noqa: ARG002
        """Test handling of permission errors when creating backup."""
        # Create initial policy file
        policy_path = os.path.join(temp_dir, "FOLDER_POLICY.md")
        with open(policy_path, "w") as f:
            f.write("Initial content")

        # This should not raise an exception, just print a warning
        create_folder_policy(
            folder_path=temp_dir,
            investigation_label="TEST1",
            study_label="TEST2",
            study_title="New Title",
            sensitivity_level="PUBLIC",
            authorized_users=[],
            overwrite_existing=True,
        )


class TestMainFunctionIntegration:
    """Test main function and command line integration."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        test_dir = tempfile.mkdtemp()
        yield test_dir
        shutil.rmtree(test_dir)

    def test_create_folder_structure_with_all_params(self, temp_dir):
        """Test create_folder_structure with all possible parameters."""
        users = [{"name": "test user", "role": "Tester", "access_level": "READ", "expiration": "PERMANENT"}]

        result_path = create_folder_structure(
            target_path=temp_dir,
            folder_name="custom_folder",
            investigation_label="TEST1",
            study_label="TEST2",
            study_title="Complete Test Study",
            study_slug="complete-test-study",
            sensitivity_level="CONFIDENTIAL",
            authorized_users=users,
            pi_name="Test PI",
            pi_email="testpi@example.com",
            workpackage="WP1",
            structure={"custom": None},
            overwrite_existing=True,
        )

        expected_path = os.path.join(temp_dir, "custom_folder")
        assert result_path == expected_path
        assert os.path.exists(expected_path)


class TestCommandLineArguments:
    """Test command line argument parsing and main function behavior."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        test_dir = tempfile.mkdtemp()
        yield test_dir
        shutil.rmtree(test_dir)

    def test_basic_cli_args(self, temp_dir):
        """Test basic required CLI arguments: investigation, study, workpackage."""
        test_args = [
            "create_study_folder.py",
            "-i",
            "TEST1",
            "-s",
            "TEST2",
            "--workpackage",
            "WP1",
            "-t",
            temp_dir,
            "--no-email-notification",
        ]

        with patch("sys.argv", test_args):
            main()

        # Check that folder was created
        expected_folder = "s_WP1-TEST1-TEST2_test2"
        expected_path = os.path.join(temp_dir, expected_folder)
        assert os.path.exists(expected_path)

    def test_cli_with_study_title_arg(self, temp_dir):
        """Test --study_title CLI argument."""
        test_args = [
            "create_study_folder.py",
            "-i",
            "TEST1",
            "-s",
            "TEST2",
            "--workpackage",
            "WP1",
            "--study_title",
            "My Test Study",
            "-t",
            temp_dir,
            "--no-email-notification",
        ]

        with patch("sys.argv", test_args):
            main()

        # Check folder was created with slug from title
        expected_folder = "s_WP1-TEST1-TEST2_my-test-study"
        expected_path = os.path.join(temp_dir, expected_folder)
        assert os.path.exists(expected_path)

        # Check policy file contains the title
        policy_path = os.path.join(expected_path, "FOLDER_POLICY.md")
        with open(policy_path) as f:
            content = f.read()
        assert "My Test Study" in content

    def test_cli_with_custom_slug(self, temp_dir):
        """Test --slug CLI argument."""
        test_args = [
            "create_study_folder.py",
            "-i",
            "TEST1",
            "-s",
            "TEST2",
            "--workpackage",
            "WP1",
            "--slug",
            "custom-slug-name",
            "-t",
            temp_dir,
            "--no-email-notification",
        ]

        with patch("sys.argv", test_args):
            main()

        expected_folder = "s_WP1-TEST1-TEST2_custom-slug-name"
        expected_path = os.path.join(temp_dir, expected_folder)
        assert os.path.exists(expected_path)

    def test_cli_with_folder_name_arg(self, temp_dir):
        """Test --folder-name CLI argument."""
        test_args = [
            "create_study_folder.py",
            "--folder-name",
            "my-custom-folder",
            "-i",
            "TEST1",
            "-s",
            "TEST2",
            "--workpackage",
            "WP1",
            "-t",
            temp_dir,
            "--no-email-notification",
        ]

        with patch("sys.argv", test_args):
            main()

        expected_path = os.path.join(temp_dir, "my-custom-folder")
        assert os.path.exists(expected_path)

    def test_cli_with_sensitivity_arg(self, temp_dir):
        """Test --sensitivity CLI argument with all valid choices."""
        sensitivity_levels = ["PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED"]

        for level in sensitivity_levels:
            test_args = [
                "create_study_folder.py",
                "-i",
                "TEST1",
                "-s",
                "TEST2",
                "--workpackage",
                "WP1",
                "--sensitivity",
                level,
                "-t",
                temp_dir,
                "--no-email-notification",
            ]

            with patch("sys.argv", test_args):
                main()

            # Check policy file contains the sensitivity level
            expected_folder = "s_WP1-TEST1-TEST2_test2"
            policy_path = os.path.join(temp_dir, expected_folder, "FOLDER_POLICY.md")
            with open(policy_path) as f:
                content = f.read()
            assert level in content

    def test_cli_with_pi_args(self, temp_dir):
        """Test --pi-name and --pi-email CLI arguments."""
        test_args = [
            "create_study_folder.py",
            "-i",
            "TEST1",
            "-s",
            "TEST2",
            "--workpackage",
            "WP1",
            "--pi-name",
            "Dr. Jane Smith",
            "--pi-email",
            "jane.smith@example.org",
            "-t",
            temp_dir,
            "--no-email-notification",
        ]

        with patch("sys.argv", test_args):
            main()

        # Check policy file contains PI information
        expected_folder = "s_WP1-TEST1-TEST2_test2"
        policy_path = os.path.join(temp_dir, expected_folder, "FOLDER_POLICY.md")
        with open(policy_path) as f:
            content = f.read()
        assert "Dr. Jane Smith" in content
        assert "jane.smith@example.org" in content

    def test_cli_with_dataset_admin_args(self, temp_dir):
        """Test --dataset-admin-name and --dataset-admin-email CLI arguments."""
        test_args = [
            "create_study_folder.py",
            "-i",
            "TEST1",
            "-s",
            "TEST2",
            "--workpackage",
            "WP1",
            "--dataset-admin-name",
            "Dr. Bob Jones",
            "--dataset-admin-email",
            "bob.jones@example.org",
            "-t",
            temp_dir,
            "--no-email-notification",
        ]

        with patch("sys.argv", test_args):
            main()

        # Check policy file contains dataset admin information
        expected_folder = "s_WP1-TEST1-TEST2_test2"
        policy_path = os.path.join(temp_dir, expected_folder, "FOLDER_POLICY.md")
        with open(policy_path) as f:
            content = f.read()
        assert "Dr. Bob Jones" in content
        assert "bob.jones@example.org" in content

    def test_cli_with_investigation_title_arg(self, temp_dir):
        """Test --investigation-title CLI argument."""
        test_args = [
            "create_study_folder.py",
            "-i",
            "TEST1",
            "-s",
            "TEST2",
            "--workpackage",
            "WP1",
            "--investigation-title",
            "My Investigation Title",
            "-t",
            temp_dir,
            "--no-email-notification",
        ]

        with patch("sys.argv", test_args):
            main()

        # Check policy file contains investigation title
        expected_folder = "s_WP1-TEST1-TEST2_test2"
        policy_path = os.path.join(temp_dir, expected_folder, "FOLDER_POLICY.md")
        with open(policy_path) as f:
            content = f.read()
        assert "My Investigation Title" in content

    def test_cli_with_description_arg(self, temp_dir):
        """Test --description CLI argument."""
        test_args = [
            "create_study_folder.py",
            "-i",
            "TEST1",
            "-s",
            "TEST2",
            "--workpackage",
            "WP1",
            "--description",
            "This is a test study description",
            "-t",
            temp_dir,
            "--no-email-notification",
        ]

        with patch("sys.argv", test_args):
            main()

        # Check policy file contains description
        expected_folder = "s_WP1-TEST1-TEST2_test2"
        policy_path = os.path.join(temp_dir, expected_folder, "FOLDER_POLICY.md")
        with open(policy_path) as f:
            content = f.read()
        assert "This is a test study description" in content

    def test_cli_with_structure_file_arg(self, temp_dir):
        """Test --structure-file CLI argument."""
        # Create a custom structure JSON file
        structure = {
            "custom_raw": None,
            "custom_processed": ["batch1", "batch2"],
            "custom_analysis": None,
        }
        structure_file = os.path.join(temp_dir, "custom_structure.json")
        with open(structure_file, "w") as f:
            json.dump(structure, f)

        test_args = [
            "create_study_folder.py",
            "-i",
            "TEST1",
            "-s",
            "TEST2",
            "--workpackage",
            "WP1",
            "--structure-file",
            structure_file,
            "-t",
            temp_dir,
            "--no-email-notification",
        ]

        with patch("sys.argv", test_args):
            main()

        # Check custom structure was created
        expected_folder = "s_WP1-TEST1-TEST2_test2"
        expected_path = os.path.join(temp_dir, expected_folder)

        # Check labeled folders exist
        assert os.path.exists(os.path.join(expected_path, "TEST2_custom_raw"))
        assert os.path.exists(os.path.join(expected_path, "TEST2_custom_processed"))
        assert os.path.exists(os.path.join(expected_path, "TEST2_custom_analysis"))
        assert os.path.exists(os.path.join(expected_path, "TEST2_custom_processed", "batch1"))
        assert os.path.exists(os.path.join(expected_path, "TEST2_custom_processed", "batch2"))

    def test_cli_overwrite_flag(self, temp_dir):
        """Test --overwrite flag for FOLDER_POLICY.md file."""
        test_args = [
            "create_study_folder.py",
            "-i",
            "TEST1",
            "-s",
            "TEST2",
            "--workpackage",
            "WP1",
            "--study_title",
            "First Title",
            "--slug",
            "test-study",  # Use fixed slug
            "-t",
            temp_dir,
            "--no-email-notification",
        ]

        # Create initial folder
        with patch("sys.argv", test_args):
            main()

        expected_folder = "s_WP1-TEST1-TEST2_test-study"
        policy_path = os.path.join(temp_dir, expected_folder, "FOLDER_POLICY.md")

        # Verify first title is in policy
        with open(policy_path) as f:
            content = f.read()
        assert "First Title" in content

        # Try to update without overwrite flag
        test_args_no_overwrite = [
            "create_study_folder.py",
            "-i",
            "TEST1",
            "-s",
            "TEST2",
            "--workpackage",
            "WP1",
            "--study_title",
            "Second Title",
            "--slug",
            "test-study",  # Use same slug
            "-t",
            temp_dir,
            "--no-email-notification",
        ]

        with patch("sys.argv", test_args_no_overwrite):
            main()

        # Policy should still have first title
        with open(policy_path) as f:
            content = f.read()
        assert "First Title" in content
        assert "Second Title" not in content

        # Update with overwrite flag
        test_args_with_overwrite = [
            "create_study_folder.py",
            "-i",
            "TEST1",
            "-s",
            "TEST2",
            "--workpackage",
            "WP1",
            "--study_title",
            "Second Title",
            "--slug",
            "test-study",  # Use same slug
            "-t",
            temp_dir,
            "--overwrite",
            "--no-email-notification",
        ]

        with patch("sys.argv", test_args_with_overwrite):
            main()

        # Policy should now have second title
        with open(policy_path) as f:
            content = f.read()
        assert "Second Title" in content

        # Backup file should exist
        backup_files = [f for f in os.listdir(os.path.join(temp_dir, expected_folder)) if f.startswith("FOLDER_POLICY.md.bak.")]
        assert len(backup_files) >= 1

    def test_cli_create_investigation_folder_flag(self, temp_dir):
        """Test --create-investigation-folder flag."""
        test_args = [
            "create_study_folder.py",
            "-i",
            "TEST1",
            "-s",
            "TEST2",
            "--workpackage",
            "WP1",
            "--create-investigation-folder",
            "-t",
            temp_dir,
            "--no-email-notification",
        ]

        with patch("sys.argv", test_args):
            main()

        # Check that investigation folder was created
        investigation_folder = "i_WP1_TEST1"
        investigation_path = os.path.join(temp_dir, investigation_folder)
        assert os.path.exists(investigation_path)

        # Check that study folder is inside investigation folder
        study_folder = "s_WP1-TEST1-TEST2_test2"
        study_path = os.path.join(investigation_path, study_folder)
        assert os.path.exists(study_path)

    def test_cli_no_email_notification_flag(self, temp_dir, capsys):
        """Test --no-email-notification flag."""
        # Test with flag - should not print email
        test_args_with_flag = [
            "create_study_folder.py",
            "-i",
            "TEST1",
            "-s",
            "TEST2",
            "--workpackage",
            "WP1",
            "-t",
            temp_dir,
            "--no-email-notification",
        ]

        with patch("sys.argv", test_args_with_flag):
            main()

        captured = capsys.readouterr()
        assert "EMAIL NOTIFICATION:" not in captured.out

        # Test without flag - should print email
        test_args_without_flag = [
            "create_study_folder.py",
            "-i",
            "TEST3",
            "-s",
            "TEST4",
            "--workpackage",
            "WP2",
            "-t",
            temp_dir,
        ]

        with patch("sys.argv", test_args_without_flag):
            main()

        captured = capsys.readouterr()
        assert "EMAIL NOTIFICATION:" in captured.out
        assert "Dear Researchers" in captured.out

    def test_cli_with_data_file_arg(self, temp_dir):
        """Test --data CLI argument with JSON file."""
        # Create a study data JSON file
        study_data = {
            "accession_code": "CXRS001",
            "investigation_accession_code": "CXRI001",
            "investigation_work_package": "WP3",
            "title": "Test Study from JSON",
            "slug": "test-study-from-json",
            "description": "This study was loaded from JSON",
            "investigation_title": "Test Investigation",
            "security_level": "INTERNAL",
            "principal_investigator": {
                "first_name": "Alice",
                "last_name": "Johnson",
                "email": "alice.johnson@example.org",
            },
            "dataset_administrator": {
                "first_name": "Bob",
                "last_name": "Smith",
                "email": "bob.smith@example.org",
            },
        }

        data_file = os.path.join(temp_dir, "study_data.json")
        with open(data_file, "w") as f:
            json.dump(study_data, f)

        test_args = [
            "create_study_folder.py",
            "--data",
            data_file,
            "-t",
            temp_dir,
            "--no-email-notification",
        ]

        with patch("sys.argv", test_args):
            main()

        # Check folder was created with data from JSON
        expected_folder = "s_WP3-CXRI001-CXRS001_test-study-from-json"
        expected_path = os.path.join(temp_dir, expected_folder)
        assert os.path.exists(expected_path)

        # Check policy file contains data from JSON
        policy_path = os.path.join(expected_path, "FOLDER_POLICY.md")
        with open(policy_path) as f:
            content = f.read()
        assert "Test Study from JSON" in content
        assert "This study was loaded from JSON" in content
        assert "Test Investigation" in content
        assert "Alice Johnson" in content
        assert "Bob Smith" in content
        assert "INTERNAL" in content

    def test_cli_data_file_overrides_with_cli_args(self, temp_dir):
        """Test that CLI arguments override values from --data file."""
        # Create a study data JSON file
        study_data = {
            "accession_code": "CXRS001",
            "investigation_accession_code": "CXRI001",
            "investigation_work_package": "WP3",
            "title": "Original Title",
            "slug": "original-slug",
        }

        data_file = os.path.join(temp_dir, "study_data.json")
        with open(data_file, "w") as f:
            json.dump(study_data, f)

        test_args = [
            "create_study_folder.py",
            "--data",
            data_file,
            "--study_title",
            "Overridden Title",
            "--slug",
            "overridden-slug",
            "-t",
            temp_dir,
            "--no-email-notification",
        ]

        with patch("sys.argv", test_args):
            main()

        # Check folder was created with overridden slug
        expected_folder = "s_WP3-CXRI001-CXRS001_overridden-slug"
        expected_path = os.path.join(temp_dir, expected_folder)
        assert os.path.exists(expected_path)

        # Check policy file contains overridden title
        policy_path = os.path.join(expected_path, "FOLDER_POLICY.md")
        with open(policy_path) as f:
            content = f.read()
        assert "Overridden Title" in content
        assert "Original Title" not in content

    def test_cli_api_url_arg(self, temp_dir):
        """Test --api-url CLI argument."""
        # Mock the API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "accession_code": "CXRS002",
            "investigation_accession_code": "CXRI002",
            "investigation_work_package": "WP4",
            "title": "Study from API",
            "slug": "study-from-api",
            "security_level": "PUBLIC",
            "principal_investigator": {
                "first_name": "Carol",
                "last_name": "White",
                "email": "carol.white@example.org",
            },
        }

        test_args = [
            "create_study_folder.py",
            "--api-url",
            "https://example.com/api/studies/CXRS002/",
            "-t",
            temp_dir,
            "--no-email-notification",
        ]

        with patch("sys.argv", test_args), patch("requests.get", return_value=mock_response):
            main()

        # Check folder was created with data from API
        expected_folder = "s_WP4-CXRI002-CXRS002_study-from-api"
        expected_path = os.path.join(temp_dir, expected_folder)
        assert os.path.exists(expected_path)

        # Check policy file contains data from API
        policy_path = os.path.join(expected_path, "FOLDER_POLICY.md")
        with open(policy_path) as f:
            content = f.read()
        assert "Study from API" in content
        assert "Carol White" in content

    def test_cli_api_url_with_token(self, temp_dir):
        """Test --api-url with --api-token CLI arguments."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "accession_code": "CXRS003",
            "investigation_accession_code": "CXRI003",
            "investigation_work_package": "WP5",
            "title": "Authenticated Study",
            "slug": "authenticated-study",
            "security_level": "RESTRICTED",
        }

        test_args = [
            "create_study_folder.py",
            "--api-url",
            "https://example.com/api/studies/CXRS003/",
            "--api-token",
            "test-token-123",
            "-t",
            temp_dir,
            "--no-email-notification",
        ]

        with patch("sys.argv", test_args), patch("requests.get", return_value=mock_response) as mock_get:
            main()

        # Verify the request was made with authorization header
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args[1]
        assert "headers" in call_kwargs
        assert "Authorization" in call_kwargs["headers"]
        assert call_kwargs["headers"]["Authorization"] == "Token test-token-123"

        # Check folder was created
        expected_folder = "s_WP5-CXRI003-CXRS003_authenticated-study"
        expected_path = os.path.join(temp_dir, expected_folder)
        assert os.path.exists(expected_path)

    def test_cli_missing_required_args_error(self):
        """Test that missing required arguments raises error."""
        # Missing investigation when not using --data
        test_args = [
            "create_study_folder.py",
            "-s",
            "TEST2",
            "--workpackage",
            "WP1",
        ]

        with patch("sys.argv", test_args):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 2  # argparse error code

    def test_cli_data_and_api_url_both_provided_error(self, temp_dir):
        """Test that providing both --data and --api-url raises error."""
        data_file = os.path.join(temp_dir, "study_data.json")
        with open(data_file, "w") as f:
            json.dump({"accession_code": "TEST"}, f)

        test_args = [
            "create_study_folder.py",
            "--data",
            data_file,
            "--api-url",
            "https://example.com/api/studies/TEST/",
            "-t",
            temp_dir,
        ]

        with patch("sys.argv", test_args):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 2  # argparse error code

    def test_cli_invalid_sensitivity_value_error(self):
        """Test that invalid sensitivity value raises error."""
        test_args = [
            "create_study_folder.py",
            "-i",
            "TEST1",
            "-s",
            "TEST2",
            "--workpackage",
            "WP1",
            "--sensitivity",
            "INVALID",  # Invalid choice
        ]

        with patch("sys.argv", test_args):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 2  # argparse error code

    def test_cli_target_directory_not_exists_error(self):
        """Test that non-existent target directory raises error."""
        test_args = [
            "create_study_folder.py",
            "-i",
            "TEST1",
            "-s",
            "TEST2",
            "--workpackage",
            "WP1",
            "-t",
            "/nonexistent/directory/path",
            "--no-email-notification",
        ]

        with patch("sys.argv", test_args):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    def test_cli_invalid_structure_file_error(self, temp_dir):
        """Test that invalid structure file raises error."""
        # Create an invalid JSON file
        structure_file = os.path.join(temp_dir, "invalid.json")
        with open(structure_file, "w") as f:
            f.write("{ invalid json content")

        test_args = [
            "create_study_folder.py",
            "-i",
            "TEST1",
            "-s",
            "TEST2",
            "--workpackage",
            "WP1",
            "--structure-file",
            structure_file,
            "-t",
            temp_dir,
            "--no-email-notification",
        ]

        with patch("sys.argv", test_args):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1
