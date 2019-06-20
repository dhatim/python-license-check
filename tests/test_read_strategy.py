from liccheck.command_line import Strategy, read_strategy


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
