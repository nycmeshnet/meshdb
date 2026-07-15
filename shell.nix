{ pkgs ? import <nixpkgs> {} }:
(pkgs.buildFHSEnv {
  name = "pipzone";
  targetPkgs = pkgs: (with pkgs; [
    python311
    python312Packages.pip
    python312Packages.virtualenv
  ]);
  runScript = "zsh";
}).env
