import os
import sys
import requests
import subprocess
import json
import re
from urllib.parse import urlparse
os.system('title PBS Kids Downloader')

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json"
}
N_M3U8DL_PATH = "N_m3u8DL-RE.exe"

def get_next_build_id(video_page_url):
    print("[+] Detecting BuildID...")
    r = requests.get(video_page_url, headers=HEADERS, timeout=15)
    r.raise_for_status()
    match = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        r.text
    )
    if not match:
        raise RuntimeError("Could not find page data.")
    next_data = json.loads(match.group(1))
    build_id = next_data.get("buildId")
    if not build_id:
        raise RuntimeError("BuildID not found.")
    print(f"[+] Found BuildID: {build_id}")
    return build_id

def build_next_data_url(video_url, build_id):
    parsed = urlparse(video_url)
    path = parsed.path.rstrip("/")
    return f"https://pbskids.org/_next/data/{build_id}/en-US{path}.json"

def resolve_redirect(url):
    try:
        r = requests.head(url, headers=HEADERS, allow_redirects=True, timeout=15)
        return r.url
    except Exception as e:
        return f"ERROR: {e}"

def extract_profiles(json_data):
    try:
        video_list = json_data["pageProps"]["videoData"]["mediaManagerAsset"]["videos"]
    except KeyError:
        raise RuntimeError("Could not find video profiles in JSON.")
    results = []
    for video in video_list:
        profile = video.get("profile", "unknown")
        redirect_url = video.get("url")
        if not redirect_url:
            continue
        final_url = resolve_redirect(redirect_url)
        results.append({
            "profile": profile,
            "final_url": final_url
        })
    return dedupe_profiles(results)

def dedupe_profiles(profiles):
    seen = set()
    unique = []
    for p in profiles:
        key = (p["profile"], p["final_url"])
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return unique

def quality_sort_key(profile_name):
    if "1080p" in profile_name:
        return 3
    if "720p" in profile_name:
        return 2
    if "baseline" in profile_name:
        return 1
    return 0

def launch_downloader(url):
    print("\n[+] Launching N_m3u8DL-RE...\n")
    script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    binary_path = os.path.join(script_dir, N_M3U8DL_PATH)
    if not os.path.isfile(binary_path):
        print("[!] N_m3u8DL-RE.exe not found.")
        return
    subprocess.Popen(
        [
            binary_path,
            url,
            "--save-dir", script_dir
        ],
        cwd=script_dir,
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )

def main():
    video_page_url = input("Paste PBS Kids Video URL: ").strip()
    if not video_page_url:
        print("No URL provided.")
        return
    try:
        build_id = get_next_build_id(video_page_url)
        next_data_url = build_next_data_url(video_page_url, build_id)
        print(f"\n[+] Fetching JSON:\n{next_data_url}\n")
        r = requests.get(next_data_url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json()
        profiles = extract_profiles(data)
        if not profiles:
            print("No video profiles found.")
            return
        profiles.sort(
            key=lambda p: quality_sort_key(p["profile"]),
            reverse=True
        )
        print("=== Available Videos ===\n")
        for idx, p in enumerate(profiles, start=1):
            print(f"[{idx}] {p['profile']}")
        choice = input("\nEnter number to download: ").strip()
        if not choice:
            print("Exiting.")
            return
        choice_num = int(choice)
        if not (1 <= choice_num <= len(profiles)):
            print("Invalid selection.")
            return
        selected = profiles[choice_num - 1]
        if selected["final_url"].startswith("ERROR"):
            print("Invalid stream.")
            return
        launch_downloader(selected["final_url"])
    except Exception as e:
        print(f"\n[!] Error: {e}")

if __name__ == "__main__":
    main()
