SET NAMES 'utf8mb4';
USE agriscouting;

-- Создание таблиц (из db-schema.sql)
CREATE TABLE IF NOT EXISTS `disease` (
  `id` varchar(255) NOT NULL,
  `name` varchar(255) NOT NULL,
  `name_en` varchar(255) DEFAULT NULL,
  `scientific_name` varchar(255) DEFAULT NULL,
  `is_active` tinyint(1) DEFAULT 1,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `disease_images` (
  `id` varchar(255) NOT NULL,
  `disease_id` varchar(255) NOT NULL,
  `image_path` varchar(255) NOT NULL,
  `image_url` varchar(255) NOT NULL,
  `version` bigint(20) NOT NULL DEFAULT 1,
  PRIMARY KEY (`id`),
  KEY `disease_id` (`disease_id`),
  CONSTRAINT `disease_images_ibfk_1` FOREIGN KEY (`disease_id`) REFERENCES `disease` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `vermin` (
  `id` varchar(255) NOT NULL,
  `name` varchar(255) NOT NULL,
  `name_en` varchar(255) DEFAULT NULL,
  `scientific_name` varchar(255) DEFAULT NULL,
  `is_active` tinyint(1) DEFAULT 1,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `vermin_images` (
  `id` varchar(255) NOT NULL,
  `vermin_id` varchar(255) NOT NULL,
  `image_path` varchar(255) NOT NULL,
  `image_url` varchar(255) NOT NULL,
  `version` bigint(20) NOT NULL DEFAULT 1,
  PRIMARY KEY (`id`),
  KEY `vermin_id` (`vermin_id`),
  CONSTRAINT `vermin_images_ibfk_1` FOREIGN KEY (`vermin_id`) REFERENCES `vermin` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `weed` (
  `id` varchar(255) NOT NULL,
  `name` varchar(255) NOT NULL,
  `name_en` varchar(255) DEFAULT NULL,
  `scientific_name` varchar(255) DEFAULT NULL,
  `is_active` tinyint(1) DEFAULT 1,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `weed_images` (
  `id` varchar(255) NOT NULL,
  `weed_id` varchar(255) NOT NULL,
  `image_path` varchar(255) NOT NULL,
  `image_url` varchar(255) NOT NULL,
  `version` bigint(20) NOT NULL DEFAULT 1,
  PRIMARY KEY (`id`),
  KEY `weed_id` (`weed_id`),
  CONSTRAINT `weed_images_ibfk_1` FOREIGN KEY (`weed_id`) REFERENCES `weed` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `disease_crops` (
  `disease_id` varchar(255) NOT NULL,
  `crops` varchar(255) NOT NULL,
  KEY `disease_id` (`disease_id`),
  CONSTRAINT `disease_crops_ibfk_1` FOREIGN KEY (`disease_id`) REFERENCES `disease` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `vermin_crops` (
  `vermin_id` varchar(255) NOT NULL,
  `crops` varchar(255) NOT NULL,
  KEY `vermin_id` (`vermin_id`),
  CONSTRAINT `vermin_crops_ibfk_1` FOREIGN KEY (`vermin_id`) REFERENCES `vermin` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `weed_crops` (
  `weed_id` varchar(255) NOT NULL,
  `crops` varchar(255) NOT NULL,
  KEY `weed_id` (`weed_id`),
  CONSTRAINT `weed_crops_ibfk_1` FOREIGN KEY (`weed_id`) REFERENCES `weed` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Импорт данных из CSV
LOAD DATA INFILE '/path/to/agriscouting_data/diseases.csv'
INTO TABLE `disease`
FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n'
IGNORE 1 LINES
(id, name, name_en, scientific_name, is_active);

LOAD DATA INFILE '/path/to/agriscouting_data/disease_descriptions.csv'
INTO TABLE `disease_description`
FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n'
IGNORE 1 LINES
(id, disease_id, description_ru, description_ua, description_en,
 symptoms_ru, symptoms_ua, symptoms_en,
 development_conditions_ru, development_conditions_ua, development_conditions_en,
 control_measures_ru, control_measures_ua, control_measures_en,
 photo_path, source_urls)
SET version = 1;

LOAD DATA INFILE '/path/to/agriscouting_data/disease_images.csv'
INTO TABLE `disease_images`
FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n'
IGNORE 1 LINES
(id, disease_id, image_url, image_path, @caption, @source, @source_url)
SET version = 1;

LOAD DATA INFILE '/path/to/agriscouting_data/disease_crops.csv'
INTO TABLE `disease_crops`
FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n'
IGNORE 1 LINES
(disease_id, crops);

LOAD DATA INFILE '/path/to/agriscouting_data/vermins.csv'
INTO TABLE `vermin`
FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n'
IGNORE 1 LINES
(id, name, name_en, scientific_name, is_active);

LOAD DATA INFILE '/path/to/agriscouting_data/vermin_descriptions.csv'
INTO TABLE `vermin_description`
FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n'
IGNORE 1 LINES
(id, vermin_id, description_ru, description_ua, description_en,
 damage_symptoms_ru, damage_symptoms_ua, damage_symptoms_en,
 biology_ru, biology_ua, biology_en,
 control_measures_ru, control_measures_ua, control_measures_en,
 photo_path, source_urls)
SET version = 1;

LOAD DATA INFILE '/path/to/agriscouting_data/vermin_images.csv'
INTO TABLE `vermin_images`
FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n'
IGNORE 1 LINES
(id, vermin_id, image_url, image_path, @caption, @source, @source_url)
SET version = 1;

LOAD DATA INFILE '/path/to/agriscouting_data/vermin_crops.csv'
INTO TABLE `vermin_crops`
FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n'
IGNORE 1 LINES
(vermin_id, crops);

LOAD DATA INFILE '/path/to/agriscouting_data/weeds.csv'
INTO TABLE `weed`
FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n'
IGNORE 1 LINES
(id, name, name_en, scientific_name, is_active);

LOAD DATA INFILE '/path/to/agriscouting_data/weed_descriptions.csv'
INTO TABLE `weed_description`
FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n'
IGNORE 1 LINES
(id, weed_id, description_ru, description_ua, description_en,
 biological_features_ru, biological_features_ua, biological_features_en,
 harmfulness_ru, harmfulness_ua, harmfulness_en,
 control_measures_ru, control_measures_ua, control_measures_en,
 photo_path, source_urls)
SET version = 1;

LOAD DATA INFILE '/path/to/agriscouting_data/weed_images.csv'
INTO TABLE `weed_images`
FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n'
IGNORE 1 LINES
(id, weed_id, image_url, image_path, @caption, @source, @source_url)
SET version = 1;

LOAD DATA INFILE '/path/to/agriscouting_data/weed_crops.csv'
INTO TABLE `weed_crops`
FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n'
IGNORE 1 LINES
(weed_id, crops);