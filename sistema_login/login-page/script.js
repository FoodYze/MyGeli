document.addEventListener('DOMContentLoaded', () => {
  
  // Tratamento do carregamento da página
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
      loginContainer.classList.add('animated');
    }
  }

  updateProgress();
  
  // Tratamento do preenchimento do formulário
  const form = document.querySelector('.login-form');
  const passwordInput = document.getElementById('password');
  const togglePassword = document.querySelector('.toggle-password');
  const errorMessage = document.querySelector('.error-message');
  const eyeOpen = document.querySelector('.eye-open');
  const eyeClosed = document.querySelector('.eye-closed');
  
  togglePassword.addEventListener('click', function() {
    const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
    passwordInput.setAttribute('type', type);
    
    if (type === 'text') {
      eyeOpen.style.display = 'none';
      eyeClosed.style.display = 'block';
    } else {
      eyeOpen.style.display = 'block';
      eyeClosed.style.display = 'none';
    }
  });
  
  form.addEventListener('submit', function(e) {
    let valid = true;
    
    errorMessage.style.display = 'none';
    passwordInput.classList.remove('error');
    
    if (passwordInput.value.length < 6) {
      valid = false;
      passwordInput.classList.add('error');
      errorMessage.style.display = 'block';
    }
    
    if (!valid) {
      e.preventDefault();
    }
  });
});
