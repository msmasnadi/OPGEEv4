# Contributing to the RMI OPGEEv4 Repository

> [!NOTE]
> This is a WIP and subject to change.

## Branches

### `main`
RMI's internal production branch. We'll periodically merge `opgee-main`, but this may contain code that's specific to RMI's needs.

### `dev`
RMI's internal development branch. Though it's safer to start with `opgee-dev` if all work is certain to be RMI-specific, feature branchs can originate here, too.

### `opgee-main`
Corresponds to the main OPGEE branch. This should not be updated from RMI's end; we will always sync this from the upstream repo.

### `opgee-dev`
This is the primary development branch for work that is intended to be integrated into the upstream OPGEE repo. All feature branches start here. We'll periodically merge `opgee-main` into `opgee-dev` to keep things up to date.

## Workflows
### OPGEE
Check out a new branch from `opgee-dev`.
```bash
git checkout opgee-dev
git checkout -b feat/my-new-branch
```
Once work is completed, open a PR into the upstream repo's `dev` branch.