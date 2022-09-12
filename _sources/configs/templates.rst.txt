.. _templates:

Templates
=========

Email templates to be used for notifying admins and users about new deployment requests. Only required if you are using the approval workflow in **feudal** with the **email** notification system.

The templates are installed by ``pip`` when you install **motley-cue**. You can find them in the ``etc/motley_cue/templates`` directory of the Python environment. We recommend installing them in ``/etc/motley_cue/templates``.

The following templates are available:

- ``admin.deploy.template``: template for the email sent to admins when a new deployment request is submitted.
- ``admin.deploy.update.template``: template for the email sent to admins when a deployment request is updated.
- ``admin.update.template``: template for the email sent to admins when a deployed user needs to be updated.
- ``admin.test.template``: template for the email sent to admins to test that the notification system is configured correctly.
- ``user.deploy.template``: template for the email sent to users when a new deployment request is submitted.
- ``user.deploy.update.template``: template for the email sent to users when a deployment request is updated.
- ``user.update.template``: template for the email sent to users when a deployed user needs to be updated.

Below an example template for ``admin.deploy.template``:

.. literalinclude:: ../../../etc/templates/admin.deploy.template
   :language: guess
