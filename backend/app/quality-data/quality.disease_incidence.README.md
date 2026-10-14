# Evidence-aligned plant symptom frequency rules (Revision 2)

## Changes from the previous CSV
- Removed the **invented** 10/30/60/80% boundaries.
- Uses a **published leaf-symptom-frequency grading approach** with boundaries at **0 / 25 / 50 / 75 / 100%**, adapted from an ICAR research scale (R29, URL below). These are **descriptive sampled-leaf frequency brackets**, not scientifically established treatment action thresholds for neem, betel, gotukola, holy basil, akkapana, or curry leaf.
- Changed 6 descriptive stages per class to 5, so 29 Model 2 classes x 5 = 145 rows. **Do not imply a verified disease-specific 'threat level' or that 'Very High' means the plant is necessarily unsafe or dying.**
- Added source-level caveats, published_scale_reference_id/url, sample_count_if_25, confirmed-condition override, and separate explicit status for percent thresholds versus treatment.
- Contains 35 references in separate `plant_disease_references_revised.csv` (28 previous + 7 additional references). URLs in each rule are provided for inspection; some references are general guidance or on related crops, NOT disease-specific validation.

## Percentage examples (25 UNIQUE accepted leaves from the SAME plant, sampled across different regions)
- 0/25 = 0% : None Detected in submitted samples
- 1/25 = 4% : Low observed symptom frequency (descriptive category; **not inherently low biological risk**)
- 7/25 = 28% : Moderate observed frequency
- 13/25 = 52% : High observed frequency
- 23/25 = 92% : Very High observed frequency (descriptive, NOT plant tissue damaged %)

## Rules for using the CSV in the app
1. Run a species check, image-quality filtering, Model 2 prediction, and uncertainty/duplicate screening per sample. Count VALID unique leaves in the denominator. Avoid combining repeated views of one leaf as separate observations.
2. For each Model 2 condition `class`, calculate frequency = 100 * matching_class_predictions / valid_unique_sample_count. Classifier is single-label; two true conditions on the same leaf may be undercounted.
3. Find the condition row whose min/max percentage range matches (respect min_exclusive and max_inclusive). All 0–100% have exactly one matching row for each class.
4. **Display the raw fraction (e.g., 3/25 = 12%) prominently**; the category is an optional descriptive visual shorthand, not a diagnosis or clinical severity determination.
5. `confirmed_condition_action_override` takes precedence over the grade-based action *after an appropriate diagnostic confirmation*. For example, confirmed betel leaf rot and confirmed basil downy mildew warrant attention at any frequency. Only one image/ML prediction is not itself confirmation.
6. Classes marked `symptom_frequency_only_NOT_infectious_disease_incidence` (yellowing, drying, phosphorus deficiency, anthocyanin pigmentation) must never be described as contagious-disease prevalence or treated with fungicide by default.
7. For `Leaf_Miners_Powdery_Mildew`, do **not** count the joint class as either individual leafminers or powdery mildew unless a separate verified multi-label rule is developed.
8. No fixed 25-leaf sample is statistically representative of the whole tree without a defensible sampling scheme. Sample across plant regions and report only 'among sampled leaves.' A 0/25 result does NOT mean whole-plant absence. Confidence intervals may quantify binomial sampling uncertainty but do not correct sampling bias/model error.
9. Do not automatically apply chemical pesticide/fungicide treatments. Recommendations are general cultural care or seek-expert/confirmation prompts. Any real treatments require species, pathogen, locally registered product, legal label, harvest interval, and medicinal-product residue review.
10. All treatment recommendations are **not separately validated for each incidence bracket**; source-informed suggestions have not been tested against these exact cutoffs. Independent expert review and prospective field validation are required before claiming biological threat levels or evidence-based treatment thresholds.

## What R29 actually validates
ICAR's original viral disease response grading uses **percent of leaves with symptoms**, with <=25%, 26-50%, 51-75%, >75% categories. It is a crop disease screening/response metric and **not a universal disease-incidence-to-treatment scale**. It is closer to the user's leaf-count percentage method than disease *tissue-area* scales. We borrow its **reporting cut points**, not its resistance meanings, risk labels or treatment implications.

R29 https://icar-nsri.res.in/pdfdoc/TechnicalProgrammeAICRP2021_22.pdf (see PDF page index 44)
R30 https://doi.org/10.1094/PDIS-03-15-0319-RE (incidence vs severity)
R31 https://doi.org/10.1007/s42360-018-0076-1 (betel tissue-severity study uses 25 sampled leaves, *different measure*)
R32 https://doi.org/10.1094/PHYTO-01-17-0017-FI (holy basil host difference)
R33 https://extension.umn.edu/agriculture/specialty-crops/vegetable-farming/disease-management/basil-downy-mildew (sweet-basil management example)
R34 https://extension.usu.edu/vegetableguide/ipm-practices/thresholds-for-treatment (pest- and crop-specific action thresholds)
R35 https://indianjournals.com/article/ijpp1-40-4-015 (betel leaf/foot rot management evidence)
