-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Tempo de geração: 30-Set-2025 às 16:01
-- Versão do servidor: 10.4.32-MariaDB
-- versão do PHP: 8.2.12

-- Configurações iniciais da sessão
SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Banco de dados: `mygeli`
--
CREATE DATABASE IF NOT EXISTS `mygeli` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE `mygeli`;

-- --------------------------------------------------------

--
-- Estrutura da tabela `usuarios`
--
CREATE TABLE IF NOT EXISTS `usuarios` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `nome` VARCHAR(255) DEFAULT NULL,
  `telefone` VARCHAR(30) DEFAULT NULL,
  `email` VARCHAR(255) NOT NULL,
  `senha` VARCHAR(255) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_email` (`email`),
  `preferencias` text DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Estrutura da tabela `historico_uso`
--
CREATE TABLE IF NOT EXISTS `historico_uso` (
  `id_historico` INT(11) NOT NULL AUTO_INCREMENT,
  `nome_receita` VARCHAR(255) NOT NULL,
  `nome_ingrediente` VARCHAR(255) NOT NULL,
  `quantidade_usada` DECIMAL(10,2) NOT NULL,
  `unidade_medida` VARCHAR(50) DEFAULT NULL,
  `data_hora_uso` TIMESTAMP NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id_historico`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Estrutura da tabela `log`
--
CREATE TABLE IF NOT EXISTS `log` (
  `id_action` INT(11) NOT NULL AUTO_INCREMENT,
  `id_user` INT(11) NOT NULL,
  `action` VARCHAR(16) NOT NULL,
  `status` VARCHAR(7) NOT NULL,
  `date_time` TIMESTAMP NOT NULL DEFAULT current_timestamp(),
  `ip_address` VARCHAR(255) DEFAULT NULL,
  PRIMARY KEY (`id_action`),
  KEY `idx_id_user` (`id_user`),
  CONSTRAINT `fk_log_usuarios` FOREIGN KEY (`id_user`) REFERENCES `usuarios` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Estrutura da tabela `login_tokens`
--
CREATE TABLE IF NOT EXISTS `login_tokens` (
  `token_id` INT(11) NOT NULL AUTO_INCREMENT,
  `user_id` INT(11) NOT NULL,
  `selector` VARCHAR(255) NOT NULL,
  `hashed_token` VARCHAR(255) NOT NULL,
  `expires` DATETIME NOT NULL,
  PRIMARY KEY (`token_id`),
  KEY `idx_user_id_tokens` (`user_id`),
  CONSTRAINT `fk_tokens_usuarios` FOREIGN KEY (`user_id`) REFERENCES `usuarios` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Estrutura da tabela `produtos`
--
CREATE TABLE IF NOT EXISTS `produtos` (
  `id_produto` INT(3) UNSIGNED ZEROFILL NOT NULL AUTO_INCREMENT,
  `nome_produto` VARCHAR(100) NOT NULL,
  `quantidade_produto` DECIMAL(10,2) UNSIGNED NOT NULL,
  `tipo_volume` VARCHAR(12) NOT NULL,
  `valor_energetico_kcal` DECIMAL(10,2) DEFAULT NULL,
  `acucares_totais_g` DECIMAL(10,2) DEFAULT NULL,
  `acucares_adicionados_g` DECIMAL(10,2) DEFAULT NULL,
  `carboidratos_g` DECIMAL(10,2) DEFAULT NULL,
  `proteinas_g` DECIMAL(10,2) DEFAULT NULL,
  `gorduras_totais_g` DECIMAL(10,2) DEFAULT NULL,
  `gorduras_saturadas_g` DECIMAL(10,2) DEFAULT NULL,
  `gorduras_trans_g` DECIMAL(10,2) DEFAULT NULL,
  `fibra_alimentar_g` DECIMAL(10,2) DEFAULT NULL,
  `sodio_g` DECIMAL(10,2) DEFAULT NULL,
  `data_criacao` TIMESTAMP NOT NULL DEFAULT current_timestamp(),
  `data_modificacao` TIMESTAMP NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id_produto`),
  UNIQUE KEY `uk_nome_produto` (`nome_produto`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Estrutura da tabela `receitas`
--
CREATE TABLE IF NOT EXISTS `receitas` (
  `idreceita` INT(3) NOT NULL AUTO_INCREMENT,
  `tituloreceita` VARCHAR(100) NOT NULL,
  `descreceita` TEXT NOT NULL,
  `idusuario` INT(11) NOT NULL,
  PRIMARY KEY (`idreceita`),
  KEY `idx_idusuario_receitas` (`idusuario`),
  CONSTRAINT `fk_receita_usuario` FOREIGN KEY (`idusuario`) REFERENCES `usuarios` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Inserindo dados (se as tabelas estiverem vazias)
--

INSERT INTO `usuarios` (`id`, `nome`, `telefone`, `email`, `senha`, `preferencias`) VALUES
(1, 'Marvin Cristhian Gomes Pinto', '19984214178', 'marvincristhian07.contato@gmail.com', '01020304', NULL),
(2, 'Luis Otavio', '19999999999', 'tevinho@gmail.com', '$2y$10$XdRmRirHIPOD4mU2wDzg1O5lkesoDXOVpz5Bf5bRRWnuu5fyYs2Ie', NULL),
(3, 'Jose', '19987654356', 'jose_silva@gmail.com', 'scrypt:32768:8:1$Zy0KvEkUNa1BlcYO$3eaef6f1ec54805d907d6c75f00b4abd38eee8183fbc864114a0d012f9eb7c94b077c9b361ef9ad8c373536605739a97941fc991e67a0ba1c41faecf3c4c7f4c', NULL),
(4, 'Tilambo Rego', '19999999999', 'tilambo.rego@gmail.com', 'scrypt:32768:8:1$AWI6ekcPl0l1N71X$26ed6252160afd096641d5d3967d5566d6cbba8c7ac2361302b54ae43438800bbb3fb315084c93875a5a89baa871dbe56f3988d0e6359cf1fec13f741c01b55f', NULL);

INSERT INTO `log` (`id_action`, `id_user`, `action`, `status`, `date_time`, `ip_address`) VALUES
(1, 4, 'Register', 'Success', '2025-09-30 16:42:50', '12ca17b49af2289436f303e0166030a21e525d266e209267433801a8fd4071a0');

INSERT INTO `login_tokens` (`token_id`, `user_id`, `selector`, `hashed_token`, `expires`) VALUES
(1, 2, '2a5432b76b2ae324377f1cbc6457bfbc', 'a0d0a9ad0591724ec69410fc15924a840ed602eecc52522844e8b451cfb33a08', '2025-10-10 15:27:46'),
(2, 2, 'd9e85dd707e839fe64fe85fb970fac87', '9bacb275f007d8d564f1aa439179b7cdd2343ba7a63614b1f538ae18da0b2b84', '2025-10-10 16:27:15'),
(3, 3, '035d86a8c1baeb5cada343f214ebac56', 'd94d29b87df1f52272327618f883a3e0c45c89bb84cab2f97fb8a91fb9c0bb3f', '2025-10-30 13:00:40'),
(4, 4, '7a463059163e25e54d9f03a11827fbd5', '8c46348e9d8a40723d760e7daf5d02437feee409064dff246448b23cb34cb3fc', '2025-10-30 13:42:50');

INSERT INTO `produtos` (`id_produto`, `nome_produto`, `quantidade_produto`, `tipo_volume`, `valor_energetico_kcal`, `acucares_totais_g`, `acucares_adicionados_g`, `carboidratos_g`, `proteinas_g`, `gorduras_totais_g`, `gorduras_saturadas_g`, `gorduras_trans_g`, `fibra_alimentar_g`, `sodio_g`, `data_criacao`, `data_modificacao`) VALUES
(001, 'Abacaxi', 2.00, 'Unidades', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '2025-09-30 11:38:57', '2025-09-30 11:38:57'),
(002, 'Frango', 1300.00, 'Gramas', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '2025-09-30 11:38:57', '2025-09-30 11:38:57'),
(003, 'Açucar', 300.00, 'Gramas', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '2025-09-30 11:38:57', '2025-09-30 11:38:57'),
(004, 'Ovo', 12.00, 'Unidades', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '2025-09-30 11:38:57', '2025-09-30 11:38:57'),
(005, 'Farinha', 2000.00, 'Gramas', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '2025-09-30 11:38:57', '2025-09-30 11:38:57'),
(006, 'Carne', 900.00, 'Gramas', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '2025-09-30 11:38:57', '2025-09-30 11:38:57'),
(007, 'Batata', 3.00, 'Unidades', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '2025-09-30 11:38:57', '2025-09-30 11:38:57'),
(008, 'Chocolate', 200.00, 'Gramas', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '2025-09-30 11:38:57', '2025-09-30 11:38:57'),
(009, 'Leite', 2000.00, 'Mililitros', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '2025-09-30 11:38:57', '2025-09-30 11:38:57'),
(010, 'Cenoura', 2.00, 'Unidades', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '2025-09-30 11:38:57', '2025-09-30 11:38:57');


-- --------------------------------------------------------
-- --------------------------------------------------------
-- NOVAS TABELAS PARA FUNCIONALIDADE DE PLANEJAMENTO
-- --------------------------------------------------------

CREATE TABLE IF NOT EXISTS `ingredients` (
  `id` INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `name` VARCHAR(255) NOT NULL,
  `unit` VARCHAR(50) DEFAULT NULL,
   KEY `idx_ingredient_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `recipe_ingredients` (
  `id` INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `recipe_id` INT(3) NOT NULL,
  `name` VARCHAR(255) NOT NULL,
  `quantity` DECIMAL(10,2) DEFAULT NULL,
  `unit` VARCHAR(50) DEFAULT NULL,
  CONSTRAINT `fk_ri_receita` FOREIGN KEY (`recipe_id`) REFERENCES `receitas`(`idreceita`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `meal_plans` (
  `id` INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `user_id` INT(11) NOT NULL,
  `recipe_id` INT(3) NOT NULL,
  `date` DATE NOT NULL,
  `meal_type` VARCHAR(50) DEFAULT NULL,
  KEY `idx_mealplan_date` (`date`),
  CONSTRAINT `fk_mp_usuario` FOREIGN KEY (`user_id`) REFERENCES `usuarios`(`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_mp_receita` FOREIGN KEY (`recipe_id`) REFERENCES `receitas`(`idreceita`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `shopping_list_items` (
  `id` INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `user_id` INT(11) NOT NULL,
  `ingredient_name` VARCHAR(255) NOT NULL,
  `quantity` DECIMAL(10,2) DEFAULT NULL,
  `unit` VARCHAR(50) DEFAULT NULL,
  `note` VARCHAR(255) DEFAULT NULL,
  CONSTRAINT `fk_sl_usuario` FOREIGN KEY (`user_id`) REFERENCES `usuarios`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- INSERÇÃO DOS DADOS DE TESTE PARA O PLANEJAMENTO
INSERT IGNORE INTO `receitas` (`idreceita`, `tituloreceita`, `descreceita`, `idusuario`) VALUES
(1, 'Salada Caesar com Frango', 'Uma salada clássica e completa', 1);

-- Apaga ingredientes antigos desta receita para evitar duplicatas ao reimportar o .sql
DELETE FROM `recipe_ingredients` WHERE `recipe_id` = 1;
INSERT INTO `recipe_ingredients` (`recipe_id`, `name`, `quantity`, `unit`) VALUES
(1, 'Alface Romana', 1, 'un'),
(1, 'Peito de Frango', 200, 'g'),
(1, 'Croutons', 50, 'g'),
(1, 'Queijo Parmesão', 30, 'g');

ALTER TABLE `receitas` MODIFY `idreceita` INT(3) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;
--
-- Configurando AUTO_INCREMENT para as tabelas
-- OBS: Isso garante que os próximos registros comecem a partir do número correto.
--

ALTER TABLE `log` MODIFY `id_action` INT(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;
ALTER TABLE `login_tokens` MODIFY `token_id` INT(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;
ALTER TABLE `produtos` MODIFY `id_produto` INT(3) UNSIGNED ZEROFILL NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=11;
ALTER TABLE `usuarios` MODIFY `id` INT(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

-- Finaliza a transação
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;