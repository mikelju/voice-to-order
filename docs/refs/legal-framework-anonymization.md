# Legal framework for the data anonymization in this project

This project publishes a dataset derived from a real client's operational data (article catalog and
voice-dictated order history). Before publishing anything, an anonymization process was applied,
designed against the regulatory framework below. This document records the sources and the design
decisions derived from them; all sources are public and cited by URL.

## Sources

| Regulation / guidance | What it contributes to this project | Source |
|---|---|---|
| **GDPR** — Regulation (EU) 2016/679 | The anonymization standard: data stops being personal **only if re-identification is reasonably impossible** (Recital 26). Pseudonymization (reversible identifier substitution) is still personal data. | https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32016R0679 |
| **LOPDGDD** — Spanish Organic Law 3/2018 | Spanish transposition of the GDPR; regime applicable to the controller (the client) and the processor. | https://www.boe.es/eli/es/lo/2018/12/05/3/con |
| **EDPB Opinion 28/2024** on AI models | Criteria for considering an AI model/dataset anonymous: one must assess the **reasonable likelihood of extraction or inference** of personal data, not just the absence of direct identifiers. | https://www.edpb.europa.eu/our-work-tools/our-documents/opinion-board-art-64/opinion-282024-certain-data-protection-aspects_en |
| **AEPD guidance on agentic AI** (2026) | Data-protection implications when AI agents process personal data in automated pipelines; reinforces minimization and traceability. | https://www.aepd.es/ |
| **AEPD policy on generative AI** | The Spanish authority's criteria on data use in generative-AI systems. | https://www.aepd.es/ |

## Design decisions derived from them

1. **Anonymization, not pseudonymization, for everything identifying.** ERP part numbers are
   regenerated with a hash keyed by a **secret salt kept outside the repository**: without the salt
   the mapping is neither reversible nor brute-force verifiable against a list of real ids
   (GDPR Recital 26).
2. **Voices are never published.** Audio is **biometric data of identifiable natural persons** (the
   technicians): no real audio file enters the repository. Demo mode uses sanitized text
   transcriptions; real mode uses the user's own microphone.
3. **Dictated text: sweep of indirect identifiers.** Historical phrases are cleaned of end-customer
   names, site names, order numbers and phone numbers (`[customer]`, `[site]`, `[order-ref]`,
   `[phone]`), an automated sweep runs with a real-terms list kept outside the repo, and a manual
   review of unlisted proper nouns is mandatory (the EDPB test: could someone in the industry narrow
   the residue down to one company?).
4. **Minimization.** Columns that do not serve the purpose (supplier, user ids, order numbers,
   precise timestamps) are dropped or generalized (dates → month).
5. **Article descriptions are kept.** They are generic plumbing/HVAC catalog vocabulary (e.g.
   `VALVULA BOLA 1/2 LATON H PN30 PALANCA`): they identify no person and — once the supplier, real
   ids and the embedded administrative names/phones are removed — no company.
6. **Automated, repeatable verification.** The repo ships a verification tool (`tools/`) that anyone
   can run over `data/` and that the publishing workflow requires green; the full real-terms list
   feeding the sweep lives outside the repository.

> Note: this document is not legal advice; it is the record of the criteria applied and their
> sources, for traceability of the anonymization process.
