document.addEventListener('DOMContentLoaded', () => {
 
  // Tratamento do carregamento da página
  const loaderWrapper = document.getElementById('loader-wrapper');
  const progressBar = document.getElementById('progress-bar');
  const progressPercentage = document.getElementById('progress-percentage');
  const loginContainer = document.querySelector('.login-container'); // Agora 'loginContainer' está definido
  const linkTermos = document.getElementById('link-termos');
  const btnFecharTermos = document.getElementById('fechar_termos');
  const termosDiv = document.querySelector('.termos');
 
  linkTermos.addEventListener('click', (event) => {
    // Impede o link de recarregar a página (comportamento padrão de <a>)
    event.preventDefault(); 

    // Mostra a div dos termos
    termosDiv.style.display = 'block';
  });

  btnFecharTermos.addEventListener('click', (event) => {
    event.preventDefault();

    termosDiv.style.display = 'none';
  });
  
  let currentProgress = 0;
  const stepInterval = 20; // Velocidade da barra de progresso

  function updateProgress() {
    if (currentProgress < 100) {
      currentProgress += Math.random() * 5 + 1; // Incrementa o progresso de forma aleatória
      if (currentProgress > 100) {
        currentProgress = 100;
      }

      progressBar.style.width = currentProgress + '%';
      progressPercentage.textContent = Math.floor(currentProgress) + '%';
     
      setTimeout(updateProgress, stepInterval);
    } else {
      // Quando o carregamento chega a 100%
      loaderWrapper.classList.add('hidden'); // Esconde o loader
      document.body.classList.add('loaded'); // Adiciona classe ao body para possíveis transições no CSS
      // Se houver uma animação CSS para 'animated' no .login-container, descomente a linha abaixo
      // loginContainer.classList.add('animated'); 
    }
  }

  updateProgress(); // Inicia a animação da barra de progresso
 
  // Tratamento do preenchimento e validação do formulário
  const form = document.querySelector('.login-form');
  const nomeInput = document.getElementById('username');
  const telefoneInput = document.getElementById('cellphone');
  const emailInput = document.getElementById('email');
  const passwordInput = document.getElementById('password');
  const confirmPasswordInput = document.getElementById('password2'); // Campo de confirmação de senha
  const errorMessage = document.querySelector('.error-message');
 
  // Lógica para alternar visibilidade da senha para AMBOS os campos de senha
  document.querySelectorAll('.toggle-password').forEach(button => {
    button.addEventListener('click', function() {
      // Encontra o input de senha dentro do mesmo .password-field ou .confirmPassword-field
      const parentField = this.closest('.password-field') || this.closest('.confirmPassword-field');
      const input = parentField.querySelector('input[type="password"], input[type="text"]');
      
      const eyeOpen = this.querySelector('.eye-open');
      const eyeClosed = this.querySelector('.eye-closed');
   
      const type = input.getAttribute('type') === 'password' ? 'text' : 'password';
      input.setAttribute('type', type);
   
      // Alterna os ícones do olho
      if (type === 'text') {
        eyeOpen.style.display = 'none';
        eyeClosed.style.display = 'block';
      } else {
        eyeOpen.style.display = 'block';
        eyeClosed.style.display = 'none';
      }
    });
  });
 
  form.addEventListener('submit', function(e) {
    let valid = true;
   
    // Limpa quaisquer estados de erro anteriores
    errorMessage.style.display = 'none';
    passwordInput.classList.remove('error');
    confirmPasswordInput.classList.remove('error'); // Limpa a classe 'error' do campo de confirmação
   
    // 1. Validação de senhas coincidentes
    if (passwordInput.value !== confirmPasswordInput.value) {
      valid = false;
      passwordInput.classList.add('error');
      confirmPasswordInput.classList.add('error');
      errorMessage.textContent = 'As senhas não coincidem!';
      errorMessage.style.display = 'block';
    }

    // 2. Validação do comprimento da senha (só verifica se as senhas já não falharam na primeira validação)
    if (valid && passwordInput.value.length < 6) {
      valid = false;
      passwordInput.classList.add('error');
      errorMessage.textContent = 'Sua senha deve ter ao mínimo 6 caracteres!';
      errorMessage.style.display = 'block';
    }
   
    // Se não for válido, impede o envio do formulário
    if (!valid) {
      e.preventDefault();
    }
  });
});
