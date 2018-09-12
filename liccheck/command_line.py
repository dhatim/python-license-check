import argparse
import collections
try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import ConfigParser
import enum
import functools
import re
import textwrap
import sys

import pkg_resources

try:
    from pip._internal.download import PipSession
except ImportError:
    from pip.download import PipSession

try:
    from pip._internal.req import parse_requirements
except ImportError:
    from pip.req import parse_requirements


class Strategy:
    def __init__(self):
        self.AUTHORIZED_LICENSES = []
        self.UNAUTHORIZED_LICENSES = []
        self.AUTHORIZED_PACKAGES = []


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

    requirements = [pkg_resources.Requirement.parse(str(req.req)) for req
                    in parse_requirements(requirement_file, session=PipSession()) if req.req is not None]

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
            license = regex_license.search(metadata).group('license')
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
            pkg['name'] in strategy.AUTHORIZED_PACKAGES and
            strategy.AUTHORIZED_PACKAGES[pkg['name']] == pkg['version']
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


def find_parents(package, all):
    parents = [p['name'] for p in all if package in p['dependencies']]
    if len(parents) == 0:
        return [package]
    dependency_trees = []
    for parent in parents:
        for dependencies in find_parents(parent, all):
            dependency_trees.append(package + " << " + dependencies)
    return dependency_trees


def write_package(package, all):
    dependency_branches = find_parents(package['name'], all)
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


def read_strategy(strategy_file):
    config = ConfigParser()
    config.read(strategy_file)
    strategy = Strategy()
    strategy.AUTHORIZED_LICENSES = list(filter(None, config.get('Licenses', 'authorized_licenses').lower().split('\n')))
    strategy.UNAUTHORIZED_LICENSES = list(filter(None, config.get('Licenses', 'unauthorized_licenses').lower().split('\n')))
    strategy.AUTHORIZED_PACKAGES = dict()
    for name, value in config.items('Authorized Packages'):
        strategy.AUTHORIZED_PACKAGES[name] = value
    return strategy


def parse_args(args):
    parser = argparse.ArgumentParser(
        description='Check license of packages and there dependencies.',
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument(
        '-s', '--sfile', dest='strategy_ini_file', help='strategy ini file',
        required=True)
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
