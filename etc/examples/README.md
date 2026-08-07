# Assurance-based shell tiers — example configuration

Assurance evaluation moved out of feudalAdapter into motley_cue. motley_cue now
classifies each user's assurance/MFA claims into a **shell tier** and passes that
tier to feudalAdapter, which maps it to a login shell. Assurance no longer
*rejects* users — everyone who is authorised is deployed; the tier only decides
which shell they get.

| Signals (evaluated in motley_cue)   | Tier         | Shell                              |
|-------------------------------------|--------------|------------------------------------|
| MFA **and** cappuccino              | `full`       | `/bin/bash`                        |
| cappuccino, no MFA                  | `limited`    | `/etc/motley_cue/shells/mc-rbash`  |
| neither                             | `restricted` | `/etc/motley_cue/shells/mc-message`|

The two tier shells are shipped as part of the package in
`/etc/motley_cue/shells/` and are already referenced by the default
`/etc/motley_cue/feudal_adapter.conf`. They stay inert until the tiers are
enabled on the motley_cue side: with the shipped `motley_cue.conf` every
authorised user resolves to `full` → the default shell, i.e. unchanged
behaviour. The files in this directory turn the feature **on** for testing and
as a reference.

## Files

- `motley_cue.assurance.conf` — motley_cue config with the shell tiers enabled: the
  policy in `[DEFAULT]`, plus one OP overriding it.
- `feudal_adapter.assurance.conf` — feudalAdapter config mapping each tier to a shell.

The shells themselves live one level up, in `/etc/motley_cue/shells/`:

- `mc-rbash` — the `limited` shell: allows only a safe command whitelist.
- `mc-message` — the `restricted` shell: prints a message and exits.

## Trying it locally

```sh
# (optionally) make the shells known to the system
grep -qxF /etc/motley_cue/shells/mc-rbash   /etc/shells || echo /etc/motley_cue/shells/mc-rbash   | sudo tee -a /etc/shells
grep -qxF /etc/motley_cue/shells/mc-message /etc/shells || echo /etc/motley_cue/shells/mc-message | sudo tee -a /etc/shells

# point the services at the example configs
export MOTLEY_CUE_CONFIG=/etc/motley_cue/examples/motley_cue.assurance.conf
export FEUDAL_ADAPTER_CONFIG=/etc/motley_cue/examples/feudal_adapter.assurance.conf
```

Then deploy with tokens of differing assurance and check the assigned shell:

```sh
getent passwd "$USERNAME"        # last field is the login shell
```

- MFA + cappuccino token → `…:/bin/bash`
- cappuccino-only token   → `…:/etc/motley_cue/shells/mc-rbash`
- neither                 → `…:/etc/motley_cue/shells/mc-message`
  (logging in prints the message and disconnects — this is the "This account is
  currently not available."-style behaviour, but with an explanatory message
  rather than `/sbin/nologin`.)

Adjust `op_url` in `motley_cue.assurance.conf` to your test OP.

## Notes / caveats

- The shipped shells are intentionally simple and self-contained. For production,
  consider a hardened restricted shell (e.g. `rbash` with a curated `PATH`) for
  the `limited` tier.
- The tiers are only applied by feudalAdapter's **local_unix** backend. The same
  shells would work for the ldap backends, but there the login shell is written
  into the directory: it must then exist (executable, and usually listed in
  `/etc/shells`) on every target system the user logs in to — not just on the
  host running motley_cue.
- Login shells generally must be executable and, depending on PAM/sshd policy,
  listed in `/etc/shells`. `/etc` may be mounted `noexec` on some hosts — if so,
  install the shells under `/usr/lib/motley-cue/shells/` (or similar) and update
  the `shell_*` paths in `feudal_adapter.conf` accordingly.
- feudal's tier defaults are **fail-closed**: if you enable a tier in
  motley_cue but leave its `shell_*` unset in feudal, that tier falls back to
  `/sbin/nologin`.

## Functional CI (test-ssh-oidc)

The SSH/mccli functional tests live in the sibling project
`m-team/tools/integration/test-ssh-oidc` (triggered from this repo's
`.gitlab-ci.yml`). To cover the *enabled* path there, that pipeline needs to:

1. Point `MOTLEY_CUE_CONFIG` / `FEUDAL_ADAPTER_CONFIG` at these example files
   (or splice the `assurance_based_shell_*` options and the `[backend.local_unix]`
   block into the
   configs it already generates — e.g. via `contextualise_ssh_server`). The
   shells are installed by the package, so nothing extra needs copying.
2. Provide (at least) two access tokens of differing assurance — one reaching
   `full`, one reaching `restricted` — and assert the resulting login shell
   (via `getent passwd`, or by asserting the `mc-message` banner on login).

Those token fixtures and assertions must be added in `test-ssh-oidc`; this
directory provides the configuration they consume.

## If everyone lands in `restricted`

Relative tokens are resolved against `assurance_prefix`, which defaults to the
REFEDS **root** (`https://refeds.org`). So the cappuccino profile has to be
written `assurance/profile/cappuccino` — it lives under `/assurance/`, while
MFA (`profile/mfa`) does not. A relative token that does not resolve expands to
a URL no provider asserts and then silently never matches, dropping every user
to the fallback tier.

If you wrote a policy before the prefix defaulted to the root, it will still say
`profile/cappuccino`, and your config file is preserved across package upgrades
— so the shipped example changing does not change yours. Set
`log_level = DEBUG` in `[mapper]` and look for the per-token verdict:

```
Tier 'limited' ... no match | expression: profile/cappuccino |
  'profile/cappuccino' = False (tried 'profile/cappuccino' and 'https://refeds.org/profile/cappuccino')
```
