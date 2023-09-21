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
        "python3-openid;python_version>=\"3.9\"\n"
    )
    tmpfh.close()
    if sys.version_info.minor >= 9:
        assert len(get_packages_info(tmppath)) == 2
    else:
        assert len(get_packages_info(tmppath)) == 0


def test_editable_requirements_get_ignored(tmpfile):
    tmpfh, tmppath = tmpfile
    tmpfh.write(
        "-e file:some_editable_req\n"
        "pip\n"
    )
    tmpfh.close()

    packages_info = get_packages_info(tmppath)
    assert len(packages_info) == 1
    assert packages_info[0]["name"] == "pip"


@pytest.mark.parametrize(
    ('no_deps', 'expected_packages'), (
        pytest.param(
            False,
            ('liccheck', 'semantic-version', 'toml'),
            id='with deps'
        ),
        pytest.param(True, ('liccheck',), id='without deps'),
    )
)
def test_deps(tmpfile, no_deps, expected_packages):
    tmpfh, tmppath = tmpfile
    tmpfh.write('liccheck\n')
    tmpfh.close()
    packages_info = get_packages_info(tmppath, no_deps)
    packages = tuple(package['name'] for package in packages_info)
    assert packages == expected_packages
