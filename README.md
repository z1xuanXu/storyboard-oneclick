这个教学页面也是由AI制作的，大致看了下，有些功能聊胜于无，故直接口述一下比较重要的部分

关于将API文档给CODEX阅读的部分，你需要这么和AI说
 ```powershell
   阅读这个文档，在目录中寻找【这里填入你要接的内容，或者是文档中需要功能的关键词】有关的文档，帮我将每个功能写成一个comfyui中的节点，并且可以调节任何可供调节的参数，并且将这个节点放入comfyui的文件夹，具体目录是【目录】
   ```

关于让AI一键开始操作的部分
```powershell
   我现在会给你一个故事大纲或者脚本，你需要使用这个脚本一键生图，并且图生视频，操作如下。
1.当comfyui没打开的时候，打开这个项目文件夹下的comfyui，如果不在这个文件夹，那么我会填写这个位置：【】
2.当故事没有具体的脚本时，执行这个步骤，如果已经有具体的脚本，那么根据这个要求优化 *但是不能改变剧本本来的意思和重要内容：
 （1）帮我细化这个视频大纲，制作成一个详细的视频脚本，excel格式文件，每段画面切的更细致，细致到需要多少次剪辑和分镜都要清楚。
      根据你的判断，一个镜头画面要包含哪几个切镜头，哪几个画面，细化成一个画面一个镜号，并且将画面详细描述，直到可以直接放在
      ai中生成单帧图的水平，每个单帧图提示词需要包含画面质感的描写，构图的描写，视角的描写，画面的各个部分分别需要有哪些内容
      的描写，并且有一列是根据单帧图生成视频的提示词，考虑到不是每个单帧图都能单独生成提示词，这一列你可以根据需求，哪几个单
      帧图组合起来，写一份完整的图生视频提示词，包括运镜，光线，画面质感，速度，画面详细构图，以及画面内的具体内容。将这一切
      生成execl导出。
3.接下来，根据这个脚本，将里面的单帧图生成提示词按照顺序分类，每一个单独放到comfyui中的一个文本框中，作为提示词使用，并且后面
  链接生图所需节点，使用【Yunwu Gemini Image Generate/Edit】节点。以此将每个单帧图提示词生图，所有节点使用统一的分辨率和比例。
  请注意，在生成剧本单帧图的时候，明确每个镜头单帧图之间的联系，即有哪些图是需要一个场景的不同角度，全片都要引用哪些同一个角色
  和物品，将有关联的图片使用同一参考图输入（同一场景，同一物品，同一角色），并且你需要根据剧情中贯穿的物品，提前先生成那个物品
  的参考图。
4.接下来，你需要从comfyui中保存最终每个镜头号的单帧图，将他们按照顺序贴到excel表格中的位置。并且将所有图片根据镜号和使用类型
整理成一个文件夹。
5.测试阶段不用进行作图步骤
   ```





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
