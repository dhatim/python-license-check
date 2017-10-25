Python License Checker
======================

Check python packages from requirement.txt and report license issues.

About
=====

You can define a list of authorized licenses, authorized packages,
unauthorized licenses.

The tool will check the requirement.txt files, check packages and their
dependencies and return an error if some packages are not compliant
against the strategy. A package is considered as not compliant when its license 
is in the unauthorized license list or is unknown. A package is considered as compliant when its 
license is in authorized license list, or if the package is itself in the list of
authorized packages.

How to install
==============

::

	$ pip install liccheck


How to use
==========

liccheck will read the requirement.txt and check packages agains a strategy defined in the ini file.
If the file is not specified on command line, it will lookup for requirement.txt in the current folder.
You have to setup an ini file with an authorized license list, unauthorized license list, authorized package list.

Here is an example of a strategy:
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


For demo purpose, let's say your requirement.txt file contains this:
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

If some dependencies are unknown or are not matching strategy, the output will be something like:
::

    $ liccheck -s my_strategy.ini -r my_project/required.txt
	gathering licenses...32 packages and dependencies.
	check forbidden packages based on licenses...1 forbidden packages :
	    Unidecode (0.4.21) : GPL ['GNU General Public License v2 or later (GPLv2+)']
	      dependencye(s):
	          Unidecode << python-slugify << yoyo-migrations

	check authorized packages based on licenses...24 packages.
	check authorized packages...6 packages.
	check unknown licenses...1 unknown packages :
	    feedparser (5.2.1) : UNKNOWN []
	      dependencye(s):
	          feedparser

Licensing
=========

-  See `LICENSE <LICENSE>`__
