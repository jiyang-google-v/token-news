import { integer, sqliteTable, text } from 'drizzle-orm/sqlite-core';
export const events = sqliteTable('events', { id: text('id').primaryKey(), data: text('data').notNull(), firstSeen: text('first_seen').notNull(), updatedAt: text('updated_at').notNull(), starred: integer('starred').notNull().default(0) });
export const runs = sqliteTable('runs', { id: text('id').primaryKey(), at: text('at').notNull(), kind: text('kind').notNull(), count: integer('count').notNull(), detail: text('detail').notNull() });
export const revisions = sqliteTable('revisions', { id: text('id').primaryKey(), eventId: text('event_id').notNull(), at: text('at').notNull(), data: text('data').notNull() });
