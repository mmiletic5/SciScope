# Research: JATS parser, sections, and locators

**Problem.** Convert the 17 preserved PLOS ONE JATS sources into inspectable
abstract, section, and paragraph records with digest-bound source locators. The
human will use these records to verify passages for Golden v0. Decisions D1-D10
in the feature request are fixed; Person 1 still reviews the taxonomy mapping.

## Approaches and sources

| Approach | Verified facts | Fit and limits |
| --- | --- | --- |
| Python 3.12 `xml.etree.ElementTree` (chosen) | [Python XML documentation](https://docs.python.org/3.12/library/xml.html) calls it a lightweight processor. It does not retrieve external DTDs; malicious entity expansion can still exhaust resources. Standard library license is the [PSF license](https://docs.python.org/3/license.html). Existing `parse_article` already uses `ET.fromstring` and local-name helpers. | No dependency; explicit tree traversal, size bounds, DOCTYPE/entity policy, and paragraph rules are needed. |
| `lxml` | [PyPI](https://pypi.org/project/lxml/) lists XPath support and CPython 3.12 wheels. Its [license page](https://lxml.de/FAQ.html#what-is-the-license-of-lxml) describes BSD-style licensing. | Mature XML tools, but adds a compiled runtime dependency and changes parsing/security configuration; D1 excludes it. |
| Existing JATS/PubMed parsers | [`pubmed-parser`](https://pypi.org/project/pubmed-parser/) 0.5.1 is MIT and extracts paragraphs with section labels; it uses `lxml`. [`s2orc-doc2json`](https://github.com/allenai/s2orc-doc2json) includes JATS2JSON, is Apache-2.0, and warns of imperfect coverage. | Their output contracts do not establish the required digest-bound positional locator and exact paragraph rule; adoption would need further validation. Python 3.12 compatibility of these two packages is **NOT VERIFIED**. |

**Recommendation.** Keep D1 and reuse the F001 parsing pattern where safe.
Reject internal entity declarations and XInclude, impose an XML size limit, and
do not fetch external resources. A plain external DOCTYPE declaration is present
in every pilot file and must remain parseable. The planned byte-level safety
scan assumes an ASCII-compatible encoding, so F002 accepts UTF-8 only and
rejects UTF-16 BOMs or non-UTF-8 declarations. All 17 observed declarations
are UTF-8, with letter case as recorded below. Reject internal DTD subsets;
choose a generous size cap from the largest measured pilot file during T006
and record the measurement and cap in T008 evidence.

## Read-only empirical survey, 2026-11-15

Source: all 17 `raw_xml_path` entries in `data/pilot/manifest.jsonl`, read by
`.venv/Scripts/python.exe -I` with `ElementTree`; no files were modified. All 17
file SHA256 digests matched the manifest. Counts below are observed, not output
counts from a future parser.

| Attribute tuple (`article-type`, `dtd-version`, `xml:lang`) | Papers |
| --- | ---: |
| `research-article`, `1.1d3`, `en` | 6 |
| `research-article`, `1.3`, `en` | 1 |
| `research-article`, `3.0`, `en` | 6 |
| `research-article`, `3.0`, `EN` | 4 |

| Structure | Observation |
| --- | --- |
| Abstract | 17 have one untyped `<abstract>`; 15 have one direct `<p>`; two have three `<sec>` children each, each with direct `<title>` and `<p>` and no direct abstract `<p>`. No `abstract-type` variant observed. |
| Body children | 83 `<sec>`; no other direct body child and no direct body `<p>`. |
| Body `<sec>` depth | 83 at depth 1, 185 at depth 2, 28 at depth 3 (296 total). All 296 have direct `<title>`; 295 have `id`. Title descendants: 15 `<italic>`. |
| Body `<sec sec-type>` | 238 absent; `materials|methods` 15; `results` 12; `conclusions` 12; `intro` 11; `supplementary-material` 5; `discussion`, `introduction`, and `methods` 1 each. |
| Direct `<p>` child kinds | `xref` 1966; `italic` 1430; `sup` 255; `sub` 134; `bold` 30; `ext-link` 24; `named-content` 22; `email` 6; `list` 2; `disp-formula` 9; `inline-formula` 1. |
| Other descendants inside `<p>` (including those inside child nodes) | `alternatives` 8; `graphic` 10; `label` 7; `list-item` 6; nested `p` 6; `math` 8; `mfrac` 5; `mi` 77; `mn` 8; `mo` 46; `mrow` 34; `mspace` 16; `msub` 14; `msup` 5; `mtext` 10. Full descendant counts for shared kinds: `xref` 1974, `italic` 1487, `sup` 256, `sub` 169. |
| Back matter | `<ref-list>` in 17, `<ack>` in 16; no other back container observed. |
| XML bytes | 17 DOCTYPE declarations, zero `<!ENTITY` declarations and zero XInclude elements; 9 uppercase `UTF-8` and 8 lowercase `utf-8` declarations; zero UTF-8 BOM and zero CRLF; all 17 contain non-ASCII bytes; six paragraph text nodes contain NBSP. |

| Top-level section heading, exact normalized whitespace only | Count |
| --- | ---: |
| `Introduction` / `1. Introduction` | 15 / 2 |
| `Material and Methods` / `Material and methods` / `Materials and Methods` / `Materials and methods` / `2. Materials and methods` / `Methods and Materials` / `Methods` | 1 / 2 / 7 / 3 / 2 / 1 / 1 |
| `Results` / `3. Results` / `Results and Discussion` | 14 / 2 / 1 |
| `Discussion` / `4. Discussion` | 14 / 2 |
| `Conclusions` | 2 |
| `Supporting Information` / `Supporting information` | 7 / 7 |

**Gaps.** The corpus does not exercise absent body, body-level paragraphs,
untitled sections, internal entities, or XInclude. Those need labeled synthetic
tests after spec and plan approval. The proposed F004 contract does not define
paragraph records or an abstract-section representation. No scientific passage
or answer is inferred from this survey.
