import argparse
import collections
import os.path

from liccheck.requirements import parse_requirements, resolve, resolve_without_deps

try:
    from configparser import ConfigParser, NoOptionError
except ImportError:
    from ConfigParser import ConfigParser, NoOptionError
import enum
import functools
import re
import textwrap
import sys
import semantic_version
import toml

try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError


class NoValidConfigurationInPyprojectToml(BaseException):
    pass


def from_pyproject_toml():
    try:
        pyproject_toml = toml.load("pyproject.toml")
        try:
            return pyproject_toml["tool"]["liccheck"]
        except KeyError:
            raise NoValidConfigurationInPyprojectToml
    except FileNotFoundError:
        raise NoValidConfigurationInPyprojectToml


class Strategy:
    def __init__(self, authorized_licenses, unauthorized_licenses, authorized_packages):
        self.AUTHORIZED_LICENSES = authorized_licenses
        self.UNAUTHORIZED_LICENSES = unauthorized_licenses
        self.AUTHORIZED_PACKAGES = authorized_packages

        self.AUTHORIZED_REGEX = (
            re.compile(r"(?!)")
            if not self.AUTHORIZED_LICENSES
            else re.compile(
                "|".join(
                    [
                        r"(?:{license})".format(license=license_str)
                        for license_str in self.AUTHORIZED_LICENSES
                    ]
                )
            )
        )

        self.UNAUTHORIZED_REGEX = (
            re.compile(r"(?!)")
            if not self.UNAUTHORIZED_LICENSES
            else re.compile(
                "|".join(
                    [
                        r"{license}".format(license=license_str)
                        for license_str in self.UNAUTHORIZED_LICENSES
                    ]
                )
            )
        )

    @classmethod
    def from_pyproject_toml(cls):
        liccheck_section = from_pyproject_toml()

        def elements_to_lower_str(lst):
            return [str(_).lower() for _ in lst]

        strategy = cls(
            authorized_licenses=elements_to_lower_str(
                liccheck_section.get("authorized_licenses", [])
            ),
            unauthorized_licenses=elements_to_lower_str(
                liccheck_section.get("unauthorized_licenses", [])
            ),
            authorized_packages=liccheck_section.get("authorized_packages", dict()),
        )
        return strategy

    @classmethod
    def from_config(cls, strategy_file):
        config = ConfigParser()
        # keep case of options
        config.optionxform = str
        config.read(strategy_file)

        def get_config_list(section, option):
            try:
                value = config.get(section, option)
            except NoOptionError:
                return []
            return [item for item in value.lower().split("\n") if item]

        authorized_packages = dict()
        if config.has_section("Authorized Packages"):
            for name, value in config.items("Authorized Packages"):
                authorized_packages[name] = value

        strategy = cls(
            authorized_licenses=get_config_list("Licenses", "authorized_licenses"),
            unauthorized_licenses=get_config_list("Licenses", "unauthorized_licenses"),
            authorized_packages=authorized_packages,
        )
        if config.has_section("Authorized Packages"):
            for name, value in config.items("Authorized Packages"):
                strategy.AUTHORIZED_PACKAGES[name] = value
        return strategy


class Level(enum.Enum):
    STANDARD = "STANDARD"
    CAUTIOUS = "CAUTIOUS"
    PARANOID = "PARANOID"

    @classmethod
    def starting(cls, value):
        """Return level starting with value (case-insensitive)"""
        for member in cls:
            if member.name.startswith(value.upper()):
                return member
        raise ValueError("No level starting with {!r}".format(value))

    def __str__(self):
        return self.name


class Reason(enum.Enum):
    OK = "OK"
    UNAUTHORIZED = "UNAUTHORIZED"
    UNKNOWN = "UNKNOWN"


def get_packages_info(requirement_file, no_deps=False):
    regex_license = re.compile(r"License: (?P<license>.*)?$", re.M)
    regex_classifier = re.compile(
        r"Classifier: License(?: :: OSI Approved)?(?: :: (?P<classifier>.*))?$", re.M
    )

    requirements = parse_requirements(requirement_file)

    def transform(dist):
        licenses = get_licenses_from_classifiers(dist) or get_license(dist) or []
        # Strip the useless "License" suffix and uniquify
        licenses = list(set([strip_license(l) for l in licenses]))
        # Removing Trailing windows generated \r
        licenses = list(set([strip_license_for_windows(l) for l in licenses]))

        return {
            "name": dist.project_name,
            "version": dist.version,
            "location": dist.location,
            "dependencies": [dependency.project_name for dependency in dist.requires()],
            "licenses": licenses,
        }

    def get_license(dist):
        if dist.has_metadata(dist.PKG_INFO):
            metadata = dist.get_metadata(dist.PKG_INFO)
            match = regex_license.search(metadata)
            if match:
                license = match.group("license")
                if license != "UNKNOWN":  # Value when license not specified.
                    return [license]

        return []

    def get_licenses_from_classifiers(dist):
        if dist.has_metadata(dist.PKG_INFO):
            metadata = dist.get_metadata(dist.PKG_INFO)

            # match might be found, but None if using the classifier:
            # License :: OSI Approved
            return [m for m in regex_classifier.findall(metadata) if m]

        return []

    def strip_license_for_windows(license):
        if license.endswith("\r"):
            return license[:-1]
        return license

    def strip_license(license):
        if license.lower().endswith(" license"):
            return license[: -len(" license")]
        return license

    resolve_func = resolve_without_deps if no_deps else resolve
    packages = [transform(dist) for dist in resolve_func(requirements)]
    # keep only unique values as there are maybe some duplicates
    unique = []
    [unique.append(item) for item in packages if item not in unique]

    return sorted(unique, key=(lambda item: item["name"].lower()))


def check_package(strategy, pkg, level=Level.STANDARD, as_regex=False):
    whitelisted = pkg["name"] in strategy.AUTHORIZED_PACKAGES and (
        semantic_version.SimpleSpec(strategy.AUTHORIZED_PACKAGES[pkg["name"]]).match(
            semantic_version.Version.coerce(pkg["version"])
        )
        or (level == Level.STANDARD and strategy.AUTHORIZED_PACKAGES[pkg["name"]] == "")
    )
    if whitelisted:
        return Reason.OK

    def check_one(
        license_str: str, license_rule: str = "AUTHORIZED", as_regex: bool = True
    ):
        if as_regex:
            license_regex = getattr(strategy, f"{license_rule}_REGEX")
            return license_regex.search(license_str) is not None
        else:
            license_list = getattr(strategy, f"{license_rule}_LICENSES")
            return license_str in license_list

    at_least_one_unauthorized = False
    count_authorized = 0
    for license in pkg["licenses"]:
        lower = license.lower()
        if check_one(
            lower,
            license_rule="UNAUTHORIZED",
            as_regex=as_regex,
        ):
            at_least_one_unauthorized = True
        if check_one(
            lower,
            license_rule="AUTHORIZED",
            as_regex=as_regex,
        ):
            count_authorized += 1

    if (
        (count_authorized and level is Level.STANDARD)
        or (
            count_authorized
            and not at_least_one_unauthorized
            and level is Level.CAUTIOUS
        )
        or (
            count_authorized
            and count_authorized == len(pkg["licenses"])
            and level is Level.PARANOID
        )
    ):
        return Reason.OK

    # if not OK and at least one unauthorized
    if at_least_one_unauthorized:
        return Reason.UNAUTHORIZED

    return Reason.UNKNOWN


def find_parents(package, all, seen):
    if package in seen:
        return [package]
    seen.add(package)
    parents = [p["name"] for p in all if package in p["dependencies"]]
    if len(parents) == 0:
        return [package]
    dependency_trees = []
    for parent in parents:
        for dependencies in find_parents(parent, all, seen):
            dependency_trees.append(package + " << " + dependencies)
    return dependency_trees


def write_package(package, all, no_deps=False):
    licenses = sorted(package["licenses"]) or "UNKNOWN"
    print("    {} ({}): {}".format(package["name"], package["version"], licenses))
    if not no_deps:
        write_deps(package, all)


def write_deps(package, all):
    dependency_branches = find_parents(package["name"], all, set())
    print("      dependenc{}:".format("y" if len(dependency_branches) <= 1 else "ies"))
    for dependency_branch in dependency_branches:
        print("          {}".format(dependency_branch))


def write_packages(packages, all, no_deps=False):
    for package in packages:
        write_package(package, all, no_deps)


def group_by(items, key):
    res = collections.defaultdict(list)
    for item in items:
        res[key(item)].append(item)

    return res


def process(
    requirement_file,
    strategy,
    level=Level.STANDARD,
    reporting_file=None,
    no_deps=False,
    as_regex=False,
):
    print("gathering licenses...")
    pkg_info = get_packages_info(requirement_file, no_deps)
    all = list(pkg_info)
    deps_mention = "" if no_deps else " and dependencies"
    print(
        "{} package{}{}.".format(
            len(pkg_info), "" if len(pkg_info) <= 1 else "s", deps_mention
        )
    )
    groups = group_by(
        pkg_info,
        functools.partial(check_package, strategy, level=level, as_regex=as_regex),
    )
    ret = 0

    if reporting_file:
        packages = []
        for r, ps in groups.items():
            for p in ps:
                packages.append(
                    {
                        "name": p["name"],
                        "version": p["version"],
                        "license": (p["licenses"] or ["UNKNOWN"])[0],
                        "status": r,
                    }
                )
        with open(reporting_file, "w") as f:
            for p in sorted(packages, key=lambda i: i["name"]):
                f.write(
                    "{} {} {} {}\n".format(
                        p["name"], p["version"], p["license"], p["status"].value
                    )
                )

    def format(l):
        return "{} package{}.".format(len(l), "" if len(l) <= 1 else "s")

    if groups[Reason.OK]:
        print("check authorized packages...")
        print(format(groups[Reason.OK]))

    if groups[Reason.UNAUTHORIZED]:
        print("check unauthorized packages...")
        print(format(groups[Reason.UNAUTHORIZED]))
        write_packages(groups[Reason.UNAUTHORIZED], all, no_deps)
        ret = -1

    if groups[Reason.UNKNOWN]:
        print("check unknown packages...")
        print(format(groups[Reason.UNKNOWN]))
        write_packages(groups[Reason.UNKNOWN], all, no_deps)
        ret = -1

    return ret


def read_strategy(strategy_file=None):
    try:
        return Strategy.from_pyproject_toml()
    except NoValidConfigurationInPyprojectToml:
        pass
    if not os.path.isfile(strategy_file):
        print(
            "Need to either configure pyproject.toml or provide an existing strategy file"
        )
        sys.exit(1)
    return Strategy.from_config(strategy_file=strategy_file)


def parse_args(args):
    parser = argparse.ArgumentParser(
        description="Check license of packages and their dependencies.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "-s",
        "--sfile",
        dest="strategy_ini_file",
        help="strategy ini file",
        default="./liccheck.ini",
    )
    parser.add_argument(
        "-l",
        "--level",
        choices=Level,
        default=Level.STANDARD,
        type=Level.starting,
        help=textwrap.dedent(
            """\
            Level for testing compliance of packages, where:
              Standard - At least one authorized license (default);
              Cautious - Per standard but no unauthorized licenses;
              Paranoid - All licenses must by authorized.
        """
        ),
    )
    parser.add_argument(
        "-r",
        "--rfile",
        dest="requirement_txt_file",
        help="path/to/requirement.txt file",
        nargs="?",
        default="./requirements.txt",
    )
    parser.add_argument(
        "-R",
        "--reporting",
        dest="reporting_txt_file",
        help="path/to/reporting.txt file",
        nargs="?",
        default=None,
    )
    parser.add_argument(
        "--no-deps",
        dest="no_deps",
        help="don't check dependencies",
        action="store_true",
    )

    return parser.parse_args(args)


def merge_args(args):
    try:
        config = from_pyproject_toml()
    except NoValidConfigurationInPyprojectToml:
        return args
    return {
        "strategy_ini_file": config.get("strategy_ini_file", args["strategy_ini_file"]),
        "requirement_txt_file": config.get(
            "requirement_txt_file", args["requirement_txt_file"]
        ),
        "level": Level.starting(config.get("level", args["level"].value)),
        "reporting_txt_file": config.get(
            "reporting_txt_file", args["reporting_txt_file"]
        ),
        "no_deps": config.get("no_deps", args["no_deps"]),
        "dependencies": config.get("dependencies", args["dependencies"]),
        "optional_dependencies": config.get(
            "optional_dependencies", args["optional_dependencies"]
        ),
        "as_regex": config.get("as_regex", args["as_regex"]),
    }


def generate_requirements_file_from_pyproject(include_dependencies, extra_dependencies):
    import tempfile

    directory = tempfile.mkdtemp(prefix="liccheck_")
    requirements_txt_file = directory + "/requirements.txt"
    with open(requirements_txt_file, "w") as f:
        project = toml.load("pyproject.toml").get("project", {})
        dependencies = project.get("dependencies", []) if include_dependencies else []
        optional_dependencies = (
            project.get("optional-dependencies", {}) if extra_dependencies else {}
        )
        for extra_dependency in extra_dependencies:
            if extra_dependency in optional_dependencies:
                dependencies += optional_dependencies[extra_dependency]
        f.write(os.linesep.join(dependencies))
    return requirements_txt_file


def run(args):
    args = merge_args(
        {
            "strategy_ini_file": args.strategy_ini_file,
            "requirement_txt_file": args.requirement_txt_file,
            "level": args.level,
            "reporting_txt_file": args.reporting_txt_file,
            "no_deps": args.no_deps,
            "dependencies": False,
            "optional_dependencies": [],
            "as_regex": False,
        }
    )
    strategy = read_strategy(args["strategy_ini_file"])
    requirements_file_generated = False
    if args["dependencies"] is True or len(args["optional_dependencies"]) > 0:
        args["requirement_txt_file"] = generate_requirements_file_from_pyproject(
            args["dependencies"], args["optional_dependencies"]
        )
        requirements_file_generated = True
    try:
        return process(
            args["requirement_txt_file"],
            strategy,
            args["level"],
            args["reporting_txt_file"],
            args["no_deps"],
            args["as_regex"],
        )
    finally:
        if requirements_file_generated:
            import pathlib
            import shutil

            shutil.rmtree(
                pathlib.Path(args["requirement_txt_file"]).parent, ignore_errors=True
            )


def main():
    args = parse_args(sys.argv[1:])
    sys.exit(run(args))


if __name__ == "__main__":
    main()
