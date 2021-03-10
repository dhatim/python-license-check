.. image:: https://badge.fury.io/py/liccheck.svg
    :target: https://badge.fury.io/py/liccheck
.. image:: https://github.com/dhatim/python-license-check/workflows/build/badge.svg
    :target: https://github.com/dhatim/python-license-check/actions
.. image:: https://codecov.io/gh/dhatim/python-license-check/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/dhatim/python-license-check

Python License Checker
======================

Check python packages listed in a ``requirements.txt`` file and report license issues.

About
=====

You can define a list of authorized licenses, unauthorized licenses and authorized packages.

The tool will check the ``requirements.txt`` file, check packages and their
dependencies and return an error if some packages are not compliant
against the given strategy.

The tool has 3 levels of checks to select from:

Standard (default):
    A package is considered as compliant when at least one of its licenses is
    in the authorized license list, or if the package is in the list of
    authorized packages.

Cautious:
    Same as *Standard*, but a package is **not** considered compliant when one
    or more of its licenses is in the unauthorized license list, even if it
    also has a license in the authorized license list. A package is still
    compliant if present in the authorized packages list.

Paranoid:
    All licenses listed for a package must be in the authorised license list
    for the package to be considered compliant. A package is still
    compliant if present in the authorized packages list.

How to install
==============

::

	$ pip install liccheck


How to use
==========

``liccheck`` will read the ``requirements.txt`` and verify compliance of packages against a strategy defined in the ``ini`` file.
If the requirements file is not specified on the command line, it will search for ``requirements.txt`` in the current folder.
You have to setup an ``ini`` file with an authorized license list, unauthorized license list and authorized package list. The packages from your ``requirements.txt`` need to all be installed in the same python environment/virtualenv as ``liccheck``.
If the ``ini`` file is not specified on the command line, it will search for ``liccheck.ini`` in the current folder.

Here is an example of a ``liccheck.ini`` file:
::

	# Authorized and unauthorized licenses in LOWER CASE
	[Licenses]
	authorized_licenses:
		bsd
		new bsd
		bsd license
		new bsd license
		simplified bsd
		apache
		apache 2.0
		apache software license
		gnu lgpl
		lgpl with exceptions or zpl
		isc license
		isc license (iscl)
		mit
		mit license
		python software foundation license
		zpl 2.1

	unauthorized_licenses:
		gpl v3

	[Authorized Packages]
	# Python software license (see http://zesty.ca/python/uuid.README.txt)
	uuid: 1.30

Note: versions of authorized packages can be defined using `PEP-0440 version specifiers <https://www.python.org/dev/peps/pep-0440/#version-specifiers>`_, such as ``>=1.3,<1.4``. The implementation uses the nice package `semantic_version <https://pypi.org/project/semantic_version/>`_.

For demo purpose, let's say your ``requirements.txt`` file contains this:
::

	Flask>=0.12.1
	flask_restful
	jsonify
	psycopg2>=2.7.1
	nose
	scipy
	scikit-learn
	pandas
	numpy
	argparse
	uuid
	sqlbuilder
	proboscis
	pyyaml>=3.12

The execution will output this:
::

    $ liccheck -s my_strategy.ini -r my_project/required.txt
    gathering licenses...23 packages and dependencies.
    check forbidden packages based on licenses...none
    check authorized packages based on licenses...19 packages.
    check authorized packages...4 packages.
    check unknown licenses...none

If some dependencies are unknown or are not matching the strategy, the output will be something like:
::

    $ liccheck -s my_strategy.ini -r my_project/requirements.txt
	gathering licenses...32 packages and dependencies.
	check forbidden packages based on licenses...1 forbidden packages :
	    Unidecode (0.4.21) : GPL ['GNU General Public License v2 or later (GPLv2+)']
	      dependency:
	          Unidecode << python-slugify << yoyo-migrations

	check authorized packages based on licenses...24 packages.
	check authorized packages...6 packages.
	check unknown licenses...1 unknown packages :
	    feedparser (5.2.1) : UNKNOWN []
	      dependency:
	          feedparser

Contributing
============

To run the tests:
::

    $ tox -p all

Licensing
=========

-  See `LICENSE <LICENSE>`__
