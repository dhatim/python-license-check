import pytest

from liccheck.command_line import get_packages_info


def test_license_strip(tmpfile):
    tmpfh, tmppath = tmpfile
    tmpfh.write("pip\n")
    tmpfh.close()
    assert get_packages_info(tmppath)[0]["licenses"] == ["MIT"]
