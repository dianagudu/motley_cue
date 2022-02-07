.. _ssh_integration:

SSH Integration
===============

A detailed documentation of all the required components to enable SSH access via OIDC with on-the-fly account provisioning can be found at: https://github.com/EOSC-synergy/ssh-oidc. A quick summary below.

PAM
---

You'll need `this <https://git.man.poznan.pl/stash/scm/pracelab/pam.git>`_ PAM module that supports OIDC authentication by prompting the user for a token instead of a password.

You can also install it from the http://repo.data.kit.edu/ repo:

.. code-block:: bash

    apt-get install pam-ssh-oidc
    or
    yum install pam-ssh-oidc


Check out the documentation for how to configure it. Make sure you set SSH to use the PAM module.

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

    ChallengeResponseAuthentication yes
    UsePam yes

Note that this may enable password based logins that you need to disable separately.

Client
------

To SSH into a server that supports OIDC authentication, you'll need to trigger the deployment of a local account by calling the ``/user/deploy`` endpoint and then get the local username via ``/user/get_status``.

Or you can have a look at `mccli <https://dianagudu.github.io/mccli>`_, an SSH client wrapper that does all this for you and can integrate with the ``oidc-agent``.
