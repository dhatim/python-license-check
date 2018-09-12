import os
import tempfile

import pytest

from liccheck.command_line import check_package, Strategy, Reason, Level, get_packages_info

OK = Reason.OK
UNAUTH = Reason.UNAUTHORIZED
UNKNOWN = Reason.UNKNOWN


@pytest.fixture('session')
def strategy():
    strategy = Strategy()
    strategy.AUTHORIZED_LICENSES = ['authorized 1', 'authorized 2']
    strategy.UNAUTHORIZED_LICENSES = ['unauthorized 1', 'unauthorized 2']
    strategy.AUTHORIZED_PACKAGES = {'whitelisted': '1'}

    return strategy


@pytest.fixture('session')
def packages():
    return [
        {
            'name': 'auth_one', 'version': '1',
            'licenses': ['authorized 1'],
        }, {
            'name': 'auth_one_and_two', 'version': '2',
            'licenses': ['authorized 1', 'authorized 2'],
        }, {
            'name': 'auth_one_unauth_one', 'version': '1',
            'licenses': ['authorized 1', 'unauthorized 1'],
        }, {
            'name': 'unauth_one', 'version': '2',
            'licenses': ['unauthorized 1'],
        }, {
            'name': 'whitelisted', 'version': '1',
            'licenses': ['unauthorized 1'],
        }, {
            'name': 'whitelisted', 'version': '2',
            'licenses': ['unauthorized 1'],
        }, {
            'name': 'auth_one_unknown', 'version': '1',
            'licenses': ['authorized 1', 'unknown'],
        }, {
            'name': 'unknown', 'version': '3',
            'licenses': ['unknown'],
        },
    ]


@pytest.mark.parametrize(
    ('level', 'reasons'),
    [(Level.STANDARD, [OK, OK, OK,     UNAUTH, OK, UNAUTH, OK,      UNKNOWN]),
     (Level.CAUTIOUS, [OK, OK, UNAUTH, UNAUTH, OK, UNAUTH, OK,      UNKNOWN]),
     (Level.PARANOID, [OK, OK, UNAUTH, UNAUTH, OK, UNAUTH, UNKNOWN, UNKNOWN]),
     ],
    ids=[level.name for level in Level])
def test_check_package(strategy, packages, level, reasons):
    for package, reason in zip(packages, reasons):
        assert check_package(strategy, package, level) is reason


@pytest.fixture("session")
def tmpfile():
    fd, filepath = tempfile.mkstemp()
    yield (os.fdopen(fd, "w"), filepath)
    try:
        os.close(fd)
    except OSError:
        pass # It may already be closed
    os.remove(filepath)

def test_license_strip(strategy, tmpfile):
    tmpfh, tmppath = tmpfile
    tmpfh.write("pip\n")
    tmpfh.close()
    assert get_packages_info(tmppath)[0]["licenses"] == ["MIT"]
