import argparse
import configparser
import collections
import functools
import enum
import re
import sys

import pkg_resources
from pip._vendor import pkg_resources
from pip.download import PipSession
from pip.req import parse_requirements


class Strategy:
    AUTHORIZED_LICENSES = []
    UNAUTHORIZED_LICENSES = []
    AUTHORIZED_PACKAGES = []


class Reason(enum.Enum):
    OK = 'OK'
    UNAUTHORIZED = 'UNAUTHORIZED'
    UNKNOWN = 'UNKNOWN'


def get_packages_info(requirement_file):
    regex_license = re.compile('License: (?P<license>.+)\n')
    regex_classifier = re.compile('Classifier: License :: OSI Approved :: (?P<classifier>.+)\n')

    requirements = [pkg_resources.Requirement.parse(str(req.req)) for req
                    in parse_requirements(requirement_file, session=PipSession()) if req.req is not None]

    def transform(dist):
        licenses = get_license(dist) + get_license_OSI_classifiers(dist)
        return {
            'name': dist.project_name,
            'version': dist.version,
            'location': dist.location,
            'dependencies': list(
                map(lambda dependency: dependency.project_name,
                    dist.requires())),
            'licenses': licenses,
        }

    def get_license(dist):
        if dist.has_metadata(dist.PKG_INFO):
            metadata = dist.get_metadata(dist.PKG_INFO)
            return [regex_license.search(metadata).group('license')]

        return []

    def get_license_OSI_classifiers(dist):
        if dist.has_metadata(dist.PKG_INFO):
            metadata = dist.get_metadata(dist.PKG_INFO)
            return regex_classifier.findall(metadata)

        return []

    packages = [transform(dist) for dist in pkg_resources.working_set.resolve(requirements)]
    # keep only unique values as there is maybe some duplicates
    unique = []
    [unique.append(item) for item in packages if item not in unique]

    return sorted(unique, key=(lambda item: item['name'].lower()))


def check_package(strategy, pkg):
    whitelisted = (
        pkg['name'] in strategy.AUTHORIZED_PACKAGES and
        strategy.AUTHORIZED_PACKAGES[pkg['name']] == pkg['version']
    )
    if whitelisted:
        return Reason.OK

    at_least_one_unauthorized = False
    for license in pkg['licenses']:
        lower = license.lower()
        if lower in strategy.UNAUTHORIZED_LICENSES:
            at_least_one_unauthorized = True
        if lower in strategy.AUTHORIZED_LICENSES:
            return Reason.OK

    # if no license authorized but at least one unauthorized
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
    dependency_branchs = find_parents(package['name'], all)
    licenses = package['licenses'] or 'UNKNOWN'
    print('    {} ({}) : {} \n'.format(package['name'], package['version'], licenses))
    print('      dependenc{}:\n'.format('y' if len(dependency_branchs)<1 else 'ies'))
    for dependency_branch in dependency_branchs:
        print('          {}\n'.format(dependency_branch))


def write_packages(packages, all):
    for package in packages:
        write_package(package, all)

def group_by(items, key):
    res = collections.defaultdict(list)
    for item in items:
        res[key(item)].append(item)

    return res


def process(requirement_file, strategy):
    print('gathering licenses...')
    pkg_info = get_packages_info(requirement_file)
    all = list(pkg_info)
    print(str(len(pkg_info)) + ' packages and dependencies.\n')
    groups = group_by(pkg_info, functools.partial(check_package, strategy))
    ret = 0

    def format(l):
        return '{} packages.\n'.format(len(l))

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
    config = configparser.ConfigParser()
    config.read(strategy_file)
    strategy = Strategy()
    strategy.AUTHORIZED_LICENSES = list(filter(None, config['Licenses']['authorized_licenses'].lower().split("\n")))
    strategy.UNAUTHORIZED_LICENSES = list(filter(None, config['Licenses']['unauthorized_licenses'].lower().split("\n")))
    strategy.AUTHORIZED_PACKAGES = config['Authorized Packages']
    return strategy


def main():
    parser = argparse.ArgumentParser(description='Check license of packages and there dependencies.')
    parser.add_argument('-s', '--sfile', dest='strategy_ini_file', help='strategy ini file', required=True)
    parser.add_argument('-r', '--rfile', dest='requirement_txt_file', help='path/to/requirement.txt file', nargs='?',
                        default='./requirements.txt')
    args = parser.parse_args()

    strategy = read_strategy(args.strategy_ini_file)
    sys.exit(process(args.requirement_txt_file, strategy))


if __name__ == "__main__":
    main()
