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
        (Level.STANDARD, [OK, OK, OK, UNAUTH, OK, UNAUTH, OK, UNKNOWN]),
        (Level.CAUTIOUS, [OK, OK, UNAUTH, UNAUTH, OK, UNAUTH, OK, UNKNOWN]),
        (Level.PARANOID, [OK, OK, UNAUTH, UNAUTH, OK, UNAUTH, UNKNOWN, UNKNOWN]),
    ],
    ids=[level.name for level in Level],
)
def test_check_package(strategy_params, packages, level, reasons, as_regex):
    strategy = Strategy(**strategy_params)
    for package, reason in zip(packages, reasons):
        assert check_package(strategy, package, level, as_regex) is reason
