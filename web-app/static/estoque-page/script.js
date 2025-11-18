document.addEventListener('DOMContentLoaded', () => {
  
    // --- 1. Tela de Carregamento ---
    const loaderWrapper = document.getElementById('loader-wrapper');
    const progressBar = document.getElementById('progress-bar');
    const progressPercentage = document.getElementById('progress-percentage');
    let currentProgress = 0;
  
    function updateProgress() {
      if (currentProgress < 100) {
        currentProgress += Math.random() * 15 + 5;
        if (currentProgress > 100) currentProgress = 100;
        progressBar.style.width = currentProgress + '%';
        progressPercentage.textContent = Math.floor(currentProgress) + '%';
        setTimeout(updateProgress, 100);
      } else {
        setTimeout(() => {
            if (loaderWrapper) loaderWrapper.classList.add('hidden');
            document.body.classList.add('loaded');
        }, 300);
      }
    }
    updateProgress();
  
    // --- 2. Variáveis de Estado e Seletores ---
    let stockData = []; // Guarda os dados reais do banco
  
    const tableBody = document.getElementById('stock-table-body');
    const addItemBtn = document.getElementById('add-item-btn');
    
    // Modal Adicionar/Editar
    const itemModal = document.getElementById('item-modal');
    const modalTitle = document.getElementById('modal-title');
    const itemForm = document.getElementById('item-form');
    const modalCancelBtn = document.getElementById('modal-cancel');
    
    // Campos do Formulário Adicionar
    const itemIdField = document.getElementById('item-id');
    const itemNameField = document.getElementById('item-name');
    const itemQuantityField = document.getElementById('item-quantity');
    const itemUnitField = document.getElementById('item-unit'); 
    
    // NOVO: Modal Consumir
    const consumeModal = document.getElementById('consume-modal');
    const consumeForm = document.getElementById('consume-form');
    const consumeCancelBtn = document.getElementById('consume-cancel');
    const consumeItemSelect = document.getElementById('consume-item-select');
    const consumeQuantityField = document.getElementById('consume-quantity');
    const consumeUnitField = document.getElementById('consume-unit');

    // Modal Confirmação Exclusão
    const confirmModal = document.getElementById('confirm-modal');
    const confirmDeleteBtn = document.getElementById('confirm-delete');
    const confirmCancelBtn = document.getElementById('confirm-cancel');
    let idToDelete = null;
  
    // --- 3. Funções de API (Back-End) ---
  
    // Busca dados do servidor
    async function fetchStockData() {
        try {
            const response = await fetch('/api/stock');
            if (!response.ok) throw new Error('Falha ao buscar estoque');
            
            const data = await response.json();
            stockData = data;
            renderTable();
        } catch (error) {
            console.error("Erro ao carregar estoque:", error);
            tableBody.innerHTML = `<tr><td colspan="3" style="text-align: center; color: #d32f2f; padding: 20px;">Erro ao carregar dados do servidor.</td></tr>`;
        }
    }
  
    // Envia ações (adicionar, atualizar, deletar, consumir)
    async function sendStockAction(action, payload) {
        try {
            const response = await fetch('/api/stock/manage', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: action, ...payload })
            });
  
            const result = await response.json();
  
            if (!response.ok || result.error) {
                alert(`Erro: ${result.error || 'Falha na operação'}`);
                return false;
            }
  
            // Se deu certo, recarrega a tabela
            await fetchStockData();
            return true;
  
        } catch (error) {
            console.error("Erro na requisição:", error);
            alert("Erro de conexão com o servidor.");
            return false;
        }
    }
  
    // --- 4. Renderização da Tabela ---
    function renderTable() {
      tableBody.innerHTML = '';
  
      if (!stockData || stockData.length === 0) {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td colspan="3" style="text-align: center; padding: 20px; color: #888;">Seu estoque está vazio. Adicione um item.</td>`;
        tableBody.appendChild(tr);
        return;
      }
  
      stockData.forEach(item => {
        const tr = document.createElement('tr');
        
        // Formata número (ex: 1.5)
        const qtyFormatted = parseFloat(item.quantity).toLocaleString('pt-BR');
        const quantityDisplay = `${qtyFormatted} ${item.unit}`;
  
        tr.innerHTML = `
          <td>${item.name}</td>
          <td>${quantityDisplay}</td>
          <td class="actions-cell">
            <!-- Botão CONSUMIR (-) -->
            <button class="action-btn btn-consume" 
                    data-name="${item.name}" 
                    data-unit="${item.raw_unit}" 
                    title="Usar item">
               <span style="color: red;" class="material-symbols-rounded">remove</span>
            </button>
            
            <!-- Botão EDITAR -->
            <button class="action-btn btn-edit" 
                    data-id="${item.id}" 
                    data-name="${item.name}" 
                    data-qty="${item.raw_quantity}" 
                    data-unit="${item.raw_unit}" 
                    title="Editar">
               <span class="material-symbols-rounded">edit</span>
            </button>
            
            <!-- Botão EXCLUIR -->
            <button class="action-btn btn-delete" 
                    data-id="${item.id}" 
                    title="Excluir">
               <span class="material-symbols-rounded">delete</span>
            </button>
          </td>
        `;
        tableBody.appendChild(tr);
      });
  
      addTableEventListeners();
    }
  
    function addTableEventListeners() {
      document.querySelectorAll('.btn-edit').forEach(btn => btn.addEventListener('click', handleEdit));
      document.querySelectorAll('.btn-delete').forEach(btn => btn.addEventListener('click', handleDelete));
      document.querySelectorAll('.btn-consume').forEach(btn => btn.addEventListener('click', handleConsumeClick));
    }
  
    // --- 5. Manipuladores de Eventos ---
    
    // -- CONSUMIR (USAR ITEM) --
    function handleConsumeClick(event) {
        const btn = event.currentTarget;
        const preSelectedName = btn.dataset.name;
        const preSelectedUnit = btn.dataset.unit; // Unidade original do banco
        
        // Limpa e popula o <select> com os itens atuais
        consumeItemSelect.innerHTML = '';
        stockData.forEach(item => {
            const option = document.createElement('option');
            option.value = item.name; // O backend usa o nome para buscar e abater
            option.textContent = `${item.name} (Atual: ${item.quantity} ${item.unit})`;
            
            if (item.name === preSelectedName) {
                option.selected = true;
            }
            consumeItemSelect.appendChild(option);
        });

        // Reseta campos
        consumeUnitField.value = preSelectedUnit; // Tenta selecionar a mesma unidade
        consumeQuantityField.value = ''; 
        
        showModal(consumeModal);
        
        // Foca no campo de quantidade
        setTimeout(() => consumeQuantityField.focus(), 100);
    }

    async function handleConsumeSubmit(event) {
        event.preventDefault();
        
        const itemName = consumeItemSelect.value;
        const qty = parseFloat(consumeQuantityField.value);
        const unit = consumeUnitField.value;

        if (!itemName || isNaN(qty) || qty <= 0) {
            alert("Por favor, preencha uma quantidade válida.");
            return;
        }

        const success = await sendStockAction('consumir', {
            item: itemName,
            quantidade: qty,
            unidade: unit
        });

        if (success) {
            hideModal(consumeModal);
        }
    }

    // -- EDITAR --
    function handleEdit(event) {
      const btn = event.currentTarget;
      modalTitle.textContent = "Editar Item";
      
      itemIdField.value = btn.dataset.id;
      itemNameField.value = btn.dataset.name;
      itemQuantityField.value = btn.dataset.qty;
      itemUnitField.value = btn.dataset.unit; 
      
      showModal(itemModal);
    }
  
    // -- EXCLUIR --
    function handleDelete(event) {
      idToDelete = event.currentTarget.dataset.id;
      showModal(confirmModal);
    }
  
    async function confirmDelete() {
      if (idToDelete) {
          const success = await sendStockAction('delete', { id: idToDelete });
          if (success) hideModal(confirmModal);
          idToDelete = null;
      }
    }
  
    // -- SALVAR (ADICIONAR/EDITAR) --
    async function handleFormSubmit(event) {
      event.preventDefault();
      
      const id = itemIdField.value;
      const payload = {
          id: id ? id : null,
          item: itemNameField.value.trim(),
          quantidade: parseFloat(itemQuantityField.value),
          unidade: itemUnitField.value
      };
  
      const action = id ? 'atualizar' : 'adicionar'; 
      
      const success = await sendStockAction(action, payload);
  
      if (success) {
        hideModal(itemModal);
      }
    }
  
    // --- 6. Funções de Modal ---
    function showModal(modal) {
      modal.classList.add('visible');
    }
  
    function hideModal(modal) {
      modal.classList.remove('visible');
    }
  
    function resetAndShowAddModal() {
      modalTitle.textContent = "Adicionar Novo Item";
      itemForm.reset();
      itemIdField.value = ''; 
      itemUnitField.value = 'Unidades'; 
      showModal(itemModal);
    }
  
    // --- 7. Listeners Iniciais ---
    
    // Botão Principal Adicionar
    if (addItemBtn) addItemBtn.addEventListener('click', resetAndShowAddModal);
    
    // Formulário Adicionar/Editar
    if (modalCancelBtn) modalCancelBtn.addEventListener('click', () => hideModal(itemModal));
    if (itemForm) itemForm.addEventListener('submit', handleFormSubmit);
    
    // Formulário Consumir
    if (consumeCancelBtn) consumeCancelBtn.addEventListener('click', () => hideModal(consumeModal));
    if (consumeForm) consumeForm.addEventListener('submit', handleConsumeSubmit);
  
    // Modal Exclusão
    if (confirmDeleteBtn) confirmDeleteBtn.addEventListener('click', confirmDelete);
    if (confirmCancelBtn) confirmCancelBtn.addEventListener('click', () => hideModal(confirmModal));
  
    // --- 8. Inicialização ---
    fetchStockData(); 
});