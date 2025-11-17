// Variáveis globais
let listaComprasData = null;
const CATEGORIAS_COMPRA = [
  "Hortifruti", "Mercearia", "Proteínas", "Laticínios", 
  "Padaria", "Bebidas", "Congelados", "Outros"
];
const UNIDADES_ESTOQUE = ["Unidades", "Quilos (Kg)", "Gramas (g)", "Litros (L)", "Mililitros (ml)"];

// Inicialização quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', () => {
  // --- Loader ---
  const loaderWrapper = document.getElementById('loader-wrapper');
  const progressBar = document.getElementById('progress-bar');
  const progressPercentage = document.getElementById('progress-percentage');

  let currentProgress = 0;

  function updateProgress() {
    if (currentProgress < 100) {
      currentProgress += Math.random() * 5 + 1;
      if (currentProgress > 100) {
        currentProgress = 100;
      }
      progressBar.style.width = currentProgress + '%';
      progressPercentage.textContent = Math.floor(currentProgress) + '%';
      setTimeout(updateProgress, 20);
    } else {
      loaderWrapper.classList.add('hidden');
      document.body.classList.add('loaded');
    }
  }
  updateProgress();

  // --- Tema ---
  const themeToggle = document.querySelector("#theme-toggle-btn");
  
  themeToggle.addEventListener("click", () => {
    const isLightTheme = document.body.classList.toggle("light-theme");
    localStorage.setItem("themeColor", isLightTheme ? "light_mode" : "dark_mode");
    themeToggle.textContent = isLightTheme ? "dark_mode" : "light_mode";
  });

  const isLightTheme = localStorage.getItem("themeColor") === "light_mode";
  document.body.classList.toggle("light-theme", isLightTheme);
  themeToggle.textContent = isLightTheme ? "dark_mode" : "light_mode";

  // --- Carregar sugestões ---
  carregarSugestoesEmBackground();

  // --- Event Listeners dos Botões ---
  document.getElementById('btn-adicionar').addEventListener('click', abrirModalAdicionar);
  document.getElementById('btn-remover-selecionados').addEventListener('click', removerSelecionados);
  document.getElementById('btn-salvar-lista').addEventListener('click', salvarLista);

  // --- Modal ---
  document.getElementById('btn-modal-cancel').addEventListener('click', fecharModal);
  document.getElementById('btn-modal-confirm').addEventListener('click', adicionarItemManual);
  
  // Fechar modal ao clicar fora
  document.getElementById('modal-overlay').addEventListener('click', (e) => {
    if (e.target.id === 'modal-overlay') {
      fecharModal();
    }
  });
});

// --- Funções de Carregamento de Dados ---

async function carregarSugestoesEmBackground() {
  try {
    // Aqui você faria uma chamada para o backend
    // Por enquanto, vamos simular com dados de exemplo
    const response = await fetch('/api/compras/sugestoes');
    
    if (response.ok) {
      listaComprasData = await response.json();
    } else {
      // Se não houver endpoint, usar dados de exemplo
      listaComprasData = gerarDadosExemplo();
    }
  } catch (error) {
    console.log('Usando dados de exemplo:', error);
    // Dados de exemplo caso o endpoint não exista
    listaComprasData = gerarDadosExemplo();
  }
  
  carregarListaCompras();
}

function gerarDadosExemplo() {
  return [
    { nome: "Açúcar", quantidade: 1, unidade: "Quilos (Kg)", categoria: "Mercearia", preco: "R$ 5,50" },
    { nome: "Arroz", quantidade: 5, unidade: "Quilos (Kg)", categoria: "Mercearia", preco: "R$ 28,00" },
    { nome: "Feijão", quantidade: 1, unidade: "Quilos (Kg)", categoria: "Mercearia", preco: "R$ 8,50" },
    { nome: "Maçã", quantidade: 6, unidade: "Unidades", categoria: "Hortifruti", preco: "R$ 12,00" },
    { nome: "Banana", quantidade: 12, unidade: "Unidades", categoria: "Hortifruti", preco: "R$ 8,00" },
    { nome: "Tomate", quantidade: 1, unidade: "Quilos (Kg)", categoria: "Hortifruti", preco: "R$ 7,00" },
    { nome: "Frango (Peito)", quantidade: 1, unidade: "Quilos (Kg)", categoria: "Proteínas", preco: "R$ 22,00" },
    { nome: "Carne Moída", quantidade: 500, unidade: "Gramas (g)", categoria: "Proteínas", preco: "R$ 18,00" },
    { nome: "Leite", quantidade: 2, unidade: "Litros (L)", categoria: "Laticínios", preco: "R$ 9,00" },
    { nome: "Queijo Mussarela", quantidade: 300, unidade: "Gramas (g)", categoria: "Laticínios", preco: "R$ 15,00" },
    { nome: "Pão Francês", quantidade: 10, unidade: "Unidades", categoria: "Padaria", preco: "R$ 12,00" },
    { nome: "Refrigerante", quantidade: 2, unidade: "Litros (L)", categoria: "Bebidas", preco: "R$ 12,00" },
    { nome: "Suco de Laranja", quantidade: 1, unidade: "Litros (L)", categoria: "Bebidas", preco: "R$ 8,00" },
    { nome: "Sorvete", quantidade: 1, unidade: "Litros (L)", categoria: "Congelados", preco: "R$ 18,00" }
  ];
}

// --- Funções de Renderização ---

function carregarListaCompras() {
  const listaFrame = document.getElementById('lista-frame');
  listaFrame.innerHTML = '';

  if (listaComprasData === null) {
    listaFrame.innerHTML = '<div class="loading-message">Gerando sugestões com base na média...</div>';
    return;
  }

  if (listaComprasData.length === 0) {
    listaFrame.innerHTML = '<div class="empty-message">Nenhum item na lista. Clique em "Adicionar Item" para começar!</div>';
    return;
  }

  // Agrupar por categoria
  const produtosPorCategoria = {};
  listaComprasData.forEach(produto => {
    const categoria = produto.categoria || "Outros";
    if (!produtosPorCategoria[categoria]) {
      produtosPorCategoria[categoria] = [];
    }
    produtosPorCategoria[categoria].push(produto);
  });

  // Renderizar por categoria
  const categoriasOrdenadas = Object.keys(produtosPorCategoria).sort();
  categoriasOrdenadas.forEach(categoria => {
    // Header da categoria
    const headerDiv = document.createElement('div');
    headerDiv.className = 'categoria-header';
    headerDiv.textContent = categoria.toUpperCase();
    listaFrame.appendChild(headerDiv);

    // Itens da categoria
    produtosPorCategoria[categoria].forEach(produto => {
      criarItemLista(listaFrame, produto);
    });
  });
}

function criarItemLista(parent, produto) {
  const itemFrame = document.createElement('div');
  itemFrame.className = 'item-frame';

  // Checkbox
  const checkbox = document.createElement('input');
  checkbox.type = 'checkbox';
  checkbox.className = 'item-checkbox';
  produto.checkbox = checkbox;

  // Nome
  const nome = document.createElement('p');
  nome.className = 'item-nome';
  nome.textContent = produto.nome;

  // Quantidade
  const quantidade = document.createElement('span');
  quantidade.className = 'item-quantidade';
  quantidade.textContent = `${produto.quantidade} ${produto.unidade}`;

  // Preço
  const preco = document.createElement('span');
  preco.className = 'item-preco';
  preco.textContent = produto.preco || "N/D";

  // Botão remover
  const btnRemover = document.createElement('button');
  btnRemover.className = 'item-remover-btn';
  btnRemover.textContent = 'X';
  btnRemover.addEventListener('click', () => removerItem(produto));

  // Montar o item
  itemFrame.appendChild(checkbox);
  itemFrame.appendChild(nome);
  itemFrame.appendChild(quantidade);
  itemFrame.appendChild(preco);
  itemFrame.appendChild(btnRemover);

  parent.appendChild(itemFrame);
  produto.frame = itemFrame;
}

// --- Funções de Manipulação de Itens ---

function abrirModalAdicionar() {
  const modal = document.getElementById('modal-overlay');
  modal.classList.add('show');
  
  // Limpar campos
  document.getElementById('input-nome').value = '';
  document.getElementById('input-quantidade').value = '';
  document.getElementById('select-unidade').value = UNIDADES_ESTOQUE[0];
  document.getElementById('select-categoria').value = CATEGORIAS_COMPRA[0];
  
  // Focar no primeiro campo
  document.getElementById('input-nome').focus();
}

function fecharModal() {
  const modal = document.getElementById('modal-overlay');
  modal.classList.remove('show');
}

function adicionarItemManual() {
  const nome = document.getElementById('input-nome').value.trim();
  const quantidade = document.getElementById('input-quantidade').value.trim();
  const unidade = document.getElementById('select-unidade').value;
  const categoria = document.getElementById('select-categoria').value;

  if (!nome || !quantidade) {
    alert('Por favor, preencha o nome e a quantidade do produto.');
    return;
  }

  const novoItem = {
    nome: nome.charAt(0).toUpperCase() + nome.slice(1),
    quantidade: quantidade,
    unidade: unidade,
    categoria: categoria,
    preco: "N/A"
  };

  if (listaComprasData === null) {
    listaComprasData = [];
  }

  listaComprasData.push(novoItem);
  carregarListaCompras();
  fecharModal();
}

function removerItem(itemToRemove) {
  const index = listaComprasData.indexOf(itemToRemove);
  if (index > -1) {
    listaComprasData.splice(index, 1);
    carregarListaCompras();
  }
}

function removerSelecionados() {
  if (!listaComprasData || listaComprasData.length === 0) {
    return;
  }

  const itensParaRemover = listaComprasData.filter(produto => 
    produto.checkbox && produto.checkbox.checked
  );

  if (itensParaRemover.length === 0) {
    alert('Nenhum item selecionado para remover.');
    return;
  }

  itensParaRemover.forEach(item => {
    const index = listaComprasData.indexOf(item);
    if (index > -1) {
      listaComprasData.splice(index, 1);
    }
  });

  carregarListaCompras();
}

// --- Função de Salvar Lista ---

function salvarLista() {
  if (!listaComprasData || listaComprasData.length === 0) {
    alert('A lista está vazia. Adicione itens antes de salvar.');
    return;
  }

  // Gerar conteúdo do arquivo
  let conteudo = `Lista de Compras - Gerada em: ${new Date().toLocaleString('pt-BR')}\n\n`;

  // Agrupar por categoria
  const produtosPorCategoria = {};
  listaComprasData.forEach(produto => {
    const categoria = produto.categoria || "Outros";
    if (!produtosPorCategoria[categoria]) {
      produtosPorCategoria[categoria] = [];
    }
    produtosPorCategoria[categoria].push(produto);
  });

  // Adicionar cada categoria
  const categoriasOrdenadas = Object.keys(produtosPorCategoria).sort();
  categoriasOrdenadas.forEach(categoria => {
    conteudo += `--- ${categoria.toUpperCase()} ---\n`;
    produtosPorCategoria[categoria].forEach(produto => {
      conteudo += `[ ] ${produto.nome} (${produto.quantidade} ${produto.unidade}) - Preço Est.: ${produto.preco}\n`;
    });
    conteudo += '\n';
  });

  // Criar e baixar o arquivo
  const blob = new Blob([conteudo], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = 'lista_compras.txt';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);

  alert('Lista salva com sucesso!');
}
