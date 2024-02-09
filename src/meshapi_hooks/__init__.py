# This package exists just to hold the custom Hook model, mostly so that it appears separately
# from the rest of the meshapi models in the admin UI. Having them together makes it hard to
# see that it's a metadata field for the functioning of the app, rather than a primary datatype
# used to represent mesh org data

default_app_config = "meshapi_hooks.apps.MeshAPIHooksConfig"
