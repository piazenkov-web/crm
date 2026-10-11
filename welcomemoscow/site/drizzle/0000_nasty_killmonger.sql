CREATE TABLE `portal_records` (
	`id` text PRIMARY KEY NOT NULL,
	`owner` text NOT NULL,
	`role` text NOT NULL,
	`kind` text NOT NULL,
	`payload` text NOT NULL,
	`created` text NOT NULL
);
--> statement-breakpoint
CREATE TABLE `booking_rewards` (
	`id` text PRIMARY KEY NOT NULL,
	`owner` text NOT NULL,
	`role` text NOT NULL,
	`booking_id` text NOT NULL,
	`paid_kopecks` integer NOT NULL,
	`reward_kopecks` integer NOT NULL,
	`status` text NOT NULL,
	`confirmed_at` text NOT NULL,
	`paid_at` text
);
--> statement-breakpoint
CREATE UNIQUE INDEX `reward_booking_recipient` ON `booking_rewards` (`owner`,`role`,`booking_id`);