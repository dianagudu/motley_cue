.. _development:

For developers
==============

Branching model
---------------

- ``prerel`` is the development branch. All day-to-day work lands here.
- Feature and fix branches branch off ``prerel`` and merge back into
  ``prerel``, preferably via pull request, with green CI.
- ``master`` is the release branch. It advances only via release pull
  requests ``prerel`` → ``master``, opened once a release is ready — never
  by direct pushes. (The last such release PR was ``v0.7.1``; ``master``
  has since advanced outside that flow, which is why this rule is now
  written down.)
- ``vX.Y.Z`` tags are created manually on ``master`` after the release PR
  is merged.

Releasing
---------

The version is tracked in three places, kept in sync by ``bump2version``
(configured in ``.bumpversion.cfg``):

- ``motley_cue/VERSION`` (Python package version)
- ``debian/changelog`` (top entry, Debian package version)
- ``rpm/motley-cue.spec`` (``Version:``, RPM package version)

When to bump
^^^^^^^^^^^^

Bump once per release, on ``prerel``, after all feature work is merged and
CI is green — as the final commit before, or the first commit inside, the
release pull request::

    bump2version [patch|minor|major]

Use ``patch`` for bug fixes, dependency updates and CI/test-only changes,
``minor`` for new backwards-compatible functionality, and ``major`` for
breaking changes. Deciding at release time means the bump level is chosen
with full knowledge of the release contents. Do not bump when starting a
feature branch (every branch would edit the same single-line files and
conflict on merge, and prerel builds would carry the new version before
the release scope is known) and not after every merge to ``prerel``
(which makes the version creep without releases).

Rules:

- Never hand-edit the version strings. Hand edits desynchronise
  ``.bumpversion.cfg`` and the tool stops working.
- The tool never tags (``tag = False``). ``vX.Y.Z`` tags are created
  manually on ``master`` when a release is published (see below).
- Prerelease numbering (``0.8.6~prN``) is fully automatic: GitLab CI
  rewrites the version at build time via
  ``.gitlab-ci-scripts/set-prerelease-version.sh``. Nothing to do manually.

Release checklist
^^^^^^^^^^^^^^^^^

1. All feature pull requests merged to ``prerel``, CI green.
2. ``bump2version [patch|minor|major]`` on ``prerel`` (commits
   automatically).
3. Open pull request ``prerel`` → ``master`` titled ``vX.Y.Z``, review,
   merge.
4. Create tag ``vX.Y.Z`` on ``master`` and push it.
5. Create a release on GitHub from the tag, with release notes describing
   the changes since the previous release.


Docker for SSH-OIDC
-------------------

`motley_cue_docker <https://github.com/dianagudu/motley_cue_docker>`_ allows you to run the whole SSH-OIDC set-up in Docker containers.

.. warning::

    motley_cue_docker is not regularly maintained.
