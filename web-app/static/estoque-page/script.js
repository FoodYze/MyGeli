document.addEventListener('DOMContentLoaded', () => {
  
  // --- Tela de Carregamento ---
  const loaderWrapper = document.getElementById('loader-wrapper');
  const progressBar = document.getElementById('progress-bar');
  const progressPercentage = document.getElementById('progress-percentage');
  let currentProgress = 0;

  function updateProgress() {
    if (currentProgress < 100) {
      currentProgress += Math.random() * 10 + 5;
      if (currentProgress > 100) currentProgress = 100;
      progressBar.style.width = currentProgress + '%';
      progressPercentage.textContent = Math.floor(currentProgress) + '%';
      setTimeout(updateProgress, 100);
    } else {
      loaderWrapper.classList.add('hidden');
      document.body.classList.add('loaded');
    }
  }
  updateProgress();

  // --- CONFIGURAÇÃO DE DADOS ---

  // 1. Lista de Alimentos Prejudiciais (Copiado do gui3.py)
  const unhealthyKeywords = [
    "salsicha", "linguiça", "mortadela", "presunto", "salame", "bacon", 
    "peito de peru", "apresunto", "hambúrguer", "nuggets", "empanado", 
    "salgadinho", "refrigerante", "suco em pó", "macarrão instantâneo", "pizza", 
    "margarina", "chocolate", "açucar", "embutido", "ultraprocessado", 
    "enlatado", "conserva"
  ];

  // 2. Mock Data (Estendido com info nutricional)
  let mockStockData = [
    { 
      id: 101, name: "Arroz Integral", quantity: 2, unit: "Quilos (Kg)", 
      nutri: { kcal: 111, carb: 23, prot: 2.6, fat: 0.9, fiber: 1.8, sod: 1 }
    },
    { 
      id: 102, name: "Peito de Frango", quantity: 1.5, unit: "Quilos (Kg)",
      nutri: { kcal: 165, carb: 0, prot: 31, fat: 3.6, fiber: 0, sod: 74 } 
    },
    { 
      id: 103, name: "Refrigerante Cola", quantity: 2, unit: "Litros (L)", // Exemplo Prejudicial
      nutri: { kcal: 42, carb: 10.6, prot: 0, fat: 0, fiber: 0, sod: 4 }
    },
    { 
      id: 104, name: "Salsicha", quantity: 100, unit: "Gramas (g)", // Exemplo Baixo Estoque + Prejudicial
      nutri: { kcal: 300, carb: 2, prot: 12, fat: 25, fiber: 0, sod: 1000 }
    },
    { 
      id: 105, name: "Ovos", quantity: 1, unit: "Unidades", // Exemplo Baixo Estoque
      nutri: { kcal: 155, carb: 1.1, prot: 13, fat: 11, fiber: 0, sod: 124 }
    }
  ];

  // --- Elementos do DOM ---
  const tableBody = document.getElementById('stock-table-body');
  const addItemBtn = document.getElementById('add-item-btn');
  const notificationBtn = document.getElementById('notification-btn');
  const notificationBadge = document.getElementById('notification-badge');
  const voiceBtn = document.getElementById('voice-btn');
  
  // Modais
  const itemModal = document.getElementById('item-modal');
  const confirmModal = document.getElementById('confirm-modal');
  const nutriModal = document.getElementById('nutri-modal');
  const notificationsModal = document.getElementById('notifications-modal');
  const voiceOverlay = document.getElementById('voice-overlay');

  // Elementos Internos dos Modais
  const itemForm = document.getElementById('item-form');
  const nutriTableBody = document.getElementById('nutri-table-body');
  const notificationsList = document.getElementById('notifications-list');
  
  // Campos de Formulário
  const itemIdField = document.getElementById('item-id');
  const itemNameField = document.getElementById('item-name');
  const itemQuantityField = document.getElementById('item-quantity');
  const itemUnitField = document.getElementById('item-unit');

  // Variável de controle para deleção
  let idToDelete = null;

  // --- FUNÇÕES PRINCIPAIS ---

  function renderTable() {
    tableBody.innerHTML = '';
    
    if (mockStockData.length === 0) {
      tableBody.innerHTML = `<tr><td colspan="4" style="text-align: center; padding: 20px;">Estoque vazio.</td></tr>`;
      return;
    }

    mockStockData.forEach(item => {
      const tr = document.createElement('tr');
      const quantityDisplay = `${item.quantity} ${item.unit}`;
      
      tr.innerHTML = `
        <td>${item.name}</td>
        <td>${quantityDisplay}</td>
        <td style="text-align: center;">
          <button class="action-btn btn-info" data-id="${item.id}" title="Ver Info Nutricional">
            <span class="material-symbols-rounded">info</span>
          </button>
        </td>
        <td>
          <button class="action-btn btn-edit" data-id="${item.id}" title="Editar">
            <span class="material-symbols-rounded">edit</span>
          </button>
          <button class="action-btn btn-delete" data-id="${item.id}" title="Excluir">
            <span class="material-symbols-rounded">delete</span>
          </button>
        </td>
      `;
      tableBody.appendChild(tr);
    });

    attachTableEvents();
    checkAlerts(); // Verifica alertas sempre que renderizar
  }

  function attachTableEvents() {
    document.querySelectorAll('.btn-edit').forEach(btn => btn.addEventListener('click', handleEdit));
    document.querySelectorAll('.btn-delete').forEach(btn => btn.addEventListener('click', handleDelete));
    document.querySelectorAll('.btn-info').forEach(btn => btn.addEventListener('click', handleInfo));
  }

  // --- LÓGICA DE ALERTAS (Baseada no gui3.py) ---
  function checkAlerts() {
    let alertCount = 0;
    notificationsList.innerHTML = ''; // Limpa lista atual

    mockStockData.forEach(item => {
      // 1. Verifica Alimentos Prejudiciais
      const isUnhealthy = unhealthyKeywords.some(keyword => item.name.toLowerCase().includes(keyword));
      if (isUnhealthy) {
        addAlertDOM('danger', 'health_and_safety', `<b>${item.name}</b>: Alimento processado/embutido. Consuma com moderação.`);
        alertCount++;
      }

      // 2. Verifica Estoque Baixo (Lógica gui3.py)
      const unit = item.unit;
      const qty = item.quantity;
      let isLow = false;

      if (unit.includes('Unidades') && qty <= 2) isLow = true;
      if ((unit.includes('Gramas') || unit.includes('Mililitros')) && qty <= 500) isLow = true;
      
      // Nota: Para simplificar, assumimos que Kg e Litros convertidos já passariam de 500 se fossem > 0.5,
      // mas aqui usaremos a lógica direta do valor numérico.

      if (isLow) {
        addAlertDOM('warning', 'warning', `<b>${item.name}</b> está acabando! (${qty} ${unit})`);
        alertCount++;
      }
    });

    // Atualiza o Badge
    if (alertCount > 0) {
      notificationBadge.style.display = 'flex';
      notificationBadge.textContent = alertCount;
      notificationsList.querySelectorAll('.no-alerts').forEach(el => el.remove());
    } else {
      notificationBadge.style.display = 'none';
      notificationsList.innerHTML = '<p class="no-alerts">Nenhum alerta no momento. Tudo ótimo!</p>';
    }
  }

  function addAlertDOM(type, icon, textHTML) {
    const div = document.createElement('div');
    div.className = `alert-item ${type}`;
    div.innerHTML = `<span class="material-symbols-rounded alert-icon">${icon}</span><span>${textHTML}</span>`;
    notificationsList.appendChild(div);
  }

  // --- INFO NUTRICIONAL ---
  function handleInfo(event) {
    const id = Number(event.currentTarget.dataset.id);
    const item = mockStockData.find(i => i.id === id);
    if (!item) return;

    // Dados Nutricionais Mockados (Se não tiver, usa padrão zerado)
    const n = item.nutri || { kcal: 0, carb: 0, prot: 0, fat: 0, fiber: 0, sod: 0 };

    nutriTableBody.innerHTML = `
      <tr><td>Valor Energético</td><td>${n.kcal} kcal</td></tr>
      <tr><td>Carboidratos</td><td>${n.carb} g</td></tr>
      <tr><td>Proteínas</td><td>${n.prot} g</td></tr>
      <tr><td>Gorduras Totais</td><td>${n.fat} g</td></tr>
      <tr><td>Fibra Alimentar</td><td>${n.fiber} g</td></tr>
      <tr><td>Sódio</td><td>${n.sod} mg</td></tr>
    `;
    
    showModal(nutriModal);
  }

  // --- CRUD ---
  function handleEdit(event) {
    const id = Number(event.currentTarget.dataset.id);
    const item = mockStockData.find(i => i.id === id);
    if (!item) return;

    document.getElementById('modal-title').textContent = "Editar Item";
    itemIdField.value = item.id;
    itemNameField.value = item.name;
    itemQuantityField.value = item.quantity;
    itemUnitField.value = item.unit;

    showModal(itemModal);
  }

  function handleDelete(event) {
    idToDelete = Number(event.currentTarget.dataset.id);
    showModal(confirmModal);
  }

  function confirmDeleteAction() {
    mockStockData = mockStockData.filter(i => i.id !== idToDelete);
    idToDelete = null;
    hideModal(confirmModal);
    renderTable();
  }

  function handleFormSubmit(event) {
    event.preventDefault();
    const id = Number(itemIdField.value);
    const newItemData = {
      name: itemNameField.value,
      quantity: Number(itemQuantityField.value),
      unit: itemUnitField.value,
      // Gera info nutricional aleatória para novos itens (mock)
      nutri: { kcal: Math.floor(Math.random()*300), carb: Math.floor(Math.random()*50), prot: Math.floor(Math.random()*30), fat: Math.floor(Math.random()*15), fiber: Math.floor(Math.random()*10), sod: Math.floor(Math.random()*500) }
    };

    if (id) {
      mockStockData = mockStockData.map(i => i.id === id ? { ...i, ...newItemData, id: i.id, nutri: i.nutri } : i);
    } else {
      const newId = mockStockData.length ? Math.max(...mockStockData.map(i => i.id)) + 1 : 101;
      mockStockData.push({ id: newId, ...newItemData });
    }
    hideModal(itemModal);
    renderTable();
  }

  // --- RECONHECIMENTO DE VOZ ---
  voiceBtn.addEventListener('click', startVoiceRecognition);

  function startVoiceRecognition() {
    // Verifica suporte do navegador
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Seu navegador não suporta reconhecimento de voz.");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = 'pt-BR';
    recognition.continuous = false;

    voiceOverlay.classList.add('active');
    document.getElementById('voice-status-text').textContent = "Ouvindo...";

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      document.getElementById('voice-status-text').textContent = `Entendi: "${transcript}"`;
      
      setTimeout(() => {
        voiceOverlay.classList.remove('active');
        // Aqui entraria a lógica de IA do gui3.py para processar o texto.
        // Como é front-end puro, simulamos um sucesso genérico.
        alert(`Simulação: Comando "${transcript}" enviado para processamento!`);
      }, 1500);
    };

    recognition.onerror = (event) => {
      document.getElementById('voice-status-text').textContent = "Erro ao ouvir.";
      setTimeout(() => voiceOverlay.classList.remove('active'), 1500);
    };

    recognition.onend = () => {
      // Se acabou sem resultado, fecha
      if (voiceOverlay.classList.contains('active') && document.getElementById('voice-status-text').textContent === "Ouvindo...") {
        voiceOverlay.classList.remove('active');
      }
    };

    recognition.start();
  }


  // --- GESTÃO DE MODAIS ---
  function showModal(modal) { modal.classList.add('visible'); }
  function hideModal(modal) { modal.classList.remove('visible'); }

  // Event Listeners Gerais
  addItemBtn.addEventListener('click', () => {
    document.getElementById('modal-title').textContent = "Adicionar Novo Item";
    itemForm.reset();
    itemIdField.value = '';
    showModal(itemModal);
  });

  document.getElementById('modal-cancel').addEventListener('click', () => hideModal(itemModal));
  itemForm.addEventListener('submit', handleFormSubmit);

  document.getElementById('confirm-cancel').addEventListener('click', () => hideModal(confirmModal));
  document.getElementById('confirm-delete').addEventListener('click', confirmDeleteAction);

  document.getElementById('nutri-close').addEventListener('click', () => hideModal(nutriModal));
  
  notificationBtn.addEventListener('click', () => showModal(notificationsModal));
  document.getElementById('notifications-close').addEventListener('click', () => hideModal(notificationsModal));

  // Fechar modal clicando fora
  document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) hideModal(overlay);
    });
  });

  // Inicialização
  renderTable();
});
