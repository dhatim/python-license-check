## Python License Checker

Check python packages from requirement.txt and report issues.

## About

You can define a list of authorized licenses, authorized packages, unauthorized licenses.

The tool will check the requirement.txt files, check packages and their dependencies and return an error if some packages are not compliante against the startegy.

## How to use

python_pckg will read the request.txt in the same folder, and check packages agains strategy defined in license_list.py file.

````
$ python license_pkg.py
gathering licenses...23 packages and dependencies.
check forbidden packages based on licenses...none
check authorized packages based on licenses...19 packages.
check authorized packages...4 packages.
check unknown licenses...none
````

## Licensing

* See [LICENSE](LICENSE)

