import os
import sys

CHECKPOINTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "third_party", "index-tts", "checkpoints")
HF_CACHE = os.path.join(CHECKPOINTS_DIR, "hf_cache")
os.environ["HF_HUB_CACHE"] = HF_CACHE
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

os.makedirs(HF_CACHE, exist_ok=True)

print(f"HF_CACHE: {HF_CACHE}")
print(f"HF_ENDPOINT: {os.environ['HF_ENDPOINT']}")
print()

from huggingface_hub import hf_hub_download, list_repo_files


def download_repo_files(repo_id):
    print(f"[下载] {repo_id} (逐个文件)")
    try:
        files = list_repo_files(repo_id)
    except Exception as e:
        print(f"  => 获取文件列表失败: {e}")
        return

    for filename in files:
        print(f"  -> {filename} ...", end=" ", flush=True)
        try:
            path = hf_hub_download(repo_id, filename=filename, cache_dir=HF_CACHE)
            print(f"OK")
        except Exception as e:
            print(f"失败: {e}")


def download_file(repo_id, filename):
    print(f"[下载] {repo_id} / {filename} ...", end=" ", flush=True)
    try:
        path = hf_hub_download(repo_id, filename=filename, cache_dir=HF_CACHE)
        print(f"OK")
    except Exception as e:
        print(f"失败: {e}")


download_repo_files("facebook/w2v-bert-2.0")
download_file("amphion/MaskGCT", "semantic_codec/model.safetensors")
download_file("funasr/campplus", "campplus_cn_common.bin")
download_repo_files("nvidia/bigvgan_v2_22khz_80band_256x")

print()
print("全部下载完成！")