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

    @pytest.mark.usefixtures("pyproject_toml_poetry_in_cwd")
    def test_with_poetry_toml(self):
        strategy = Strategy.from_pyproject_toml()
        assert "python software foundation license" in strategy.AUTHORIZED_LICENSES
        assert "gpl v3" in strategy.UNAUTHORIZED_LICENSES


    @pytest.fixture
    def empty_pyproject_toml_in_cwd(self, tmpdir):
        cwd = os.getcwd()
        os.chdir(str(tmpdir))
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
                  "BSD",
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

    @pytest.fixture
    def pyproject_toml_poetry_in_cwd(self, empty_pyproject_toml_in_cwd):
        with open("pyproject.toml", "w") as file:
            file.write(
                """
                [tool.poetry]
                name = "liccheck"
                version = "0.8.3"
                description = "Check python packages from requirement.txt and report issues"
                authors = ["Dhatim <contact@dhatim.com>"]
                license = "Apache Software License"
                readme = "README.rst"

                [tool.poetry.dependencies]
                python = "^3.9"
                semantic-version = "^2.10.0"
                toml = "^0.10.2"

                [tool.poetry.group.dev.dependencies]
                pytest = ">=3.6.3"
                pytest-cov = "^4.0.0"
                python3-openid = "^3.2.0"
                pytest-mock = ">=1.10"

                [build-system]
                requires = ["poetry-core"]
                build-backend = "poetry.core.masonry.api"

                [tool.poetry.scripts]
                liccheck = 'liccheck.command_line:main'

                [tool.liccheck]
                authorized_licenses = [
                    "new BSD",
                    "BSD license",
                    "new BDS license",
                    "simplified BSD",
                    "Apache",
                    "Apache 2.0",
                    "Apache software license",
                    "gnu LGPL",
                    "LGPL with exceptions or zpl",
                    "ISC license",
                    "ISC license (ISCL)",
                    "MIT",
                    "MIT license",
                    "python software foundation license",
                    "zpl 2.1"
                ]
                unauthorized_licenses = [
                    "GPL v3",
                    "GPL2",
                    "GNU General Public License v2 or later (GPLv2+)"
                ]
                authorized_packages = [
                    "uuid: 1.25,>=1.30"
                ]
                dependencies = true
                optional_dependencies = ['*']
                """
            )


class TestReadStrategy:
    @pytest.mark.usefixtures("from_pyproject_toml_raising")
    def test_falls_back_to_config_if_no_valid_pyproject_toml(self, mocker):
        from_config_mock = mocker.patch("liccheck.command_line.Strategy.from_config")
        mocker.patch("os.path.isfile", return_value=True)
        read_strategy(strategy_file="strategy_file")
        from_config_mock.assert_called_once_with(strategy_file="strategy_file")

    @pytest.mark.usefixtures("from_pyproject_toml_raising")
    def test_displays_error_if_no_valid_pyproject_toml_and_no_strategy_file(self, capsys, mocker):
        mocker.patch("os.path.isfile", return_value=False)
        with pytest.raises(SystemExit) as exc:
            read_strategy(strategy_file="./liccheck.ini")
        assert exc.value.code == 1
        capture_result = capsys.readouterr()
        std, _ = capture_result
        assert "Need to either configure pyproject.toml or provide an existing strategy file" in std.split("\n")

    @pytest.fixture
    def from_pyproject_toml_raising(self, mocker):
        mocker.patch(
            "liccheck.command_line.Strategy.from_pyproject_toml",
            side_effect=NoValidConfigurationInPyprojectToml
        )
