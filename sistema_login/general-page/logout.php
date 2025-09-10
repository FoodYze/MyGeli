<?php
  session_start();

  // Destruir a sessão
  session_unset();
  session_destroy();

  // Invalida o cookie de login persistente
  setcookie('remember_me', '', [
            'expires' => time() - 3600,
            'path' => '/',
            'httponly' => true,
            'secure' => true,
            'samesite' => 'Lax'
  ]);

  // Redireciona para a página de login
  header('Location: ../login-page/index.html');
  exit();
?>
