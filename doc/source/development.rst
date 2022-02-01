.. _development:

For developers
==============

Building the Linux packages
---------------------------

To build the Linux packages, a Makefile is provided, which uses docker
for building:

.. code-block:: bash

    make dockerised_<name>

where ``<name>`` can be one of:

- ``dockerised_deb_debian_bullseye``
- ``dockerised_deb_debian_bookworm``
- ``dockerised_deb_ubuntu_bionic``
- ``dockerised_deb_ubuntu_focal``
- ``dockerised_rpm_centos7``
- ``dockerised_rpm_centos8``
- ``dockerised_rpm_opensuse15.2``
- ``dockerised_rpm_opensuse15.3``
- ``dockerised_rpm_opensuse_tumbleweed``
- ``dockerised_all_packages`` (to build all of the above)

The resulting files are copied out of the build container to the ``../results`` folder.

Docker for SSH-OIDC
-------------------

`motley_cue_docker <https://github.com/dianagudu/motley_cue_docker>`_ allows you to run the whole SSH-OIDC set-up in Docker containers.

.. warning::

    motley_cue_docker is not regularly maintained.