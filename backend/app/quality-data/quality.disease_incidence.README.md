# Corrected plant visual-condition interpretation and sampled-leaf incidence rules

## What changed
- Maintained the original column names and the existing 30 Model 2 non-healthy class identifiers. Added optional interpretation columns to both knowledge and incidence CSVs, without deleting existing fields.
- Completed five frequency bands for **all 30** non-healthy classes (150 rows); filled the previously missing `murraya_koenigii / Complex Foliar Damage` and `murraya_koenigii / Fungus` classes.
- Revised all classifications to distinguish *visual conditions* from *confirmed causes*: suspected fungal/bacterial/oomycete signs, pest/mite injury, unresolved lesions, natural pigmentation, suspected nutrient disorder, mixed symptoms, and non-specific yellowing/drying.
- Added **possible_causes**, **natural_aging_possible**, **distinguishing_signs**, **additional_checks**, **cause_confirmation_required**, **treatment_applicability**, and **condition_risk_interpretation** to explain findings before recommending cause-specific action.
- In every incidence band, changes focus on the **priority of observing, investigating, and obtaining advice**, never on a proven biological threat or an automatic treatment trigger.
- Dried gotukola now explicitly considers **natural leaf senescence** and water/heat/root stress, and does not conflate leaf drying with shoot/branch dieback.
- Holy basil anthocyanin pigmentation is treated as potentially **normal and healthy**, even when common among sampled leaves. No automatic anti-disease treatment.
- Combined neem `Leaf_Miners_Powdery_Mildew` remains a *single model class*, not artificially split into independent counts of two diseases.
- Added four supporting **general differential-diagnosis** university extension references (R36-R39). These do not validate individual medicinal-species diagnoses or treatment cutoffs.

## Meaning of 0 / 25 / 50 / 75 / 100% bands
`percentage = accepted unique sampled leaves with Model 2 class / all accepted unique sampled leaves * 100`

- 0%: `None_Detected` (not proof of absence)
- >0 to 25%: `Low`
- >25 to 50%: `Moderate`
- >50 to 75%: `High`
- >75 to 100%: `Very_High`

These ranges are adapted as *descriptive frequency brackets* from an ICAR crop-screening scale (R29). They are **not validated severity, threat, treatment, plant-wide infection or medicinal-safety thresholds** for the six studied species. Management is based on signs, probable cause, progression, sampling representativeness, and qualified guidance, not percent alone.

## Compatibility
- Replace existing `backend/app/quality-data/quality.disease_knowledge.csv` with the corrected file of the same name.
- Replace existing `backend/app/quality-data/quality.disease_incidence.csv` and `quality.disease_incidence_references.csv` with the corrected files of the same names.
- Optional new fields are appended; original fields remain in the same order so `csv.DictReader` consumers using existing keys should continue to work.
- **Backend and Flutter must still display condition labels accurately.** Do not show all non-healthy Model 2 outputs as "confirmed disease". Prefer "visual condition predicted" followed by possible causes, checks, then care guidance.
- `medicinal_suitability_level` original enum values remain unchanged for compatibility. They are **precautionary visual-quality hints only**, not independent certification. The user-facing UI must not turn "Suitable" into "medicinally safe/approved" without separately verified quality and safety requirements.
- No model retraining, no changes to the maturity CSV, and no automatic live reload: restart the Flask backend or clear CSV caches to load updated CSV rows.

## Evidence and limitations
- Existing row-specific URLs were preserved, not independently validated one by one in this revision.
- R36 Iowa State Extension: https://yardandgarden.extension.iastate.edu/how-to/biotic-vs-abiotic-distinguishing-disease-problems
- R37 University of Maryland Extension: https://extension.umd.edu/resource/yellowing-leaves-vegetable-plants
- R38 Colorado State Extension: https://extension.colostate.edu/resource/diagnosing-plant-disorders/
- R39 University of Delaware Cooperative Extension: https://www.udel.edu/academics/colleges/canr/cooperative-extension/fact-sheets/diagnosing-horticultural-plant-problems/

Possible causes in the CSV are differential *possibilities*, not proven primary causal agents for each species. Expert review and field validation are still necessary before claiming plant-wide diagnostic, treatment, or medicinal safety accuracy.
