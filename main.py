from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import (
    TimeoutException,
    WebDriverException
)

from Settings import (
    LINK,
    TEMPO_ABERTURA_NAVEGADOR,
    TEMPO_CARREGAMENTO_PAGINA
)

from opsystemcheck import verificar_sistema_operacional
from iduser import identificar_usuario

from idbrowser import (
    localizar_navegador_padrao,
    identificar_tipo_navegador
)

from driver import criar_driver

def executaraut(driver_selenium):
    print(['[OK] Iniciando execução do script de automação e análise de dados...'])

# COLOCAR AUTOMAÇÃO AQUI

def main():
    driver_selenium = None

    try:
        # ============================================
        # 1. VERIFICAR WINDOWS
        # ============================================

        sistema = verificar_sistema_operacional()

        print(
            f"[OK] Sistema operacional: {sistema}"
        )


        # ============================================
        # 2. IDENTIFICAR USUÁRIO
        # ============================================
        (
            usuario,
            pasta_usuario,
            local_appdata
        ) = identificar_usuario()

        print (
            f'[OK] Usuário identificado: {usuario}'
        )

        print (
            f'[OK] Pasta do usuário: {pasta_usuario}'
        )

        print (
            f'[OK] Local do AppData: {local_appdata}'
        )

        # ============================================
        # 3. LOCALIZAR NAVEGADOR PADRÃO
        # ============================================

        (
            prog_id,
            caminho_executavel
        ) = localizar_navegador_padrao()

        print(
            f'[OK] Identificador do navegador localizado: {prog_id}'
        )

        print(
            f'[OK] Executável do navegador localizado: {caminho_executavel}'
        )

        # ============================================
        # 4. VERIFICAR EXECUTÁVEL
        # ============================================

        if not caminho_executavel.exists():
            raise FileNotFoundError(
                f"Executável do navegador não encontrado: {caminho_executavel}"
            )

        # ============================================
        # 5. IDENTIFICAR TIPO DE NAVEGADOR
        # ============================================

        navegador = identificar_tipo_navegador(
            prog_id,
            caminho_executavel
        )

        print(
            f'[OK] Tipo de navegador identificado: {navegador.upper()}'
        )

        # ============================================
        # 6. ABRIR NAVEGADOR COM SELENIUM
        # ============================================
        
        print(
            '[AGUARDE] Abrindo navegador...'
        )

        driver_selenium = criar_driver(
            navegador,
            caminho_executavel
        )

        WebDriverWait(
            driver_selenium,
            TEMPO_ABERTURA_NAVEGADOR
        ).until(
            lambda navegador_aberto:(
                len(
                    navegador_aberto.window_handles
                    ) > 0
            )
        )

        driver_selenium.maximize_window()

        print(
            '[OK] Navegador aberto com sucesso!'
        )

        # ============================================
        # 7. ACESSAR LINK DA EMPRESA
        # ============================================

        print('[AGUARDE] Acessando link...'
        )

        driver_selenium.get(LINK)


        # ============================================
        # 8. AGUARDAR CARREGAMENTO DA PÁGINA
        # ============================================

        WebDriverWait(
            driver_selenium,
            TEMPO_CARREGAMENTO_PAGINA
        ).until(
            lambda navegador_aberto:(
                navegador_aberto.execute_script(
                    "return document.readyState"
                ) == "complete"
            )
        )

        print(
        '[OK] Página carregada com sucesso!'
        )

        # ============================================
        # 9. EXECUTAR AUTOMAÇÃO
        # ============================================

        executaraut(
            driver_selenium
        )

    except TimeoutException:
        print(
            '[ERRO] Tempo de espera excedido. O navegador não respondeu a tempo.'
        )

    except WebDriverException as erro:
        print(
            f'[ERRO] Ocorreu um erro com o WebDriver: {erro}'
        )

    except (
            FileNotFoundError,
            OSError,
            RuntimeError
        ) as erro:
            print(
                f'[ERRO] {erro}'
            )

    finally:
        if driver_selenium is not None:
            print(
                '[OK] Fechando navegador...'
            )

            driver_selenium.quit()
if __name__ == "__main__":
    main()