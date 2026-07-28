# Translation and extraction notes

- Source format: selectable-text PDF (`pdf-text`), 26 pages.
- Source license shown on p.1: Creative Commons Attribution 4.0 International.
- Extraction: PyPDF/PyMuPDF text layer; no OCR was applied.
- Visual verification: methodology figures on pp.9 and 13, the LightFTP case on pp.18-19, and experiment figures/tables on pp.15-23 were rendered and inspected.
- Reader scope: the user requested a detailed methodological and experimental analysis, not a verbatim full translation. `paper.md` is therefore an analysis-focused bilingual evidence map containing 35 stable evidence blocks and every method/result figure or table used by the analysis. Related-work prose and the bibliography are not translated block by block. Under the full-translation contract this is draft/selected-block mode, and the omission is intentional and visible rather than silent.
- Figure/table crops are semantic tight crops. Captions remain separate in `paper.md`.
- The PDF text on p.23 contains the literal typesetting artifact `start here`; it was not treated as substantive content.
- Figure 2 labels the apparent resume operation as `kill(SIGSTOP)`, although a stopped process would normally be resumed with `SIGCONT`. The prose does not resolve this; the detailed analysis flags it as a likely diagram typo rather than assuming implementation behavior.
- No external web lookup, source-code audit, or artifact execution was performed. All substantive claims are grounded in the supplied PDF.
