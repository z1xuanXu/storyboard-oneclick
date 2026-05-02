# ComfyUI Storyboard Oneclick

One-click ComfyUI workflow kit for turning story outlines into shot-list Excel files, Yunwu/Gemini still-image generation, and image-filled storyboards.

## What This Repo Contains

- A GitHub Pages teaching site: `index.html` and `prompts.html`
- A reusable Yunwu/Gemini ComfyUI custom node: `custom_nodes/comfyui_yunwu_image_nodes`
- A sample horror short script dataset: `data/phone-key-story.json`
- A sanitized ComfyUI workflow: `examples/workflows/phone_key_story_yunwu_template.json`
- Python scripts for:
  - building an Excel storyboard and ComfyUI workflow
  - queueing the workflow through ComfyUI
  - embedding final stills back into the Excel sheet

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

