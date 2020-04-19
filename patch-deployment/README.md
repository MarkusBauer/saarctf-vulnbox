# Patch Deployment

## Dependencies
- install `ansible` (on Arch-Linux: `pacman -S ansible`)

## How to patch
- Create patch as shell-script and call it according to our name-scheme: `apply-<servicename>-<patchname>.sh`
- Copy `patch-deploy-template.yaml` to `patch-deploy-<patchname>.yaml`
- Edit `patch-deploy-<patchname>.yaml` (see TODO's)
- Deploy patchfile to test-vulnboxes: `ansible-playbook -i test-vulnboxes.yaml ./patch-deploy-<patchname>.yaml`
- Check if everything worked on the test-vulnboxes
- Deploy patchfile to vulnboxes: `ansible-playbook -i vulnboxes.yaml ./patch-deploy-<patchname>.yaml`
- Write notification via Twitter and announce it in IRC