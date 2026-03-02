import os
import json
from playwright.sync_api import sync_playwright
from browser_use import BrowserUse

class NavegacaoAutonomaTool:
    def __init__(self, config_path='nucleo/ferramentas/navegacao_autonoma/config.json'):
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        self.browser_use = BrowserUse(config=self.config)

    def navegar_site(self, instrucao: str, url_inicial: str = None, max_passos: int = 20, salvar_screenshot: bool = True, retornar_html: bool = False):
        """
        Navega em sites reais como um humano. Recebe instrução natural e executa.
        Ex: 'pesquise concorrentes no Google, abra o primeiro resultado, tire screenshot do anúncio'.
        Retorna texto + screenshot.

        :param instrucao: prompt natural em português com a tarefa a ser executada.
        :param url_inicial: (opcional) URL para começar a navegação.
        :param max_passos: (opcional) máximo de ações que o BrowserUse pode executar (default 20).
        :param salvar_screenshot: (opcional) se deve salvar um screenshot da página final (default true).
        :param retornar_html: (opcional) se deve retornar o HTML completo da página (default false).
        :return: Dicionário com 'texto', 'screenshot_path', 'url_final' e 'erro' (se houver).
        """
        try:
            result = self.browser_use.run_instruction(
                instruction=instrucao,
                start_url=url_inicial,
                max_steps=max_passos,
                save_screenshot=salvar_screenshot,
                return_html=retornar_html
            )

            screenshot_path = None
            if salvar_screenshot and result.screenshot_path:
                # Assuming BrowserUse saves to a specific path, adjust if needed
                screenshot_path = result.screenshot_path

            return {
                "texto": result.text_content,
                "screenshot_path": screenshot_path,
                "url_final": result.final_url,
                "erro": None
            }
        except Exception as e:
            return {
                "texto": None,
                "screenshot_path": None,
                "url_final": None,
                "erro": str(e)
            }

# Exemplo de uso (para testes internos ou demonstração)
if __name__ == "__main__":
    # Certifique-se de ter o Playwright instalado: playwright install chromium --with-deps
    # E as dependências Python: pip install playwright browser-use crewai-tools python-dotenv 2captcha-python

    # Crie um arquivo config.json em nucleo/ferramentas/navegacao_autonoma/config.json
    # com a estrutura fornecida no JSON original.

    # Para testar, você pode precisar de uma chave 2Captcha real ou desabilitar o solver no config.json

    tool = NavegacaoAutonomaTool()
    print("Testando navegação autônoma...")
    resultado = tool.navegar_site(
        instrucao="Entre no Mercado Livre, pesquise 'planner 2026', clique no primeiro produto, veja o preço e tire screenshot da página.",
        url_inicial="https://www.mercadolivre.com.br",
        salvar_screenshot=True
    )
    print(json.dumps(resultado, indent=2))

    if resultado['screenshot_path']:
        print(f"Screenshot salvo em: {resultado['screenshot_path']}")

    print("\nTestando com erro (URL inválida)...")
    resultado_erro = tool.navegar_site(
        instrucao="Tente ir para uma URL inválida",
        url_inicial="http://url.invalida.xyz"
    )
    print(json.dumps(resultado_erro, indent=2))
