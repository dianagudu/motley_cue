# Assurance-based shell tiers — example configuration

Assurance evaluation moved out of feudalAdapter into motley_cue. motley_cue now
classifies each user's assurance/MFA claims into a **shell tier** and passes that
tier to feudalAdapter, which maps it to a login shell. Assurance no longer
*rejects* users — everyone who is authorised is deployed; the tier only decides
which shell they get.

| Signals (evaluated in motley_cue)   | Tier         | Example shell (this dir)      |
|-------------------------------------|--------------|-------------------------------|
| MFA **and** `profile/cappuccino`    | `full`       | `/bin/bash`                   |
| `profile/cappuccino`, no MFA        | `limited`    | `shells/mc-rbash`             |
| neither                             | `restricted` | `shells/mc-message`           |

The default configs shipped in `/etc/motley_cue/` keep this feature **off**
(every authorised user resolves to `full` → the default shell, i.e. unchanged
behaviour). The files here turn it **on** for testing and as a reference.

## Files

- `motley_cue.assurance.conf` — motley_cue config with the `[assurance]` tiers enabled.
- `feudal_adapter.assurance.conf` — feudalAdapter config mapping each tier to a shell.
- `shells/mc-rbash` — the `limited` shell: allows only a safe command whitelist.
- `shells/mc-message` — the `restricted` shell: prints a message and exits.

## Trying it locally

```sh
# make the example shells executable and (optionally) known to the system
sudo install -m 0755 shells/mc-rbash shells/mc-message /etc/motley_cue/examples/shells/
grep -qxF /etc/motley_cue/examples/shells/mc-rbash   /etc/shells || echo /etc/motley_cue/examples/shells/mc-rbash   | sudo tee -a /etc/shells
grep -qxF /etc/motley_cue/examples/shells/mc-message /etc/shells || echo /etc/motley_cue/examples/shells/mc-message | sudo tee -a /etc/shells

# point the services at the example configs
export MOTLEY_CUE_CONFIG=/etc/motley_cue/examples/motley_cue.assurance.conf
export FEUDAL_ADAPTER_CONFIG=/etc/motley_cue/examples/feudal_adapter.assurance.conf
```

Then deploy with tokens of differing assurance and check the assigned shell:

```sh
getent passwd "$USERNAME"        # last field is the login shell
```

- MFA + cappuccino token → `…:/bin/bash`
- cappuccino-only token   → `…:/etc/motley_cue/examples/shells/mc-rbash`
- neither                 → `…:/etc/motley_cue/examples/shells/mc-message`
  (logging in prints the message and disconnects — this is the "This account is
  currently not available."-style behaviour, but with an explanatory message
  rather than `/sbin/nologin`.)

Adjust `op_url` in `motley_cue.assurance.conf` to your test OP.

## Notes / caveats

- The example shells are intentionally simple and self-contained. For production,
  consider a hardened restricted shell (e.g. `rbash` with a curated `PATH`) for
  the `limited` tier.
- Login shells generally must be executable and, depending on PAM/sshd policy,
  listed in `/etc/shells`. `/etc` may be mounted `noexec` on some hosts — if so,
  install the shells under `/usr/lib/motley-cue/shells/` (or similar) and update
  the `shell_*` paths accordingly.
- feudal's tier defaults are **fail-closed**: if you enable a tier in
  motley_cue but leave its `shell_*` unset in feudal, that tier falls back to
  `/sbin/nologin`.

## Functional CI (test-ssh-oidc)

The SSH/mccli functional tests live in the sibling project
`m-team/tools/integration/test-ssh-oidc` (triggered from this repo's
`.gitlab-ci.yml`). To cover the *enabled* path there, that pipeline needs to:

1. Install the shells and point `MOTLEY_CUE_CONFIG` / `FEUDAL_ADAPTER_CONFIG` at
   these example files (or splice the `[assurance]` and `[backend.local_unix]`
   blocks into the configs it already generates — e.g. via
   `contextualise_ssh_server`).
2. Provide (at least) two access tokens of differing assurance — one reaching
   `full`, one reaching `restricted` — and assert the resulting login shell
   (via `getent passwd`, or by asserting the `mc-message` banner on login).

Those token fixtures and assertions must be added in `test-ssh-oidc`; this
directory provides the configuration and shells they consume.
