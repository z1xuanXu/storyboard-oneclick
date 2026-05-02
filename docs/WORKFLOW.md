# Workflow Design

The example workflow is organized around a production-friendly storyboard process.

## Reference Images

Generate references before shot stills:

- `REF01`: main character
- `REF02`: office desk
- `REF03`: apartment interior
- `REF04`: missing key
- `REF05`: wallet, ID card, bank cards, phone

These references are connected to shot nodes through `image_1`, `image_2`, and later image inputs.

## Shot Images

Each `Sxx` node corresponds to one row in the Excel storyboard.

The node prompt describes:

- aspect ratio and image size
- scene and time of day
- subject and action
- camera distance and angle
- composition and spatial layout
- lighting and color
- texture and style constraints

## Output Naming

Every generated image is saved with a stable prefix:

```text
phone_key_story/REF01
phone_key_story/S01
phone_key_story/S02
...
phone_key_story/S20
```

This makes it easy for `embed_outputs_to_excel.py` to find the newest still for each shot.

## Frontend Seed Widget Compatibility

Modern ComfyUI frontends may insert a seed control widget after the numeric `seed` value. This workflow keeps the widget order explicit:

```text
seed = -1
seed control = randomize
mime_type = image/png
```

This prevents `mime_type` from shifting into the wrong slot.

