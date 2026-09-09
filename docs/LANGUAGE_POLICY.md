# Language policy

Language is an explicit product decision, never an accidental mixture.

- English: source code, entity unique IDs, service names, logs, reason codes,
  developer documentation, changelog and GitHub workflows.
- English is the canonical repository landing page. `docs/de/README.md` is the
  defined exception: a complete German customer-facing counterpart whose
  product facts, requirements, version policy and license terms must stay in
  sync with `README.md`.
- English and German: config flow, options flow, entity names, Card labels and
  future repair flows.
- User-provided mission names, room names and entity friendly names are shown
  unchanged.
- Adapter values remain the exact machine values accepted by the underlying
  integration and are not translated in service calls.

Cards and Badges follow the active Home Assistant app/profile language on each
client. Explicit English and regional English tags select English; German,
unsupported and missing language tags select German. The Home Assistant
installation language and the browser language never override the active app
profile. Unknown backend reason codes are shown only as a same-language generic
message; raw codes remain available through diagnostics.

Native entity names are shared Home Assistant registry metadata generated in the
backend language; they do not switch for each app. Native state, selector and
flow translations follow the viewing user's language. User names stay unchanged.
