{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
  };

  outputs =
    {
      nixpkgs,
      ...
    }:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs {
        inherit system;
        config.allowUnfree = true;
        config.cudaSupport = true;
      };
    in
    {
      devShells.${system} = {
        default = pkgs.mkShell {
          packages = with pkgs; [
            (python3.withPackages (
              ps: with ps; [
                faster-whisper
                sounddevice
                soundfile
                pyperclip
              ]
            ))
          ];
          LD_LIBRARY_PATH =
            with pkgs;
            lib.makeLibraryPath [
              xorg.libX11
              xorg.libXrender
              xorg.libXrandr
              libGL
              glib
              zlib
              stdenv.cc.cc.lib
              "/run/opengl-driver"
              e2fsprogs
              gmpxx
              p11-kit
            ];
        };
        cpu = pkgs.mkShell {
          packages = with pkgs; [
            (python3.withPackages (
              ps: with ps; [
                faster-whisper
                sounddevice
                soundfile
                pyperclip
              ]
            ))
          ];
        };
      };
    };
}
