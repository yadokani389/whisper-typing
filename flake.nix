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
      pkgs_server = import nixpkgs {
        inherit system;
        config.allowUnfree = true;
        config.cudaSupport = true;
      };
      pkgs_client = import nixpkgs {
        inherit system;
      };
      server_ps =
        ps: with ps; [
          faster-whisper
          fastapi
          uvicorn
          python-multipart
        ];
      client_ps =
        ps: with ps; [
          sounddevice
          soundfile
          pyperclip
          requests
          numpy
          setproctitle
        ];
      python3_server = pkgs_server.python3.withPackages server_ps;
      python3_client = pkgs_client.python3.withPackages client_ps;
      python3_combined = pkgs_server.python3.withPackages (ps: (server_ps ps) ++ (client_ps ps));
    in
    {
      apps.${system} = {
        server = {
          type = "app";
          program = pkgs_server.lib.getExe (
            pkgs_server.writeShellApplication {
              name = "whisper-typing-server";
              text = ''
                #!${pkgs_server.runtimeShell}
                exec ${python3_server}/bin/python ${./server.py} "$@"
              '';
            }
          );
        };

        client = {
          type = "app";
          program = pkgs_client.lib.getExe (
            pkgs_client.writeShellApplication {
              name = "whisper-typing-client";
              runtimeInputs = [
                pkgs_client.wtype
              ];
              text = ''
                #!${pkgs_client.runtimeShell}
                exec ${python3_client}/bin/python ${./client.py} "$@"
              '';
            }
          );
        };
      };

      devShells.${system}.default = pkgs_server.mkShell {
        packages = [
          python3_combined
          pkgs_server.wtype
        ];
        PYTHONPATH = "${python3_combined}/${python3_combined.sitePackages}";
      };
    };
}
