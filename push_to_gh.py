import requests
import base64
import os
import logging

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")

def upload_to_github(file_path, repo_path):
    token = os.getenv("GH_TOKEN")
    repo = "astonef/fstfd-cdn"
    branch = "core"
    api_url = f"https://api.github.com/repos/{repo}/contents/{repo_path}"

    logging.debug(f"Uploading {file_path} to {repo_path} in repo {repo} on branch {branch}")
    logging.debug(f"GitHub API URL: {api_url}")

    with open(file_path, "rb") as f:
        raw_bytes = f.read()
        content = base64.b64encode(raw_bytes).decode()

    logging.debug(f"Encoded content length: {len(content)}")

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }

    # check if file exists
    logging.debug("Checking if file already exists...")
    r = requests.get(api_url, headers=headers, params={"ref": branch})
    logging.debug(f"GET status code: {r.status_code}")
    sha = r.json().get("sha") if r.status_code == 200 else None
    if sha:
        logging.debug(f"File exists. SHA: {sha}")
    else:
        logging.debug("File does not exist or error occurred.")

    data = {
        "message": f"upload {repo_path}",
        "content": content,
        "branch": branch
    }
    if sha:
        data["sha"] = sha

    logging.debug(f"PUT data payload: {data.keys()}")
    r = requests.put(api_url, headers=headers, json=data)
    logging.debug(f"PUT status: {r.status_code}")
    logging.debug(f"PUT response: {r.json()}")

    return r.status_code, r.json()
