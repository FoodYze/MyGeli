from scraper.consulta_precos import buscar_preco

ingredientes = ['arroz', 'feijão', 'óleo', 'farinha']

for ing in ingredientes:
    print(f'{ing}: {buscar_preco(ing)}')
