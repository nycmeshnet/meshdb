import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Union

import requests
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response

from meshapi.models import Install
from meshapi.models.building import Building
from meshapi.models.node import Node
from meshapi.permissions import HasPanoramaUpdatePermission
from meshapi.util.constants import DEFAULT_EXTERNAL_API_TIMEOUT_SECONDS
from meshapi.util.django_pglocks import advisory_lock

# Config for gathering/generating panorama links
PANO_REPO_OWNER = "nycmeshnet"
PANO_REPO = "node-db"
PANO_BRANCH = "master"
PANO_DIR = "data/panoramas"
PANO_HOST = "https://node-db.netlify.app/panoramas/"


"""
Panoramas can be titled as either ###[a-z*].jpg or nn###[a-z*].jpg. This will
apply those rules to a given string and either return a title or raise a special
exception if it finds a pano that breaks the rules.

Returns a PanoramaTitle which determines if we're dealing with a panorama
labeled after a NN or Install #, contains its number, and any special label
like `a`.
"""


@dataclass
class PanoramaKey:
    is_nn: bool
    number: str

    def __str__(self) -> str:
        if self.is_nn:
            return f"nn{self.number}"
        return self.number


@dataclass
class PanoramaTitle:
    filename: str
    is_nn: bool
    number: str  # Confusingly, this is not a number.
    label: str

    def __str__(self) -> str:
        return self.filename

    def get_key(self) -> PanoramaKey:
        return PanoramaKey(self.is_nn, self.number)

    def get_url(self) -> str:
        return f"{PANO_HOST}{self}"

    @classmethod
    def from_filename(cls, filename: str) -> "PanoramaTitle":
        if len(filename) <= 0:
            raise BadPanoramaTitle("Got filename of length 0")

        # Get that file extension outta here
        stem = Path(filename).stem

        # Handle dumb edge case
        if len(stem) > 4 and stem[0:4] == "IMG_":
            return cls(filename=filename, is_nn=False, number=stem[4:], label="")

        # Some of the files have spaces but are otherwise fine
        if stem[0] == " ":
            stem = stem[1:]

        # Handle any other dumb edge cases by bailing
        # Mainly, if the first 2 characters are not digits and not `nn`, then bail
        if not stem[0].isdigit() and len(stem) < 2 and stem[0:2] != "nn":
            raise BadPanoramaTitle(f"First character not a digit nor NN marker: {filename}")

        # By default, all files are associated and labeled with Install #.
        # Files associated with Network Numnbers are prepended with `nn`.
        # Figure that out and chop it off for later
        is_nn = False
        if stem[0:2] == "nn":
            is_nn = True
            stem = stem[2:]

        # Finally, parse the number and label
        number = label = ""
        for i in range(0, len(stem)):
            if stem[i].isdigit():
                number += stem[i]
            elif i == 0:
                # There are some files in here that have a space or something in the
                # first letter, so we handle that edge case by ignoring it.
                continue
            else:
                label = stem[i:]
                break

        return cls(filename=filename, is_nn=is_nn, number=number, label=label)

    @classmethod
    def from_filenames(cls, filenames: list[str]) -> list["PanoramaTitle"]:
        panorama_titles = []
        for f in filenames:
            panorama_titles.append(cls.from_filename(f))
        return panorama_titles


# Raised if we get total nonsense as a panorama title
class BadPanoramaTitle(Exception):
    pass


class GitHubError(Exception):
    pass


# View called to make MeshDB refresh the panoramas.
@api_view(["POST"])
@permission_classes([HasPanoramaUpdatePermission])
def update_panoramas(request: Request) -> Response:
    try:
        panoramas_saved, warnings = sync_github_panoramas()
        return Response(
            {
                "detail": f"Saved {panoramas_saved} panoramas. Got {len(warnings)} warnings.",
                "saved": panoramas_saved,
                "warnings": len(warnings),
                "warn_install_nums": warnings,
            },
            status=status.HTTP_200_OK,
        )
    except (ValueError, GitHubError) as e:
        logging.exception("Error when syncing panoramas")
        return Response({"detail": str(type(e).__name__)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Used by the above api route, and also the celery task
@advisory_lock("update_panoramas_lock")
def sync_github_panoramas() -> tuple[int, list[str]]:
    # Check that we have all the environment variables we need
    owner = PANO_REPO_OWNER
    repo = PANO_REPO
    branch = PANO_BRANCH
    directory = PANO_DIR

    token = os.environ.get("PANO_GITHUB_TOKEN")
    if token is None:
        raise ValueError("Environment variable PANO_GITHUB_TOKEN not found")

    head_tree_sha = get_head_tree_sha(owner, repo, branch, token)
    if not head_tree_sha:
        raise GitHubError("Could not get head tree SHA from GitHub")

    filenames = list_files_in_git_directory(owner, repo, directory, head_tree_sha, token)
    if not filenames:
        raise GitHubError("Could not get file list from GitHub")

    panos: dict[PanoramaKey, list[PanoramaTitle]] = group_panoramas_by_install_or_nn(filenames)
    return set_panoramas(panos)


# Panorama saving helper functions


# Builds a dictionary of panoramas, grouping panoramas under the same NN or Install #
def group_panoramas_by_install_or_nn(filenames: list[str]) -> dict[PanoramaKey, list[PanoramaTitle]]:
    panos: dict[PanoramaKey, list[PanoramaTitle]] = {}
    for f in filenames:
        try:
            title = PanoramaTitle.from_filename(f)
        except BadPanoramaTitle:
            logging.exception("Error due to bad filename: f")
            continue

        # Use this special get_key() function to separate NNs from not NNs.
        # This way, we'll have 632 and nn632 in separate keys
        if title.get_key() not in panos:
            panos[title.get_key()] = [title]
        else:
            panos[title.get_key()].append(title)
    return panos


# Helper function to update panorama list. One day, this should probably
# clobber the panoramas already saved (since a robot should probably be
# controlling this), but for now, it either appends to the current list,
# or bails if the current list and the new list are the same.
def save_building_panoramas(building: Building, panorama_titles: list[PanoramaTitle]) -> int:
    # Generate storage URL for panorama
    panoramas = []
    for filename in panorama_titles:
        panoramas.append(filename.get_url())

    # Bail if the panoramas have not changed
    if building.panoramas == panoramas:
        return 0

    # Add new panoramas
    for p in panoramas:
        if p not in building.panoramas:
            building.panoramas.append(p)
    building.save()

    return len(panoramas)


# Given a list of panoramas grouped by install number/network number, find the
# appropriate Building object and update the list of panoramas for that Building
def set_panoramas(panos: dict[PanoramaKey, list[PanoramaTitle]]) -> tuple[int, list[str]]:
    panoramas_saved = 0
    warnings = []

    for key, filenames in panos.items():
        try:
            if key.is_nn:
                try:
                    node: Node = Node.objects.get(network_number=int(key.number))
                    node_installs = node.installs.all()
                    if len(node_installs) == 0:
                        # This should never happen
                        logging.error(f"NN{key.number} exists, but has no installs.")
                        continue

                    # Get the first install from the node and use its building. Can't
                    # really do any better than that.
                    install = node_installs[0]

                    panoramas_saved += save_building_panoramas(install.building, filenames)
                except Node.DoesNotExist:
                    logging.error(f"Could not find corresponding NN {key.number}.")
                    warnings.append(str(key))
            else:
                try:
                    install = Install.objects.get(install_number=int(key.number))

                    panoramas_saved += save_building_panoramas(install.building, filenames)
                except Install.DoesNotExist:
                    logging.warning(f"Install #{key} Does not exist")
        except Exception:
            logging.exception(f"Could not add panorama to building (key = {key})")
            warnings.append(str(key))
    return panoramas_saved, warnings


# Github helper functions


# Gets the tree-sha, which we need to use the trees API (allows us to list up to
# 100k/7MB of data)
def get_head_tree_sha(owner: str, repo: str, branch: str, token: str = "") -> str | None:
    url = f"https://api.github.com/repos/{owner}/{repo}/branches/{branch}"
    master = requests.get(
        url, headers={"Authorization": f"Bearer {token}"}, timeout=DEFAULT_EXTERNAL_API_TIMEOUT_SECONDS
    )
    if master.status_code != 200:
        logging.error(f"Error: Got status {master.status_code} from GitHub trying to get SHA.")
        return None
    master_json = master.json()
    return master_json["commit"]["commit"]["tree"]["sha"]


# Returns all the filenames, stripped of extensions and everything
def list_files_in_git_directory(
    owner: str, repo: str, directory: str, tree: str, token: str = ""
) -> Union[list[str], None]:
    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{tree}?recursive=1"
    response = requests.get(
        url, headers={"Authorization": f"Bearer {token}"}, timeout=DEFAULT_EXTERNAL_API_TIMEOUT_SECONDS
    )
    if response.status_code != 200:
        logging.error(f"Error: Failed to fetch GitHub directory contents. Status code: {response.status_code}")
        return None
    files = []
    tree_res = response.json()
    for item in tree_res["tree"]:
        if item["type"] == "blob" and directory in item["path"]:
            files.append(os.path.basename(item["path"]))
    return files
