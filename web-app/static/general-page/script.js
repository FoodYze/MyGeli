document.addEventListener('DOMContentLoaded', () => {
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
  let stockString = "Nenhum item em estoque informado."; // Mensagem padrão
  
    try {
        const stockDataElement = document.getElementById('app-data');
        if (stockDataElement && stockDataElement.textContent.trim() !== "") {
            // 1. Lê o JSON que o Flask injetou
            const stockData = JSON.parse(stockDataElement.textContent);
            // 2. Transforma o objeto em array de [chave, valor]
            const stockEntries = Object.entries(stockData);

            if (stockEntries.length > 0) {
                // 3. Formata como: "Arroz: 1300.00 Gramas, Frango: 300.00 Gramas"
                stockString = stockEntries.map(([item, qty]) => `${item}: ${qty}`).join(', ');
            }
        }
    } catch (e) {
        console.error("Erro ao carregar o estoque do usuário:", e);
        // stockString continua com a mensagem padrão
    }

  const container = document.querySelector(".container");
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
