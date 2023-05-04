import pytest

from liccheck.command_line import check_package, Strategy, Reason, Level

OK = Reason.OK
UNAUTH = Reason.UNAUTHORIZED
UNKNOWN = Reason.UNKNOWN


@pytest.fixture(scope="session")
def packages():
    return [
        {
            "name": "auth_one",
            "version": "1",
            "licenses": ["authorized 1"],
        },
        {
            "name": "auth_one_and_two",
            "version": "2",
            "licenses": ["authorized 1", "authorized 2"],
        },
        {
            "name": "auth_one_unauth_one",
            "version": "1",
            "licenses": ["authorized 1", "unauthorized 1"],
        },
        {
            "name": "auth_one_or_unauth_one",
            "version": "2",
            "licenses": ["authorized 1 OR unauthorized 1"],
        },
        {
            "name": "unauth_one",
            "version": "2",
            "licenses": ["unauthorized 1"],
        },
        {
            "name": "whitelisted",
            "version": "1",
            "licenses": ["unauthorized 1"],
        },
        {
            "name": "whitelisted",
            "version": "2",
            "licenses": ["unauthorized 1"],
        },
        {
            "name": "auth_one_unknown",
            "version": "1",
            "licenses": ["authorized 1", "unknown"],
        },
        {
            "name": "unknown",
            "version": "3",
            "licenses": ["unknown"],
        },
    ]

def strategy_with_one_auth(license):
    return Strategy(
        authorized_licenses=[license.lower()],
        unauthorized_licenses=[],
        authorized_packages={},
    )

@pytest.mark.parametrize(
    ("strategy_params", "as_regex"),
    [
        (
            dict(
                authorized_licenses=["authorized 1", "authorized 2"],
                unauthorized_licenses=["unauthorized 1", "unauthorized 2"],
                authorized_packages={"whitelisted": "1"},
            ),
            False,
        ),
        (
            dict(
                authorized_licenses=[r"\bauthorized"],
                unauthorized_licenses=[r"\bunauthorized"],
                authorized_packages={"whitelisted": "1"},
            ),
            True,
        ),
    ],
)
@pytest.mark.parametrize(
    ("level", "reasons"),
    [
        (Level.STANDARD, [OK, OK, OK, OK, UNAUTH, OK, UNAUTH, OK, UNKNOWN]),
        (Level.CAUTIOUS, [OK, OK, UNAUTH, UNAUTH, UNAUTH, OK, UNAUTH, OK, UNKNOWN]),
        (Level.PARANOID, [OK, OK, UNAUTH, UNAUTH, UNAUTH, OK, UNAUTH, UNKNOWN, UNKNOWN]),
    ],
    ids=[level.name for level in Level],
)
def test_check_package(strategy_params, packages, level, reasons, as_regex):
    strategy = Strategy(**strategy_params)
    for package, reason in zip(packages, reasons):
        assert check_package(strategy, package, level, as_regex) is reason

@pytest.mark.parametrize(
    "license", [
        "GNU Library or Lesser General Public License (LGPL)",
        "GNU Lesser General Public License v2 or later (LGPLv2+)"
    ]
)
def test_check_package_respects_licences_with_a_lowercase_or(license):
    strategy = strategy_with_one_auth(license)
    package = {
        "name": "lgpl_example",
        "version": "2",
        "licenses": [license],
    }
    assert check_package(strategy, package, Level.STANDARD, False) is OK

def test_check_package_splits_licenses_with_SPDX_OR():
    # The SPDX standard allows packages to specific dual licenses with an OR operator.
    # See https://spdx.org/spdx-specification-21-web-version#h.jxpfx0ykyb60
    mit_strategy = strategy_with_one_auth("MIT")
    apache_strategy = strategy_with_one_auth("Apache-2.0")
    gpl_strategy = strategy_with_one_auth("GPL-2.0-or-later")
    package = {
        "name": "mit_example",
        "version": "2",
        "licenses": ["MIT OR Apache-2.0"],
    }
    assert check_package(mit_strategy, package, Level.STANDARD, False) is OK
    assert check_package(apache_strategy, package, Level.STANDARD, False) is OK
    assert check_package(gpl_strategy, package, Level.STANDARD, False) is UNKNOWN