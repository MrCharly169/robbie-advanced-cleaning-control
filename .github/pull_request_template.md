## Summary

<!-- What user problem does this change solve? -->

## Scope and compatibility

- Adapter(s):
- Home Assistant version tested:
- Migration or release impact:

## Validation

- [ ] `python -m unittest discover -s tests -v`
- [ ] `python scripts/check_source_syntax.py`
- [ ] `node tests/test_card_runtime.js`
- [ ] `node tests/test_card_browser.mjs` when Card/Badge behavior changed
- [ ] `python scripts/build_release.py --check`
- [ ] Disposable Home Assistant lab when runtime, registry or migration behavior changed
- [ ] `git diff --check`

## Documentation and safety

- [ ] Added or updated regression coverage; no regression test was removed to make the change pass.
- [ ] Updated `CHANGELOG.md -> Unreleased` for user-visible changes.
- [ ] Updated English/German customer text together when product facts changed.
- [ ] Kept manufacturer transport and credentials in the existing Home Assistant integration.
- [ ] Included no tokens, credentials, private entity names, production URLs or full diagnostics/backups.
- [ ] Kept the contribution compatible with the MIT License.
