# Language policy

Language is an explicit product decision, never an accidental mixture.

- English: source code, entity unique IDs, service names, logs, reason codes,
  repository documentation, changelog and GitHub workflows.
- English and German: config flow, options flow, entity names, Card labels and
  future repair flows.
- User-provided mission names, room names and entity friendly names are shown
  unchanged.
- Adapter values remain the exact machine values accepted by the underlying
  integration and are not translated in service calls.

English is the fallback when Home Assistant uses any language other than
German.
