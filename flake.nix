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
      python3 = pkgs.python3.withPackages (
        ps: with ps; [
          faster-whisper
          sounddevice
          soundfile
          pyperclip
          fastapi
          uvicorn
          requests
          python-multipart
          numpy
          setproctitle
        ]
      );
      mkApp = app: file: {
        type = "app";
        program = pkgs.lib.getExe (
          pkgs.writeShellApplication {
            name = "whisper-typing-${app}";
            runtimeInputs = [
              python3
              pkgs.wtype
            ];
            text = ''
              #!${pkgs.runtimeShell}
              exec ${python3}/bin/python ${file} "$@"
            '';
          }
        );
      };
    in
    {
      apps.${system} = {
        server = mkApp "server" ./server.py;
        client = mkApp "client" ./client.py;
      };

      devShells.${system}.default = pkgs.mkShell {
        packages = [
          python3
          pkgs.wtype
        ];
        PYTHONPATH = "${python3}/${python3.sitePackages}";
      };
    };
}
