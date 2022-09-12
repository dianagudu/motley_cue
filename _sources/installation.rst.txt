.. _installation:


Installation
============

The recommended way to install ``motley_cue`` is via your Linux package manager.

Supported Linux distributions:

- Debian
- Ubuntu
- CentOS
- Rocky Linux
- openSUSE

We strive to support all LTS releases of the above distributions, as well as the latest stable release. Please check the repository at http://repo.data.kit.edu for all supported distributions and versions.

Follow the instructions there to support the repository on your system. Then install ``motley_cue`` with your favourite package manager:

.. code-block:: bash

   apt install motley-cue     # on debian-based systems
   yum install motley-cue     # on centos/rocky linux
   zypper install motley-cue  # on opensuse


This will ensure that all the dependencies are installed as well, and ``motley_cue`` is up and running as a systemd service.

.. warning::

   On Centos 7, you'll need to install two additional repositories for ``motley_cue``'s dependencies:

   - Extra Packages for Enterprise Linux (EPEL): for ``nginx``
   - Software Collections (SCL): for ``rh-python38``

   .. code-block:: bash

      yum install epel-release centos-release-scl


Installation from pypi
-----------------------

It is also possible to install ``motley_cue`` with ``pip``:

.. code-block:: bash

   pip install motley_cue

This will fetch the stable version from pip. You will need to set-up and run the service manually (see :ref:`running motley_cue in production <production>`).



Installing the development version
----------------------------------

The development version of ``motley_cue`` can be installed from the ``master`` branch
of the `GitHub motley_cue repository <https://github.com/dianagudu/motley_cue>`_ and
can be installed as follows (note the ``-e`` switch to install it in editable
or "develop mode"):

.. code-block:: bash

   git clone https://github.com/dianagudu/motley_cue
   cd motley_cue
   pip install -e .

