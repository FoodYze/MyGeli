<?php
    // Conexão com banco
    $pdo = new PDO('mysql:host=localhost;dbname=foodyze', 'foodyzeadm', 'supfood0017admx');

    if ($_SERVER['REQUEST_METHOD'] === 'POST') {
        if (isset($_POST['cadastrar'])) {
            $nome = $_POST['nome'];
            $telefone = $_POST['telefone'];
            $email = $_POST['email'];
            $senha = $_POST['senha'];
            $confirmSenha = $_POST['confirm-senha'];
            $lembrar_de_mim = isset($_POST['remember']);

            // Validação básica
            if ($senha !== $confirmSenha) {
                die("As senhas não coincidem!");
            }
            if (strlen($senha) < 6) {
                die("A senha deve ter pelo menos 6 caracteres!");
            }

            // Hash seguro
            $senhaHash = password_hash($senha, PASSWORD_DEFAULT);

            // Inserir usuário
            $stmt = $pdo->prepare("INSERT INTO usuarios (nome, telefone, email, senha) VALUES (?, ?, ?, ?)");
            $stmt->execute([$nome, $telefone, $email, $senhaHash]);

            // Recuperar ID do usuário cadastrado
            $userId = $pdo->lastInsertId();

            // Inicia sessão automaticamente
            session_start();
            $_SESSION['user_id'] = $userId;

            // Se lembrar-me estiver marcado → cria token persistente
            if ($lembrar_de_mim) {
                $selector = bin2hex(random_bytes(16));
                $authenticator = bin2hex(random_bytes(32));
                $hashed_authenticator = hash('sha256', $authenticator);
                $expires = date('Y-m-d H:i:s', strtotime('+30 days'));

                $stmt = $pdo->prepare("INSERT INTO login_tokens (user_id, selector, hashed_token, expires) VALUES (?, ?, ?, ?)");
                $stmt->execute([$userId, $selector, $hashed_authenticator, $expires]);

                $cookie_value = $selector . ':' . $authenticator;
                setcookie('remember_me', $cookie_value, [
                    'expires' => strtotime('+30 days'),
                    'path' => '/',
                    'httponly' => true,
                    'secure' => true,
                    'samesite' => 'Lax'
                ]);
            }

            // Redireciona para a página principal
            header('Location: ../general-page/index.php');
            exit();
        }
    }
?>