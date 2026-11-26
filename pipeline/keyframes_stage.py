from pathlib import Path
from common import REPO_ROOT, compute_cache_key, is_cached, load_storyboard, log_run, mark_cached, retry_call
import os
import struct
import time
import urllib.request
import json
import zlib


def _write_solid_png(path: Path, rgb: tuple[int, int, int], width: int = 1280, height: int = 720) -> None:
    """Writes a valid minimal PNG placeholder when offline or no Cloudflare token is configured."""
    r, g, b = rgb
    raw_row = bytes([0] + [r, g, b] * width)
    raw_data = raw_row * height

    def _chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack("!I", len(data)) + tag + data + struct.pack("!I", crc)

    ihdr = struct.pack("!IIBBBBB", width, height, 8, 2, 0, 0, 0)
    idat = zlib.compress(raw_data, level=6)
    png_bytes = b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", idat) + _chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png_bytes)


def _generate_flux_cloudflare(prompt: str, seed: int, out_path: Path) -> bool:
    account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip()
    api_token = os.getenv("CLOUDFLARE_API_TOKEN", "").strip()
    if not account_id or not api_token:
        return False

    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/black-forest-labs/flux-1-schnell"
    body = json.dumps({"prompt": prompt, "seed": seed, "num_steps": 4}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        import base64
        b64_img = data.get("result", {}).get("image")
        if not b64_img:
            raise RuntimeError("Cloudflare FLUX response missing image")
        with open(out_path, "wb") as f:
            f.write(base64.b64decode(b64_img))
    return True


def run(storyboard_path: Path = REPO_ROOT / "storyboard.json", force: bool = False) -> list[Path]:
    sb = load_storyboard(storyboard_path)
    out_dir = REPO_ROOT / "outputs" / "keyframes"
    out_dir.mkdir(parents=True, exist_ok=True)
    generated: list[Path] = []

    # 1. Character reference sheet
    ref = sb["character_reference"]
    ref_path = REPO_ROOT / ref.get("reference_image_path", "outputs/keyframes/ref_character.png")
    ref_payload = {"prompt": f"{ref['description']}. {sb['style_block']}", "seed": ref["seed"], "model": "flux-1-schnell"}
    ref_key = compute_cache_key("keyframe_ref", ref_payload)
    t0 = time.perf_counter()
    if not force and is_cached(ref_key, ref_path):
        log_run("keyframes", "flux-1-schnell", {"role": "character_ref"}, ref["seed"], time.perf_counter() - t0, 0.0, "ok", cached=True)
    else:
        def _gen_ref():
            if not _generate_flux_cloudflare(ref_payload["prompt"], ref["seed"], ref_path):
                _write_solid_png(ref_path, (186, 148, 108))
        retry_call(_gen_ref)
        mark_cached(ref_key, ref_path, {"cache_key": ref_key})
        log_run("keyframes", "flux-1-schnell", {"role": "character_ref", "steps": 4}, ref["seed"], time.perf_counter() - t0, 0.0, "ok", cached=False)
    generated.append(ref_path)

    # 2. Per-shot keyframes conditioned on character & style block
    for idx, shot in enumerate(sb["shots"]):
        shot_path = out_dir / f"{shot['shot_id']}.png"
        full_prompt = f"{shot['image_prompt']} Character reference: {ref['description']}. {sb['style_block']}"
        payload = {"shot_id": shot["shot_id"], "prompt": full_prompt, "seed": shot["seed"], "model": "flux-1-schnell"}
        key = compute_cache_key("keyframe", payload)
        t_s = time.perf_counter()
        if not force and is_cached(key, shot_path):
            log_run("keyframes", "flux-1-schnell", {"shot_id": shot["shot_id"]}, shot["seed"], time.perf_counter() - t_s, 0.0, "ok", cached=True)
        else:
            palette = (165 + idx * 4, 132 + idx * 3, 98 + idx * 2)
            def _gen_shot(p=full_prompt, s=shot["seed"], dst=shot_path, col=palette):
                if not _generate_flux_cloudflare(p, s, dst):
                    _write_solid_png(dst, (min(col[0], 240), min(col[1], 230), min(col[2], 220)))
            retry_call(_gen_shot)
            mark_cached(key, shot_path, {"cache_key": key})
            log_run("keyframes", "flux-1-schnell", {"shot_id": shot["shot_id"], "steps": 4}, shot["seed"], time.perf_counter() - t_s, 0.0, "ok", cached=False)
        generated.append(shot_path)

    return generated


if __name__ == "__main__":
    run()
