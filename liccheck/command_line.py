import argparse
import configparser
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


def get_packages_info(requirement_file):
    regex_license = re.compile('License: (?P<license>.+)\n')
    regex_classifier = re.compile('Classifier: License :: OSI Approved :: (?P<classifier>.+)\n')

    requirements = [pkg_resources.Requirement.parse(str(req.req)) for req
                    in parse_requirements(requirement_file, session=PipSession()) if req.req is not None]

    transform = lambda dist: {
        'name': dist.project_name,
        'version': dist.version,
        'location': dist.location,
        'dependencies': list(
            map(lambda dependency: dependency.project_name,
                dist.requires())),
        'license': get_license(dist),
        'license_OSI_classifiers': get_license_OSI_classifiers(dist)
    }

    def get_license(dist):
        if dist.has_metadata(dist.PKG_INFO):
            metadata = dist.get_metadata(dist.PKG_INFO)
            return regex_license.search(metadata).group('license')

        return 'UNKNOWN'

    def get_license_OSI_classifiers(dist):
        if dist.has_metadata(dist.PKG_INFO):
            metadata = dist.get_metadata(dist.PKG_INFO)
            return regex_classifier.findall(metadata)

        return None

    packages = [transform(dist) for dist in pkg_resources.working_set.resolve(requirements)]
    # keep only unique values as there is maybe some duplicates
    unique = []
    [unique.append(item) for item in packages if item not in unique]

    return sorted(unique, key=(lambda item: item['name'].lower()))


def partition(list_, condition):
    trues, falses = [], []
    for x in list_:
        if condition(x):
            trues.append(x)
        else:
            falses.append(x)
    return trues, falses


def get_forbidden_packages_based_on_licenses(pkg_info, strategy):
    return partition(pkg_info, lambda pkg: pkg['license'].lower() in strategy.UNAUTHORIZED_LICENSES)


def get_authorized_packages_based_on_licenses(pkg_info, strategy):
    return partition(pkg_info, lambda pkg: pkg['license'].lower() in strategy.AUTHORIZED_LICENSES)


def get_authorized_packages(pkg_info, strategy):
    return partition(pkg_info, lambda pkg: is_authorized_package(pkg, strategy))


def is_authorized_package(pkg, strategy):
    license_classifiers = pkg['license_OSI_classifiers']
    if license_classifiers is not None:
        at_least_one_unauthorized = False
        for license in license_classifiers:
            if license.lower() in strategy.UNAUTHORIZED_LICENSES:
                at_least_one_unauthorized = True
            if license.lower() in strategy.AUTHORIZED_LICENSES:
                return True
        # if no license authorized but at least one unauthorized
        if at_least_one_unauthorized:
            return False
    # if not found, lookup in AUTHORIZED_PACKAGES list
    return (pkg['name'] in strategy.AUTHORIZED_PACKAGES) \
           and (strategy.AUTHORIZED_PACKAGES[pkg['name']] == pkg['version'])


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
    print('    {} ({}) : {} {} \n'.format(package['name'], package['version'], package['license'],
                                          package['license_OSI_classifiers']))
    print('      dependenc{}:\n'.format('y' if len(dependency_branchs)<1 else 'ies'))
    for dependency_branch in dependency_branchs:
        print('          {}\n'.format(dependency_branch))


def write_packages(packages, all):
    for package in packages:
        write_package(package, all)


def process(requirement_file, strategy):
    print('gathering licenses...')
    pkg_info = get_packages_info(requirement_file)
    all = list(pkg_info)
    print(str(len(pkg_info)) + ' packages and dependencies.\n')

    print('check forbidden packages based on licenses...')
    forbidden, pkg_info = get_forbidden_packages_based_on_licenses(pkg_info, strategy)
    if len(forbidden) > 0:
        print(str(len(forbidden)) + ' forbidden packages :\n')
        write_packages(forbidden, all)
    else:
        print('none')
    print('\n')

    print('check authorized packages based on licenses...')
    authorized, pkg_info = get_authorized_packages_based_on_licenses(pkg_info, strategy)
    print(str(len(authorized)) + ' packages.\n')

    print('check authorized packages...')
    authorized, unknown = get_authorized_packages(pkg_info, strategy)
    print(str(len(authorized)) + ' packages.\n')

    print('check unknown licenses...')
    if len(unknown) > 0:
        print(str(len(unknown)) + ' unknown packages :\n')
        write_packages(unknown, all)
    else:
        print('none')
    print('\n')

    if (len(forbidden) > 0) or (len(unknown) > 0):
        return -1
    return 0


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
