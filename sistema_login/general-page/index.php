<?php
  session_start();

  // Conexão com o banco de dados
  $pdo = new PDO('mysql:host=localhost;dbname=foodyze', 'foodyzeadm', 'supfood0017admx');

  $is_logged_in = false;

  // Tentar carregar a sessão normal
  if (isset($_SESSION['user_id'])) {
    $is_logged_in = true;
  } else {
    // Tenta o login persistente
    if (isset($_COOKIE['remember_me'])) {
      list($selector, $authenticator) = explode(':', $_COOKIE['remember_me'], 2);

      // Busca o token no banco de dados pelo seletor
      $stmt = $pdo->prepare("SELECT * FROM login_tokens WHERE selector = ?");
      $stmt->execute([$selector]);
      $token = $stmt->fetch();

      if ($token) {
        // Verifica a expiração e o token
        if (hash_equals($token['hashed_token'], hash('sha256', $authenticator))) {
          // Login válido! Renova o par de tokens

          // Invalida o token antigo e gera um novo
          $new_selector = bin2hex(random_bytes(16));
          $new_authenticator = bin2hex(random_bytes(32));
          $new_hashed_authenticator = hash('sha256', $new_authenticator);
          $new_expires = date('Y-m-d H:i:s', strtotime('+30 days'));

          // Atualiza o banco de dados
          $stmt = $pdo->prepare("UPDATE login_tokens SET selector = ?, hashed_token = ?, expires = ? WHERE token_id = ?");
          $stmt->execute([$new_selector, $new_hashed_authenticator, $new_expires, $token['token_id']]);

          // Define o novo cookie
          $new_cookie_value = $new_selector . ':' . $new_authenticator;
          setcookie('remember_me', $new_cookie_value, [
            'expires' => strtotime('+30 days'),
            'path' => '/',
            'httponly' => true,
            'secure' => true,
            'samesite' => 'Lax'
          ]);

          // Define a sessão do usuário
          $_SESSION['user_id'] = $token['user_id'];
          $is_logged_in = true;
        } else {
          // Se a validação falhar, invalida os tokens do usuário
          $stmt = $pdo->prepare("DELETE FROM login_tokens WHERE user_id = ?");
          $stmt->execute([$token['user_id']]);
          setcookie('remember_me', '', time() - 3600);
        }
      }
    }

    // Se o usuário não estiver logado, redireciona para a página de login
    if (!$is_logged_in) {
      header('Location: ../login-page/index.html');
      exit();
    }
  }
?>

<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="stylesheet" href="style.css">
  <link rel="icon" href="data:image/x-icon,;">
  <title>Início | MyGeli</title>
  <script src="https://cdn.jsdelivr.net/npm/gauge.js/dist/gauge.min.js"></script>
</head>
<body>

  <div class="loader-wrapper" id="loader-wrapper">
    <div class="loader-container">
      <p class="loader-text">Carregando</p>
      <div class="progress-bar-container">
        <div class="progress-bar" id="progress-bar"></div>
      </div>
      <p class="progress-percentage" id="progress-percentage">0%</p>
    </div>
  </div>

  <nav class="nav-drawer" aria-label="Menu de Navegação Principal">
    <h2 class="visually-hidden">Menu de Navegação</h2>
    <ul>
      <li><a href="#">Geral</a></li>
      <li><a href="#">Chat</a></li>
      <li><a href="#">Receitas</a></li>
      <li><a href="#">Estoque</a></li>
    </ul>
    <ul style="bottom: 20px;">
      <li><a href="logout.php">Sair</a></li>
    </ul>
  </nav>

  <main class="content" id="main-content">
    <h1>Visão Geral</h1>
    <p>Este é o seu conteúdo principal.</p>
  </main>

  <script src="script.js"></script>
</body>
</html>