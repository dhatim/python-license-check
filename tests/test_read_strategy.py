import os

import pytest

from liccheck.command_line import Strategy, read_strategy

@pytest.fixture
def empty_pyproject_toml_in_cwd(tmpdir):
    cwd = os.getcwd()
    os.chdir(tmpdir)
    with open("pyproject.toml", "w") as file:
        pass
    yield
    os.chdir(cwd)


def test_absent_sections(tmpfile):
    tmpfh, tmppath = tmpfile
    tmpfh.write("""
[Licenses]
""")
    tmpfh.close()
    strategy = Strategy.from_config(path=tmppath)
    assert strategy.AUTHORIZED_LICENSES == []
    assert strategy.UNAUTHORIZED_LICENSES == []
    assert strategy.AUTHORIZED_PACKAGES == {}


def test_falls_back_to_strategy_file_if_no_pyproject_toml(mocker):
    from_strategy_mock = mocker.patch("liccheck.command_line.Strategy.from_config")
    read_strategy("strategy_file")
    from_strategy_mock.assert_called_once_with(path="strategy_file")


@pytest.mark.usefixtures("empty_pyproject_toml_in_cwd")
def test_falls_back_to_strategy_if_no_liccheck_section_in_pyproject_toml(mocker):
    from_config_mock = mocker.patch("liccheck.command_line.Strategy.from_config")
    read_strategy("strategy_file")
    from_config_mock.assert_called_once_with(path="strategy_file")
