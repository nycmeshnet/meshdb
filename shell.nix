{ pkgs ? import <nixpkgs> {}}:

pkgs.mkShell {

  #buildInputs = [
  #];

  packages = [
    pkgs.python311
  ];
}
