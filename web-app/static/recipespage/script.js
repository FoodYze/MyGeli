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

  const accordionHeaders = document.querySelectorAll('.recipe-header');

      accordionHeaders.forEach(header => {
        header.addEventListener('click', function () {
          const content = this.nextElementSibling;
          
          // Fecha outros acordeões que possam estar abertos
          // Comente ou remova as 6 linhas abaixo se quiser permitir múltiplos abertos
          accordionHeaders.forEach(otherHeader => {
            if (otherHeader !== this && otherHeader.classList.contains('active')) {
              otherHeader.classList.remove('active');
              otherHeader.nextElementSibling.style.maxHeight = null;
              otherHeader.nextElementSibling.classList.remove('show');
            }
          });

          // Abre/Fecha o acordeão clicado
          this.classList.toggle('active');

          if (this.classList.contains('active')) {
            // Adiciona a classe 'show' para o padding aparecer
            content.classList.add('show');
            // Define o max-height com base na altura real do conteúdo + padding
            // Adicionamos 40px (20px top + 20px bottom)
            content.style.maxHeight = (content.scrollHeight + 40) + 'px';
          } else {
            content.style.maxHeight = null;
            // Remove a classe 'show' para o padding sumir
            content.classList.remove('show');
          }
        });
      });
});