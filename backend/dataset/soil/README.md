# Soil image dataset

The images in this folder were extracted from the user-provided `archive.zip`.
The archive contains four labeled classes and separate training and test sets,
but no source citation, dataset card, or license file. Verify the original
dataset's terms before redistributing this repository or using the images
outside this project.

## Structure

```text
soil/
  train/
  validation/
  test/
```

The archive's `test` images were exact duplicates of images in its `Train`
folders, so keeping the supplied split would cause test leakage. Exact
duplicates were removed and the unique images from the source `Train` folders
were deterministically divided per class into approximately 70% `train`,
15% `validation`, and 15% `test`. No image hash occurs in more than one split.

Class labels correspond to the archive's folder names:

```text
Alluvial soil/
Black Soil/
Clay soil/
Red soil/
```

## Training

Install `backend/requirements.txt`, then run:

```powershell
Set-Location backend
python -m crs_soil.crs_soil_training
```

Training uses MobileNetV2 transfer learning and writes `soil_model.keras`,
`soil_labels.json`, `soil_model_metadata.json`, and `soil_feature_bank.npz`
next to the training code. The feature bank supports rejection of uploads that
do not resemble the supported soil classes.

The classifier accepts alluvial, black, clay, and red soil. Uploads that do not
match the soil model's learned image features are rejected with instructions to
upload a clear, close-up soil photo. This is a best-effort out-of-distribution
check, not a guarantee that every unrelated image will be recognized.

Synthetic non-soil illustrations supplied for rejection testing are not used for
training and do not establish performance on real photos of people, animals,
flowers, roots, or trees.
