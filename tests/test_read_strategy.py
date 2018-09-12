import pytest

from liccheck.command_line import read_strategy


def test_absent_sections(tmpfile):
    tmpfh, tmppath = tmpfile
    tmpfh.write("""
[Licenses]
""")
    tmpfh.close()
    strategy = read_strategy(tmppath)
    assert strategy.AUTHORIZED_LICENSES == []
    assert strategy.UNAUTHORIZED_LICENSES == []
    assert strategy.AUTHORIZED_PACKAGES == {}
