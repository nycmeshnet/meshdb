from pathlib import Path
import requests
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import status

from meshapi.util.django_pglocks import advisory_lock


# View called to make MeshDB refresh the panoramas.
# We want a cache to be able to diff which panos we've already ingested. Maybe
# we could store it in postgres :P
@api_view(["GET"])
@permission_classes([permissions.AllowAny])
#@advisory_lock() # TODO: Wanna lock the table when we update the panoramas?
def update_panos(request):
    # TODO: Make env variables
    owner = 'nycmeshnet'
    repo = 'node-db'
    branch = 'master'
    directory = 'data/panoramas'

    head_tree_sha = get_head_tree_sha(owner, repo, branch)

    files = list_files_in_directory(owner, repo, directory, head_tree_sha)
    if not files:
        return Response({"detail": "Could not list files"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    print("Files in directory:")
    for file in files:
        print(file)

    panos = build_pano_dict(files)

    print(panos)

    return Response({}, status=status.HTTP_200_OK)

def build_pano_dict(files: list[str]):
    panos = {}
    for f in files:
        number, label = parse_pano_title(f)
        if number not in panos:
            panos[number] = [label]
        else:
            panos[number].append(label)
    return panos

def parse_pano_title(title: str):
    number = ''
    label = ''
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

def get_head_tree_sha(owner, repo, branch):
    url = f'https://api.github.com/repos/{owner}/{repo}/branches/{branch}'
    master = requests.get(url)
    master = master.json()
    return master['commit']['commit']['tree']['sha']

# Returns all the filenames, stripped of extensions and everything
def list_files_in_directory(owner: str, repo: str, directory: str, tree):
    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{tree}?recursive=1"
    response = requests.get(url)
    
    if response.status_code == 200:
        files = []
        tree = response.json()
        for item in tree['tree']:
            if item['type'] == 'blob' and directory in item['path']:
                files.append(Path(item['path']).stem)
        return files
    else:
        print(f"Error: Failed to fetch directory contents. Status code: {response.status_code}")
        return None

