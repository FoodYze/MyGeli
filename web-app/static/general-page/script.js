document.addEventListener('DOMContentLoaded', () => {
  // --- Seu código de Loader (permanece o mesmo) ---
  const loaderWrapper = document.getElementById('loader-wrapper');
  const progressBar = document.getElementById('progress-bar');
  const progressPercentage = document.getElementById('progress-percentage');

  let currentProgress = 0;
  const totalSteps = 100;
  const stepInterval = 20;

  function updateProgress() {
    if (currentProgress < 100) {
      currentProgress += Math.random() * 5 + 1;
      if (currentProgress > 100) {
        currentProgress = 100;
      }
      progressBar.style.width = currentProgress + '%';
      progressPercentage.textContent = Math.floor(currentProgress) + '%';
      setTimeout(updateProgress, stepInterval);
    } else {
      loaderWrapper.classList.add('hidden');
      document.body.classList.add('loaded');
    }
  }
  updateProgress();

  // ----------------------------------------------------- //

  // --- LÓGICA DO DASHBOARD ---
  try {
    const dataElement = document.getElementById('app-data');
    if (dataElement && dataElement.textContent.trim() !== "") {

      // 1. Lê o JSON que o Flask injetou
      const data = JSON.parse(dataElement.textContent);

      // 2. Popula os cards do dashboard
      if (data) {
        // Atualiza o "Olá, [Nome]"
        document.getElementById('dash-heading').textContent = `Olá, ${data.user_name || ''}!`;

        // Atualiza os cards
        document.getElementById('total-items-value').textContent = data.total_items || '0';
        document.getElementById('low-stock-value').textContent = data.low_stock_count || '0';
        document.getElementById('total-recipes-value').textContent = data.total_recipes || '0';

        // Trata o item mais estocado (encurta se for muito longo)
        let highestItem = data.highest_stock_item || 'Nenhum';
        if (highestItem.length > 15) {
          highestItem = highestItem.substring(0, 15) + '...';
        }
        const highestStockEl = document.getElementById('highest-stock-value');
        highestStockEl.textContent = highestItem;
        // Diminui a fonte se o nome for grande, para caber
        if (highestItem.length > 10) {
          highestStockEl.style.fontSize = "1.4rem";
        }
      }
    }
  } catch (e) {
    console.error("Erro ao carregar dados do dashboard:", e);
    // Popula com valores de erro
    document.getElementById('total-items-value').textContent = 'Erro';
    document.getElementById('low-stock-value').textContent = 'Erro';
    document.getElementById('total-recipes-value').textContent = 'Erro';
    document.getElementById('highest-stock-value').textContent = 'Erro';
  }
  // --- FIM DA LÓGICA DO DASHBOARD ---


  // --- LÓGICA DO TEMA (permanece a mesma) ---
  const themeToggle = document.querySelector("#theme-toggle-btn");

  themeToggle.addEventListener("click", () => {
    const isLightTheme = document.body.classList.toggle("light-theme");
    localStorage.setItem("themeColor", isLightTheme ? "light_mode" : "dark_mode");
    themeToggle.textContent = isLightTheme ? "dark_mode" : "light_mode";
  });

  const isLightTheme = localStorage.getItem("themeColor") === "light_mode";
  document.body.classList.toggle("light-theme", isLightTheme);
  themeToggle.textContent = isLightTheme ? "dark_mode" : "light_mode";
});