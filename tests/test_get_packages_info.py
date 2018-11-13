import sys

import pytest

from liccheck.command_line import get_packages_info


def test_license_strip(tmpfile):
    tmpfh, tmppath = tmpfile
    tmpfh.write("pip\n")
    tmpfh.close()
    assert get_packages_info(tmppath)[0]["licenses"] == ["MIT"]

def test_requirements_markers(tmpfile):
    tmpfh, tmppath = tmpfile
    tmpfh.write(
        "python-openid;python_version<=\"2.7\"\n"
        "python3-openid;python_version>=\"3.0\"\n"
    )
    tmpfh.close()
    if sys.version_info.major == 3:
        assert len(get_packages_info(tmppath)) == 2
    else:
        assert len(get_packages_info(tmppath)) == 1
