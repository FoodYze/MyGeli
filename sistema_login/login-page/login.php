<?php
  // Estabelecendo conexão com o banco de dados
  $pdo = new PDO('mysql:host=localhost;dbname=foodyze', 'foodyzeadm', 'supfood0017admx');

  if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    // Lógica de Login com Token persistente
    if (isset($_POST['login'])) {
      $email = $_POST['email'];
      $senha = $_POST['senha'];
      $lembrar_de_mim = isset($_POST['lembrar_de_mim']);

      $stmt = $pdo->prepare("SELECT * FROM usuarios WHERE email = ?");
      $stmt->execute([$email]);
      $usuario = $stmt->fetch();

      if ($usuario && password_verify($senha, $usuario['senha'])) {
        //Login bem-sucedido
        session_start();
        $_SESSION['user_id'] = $usuario['id'];

        if ($lembrar_de_mim) {
          // Gerar os tokens
          $selector = bin2hex(random_bytes(16)); // 16 bytes = 32 caracteres hex
          $authenticator = bin2hex(random_bytes(32)); // 32 bytes = 64 caracteres hex
          $hashed_authenticator = hash('sha256', $authenticator);
          // Calcular expiração e salvar no BD
          $expires = date('Y-m-d H:i:s', strtotime('+30 days'));
          $stmt = $pdo->prepare("INSERT INTO login_tokens (user_id, selector, hashed_token, expires) VALUES (?, ?, ?, ?)");
          $stmt->execute([$usuario['id'], $selector, $hashed_authenticator, $expires]);
          // Criar o cookie (HttpOnly e Secure)
          $cookie_value = $selector . ':' . $authenticator;
          setcookie('remember_me', $cookie_value, [
                    'expires' => strtotime('+30 days'),
                    'path' => '/',
                    'httponly' => true,
                    'secure' => true,
                    'samesite' => 'Lax'
          ]);
        }
        header('Location: ../general-page/index.php');
        exit();
      } else {
        echo "Email ou senha incorretos.";
      }
    }
  }
?>
