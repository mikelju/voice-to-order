# Fix N: [Bug Title]

<!-- N is a GLOBALLY sequential number (fix-1, fix-2, fix-3...), shared across all phases. -->

## Affected phase / functionality
Which part of the product has the bug and which phase of the plan it belongs to.

<!-- If this fix closes a security finding, add the reference here:
Finding reference: [docs/security/audit-YYYY-MM-DD-phase-X.md §3.N SEC-NNN](../security/audit-YYYY-MM-DD-phase-X.md)
-->

## Symptom
What incorrect behavior the user observes (or, if it is a security finding, the exploitable vector).

## Root cause
Why exactly it happens (with file:line references if applicable).

## Adopted solution
What exactly was changed.

## UX
<!-- Mandatory if the fix touches anything user-visible. Write "No change"
if the fix is internal and legitimate behavior is not altered. This field
is especially important for security fixes, where the goal is to close
the vector without introducing friction for the end user. -->
[No change / what the user notices]

## Modified files
- `path/file:line` — description of the change

## Cross-reference
<!-- Mandatory: this fix MUST be referenced in the "Fixes" section
of the affected phase plan (X.0_name.md). If the phase has no plan, reference it
in the master plan's "Fixes" section.

If the fix closes one or more security findings, list the closed IDs here
to keep traceability in docs/security/README.md:
- Closes: SEC-NNN, SEC-MMM, DEF-NNN (only if applicable).
-->
- Recorded in: `docs/plans/phase_X/X.0_name.md` → Fixes section
- Closes: [optional list of SEC/DEF/OBS from `docs/security/`]
