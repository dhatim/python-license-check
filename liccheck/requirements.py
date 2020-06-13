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


def resolve_without_deps(requirements):
    working_set = pkg_resources.working_set
    for req in requirements:
        env = pkg_resources.Environment(working_set.entries)
        dist = env.best_match(
            req=req,
            working_set=working_set,
            installer=None,
            replace_conflicting=False,
        )
        yield dist


def resolve(requirements):
    for dist in pkg_resources.working_set.resolve(requirements):
        yield dist
