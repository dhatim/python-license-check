import pkg_resources

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
        if install_req.markers and not pkg_resources.evaluate_marker(str(install_req.markers)):
            continue
        requirements.append(pkg_resources.Requirement.parse(str(install_req.req)))
    return requirements
