import os
from pathlib import Path
import requests
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import status
from meshapi.models import Building, Install

from meshapi.util.django_pglocks import advisory_lock


# View called to make MeshDB refresh the panoramas.
# We want a cache to be able to diff which panos we've already ingested. Maybe
# we could store it in postgres :P
@api_view(["GET"])
@permission_classes([permissions.AllowAny])
# @advisory_lock() # TODO: Wanna lock the table when we update the panoramas?
def update_panoramas_from_github(request):
    # TODO: Make env variables
    owner = "nycmeshnet"
    repo = "node-db"
    branch = "master"
    directory = "data/panoramas"

    netlify_pano_url = "https://node-db.netlify.app/panoramas/"

    head_tree_sha = get_head_tree_sha(owner, repo, branch)

    panorama_files = list_files_in_directory(owner, repo, directory, head_tree_sha)
    if not panorama_files:
        return Response({"detail": "Could not list files"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    panos = build_pano_dict(panorama_files)

    panoramas_saved = 0
    warnings = []

    for install_number, filenames in panos.items():
        try:
            install: Install = Install.objects.get(install_number=int(install_number))
            install.building.panoramas = []
            if not install:
                print(
                    f"Warning: Could not add panorama to building (Install #{install_number}). Install does not exist."
                )
                warnings.append(install_number)
                continue
            for filename in filenames:
                file_url = f"{netlify_pano_url}{filename}"
                install.building.panoramas.append(file_url)
            install.building.save()
            panoramas_saved += len(filenames)
        except Exception as e:
            print(f"Warning: Could not add panorama to building (Install #{install_number}): {e}")
            warnings.append(install_number)

    return Response(
        {
            "detail": f"Saved {panoramas_saved} panoramas. Got {len(warnings)} warnings.",
            "saved": panoramas_saved,
            "warnings": len(warnings),
            "warn_install_nums": warnings,
        },
        status=status.HTTP_200_OK,
    )


def build_pano_dict(files: list[str]):
    panos = {}
    for f in files:
        number, label = parse_pano_title(Path(f).stem)
        if number not in panos:
            panos[number] = [f]
        else:
            panos[number].append(f)
    return panos


def parse_pano_title(title: str):
    number = ""
    label = ""
    for i in range(0, len(title)):
        if title[i].isdigit():
            number += title[i]
        elif i == 0:
            # There are some files in here that have a space or something in the
            # first letter, so we handle that edge case by ignoring it.
            continue
        else:
            label = title[i:]
            break
    return (number, label)


# Gets the tree-sha, which we need to use the trees API (allows us to list up to
# 100k/7MB of data)
def get_head_tree_sha(owner, repo, branch):
    url = f"https://api.github.com/repos/{owner}/{repo}/branches/{branch}"
    master = requests.get(url)
    master = master.json()
    return master["commit"]["commit"]["tree"]["sha"]


# Returns all the filenames, stripped of extensions and everything
def list_files_in_directory(owner: str, repo: str, directory: str, tree):
    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{tree}?recursive=1"
    response = requests.get(url)

    if response.status_code == 200:
        files = []
        tree = response.json()
        for item in tree["tree"]:
            if item["type"] == "blob" and directory in item["path"]:
                files.append(os.path.basename(item["path"]))
        return files
    else:
        print(f"Error: Failed to fetch directory contents. Status code: {response.status_code}")
        return None
