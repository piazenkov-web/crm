import {sqliteTable,text,integer,uniqueIndex} from 'drizzle-orm/sqlite-core';
export const records=sqliteTable('portal_records',{id:text('id').primaryKey(),owner:text('owner').notNull(),role:text('role').notNull(),kind:text('kind').notNull(),payload:text('payload').notNull(),created:text('created').notNull()});
export const rewards=sqliteTable('booking_rewards',{
 id:text('id').primaryKey(),owner:text('owner').notNull(),role:text('role').notNull(),bookingId:text('booking_id').notNull(),paidKopecks:integer('paid_kopecks').notNull(),rewardKopecks:integer('reward_kopecks').notNull(),status:text('status').notNull(),confirmedAt:text('confirmed_at').notNull(),paidAt:text('paid_at')
},table=>[uniqueIndex('reward_booking_recipient').on(table.owner,table.role,table.bookingId)]);
