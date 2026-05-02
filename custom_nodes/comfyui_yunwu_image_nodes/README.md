# ComfyUI Yunwu Image Nodes

Custom ComfyUI nodes for the image-related API sections in the exported module
Markdown file under `C:\Users\xuzix\Downloads`.

## Nodes

- `Yunwu Gemini Image Generate/Edit`
  - Gemini native `generateContent` image generation and editing.
  - Supports text-to-image, image-to-image, and multi-image reference/edit
    flows.
  - Provides `image_1` through `image_14`, matching Gemini's documented
    multi-image input limit.
  - Exposes `model`, `response_modalities`, `aspect_ratio`, `image_size`,
    sampling parameters, seed, MIME type, and JSON override fields.
- `Yunwu Gemini Image Understand`
  - Gemini native image understanding or text response with optional image input.
  - Supports temperature, top-p, thinking config, Google Search tool toggle, and
    JSON override fields.
- `Yunwu Imagen Predict`
  - Imagen-style `/v1beta/models/{model}:predict`.
  - Exposes prompt, sample count, aspect ratio, person generation, negative
    prompt, seed, and JSON override fields.
- `Yunwu GPT Image Generate`
  - OpenAI-compatible `/v1/images/generations`.
  - Exposes model, `n`, size, quality, background, moderation, response format,
    output format, output compression, user, and JSON override fields.
- `Yunwu GPT Image Edit`
  - OpenAI-compatible `/v1/images/edits`.
  - Supports one or two input images, optional mask, aspect ratio, and the image
    generation controls above.
- `Yunwu Image Variation`
  - OpenAI-compatible `/v1/images/variations`.
  - This endpoint is currently DALL-E 2-only in OpenAI's public API, but is
    included because the Images API has three endpoint documents.

## Installation

Copy the `comfyui_yunwu_image_nodes` folder into:

```text
ComfyUI/custom_nodes/
```

Then restart ComfyUI.

## API Keys

Each node has an `api_key` input. You can type it in the node or set one of
these environment variables before starting ComfyUI:

```text
YUNWU_API_KEY
GEMINI_API_KEY
OPENAI_API_KEY
```

The default `base_url` is `https://yunwu.ai`, matching the exported module.
Change it if your proxy or provider uses another base URL.

## Extra Parameters

Use the `extra_*_json` inputs to pass parameters not exposed as first-class
widgets. These values are merged into the request body or config and take
precedence over widget values.
