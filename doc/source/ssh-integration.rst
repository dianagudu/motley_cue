.. _ssh_integration:

SSH Integration
===============

A detailed documentation of all the required components to enable SSH access via OIDC with on-the-fly account provisioning can be found at: https://github.com/EOSC-synergy/ssh-oidc. A quick summary below.

PAM
---

SSH access with an OIDC access token as password is handled on the server side
by the ``pam-ssh-oidc`` module. See the `SSH-OIDC documentation
<https://ssh-oidc-doc.data.kit.edu/ssh/access-token-password/>`_ for the login
flows and how the components fit together.

You can install the module from the http://repo.data.kit.edu/ repo:

.. code-block:: bash

    apt-get install pam-ssh-oidc
    or
    yum install pam-ssh-oidc


Check out the documentation for how to configure it, and make sure you set SSH to use the PAM module.

If you install the package `pam-ssh-oidc-autoconfig`, it will automatically configure SSH to use the PAM module.

In ``/etc/pam.d/sshd`` add on the first line:

.. code-block::
    
    auth     sufficient pam_oidc_token.so config=/etc/pam.d/config.ini

and configure the verification endpoint to your motley_cue instance in ``/etc/pam.d/config.ini``:

.. code-block:: ini

    [user_verification]
    local = false
    verify_endpoint = $MOTLEY_CUE_ENDPOINT/verify_user

where MOTLEY_CUE_ENDPOINT=<http://localhost:8080> with a default installation.

Finally, make sure you have in your ``/etc/ssh/sshd_config``:

.. code-block::

    UsePam yes
    # one of the following, depending on your version of OpenSSH:
    ChallengeResponseAuthentication yes
    KbdInteractiveAuthentication yes

Note that this may enable password based logins that you need to disable separately.

oinit (SSH certificates)
------------------------

As an alternative to PAM, SSH logins can use short-lived SSH certificates
via `oinit <https://ssh-oidc-doc.data.kit.edu/ssh/ssh-certificates/>`_.
This needs no PAM module on the SSH server: ``oinit-ca`` validates the
user's OIDC token against ``motley_cue`` (through ``/verify_user``,
i.e. the same authorisation and deployment state as any other login)
and issues a certificate for the local username ``motley_cue`` reports.
No extra ``motley_cue`` configuration is required for this flow.

See the `SSH certificates documentation
<https://ssh-oidc-doc.data.kit.edu/ssh/ssh-certificates/>`_ for setting up
``oinit`` (client), ``oinit-ca`` and the SSH server, and the `demos
<https://ssh-oidc-doc.data.kit.edu/demos/>`_ for a walk-through.

Client
------

To SSH into a server that supports OIDC authentication, you'll need to trigger the deployment of a local account by calling the ``/user/deploy`` endpoint and then get the local username via ``/user/get_status``.

Or you can have a look at `mccli <https://mccli.readthedocs.io>`_, an SSH client wrapper that does all this for you and can integrate with the ``oidc-agent``.
