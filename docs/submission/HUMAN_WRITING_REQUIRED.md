# Human Writing Required Checklist

This checklist identifies all sections in `report/final-report-draft.md` that require human writing. The report has these sections with TODO/unchecked items.

> **Deadline:** July 22 (noted in the file itself)

### Abstract
- **File:** `report/final-report-draft.md`
- **Section name and line range:** Abstract (line 8-15)
- **Owner:** Yuze
- **What needs to be written:** Draft skeleton exists but needs human writing.
- **Available evidence files:** N/A (Summarize the entire report)

### Section 1 Introduction
- **File:** `report/final-report-draft.md`
- **Section name and line range:** Section 1 Introduction (line 17-21)
- **Owner:** Yuze
- **What needs to be written:** 3 unchecked items.
- **Available evidence files:** Motivation figures (fig_motivation.png).

### Section 2 Background
- **File:** `report/final-report-draft.md`
- **Section name and line range:** Section 2 Background (line 23-28)
- **Owner:** Chenxi
- **What needs to be written:** 4 unchecked items.
- **Available evidence files:** Standard LLM serving background.

### Section 3 Related Work
- **File:** `report/final-report-draft.md`
- **Section name and line range:** Section 3 Related Work (line 30-36)
- **Owner:** Shun, Mengze
- **What needs to be written:** 4 unchecked items.
- **Available evidence files:** Reference list and literature.

### Section 4 Methodology
- **File:** `report/final-report-draft.md`
- **Section name and line range:** Section 4 Methodology (line 38-44)
- **Owner:** Yuze
- **What needs to be written:** 5 unchecked items.
- **Available evidence files:** Methodology descriptions.

### Section 5 Evaluation
- **File:** `report/final-report-draft.md`
- **Section name and line range:** Section 5 Evaluation (line 46-57)
- **Owner:** Yuze + Yuh Jen
- **What needs to be written:** Multiple sub-items unchecked.
- **Available evidence files:** Main evaluation figures (fig_ttft_vs_rate.png, fig_cdf_indist_r8.png).

### Section 6 Ablation Study
- **File:** `report/final-report-draft.md`
- **Section name and line range:** Section 6 Ablation Study (line 59-76)
- **Owner:** Yuze + Yuh Jen
- **What needs to be written:** Multiple items including data verification.
- **Available evidence files:** Phase D outputs.
- **CRITICAL WARNINGS about Phase D:**
  - Phase D results use a ShareGPT-trained predictor on ShareGPT test data.
  - Phase D is matched-distribution multi-seed stability, NOT LMSYS→ShareGPT OOD.
  - Do NOT cite Phase D as OOD evidence.
  - Phase A/C from `docs/experiments/2026-06-21-aging-gate-validation.md` IS the OOD evidence (single seed).
- **Forbidden claims to avoid:** Do NOT claim OOD robustness using Phase D data.

### Section 7 Artifact Statement
- **File:** `report/final-report-draft.md`
- **Section name and line range:** Section 7 Artifact Statement (line 78-82)
- **Owner:** Ben
- **What needs to be written:** 3 unchecked items.
- **Available evidence files:** `docs/submission/FIGURE_EVIDENCE_CHAIN.md`, `scripts/audit_submission_results.py`.

### Section 8 Individual Contributions
- **File:** `report/final-report-draft.md`
- **Section name and line range:** Section 8 Individual Contributions (line 84-86)
- **Owner:** All members
- **What needs to be written:** 1 unchecked item.
- **Available evidence files:** Team notes.

### Section 9 Limitations
- **File:** `report/final-report-draft.md`
- **Section name and line range:** Section 9 Limitations (line 88-93)
- **Owner:** Yuze
- **What needs to be written:** 4 unchecked items.
- **Available evidence files:** Known limitations discussed in meetings.

### Section 10 Conclusion
- **File:** `report/final-report-draft.md`
- **Section name and line range:** Section 10 Conclusion (line 95-97)
- **Owner:** Yuze
- **What needs to be written:** TODO.
- **Available evidence files:** Summary of the rest of the report.

---

**Note:** `docs/roadmap-v0.1.md` has 3 TBD items and 7 unchecked items, and `docs/lessons/` has unchecked items — these are informational and may not need completion for submission.
