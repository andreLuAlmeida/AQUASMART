"""Autenticação e inicialização do Google Earth Engine."""

import ee

from acquisition.google_earth_engine.config import EE_PROJECT_ID


def inicializar_earth_engine(permitir_login_interativo: bool = True) -> None:
    """Inicializa o Earth Engine usando o projeto configurado no ``.env``.

    Quando ``permitir_login_interativo`` é True e não há credenciais locais,
    ``ee.Authenticate()`` inicia o fluxo de login. Isso é útil no terminal.

    Em um servidor sem navegador é preferível autenticar previamente e iniciar
    a API depois, evitando um fluxo interativo no meio de uma requisição HTTP.
    """
    if not EE_PROJECT_ID:
        raise RuntimeError(
            "EE_PROJECT_ID não foi configurado no .env. "
            "Copie .env.example para .env e informe o Project ID do Google Cloud."
        )

    try:
        ee.Initialize(project=EE_PROJECT_ID)
        return
    except Exception as primeiro_erro:
        if not permitir_login_interativo:
            raise RuntimeError(
                "Google Earth Engine não autenticado. Execute primeiro: "
                "python -m google_earth_engine.auth"
            ) from primeiro_erro

    print("Credenciais do Earth Engine não encontradas. Iniciando autenticação...")
    ee.Authenticate()
    ee.Initialize(project=EE_PROJECT_ID)
    print("Google Earth Engine autenticado e inicializado.")


if __name__ == "__main__":
    inicializar_earth_engine(permitir_login_interativo=True)
    print("Teste de autenticação concluído com sucesso.")
