import os
import shutil
import tempfile
from unittest.mock import patch

import pytest

try:
    from dataxr_tools.research_drive.create_study_folder import (
        create_folder_policy,
        create_folder_structure,
        load_study_config,
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
        result_path = create_folder_structure(
            target_path=temp_dir, folder_name=custom_name, investigation_label="TEST1", study_label="TEST2"
        )

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

    def test_load_study_config_file_not_found(self):
        """Test that missing config file causes system exit."""
        with pytest.raises(SystemExit) as exc_info:
            load_study_config("nonexistent.json")
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
