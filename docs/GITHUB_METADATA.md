# GitHub metadata and manual repository settings

This file records the recommended public metadata. Applying these settings is a
manual maintainer action and is not part of the working-tree changes.

## About

```text
Local, vendor-neutral mission planner for robot vacuums already connected to Home Assistant.
```

Suggested website: leave empty until a maintained documentation/site URL exists.

## Topics

```text
home-assistant
homeassistant
hacs
custom-integration
robot-vacuum
vacuum
valetudo
local-first
home-automation
mission-planner
```

## Social preview

Upload `docs/images/social-preview.png`. It is 1280 × 640 px and uses the
existing Robbie logo.

## Support and sponsorship

- Support URL: `https://github.com/MrCharly169/robbie-advanced-cleaning-control/issues`
- Security URL: `https://github.com/MrCharly169/robbie-advanced-cleaning-control/security`
- Sponsor/Buy Me a Coffee: **not configured**. Add no badge or payment link
  until the maintainer supplies and verifies the real URL.

## Manual settings checklist

- Add the About description and topics above. The public repository currently
  has a description but no topics.
- Upload the social preview under **Settings → General → Social preview**.
- Keep Issues enabled and confirm the YAML issue forms render.
- Enable **Private vulnerability reporting** so `SECURITY.md` and the Code of
  Conduct have a confidential reporting path.
- Add useful issue labels such as `bug`, `enhancement`, `documentation`,
  `adapter: generic`, `adapter: valetudo` and `needs-info`.
- Protect `main` and `develop`: require pull requests and the relevant Validate
  and Home Assistant lab checks, prevent force pushes and preserve the existing
  stable/beta branch contract.
- Keep GitHub Actions permissions at least privilege and retain immutable
  release tags/assets.
- If applying for inclusion in HACS defaults later, add and pass the official
  HACS Action and Hassfest checks first. The current public claim remains
  **HACS Custom**.
- Configure a GitHub Sponsors/custom funding link only after a verified support
  URL is available; voluntary support is not a license fee.
