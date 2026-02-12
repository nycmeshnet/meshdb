{ pkgs ? import <nixpkgs> {} }:
(pkgs.buildFHSEnv {
  name = "pipzone";
  targetPkgs = pkgs: (with pkgs; [
    python311
    python311Packages.pip
    python311Packages.virtualenv
  ]);
  runScript = "zsh";
}).env
