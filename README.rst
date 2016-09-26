.. image:: https://badge.fury.io/py/omero-reader.svg
    :target: https://badge.fury.io/py/omero-reader

OMERO Reader
=============

Pure Python implementation of python-bioformats reader API using OMERO.

Requirements
============

* OMERO.py 5.1.x, 5.2.x
* Python 2.6+

Development Installation
========================

1. Clone the repository::

        git@github.com:glencoesoftware/omero-reader.git

2. Set up a virtualenv (http://www.pip-installer.org/) and activate it::

        curl -O -k https://raw.github.com/pypa/virtualenv/master/virtualenv.py
        python virtualenv.py omero-reader
        source omero-reader/bin/activate
        pip install -r requirements.txt
        pip install -r requirements-dev.txt

Running Tests
=============

Using py.test to run the unit tests::

    	py.test tests/unit/

License
=======

This project is licensed under the terms of the GNU General Public License (GPL) v2 or later.

Reference
=========

* http://www.openmicroscopy.org/site/products/bio-formats
* https://github.com/CellProfiler/python-bioformats
* https://www.openmicroscopy.org/site/support/omero5.2/developers/Python.html
