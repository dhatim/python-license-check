import argparse
import collections
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

import pkg_resources

try:
    from pip._internal.network.session import PipSession
except ImportError:
    try:
        from pip._internal.download import PipSession
    except ImportError:
        from pip.download import PipSession

try:
    from pip._internal.req import parse_requirements
except ImportError:
    from pip.req import parse_requirements

try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError


class NoValidConfigurationInPyprojectToml(BaseException):
    pass


class Strategy:
    def __init__(self, authorized_licenses, unauthorized_licenses, authorized_packages):
        self.AUTHORIZED_LICENSES = authorized_licenses
        self.UNAUTHORIZED_LICENSES = unauthorized_licenses
        self.AUTHORIZED_PACKAGES = authorized_packages

    @classmethod
    def from_pyproject_toml(cls):
        try:
            pyproject_toml = toml.load("pyproject.toml")
        except FileNotFoundError:
            raise NoValidConfigurationInPyprojectToml

        try:
            liccheck_section = pyproject_toml["tool"]["liccheck"]
        except KeyError:
            raise NoValidConfigurationInPyprojectToml

        def elements_to_lower_str(lst):
            return [str(_).lower() for _ in lst]

        strategy = cls(
            authorized_licenses=elements_to_lower_str(liccheck_section.get("authorized_licenses", [])),
            unauthorized_licenses=elements_to_lower_str(liccheck_section.get("unauthorized_licenses", [])),
            authorized_packages=liccheck_section.get("authorized_packages", dict())
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
            return [item for item in value.lower().split('\n') if item]

        authorized_packages = dict()
        if config.has_section('Authorized Packages'):
            for name, value in config.items('Authorized Packages'):
                authorized_packages[name] = value

        strategy = cls(
            authorized_licenses=get_config_list('Licenses', 'authorized_licenses'),
            unauthorized_licenses=get_config_list('Licenses', 'unauthorized_licenses'),
            authorized_packages=authorized_packages,
        )
        if config.has_section('Authorized Packages'):
            for name, value in config.items('Authorized Packages'):
                strategy.AUTHORIZED_PACKAGES[name] = value
        return strategy


class Level(enum.Enum):
    STANDARD = 'STANDARD'
    CAUTIOUS = 'CAUTIOUS'
    PARANOID = 'PARANOID'

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
    OK = 'OK'
    UNAUTHORIZED = 'UNAUTHORIZED'
    UNKNOWN = 'UNKNOWN'


def get_packages_info(requirement_file):
    regex_license = re.compile(r'License: (?P<license>[^\r\n]+)\r?\n')
    regex_classifier = re.compile(r'Classifier: License :: OSI Approved :: (?P<classifier>[^\r\n]+)\r?\n')

    requirements = []
    for req in parse_requirements(requirement_file, session=PipSession()):
        if req.markers:
            if not pkg_resources.evaluate_marker(str(req.markers)):
                continue
        requirements.append(pkg_resources.Requirement.parse(str(req.req)))

    def transform(dist):
        licenses = get_license(dist) + get_license_OSI_classifiers(dist)
        # Strip the useless "License" suffix and uniquify
        licenses = list(set([strip_license(l) for l in licenses]))
        return {
            'name': dist.project_name,
            'version': dist.version,
            'location': dist.location,
            'dependencies': [dependency.project_name for dependency in dist.requires()],
            'licenses': licenses,
        }

    def get_license(dist):
        if dist.has_metadata(dist.PKG_INFO):
            metadata = dist.get_metadata(dist.PKG_INFO)
            match = regex_license.search(metadata)
            if match:
                license = match.group('license')
                if license != "UNKNOWN":  # Value when license not specified.
                    return [license]

        return []

    def get_license_OSI_classifiers(dist):
        if dist.has_metadata(dist.PKG_INFO):
            metadata = dist.get_metadata(dist.PKG_INFO)
            return regex_classifier.findall(metadata)

        return []

    def strip_license(license):
        if license.lower().endswith(" license"):
            return license[:-len(" license")]
        return license

    packages = [transform(dist) for dist in pkg_resources.working_set.resolve(requirements)]
    # keep only unique values as there are maybe some duplicates
    unique = []
    [unique.append(item) for item in packages if item not in unique]

    return sorted(unique, key=(lambda item: item['name'].lower()))


def check_package(strategy, pkg, level=Level.STANDARD):
    whitelisted = (
            pkg['name'] in strategy.AUTHORIZED_PACKAGES and (
                semantic_version.Spec(strategy.AUTHORIZED_PACKAGES[pkg['name']]).match(semantic_version.Version.coerce(pkg['version']))
                or (level == Level.STANDARD and strategy.AUTHORIZED_PACKAGES[pkg['name']] == '')
            )
    )
    if whitelisted:
        return Reason.OK

    at_least_one_unauthorized = False
    count_authorized = 0
    for license in pkg['licenses']:
        lower = license.lower()
        if lower in strategy.UNAUTHORIZED_LICENSES:
            at_least_one_unauthorized = True
        if lower in strategy.AUTHORIZED_LICENSES:
            count_authorized += 1

    if (count_authorized and level is Level.STANDARD) \
            or (count_authorized and not at_least_one_unauthorized
                and level is Level.CAUTIOUS) \
            or (count_authorized and count_authorized == len(pkg['licenses'])
                and level is Level.PARANOID):
        return Reason.OK

    # if not OK and at least one unauthorized
    if at_least_one_unauthorized:
        return Reason.UNAUTHORIZED

    return Reason.UNKNOWN


def find_parents(package, all, seen):
    if package in seen:
        return [package]
    seen.add(package)
    parents = [p['name'] for p in all if package in p['dependencies']]
    if len(parents) == 0:
        return [package]
    dependency_trees = []
    for parent in parents:
        for dependencies in find_parents(parent, all, seen):
            dependency_trees.append(package + " << " + dependencies)
    return dependency_trees


def write_package(package, all):
    dependency_branches = find_parents(package['name'], all, set())
    licenses = package['licenses'] or 'UNKNOWN'
    print('    {} ({}): {}'.format(package['name'], package['version'], licenses))
    print('      dependenc{}:'.format('y' if len(dependency_branches) <= 1 else 'ies'))
    for dependency_branch in dependency_branches:
        print('          {}'.format(dependency_branch))


def write_packages(packages, all):
    for package in packages:
        write_package(package, all)


def group_by(items, key):
    res = collections.defaultdict(list)
    for item in items:
        res[key(item)].append(item)

    return res


def process(requirement_file, strategy, level=Level.STANDARD):
    print('gathering licenses...')
    pkg_info = get_packages_info(requirement_file)
    all = list(pkg_info)
    print('{} package{} and dependencies.'.format(len(pkg_info), '' if len(pkg_info) <= 1 else 's'))
    groups = group_by(
        pkg_info, functools.partial(check_package, strategy, level=level))
    ret = 0

    def format(l):
        return '{} package{}.'.format(len(l), '' if len(l) <= 1 else 's')

    if groups[Reason.OK]:
        print('check authorized packages...')
        print(format(groups[Reason.OK]))

    if groups[Reason.UNAUTHORIZED]:
        print('check unauthorized packages...')
        print(format(groups[Reason.UNAUTHORIZED]))
        write_packages(groups[Reason.UNAUTHORIZED], all)
        ret = -1

    if groups[Reason.UNKNOWN]:
        print('check unknown packages...')
        print(format(groups[Reason.UNKNOWN]))
        write_packages(groups[Reason.UNKNOWN], all)
        ret = -1

    return ret


def read_strategy(strategy_file=None):
    try:
        return Strategy.from_pyproject_toml()
    except NoValidConfigurationInPyprojectToml:
        pass
    if strategy_file is None:
        print("Need to either configure pyproject.toml or provide a strategy file")
        sys.exit(1)
    return Strategy.from_config(strategy_file=strategy_file)


def parse_args(args):
    parser = argparse.ArgumentParser(
        description='Check license of packages and there dependencies.',
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument(
        '-s', '--sfile', dest='strategy_ini_file', help='strategy ini file',
        required=False)
    parser.add_argument(
        '-l', '--level', choices=Level,
        default=Level.STANDARD, type=Level.starting,
        help=textwrap.dedent("""\
            Level for testing compliance of packages, where:
              Standard - At least one authorized license (default);
              Cautious - Per standard but no unauthorized licenses;
              Paranoid - All licenses must by authorized.
        """))
    parser.add_argument(
        '-r', '--rfile', dest='requirement_txt_file',
        help='path/to/requirement.txt file', nargs='?',
        default='./requirements.txt')
    return parser.parse_args(args)


def run(args):
    strategy = read_strategy(args.strategy_ini_file)
    return process(args.requirement_txt_file, strategy, args.level)


def main():
    args = parse_args(sys.argv[1:])
    sys.exit(run(args))


if __name__ == "__main__":
    main()
