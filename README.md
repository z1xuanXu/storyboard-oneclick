# ComfyUI Storyboard Oneclick

One-click ComfyUI workflow kit for turning story outlines into shot-list Excel files, Yunwu/Gemini still-image generation, and image-filled storyboards.

This repository is both a teaching site and a working local toolkit. It demonstrates the full process used to turn a short horror outline into:

- a detailed Excel storyboard
- reference-image prompts
- one ComfyUI workflow with connected reference inputs
- batch still-image generation
- a final Excel sheet with generated stills embedded by shot number

## Pages

- `index.html`: polished teaching homepage
- `prompts.html`: prompt-writing examples and formulas
- `.github/workflows/pages.yml`: GitHub Pages deployment workflow

## What This Repo Contains

- `custom_nodes/comfyui_yunwu_image_nodes`: reusable Yunwu/Gemini ComfyUI custom node
- `data/phone-key-story.json`: structured example story data
- `examples/workflows/phone_key_story_yunwu_template.json`: sanitized ComfyUI workflow
- `examples/phone_key_storyboard.xlsx`: sample storyboard workbook
- `assets/sample-stills`: compressed example stills for the teaching site
- `scripts`: reusable build, queue, and Excel-embedding scripts

## Quick Start

1. Install the custom node:

   ```powershell
   Copy-Item -Recurse .\custom_nodes\comfyui_yunwu_image_nodes F:\ComfyUI\ComfyUI-aki-v2\ComfyUI\custom_nodes\
   ```

2. Restart ComfyUI.

3. Install script dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

4. Build the storyboard workbook and workflow:

   ```powershell
   python .\scripts\build_storyboard_assets.py --story .\data\phone-key-story.json --out .\build
   ```

5. Set your API key only in the terminal environment:

   ```powershell
   $env:YUNWU_API_KEY="sk-your-key-here"
   ```

6. Queue the workflow:

   ```powershell
   python .\scripts\queue_comfyui_workflow.py --workflow .\build\phone_key_story_yunwu_template.json --comfy http://127.0.0.1:8188
   ```

7. Embed generated stills back into Excel:

   ```powershell
   python .\scripts\embed_outputs_to_excel.py --workbook .\build\phone_key_storyboard.xlsx --images F:\ComfyUI\ComfyUI-aki-v2\ComfyUI\output\phone_key_story --out .\build\phone_key_storyboard_with_images.xlsx
   ```

## Safety Notes

Do not commit API keys, generated history files, or private ComfyUI output metadata. The workflow in this repo is intentionally sanitized.

See `docs/DEPLOY.md` for GitHub Pages setup and `docs/WORKFLOW.md` for workflow design notes.
