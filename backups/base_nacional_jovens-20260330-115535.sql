-- MariaDB dump 10.19  Distrib 10.4.32-MariaDB, for Win64 (AMD64)
--
-- Host: 127.0.0.1    Database: base_nacional_jovens
-- ------------------------------------------------------
-- Server version	10.4.32-MariaDB

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Current Database: `base_nacional_jovens`
--

CREATE DATABASE /*!32312 IF NOT EXISTS*/ `base_nacional_jovens` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci */;

USE `base_nacional_jovens`;

--
-- Table structure for table `accounts_passwordresetcode`
--

DROP TABLE IF EXISTS `accounts_passwordresetcode`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `accounts_passwordresetcode` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `code` varchar(6) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `used` tinyint(1) NOT NULL,
  `user_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `accounts_passwordresetcode_user_id_5331448e_fk_accounts_user_id` (`user_id`),
  CONSTRAINT `accounts_passwordresetcode_user_id_5331448e_fk_accounts_user_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `accounts_passwordresetcode`
--

LOCK TABLES `accounts_passwordresetcode` WRITE;
/*!40000 ALTER TABLE `accounts_passwordresetcode` DISABLE KEYS */;
INSERT INTO `accounts_passwordresetcode` VALUES (1,'308221','2026-03-17 16:46:52.902000',0,2),(2,'650117','2026-03-17 16:55:55.511000',0,2);
/*!40000 ALTER TABLE `accounts_passwordresetcode` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `accounts_phonechange`
--

DROP TABLE IF EXISTS `accounts_phonechange`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `accounts_phonechange` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `new_phone` varchar(20) NOT NULL,
  `code` varchar(6) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `used` tinyint(1) NOT NULL,
  `user_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `accounts_phonechange_user_id_f19277c0_fk_accounts_user_id` (`user_id`),
  CONSTRAINT `accounts_phonechange_user_id_f19277c0_fk_accounts_user_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `accounts_phonechange`
--

LOCK TABLES `accounts_phonechange` WRITE;
/*!40000 ALTER TABLE `accounts_phonechange` DISABLE KEYS */;
/*!40000 ALTER TABLE `accounts_phonechange` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `accounts_user`
--

DROP TABLE IF EXISTS `accounts_user`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `accounts_user` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `password` varchar(128) NOT NULL,
  `is_superuser` tinyint(1) NOT NULL,
  `email` varchar(254) DEFAULT NULL,
  `telefone` varchar(20) NOT NULL,
  `nome` varchar(255) NOT NULL,
  `perfil` varchar(3) NOT NULL,
  `is_staff` tinyint(1) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `is_verified` tinyint(1) NOT NULL,
  `consentimento_dados` tinyint(1) NOT NULL,
  `consentimento_contacto` tinyint(1) NOT NULL,
  `data_consentimento` datetime(6) DEFAULT NULL,
  `date_joined` datetime(6) NOT NULL,
  `last_login` datetime(6) DEFAULT NULL,
  `nome_empresa` varchar(255) NOT NULL,
  `nif` varchar(20) NOT NULL,
  `setor_empresa` varchar(100) NOT NULL,
  `associacao_parceira` varchar(255) NOT NULL,
  `distrito_id` bigint(20) DEFAULT NULL,
  `bi_numero` varchar(50) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `telefone` (`telefone`),
  UNIQUE KEY `email` (`email`),
  KEY `accounts_user_distrito_id_ae6c8ea9_fk_core_district_id` (`distrito_id`),
  CONSTRAINT `accounts_user_distrito_id_ae6c8ea9_fk_core_district_id` FOREIGN KEY (`distrito_id`) REFERENCES `core_district` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=20 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `accounts_user`
--

LOCK TABLES `accounts_user` WRITE;
/*!40000 ALTER TABLE `accounts_user` DISABLE KEYS */;
INSERT INTO `accounts_user` VALUES (1,'pbkdf2_sha256$1200000$FRasutm1CPoO4nFxlBo7CH$WoPVFravSozC0WC389Gx/K+IQsxVHaft9z9vOS53p3Q=',1,'cpfpbstp@gmail.com','+2399940219','Wander Menezes','ADM',1,1,0,0,0,'2026-03-16 13:39:08.688000','2026-03-13 10:16:29.540000','2026-03-30 11:25:20.408017','','','','',1,''),(2,'pbkdf2_sha256$1200000$DFDQf1Bifp0SgkmwEl9nI7$sq6cafVAsHUPzt0tRnpKTbrpDf0QWBzsbeKW63CI/Kg=',0,'','9940219','Englobe','EMP',0,1,0,1,1,NULL,'2026-03-13 10:49:40.426000','2026-03-29 18:22:57.219728','Englobe','2342456789','Agricultura, Turismo, Energias Renováveis, Administração Pública, Comércio','',NULL,''),(3,'pbkdf2_sha256$1200000$IFMY2FB3Q9AJ3BC32Aijom$58Jndl5cJS2XSLDWnVGfP470G11UJxqVLJfK0ajGdjA=',0,'abnilzalopes@gmail.com','9814455','Abnilza','EMP',0,1,0,1,1,NULL,'2026-03-17 13:31:31.089000','2026-03-20 21:18:31.332789','Abnilza','23424567897','Serviços, Comércio','',4,''),(4,'pbkdf2_sha256$1200000$UJhEOSAmIwEzl8QzJHC7d1$W0tNy9s2s/PZBZAzlWwl/5aa4F6nQwnMmV4QVrBsfc0=',0,'oooooo@gmail.com','0000000','Carlos dos santos','JO',0,1,0,1,1,'2026-03-29 22:40:30.193668','2026-03-17 13:42:29.798000','2026-03-29 22:42:04.235290','','','','',6,''),(7,'pbkdf2_sha256$1200000$2Ytq5OKmLQlaYTrPs6sIFe$Dc4iigdfv78y9q4lU871iJEkQAuZhDLQ1MJC78TyccM=',0,'WanderMenezes55@jwpub.org','99940219','Gelto','TEC',0,0,0,0,0,NULL,'2026-03-18 11:00:05.147000','2026-03-23 12:17:30.380171','','','','',6,''),(9,'pbkdf2_sha256$1200000$oBTKGkttWb5VvCsiMcH7kX$7mKv3LUjXwgc6A42VuFD6s+o5uW3pIF3eeU2DNRTay0=',0,'damianatete@gmail.cpm','+2399999999','Tiago','OP',0,1,0,0,0,NULL,'2026-03-19 22:09:25.489000','2026-03-23 12:27:56.986198','','','','',NULL,''),(10,'pbkdf2_sha256$1200000$suNV7uwm82awPx8vr8EWtn$tVNC4ghXK8i7LvmdeXgGx0fLopVbdbORTR09IaRbL4g=',0,'2222222@gmail.com','2222222','Tiago Nogueiras da silva','JO',0,1,0,1,1,'2026-03-20 15:01:12.913399','2026-03-20 00:37:56.577343','2026-03-20 14:45:56.026679','','','','',1,'12121'),(11,'pbkdf2_sha256$1200000$ZcNWlBTaXHcRy8zvoTEuT7$1n8ZgjeZ8U2cBuSurdkHfMip04wZMuuHYYMHD7BvONM=',0,'tutorial.jovem@local.test','+2397001001','Maria Tutorial','JO',0,1,1,1,1,'2026-03-20 19:54:10.108345','2026-03-20 19:49:09.878938','2026-03-20 19:54:30.444303','','','','',1,'TUT-0001'),(12,'pbkdf2_sha256$1200000$KJEky5LsfZsXUtouKK5uNW$YKL2LiqB8LXr6zFl7phZxqQo3Ld4VVXrs1RDCBdA40c=',0,'tutorial.empresa@local.test','+2397001002','Studio Tutorial','EMP',0,1,1,0,0,NULL,'2026-03-20 19:49:11.050204','2026-03-20 21:27:22.585710','Studio Tutorial','TUT-EMP-01','','',1,''),(13,'pbkdf2_sha256$1200000$EfOp43HcbQnYAA9KHQUJvK$dPmenBE3rzZdR6Nvitf/65+0U69UjFHqTfchW0CKT3s=',0,'artur@gmail.com','9071407','Artur Fernandes Raposo Mendes','JO',0,1,0,1,1,'2026-03-23 12:39:33.180726','2026-03-23 12:34:24.865002','2026-03-23 12:35:05.614855','','','','',6,'111111'),(14,'pbkdf2_sha256$1200000$gicmqpwu6gfgnONcUQWDyy$r/lTxiPvo+jpMo+ZXYCHI7cUIH2mRTX9/QWgWrGsJWg=',0,'gilenemenezes38@gmail.com','9949839','Gilene Menezes','JO',0,1,0,1,1,'2026-03-24 12:49:41.835454','2026-03-24 12:40:34.927158','2026-03-24 15:15:26.354233','','','','',6,'172673'),(15,'pbkdf2_sha256$1200000$F123ncP5Bi3tl1iySDH7XL$kfPvaU9zTDxPkF/d2LBbpteWGNg5mNiGdap5IpKHI2w=',0,'abdu@gmail.com','9898990','Abdu Sousa','JO',0,1,0,1,1,'2026-03-25 10:27:41.034929','2026-03-25 10:20:42.620618','2026-03-29 21:15:15.162083','','','','',1,'1111111'),(16,'pbkdf2_sha256$1200000$7KAQaqjeNkYf1ur4gN65y8$rR9YO5yXbnv8/Vcqi+UjD/TVgjioXsqRKargCWNhkdI=',0,'1111111@gmail.com','1111111','Tiago dos Ramos da Costa Menezes','JO',0,1,0,1,1,NULL,'2026-03-29 17:08:49.923367',NULL,'','','','',NULL,'11111'),(18,'pbkdf2_sha256$1200000$SKMTKT5yusREkdOvpSg4Y6$AG2xlJumSqX44c9IHsAQJKiZZkNxJGffccOj4I1k5+k=',0,'tiago@gmail.com','1111111111','Tiago dos Ramos da Costa Menezes','JO',0,1,0,0,0,'2026-03-29 17:22:38.898439','2026-03-29 17:11:33.298968','2026-03-29 19:27:55.862022','','','','',6,'10291'),(19,'pbkdf2_sha256$1200000$CjY1QtkTqlaVGu90e9S4lK$9oGaNx8jyGO7QJXBN3B6dn2Bh/xylJcgta/8OFbUoRs=',0,'123456789@gmail.com','123456789','Nicolas da Costa Menezes','JO',0,1,0,0,0,NULL,'2026-03-29 19:38:15.838217','2026-03-29 21:16:13.324313','','','','',1,'121212');
/*!40000 ALTER TABLE `accounts_user` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `accounts_user_groups`
--

DROP TABLE IF EXISTS `accounts_user_groups`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `accounts_user_groups` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `user_id` bigint(20) NOT NULL,
  `group_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `accounts_user_groups_user_id_group_id_59c0b32f_uniq` (`user_id`,`group_id`),
  KEY `accounts_user_groups_group_id_bd11a704_fk_auth_group_id` (`group_id`),
  CONSTRAINT `accounts_user_groups_group_id_bd11a704_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`),
  CONSTRAINT `accounts_user_groups_user_id_52b62117_fk_accounts_user_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `accounts_user_groups`
--

LOCK TABLES `accounts_user_groups` WRITE;
/*!40000 ALTER TABLE `accounts_user_groups` DISABLE KEYS */;
/*!40000 ALTER TABLE `accounts_user_groups` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `accounts_user_user_permissions`
--

DROP TABLE IF EXISTS `accounts_user_user_permissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `accounts_user_user_permissions` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `user_id` bigint(20) NOT NULL,
  `permission_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `accounts_user_user_permi_user_id_permission_id_2ab516c2_uniq` (`user_id`,`permission_id`),
  KEY `accounts_user_user_p_permission_id_113bb443_fk_auth_perm` (`permission_id`),
  CONSTRAINT `accounts_user_user_p_permission_id_113bb443_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `accounts_user_user_p_user_id_e4f0a161_fk_accounts_` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `accounts_user_user_permissions`
--

LOCK TABLES `accounts_user_user_permissions` WRITE;
/*!40000 ALTER TABLE `accounts_user_user_permissions` DISABLE KEYS */;
/*!40000 ALTER TABLE `accounts_user_user_permissions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_group`
--

DROP TABLE IF EXISTS `auth_group`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `auth_group` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(150) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_group`
--

LOCK TABLES `auth_group` WRITE;
/*!40000 ALTER TABLE `auth_group` DISABLE KEYS */;
/*!40000 ALTER TABLE `auth_group` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_group_permissions`
--

DROP TABLE IF EXISTS `auth_group_permissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `auth_group_permissions` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `group_id` int(11) NOT NULL,
  `permission_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_group_permissions_group_id_permission_id_0cd325b0_uniq` (`group_id`,`permission_id`),
  KEY `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` (`permission_id`),
  CONSTRAINT `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `auth_group_permissions_group_id_b120cbf9_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_group_permissions`
--

LOCK TABLES `auth_group_permissions` WRITE;
/*!40000 ALTER TABLE `auth_group_permissions` DISABLE KEYS */;
/*!40000 ALTER TABLE `auth_group_permissions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_permission`
--

DROP TABLE IF EXISTS `auth_permission`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `auth_permission` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `content_type_id` int(11) NOT NULL,
  `codename` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_permission_content_type_id_codename_01ab375a_uniq` (`content_type_id`,`codename`),
  CONSTRAINT `auth_permission_content_type_id_2f476e4b_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=93 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_permission`
--

LOCK TABLES `auth_permission` WRITE;
/*!40000 ALTER TABLE `auth_permission` DISABLE KEYS */;
INSERT INTO `auth_permission` VALUES (1,'Can add log entry',1,'add_logentry'),(2,'Can change log entry',1,'change_logentry'),(3,'Can delete log entry',1,'delete_logentry'),(4,'Can view log entry',1,'view_logentry'),(5,'Can add permission',3,'add_permission'),(6,'Can change permission',3,'change_permission'),(7,'Can delete permission',3,'delete_permission'),(8,'Can view permission',3,'view_permission'),(9,'Can add group',2,'add_group'),(10,'Can change group',2,'change_group'),(11,'Can delete group',2,'delete_group'),(12,'Can view group',2,'view_group'),(13,'Can add content type',4,'add_contenttype'),(14,'Can change content type',4,'change_contenttype'),(15,'Can delete content type',4,'delete_contenttype'),(16,'Can view content type',4,'view_contenttype'),(17,'Can add session',5,'add_session'),(18,'Can change session',5,'change_session'),(19,'Can delete session',5,'delete_session'),(20,'Can view session',5,'view_session'),(21,'Can add utilizador',8,'add_user'),(22,'Can change utilizador',8,'change_user'),(23,'Can delete utilizador',8,'delete_user'),(24,'Can view utilizador',8,'view_user'),(25,'Can add código de recuperação',6,'add_passwordresetcode'),(26,'Can change código de recuperação',6,'change_passwordresetcode'),(27,'Can delete código de recuperação',6,'delete_passwordresetcode'),(28,'Can view código de recuperação',6,'view_passwordresetcode'),(29,'Can add alteração de telemóvel',7,'add_phonechange'),(30,'Can change alteração de telemóvel',7,'change_phonechange'),(31,'Can delete alteração de telemóvel',7,'delete_phonechange'),(32,'Can view alteração de telemóvel',7,'view_phonechange'),(33,'Can add perfil de jovem',12,'add_youthprofile'),(34,'Can change perfil de jovem',12,'change_youthprofile'),(35,'Can delete perfil de jovem',12,'delete_youthprofile'),(36,'Can view perfil de jovem',12,'view_youthprofile'),(37,'Can add experiência',11,'add_experience'),(38,'Can change experiência',11,'change_experience'),(39,'Can delete experiência',11,'delete_experience'),(40,'Can view experiência',11,'view_experience'),(41,'Can add formação',10,'add_education'),(42,'Can change formação',10,'change_education'),(43,'Can delete formação',10,'delete_education'),(44,'Can view formação',10,'view_education'),(45,'Can add documento',9,'add_document'),(46,'Can change documento',9,'change_document'),(47,'Can delete documento',9,'delete_document'),(48,'Can view documento',9,'view_document'),(49,'Can add skill do jovem',13,'add_youthskill'),(50,'Can change skill do jovem',13,'change_youthskill'),(51,'Can delete skill do jovem',13,'delete_youthskill'),(52,'Can view skill do jovem',13,'view_youthskill'),(53,'Can add empresa',16,'add_company'),(54,'Can change empresa',16,'change_company'),(55,'Can delete empresa',16,'delete_company'),(56,'Can view empresa',16,'view_company'),(57,'Can add pedido de contacto',17,'add_contactrequest'),(58,'Can change pedido de contacto',17,'change_contactrequest'),(59,'Can delete pedido de contacto',17,'delete_contactrequest'),(60,'Can view pedido de contacto',17,'view_contactrequest'),(61,'Can add vaga',18,'add_jobpost'),(62,'Can change vaga',18,'change_jobpost'),(63,'Can delete vaga',18,'delete_jobpost'),(64,'Can view vaga',18,'view_jobpost'),(65,'Can add candidatura',14,'add_application'),(66,'Can change candidatura',14,'change_application'),(67,'Can delete candidatura',14,'delete_application'),(68,'Can view candidatura',14,'view_application'),(69,'Can add mensagem de candidatura',15,'add_applicationmessage'),(70,'Can change mensagem de candidatura',15,'change_applicationmessage'),(71,'Can delete mensagem de candidatura',15,'delete_applicationmessage'),(72,'Can view mensagem de candidatura',15,'view_applicationmessage'),(73,'Can add distrito',20,'add_district'),(74,'Can change distrito',20,'change_district'),(75,'Can delete distrito',20,'delete_district'),(76,'Can view distrito',20,'view_district'),(77,'Can add configuração',22,'add_siteconfig'),(78,'Can change configuração',22,'change_siteconfig'),(79,'Can delete configuração',22,'delete_siteconfig'),(80,'Can view configuração',22,'view_siteconfig'),(81,'Can add skill',23,'add_skill'),(82,'Can change skill',23,'change_skill'),(83,'Can delete skill',23,'delete_skill'),(84,'Can view skill',23,'view_skill'),(85,'Can add log de auditoria',19,'add_auditlog'),(86,'Can change log de auditoria',19,'change_auditlog'),(87,'Can delete log de auditoria',19,'delete_auditlog'),(88,'Can view log de auditoria',19,'view_auditlog'),(89,'Can add notificação',21,'add_notification'),(90,'Can change notificação',21,'change_notification'),(91,'Can delete notificação',21,'delete_notification'),(92,'Can view notificação',21,'view_notification');
/*!40000 ALTER TABLE `auth_permission` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `companies_application`
--

DROP TABLE IF EXISTS `companies_application`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `companies_application` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `estado` varchar(15) NOT NULL,
  `mensagem` longtext NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `youth_id` bigint(20) NOT NULL,
  `job_id` bigint(20) NOT NULL,
  `resposta_empresa` longtext NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `companies_application_job_id_youth_id_7e4cb1dd_uniq` (`job_id`,`youth_id`),
  KEY `companies_applicatio_youth_id_a9411b0e_fk_profiles_` (`youth_id`),
  CONSTRAINT `companies_applicatio_youth_id_a9411b0e_fk_profiles_` FOREIGN KEY (`youth_id`) REFERENCES `profiles_youthprofile` (`id`),
  CONSTRAINT `companies_application_job_id_ec326096_fk_companies_jobpost_id` FOREIGN KEY (`job_id`) REFERENCES `companies_jobpost` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `companies_application`
--

LOCK TABLES `companies_application` WRITE;
/*!40000 ALTER TABLE `companies_application` DISABLE KEYS */;
INSERT INTO `companies_application` VALUES (1,'EM_ANALISE','','2026-03-17 18:29:21.214000','2026-03-17 19:49:20.490000',2,3,'entrevista dia 12 de 12 de 2025'),(2,'ACEITE','','2026-03-17 18:40:53.871000','2026-03-28 14:08:43.363916',2,1,''),(3,'ACEITE','','2026-03-17 22:22:18.969000','2026-03-28 13:47:54.572955',2,4,''),(4,'EM_ANALISE','Tenho interesse na vaga e disponibilidade imediata.','2026-03-20 19:49:12.142645','2026-03-20 19:54:12.528956',4,6,''),(5,'ACEITE','','2026-03-24 15:17:39.801653','2026-03-28 14:02:55.287526',6,1,''),(6,'PENDENTE','','2026-03-25 10:31:59.379940','2026-03-25 10:31:59.379940',7,6,''),(7,'PENDENTE','','2026-03-26 23:03:31.713473','2026-03-26 23:03:31.713473',2,6,''),(8,'PENDENTE','','2026-03-26 23:03:55.144883','2026-03-26 23:03:55.145861',2,5,'');
/*!40000 ALTER TABLE `companies_application` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `companies_applicationmessage`
--

DROP TABLE IF EXISTS `companies_applicationmessage`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `companies_applicationmessage` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `sender` varchar(3) NOT NULL,
  `message` longtext NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `application_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `companies_applicatio_application_id_90908601_fk_companies` (`application_id`),
  CONSTRAINT `companies_applicatio_application_id_90908601_fk_companies` FOREIGN KEY (`application_id`) REFERENCES `companies_application` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `companies_applicationmessage`
--

LOCK TABLES `companies_applicationmessage` WRITE;
/*!40000 ALTER TABLE `companies_applicationmessage` DISABLE KEYS */;
INSERT INTO `companies_applicationmessage` VALUES (1,'EMP','entrevista dia 12 de 12 de 2025','2026-03-17 19:48:05.949000',1),(2,'EMP','entrevista dia 12 de 12 de 2025','2026-03-17 19:49:20.475000',1);
/*!40000 ALTER TABLE `companies_applicationmessage` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `companies_company`
--

DROP TABLE IF EXISTS `companies_company`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `companies_company` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `nome` varchar(255) NOT NULL,
  `nif` varchar(20) NOT NULL,
  `setor` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`setor`)),
  `descricao` longtext NOT NULL,
  `telefone` varchar(20) NOT NULL,
  `email` varchar(254) NOT NULL,
  `website` varchar(200) NOT NULL,
  `endereco` longtext NOT NULL,
  `ativa` tinyint(1) NOT NULL,
  `verificada` tinyint(1) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `distrito_id` bigint(20) DEFAULT NULL,
  `user_id` bigint(20) NOT NULL,
  `logo` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_id` (`user_id`),
  KEY `companies_company_distrito_id_d3db2fe4_fk_core_district_id` (`distrito_id`),
  CONSTRAINT `companies_company_distrito_id_d3db2fe4_fk_core_district_id` FOREIGN KEY (`distrito_id`) REFERENCES `core_district` (`id`),
  CONSTRAINT `companies_company_user_id_175c2d31_fk_accounts_user_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `companies_company`
--

LOCK TABLES `companies_company` WRITE;
/*!40000 ALTER TABLE `companies_company` DISABLE KEYS */;
INSERT INTO `companies_company` VALUES (1,'Englobe','2342456789','[\"AGR\", \"TUR\", \"ENE\", \"ADM\", \"COM\"]','fazemos de tudo','9940219','wamdermenezes36@gmail.com','','efqef',1,0,'2026-03-13 10:50:51.597000','2026-03-18 23:30:48.143000',5,2,'company_logos/cpfp-bstp_cHG3cyg.jpg'),(2,'Abnilza','23424567897','[\"SER\", \"COM\"]','','9814455','abnilzalopes@gmail.com','','Folha-Fede Trindade',1,0,'2026-03-17 13:31:32.926000','2026-03-19 22:25:44.794000',4,3,'company_logos/logo.jpg'),(3,'Studio Tutorial','TUT-EMP-01','[\"TIC\", \"SER\"]','Empresa demo para o tutorial da plataforma.','+239 700 1002','tutorial.empresa@local.test','https://studio-tutorial.local','Avenida Marginal, Sao Tome',1,1,'2026-03-20 19:49:12.126540','2026-03-20 19:54:12.520920',1,12,'');
/*!40000 ALTER TABLE `companies_company` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `companies_contactrequest`
--

DROP TABLE IF EXISTS `companies_contactrequest`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `companies_contactrequest` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `motivo` longtext NOT NULL,
  `estado` varchar(10) NOT NULL,
  `resposta_admin` longtext NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `responded_at` datetime(6) DEFAULT NULL,
  `company_id` bigint(20) NOT NULL,
  `youth_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `companies_contactreq_company_id_3543a945_fk_companies` (`company_id`),
  KEY `companies_contactreq_youth_id_036ff097_fk_profiles_` (`youth_id`),
  CONSTRAINT `companies_contactreq_company_id_3543a945_fk_companies` FOREIGN KEY (`company_id`) REFERENCES `companies_company` (`id`),
  CONSTRAINT `companies_contactreq_youth_id_036ff097_fk_profiles_` FOREIGN KEY (`youth_id`) REFERENCES `profiles_youthprofile` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `companies_contactrequest`
--

LOCK TABLES `companies_contactrequest` WRITE;
/*!40000 ALTER TABLE `companies_contactrequest` DISABLE KEYS */;
INSERT INTO `companies_contactrequest` VALUES (1,'jn','APROVADO','','2026-03-13 11:27:59.191000','2026-03-16 14:44:09.691000',1,1),(2,'quero falar consigo pesualmente','DESATIVADO','O acesso direto ao contacto foi desativado automaticamente porque o perfil ficou abaixo da idade minima de 18 anos.','2026-03-18 23:10:28.589000','2026-03-26 23:31:08.020121',1,2),(3,'Perfil alinhado com as vagas administrativas e digitais.','APROVADO','','2026-03-20 19:49:12.153085','2026-03-20 21:55:55.518104',3,4),(4,'gostei do  jovem','APROVADO','','2026-03-25 10:39:04.856417','2026-03-25 10:39:29.007470',1,7);
/*!40000 ALTER TABLE `companies_contactrequest` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `companies_jobpost`
--

DROP TABLE IF EXISTS `companies_jobpost`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `companies_jobpost` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `titulo` varchar(255) NOT NULL,
  `descricao` longtext NOT NULL,
  `requisitos` longtext NOT NULL,
  `tipo` varchar(3) NOT NULL,
  `local_trabalho` varchar(255) NOT NULL,
  `nivel_educacao` varchar(3) NOT NULL,
  `area_formacao` varchar(3) NOT NULL,
  `experiencia_minima` int(11) NOT NULL,
  `salario` varchar(255) NOT NULL,
  `beneficios` longtext NOT NULL,
  `estado` varchar(10) NOT NULL,
  `data_publicacao` datetime(6) NOT NULL,
  `data_fecho` date DEFAULT NULL,
  `visualizacoes` int(10) unsigned NOT NULL CHECK (`visualizacoes` >= 0),
  `company_id` bigint(20) NOT NULL,
  `distrito_id` bigint(20) DEFAULT NULL,
  `numero_vagas` int(10) unsigned NOT NULL CHECK (`numero_vagas` >= 0),
  PRIMARY KEY (`id`),
  KEY `companies_jobpost_company_id_5c66c205_fk_companies_company_id` (`company_id`),
  KEY `companies_jobpost_distrito_id_45b22380_fk_core_district_id` (`distrito_id`),
  CONSTRAINT `companies_jobpost_company_id_5c66c205_fk_companies_company_id` FOREIGN KEY (`company_id`) REFERENCES `companies_company` (`id`),
  CONSTRAINT `companies_jobpost_distrito_id_45b22380_fk_core_district_id` FOREIGN KEY (`distrito_id`) REFERENCES `core_district` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `companies_jobpost`
--

LOCK TABLES `companies_jobpost` WRITE;
/*!40000 ALTER TABLE `companies_jobpost` DISABLE KEYS */;
INSERT INTO `companies_jobpost` VALUES (1,'Técnico informático','Cuidar da rede da empresa','Ser Licenciado','EMP','São tomé','SUP','TIC',1,'15000','','ATIVA','2026-03-17 10:07:02.310000','2026-04-10',0,1,1,4),(2,'Técnico informático','Cuidar da rede da empresa','Ser Licenciado','EMP','São tomé','SUP','TIC',1,'15000','','FECHADA','2026-03-17 10:07:08.825000','2026-04-10',0,1,1,1),(3,'Técnico informático','Cuidar da rede da empresa','Ser Licenciado','EMP','São tomé','SUP','TIC',1,'15000','','FECHADA','2026-03-17 10:08:40.487000','2026-04-10',0,1,1,1),(4,'Carpinteiro','cortar','10 anos','EST','São tomé','','',0,'15000','','FECHADA','2026-03-17 10:14:28.536000','2026-04-10',0,1,2,1),(5,'Assistente administrativo junior','Apoio ao atendimento, organizacao de documentos e comunicacao com candidatos.','Boa comunicacao, nocao de ferramentas digitais e disponibilidade imediata.','EMP','Sao Tome','SEC','ADM',0,'A combinar','Formacao inicial e acompanhamento.','ATIVA','2026-03-20 19:49:12.136481','2026-04-07',0,3,1,2),(6,'Operador de apoio digital','Acompanhamento de pedidos, verificacao de documentos e suporte a usuarios.','Conforto com computador, boa escrita e vontade de aprender.','EMP','Sao Tome','TEC','TIC',0,'Bolsa mensal','Mentoria e horario flexivel.','ATIVA','2026-03-20 19:49:12.142645','2026-03-30',0,3,1,1);
/*!40000 ALTER TABLE `companies_jobpost` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `core_auditlog`
--

DROP TABLE IF EXISTS `core_auditlog`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `core_auditlog` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `acao` varchar(255) NOT NULL,
  `payload` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`payload`)),
  `ip_address` char(39) DEFAULT NULL,
  `created_at` datetime(6) NOT NULL,
  `user_id` bigint(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `core_auditlog_user_id_3797aaab_fk_accounts_user_id` (`user_id`),
  CONSTRAINT `core_auditlog_user_id_3797aaab_fk_accounts_user_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `core_auditlog`
--

LOCK TABLES `core_auditlog` WRITE;
/*!40000 ALTER TABLE `core_auditlog` DISABLE KEYS */;
INSERT INTO `core_auditlog` VALUES (1,'POST /admin/login/','{}','127.0.0.1','2026-03-17 12:44:23.204000',1),(2,'Candidatura offline exportada','{\"job_id\": 1, \"job_title\": \"T\\u00e9cnico inform\\u00e1tico\", \"company_name\": \"Englobe\", \"youth_id\": 1, \"youth_name\": \"Wander Menezes\"}','127.0.0.1','2026-03-20 00:14:41.595595',1),(3,'Registo offline exportado','{\"profile_type\": \"JO\", \"profile_label\": \"jovem\"}','127.0.0.1','2026-03-20 00:26:01.154840',1),(4,'Registo offline exportado','{\"profile_type\": \"JO\", \"profile_label\": \"jovem\"}','127.0.0.1','2026-03-20 00:34:03.325179',1),(5,'Registo offline importado','{\"file_name\": \"importacao_registo_offline_jovem.json\", \"profile_type\": \"JO\", \"user_id\": 10, \"user_name\": \"Tiago Nogueiras da silva\", \"telefone\": \"2222222\", \"district_code\": \"AGU\", \"collected_offline_at\": \"2026-03-20T00:36\", \"collected_by_name\": \"Wander Menezes\", \"collected_by_role\": \"\", \"observacoes\": \"\"}','127.0.0.1','2026-03-20 00:37:58.495256',1),(6,'Registo offline exportado','{\"profile_type\": \"JO\", \"profile_label\": \"jovem\"}','127.0.0.1','2026-03-20 11:00:09.000238',1),(7,'Registo offline exportado','{\"profile_type\": \"JO\", \"profile_label\": \"jovem\"}','127.0.0.1','2026-03-23 13:22:45.996387',1),(8,'Registo offline exportado','{\"profile_type\": \"EMP\", \"profile_label\": \"empresa\"}','127.0.0.1','2026-03-23 13:24:01.252566',1),(9,'Registo offline exportado','{\"profile_type\": \"JO\", \"profile_label\": \"jovem\"}','127.0.0.1','2026-03-25 10:40:43.758450',1),(10,'Registo offline exportado','{\"profile_type\": \"JO\", \"profile_label\": \"jovem\"}','127.0.0.1','2026-03-26 23:54:56.433767',1);
/*!40000 ALTER TABLE `core_auditlog` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `core_district`
--

DROP TABLE IF EXISTS `core_district`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `core_district` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `codigo` varchar(3) NOT NULL,
  `nome` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `codigo` (`codigo`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `core_district`
--

LOCK TABLES `core_district` WRITE;
/*!40000 ALTER TABLE `core_district` DISABLE KEYS */;
INSERT INTO `core_district` VALUES (1,'AGU','Água Grande'),(2,'CAN','Cantagalo'),(3,'CAU','Caué'),(4,'LEM','Lembá'),(5,'LOB','Lobata'),(6,'MEZ','Mé-Zóchi'),(7,'PAG','Pagué');
/*!40000 ALTER TABLE `core_district` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `core_notification`
--

DROP TABLE IF EXISTS `core_notification`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `core_notification` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `titulo` varchar(255) NOT NULL,
  `mensagem` longtext NOT NULL,
  `tipo` varchar(10) NOT NULL,
  `lida` tinyint(1) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `user_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `core_notification_user_id_6e341aac_fk_accounts_user_id` (`user_id`),
  CONSTRAINT `core_notification_user_id_6e341aac_fk_accounts_user_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=81 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `core_notification`
--

LOCK TABLES `core_notification` WRITE;
/*!40000 ALTER TABLE `core_notification` DISABLE KEYS */;
INSERT INTO `core_notification` VALUES (1,'Bem-vindo à Base Nacional de Jovens!','O seu registo foi realizado com sucesso. Complete o seu perfil para começar a receber oportunidades.','SUCESSO',1,'2026-03-13 10:16:31.320000',1),(2,'Perfil criado com sucesso!','O teu perfil está completo e visível para empresas. Boa sorte nas oportunidades!','SUCESSO',1,'2026-03-13 10:21:31.362000',1),(3,'Bem-vindo à Base Nacional de Jovens!','O seu registo foi realizado com sucesso. Complete o seu perfil para começar a receber oportunidades.','SUCESSO',1,'2026-03-13 10:49:41.536000',2),(4,'Perfil da empresa criado!','O perfil da empresa foi criado com sucesso. Já pode publicar vagas e pesquisar jovens.','SUCESSO',1,'2026-03-13 10:50:51.608000',2),(5,'Novo pedido de contacto','A empresa \"Englobe\" solicitou contacto consigo.','INFO',1,'2026-03-13 11:27:59.213000',1),(6,'Perfil validado!','O teu perfil foi validado e está agora visível para empresas.','SUCESSO',1,'2026-03-16 14:43:11.123000',1),(7,'Pedido de contacto aprovado','O teu pedido de contacto para Wander Menezes foi aprovado. Podes agora contactar o jovem através do telefone: +2399940219','SUCESSO',1,'2026-03-16 14:44:09.739000',2),(8,'Novo contacto autorizado','A empresa \"Englobe\" foi autorizada a contactar-te.','INFO',1,'2026-03-16 14:44:09.763000',1),(11,'Nova candidatura','Carlos dos santos candidatou-se à vaga \"Técnico informático\".','INFO',1,'2026-03-17 18:29:21.233000',2),(12,'Nova candidatura','Carlos dos santos candidatou-se à vaga \"Técnico informático\".','INFO',1,'2026-03-17 18:40:53.882000',2),(13,'Perfil validado!','O teu perfil foi validado e está agora visível para empresas.','SUCESSO',1,'2026-03-17 19:34:24.384000',4),(14,'Atualização de candidatura','A tua candidatura para \"Técnico informático\" foi atualizada para: Aceite. Mensagem da empresa: entrevista dia 12 de 12 de 2025','INFO',1,'2026-03-17 19:48:05.995000',4),(15,'Atualização de candidatura','A tua candidatura para \"Técnico informático\" foi atualizada para: Rejeitada.','INFO',1,'2026-03-17 19:48:59.770000',4),(16,'Atualização de candidatura','A tua candidatura para \"Técnico informático\" foi atualizada para: Em Análise. Mensagem da empresa: entrevista dia 12 de 12 de 2025','INFO',1,'2026-03-17 19:49:20.519000',4),(17,'Atualização de candidatura','A tua candidatura para \"Técnico informático\" foi atualizada para: Pendente.','INFO',1,'2026-03-17 19:49:57.011000',4),(18,'Perfil atualizado com sucesso!','O teu perfil foi atualizado e está pronto para novas oportunidades.','SUCESSO',1,'2026-03-17 20:25:00.370000',4),(19,'Perfil atualizado com sucesso!','O teu perfil foi atualizado e está pronto para novas oportunidades.','SUCESSO',1,'2026-03-17 20:54:01.081000',4),(20,'Nova candidatura','Carlos dos santos candidatou-se à vaga \"Carpinteiro\".','INFO',1,'2026-03-17 22:22:18.979000',2),(21,'Atualização de candidatura','A tua candidatura para \"Carpinteiro\" foi atualizada para: Aceite.','INFO',1,'2026-03-18 21:43:48.419000',4),(22,'Novo pedido de contacto','A empresa \"Englobe\" solicitou contacto contigo.','INFO',1,'2026-03-18 23:10:28.601000',4),(23,'Novo pedido de contacto','A empresa \"Englobe\" solicitou contacto com Carlos dos santos.','INFO',1,'2026-03-18 23:10:28.611000',1),(24,'Pedido de contacto aprovado','O teu pedido de contacto para Carlos dos santos foi aprovado. Podes agora contactar o jovem através do telefone: 0000000','SUCESSO',1,'2026-03-18 23:11:46.222000',2),(25,'Novo contacto autorizado','A empresa \"Englobe\" foi autorizada a contactar-te.','INFO',1,'2026-03-18 23:11:46.229000',4),(26,'Registo offline recebido','O teu registo offline foi importado com sucesso na plataforma.','SUCESSO',1,'2026-03-20 00:37:58.493209',10),(27,'Perfil atualizado com sucesso!','O teu perfil foi atualizado e está pronto para novas oportunidades.','SUCESSO',0,'2026-03-20 14:38:54.400330',10),(28,'Perfil atualizado com sucesso!','O teu perfil foi atualizado e está pronto para novas oportunidades.','SUCESSO',0,'2026-03-20 15:01:12.932339',10),(29,'Perfil validado!','O teu perfil foi validado e está agora visível para empresas.','SUCESSO',0,'2026-03-20 15:03:44.388777',10),(30,'Pedido de contacto aprovado','O teu pedido de contacto para Maria Tutorial foi aprovado. Podes agora contactar o jovem através do telefone: +2397001001','SUCESSO',0,'2026-03-20 21:55:55.531839',12),(31,'Novo contacto autorizado','A empresa \"Studio Tutorial\" foi autorizada a contactar-te.','INFO',0,'2026-03-20 21:55:55.543510',11),(32,'Bem-vindo à Base Nacional de Jovens!','O seu registo foi realizado com sucesso. Complete o seu perfil para começar a receber oportunidades.','SUCESSO',1,'2026-03-23 12:34:27.940055',13),(33,'Perfil atualizado com sucesso!','O teu perfil foi atualizado e está pronto para novas oportunidades.','SUCESSO',1,'2026-03-23 12:39:33.209108',13),(34,'Perfil validado!','O teu perfil foi validado e está agora visível para empresas.','SUCESSO',0,'2026-03-23 13:11:44.498169',13),(35,'Perfil atualizado com sucesso!','O teu perfil foi atualizado e está pronto para novas oportunidades.','SUCESSO',1,'2026-03-24 12:49:41.883495',14),(36,'Nova candidatura','Gilene Menezes candidatou-se à vaga \"Técnico informático\".','INFO',1,'2026-03-24 15:17:39.826760',2),(37,'Perfil validado!','O teu perfil foi validado e está agora visível para empresas.','SUCESSO',1,'2026-03-24 15:25:15.107014',14),(38,'Bem-vindo à Base Nacional de Jovens!','O seu registo foi realizado com sucesso. Complete o seu perfil para começar a receber oportunidades.','SUCESSO',0,'2026-03-25 10:20:45.650133',15),(39,'Perfil atualizado com sucesso!','O teu perfil foi atualizado e está pronto para novas oportunidades.','SUCESSO',0,'2026-03-25 10:27:41.086883',15),(40,'Perfil validado!','O teu perfil foi validado e está agora visível para empresas.','SUCESSO',1,'2026-03-25 10:29:58.311787',15),(41,'Nova candidatura','Abdu Sousa candidatou-se à vaga \"Operador de apoio digital\".','INFO',0,'2026-03-25 10:31:59.399907',12),(42,'Novo pedido de contacto','A empresa \"Englobe\" solicitou contacto contigo.','INFO',0,'2026-03-25 10:39:04.861653',15),(43,'Novo pedido de contacto','A empresa \"Englobe\" solicitou contacto com Abdu Sousa.','INFO',1,'2026-03-25 10:39:04.881082',1),(44,'Pedido de contacto aprovado','O teu pedido de contacto para Abdu Sousa foi aprovado. Podes agora contactar o jovem através do telefone: 9898990','SUCESSO',1,'2026-03-25 10:39:29.060680',2),(45,'Novo contacto autorizado','A empresa \"Englobe\" foi autorizada a contactar-te.','INFO',0,'2026-03-25 10:39:29.068344',15),(46,'Perfil atualizado com sucesso!','O teu perfil foi atualizado e está pronto para novas oportunidades.','SUCESSO',1,'2026-03-26 22:50:32.897174',4),(47,'Nova candidatura','Carlos dos santos candidatou-se à vaga \"Operador de apoio digital\".','INFO',0,'2026-03-26 23:03:31.751259',12),(48,'Nova candidatura','Carlos dos santos candidatou-se à vaga \"Assistente administrativo junior\".','INFO',0,'2026-03-26 23:03:55.160631',12),(49,'Perfil atualizado com sucesso!','O teu perfil foi atualizado e está pronto para novas oportunidades.','SUCESSO',1,'2026-03-26 23:29:58.541870',4),(50,'Pedido de contacto desativado','O acesso ao contacto de Carlos dos santos foi desativado automaticamente porque o perfil ficou abaixo da idade minima.','ALERTA',1,'2026-03-26 23:31:08.032260',2),(51,'Validacao removida por idade','O teu perfil nao pode ser aprovado porque tens 8 anos. A idade minima para aprovacao e 18 anos. Tambem desativamos 1 acesso de empresa ao teu contacto.','ALERTA',1,'2026-03-26 23:31:08.034416',4),(52,'Validacao removida por idade','O teu perfil foi atualizado, mas a validacao anterior foi removida automaticamente. O teu perfil nao pode ser aprovado porque tens 8 anos. A idade minima para aprovacao e 18 anos. Tambem desativamos 1 acesso de empresa ao teu contacto.','ALERTA',1,'2026-03-26 23:31:08.049240',4),(53,'Atualização de candidatura','A tua candidatura para \"Carpinteiro\" foi atualizada para: Aceite.','INFO',1,'2026-03-28 13:47:36.837367',4),(54,'Atualização de candidatura','A tua candidatura para \"Carpinteiro\" foi atualizada para: Aceite.','INFO',1,'2026-03-28 13:47:54.583610',4),(55,'Atualização de candidatura','A tua candidatura para \"Técnico informático\" foi atualizada para: Aceite.','INFO',0,'2026-03-28 14:02:55.305781',14),(56,'Atualização de candidatura','A tua candidatura para \"Técnico informático\" foi atualizada para: Aceite.','INFO',1,'2026-03-28 14:08:43.385289',4),(57,'Bem-vindo à plataforma do CNJ!','O seu registo foi realizado com sucesso. Complete o seu perfil para começar a receber oportunidades.','SUCESSO',0,'2026-03-29 17:08:53.826203',16),(58,'Bem-vindo à plataforma do CNJ!','O seu registo foi realizado com sucesso. Complete o seu perfil para começar a receber oportunidades.','SUCESSO',1,'2026-03-29 17:11:36.130602',18),(59,'Perfil atualizado com sucesso!','O teu perfil foi atualizado e está pronto para novas oportunidades.','SUCESSO',1,'2026-03-29 17:18:51.748630',18),(60,'Perfil atualizado com sucesso!','O teu perfil foi atualizado e está pronto para novas oportunidades.','SUCESSO',1,'2026-03-29 17:22:20.345971',18),(61,'Validacao removida por idade','O teu perfil nao pode ser aprovado porque tens 0 anos. A idade minima para aprovacao e 18 anos.','ALERTA',1,'2026-03-29 17:22:38.932952',18),(62,'Perfil atualizado com restricao de idade','O teu perfil foi atualizado. O teu perfil nao pode ser aprovado porque tens 0 anos. A idade minima para aprovacao e 18 anos.','ALERTA',1,'2026-03-29 17:22:38.952844',18),(63,'Perfil pendente por idade minima','O teu perfil nao pode ser aprovado porque tens 0 anos. A idade minima para aprovacao e 18 anos.','ALERTA',0,'2026-03-29 18:21:40.925656',18),(64,'Perfil atualizado com sucesso!','O teu perfil foi atualizado e está pronto para novas oportunidades.','SUCESSO',1,'2026-03-29 18:37:29.207769',4),(65,'Perfil validado!','O teu perfil foi validado e está agora visível para empresas.','SUCESSO',1,'2026-03-29 18:37:47.019051',4),(66,'Validacao removida por idade','O teu perfil nao pode ser aprovado porque tens 16 anos. A idade minima para aprovacao e 18 anos.','ALERTA',1,'2026-03-29 18:38:28.930949',4),(67,'Validacao removida por idade','O teu perfil foi atualizado, mas a validacao anterior foi removida automaticamente. O teu perfil nao pode ser aprovado porque tens 16 anos. A idade minima para aprovacao e 18 anos.','ALERTA',1,'2026-03-29 18:38:28.947926',4),(68,'Perfil atualizado com restricao de idade','O teu perfil foi atualizado. O teu perfil nao pode ser aprovado porque tens 0 anos. A idade minima para aprovacao e 18 anos.','ALERTA',0,'2026-03-29 19:32:47.960299',18),(69,'Bem-vindo à plataforma do CNJ!','O seu registo foi realizado com sucesso. Complete o seu perfil para começar a receber oportunidades.','SUCESSO',0,'2026-03-29 19:38:18.364545',19),(70,'Novo utilizador registado','Novo utilizador registado na plataforma: Nicolas da Costa Menezes (Jovem).','INFO',1,'2026-03-29 19:38:18.383394',1),(71,'Validacao removida por idade','O teu perfil nao pode ser aprovado porque tens 0 anos. A idade minima para aprovacao e 18 anos.','ALERTA',0,'2026-03-29 21:11:44.442122',19),(72,'Perfil pronto para validacao','O perfil de Nicolas da Costa Menezes atingiu 51%, mas o candidato tem menos de 18 anos e nao pode ser aprovado.','INFO',0,'2026-03-29 21:11:44.457129',1),(73,'Perfil atualizado com restricao de idade','O teu perfil foi atualizado. O teu perfil nao pode ser aprovado porque tens 0 anos. A idade minima para aprovacao e 18 anos.','ALERTA',0,'2026-03-29 21:11:45.156286',19),(74,'Perfil atualizado com sucesso!','O teu perfil foi atualizado e ja entrou na fila de validacao do administrador.','SUCESSO',0,'2026-03-29 21:16:29.117047',19),(75,'Perfil validado!','O teu perfil foi validado e está agora visível para empresas.','SUCESSO',0,'2026-03-29 21:16:40.013897',19),(76,'Perfil atualizado com sucesso!','O teu perfil foi atualizado com sucesso.','SUCESSO',0,'2026-03-29 21:18:08.576740',19),(77,'Perfil atualizado com sucesso!','O teu perfil foi atualizado com sucesso. O teu perfil ja foi aprovado e tem progresso suficiente, mas a visibilidade para empresas esta desativada nas tuas preferencias.','SUCESSO',0,'2026-03-29 21:45:53.503063',19),(78,'Perfil atualizado com sucesso!','O teu perfil foi atualizado com sucesso. O teu perfil ja foi aprovado e tem progresso suficiente, mas a visibilidade para empresas esta desativada nas tuas preferencias.','SUCESSO',0,'2026-03-29 21:53:13.139131',19),(79,'Perfil atualizado com sucesso!','O teu perfil foi atualizado e ja entrou na fila de validacao do administrador. Depois da aprovacao, fica visivel automaticamente para empresas ao atingir 80%.','SUCESSO',1,'2026-03-29 22:40:30.232390',4),(80,'Perfil validado!','O teu perfil foi validado e esta agora visivel para empresas.','SUCESSO',1,'2026-03-29 22:40:59.525625',4);
/*!40000 ALTER TABLE `core_notification` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `core_siteconfig`
--

DROP TABLE IF EXISTS `core_siteconfig`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `core_siteconfig` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `chave` varchar(100) NOT NULL,
  `valor` longtext NOT NULL,
  `descricao` longtext NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `chave` (`chave`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `core_siteconfig`
--

LOCK TABLES `core_siteconfig` WRITE;
/*!40000 ALTER TABLE `core_siteconfig` DISABLE KEYS */;
/*!40000 ALTER TABLE `core_siteconfig` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `core_skill`
--

DROP TABLE IF EXISTS `core_skill`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `core_skill` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `nome` varchar(100) NOT NULL,
  `tipo` varchar(3) NOT NULL,
  `descricao` longtext NOT NULL,
  `aprovada` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=21 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `core_skill`
--

LOCK TABLES `core_skill` WRITE;
/*!40000 ALTER TABLE `core_skill` DISABLE KEYS */;
INSERT INTO `core_skill` VALUES (1,'Comunicação','TRA','',1),(2,'Trabalho em equipa','TRA','',1),(3,'Liderança','TRA','',1),(4,'Gestão de projetos','TRA','',1),(5,'Atendimento ao cliente','TRA','',1),(6,'Contabilidade','TEC','',1),(7,'Marketing','TRA','',1),(8,'Programação','TEC','',1),(9,'Desenvolvimento web','TEC','',1),(10,'Informática','TEC','',1),(11,'Design Gráfico','TEC','',1),(12,'Carpintaria','TEC','',1),(13,'Eletricidade','TEC','',1),(14,'Canalização','TEC','',1),(15,'Agricultura','TEC','',1),(16,'Turismo','TRA','',1),(17,'Idiomas','TRA','',1),(18,'UX/UI','TEC','',1),(19,'Pintura','TEC','',1),(20,'cantor','TEC','',0);
/*!40000 ALTER TABLE `core_skill` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_admin_log`
--

DROP TABLE IF EXISTS `django_admin_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `django_admin_log` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `action_time` datetime(6) NOT NULL,
  `object_id` longtext DEFAULT NULL,
  `object_repr` varchar(200) NOT NULL,
  `action_flag` smallint(5) unsigned NOT NULL CHECK (`action_flag` >= 0),
  `change_message` longtext NOT NULL,
  `content_type_id` int(11) DEFAULT NULL,
  `user_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `django_admin_log_content_type_id_c4bce8eb_fk_django_co` (`content_type_id`),
  KEY `django_admin_log_user_id_c564eba6_fk_accounts_user_id` (`user_id`),
  CONSTRAINT `django_admin_log_content_type_id_c4bce8eb_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`),
  CONSTRAINT `django_admin_log_user_id_c564eba6_fk_accounts_user_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_admin_log`
--

LOCK TABLES `django_admin_log` WRITE;
/*!40000 ALTER TABLE `django_admin_log` DISABLE KEYS */;
INSERT INTO `django_admin_log` VALUES (1,'2026-03-20 21:27:01.696023','12','Studio Tutorial (Empresa)',2,'[{\"changed\": {\"fields\": [\"password\"]}}]',8,1);
/*!40000 ALTER TABLE `django_admin_log` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_content_type`
--

DROP TABLE IF EXISTS `django_content_type`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `django_content_type` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `app_label` varchar(100) NOT NULL,
  `model` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `django_content_type_app_label_model_76bd3d3b_uniq` (`app_label`,`model`)
) ENGINE=InnoDB AUTO_INCREMENT=24 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_content_type`
--

LOCK TABLES `django_content_type` WRITE;
/*!40000 ALTER TABLE `django_content_type` DISABLE KEYS */;
INSERT INTO `django_content_type` VALUES (6,'accounts','passwordresetcode'),(7,'accounts','phonechange'),(8,'accounts','user'),(1,'admin','logentry'),(2,'auth','group'),(3,'auth','permission'),(14,'companies','application'),(15,'companies','applicationmessage'),(16,'companies','company'),(17,'companies','contactrequest'),(18,'companies','jobpost'),(4,'contenttypes','contenttype'),(19,'core','auditlog'),(20,'core','district'),(21,'core','notification'),(22,'core','siteconfig'),(23,'core','skill'),(9,'profiles','document'),(10,'profiles','education'),(11,'profiles','experience'),(12,'profiles','youthprofile'),(13,'profiles','youthskill'),(5,'sessions','session');
/*!40000 ALTER TABLE `django_content_type` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_migrations`
--

DROP TABLE IF EXISTS `django_migrations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `django_migrations` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `app` varchar(255) NOT NULL,
  `name` varchar(255) NOT NULL,
  `applied` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=41 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_migrations`
--

LOCK TABLES `django_migrations` WRITE;
/*!40000 ALTER TABLE `django_migrations` DISABLE KEYS */;
INSERT INTO `django_migrations` VALUES (1,'accounts','0001_initial','2026-03-19 23:41:28.439683'),(2,'core','0001_initial','2026-03-19 23:41:28.660380'),(3,'contenttypes','0001_initial','2026-03-19 23:41:28.693705'),(4,'contenttypes','0002_remove_content_type_name','2026-03-19 23:41:28.754587'),(5,'auth','0001_initial','2026-03-19 23:41:28.978687'),(6,'auth','0002_alter_permission_name_max_length','2026-03-19 23:41:29.032955'),(7,'auth','0003_alter_user_email_max_length','2026-03-19 23:41:29.039031'),(8,'auth','0004_alter_user_username_opts','2026-03-19 23:41:29.046970'),(9,'auth','0005_alter_user_last_login_null','2026-03-19 23:41:29.054708'),(10,'auth','0006_require_contenttypes_0002','2026-03-19 23:41:29.057166'),(11,'auth','0007_alter_validators_add_error_messages','2026-03-19 23:41:29.063798'),(12,'auth','0008_alter_user_username_max_length','2026-03-19 23:41:29.070604'),(13,'auth','0009_alter_user_last_name_max_length','2026-03-19 23:41:29.078749'),(14,'auth','0010_alter_group_name_max_length','2026-03-19 23:41:29.088932'),(15,'auth','0011_update_proxy_permissions','2026-03-19 23:41:29.097436'),(16,'auth','0012_alter_user_first_name_max_length','2026-03-19 23:41:29.101663'),(17,'accounts','0002_initial','2026-03-19 23:41:29.432098'),(18,'accounts','0003_phonechange','2026-03-19 23:41:29.491568'),(19,'accounts','0004_user_bi_numero','2026-03-19 23:41:29.518729'),(20,'admin','0001_initial','2026-03-19 23:41:29.623268'),(21,'admin','0002_logentry_remove_auto_add','2026-03-19 23:41:29.637397'),(22,'admin','0003_logentry_add_action_flag_choices','2026-03-19 23:41:29.649856'),(23,'profiles','0001_initial','2026-03-19 23:41:30.041819'),(24,'companies','0001_initial','2026-03-19 23:41:30.535643'),(25,'companies','0002_company_logo','2026-03-19 23:41:30.560040'),(26,'companies','0002_application_resposta_empresa','2026-03-19 23:41:30.579235'),(27,'companies','0003_merge_20260317_1853','2026-03-19 23:41:30.584637'),(28,'companies','0004_application_message','2026-03-19 23:41:30.657030'),(29,'companies','0005_jobpost_numero_vagas','2026-03-19 23:41:30.681624'),(30,'companies','0006_company_setor_multiple','2026-03-19 23:41:30.768932'),(31,'companies','0007_alter_contactrequest_estado','2026-03-19 23:41:30.782345'),(32,'core','0002_populate_skills','2026-03-19 23:41:30.884328'),(33,'core','0003_populate_districts','2026-03-19 23:41:30.921613'),(34,'core','0004_skill_aprovada','2026-03-19 23:41:30.957757'),(35,'profiles','0002_youthprofile_photo','2026-03-19 23:41:30.980998'),(36,'profiles','0003_youthprofile_consentimento_email_and_more','2026-03-19 23:41:31.091621'),(37,'profiles','0004_alter_youthprofile_interesse_setorial','2026-03-19 23:41:31.187221'),(38,'sessions','0001_initial','2026-03-19 23:41:31.217252'),(39,'profiles','0005_youthprofile_idiomas','2026-03-23 13:00:13.588724'),(40,'profiles','0006_education_outra_area_formacao','2026-03-28 12:43:36.051867');
/*!40000 ALTER TABLE `django_migrations` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_session`
--

DROP TABLE IF EXISTS `django_session`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `django_session` (
  `session_key` varchar(40) NOT NULL,
  `session_data` longtext NOT NULL,
  `expire_date` datetime(6) NOT NULL,
  PRIMARY KEY (`session_key`),
  KEY `django_session_expire_date_a5c62663` (`expire_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_session`
--

LOCK TABLES `django_session` WRITE;
/*!40000 ALTER TABLE `django_session` DISABLE KEYS */;
INSERT INTO `django_session` VALUES ('0oiwpxa01skzge9u2vzt4suiicwsxe0y','.eJxVjMEOwiAQBf-FsyFQoCw9evcbCCxbixowpU00xn_XJj3o9c28eTEf1mXya6PZ58QGJtnhd4sBr1Q2kC6hnCvHWpY5R74pfKeNn2qi23F3_wJTaNP3HVIH0irQgshANE4ptKpzY2dQSG0ToLGjFKgxah0Bbe96AnJOJhUAtmij1nItnh73PD_ZIN4fXtM-bQ:1w6V8j:Agy1NTNVk8KHOutyIDjKZIFdwekUqpg9YTzDBPq8sj4','2026-03-29 14:59:53.621819'),('1qplngf9ptjbbknv3i546qq61r4zyqyf','.eJxVjMEOwiAQBf-FsyFQoCw9evcbCCxbixowpU00xn_XJj3o9c28eTEf1mXya6PZ58QGJtnhd4sBr1Q2kC6hnCvHWpY5R74pfKeNn2qi23F3_wJTaNP3HVIH0irQgshANE4ptKpzY2dQSG0ToLGjFKgxah0Bbe96AnJOJhUAtmij1nItnh73PD_ZIN4fXtM-bQ:1w6zKO:_vvjkDfaeWq62SUyGrEcwMz6DMhnc_StwCuq_QgVoRA','2026-03-30 23:13:56.549786'),('3u12u6jyaa3b9aucm0kt2co2nv9q3r0l','.eJxtU9tq4zAQ_RWj13WC7DRxk6ftJYUuBMq2b2UxY2mcqLUlI8lpd0v_fWdst6RQMJY1lzNn5ozfRAl9PJR9QF8aLTYiy0R6aqxAPaNlj34Cu3dz5Wz0pppzyHzyhvnOaWwup9gvAAcIB8ousqXONK6qYqE1ZEWhVFHlco1KYp7LfFVUuFByvVpldS3rQp6tcJ1n9ep8uapkVjFowBCMsyW-dsb_FRuZihfzD7wuNUQQmzeR8cu6FqniDryB5KGPjs6G8iM2WDvLvh_5Yl1ImdFDDmzBNGSNU-z8yR2x_dk4Rd8RQ6QYbQK1HZ3YZHShcqWFoEyLlm0ilzKfyfNZtqTYgK9su6HPAcNo0Fz1jkaHyc5YIA_PEVR0JTQRvYVojm5ilqzPZTJwe09FPrRkjsgMH7ZXlAoeoaydb0EB5zzcstXYEE3szWi7ImLeJRqTmynwdBRgKYamviQevQ8DCCpr1JBxawfwSFDczbNpmiA2j1map4s_qXB99FAO5nKatfhqjaZjSKa_YPqBeDGFEujkPu62u3GmnbOmMp8Tur_dDZ3QREhrJMUnypvHqcv77W96X1zvBDHpPNYUaZWB0nXOx95-IG13d8zdVZ5vv1jQRLk2-cROyACR1nXUMNFmbyI0aUKIHtgGgYeBQbHu3rgEE-gcnaBbY3kfBtHmw2q1vJXozUBGbKLvkRbrtSsJ6IPTJTSsw0jmeqwnxigFfs8ju6AND8SK9oRqn_Cb4vRAZ5T4YiSTKKAgWkkX0oR2FPaETskdktUFYu38Hiz9KFycHMSGzBUEkjvMJ2BqSJlxk_PlTBYzuZg8tWlHhfkyCcjtkbhnLO7RhHE7x55prwP3PLAuQxu-d7wcIAbouu-90x85lHl__w9UdZCW:1w3fvV:tLPlYoQK8U8Csyd1YBpcobMMrucE0LiNGExybV26V3U','2026-03-21 19:54:33.276154'),('5rxtuns6h9arxl006xhsb72u4vs9v5cl','.eJxVjMsOwiAQRf-FtSEDfQBduvcbyDBDLWrAlDbRGP9dm3Sh23vOPS_hcV0mv9Y4-8RiEFocfreAdI15A3zBfC6SSl7mFOSmyJ1WeSocb8fd_QtMWKfvmxxTMCYoDSNGa0bC1jWKtdIWIrueCXsNrTZgkbBT3DoMFhqru4aBtmiNtaaSfXzc0_wUA7w_n_o_Kg:1w5LeV:n26kQoew4yxR4B12SRy2vDkmGjiEw8Ufgb_BkILA_M0','2026-03-26 10:39:55.855813'),('7l7mjp02uxm22vqnsq90gs8wp08slw9i','.eJxVjDsOwjAQBe_iGln-xmtKes5g2bsbHECOFCcV4u4QKQW0b2beS6S8rTVtnZc0kTgLLU6_W8n44LYDuud2myXObV2mIndFHrTL60z8vBzu30HNvX7rTAZ0sOAUs4fio7UYrImj8ai0CwTow6gVOizOFcAwxIGBY9RkM4B4fwDEvTcw:1w3hmH:mEf2moTV5zT3Co3e8zgsMV_kRg5dwZBvfcEL_427Pr0','2026-03-21 21:53:09.137364'),('7ufy5b7g9gdtgwsaemzvqb1em470gv90','.eJxVjMEOwiAQBf-FsyFQoCw9evcbCCxbixowpU00xn_XJj3o9c28eTEf1mXya6PZ58QGJtnhd4sBr1Q2kC6hnCvHWpY5R74pfKeNn2qi23F3_wJTaNP3HVIH0irQgshANE4ptKpzY2dQSG0ToLGjFKgxah0Bbe96AnJOJhUAtmij1nItnh73PD_ZIN4fXtM-bQ:1w53d5:CLJf7F8S1TmxzLQ0k12iO9yGvH_eJJKyGqQkRnVBbvw','2026-03-25 15:25:15.193984'),('8ah7v8z13avbydfyykwvqivfgpibsjuw','.eJxtUttu2zAM_ZVAz27gS5LGeRrWZUAfAgxI99QNAm3RCVdbMiQ57Vbk30c6SW-oAdviORTJQ_JZaRjiXg8BvSajVmqmkrdYBfUDWiHMH7A7N62djZ6qqbhMz2yYbpzB9uvZ912APYS9hC0Xs2pWYFPMy3yJaQZlURf1wjTGVDWUYNIarivAbFk0-fVyAYuiSK8hL0so5yVK0IAhkLMan3ryf9UqTdQj_QNvtIEIavWsMvlY1yFnvAHfujAx_Aaw0QUOEbHFxlmh09PDIHZALSNufL7sxGSZHVOGAouNTq0WbHASbSHU1KEVTGVlubzK8qu8YN-AT4Jt-Ni6GloyYCTRd9fu4apBIxqke1BHp6GN6C1EOsilcpnNZvO5OiYqHyXQAaWk7fqGL4FH0I3zHdQg3ne3grohetAfOSbIhkhxoBPwc3v3Q2JYNvI0L7iGwQdh1naHdg-eYHJrJcSvIU0xi3xR5DxQ2wa1us-TIpkly6RMsjTJst-XzKODPjdbvUcj9WMxrKcQPYHrkQI18F-EfVtvT-3tnaWKXpq1vd2MCrg5PGzkkUfHBfKV-1E2Z-89NszamkC73vk42Mvt9UakBld5sXYuRDcxOOG6KuAh-HEDOtkf9DRGUKsG2oC8BE-95qleIqkTUoPfuVfTYKg9vTRaILJU0xu7oe7VOKsdU3ArZtKKA4XTcKMfcFyIIHnHldKhC58Tj3uIAfr-c_a8wWfq8HJCH6nheo27QBWdTsfj8T-Db1Mu:1w6zIq:3usxX52eqmJ9TU7J1IZJwy4Z1PNRs21UwN1x70znPQc','2026-03-30 23:12:20.643833'),('a9arbeexb6o6b83q080nfwf3ssedyu8f','.eJxVjMsOwiAQRf-FtSEDfQBduvcbyDBDLWrAlDbRGP9dm3Sh23vOPS_hcV0mv9Y4-8RiEFocfreAdI15A3zBfC6SSl7mFOSmyJ1WeSocb8fd_QtMWKfvmxxTMCYoDSNGa0bC1jWKtdIWIrueCXsNrTZgkbBT3DoMFhqru4aBtmiNtaaSfXzc0_wUA7w_n_o_Kg:1w4fEd:gvgHRNqnT3GnRDx2jrcGghmUxZLxTjfcneGGHfmDOWM','2026-03-24 13:22:23.353979'),('baalws8b00ht3j3vhtxzenh4khg9pvro','.eJxVjDsOwjAQBe_iGln-xmtKes5g2bsbHECOFCcV4u4QKQW0b2beS6S8rTVtnZc0kTgLLU6_W8n44LYDuud2myXObV2mIndFHrTL60z8vBzu30HNvX7rTAZ0sOAUs4fio7UYrImj8ai0CwTow6gVOizOFcAwxIGBY9RkM4B4fwDEvTcw:1w3hfA:IjrQPU3zMrabTCdTj5WtR10IEMnrAkD11Mg6espVgJE','2026-03-21 21:45:48.441756'),('bfawe34174u6z0v94p15x1vjecvkozl5','.eJxVjDsOwjAQBe_iGln-xmtKes5g2bsbHECOFCcV4u4QKQW0b2beS6S8rTVtnZc0kTgLLU6_W8n44LYDuud2myXObV2mIndFHrTL60z8vBzu30HNvX7rTAZ0sOAUs4fio7UYrImj8ai0CwTow6gVOizOFcAwxIGBY9RkM4B4fwDEvTcw:1w3hfA:IjrQPU3zMrabTCdTj5WtR10IEMnrAkD11Mg6espVgJE','2026-03-21 21:45:48.404466'),('cnoly6f4ir120av5qwvlpp2lpi46j70d','.eJxVjEEKwjAQAP-Ss4S026Zdj959Q9hktzYqiTQtKOLfJdCDXmeGeStH2zq7rcjiIquj6tThl3kKN0lV8JXSJeuQ07pEr2uid1v0ObPcT3v7N5ipzHWLtvMdyAQ9tqOYhhACBMsTsw-ExCbQ4EmaEaZ2GC1ZADNQi0jYo9RpkVJiTk6ej7i81NF8vqL6P30:1w50t9:A0dSnG8e68jCgyvSnRmzN_fTyKtnCATODhqG4DousTw','2026-03-25 12:29:39.512403'),('dmiwm354rgru9y9dwv8ensp91catdgo1','.eJxVjMEOwiAQBf-FsyFQoCw9evcbCCxbixowpU00xn_XJj3o9c28eTEf1mXya6PZ58QGJtnhd4sBr1Q2kC6hnCvHWpY5R74pfKeNn2qi23F3_wJTaNP3HVIH0irQgshANE4ptKpzY2dQSG0ToLGjFKgxah0Bbe96AnJOJhUAtmij1nItnh73PD_ZIN4fXtM-bQ:1w3Nsl:gd3ihotz-v8wsHda1G-qg4mADB3W9xTLuIviykmcXEA','2026-03-21 00:38:31.032408'),('do9k5unhhsgulsxzchv421bzfms1att5','.eJxVjMEOwiAQBf-FsyFQoCw9evcbCCxbixowpU00xn_XJj3o9c28eTEf1mXya6PZ58QGJtnhd4sBr1Q2kC6hnCvHWpY5R74pfKeNn2qi23F3_wJTaNP3HVIH0irQgshANE4ptKpzY2dQSG0ToLGjFKgxah0Bbe96AnJOJhUAtmij1nItnh73PD_ZIN4fXtM-bQ:1w5uXQ:iXSAmaN0p418FOSpoZz2w8BSofksElHt8sLQhujkkuU','2026-03-27 23:54:56.456398'),('h95dtj0s8777vlpicf32mg10xcsa1idk','.eJxVjMsOwiAQRf-FtSEDfQBduvcbyDBDLWrAlDbRGP9dm3Sh23vOPS_hcV0mv9Y4-8RiEFocfreAdI15A3zBfC6SSl7mFOSmyJ1WeSocb8fd_QtMWKfvmxxTMCYoDSNGa0bC1jWKtdIWIrueCXsNrTZgkbBT3DoMFhqru4aBtmiNtaaSfXzc0_wUA7w_n_o_Kg:1w56yu:k92Dgr2p8t_eDD0plkVuYXbWsbZUt23zF3aEVH94Jro','2026-03-25 19:00:00.076197'),('hiw3o11htcsl9cupdszf1mo4so4sbacr','.eJxVjEEKwjAQAP-Ss4S026Zdj959Q9hktzYqiTQtKOLfJdCDXmeGeStH2zq7rcjiIquj6tThl3kKN0lV8JXSJeuQ07pEr2uid1v0ObPcT3v7N5ipzHWLtvMdyAQ9tqOYhhACBMsTsw-ExCbQ4EmaEaZ2GC1ZADNQi0jYo9RpkVJiTk6ej7i81NF8vqL6P30:1w5ua3:YeFVT8wqV-t8Vhjl0lcmag9dHg8aS3L0SvZxA4qBYt4','2026-03-27 23:57:39.709075'),('i3dvr3ethe5l5tbk5csdqj7actgov32l','.eJxVjDsOwjAQBe_iGln-xmtKes5g2bsbHECOFCcV4u4QKQW0b2beS6S8rTVtnZc0kTgLLU6_W8n44LYDuud2myXObV2mIndFHrTL60z8vBzu30HNvX7rTAZ0sOAUs4fio7UYrImj8ai0CwTow6gVOizOFcAwxIGBY9RkM4B4fwDEvTcw:1w3iD5:lH0VMfWmpfe4IdT2JuNjs_JddZpAu6W-TgqEf3lVNGU','2026-03-21 22:20:51.584850'),('ibz4jcft8chu9ngcn33iqo6vqfdjyo51','.eJxVjDsOwjAQBe_iGln-xmtKes5g2bsbHECOFCcV4u4QKQW0b2beS6S8rTVtnZc0kTgLLU6_W8n44LYDuud2myXObV2mIndFHrTL60z8vBzu30HNvX7rTAZ0sOAUs4fio7UYrImj8ai0CwTow6gVOizOFcAwxIGBY9RkM4B4fwDEvTcw:1w7Amq:0pXGKoq2zfoO-3Z2aOUs_OJA_HJc2Mj-3q-jdv5a8YI','2026-03-31 11:28:04.939511'),('kpxvfqfvfl3bsf9eqmpjvnet4sftqrrv','.eJxVjMsOwiAQRf-FtSEDfQBduvcbyDBDLWrAlDbRGP9dm3Sh23vOPS_hcV0mv9Y4-8RiEFocfreAdI15A3zBfC6SSl7mFOSmyJ1WeSocb8fd_QtMWKfvmxxTMCYoDSNGa0bC1jWKtdIWIrueCXsNrTZgkbBT3DoMFhqru4aBtmiNtaaSfXzc0_wUA7w_n_o_Kg:1w5uAo:FWUuyx94Cr1y5RZqy9aKa-ktMsRH42PO2LNiGug3sYw','2026-03-27 23:31:34.981251'),('l8um2uqqvl6shbds9xlb2w3e32genwsj','.eJxtUk1v2zAM_SuBzmlgO7bj5LQN64AdcmmyUzEItCQnXG3JkOQ0W5H_PtJxmxboxSYfvx4f9SIkDPEoh2C8RC02Il2K-XuwBvVkLEf0H7AHt1DORo_1glMWUzQstk6b9tuU-6HBEcKRqhudrdIadJKsqyTRZNdNsVyV60wVkBd5nqhMN0VTqxzKUqm0aPIyreqqWuoiq0puGkwI6Kw05x79X7FJ5uIZ_4HXUkMEsXkRKX_YkRaCws7Y6Gh4lqTFXZLdZQm1CebM2JbM1iloUYM2BOw92tGcC94RVHQS2mi8hYgnLllXaZ4XBSVY13HJVx8HP_vBKVabMHuA3gU32xr2KC2a1jTOcuo6WaV5siLQdIAtIcDFXw7skagdRTQGkpYZl5e5yHgXiyfDyRQFb0A2znegwF0htCFiHPANADsZavBhMsMTtm0Qm8ffc-GG6EGOiJx2EB_RiP1YRwSWTCBQfx4ogf7M5Pv97kq1dxZrfJNv93M7MiLB6EyGjhWdRy55FPtfD4Km9940FLUKQbre0f72tfp-t2eqrvYTp2g6vrPxOOaLTQNtMKTeuZd01dc6cUUU-IO7uaS-8jdVGEKLCt_5DXY3Z9ptHEGL57z4CcNV--gHMz6JwHPHJyVDFz4PPB8hBuj7z6PT6Tl0uVz-A2U-KQw:1w4f34:ulqSV_QtKjPSI1-rBOHPqGb3bqcCPNCwD48nCWLXZkA','2026-03-24 13:10:26.673993'),('n8rj6g7n4ne5oip4cph7yia30uhy66n5','.eJxVjMEOwiAQBf-FsyFQoCw9evcbCCxbixowpU00xn_XJj3o9c28eTEf1mXya6PZ58QGJtnhd4sBr1Q2kC6hnCvHWpY5R74pfKeNn2qi23F3_wJTaNP3HVIH0irQgshANE4ptKpzY2dQSG0ToLGjFKgxah0Bbe96AnJOJhUAtmij1nItnh73PD_ZIN4fXtM-bQ:1w4fGD:Mv5zKSsY1BgGS4qyLPKK_Dozn-PotcVDNRUlSaCE6UA','2026-03-24 13:24:01.257245'),('qnwjv6pq7u1pktik6z55xdag3qzw976r','.eJxVjMsOwiAQRf-FtSEDfQBduvcbyDBDLWrAlDbRGP9dm3Sh23vOPS_hcV0mv9Y4-8RiEFocfreAdI15A3zBfC6SSl7mFOSmyJ1WeSocb8fd_QtMWKfvmxxTMCYoDSNGa0bC1jWKtdIWIrueCXsNrTZgkbBT3DoMFhqru4aBtmiNtaaSfXzc0_wUA7w_n_o_Kg:1w3N6H:8sMvETdbPsRx_gS6krto6v4tO6xzxzhJhgwPj59vEMg','2026-03-20 23:48:25.769421'),('u00bn7d923h1bknl60v4okbdm4pknmpu','.eJxVjMEOwiAQBf-FsyFQoCw9evcbCCxbixowpU00xn_XJj3o9c28eTEf1mXya6PZ58QGJtnhd4sBr1Q2kC6hnCvHWpY5R74pfKeNn2qi23F3_wJTaNP3HVIH0irQgshANE4ptKpzY2dQSG0ToLGjFKgxah0Bbe96AnJOJhUAtmij1nItnh73PD_ZIN4fXtM-bQ:1w3iEm:sH-B526J8iiH4bp-moQg9Avg3NOChU13d-r4RuZW7zs','2026-03-21 22:22:36.363017'),('vi00j6sh5lqia65mt032ldm6ben4dult','.eJxVjMsOwiAQRf-FtSEDfQBduvcbyDBDLWrAlDbRGP9dm3Sh23vOPS_hcV0mv9Y4-8RiEFocfreAdI15A3zBfC6SSl7mFOSmyJ1WeSocb8fd_QtMWKfvmxxTMCYoDSNGa0bC1jWKtdIWIrueCXsNrTZgkbBT3DoMFhqru4aBtmiNtaaSfXzc0_wUA7w_n_o_Kg:1w6ULD:Toe0BXCuPjkbiS_M-z8IPAS2q5mNZhBJb1_9AjGXIwQ','2026-03-29 14:08:43.886525'),('wzcjfm1pryb6ecp6oqpn7hhpovkt97ga','.eJxVjMsOwiAQRf-FtSEDfQBduvcbyDBDLWrAlDbRGP9dm3Sh23vOPS_hcV0mv9Y4-8RiEFocfreAdI15A3zBfC6SSl7mFOSmyJ1WeSocb8fd_QtMWKfvmxxTMCYoDSNGa0bC1jWKtdIWIrueCXsNrTZgkbBT3DoMFhqru4aBtmiNtaaSfXzc0_wUA7w_n_o_Kg:1w6zJQ:qz2lWqY2YvpDJJW7DG9KdsSjp5CYGof3JM8fSrQngiQ','2026-03-30 23:12:56.594554'),('x0fi3ga1azgbcm94yn13v707pwc7nbfu','.eJxVjjsOwjAQRO_iGln-kXhT0nMGa-PdEAOyUZxIIMTdISgFtPPejOYpAi7zGJbKU0gkOqGN2P2GPcYL55XQGfOpyFjyPKVerorcaJXHQnw9bO7fwIh1_LSjtY2Kas_goAG0CK3uLQFj65VvDGNEQus1tazjYMyAFjw6D8YR-u-ryrWmkgPfb2l6iE693qvEP0k:1w3fvd:rh3AtqZdw_3PjM13fpx3TDBMkzFBgMyYj4UzY-btJ_A','2026-03-21 19:54:41.555207'),('x490p3bho9y9tcovul3lghu2w4xx0ur3','.eJxVjDsOwjAQBe_iGln-xmtKes5g2bsbHECOFCcV4u4QKQW0b2beS6S8rTVtnZc0kTgLLU6_W8n44LYDuud2myXObV2mIndFHrTL60z8vBzu30HNvX7rTAZ0sOAUs4fio7UYrImj8ai0CwTow6gVOizOFcAwxIGBY9RkM4B4fwDEvTcw:1w3i5w:2nvT1RWtMWr1YAUvJ4pGyO1Vupob1BaXXb74wCIc0cs','2026-03-21 22:13:28.560989');
/*!40000 ALTER TABLE `django_session` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `profiles_document`
--

DROP TABLE IF EXISTS `profiles_document`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `profiles_document` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `tipo` varchar(10) NOT NULL,
  `nome` varchar(255) NOT NULL,
  `arquivo` varchar(100) NOT NULL,
  `verificado` tinyint(1) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `profile_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `profiles_document_profile_id_e7ecab6b_fk_profiles_` (`profile_id`),
  CONSTRAINT `profiles_document_profile_id_e7ecab6b_fk_profiles_` FOREIGN KEY (`profile_id`) REFERENCES `profiles_youthprofile` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `profiles_document`
--

LOCK TABLES `profiles_document` WRITE;
/*!40000 ALTER TABLE `profiles_document` DISABLE KEYS */;
INSERT INTO `profiles_document` VALUES (1,'BI','BI','documents/2026/03/WhatsApp_Image_2026-03-13_at_12.03.46.jpeg',0,'2026-03-17 20:23:28.900000',2),(2,'OUTRO','cartão escolar','documents/2026/03/WhatsApp_Image_2026-03-13_at_12.03.52.jpeg',0,'2026-03-17 20:28:06.362000',2),(3,'CV','Curriculum Vitae','documents/2026/03/A_ZBDGDqY.1.1.1.3__Plano_de_curso_técnico_em_Redes_de_Computadores_CFPBSTP_1.pdf',0,'2026-03-17 20:28:32.303000',2),(7,'CERT','Certificado','documents/2026/03/1_ª_Caixa1.docx',0,'2026-03-17 21:17:23.544000',2),(8,'CERT','Metodologia de SENAI','documents/2026/03/carta_de_apresentação_de_vania.docx',0,'2026-03-17 21:18:05.329000',2),(9,'BI','bi 2','documents/2026/03/IMG_20251221_150936.jpg',0,'2026-03-17 21:23:32.854000',2);
/*!40000 ALTER TABLE `profiles_document` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `profiles_education`
--

DROP TABLE IF EXISTS `profiles_education`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `profiles_education` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `nivel` varchar(3) NOT NULL,
  `area_formacao` varchar(3) NOT NULL,
  `instituicao` varchar(255) NOT NULL,
  `ano` int(11) DEFAULT NULL,
  `curso` varchar(255) NOT NULL,
  `profile_id` bigint(20) NOT NULL,
  `outra_area_formacao` varchar(255) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `profiles_education_profile_id_fc3828ab_fk_profiles_` (`profile_id`),
  CONSTRAINT `profiles_education_profile_id_fc3828ab_fk_profiles_` FOREIGN KEY (`profile_id`) REFERENCES `profiles_youthprofile` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `profiles_education`
--

LOCK TABLES `profiles_education` WRITE;
/*!40000 ALTER TABLE `profiles_education` DISABLE KEYS */;
INSERT INTO `profiles_education` VALUES (1,'SUP','TIC','USTP',2022,'Engenharia Informática',1,''),(2,'SEC','TIC','USTP',2023,'Engenharia Informática',2,''),(3,'SEC','OUT','MMM',2022,'Linguas',3,''),(4,'TEC','TIC','Centro de Formacao Tutorial',2025,'Tecnico de Informatica',4,''),(5,'SUP','EDU','Ustp',NULL,'Licenciatura em Lingua Portuguesa',6,''),(6,'TEC','TIC','USTP',NULL,'Engenharia Informática',7,''),(7,'BAS','TUR','USTP',2023,'Administração',10,'');
/*!40000 ALTER TABLE `profiles_education` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `profiles_experience`
--

DROP TABLE IF EXISTS `profiles_experience`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `profiles_experience` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `entidade` varchar(255) NOT NULL,
  `cargo` varchar(255) NOT NULL,
  `inicio` date NOT NULL,
  `fim` date DEFAULT NULL,
  `atual` tinyint(1) NOT NULL,
  `descricao` longtext NOT NULL,
  `profile_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `profiles_experience_profile_id_1aec30fb_fk_profiles_` (`profile_id`),
  CONSTRAINT `profiles_experience_profile_id_1aec30fb_fk_profiles_` FOREIGN KEY (`profile_id`) REFERENCES `profiles_youthprofile` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `profiles_experience`
--

LOCK TABLES `profiles_experience` WRITE;
/*!40000 ALTER TABLE `profiles_experience` DISABLE KEYS */;
INSERT INTO `profiles_experience` VALUES (1,'CPFP','Professor na areas de TIC','2018-10-08',NULL,1,'',1),(2,'Balcao Jovem Digital','Assistente de atendimento','2025-07-03',NULL,1,'Apoio a candidatos, triagem de pedidos e organizacao de dados basicos.',4);
/*!40000 ALTER TABLE `profiles_experience` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `profiles_youthprofile`
--

DROP TABLE IF EXISTS `profiles_youthprofile`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `profiles_youthprofile` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `data_nascimento` date DEFAULT NULL,
  `sexo` varchar(1) NOT NULL,
  `localidade` varchar(255) NOT NULL,
  `situacao_atual` varchar(3) NOT NULL,
  `disponibilidade` varchar(10) NOT NULL,
  `interesse_setorial` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`interesse_setorial`)),
  `preferencia_oportunidade` varchar(5) NOT NULL,
  `sobre` longtext NOT NULL,
  `completo` tinyint(1) NOT NULL,
  `validado` tinyint(1) NOT NULL,
  `visivel` tinyint(1) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `wizard_step` int(11) NOT NULL,
  `wizard_data` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`wizard_data`)),
  `user_id` bigint(20) NOT NULL,
  `photo` varchar(100) DEFAULT NULL,
  `consentimento_email` tinyint(1) NOT NULL,
  `consentimento_sms` tinyint(1) NOT NULL,
  `consentimento_whatsapp` tinyint(1) NOT NULL,
  `contacto_alternativo` varchar(255) NOT NULL,
  `idiomas` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`idiomas`)),
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_id` (`user_id`),
  CONSTRAINT `profiles_youthprofile_user_id_ff8fadf2_fk_accounts_user_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `profiles_youthprofile`
--

LOCK TABLES `profiles_youthprofile` WRITE;
/*!40000 ALTER TABLE `profiles_youthprofile` DISABLE KEYS */;
INSERT INTO `profiles_youthprofile` VALUES (1,'1998-12-23','M','Folha-fede','EMP','SIM','[\"TIC\", \"ENE\", \"EDU\", \"ELE\"]','FOR','',1,1,1,'2026-03-13 10:21:31.343000','2026-03-16 14:43:11.087000',4,'{}',1,'youth_avatars/Gemini_Generated_Image_2znby72znby72znb.png',1,1,1,'','[]'),(2,'1998-12-23','M','Folha-fede','DES','SIM','[\"TIC\"]','EMP','gosto de trabalhar',1,1,1,'2026-03-17 13:42:33.219000','2026-03-29 22:40:59.502572',1,'{\"1\": {\"nome\": \"Carlos dos santos\", \"telefone\": \"0000000\", \"email\": \"oooooo@gmail.com\", \"distrito\": 6, \"data_nascimento\": \"1998-12-23\", \"sexo\": \"M\", \"localidade\": \"Folha-fede\", \"contacto_alternativo\": \"9814455\"}, \"2\": {\"nivel\": \"SEC\", \"area_formacao\": \"TIC\", \"outra_area_formacao\": \"\", \"instituicao\": \"USTP\", \"ano\": 2023, \"curso\": \"Engenharia Inform\\u00e1tica\", \"skills\": [2, 3, 4, 8, 9, 10, 11], \"outra_skill_nome\": \"\", \"outra_skill_tipo\": \"\"}, \"3\": {\"situacao_atual\": \"DES\", \"disponibilidade\": \"SIM\", \"interesse_setorial\": [\"TIC\"], \"preferencia_oportunidade\": \"EMP\", \"sobre\": \"gosto de trabalhar\", \"tem_experiencia\": false, \"exp_entidade\": \"\", \"exp_cargo\": \"\", \"exp_descricao\": \"\", \"exp_inicio\": \"\", \"exp_fim\": \"\", \"exp_atual\": false}, \"4\": {\"visivel\": true, \"consentimento_sms\": true, \"consentimento_whatsapp\": true, \"consentimento_email\": true, \"cv\": true, \"certificado\": true, \"bi\": true}}',4,'',1,1,1,'9814455','[]'),(3,'1999-12-12','M','Trindade - Folha Fede','PEM','SIM','[\"INF\", \"Robotica\"]','EMP','',1,1,1,'2026-03-20 00:37:58.486115','2026-03-20 15:03:44.373042',4,'{}',10,'',1,1,1,'','[]'),(4,'2002-08-15','F','Ponte Mina','PEM','SIM','[\"TIC\", \"SER\", \"ADM\"]','EMP','Jovem com interesse em atendimento digital, ferramentas de escritorio e apoio administrativo.',1,1,1,'2026-03-20 19:49:11.009274','2026-03-20 19:54:11.307834',4,'{}',11,'',1,1,1,'+239 980 1001','[]'),(5,'2015-02-20','M','Trindade','DES','SIM','[\"TUR\"]','EST','',1,1,1,'2026-03-23 12:34:27.924273','2026-03-23 13:11:44.491871',4,'{}',13,'youth_avatars/IMG_20260220_151618.jpg',1,1,1,'9814455','[]'),(6,'2004-05-23','F','Folha Fede - trindade','DES','SIM','[\"EDU\"]','EMP','',1,1,1,'2026-03-24 12:40:37.808332','2026-03-24 15:25:15.089854',4,'{}',14,'',1,1,1,'','[{\"idioma\": \"Portugues\", \"dominio\": \"AMBOS\"}]'),(7,'1997-02-12','M','Trindade','DES','SIM','[\"TIC\", \"ENE\"]','EMP','',1,1,1,'2026-03-25 10:20:45.641125','2026-03-25 10:29:58.293318',4,'{}',15,'',1,1,1,'','[]'),(8,NULL,'','','DES','SIM','[]','EMP','',0,0,1,'2026-03-29 17:08:53.814917','2026-03-29 17:08:53.814917',1,'{}',16,'',0,0,0,'','[]'),(9,'2026-03-29','M','Folha-fede','DES','SIM','[]','EMP','',1,0,0,'2026-03-29 17:11:36.130602','2026-03-29 19:32:47.942066',4,'{}',18,'',0,0,0,'','[]'),(10,'1998-09-19','M','Folha-fede','DES','SIM','[\"ADM\", \"ELE\"]','EMP','',1,1,0,'2026-03-29 19:38:18.358160','2026-03-29 21:53:13.087321',4,'{}',19,'',0,0,0,'','[{\"idioma\": \"Portugu\\u00eas\", \"dominio\": \"AMBOS\"}]');
/*!40000 ALTER TABLE `profiles_youthprofile` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `profiles_youthskill`
--

DROP TABLE IF EXISTS `profiles_youthskill`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `profiles_youthskill` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `nivel` int(11) NOT NULL,
  `profile_id` bigint(20) NOT NULL,
  `skill_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `profiles_youthskill_profile_id_skill_id_9d2bdac1_uniq` (`profile_id`,`skill_id`),
  KEY `profiles_youthskill_skill_id_fe277fc6_fk_core_skill_id` (`skill_id`),
  CONSTRAINT `profiles_youthskill_profile_id_22f6865f_fk_profiles_` FOREIGN KEY (`profile_id`) REFERENCES `profiles_youthprofile` (`id`),
  CONSTRAINT `profiles_youthskill_skill_id_fe277fc6_fk_core_skill_id` FOREIGN KEY (`skill_id`) REFERENCES `core_skill` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=30 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `profiles_youthskill`
--

LOCK TABLES `profiles_youthskill` WRITE;
/*!40000 ALTER TABLE `profiles_youthskill` DISABLE KEYS */;
INSERT INTO `profiles_youthskill` VALUES (1,1,1,3),(2,1,1,5),(3,1,1,6),(4,1,1,7),(5,1,1,9),(6,1,1,11),(7,1,1,12),(8,1,1,13),(9,1,1,14),(10,1,1,19),(11,1,1,20),(12,1,2,2),(13,1,2,3),(14,1,2,4),(15,1,2,8),(16,1,2,9),(17,1,2,10),(18,1,2,11),(19,1,3,17),(20,2,4,1),(21,2,4,2),(22,2,4,3),(23,1,6,17),(24,1,7,12),(25,1,7,14),(26,1,7,15),(27,1,10,1),(28,1,10,3),(29,1,10,17);
/*!40000 ALTER TABLE `profiles_youthskill` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping routines for database 'base_nacional_jovens'
--
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-03-30 11:55:37
