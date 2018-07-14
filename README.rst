
Intelligent Tracker  |build-status| |docs|
=========================================================

Overview
========

This package provides an API and user interface for tracking objects using haarcascades, keypoints and
other methods that will be integrated in the future.

The purpose is to create a software to create smart cameras that can detect and follow people
in a close environment composed of scenes and entries on them like doors or imaginary areas
where people or objects can be counted or statistics can be obtained.

For now the project is its early stages and the development until the objectives can be reach can take time.
But for now it offers a demo in the main.py script which hopefully can convey the intend of the project and be useful to someone.
That said, this code does not intent to compete against commercial software but rather complement them for integration
with a CCTV system and to not obscure users of what information is being processed from them hence the GPL licence.

Latest:

    - Documentation: http://intelligent-tracker.readthedocs.io/
    - Project Homepage: https://github.com/davtoh/intelligent-tracker

Licence:

    GPL v3 Licence_

Documentation
=============

For API documentation, usage and examples see files in the "documentation"
directory.  The ".rst" files can be read in any text editor or being converted to
HTML or PDF using Sphinx_. A HTML version will be available soon.

Installation
============
``pip install intelligent-tracker`` should work for most users.

The usual setup.py for Python_ libraries are used for the source distribution.
But OpenCV must be installed separately usually compiled from source.

To install OpenCV on windows without much hassle I recommend installing the binaries from
the `Unofficial Windows Binaries for Python`_ and for Debian distributions I
provide the bash `OpenCV linux installation`_ so that the user can compile
openCV (it can take some time). Bear in mind that for Linux it downloads the
latest 3.x version.

Once successfully installed you can import it in python as:

    >>>> import intelligent_tracker as itt

Releases
========

All releases follow semantic rules proposed in https://www.python.org/dev/peps/pep-0440/
and http://semver.org/

Testing and application
=======================

This project provides unittest tests under the tests/ folder. As an example we can see the tracker in action:

.. figure:: https://github.com/davtoh/intelligent-tracker/blob/master/documentation/_static/Scene1_f1.jpg
    :align: center
    :scale: 5%

.. figure:: https://github.com/davtoh/intelligent-tracker/blob/master/documentation/_static/Scene1_f2.jpg
    :align: center
    :scale: 5%

.. figure:: https://github.com/davtoh/intelligent-tracker/blob/master/documentation/_static/Scene1_f3.jpg
    :align: center
    :scale: 5%

.. figure:: https://github.com/davtoh/intelligent-tracker/blob/master/documentation/_static/Scene1_f4.jpg
    :align: center
    :scale: 5%

.. figure:: https://github.com/davtoh/intelligent-tracker/blob/master/documentation/_static/Scene1_f5.jpg
    :align: center
    :scale: 5%

Usage
=====

Open your console and type ``python main.py``


- Contributions and bug reports are appreciated.
- author: David Toro
- e-mail: davsamirtor@gmail.com
- project: https://github.com/davtoh/intelligent-tracker

.. _Licence: https://github.com/davtoh/intelligent-tracker/LICENSE.rst
.. _Python: http://python.org/
.. _Sphinx: http://sphinx-doc.org/
.. _pyinstaller: http://www.pyinstaller.org/
.. |build-status| image:: https://travis-ci.org/pyserial/pyserial.svg?branch=master
   :target: https://github.com/davtoh/intelligent-tracker/releases
   :alt: Build status
.. |docs| image:: https://readthedocs.org/projects/pyserial/badge/?version=latest
   :target: http://intelligent-tracker.readthedocs.io/
   :alt: Documentation
.. _`Unofficial Windows Binaries for Python`: http://www.lfd.uci.edu/~gohlke/pythonlibs/
.. _`OpenCV linux installation`: https://github.com/davtoh/intelligent-tracker/blob/master/install_opencv.sh
