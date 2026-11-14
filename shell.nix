{ pkgs ? import <nixpkgs> {} }:
(pkgs.buildFHSEnv {
  name = "pipzone";
  targetPkgs = pkgs: (with pkgs; [
    python311
    python312Packages.pip
    python312Packages.virtualenv
    # psycopg2-binary needs the system libz at runtime; buildFHSEnv
    # symlinks it into /lib so `uv run pytest` works without LD_LIBRARY_PATH
    zlib
  ]);
  runScript = "zsh";
}).env
