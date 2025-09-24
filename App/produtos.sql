-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Tempo de geração: 16-Set-2025 às 16:44
-- Versão do servidor: 10.4.32-MariaDB
-- versão do PHP: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Banco de dados: `foodyze`
--

-- --------------------------------------------------------

--
-- Estrutura da tabela `produtos`
--

CREATE TABLE `produtos` (
  `id_produto` int(11) NOT NULL,
  `nome_produto` varchar(255) NOT NULL,
  `quantidade_produto` decimal(10,2) NOT NULL,
  `tipo_volume` varchar(50) NOT NULL,
  `valor_energetico_kcal` decimal(10,2) DEFAULT NULL,
  `acucares_totais_g` decimal(10,2) DEFAULT NULL,
  `acucares_adicionados_g` decimal(10,2) DEFAULT NULL,
  `carboidratos_g` decimal(10,2) DEFAULT NULL,
  `proteinas_g` decimal(10,2) DEFAULT NULL,
  `gorduras_totais_g` decimal(10,2) DEFAULT NULL,
  `gorduras_saturadas_g` decimal(10,2) DEFAULT NULL,
  `gorduras_trans_g` decimal(10,2) DEFAULT NULL,
  `fibra_alimentar_g` decimal(10,2) DEFAULT NULL,
  `sodio_g` decimal(10,2) DEFAULT NULL,
  `data_criacao` timestamp NOT NULL DEFAULT current_timestamp(),
  `data_modificacao` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Extraindo dados da tabela `produtos`
--

INSERT INTO `produtos` (`id_produto`, `nome_produto`, `quantidade_produto`, `tipo_volume`, `valor_energetico_kcal`, `acucares_totais_g`, `acucares_adicionados_g`, `carboidratos_g`, `proteinas_g`, `gorduras_totais_g`, `gorduras_saturadas_g`, `gorduras_trans_g`, `fibra_alimentar_g`, `sodio_g`, `data_criacao`, `data_modificacao`) VALUES
(1, 'Maçã', 5.00, 'Unidades', 52.00, NULL, NULL, 14.00, 0.30, 0.20, NULL, NULL, NULL, 1.00, '2025-09-16 14:36:04', '2025-09-16 14:36:04'),
(2, 'Arroz', 1000.00, 'Gramas', 130.00, NULL, NULL, 28.00, 2.70, 0.30, NULL, NULL, NULL, 1.00, '2025-09-16 14:36:04', '2025-09-16 14:36:04');

--
-- Índices para tabelas despejadas
--

--
-- Índices para tabela `produtos`
--
ALTER TABLE `produtos`
  ADD PRIMARY KEY (`id_produto`),
  ADD UNIQUE KEY `nome_produto` (`nome_produto`);

--
-- AUTO_INCREMENT de tabelas despejadas
--

--
-- AUTO_INCREMENT de tabela `produtos`
--
ALTER TABLE `produtos`
  MODIFY `id_produto` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
