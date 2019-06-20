import os

import pytest

from liccheck.command_line import Strategy, NoValidConfigurationInPyprojectToml


@pytest.fixture
def empty_pyproject_toml_in_cwd(tmpdir):
    cwd = os.getcwd()
    os.chdir(tmpdir)
    open("pyproject.toml", "w").close()
    yield
    os.chdir(cwd)


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
    def test_falls_back_to_strategy_if_no_liccheck_section_in_pyproject_toml(self, mocker):
        with pytest.raises(NoValidConfigurationInPyprojectToml):
            Strategy.from_pyproject_toml()
