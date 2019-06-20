import os

import pytest

from liccheck.command_line import Strategy, NoValidConfigurationInPyprojectToml, read_strategy


class TestReadFromConfig:
    def test_absent_sections_in_config_file(self, tmpfile):
        tmpfh, tmppath = tmpfile
        tmpfh.write("""
    [Licenses]
    """)
        tmpfh.close()
        strategy = Strategy.from_config(strategy_file=tmppath)
        assert strategy.AUTHORIZED_LICENSES == []
        assert strategy.UNAUTHORIZED_LICENSES == []
        assert strategy.AUTHORIZED_PACKAGES == {}


class TestReadFromPyprojectToml:
    def test_raises_if_no_pyproject_toml(self):
        with pytest.raises(NoValidConfigurationInPyprojectToml):
            Strategy.from_pyproject_toml()

    @pytest.mark.usefixtures("empty_pyproject_toml_in_cwd")
    def test_falls_back_to_strategy_if_no_liccheck_section_in_pyproject_toml(self):
        with pytest.raises(NoValidConfigurationInPyprojectToml):
            Strategy.from_pyproject_toml()

    @pytest.mark.usefixtures("pyproject_toml_with_liccheck_section_in_cwd")
    def test_with_liccheck_section_in_pyproject_toml(self):
        strategy = Strategy.from_pyproject_toml()
        assert strategy.AUTHORIZED_LICENSES == [
            "bsd",
            "new bsd",
            "bsd license"
        ]
        assert strategy.UNAUTHORIZED_LICENSES == [
            "gpl v3"
        ]
        assert strategy.AUTHORIZED_PACKAGES == {
            "uuid": "1.30"
        }

    @pytest.fixture
    def empty_pyproject_toml_in_cwd(self, tmpdir):
        cwd = os.getcwd()
        os.chdir(tmpdir)
        open("pyproject.toml", "w").close()
        yield
        os.chdir(cwd)

    @pytest.fixture
    def pyproject_toml_with_liccheck_section_in_cwd(self, empty_pyproject_toml_in_cwd):
        with open("pyproject.toml", "w") as file:
            file.write(
                """
                [tool.liccheck]
                authorized_licenses = [
                  "bsd",
                  "new bsd",
                  "bsd license"
                ]
                unauthorized_licenses = [
                  "gpl v3"
                ]
                [tool.liccheck.authorized_packages]
                uuid = "1.30"
                """
            )


class TestReadStrategy:
    @pytest.mark.usefixtures("from_pyproject_toml_raising")
    def test_falls_back_to_config_if_no_valid_pyproject_toml(self, mocker):
        from_config_mock = mocker.patch("liccheck.command_line.Strategy.from_config")
        read_strategy(strategy_file="strategy_file")
        from_config_mock.assert_called_once_with(strategy_file="strategy_file")

    @pytest.mark.usefixtures("from_pyproject_toml_raising")
    def test_displays_error_if_no_valid_pyproject_toml_and_no_strategy_file(self, capsys):
        with pytest.raises(SystemExit) as exc:
           read_strategy(strategy_file=None)
        assert exc.value.code == 1
        capture_result = capsys.readouterr()
        _, err = capture_result
        assert "Need to either configure pyproject.toml or provide a strategy file" in err.split("\n")

    @pytest.fixture
    def from_pyproject_toml_raising(self, mocker):
        mocker.patch(
            "liccheck.command_line.Strategy.from_pyproject_toml",
            side_effect=NoValidConfigurationInPyprojectToml
        )
