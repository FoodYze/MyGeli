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
      // Quando o carregamento chega a 100%
      loaderWrapper.classList.add('hidden');
      document.body.classList.add('loaded');
    }
  }

  updateProgress();
});