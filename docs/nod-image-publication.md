# Nod image publication

Home Assistant reads add-on versions from `feat/nod-home-assistant`. Publishing a new version on that branch before its GHCR image exists can cause an HTTP 404 in Supervisor.

## Release order (experimental)

1. Create a candidate branch based on the current distribution branch. Change the implementation and bump the version of every affected add-on. Never reuse a published version for changed runtime content.
2. Run the relevant tests on a pull request against `feat/nod-home-assistant`. Record the exact candidate commit.
3. Advance the trusted `publish/nod-candidate` branch to that candidate commit. This branch is not configured in Home Assistant. Only authorized maintainers may advance it. The push-triggered server and worker image workflows build missing tags; existing tags are preserved.
4. Require the candidate's anonymous GHCR pull checks to pass for all three configured versions (linux/amd64, expected source and smoke test). Record the resulting digests and require the relevant runtime CI to pass.
5. Confirm the candidate SHA has not changed and the distribution branch can be advanced without losing intervening commits. Fast-forward `feat/nod-home-assistant` to that exact validated SHA. Do not force-push the distribution branch.
6. Verify Home Assistant sees the update, then test on VMware and Lenovo. Stable release remains a separate decision.

If any check fails, keep the distribution branch unchanged. If a candidate image has already been published but needs a runtime correction, use a new version rather than overwriting the existing tag.

This is a maintainer-controlled promotion procedure, not an automatic branch protection rule. Do not bypass the registry check. Repository maintainers should restrict write access to both trusted branches. The PR registry check can be rerun after publication if it timed out before the image was available.
