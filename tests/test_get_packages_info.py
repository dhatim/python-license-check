import sys

import pkg_resources
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
            ('configparser', 'liccheck', 'semantic-version', 'toml'),
            marks=pytest.mark.skipif(
                sys.version_info[0] < 3,
                reason='with py2 there are more dependencies',
            ),
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


def test_license_expression(tmp_path, mocker):
    resolve = mocker.patch("liccheck.command_line.resolve")
    req_path = tmp_path.joinpath("requirements.txt").as_posix()
    with open(req_path, "w") as tmpfh:
        tmpfh.write("Twisted\n")
    pkg_info_path = tmp_path.joinpath("PKG-INFO").as_posix()
    with open(pkg_info_path, "w") as tmpfh:
        tmpfh.write("Metadata-Version: 2.1\n")
        tmpfh.write("Name: Twisted\n")
        tmpfh.write("Version: 23.8.0\n")
        tmpfh.write("License-Expression: MIT\n")
    metadata = pkg_resources.FileMetadata(pkg_info_path)
    resolve.return_value = [
        pkg_resources.Distribution(project_name="Twisted", metadata=metadata)
    ]
    assert get_packages_info(req_path)[0]["licenses"] == ["MIT"]
