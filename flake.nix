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
          httpx
        ];
      client_ps =
        ps: with ps; [
          sounddevice
          soundfile
          pyperclip
          requests
          numpy
          setproctitle
          pystray
          pygobject3
          pillow
        ];
      python3_server = pkgs_server.python3.withPackages server_ps;
      python3_client = pkgs_client.python3.withPackages client_ps;
      python3_combined = pkgs_server.python3.withPackages (ps: (server_ps ps) ++ (client_ps ps));

      client = pkgs_client.stdenv.mkDerivation {
        pname = "whisper-typing-client";
        version = "0.1.0";

        src = ./.;

        nativeBuildInputs = with pkgs_client; [
          gobject-introspection
          wrapGAppsHook3
        ];

        buildInputs = [
          python3_client
          pkgs_client.gtk3
          pkgs_client.libappindicator
        ];

        installPhase = ''
          install -D client.py -t "$out/bin/"
        '';
      };
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
                exec ${python3_server}/bin/python3 ${./server.py} "$@"
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
                client
                pkgs_client.wtype
              ];
              text = ''
                #!${pkgs_server.runtimeShell}
                exec ${client}/bin/client.py "$@"
              '';
            }
          );
        };
      };

      devShells.${system}.default = pkgs_server.mkShell {
        packages = with pkgs_server; [
          python3_combined
          wtype
          gobject-introspection
          gtk3
          libappindicator
        ];
        PYTHONPATH = "${python3_combined}/${python3_combined.sitePackages}";
      };
    };
}
