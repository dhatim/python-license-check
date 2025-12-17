import importlib.metadata as ilm
from packaging.markers import Marker, default_environment
from packaging.requirements import Requirement

try:
    from pip._internal.network.session import PipSession
except ImportError:
    try:
        from pip._internal.download import PipSession
    except ImportError:
        from pip.download import PipSession

try:
    from pip._internal.req import parse_requirements as pip_parse_requirements
except ImportError:
    from pip.req import parse_requirements as pip_parse_requirements

try:
    from pip._internal.req.constructors import install_req_from_parsed_requirement
except ImportError:
    def install_req_from_parsed_requirement(r):
        return r


def parse_requirements(requirement_file):
    requirements = []
    for req in pip_parse_requirements(requirement_file, session=PipSession()):
        install_req = install_req_from_parsed_requirement(req)
        if install_req.markers is not None and not install_req.markers.evaluate():
            # req should not installed due to env markers
            continue
        elif install_req.editable:
            # skip editable req as they are failing in the resolve phase
            continue
        requirements.append(install_req.req)
    return requirements


def resolve(requirements, without_deps=False):
    for req in requirements:
        dist = ilm.distribution(req.name)
        yield dist
        if not without_deps and dist.requires is not None:
            requires = [Requirement(r) for r in dist.requires]
            requires = [r for r in requires if r.marker is None or r.marker.evaluate()]
            yield from resolve(requires)
