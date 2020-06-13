from liccheck.command_line import write_packages


def test_write_packages(capsys):
    packages = [
        {'name': 'functools32', 'version': '3.2.3-2', 'location': 'path',
         'dependencies': [], 'licenses': ['PSF license']},
        {'name': 'jsonschema', 'version': '2.6.0', 'location': 'path',
         'dependencies': ['functools32'], 'licenses': ['Apache2']},
        {'name': 'os-faults', 'version': '0.2.0', 'location': 'path',
         'dependencies': ['jsonschema'], 'licenses': ['Apache2']}]

    write_packages([packages[0]], packages)

    captured = capsys.readouterr().out
    expected = '''    functools32 (3.2.3-2): ['PSF license']
      dependency:
          functools32 << jsonschema << os-faults
'''
    assert captured == expected


def test_write_packages_with_cyclic_dependencies(capsys):
    packages = [
        {'name': 'testtools', 'version': '2.3.0', 'location': 'path',
         'dependencies': ['fixtures'], 'licenses': ['Apache2']},
        {'name': 'fixtures', 'version': '3.0.0', 'location': 'path',
         'dependencies': ['testtools'], 'licenses': ['Apache2']}]

    write_packages(packages, packages)

    captured = capsys.readouterr().out
    expected = '''    testtools (2.3.0): ['Apache2']
      dependency:
          testtools << fixtures << testtools
    fixtures (3.0.0): ['Apache2']
      dependency:
          fixtures << testtools << fixtures
'''
    assert captured == expected


def test_write_packages_without_deps(capsys):
    packages = [
        {'name': 'functools32', 'version': '3.2.3-2', 'location': 'path',
         'dependencies': [], 'licenses': ['PSF license']},
        {'name': 'jsonschema', 'version': '2.6.0', 'location': 'path',
         'dependencies': ['functools32'], 'licenses': ['Apache2']},
        {'name': 'os-faults', 'version': '0.2.0', 'location': 'path',
         'dependencies': ['jsonschema'], 'licenses': ['Apache2']}]

    write_packages([packages[0]], packages, no_deps=True)

    captured = capsys.readouterr().out
    expected = "    functools32 (3.2.3-2): ['PSF license']\n"
    assert captured == expected
