from importlib.metadata import PackageNotFoundError, distribution

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

from pip._internal.network.session import PipSession
from pip._internal.req import parse_requirements as pip_parse_requirements
from pip._internal.req.constructors import install_req_from_parsed_requirement


def parse_requirements(requirement_file):
    requirements = []
    for req in pip_parse_requirements(requirement_file, session=PipSession()):
        install_req = install_req_from_parsed_requirement(req)
        if install_req.markers and not install_req.markers.evaluate():
            # req should not installed due to env markers
            continue
        elif install_req.editable:
            # skip editable req as they are failing in the resolve phase
            continue
        requirements.append(Requirement(str(install_req.req)))
    return requirements


def _find_distribution(req):
    try:
        dist = distribution(req.name)
    except PackageNotFoundError:
        return None
    if req.specifier and not req.specifier.contains(dist.version, prereleases=True):
        return None
    return dist


def resolve_without_deps(requirements):
    for req in requirements:
        yield _find_distribution(req)


def _resolve_one(req, seen):
    dist = _find_distribution(req)
    if dist is None:
        return
    key = canonicalize_name(dist.metadata["Name"])
    if key in seen:
        return
    seen.add(key)
    yield dist
    for dep_str in dist.requires or []:
        dep_req = Requirement(dep_str)
        if dep_req.marker and not dep_req.marker.evaluate():
            continue
        yield from _resolve_one(dep_req, seen)


def resolve(requirements):
    seen = set()
    for req in requirements:
        yield from _resolve_one(req, seen)
