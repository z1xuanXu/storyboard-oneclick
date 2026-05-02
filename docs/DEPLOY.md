# Deployment Guide

This repository is designed to be published as a GitHub Pages site and used as a local ComfyUI workflow kit.

## Recommended GitHub Repository Settings

- Repository name: `comfyui-storyboard-oneclick`
- Visibility: `Public`
- Description: `One-click ComfyUI workflow kit for turning story outlines into shot-list Excel files, Yunwu/Gemini still-image generation, and image-filled storyboards.`

## Enable GitHub Pages

After pushing to GitHub:

1. Open the repository on GitHub.
2. Go to `Settings -> Pages`.
3. Set source to `GitHub Actions`.
4. Push to `main`, or run the `Deploy GitHub Pages` workflow manually.

The static site entry is `index.html`; the prompt example page is `prompts.html`.

## Local ComfyUI Setup

Copy the included custom node into your ComfyUI install:

```powershell
Copy-Item -Recurse .\custom_nodes\comfyui_yunwu_image_nodes `
  F:\ComfyUI\ComfyUI-aki-v2\ComfyUI\custom_nodes\
```

Restart ComfyUI, then confirm the node appears as:

```text
Yunwu Gemini Image Generate/Edit
```

## API Key Handling

Never commit real keys. Use an environment variable before queueing:

```powershell
$env:YUNWU_API_KEY="sk-your-key-here"
```

The workflow template in `examples/workflows/phone_key_story_yunwu_template.json` is intentionally sanitized.

