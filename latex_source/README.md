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

## Final Appendix Step

After this directory is uploaded to the team GitHub repository, capture one
real screenshot showing the top-level `latex_source/` directory and save it as:

```text
figures/github_latex_source.png
```

Rebuild the report. The appendix placeholder will automatically be replaced by
the screenshot. Do not use a synthetic or local-file screenshot for this step.
