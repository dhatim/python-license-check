Python License Checker
======================

Check python packages from requirement.txt and report license issues.

About
=====

You can define a list of authorized licenses, authorized packages,
unauthorized licenses.

The tool will check the requirement.txt files, check packages and their
dependencies and return an error if some packages are not compliante
against the strategy. A package is considered as not compliant when it's license 
is in unauthorized license list or is unknown. A package is considered as compliant when it's 
license is in authorized license list, or if the package is itself in the list of
authorized packages.

How to install
==============

::

	$ pip install liccheck


How to use
==========

liccheck will read a the required.txt, and check packages agains strategy defined in ini file.
If the file is not specified on command line, it will lookup for required.txt in current folder.
You have to setup an ini file with authorized license list, unauthorized license list, authorized package list.

Here is an example:
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


::

    $ python -m license_check -s my_strategy.ini -r my_project/required.txt
    gathering licenses...23 packages and dependencies.
    check forbidden packages based on licenses...none
    check authorized packages based on licenses...19 packages.
    check authorized packages...4 packages.
    check unknown licenses...none

Licensing
=========

-  See `LICENSE <LICENSE>`__