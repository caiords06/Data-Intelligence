"""Executa o receptor central: python -m servidor."""

import argparse

from servidor.api import executar_servidor


def main():
    parser = argparse.ArgumentParser(description="Servidor central Data Intelligence")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--cert")
    parser.add_argument("--key")
    args = parser.parse_args()
    servidor = executar_servidor(args.host, args.port, certificado=args.cert, chave_privada=args.key)
    esquema = "https" if args.cert else "http"
    print(f"Servidor operacional em {esquema}://{args.host}:{args.port}")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        servidor.server_close()


if __name__ == "__main__":
    main()
