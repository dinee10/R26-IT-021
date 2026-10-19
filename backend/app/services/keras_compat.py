"""Compatibility helpers for quality models exported by an older Keras build."""


def load_model_compatibly(model_path):
    from tensorflow import keras

    class LegacyVarianceScaling(keras.initializers.VarianceScaling):
        """Ignore the legacy inference-irrelevant `input_axes` config field."""

        def __init__(self, *args, input_axes=None, **kwargs):
            del input_axes
            super().__init__(*args, **kwargs)

    return keras.models.load_model(
        model_path,
        compile=False,
        custom_objects={"VarianceScaling": LegacyVarianceScaling},
    )
