import base64
import http.client
import io
import json
import os
import socket
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError

import numpy as np
import torch
from PIL import Image


GEMINI_BASE_URL = "https://yunwu.ai"
OPENAI_BASE_URL = "https://yunwu.ai"

ASPECT_RATIOS = [
    "auto",
    "1:1",
    "3:4",
    "4:3",
    "9:16",
    "16:9",
    "2:3",
    "3:2",
    "5:4",
    "4:5",
    "21:9",
    "9:21",
    "1:4",
    "4:1",
    "1:8",
    "8:1",
]

GEMINI_IMAGE_MODELS = [
    "gemini-2.5-flash-image",
    "gemini-2.5-flash-image-preview",
    "gemini-3-pro-image-preview",
    "gemini-3.1-flash-image-preview",
    "gemini-2.0-flash-exp-image-generation",
]

GEMINI_TEXT_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-3-pro-preview",
    "gemini-2.0-flash",
]

GPT_IMAGE_MODELS = [
    "gpt-image-1.5",
    "gpt-image-1",
    "gpt-image-1-mini",
    "gpt-image-1-all",
    "dall-e-3",
    "dall-e-2",
]


def _env_api_key(*names: str) -> str:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return ""


def _json_loads(value: str, label: str) -> Dict[str, Any]:
    value = (value or "").strip()
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} is not valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"{label} must be a JSON object")
    return parsed


def _clean_url(base_url: str) -> str:
    return (base_url or "").rstrip("/")


def _headers(api_key: str, bearer: bool = True) -> Dict[str, str]:
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}" if bearer else api_key
        headers["x-goog-api-key"] = api_key
    return headers


def _tensor_to_pil(image: torch.Tensor, index: int = 0) -> Image.Image:
    if image is None:
        raise ValueError("Missing image input")
    if image.ndim == 3:
        array = image.detach().cpu().numpy()
    else:
        array = image[index].detach().cpu().numpy()
    array = np.clip(array * 255.0, 0, 255).astype(np.uint8)
    return Image.fromarray(array).convert("RGB")


def _mask_to_pil(mask: torch.Tensor, size: Tuple[int, int], invert: bool) -> Image.Image:
    if mask.ndim == 3:
        array = mask[0].detach().cpu().numpy()
    else:
        array = mask.detach().cpu().numpy()
    array = np.clip(array, 0, 1)
    if invert:
        alpha = (array * 255.0).astype(np.uint8)
    else:
        alpha = ((1.0 - array) * 255.0).astype(np.uint8)
    return Image.fromarray(alpha, mode="L").resize(size)


def _pil_to_png_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _pil_to_b64(image: Image.Image) -> str:
    return base64.b64encode(_pil_to_png_bytes(image)).decode("utf-8")


def _tensor_to_inline_data(image: Optional[torch.Tensor], mime_type: str, max_images: int) -> List[Dict[str, Any]]:
    if image is None:
        return []
    count = 1 if image.ndim == 3 else min(int(image.shape[0]), max_images)
    parts = []
    for index in range(count):
        parts.append(
            {
                "inline_data": {
                    "mime_type": mime_type,
                    "data": _pil_to_b64(_tensor_to_pil(image, index)),
                }
            }
        )
    return parts


def _collect_inline_images(image_inputs: Dict[str, Optional[torch.Tensor]], mime_type: str, max_images: int) -> List[Dict[str, Any]]:
    parts: List[Dict[str, Any]] = []

    def sort_key(name: str) -> int:
        try:
            return int(name.rsplit("_", 1)[1])
        except (IndexError, ValueError):
            return 0

    for name in sorted(image_inputs, key=sort_key):
        image = image_inputs[name]
        if image is None:
            continue
        remaining = max_images - len(parts)
        if remaining <= 0:
            break
        parts.extend(_tensor_to_inline_data(image, mime_type, remaining))
    return parts


def _pil_to_tensor(image: Image.Image) -> torch.Tensor:
    array = np.array(image.convert("RGB")).astype(np.float32) / 255.0
    return torch.from_numpy(array)[None,]


def _empty_image() -> torch.Tensor:
    return torch.zeros((1, 64, 64, 3), dtype=torch.float32)


def _images_to_batch(images: List[Image.Image]) -> torch.Tensor:
    if not images:
        return _empty_image()
    tensors = [_pil_to_tensor(img) for img in images]
    first_h, first_w = tensors[0].shape[1], tensors[0].shape[2]
    normalized = []
    for tensor in tensors:
        if tensor.shape[1] != first_h or tensor.shape[2] != first_w:
            pil = Image.fromarray((tensor[0].numpy() * 255).astype(np.uint8))
            tensor = _pil_to_tensor(pil.resize((first_w, first_h), Image.LANCZOS))
        normalized.append(tensor)
    return torch.cat(normalized, dim=0)


def _decode_image_bytes(data: bytes) -> Image.Image:
    return Image.open(io.BytesIO(data)).convert("RGB")


def _decode_b64_image(value: str) -> Image.Image:
    if "," in value and value.strip().startswith("data:"):
        value = value.split(",", 1)[1]
    return _decode_image_bytes(base64.b64decode(value))


def _download_image(url: str) -> Image.Image:
    with urlrequest.urlopen(url, timeout=120) as response:
        return _decode_image_bytes(response.read())


def _extract_text(value: Any) -> str:
    texts: List[str] = []
    if isinstance(value, dict):
        if isinstance(value.get("text"), str):
            texts.append(value["text"])
        if isinstance(value.get("content"), str):
            texts.append(value["content"])
        for child in value.values():
            child_text = _extract_text(child)
            if child_text:
                texts.append(child_text)
    elif isinstance(value, list):
        for item in value:
            child_text = _extract_text(item)
            if child_text:
                texts.append(child_text)
    return "\n".join(dict.fromkeys(texts))


def _extract_images(value: Any) -> List[Image.Image]:
    images: List[Image.Image] = []
    if isinstance(value, dict):
        for key in ("b64_json", "bytesBase64Encoded", "image"):
            item = value.get(key)
            if isinstance(item, str):
                try:
                    images.append(_decode_b64_image(item))
                except Exception:
                    pass
        for key in ("url", "image_url"):
            item = value.get(key)
            if isinstance(item, str) and item.startswith(("http://", "https://")):
                images.append(_download_image(item))
        for key in ("inlineData", "inline_data"):
            inline = value.get(key)
            if isinstance(inline, dict) and isinstance(inline.get("data"), str):
                images.append(_decode_b64_image(inline["data"]))
        for child in value.values():
            images.extend(_extract_images(child))
    elif isinstance(value, list):
        for item in value:
            images.extend(_extract_images(item))
    return images


def _request_json(method: str, url: str, api_key: str, body: Dict[str, Any]) -> Dict[str, Any]:
    data = json.dumps(body).encode("utf-8")
    req = urlrequest.Request(
        url,
        data=data,
        method=method,
        headers={**_headers(api_key), "Content-Type": "application/json"},
    )
    last_error: Optional[BaseException] = None
    for attempt in range(3):
        try:
            with urlrequest.urlopen(req, timeout=300) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            if exc.code not in (408, 429, 500, 502, 503, 504) or attempt == 2:
                raise RuntimeError(f"HTTP {exc.code} from {url}: {detail}") from exc
            last_error = exc
        except (URLError, TimeoutError, socket.timeout, http.client.IncompleteRead) as exc:
            if attempt == 2:
                raise RuntimeError(f"Request failed for {url}: {exc}") from exc
            last_error = exc
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"Request failed for {url}: {last_error}")


def _request_multipart(
    url: str,
    api_key: str,
    fields: Dict[str, Any],
    files: Union[Dict[str, Any], List[Tuple[str, Any]]],
) -> Dict[str, Any]:
    boundary = f"----ComfyUIYunwu{uuid.uuid4().hex}"
    body = io.BytesIO()

    def write(value: Union[str, bytes]) -> None:
        body.write(value.encode("utf-8") if isinstance(value, str) else value)

    for key, value in fields.items():
        write(f"--{boundary}\r\n")
        write(f'Content-Disposition: form-data; name="{key}"\r\n\r\n')
        write(str(value))
        write("\r\n")

    file_items = files.items() if isinstance(files, dict) else files
    for key, file_value in file_items:
        filename, content, mime_type = file_value
        write(f"--{boundary}\r\n")
        write(f'Content-Disposition: form-data; name="{key}"; filename="{filename}"\r\n')
        write(f"Content-Type: {mime_type}\r\n\r\n")
        write(content)
        write("\r\n")
    write(f"--{boundary}--\r\n")

    req = urlrequest.Request(
        url,
        data=body.getvalue(),
        method="POST",
        headers={**_headers(api_key), "Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    try:
        with urlrequest.urlopen(req, timeout=300) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from {url}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Request failed for {url}: {exc}") from exc


def _merge_dict(target: Dict[str, Any], extra: Dict[str, Any]) -> Dict[str, Any]:
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _merge_dict(target[key], value)
        else:
            target[key] = value
    return target


class YunwuGeminiImage:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": "A clean product photo of a glass teapot on a wooden table"}),
                "api_key": ("STRING", {"default": _env_api_key("YUNWU_API_KEY", "GEMINI_API_KEY")}),
                "base_url": ("STRING", {"default": GEMINI_BASE_URL}),
                "model": ("STRING", {"default": "gemini-2.5-flash-image"}),
                "response_modalities": ("STRING", {"default": "TEXT,IMAGE"}),
                "aspect_ratio": (ASPECT_RATIOS,),
                "image_size": (["auto", "0.5K", "1K", "2K", "4K", "512"],),
                "temperature": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 2.0, "step": 0.05}),
                "top_p": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01}),
                "top_k": ("INT", {"default": 0, "min": 0, "max": 1000}),
                "candidate_count": ("INT", {"default": 1, "min": 1, "max": 8}),
                "max_output_tokens": ("INT", {"default": 0, "min": 0, "max": 65536}),
                "seed": ("INT", {"default": -1, "min": -1, "max": 2147483647}),
                "mime_type": ("STRING", {"default": "image/png"}),
                "extra_generation_config_json": ("STRING", {"multiline": True, "default": "{}"}),
                "extra_body_json": ("STRING", {"multiline": True, "default": "{}"}),
            },
            "optional": {f"image_{index}": ("IMAGE",) for index in range(1, 15)},
        }

    RETURN_TYPES = ("IMAGE", "STRING", "STRING")
    RETURN_NAMES = ("images", "text", "raw_json")
    FUNCTION = "run"
    CATEGORY = "Yunwu API/Gemini"

    def run(
        self,
        prompt,
        api_key,
        base_url,
        model,
        response_modalities,
        aspect_ratio,
        image_size,
        temperature,
        top_p,
        top_k,
        candidate_count,
        max_output_tokens,
        seed,
        mime_type,
        extra_generation_config_json,
        extra_body_json,
        **image_inputs,
    ):
        parts = [{"text": prompt}]
        parts.extend(_collect_inline_images(image_inputs, mime_type, 14))

        generation_config: Dict[str, Any] = {
            "responseModalities": [item.strip() for item in response_modalities.split(",") if item.strip()],
            "temperature": temperature,
            "topP": top_p,
            "candidateCount": candidate_count,
        }
        if top_k > 0:
            generation_config["topK"] = top_k
        if max_output_tokens > 0:
            generation_config["maxOutputTokens"] = max_output_tokens
        if seed >= 0:
            generation_config["seed"] = seed
        image_config = {}
        if aspect_ratio != "auto":
            image_config["aspectRatio"] = aspect_ratio
        if image_size != "auto":
            image_config["imageSize"] = image_size
        if image_config:
            generation_config["imageConfig"] = image_config
        _merge_dict(generation_config, _json_loads(extra_generation_config_json, "extra_generation_config_json"))

        body = {"contents": [{"role": "user", "parts": parts}], "generationConfig": generation_config}
        _merge_dict(body, _json_loads(extra_body_json, "extra_body_json"))
        url = f"{_clean_url(base_url)}/v1beta/models/{model}:generateContent"
        raw = _request_json("POST", url, api_key, body)
        images = _extract_images(raw)
        return (_images_to_batch(images), _extract_text(raw), json.dumps(raw, ensure_ascii=False, indent=2))


class YunwuGeminiImageUnderstand:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": "Describe this image in detail."}),
                "api_key": ("STRING", {"default": _env_api_key("YUNWU_API_KEY", "GEMINI_API_KEY")}),
                "base_url": ("STRING", {"default": GEMINI_BASE_URL}),
                "model": ("STRING", {"default": "gemini-2.5-flash"}),
                "temperature": ("FLOAT", {"default": 0.4, "min": 0.0, "max": 2.0, "step": 0.05}),
                "top_p": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01}),
                "thinking_budget": ("INT", {"default": 0, "min": 0, "max": 32768}),
                "include_thoughts": ("BOOLEAN", {"default": False}),
                "mime_type": ("STRING", {"default": "image/png"}),
                "enable_google_search": ("BOOLEAN", {"default": False}),
                "extra_generation_config_json": ("STRING", {"multiline": True, "default": "{}"}),
                "extra_body_json": ("STRING", {"multiline": True, "default": "{}"}),
            },
            "optional": {"image": ("IMAGE",)},
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("text", "raw_json")
    FUNCTION = "run"
    CATEGORY = "Yunwu API/Gemini"

    def run(
        self,
        prompt,
        api_key,
        base_url,
        model,
        temperature,
        top_p,
        thinking_budget,
        include_thoughts,
        mime_type,
        enable_google_search,
        extra_generation_config_json,
        extra_body_json,
        image=None,
    ):
        parts = [{"text": prompt}]
        parts.extend(_tensor_to_inline_data(image, mime_type, 14))
        generation_config: Dict[str, Any] = {"temperature": temperature, "topP": top_p}
        if thinking_budget > 0 or include_thoughts:
            generation_config["thinkingConfig"] = {
                "thinkingBudget": thinking_budget,
                "includeThoughts": include_thoughts,
            }
        _merge_dict(generation_config, _json_loads(extra_generation_config_json, "extra_generation_config_json"))
        body: Dict[str, Any] = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": generation_config,
        }
        if enable_google_search:
            body["tools"] = [{"googleSearch": {}}]
        _merge_dict(body, _json_loads(extra_body_json, "extra_body_json"))
        url = f"{_clean_url(base_url)}/v1beta/models/{model}:generateContent"
        raw = _request_json("POST", url, api_key, body)
        return (_extract_text(raw), json.dumps(raw, ensure_ascii=False, indent=2))


class YunwuGeminiImagenPredict:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": "Robot holding a red skateboard"}),
                "api_key": ("STRING", {"default": _env_api_key("YUNWU_API_KEY", "GEMINI_API_KEY")}),
                "base_url": ("STRING", {"default": GEMINI_BASE_URL}),
                "model": ("STRING", {"default": "imagen-4.0-ultra-generate-001"}),
                "sample_count": ("INT", {"default": 1, "min": 1, "max": 8}),
                "aspect_ratio": (ASPECT_RATIOS,),
                "person_generation": (["auto", "allow_adult", "allow_all", "dont_allow"],),
                "negative_prompt": ("STRING", {"multiline": True, "default": ""}),
                "seed": ("INT", {"default": -1, "min": -1, "max": 2147483647}),
                "extra_parameters_json": ("STRING", {"multiline": True, "default": "{}"}),
                "extra_body_json": ("STRING", {"multiline": True, "default": "{}"}),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("images", "raw_json")
    FUNCTION = "run"
    CATEGORY = "Yunwu API/Gemini"

    def run(
        self,
        prompt,
        api_key,
        base_url,
        model,
        sample_count,
        aspect_ratio,
        person_generation,
        negative_prompt,
        seed,
        extra_parameters_json,
        extra_body_json,
    ):
        parameters: Dict[str, Any] = {"sampleCount": sample_count}
        if aspect_ratio != "auto":
            parameters["aspectRatio"] = aspect_ratio
        if person_generation != "auto":
            parameters["personGeneration"] = person_generation
        if negative_prompt:
            parameters["negativePrompt"] = negative_prompt
        if seed >= 0:
            parameters["seed"] = seed
        _merge_dict(parameters, _json_loads(extra_parameters_json, "extra_parameters_json"))
        body = {"instances": [{"prompt": prompt}], "parameters": parameters}
        _merge_dict(body, _json_loads(extra_body_json, "extra_body_json"))
        url = f"{_clean_url(base_url)}/v1beta/models/{model}:predict"
        raw = _request_json("POST", url, api_key, body)
        return (_images_to_batch(_extract_images(raw)), json.dumps(raw, ensure_ascii=False, indent=2))


class YunwuGPTImageGenerate:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": "A cute tiny pig, studio lighting"}),
                "api_key": ("STRING", {"default": _env_api_key("YUNWU_API_KEY", "OPENAI_API_KEY")}),
                "base_url": ("STRING", {"default": OPENAI_BASE_URL}),
                "model": ("STRING", {"default": "gpt-image-1"}),
                "n": ("INT", {"default": 1, "min": 1, "max": 10}),
                "size": (["auto", "1024x1024", "1536x1024", "1024x1536", "1792x1024", "1024x1792", "512x512", "256x256"],),
                "quality": (["auto", "low", "medium", "high", "standard", "hd"],),
                "background": (["auto", "transparent", "opaque"],),
                "moderation": (["auto", "low"],),
                "response_format": (["auto", "b64_json", "url"],),
                "output_format": (["auto", "png", "jpeg", "webp"],),
                "output_compression": ("INT", {"default": -1, "min": -1, "max": 100}),
                "user": ("STRING", {"default": ""}),
                "extra_body_json": ("STRING", {"multiline": True, "default": "{}"}),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("images", "raw_json")
    FUNCTION = "run"
    CATEGORY = "Yunwu API/GPT Image"

    def run(
        self,
        prompt,
        api_key,
        base_url,
        model,
        n,
        size,
        quality,
        background,
        moderation,
        response_format,
        output_format,
        output_compression,
        user,
        extra_body_json,
    ):
        body: Dict[str, Any] = {"prompt": prompt, "model": model, "n": n}
        for key, value in {
            "size": size,
            "quality": quality,
            "background": background,
            "moderation": moderation,
            "response_format": response_format,
            "output_format": output_format,
        }.items():
            if value != "auto":
                body[key] = value
        if output_compression >= 0:
            body["output_compression"] = output_compression
        if user:
            body["user"] = user
        _merge_dict(body, _json_loads(extra_body_json, "extra_body_json"))
        url = f"{_clean_url(base_url)}/v1/images/generations"
        raw = _request_json("POST", url, api_key, body)
        return (_images_to_batch(_extract_images(raw)), json.dumps(raw, ensure_ascii=False, indent=2))


class YunwuGPTImageEdit:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "prompt": ("STRING", {"multiline": True, "default": "Add a small llama next to the subject."}),
                "api_key": ("STRING", {"default": _env_api_key("YUNWU_API_KEY", "OPENAI_API_KEY")}),
                "base_url": ("STRING", {"default": OPENAI_BASE_URL}),
                "model": ("STRING", {"default": "gpt-image-1"}),
                "n": ("INT", {"default": 1, "min": 1, "max": 10}),
                "size": (["auto", "1024x1024", "1536x1024", "1024x1536", "512x512", "256x256"],),
                "quality": (["auto", "low", "medium", "high", "standard"],),
                "background": (["auto", "transparent", "opaque"],),
                "moderation": (["auto", "low"],),
                "aspect_ratio": (ASPECT_RATIOS,),
                "response_format": (["auto", "b64_json", "url"],),
                "output_format": (["auto", "png", "jpeg", "webp"],),
                "output_compression": ("INT", {"default": -1, "min": -1, "max": 100}),
                "mask_invert": ("BOOLEAN", {"default": False}),
                "user": ("STRING", {"default": ""}),
                "extra_body_json": ("STRING", {"multiline": True, "default": "{}"}),
            },
            "optional": {
                "image_2": ("IMAGE",),
                "mask": ("MASK",),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("images", "raw_json")
    FUNCTION = "run"
    CATEGORY = "Yunwu API/GPT Image"

    def run(
        self,
        image,
        prompt,
        api_key,
        base_url,
        model,
        n,
        size,
        quality,
        background,
        moderation,
        aspect_ratio,
        response_format,
        output_format,
        output_compression,
        mask_invert,
        user,
        extra_body_json,
        image_2=None,
        mask=None,
    ):
        fields: Dict[str, Any] = {"prompt": prompt, "model": model, "n": str(n)}
        for key, value in {
            "size": size,
            "quality": quality,
            "background": background,
            "moderation": moderation,
            "aspect_ratio": aspect_ratio,
            "response_format": response_format,
            "output_format": output_format,
        }.items():
            if value != "auto":
                fields[key] = value
        if output_compression >= 0:
            fields["output_compression"] = str(output_compression)
        if user:
            fields["user"] = user
        fields.update({key: json.dumps(value) if isinstance(value, (dict, list)) else str(value) for key, value in _json_loads(extra_body_json, "extra_body_json").items()})

        files: List[Tuple[str, Any]] = [("image", ("image_1.png", _pil_to_png_bytes(_tensor_to_pil(image)), "image/png"))]
        if image_2 is not None:
            files.append(("image", ("image_2.png", _pil_to_png_bytes(_tensor_to_pil(image_2)), "image/png")))
        if mask is not None:
            base_image = _tensor_to_pil(image)
            alpha = _mask_to_pil(mask, base_image.size, mask_invert)
            rgba = base_image.convert("RGBA")
            rgba.putalpha(alpha)
            files.append(("mask", ("mask.png", _pil_to_png_bytes(rgba), "image/png")))

        url = f"{_clean_url(base_url)}/v1/images/edits"
        raw = _request_multipart(url, api_key, fields, files)
        return (_images_to_batch(_extract_images(raw)), json.dumps(raw, ensure_ascii=False, indent=2))


class YunwuGPTImageVariation:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "api_key": ("STRING", {"default": _env_api_key("YUNWU_API_KEY", "OPENAI_API_KEY")}),
                "base_url": ("STRING", {"default": OPENAI_BASE_URL}),
                "model": ("STRING", {"default": "dall-e-2"}),
                "n": ("INT", {"default": 1, "min": 1, "max": 10}),
                "size": (["1024x1024", "512x512", "256x256"],),
                "response_format": (["b64_json", "url"],),
                "user": ("STRING", {"default": ""}),
                "extra_body_json": ("STRING", {"multiline": True, "default": "{}"}),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("images", "raw_json")
    FUNCTION = "run"
    CATEGORY = "Yunwu API/GPT Image"

    def run(self, image, api_key, base_url, model, n, size, response_format, user, extra_body_json):
        fields: Dict[str, Any] = {"model": model, "n": str(n), "size": size, "response_format": response_format}
        if user:
            fields["user"] = user
        fields.update({key: json.dumps(value) if isinstance(value, (dict, list)) else str(value) for key, value in _json_loads(extra_body_json, "extra_body_json").items()})
        files = {"image": ("image.png", _pil_to_png_bytes(_tensor_to_pil(image)), "image/png")}
        url = f"{_clean_url(base_url)}/v1/images/variations"
        raw = _request_multipart(url, api_key, fields, files)
        return (_images_to_batch(_extract_images(raw)), json.dumps(raw, ensure_ascii=False, indent=2))


NODE_CLASS_MAPPINGS = {
    "YunwuGeminiImage": YunwuGeminiImage,
    "YunwuGeminiImageUnderstand": YunwuGeminiImageUnderstand,
    "YunwuGeminiImagenPredict": YunwuGeminiImagenPredict,
    "YunwuGPTImageGenerate": YunwuGPTImageGenerate,
    "YunwuGPTImageEdit": YunwuGPTImageEdit,
    "YunwuGPTImageVariation": YunwuGPTImageVariation,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "YunwuGeminiImage": "Yunwu Gemini Image Generate/Edit",
    "YunwuGeminiImageUnderstand": "Yunwu Gemini Image Understand",
    "YunwuGeminiImagenPredict": "Yunwu Imagen Predict",
    "YunwuGPTImageGenerate": "Yunwu GPT Image Generate",
    "YunwuGPTImageEdit": "Yunwu GPT Image Edit",
    "YunwuGPTImageVariation": "Yunwu Image Variation",
}
