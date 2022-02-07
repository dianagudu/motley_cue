.. _running:

Running
=======

If you installed ``motley_cue`` using a package manager, you can simply start the service by:

.. code-block:: bash

    systemctl start motley-cue

The :doc:`motley_cue API <api>` will be available http://localhost:8080. 

It is highly recommended to use HTTPS. The nginx site file installed with the package also provides an example configuration for that in the comments (see section on :ref:`how to manually configure nginx with motley_cue <nginx>` for more details).

You will also need certificates for your server. Probably the simplest way to do that is by using https://letsencrypt.org/.



Development
-----------

If you installed ``motley_cue`` with ``pip``, for quick testing you can simply run it with ``uvicorn`` (as user with permissions to add users):

.. code-block:: bash

    sudo motley_cue_uvicorn


The API will then be available at http://localhost:8080.


.. _production:

Production
----------

This section describes how to run ``motley_cue`` in production if you installed it with ``pip``.
If you used the package, these configuration options are already applied.

To set up the production environment, we recommended using:

- ``gunicorn``: manages multiple uvicorn worker processes, monitors and restarts crashed processes
- ``systemd``: service management and monitoring
- ``nginx``: HTTPS support, buffers slow clients and prevents DoS attacks


The code examples below assume a python virtualenv at ``/usr/lib/motley-cue``, where you have installed ``motley_cue`` and its dependencies. Adapt paths if necessary.

Templates for all referred configuration files are provided with either the package or the ``pip`` installation.

..
 You can change the port and other nginx settings by editing ``/etc/nginx/sites-enabled/nginx.motley_cue``.


gunicorn
^^^^^^^^

To configure ``motley_cue`` to run with ``gunicorn``, you will need two additional configuration files.

- :ref:`gunicorn.conf.py <gunicorn_conf>`: config file for gunicorn with sane default values.
- :ref:`motley_cue.env <motley_cue_env>`: here you can set the environment variables used in the gunicorn config, such as the socket address gunicorn listens on (``BIND``), log file location or log level.

Recommended locations for these files:

- ``/usr/lib/motley-cue/etc/gunicorn/gunicorn.conf.py``
- ``/etc/motley_cue/motley_cue.env``


systemd
^^^^^^^

Create the :ref:`service file <motley_cue_service>` to run gunicorn under ``systemd`` and place it in ``/lib/systemd/system/motley-cue.service``:

.. literalinclude:: ../../etc/motley-cue.service
   :language: bash

..
  :emphasize-lines: 9,11

Start the service with:

.. code-block:: bash

    systemctl start motley-cue


.. _nginx:

nginx
^^^^^

An example :ref:`site configuration <nginx_motley_cue>` is provided below: 

.. literalinclude:: ../../etc/nginx.motley_cue
    :language: bash

Copy it to the appropriate location (e.g. ``/etc/nginx/sites-enabled/nginx.motley_cue``) and reload ``nginx``.


Config files
^^^^^^^^^^^^

This is the list of the required configuration files, which are usually present when you install ``motley_cue`` with a package manager:

.. toctree::
    :maxdepth: 1

    /etc/motley_cue/motley_cue.conf  <configs/motley_cue_conf>
    /etc/motley_cue/feudal_adapter.conf <configs/feudal_adapter_conf>
    /etc/motley_cue/motley_cue.env <configs/motley_cue_env>
    /lib/systemd/system/motley-cue.service <configs/motley_cue_service>
    /etc/nginx/sites-available/nginx.motley_cue <configs/nginx_motley_cue>
    /usr/lib/motley-cue/etc/gunicorn/gunicorn.conf.py <configs/gunicorn_conf>
