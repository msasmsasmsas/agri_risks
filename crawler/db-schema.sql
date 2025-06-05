# Скрипт для создания связанных таблиц в MariaDB

SET NAMES 'utf8mb4';
USE agriscouting;

-- Создание таблицы для описаний болезней
CREATE TABLE IF NOT EXISTS `disease_description` (
  `id` varchar(255) NOT NULL,
  `disease_id` varchar(255) NOT NULL,
  `description_ru` text DEFAULT NULL,
  `description_ua` text DEFAULT NULL,
  `description_en` text DEFAULT NULL,
  `symptoms_ru` text DEFAULT NULL,
  `symptoms_ua` text DEFAULT NULL,
  `symptoms_en` text DEFAULT NULL,
  `development_conditions_ru` text DEFAULT NULL,
  `development_conditions_ua` text DEFAULT NULL,
  `development_conditions_en` text DEFAULT NULL,
  `control_measures_ru` text DEFAULT NULL,
  `control_measures_ua` text DEFAULT NULL,
  `control_measures_en` text DEFAULT NULL,
  `photo_path` varchar(255) DEFAULT NULL,
  `version` bigint(20) NOT NULL DEFAULT 1,
  PRIMARY KEY (`id`),
  KEY `disease_id` (`disease_id`),
  CONSTRAINT `disease_description_ibfk_1` FOREIGN KEY (`disease_id`) REFERENCES `disease` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci ROW_FORMAT=DYNAMIC;

-- Создание таблицы для изображений болезней
CREATE TABLE IF NOT EXISTS `disease_images` (
  `id` varchar(255) NOT NULL,
  `disease_id` varchar(255) NOT NULL,
  `image_path` varchar(255) NOT NULL,
  `image_url` varchar(255) NOT NULL,
  `version` bigint(20) NOT NULL DEFAULT 1,
  PRIMARY KEY (`id`),
  KEY `disease_id` (`disease_id`),
  CONSTRAINT `disease_images_ibfk_1` FOREIGN KEY (`disease_id`) REFERENCES `disease` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Создание таблицы для описаний вредителей
CREATE TABLE IF NOT EXISTS `vermin_description` (
  `id` varchar(255) NOT NULL,
  `vermin_id` varchar(255) NOT NULL,
  `description_ru` text DEFAULT NULL,
  `description_ua` text DEFAULT NULL,
  `description_en` text DEFAULT NULL,
  `damage_symptoms_ru` text DEFAULT NULL,
  `damage_symptoms_ua` text DEFAULT NULL,
  `damage_symptoms_en` text DEFAULT NULL,
  `biology_ru` text DEFAULT NULL,
  `biology_ua` text DEFAULT NULL,
  `biology_en` text DEFAULT NULL,
  `control_measures_ru` text DEFAULT NULL,
  `control_measures_ua` text DEFAULT NULL,
  `control_measures_en` text DEFAULT NULL,
  `photo_path` varchar(255) DEFAULT NULL,
  `version` bigint(20) NOT NULL DEFAULT 1,
  PRIMARY KEY (`id`),
  KEY `vermin_id` (`vermin_id`),
  CONSTRAINT `vermin_description_ibfk_1` FOREIGN KEY (`vermin_id`) REFERENCES `vermin` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci ROW_FORMAT=DYNAMIC;

-- Создание таблицы для изображений вредителей
CREATE TABLE IF NOT EXISTS `vermin_images` (
  `id` varchar(255) NOT NULL,
  `vermin_id` varchar(255) NOT NULL,
  `image_path` varchar(255) NOT NULL,
  `image_url` varchar(255) NOT NULL,
  `version` bigint(20) NOT NULL DEFAULT 1,
  PRIMARY KEY (`id`),
  KEY `vermin_id` (`vermin_id`),
  CONSTRAINT `vermin_images_ibfk_1` FOREIGN KEY (`vermin_id`) REFERENCES `vermin` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Создание таблицы для описаний сорняков
CREATE TABLE IF NOT EXISTS `weed_description` (
  `id` varchar(255) NOT NULL,
  `weed_id` varchar(255) NOT NULL,
  `description_ru` text DEFAULT NULL,
  `description_ua` text DEFAULT NULL,
  `description_en` text DEFAULT NULL,
  `biological_features_ru` text DEFAULT NULL,
  `biological_features_ua` text DEFAULT NULL,
  `biological_features_en` text DEFAULT NULL,
  `harmfulness_ru` text DEFAULT NULL,
  `harmfulness_ua` text DEFAULT NULL,
  `harmfulness_en` text DEFAULT NULL,
  `control_measures_ru` text DEFAULT NULL,
  `control_measures_ua` text DEFAULT NULL,
  `control_measures_en` text DEFAULT NULL,
  `photo_path` varchar(255) DEFAULT NULL,
  `version` bigint(20) NOT NULL DEFAULT 1,
  PRIMARY KEY (`id`),
  KEY `weed_id` (`weed_id`),
  CONSTRAINT `weed_description_ibfk_1` FOREIGN KEY (`weed_id`) REFERENCES `weed` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci ROW_FORMAT=DYNAMIC;

-- Создание таблицы для изображений сорняков
CREATE TABLE IF NOT EXISTS `weed_images` (
  `id` varchar(255) NOT NULL,
  `weed_id` varchar(255) NOT NULL,
  `image_path` varchar(255) NOT NULL,
  `image_url` varchar(255) NOT NULL,
  `version` bigint(20) NOT NULL DEFAULT 1,
  PRIMARY KEY (`id`),
  KEY `weed_id` (`weed_id`),
  CONSTRAINT `weed_images_ibfk_1` FOREIGN KEY (`weed_id`) REFERENCES `weed` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
