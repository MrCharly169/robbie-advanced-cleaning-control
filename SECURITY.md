# Security Policy

## Supported versions

Security fixes target the latest stable release and, when affected, the latest
prerelease. Older releases and arbitrary development snapshots are not normally
patched. Check the manifest and GitHub Releases before reporting.

## Reporting a vulnerability

Do not disclose a vulnerability, exploit, Home Assistant token, manufacturer
credential, cookie, auth file or private diagnostic in a public issue.

Use GitHub's **Report a vulnerability** action on the repository Security page
to create a private report. Include:

- affected Robbie and Home Assistant versions;
- Generic or Valetudo adapter path;
- an anonymized `vacuum.*` entity;
- impact and reproducible steps;
- the smallest reviewed diagnostic excerpt needed to understand the issue.

If private vulnerability reporting is not available, open a public issue titled
`[Security contact request]` without technical or sensitive details and ask the
maintainer for a private channel.

The maintainer will acknowledge a private report, reproduce and assess it, and
coordinate a fix and disclosure. Response times are best effort for this
volunteer-maintained project.

## Scope reminders

Robbie does not own manufacturer authentication or device transport. Security
problems in an existing Home Assistant vacuum integration, Valetudo, MQTT or a
manufacturer cloud should also be reported to that upstream project. A Robbie
report is appropriate when planner storage, services, diagnostics, Card/Badge
delivery or adapter translation creates the issue.
