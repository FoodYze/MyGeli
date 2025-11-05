# Cole este código em application/product_service.py

from infrastructure.database_repository import ProductRepository
from domain.product import Product

class ProductService:
    def __init__(self, product_repo: ProductRepository):
        self.product_repo = product_repo

    def add_new_product_to_stock(self, name, quantity, volume_type, user_id):
        try:
            product = Product(
                product_id=None, 
                name=name, 
                quantity=quantity, 
                volume_type=volume_type, 
                user_id=user_id
            )
            return self.product_repo.add(product)
        except ValueError as ve:
            raise ve
        except Exception as e:
            raise RuntimeError(f"Não foi possível criar o produto: {e}")

    def get_stock_for_user(self, user_id):
        # Esta parte do código tem um pequeno erro, vamos corrigir
        # O construtor do Product espera argumentos nomeados, não um dicionário com '**'
        products_data = self.product_repo.get_by_user_id(user_id)
        
        products_list = []
        for p_data in products_data:
            # Mapeia os nomes das colunas do DB para os nomes dos argumentos do construtor
            product = Product(
                product_id=p_data['id_produto'],
                name=p_data['nome_produto'],
                quantity=p_data['quantidade_produto'],
                volume_type=p_data['tipo_volume'],
                user_id=p_data['usuario_id']
            )
            products_list.append(product)
        return products_list