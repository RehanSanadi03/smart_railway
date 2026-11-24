-- Smart Railway Management System - Database Schema
-- Compatible with MySQL 8.0+

CREATE DATABASE IF NOT EXISTS smart_railway;
USE smart_railway;

SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS `booking_seat`;
DROP TABLE IF EXISTS `booking`;
DROP TABLE IF EXISTS `passenger`;
DROP TABLE IF EXISTS `run_seat`;
DROP TABLE IF EXISTS `train_run`;
DROP TABLE IF EXISTS `seat`;
DROP TABLE IF EXISTS `coach`;
DROP TABLE IF EXISTS `train_stop`;
DROP TABLE IF EXISTS `train`;
DROP TABLE IF EXISTS `station`;

SET FOREIGN_KEY_CHECKS = 1;

-- Table structure for table `station`
CREATE TABLE `station` (
  `station_id` int NOT NULL AUTO_INCREMENT,
  `station_code` varchar(10) NOT NULL,
  `station_name` varchar(100) NOT NULL,
  `city` varchar(100) NOT NULL,
  `state` varchar(100) NOT NULL,
  PRIMARY KEY (`station_id`),
  UNIQUE KEY `station_code` (`station_code`)
) ENGINE=InnoDB AUTO_INCREMENT=155 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table structure for table `train`
CREATE TABLE `train` (
  `train_id` int NOT NULL AUTO_INCREMENT,
  `train_number` varchar(10) NOT NULL,
  `train_name` varchar(100) NOT NULL,
  `train_type` varchar(30) NOT NULL,
  PRIMARY KEY (`train_id`),
  UNIQUE KEY `train_number` (`train_number`)
) ENGINE=InnoDB AUTO_INCREMENT=18 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table structure for table `train_stop`
CREATE TABLE `train_stop` (
  `train_id` int NOT NULL,
  `station_id` int NOT NULL,
  `stop_number` int NOT NULL,
  `arrival_time` time DEFAULT NULL,
  `departure_time` time DEFAULT NULL,
  `distance_from_source` decimal(8,2) DEFAULT NULL,
  PRIMARY KEY (`train_id`,`station_id`),
  UNIQUE KEY `train_id` (`train_id`,`stop_number`),
  KEY `station_id` (`station_id`),
  CONSTRAINT `train_stop_ibfk_1` FOREIGN KEY (`train_id`) REFERENCES `train` (`train_id`),
  CONSTRAINT `train_stop_ibfk_2` FOREIGN KEY (`station_id`) REFERENCES `station` (`station_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table structure for table `coach`
CREATE TABLE `coach` (
  `coach_id` int NOT NULL AUTO_INCREMENT,
  `train_id` int NOT NULL,
  `coach_number` varchar(10) NOT NULL,
  `coach_type` varchar(30) NOT NULL,
  PRIMARY KEY (`coach_id`),
  UNIQUE KEY `train_id` (`train_id`,`coach_number`),
  CONSTRAINT `coach_ibfk_1` FOREIGN KEY (`train_id`) REFERENCES `train` (`train_id`)
) ENGINE=InnoDB AUTO_INCREMENT=23 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table structure for table `seat`
CREATE TABLE `seat` (
  `seat_id` int NOT NULL AUTO_INCREMENT,
  `coach_id` int NOT NULL,
  `seat_number` int NOT NULL,
  `berth_type` varchar(20) NOT NULL,
  PRIMARY KEY (`seat_id`),
  UNIQUE KEY `coach_id` (`coach_id`,`seat_number`),
  CONSTRAINT `seat_ibfk_1` FOREIGN KEY (`coach_id`) REFERENCES `coach` (`coach_id`),
  CONSTRAINT `seat_chk_1` CHECK ((`seat_number` between 1 and 72))
) ENGINE=InnoDB AUTO_INCREMENT=1153 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table structure for table `train_run`
CREATE TABLE `train_run` (
  `run_id` int NOT NULL AUTO_INCREMENT,
  `train_id` int NOT NULL,
  `journey_date` date NOT NULL,
  `running_status` varchar(20) DEFAULT 'Scheduled',
  PRIMARY KEY (`run_id`),
  UNIQUE KEY `train_id` (`train_id`,`journey_date`),
  CONSTRAINT `train_run_ibfk_1` FOREIGN KEY (`train_id`) REFERENCES `train` (`train_id`),
  CONSTRAINT `train_run_chk_1` CHECK ((`running_status` in (_cp850'Scheduled',_cp850'Cancelled',_cp850'Completed')))
) ENGINE=InnoDB AUTO_INCREMENT=270 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table structure for table `run_seat`
CREATE TABLE `run_seat` (
  `run_seat_id` int NOT NULL AUTO_INCREMENT,
  `run_id` int NOT NULL,
  `seat_id` int NOT NULL,
  `seat_status` varchar(20) DEFAULT 'Available',
  PRIMARY KEY (`run_seat_id`),
  UNIQUE KEY `run_id` (`run_id`,`seat_id`),
  KEY `seat_id` (`seat_id`),
  CONSTRAINT `run_seat_ibfk_1` FOREIGN KEY (`run_id`) REFERENCES `train_run` (`run_id`),
  CONSTRAINT `run_seat_ibfk_2` FOREIGN KEY (`seat_id`) REFERENCES `seat` (`seat_id`),
  CONSTRAINT `run_seat_chk_1` CHECK ((`seat_status` in (_cp850'Available',_cp850'Booked',_cp850'Blocked')))
) ENGINE=InnoDB AUTO_INCREMENT=35497 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table structure for table `passenger`
CREATE TABLE `passenger` (
  `passenger_id` int NOT NULL AUTO_INCREMENT,
  `passenger_name` varchar(100) NOT NULL,
  `email` varchar(100) DEFAULT NULL,
  `phone_number` varchar(20) DEFAULT NULL,
  `age` int DEFAULT NULL,
  `date_of_birth` date DEFAULT NULL,
  PRIMARY KEY (`passenger_id`),
  UNIQUE KEY `email` (`email`),
  UNIQUE KEY `phone_number` (`phone_number`),
  CONSTRAINT `passenger_chk_1` CHECK (((`age` >= 5) and (`age` <= 120)))
) ENGINE=InnoDB AUTO_INCREMENT=12 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table structure for table `booking`
CREATE TABLE `booking` (
  `booking_id` int NOT NULL AUTO_INCREMENT,
  `passenger_id` int NOT NULL,
  `run_id` int NOT NULL,
  `booking_date` datetime DEFAULT CURRENT_TIMESTAMP,
  `booking_status` varchar(20) DEFAULT 'Confirmed',
  `total_fare` decimal(10,2) NOT NULL,
  PRIMARY KEY (`booking_id`),
  KEY `passenger_id` (`passenger_id`),
  KEY `run_id` (`run_id`),
  CONSTRAINT `booking_ibfk_1` FOREIGN KEY (`passenger_id`) REFERENCES `passenger` (`passenger_id`),
  CONSTRAINT `booking_ibfk_2` FOREIGN KEY (`run_id`) REFERENCES `train_run` (`run_id`),
  CONSTRAINT `booking_chk_1` CHECK ((`booking_status` in (_cp850'Confirmed',_cp850'Cancelled',_cp850'Pending'))),
  CONSTRAINT `booking_chk_2` CHECK ((`total_fare` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table structure for table `booking_seat`
CREATE TABLE `booking_seat` (
  `booking_seat_id` int NOT NULL AUTO_INCREMENT,
  `booking_id` int NOT NULL,
  `seat_id` int NOT NULL,
  `seat_fare` decimal(10,2) NOT NULL,
  PRIMARY KEY (`booking_seat_id`),
  UNIQUE KEY `booking_id` (`booking_id`,`seat_id`),
  KEY `seat_id` (`seat_id`),
  CONSTRAINT `booking_seat_ibfk_1` FOREIGN KEY (`booking_id`) REFERENCES `booking` (`booking_id`),
  CONSTRAINT `booking_seat_ibfk_2` FOREIGN KEY (`seat_id`) REFERENCES `seat` (`seat_id`),
  CONSTRAINT `booking_seat_chk_1` CHECK ((`seat_fare` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
