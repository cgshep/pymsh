# Changelog

All notable changes to **pymsh** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `CITATION.cff` so academic users can cite the library directly from GitHub's
  "Cite this repository" button, alongside the underlying ASIACRYPT 2003 paper.
- A "When Would I Use This?" section in the README with three short,
  beginner-friendly examples (comparing shopping carts, bag-of-words
  document fingerprinting, running fingerprint over streaming data) that
  motivate *why* a multiset hash is the right tool before any cryptography
  vocabulary appears.
- `__all__` to the public module so `from pymsh import *` exposes only the
  documented API.
- Validation of `m` in `MSetAddHash` (must be a positive power of two,
  `<= 512`), matching the existing check in `MSetXORHash`.
- Validation that `MSetAddHash.update` rejects negative multiplicities,
  consistent with `MSetAddHash.hash` and `MSetXORHash`.
- Validation that `MSetVAddHash` rejects non-positive `n_bits`.
- More precise return-type annotations (`tuple[bytes, int, bytes]`,
  `tuple[bytes, bytes]`, `bytes`).
- Test coverage for the new validation paths.
- Cross-class property tests in `tests/test_msh_basic.py` covering all four
  hashes (same-multiset equivalence, order independence, distinct-multiset
  separation, empty-multiset behaviour).
- Coverage reporting and a build/`twine check` job in CI.
- Python 3.13 added to the CI matrix.

### Changed
- `MSetMuHash` no longer requires `q_bits` to be a power of two — that
  constraint blocked legitimate primes (e.g. 3000-bit `q`). When `q_bits` is
  omitted it is now derived from `q.bit_length()`. When supplied it must be
  at least `q.bit_length()`.
- `MSetAddHash.hash` is now implemented in terms of `update`, removing the
  awkward post-construction reseeding of the temporary instance.
- `requires-python` raised to `>= 3.9` to match the supported CI matrix.
- The Hatch wheel/sdist targets are now declared explicitly so the build
  artefacts are deterministic.

### Removed
- The orphaned `src/pymsh/{base,addmsh,xormsh}.py` legacy files — they
  implemented an older, undocumented API that conflicted with the published
  package layout, were not exported from any release, and broke `pytest`
  collection.
- `tests/test_addmsh.py` (was empty) and `tests/utils.py` (was only used by
  the legacy test).

### Fixed
- `tests/test_msh_basic.py` previously imported `pymsh.xormsh.XORMSH`, a
  module that does not exist in the published package, causing
  `pytest` collection to fail.
- Several docstring inconsistencies (e.g. `:param none:` typo; return types
  documented as `int` while the methods return `bytes`).

## [1.2.1]

- Initial documented release.
