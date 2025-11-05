from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time

def buscar_preco(produto):
    options = Options()
    options.add_argument("--headless")  # Executa sem abrir a janela do navegador
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
    driver.get(f'https://www.paodeacucar.com/busca?terms={produto}')
    time.sleep(4)  # Aguarda o JS renderizar, ajuste para mais se sua conexão for lenta

    precos = driver.find_elements(By.XPATH, "//*[contains(text(),'R$')]")
    for p in precos:
        txt = p.text.strip()
        if txt.startswith("R$"):
            driver.quit()
            return txt
    driver.quit()
    return "Preço não encontrado"

ingredientes = ['arroz integral', 'bife ancho', 'wagyu', 'linguiça toscana', 'fraldinha carne', 'pão de alho', 'coração de frango','sal de parrilha']

for ing in ingredientes:
    print(f"{ing}: {buscar_preco(ing)}")

