# Cole este código em domain/product.py

class Product:
    def __init__(self, product_id, name, quantity, volume_type, user_id, **kwargs):
        # Validações de regras de negócio essenciais
        if not name or len(name) < 2:
            raise ValueError("Nome do produto deve ter no mínimo 2 caracteres.")
        if quantity < 0:
            raise ValueError("Quantidade não pode ser negativa.")

        self.product_id = product_id
        self.name = name
        self.quantity = quantity
        self.volume_type = volume_type
        self.user_id = user_id # Para saber a qual usuário o produto pertence
        
        # Atributos opcionais (informações nutricionais)
        self.nutritional_info = {
            'valor_energetico_kcal': kwargs.get('valor_energetico_kcal'),
            'acucares_totais_g': kwargs.get('acucares_totais_g'),
            # ... adicione outros campos nutricionais aqui conforme a tabela
        }