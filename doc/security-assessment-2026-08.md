# Security assessment — motley_cue and feudalAdapter, round 2

**Date:** 2026-08-10
**Scope:** `motley_cue` and `feudalAdapterLdf` (`ldf_adapter`), branch `security-assessment` in both.
**Status:** F1, F2, F3, F5, F6 and F7 fixed (see the status column and the per-finding
notes). F4 is the only one outstanding.

All `file:line` references below are to the tree as it was when the assessment was
made, i.e. *before* the three fixes.

## Summary

A previous round of hardening closed LDAP filter and DN injection, the OTP keyfile
handling, the `/tmp` token store, sudo-based de-privileging of shadow-utils, and
systemd confinement. This round looked at what that work did not cover.

Seven issues remain. The two most serious end at root on the SSH host, and neither
requires exploiting a bug — they are what the code does in normal operation:

* a `groups` claim in a user's token is turned into local supplementary group
  membership with no filtering whatsoever, so a token carrying `groups: ["sudo"]`
  produces `usermod --groups sudo`;
* `log_level = DEBUG` — the mode the recent assurance-diagnostics work steers
  operators towards — writes raw access tokens and OTPs into the journal.

| # | Finding | Severity | Component | Status |
|---|---------|----------|-----------|--------|
| F1 | A `groups` claim becomes local group membership, unfiltered | **Critical** | feudalAdapter (`local_unix`) | **Fixed** — `a2d800a` |
| F2 | Access tokens and OTPs written to the log at DEBUG | **High** | motley_cue | **Fixed** — `654fe13` |
| F3 | `install_ssh_keys` follows symlinks while running as root | **High** | feudalAdapter (`local_unix`) | **Fixed** — `fda6642` |
| F4 | Name and group existence checks bypass NSS | Medium | feudalAdapter (`local_unix`) | **Open** |
| F5 | The OTP is stored in cleartext as the database key | Medium | motley_cue | **Fixed** — `8664790` |
| F6 | No audience restriction by default; tokens replay across services | Medium | motley_cue (config) | **Fixed** — `5ef1478` |
| F7 | Five smaller issues | Low | both | **Fixed** — `e3caa4a`, `5a1ac79` (4 of 5; the fifth needed no change) |

Findings are described below as they were found; the fixed ones end with a note on
what was done. The commits are on the `security-assessment` branch of each repository.

A list of things that were checked and found sound is at the end, so the next round
does not re-derive them.

---

## F1 — A `groups` claim becomes local group membership, unfiltered

**Severity: Critical.** An OIDC claim reaches `usermod --groups sudo`.

### Where

* `ldf_adapter/config.py:414` — `ConfigGroups.policy` defaults to `"all"`.
  `motley_cue/etc/feudal_adapter.conf:202` ships `policy = all` as well, so this is
  the deployed configuration, not just the code default.
* `ldf_adapter/userinfo.py:371` `groups_from_grouplist` — takes the `groups` claim
  verbatim. The `listed` filter is skipped entirely under `policy = all`.
* `ldf_adapter/userinfo.py:396` `_group_masked_for_bwidm` and
  `ldf_adapter/backend/local_unix.py:621` `make_shadow_compatible` — both lowercase
  and transliterate; neither rejects anything. `sudo`, `wheel`, `docker`, `root` and
  `adm` pass through byte for byte.
* `ldf_adapter/__init__.py:630` `ensure_group_memberships` →
  `ldf_adapter/backend/local_unix.py:243` `_mod_cmd` → `usermod --groups <list> <user>`.
* `ldf_adapter/userinfo.py:437` `primary_group` — with no `primary_group` configured
  and more than one claimed group, the alphabetically first one becomes the **primary**
  group (`useradd -g adm`).

Amplifier on the motley_cue side: `motley_cue/mapper/authorisation.py:239` deliberately
copies `wlcg.groups` out of the access-token body into the `groups` claim, and
`merged_userinfo` (`:250`) merges the access-token body and the introspection response
into what feudalAdapter sees. A claim present only in the raw JWT still lands here.

### Reproduction

Read-only, against the repo's own test config:

```
cd feudalAdapterLdf
FEUDAL_ADAPTER_CONFIG=tests/feudal_adapter.conf .tox/py313/bin/python -c "
from feudal_globalconfig import globalconfig
globalconfig.config['parse_commandline_args']=False
from ldf_adapter.config import CONFIG
from ldf_adapter.userinfo import UserInfo
from ldf_adapter.backend.local_unix import make_shadow_compatible
print('groups.policy =', CONFIG.groups.policy)
data={'user':{'userinfo':{'sub':'attacker','iss':'https://op.example',
      'preferred_username':'eve','groups':['sudo','wheel','docker','root','adm']}}}
ui=UserInfo(data)
print('derived groups:', ui.groups)
print('shadow names:', [make_shadow_compatible(g) for g in ui.groups])
print('primary_group:', ui.primary_group)"
```

```
groups.policy = all
derived groups: ['sudo', 'docker', 'root', 'adm', 'wheel']
shadow names:   ['sudo', 'docker', 'root', 'adm', 'wheel']
primary_group:  adm
```

`ensure_groups_exist` (`ldf_adapter/__init__.py:609`) skips groups that already exist,
so the real local `sudo` group is used — no new group is created to make this visible.
The resulting `usermod --groups sudo,...` is root.

### Preconditions

The OP must assert the claim for the user. That is not a high bar: several AAIs allow
self-service VO or group creation, `wlcg.groups` travels in the token body, and any OP
compromise or misconfiguration converts directly into root here. A *legitimately named*
VO group (`docker`, `staff`, `disk`) does the same thing by accident, with no attacker
involved at all.

### Fix options

1. **Denylist plus a GID floor in the `local_unix` backend — recommended.**
   Refuse any group whose name is in a reserved set (`root`, `sudo`, `wheel`, `adm`,
   `docker`, `shadow`, `disk`, `staff`, `lxd`, `systemd-journal`, `ssh`, …) *or* whose
   already-existing GID is below a new `gid_min` in `[backend.local_unix]`.
   `ConfigLdap` and `ConfigBonsaiLdap` already carry `gid_min`/`gid_max`
   (`ldf_adapter/config.py:356`, `:396`); `local_unix` has no equivalent, and that is
   the actual gap.
   On a hit: drop that single group, emit an AUDIT record
   (`ldf_adapter/logsetup.py:25` `audit`), and let the deployment continue. Failing the
   whole deployment would turn a claim the user does not control into a denial of
   service. Apply the same check to `primary_group`.
2. **Flip the shipped default to `policy = listed`,** making group creation opt-in.
   Safest posture, but it silently breaks every existing deployment that relies on
   `all`. If taken, it belongs in `feudal_adapter_template.conf` plus release notes,
   not in the code default.
3. **Denylist only, no GID floor.** Simpler, but misses site-specific privileged groups
   — a local `operators` group with sudoers rights would still be reachable.

**Recommendation: 1**, with 2 documented as the stricter posture for new installs.
Option 1 alone makes the default configuration safe without requiring a config change,
which is what matters for the installs already out there.

### Fixed in `a2d800a`

Option 1. `RESERVED_GROUPS` and a new `gid_min` in `[backend.local_unix]`, behind
`Group.refused_reason()` so the policy lives with the unix semantics that make a name
dangerous. A refused supplementary group is dropped and recorded at AUDIT; the primary
group falls back to `fallback_group`, and fails if that is unset or refused too. Also
fixed a latent bug this exposed: both places that decided whether to append the primary
group compared *userinfo* names against a list of *backend* Group objects, so a
substituted primary group would never have been created or joined.

---

## F2 — Access tokens and OTPs are written to the log at DEBUG

**Severity: High.** Bearer credentials in the journal.

### Where

* `motley_cue/mapper/token_manager.py:254`, `:330`, `:392` —
  `logger.debug("Storing OTP [%s] for token [%s]", otp, token)`, once per backend.
* `motley_cue/mapper/token_manager.py:527`, `:530`, `:533` — the OTP, then
  `"Injected Access Token %s corresponding to given OTP %s"`.
* `motley_cue/mapper/token_manager.py:470` — the OTP again on the failure path.
* flaat itself: `flaat/__init__.py:217`, `logger.debug("Access token: %s", access_token)`.
  `motley_cue/mapper/config.py:102` maps `log_level = DEBUG` to flaat verbosity 3, so
  motley_cue is what turns this on.

### Consequence

The OTP *is* the SSH password — `inject_token` exchanges it for the access token before
authorisation runs (`motley_cue/apis/v1/root.py:112`) — and the access token is a
bearer credential at every relying party of that OP. At `log_level = DEBUG` both land in
the journal: readable by the `systemd-journal` group, forwarded to central log
collectors, retained in backups.

`motley_cue/logsetup.py` takes deliberate care to put audit records *above* CRITICAL so
they survive any configured level. The token lines have had no equivalent thought
applied.

This matters more than it used to. Commits `fab6cc7`, `59f3dca` and `61ca71c` added
extensive DEBUG diagnostics for assurance-tier troubleshooting, and
`motley-cue-simulator.py` sets `level=logging.DEBUG` outright. DEBUG is now the
documented way to diagnose a tier problem, and it is not currently safe to run on a
production service.

### Fix options

1. **Log a fingerprint, not the value — recommended.** Add a helper in
   `token_manager.py` returning `sha256(secret).hexdigest()[:8]` and use it in every
   line above. Correlating one OTP across several log lines — the only thing these
   messages are actually for — still works; the credential is no longer present.
2. **Clamp flaat's logger,** which is out of tree. One line in `Mapper.__init__`
   (`motley_cue/mapper/__init__.py:42`):
   `logging.getLogger("flaat").setLevel(max(config.log_level, logging.INFO))`.
   The alternative — a `logging.Filter` that redacts bearer-token-shaped strings —
   depends on guessing token formats and is less reliable.
3. **Document it.** Note at the `log_level` setting in `motley_cue.conf` that DEBUG
   exposes credentials, and point the assurance-troubleshooting docs at the AUDIT
   records rather than at DEBUG.

**Recommendation: 1 and 2, plus the documentation note.**

### Fixed in `654fe13`

All three. Every log line carrying either half now passes it through
`fingerprint()` — an 8-character sha256 prefix — in all three DB backends, and
`clamp_flaat_logging()` holds flaat's logger at INFO. The effect is that DEBUG became
safe to switch on rather than something to warn about, which is what the assurance
troubleshooting workflow needs.

---

## F3 — `install_ssh_keys` follows symlinks while running as root

**Severity: High.** Local privilege escalation, conditional on `deploy_user_ssh_keys`.

### Where

`ldf_adapter/backend/local_unix.py:376`:

```python
self.__authorized_keys.parent.mkdir(parents=True, exist_ok=True)
self.__authorized_keys.parent.chmod(0o700)
chown(self.__authorized_keys.parent, self.__uid, self.__gid)

self.__authorized_keys.write_text("\n".join(self.ssh_keys))
self.__authorized_keys.chmod(0o600)
chown(self.__authorized_keys, self.__uid, self.__gid)
```

The path is `Path(passwd_entry["home"]) / ".ssh" / "authorized_keys"` — inside a home
directory owned by the target user. Every operation here follows symlinks: `os.chown`
is not `lchown`, `Path.chmod` is not `lchmod`, and `write_text` opens through a link.

A user who already holds an account can replace `~/.ssh` with a symlink to, say,
`/etc` and have `chown` applied to it on their next deployment; or point
`authorized_keys` at an arbitrary file and have root truncate and rewrite it.

The shipped unit runs the service as `User=root` (`etc/motley-cue.service`) with
`CAP_CHOWN` and `CAP_DAC_OVERRIDE` in the bounding set, and the template config notes
explicitly that this path is **not** covered by `use_sudo`. `etc/feudal_adapter.conf:311`
ships `deploy_user_ssh_keys = no`, but the code default (`ldf_adapter/config.py:294`) is
`True`, so any site with a hand-written config is exposed.

### Fix options

1. **`O_NOFOLLOW` and descriptor-relative operations — recommended.** Open the home
   directory with `O_DIRECTORY|O_NOFOLLOW`, then create `.ssh` and `authorized_keys`
   relative to that descriptor using `dir_fd=`, with
   `O_CREAT|O_EXCL|O_NOFOLLOW, 0o600`, and `os.fchown`/`os.fchmod` on the resulting
   descriptor. This is exactly the idiom already used correctly in
   `motley_cue/mapper/token_manager.py:105` `Encryption.create_key` — an in-tree
   precedent worth following literally.
2. **Drop privileges for the operation:** fork, `setresgid`/`setresuid` to the target
   user, write, exit. The kernel then enforces the boundary rather than the code.
   Strongest guarantee, more machinery.
3. **Stop writing into home directories at all** and use
   `AuthorizedKeysFile /etc/ssh/authorized_keys.d/%u` with root-owned files. Changes
   deployment, but removes the class of bug rather than one instance of it.

**Recommendation: 1**, with 3 noted as the direction of travel.

### Fixed in `fda6642`

Option 1, extended in two ways the original plan did not anticipate. A hard link is not
covered by `O_NOFOLLOW`, so `authorized_keys` is `fstat`ed on the open descriptor and
rejected unless it is a regular file with one link. And the open deliberately omits
`O_TRUNC`: with it, the hard-link case still raised, but only after the victim file had
been emptied — truncation is the damage, so it now happens as an explicit `ftruncate`
after the checks. `uninstall_ssh_keys` was on the same footing and got the same
treatment.

---

## F4 — Name and group existence checks bypass NSS

**Severity: Medium.**

### Where

`ldf_adapter/backend/local_unix.py:427` `__all_passwd_entries` and `:589`
`__all_group_entries` read and split `/etc/passwd` and `/etc/group` directly. They back
`name_taken` (`:133`) and `Group.exists` (`:480`).

On any host where users or groups come from LDAP, SSSD, NIS or systemd-homed, those
accounts are invisible to this check:

* `name_taken` returns `False` for a directory user, so a federated user who sets
  `preferred_username` to a directory account's name gets a *local* account with that
  name — shadowing the directory entry, and, depending on `nsswitch.conf` order, taking
  precedence over it.
* `Group.exists` returning `False` makes feudalAdapter `groupadd` a name that already
  exists in the directory, splitting one group across two GIDs.

`root` happens to be safe here only because it is in `/etc/passwd`.

### Fix options

1. **Use NSS for the existence question — recommended.** `pwd.getpwnam` and
   `grp.getgrnam` for "does this name exist", keeping the `/etc/passwd` scan only for
   the GECOS → `unique_id` reverse lookup, which is the one thing it is genuinely
   needed for. Small change, and it also picks up reserved names from every source.
2. Shell out to `getent passwd` / `getent group`. Same coverage, one subprocess per
   check, no advantage over 1.
3. Add a static reserved-name list. Complementary — and worth having anyway, see F1 —
   but it does not address the directory-shadowing case.

**Recommendation: 1**, with the reserved list from F1 as defence in depth.

---

## F5 — The OTP is stored in cleartext as the database key

**Severity: Medium.** Defence in depth today, not a live hole.

### Where

`motley_cue/mapper/token_manager.py:236`–`:279`, and the `memory` and `sqlitedict`
equivalents at `:313` and `:386`. The `otp` column holds the plaintext OTP; only the
`at` column is Fernet-encrypted.

Because the OTP is itself an accepted credential (`inject_token` → `/verify_user`),
anyone who can read the database can authenticate as every user with a live OTP. The
encryption of the `at` column — and the careful keyfile vetting at `:35`–`:102` — buys
nothing against precisely the threat it was written for: a disclosed database file, a
backup, a stray copy.

`/var/lib/motley_cue` is mode 0700 (`debian/motley-cue.postinst:10`,
`rpm/motley-cue.spec:141`), so reading the file already requires root or the service
account. That is what keeps this at Medium.

Secondary issue in the same file: `SQLiteTokenDB.pop` (`:221`) does `SELECT` then
`DELETE` with no explicit transaction. Under gunicorn with several workers, two
concurrent requests can both read the row before either deletes it, so a "one-time"
password is usable twice.

### Fix options

1. **Key the table by `sha256(otp)` — recommended.** Store the digest, look up by
   digest, keep the encrypted `at`. Semantics and schema shape are unchanged, and a
   database read then yields nothing usable. Migration is trivial: OTPs are
   short-lived, so a new table name and letting the old one lapse is enough.
2. Encrypt the OTP column too. This does not work — it has to be looked up by value,
   and Fernet is non-deterministic.
3. For the race: `DELETE FROM tokenmap WHERE otp=? RETURNING at` (SQLite ≥ 3.35,
   present on all target distributions), or wrap the pair in `BEGIN IMMEDIATE`.

**Recommendation: 1 and 3.**

### Fixed in `8664790`

Both. The table is keyed by `sha256(otp)` and renamed, with the old cleartext-keyed one
dropped so those OTPs leave the disk. `pop` wraps its select and delete in `BEGIN
IMMEDIATE` (not `DELETE ... RETURNING`, which needs SQLite 3.35 while rockylinux-8 ships
3.26); a test forces the interleaving and fails without it, both workers getting the
same token. The `sqlitedict` backend cannot be given the same guarantee — it exposes a
mapping whose `__delitem__` is a separate statement on its writer thread — so that is
now documented where the race is.

---

## F6 — No audience restriction by default; tokens replay across services

**Severity: Medium.** A configuration trade-off the config does not surface.

`motley_cue/mapper/config.py:370` defaults `audience = ""`, and flaat's
`get_audience_requirement("")` returns `Satisfied()`. A token issued to *any* relying
party of a trusted OP is therefore accepted here.

Combined with `authorise_all = True`, every other service the user logs into with that
OP holds a credential that provisions them a shell account on this host.

This is arguably the intended ssh-oidc model — tokens are not service-bound by design —
but it is a deliberate trade-off, and nothing in the configuration currently says so.

### Fix options

1. **Document it at the `audience` setting and recommend setting it — recommended.**
2. **Emit a startup warning** when an OP has `authorise_all = True` and an empty
   `audience`. One line in `ConfigOPAuthZ`; makes the trade-off visible without
   breaking anyone.
3. Require `audience` whenever `authorise_all` is set. Breaking, and not proportionate.

**Recommendation: 1 and 2.**

### Fixed in `5ef1478`

Both. `Authorisation.__init__` warns for any OP with `authorise_all` and no `audience`,
and the `audience` setting in `motley_cue.conf` now says what leaving it empty means.

---

## F7 — Smaller issues

**`canonical_url` collisions silently merge OP policies.**
`motley_cue/mapper/config.py:213` strips the scheme, a trailing slash *and* a leading
`www.`. `ConfigAuthorisation.load` (`:468`) keys `all_op_authz` by that value, so
`[authorisation.https://example.org]` and `[authorisation.https://www.example.org]`
collapse into one entry: the last section wins, and the other OP silently runs under
authorisation rules that were not written for it. flaat matches issuers exactly
(`flaat/__init__.py:110`), so this cannot admit an untrusted OP — it can misapply policy
between two trusted ones.
*Fix:* detect duplicate canonical keys at load time and refuse to start, matching the
fail-closed stance `_validated_tier` (`motley_cue/mapper/assurance.py:228`) already
takes for a mistyped tier name.

**An empty `iss` skips the admin same-issuer check.**
`motley_cue/mapper/authorisation.py:191`: `_check_request` only compares issuers when
`kwargs.get("iss", "")` is non-empty, so `?iss=` reaches `admin_suspend(sub, "")`
unchecked. No account matches an empty issuer, so the impact today is nil — but the
check reads as though it enforces something it does not.
*Fix:* reject an empty `iss`.

**An unrecognised `shadow_compatibility_function` yields `None`.**
`ldf_adapter/backend/local_unix.py:621` `make_shadow_compatible` has no `else` branch,
so a typo in the config makes every username `None`, which then reaches `useradd`.
*Fix:* validate the setting at startup — again, `_validated_tier` is the precedent.

**`verbose_info_plugin` writes a world-readable claim dump into a world-writable
directory.** `ldf_adapter/__init__.py:56`–`:79`: `os.chmod(dirname, 0o0777)` and
`os.chmod(filename, 0o0666)`, defaulting to `/tmp/userinfo/`
(`ldf_adapter/config.py:426`). It dumps the full merged claim set — everything from the
token body, including whatever PII the OP releases. The 0777 directory in a shared
`/tmp` is also a symlink target for the root-owned `open(..., "w")` a line above. The
plugin is off by default and `PrivateTmp=yes` in the shipped unit contains it, but
neither of those is a reason for the mode bits.
*Fix:* mode 0600 in a root-owned directory, or delete the plugin.

**Config search paths include the working directory.**
`motley_cue/mapper/config.py:143` and `ldf_adapter/config.py:35` both consider
`./<name>.conf` and `~/.config/…`. The shipped unit sets
`WorkingDirectory=/usr/lib/motley-cue` (root-owned), so this is fine today. Worth
confirming the same holds for `etc/examples/motley-cue-unprivileged.service`, where
`HOME` belongs to a service account.

---

## Checked and sound

Recorded so the next round does not re-derive them.

* **Empty authorisation config fails closed.** `ConfigOPAuthZ.get_user_requirement`
  builds `OneOf()` with no sub-requirements, and flaat's `N_Of` returns
  `CheckResult(False, "No sub-requirements")`. There is no accidental allow-all.
  `get_admin_requirement` returns `Unsatisfiable()` when no admins are listed.
* **Decorator order on `/verify_user` is correct.** `motley_cue/apis/v1/root.py:112`–`:113`:
  `inject_token` is the outer decorator, so the OTP is exchanged for the real access
  token *before* authorisation runs against it.
* **Issuer trust is enforced exactly by flaat** (`_issuer_is_trusted`,
  `flaat/__init__.py:110`), independently of motley_cue's `canonical_url` normalisation.
* **`unique_id` cannot corrupt the passwd column split.** It is
  `quote_plus(sub)@quote_plus(iss)`, so no `:` can reach the GECOS field.
* **LDAP injection is closed** in both LDAP backends (`escape_filter_chars` /
  `escape_rdn`, `escape_filter_exp` / `escape_attribute_value`), `homeDirectory` is
  pinned under `home_base`, and `make_ldap_compatible` reduces names to a safe set.
* **`privileged()` is argument-safe.** It uses `sudo -n --`, and `make_shadow_compatible`
  guarantees names start with `[a-z_]`, so no argument can be read as an option by sudo
  or by shadow-utils.
* **The OTP keyfile handling is correct** — `O_NOFOLLOW`, `O_EXCL`, `fstat` on the
  already-open descriptor, refusal of group- or other-accessible modes. It is the model
  the F3 fix should copy.
