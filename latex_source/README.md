# Group 10 Final Report LaTeX Source

This directory contains the IEEE two-column LaTeX and BibTeX source for the
Group 10 capstone final report.

## Files

- `main.tex`: complete report source using `IEEEtran`
- `references.bib`: BibTeX database for all cited sources
- `figures/`: code-generated report figures
- `build.ps1`: Windows build helper

## Build

With Tectonic installed and available on `PATH`:

```powershell
.\build.ps1
```

Equivalent direct command:

```powershell
tectonic main.tex --keep-logs --keep-intermediates
```

The generated submission PDF is `main.pdf`.

## Appendix Screenshot

`figures/github_latex_source.png` is the real screenshot of the top-level
`latex_source/` directory used on the appendix page. It is included in the
source package and compiled PDF.
