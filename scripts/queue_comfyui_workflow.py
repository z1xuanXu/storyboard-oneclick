import argparse
import json
import os
import time
from pathlib import Path

import requests


YUNWU_REQUIRED = [
    "prompt",
    "api_key",
    "base_url",
    "model",
    "response_modalities",
    "aspect_ratio",
    "image_size",
    "temperature",
    "top_p",
    "top_k",
    "candidate_count",
    "max_output_tokens",
    "seed",
    "mime_type",
    "extra_generation_config_json",
    "extra_body_json",
]


def widget_value(values, index):
    has_seed_control = len(values) >= 17 and values[13] != "image/png"
    if has_seed_control and index > 12:
        return values[index + 1]
    return values[index]


def convert_to_prompt(workflow, api_key):
    links_by_target = {}
    for link in workflow["links"]:
        link_id, source_id, source_slot, target_id, target_slot, _ = link
        links_by_target[(target_id, target_slot)] = [str(source_id), source_slot, link_id]

    prompt = {}
    for node in workflow["nodes"]:
        if node["type"] == "YunwuGeminiImage":
            values = list(node["widgets_values"])
            inputs = {}
            for index, name in enumerate(YUNWU_REQUIRED):
                inputs[name] = widget_value(values, index)
            inputs["api_key"] = api_key
            for input_index in range(14):
                linked = links_by_target.get((node["id"], input_index))
                if linked:
                    inputs[f"image_{input_index + 1}"] = [linked[0], linked[1]]
            prompt[str(node["id"])] = {"class_type": node["type"], "inputs": inputs}

        if node["type"] == "SaveImage":
            linked = links_by_target.get((node["id"], 0))
            if not linked:
                continue
            prompt[str(node["id"])] = {
                "class_type": "SaveImage",
                "inputs": {
                    "images": [linked[0], linked[1]],
                    "filename_prefix": node["widgets_values"][0],
                },
            }
    return prompt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflow", required=True, type=Path)
    parser.add_argument("--comfy", default="http://127.0.0.1:8188")
    parser.add_argument("--wait", action="store_true", default=True)
    args = parser.parse_args()

    api_key = os.environ.get("YUNWU_API_KEY")
    if not api_key:
        raise SystemExit("Set YUNWU_API_KEY in your shell before queueing.")

    workflow = json.loads(args.workflow.read_text(encoding="utf-8-sig"))
    prompt = convert_to_prompt(workflow, api_key)
    response = requests.post(
        f"{args.comfy}/prompt",
        json={"prompt": prompt, "client_id": "storyboard-oneclick", "extra_data": {"extra_pnginfo": {"workflow": workflow}}},
        timeout=30,
    )
    response.raise_for_status()
    prompt_id = response.json()["prompt_id"]
    print({"prompt_id": prompt_id})

    if not args.wait:
        return

    while True:
        history = requests.get(f"{args.comfy}/history/{prompt_id}", timeout=10).json()
        if prompt_id in history:
            item = history[prompt_id]
            status = item.get("status", {})
            print({"status": status.get("status_str"), "completed": status.get("completed"), "outputs": len(item.get("outputs", {}))})
            if status.get("status_str") != "success":
                for message in status.get("messages", []):
                    if message[0] == "execution_error":
                        print({"error_node": message[1].get("node_id"), "error": message[1].get("exception_message")})
            return
        time.sleep(5)


if __name__ == "__main__":
    main()

