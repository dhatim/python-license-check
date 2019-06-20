import os

import pytest

from liccheck.command_line import Strategy, NoValidConfigurationInPyprojectToml


def test_absent_sections_in_config_file(tmpfile):
    tmpfh, tmppath = tmpfile
    tmpfh.write("""
[Licenses]
""")
    tmpfh.close()
    strategy = Strategy.from_config(path=tmppath)
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
