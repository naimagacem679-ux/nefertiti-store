-- Néfertiti store — D1 (SQLite) schema. Phase 1.
-- Apply with:  wrangler d1 execute nefertiti-db --file=db/schema.sql [--local | --remote]
PRAGMA foreign_keys = ON;

-- Store identity / texts. value is JSON text. Images are stored as R2 keys, never as data URIs.
CREATE TABLE IF NOT EXISTS settings (
  key        TEXT PRIMARY KEY,
  value      TEXT NOT NULL,
  updated_at INTEGER NOT NULL DEFAULT (unixepoch())
);

-- Social links shown in the store (order, visibility, avatar circle, QR).
CREATE TABLE IF NOT EXISTS socials (
  platform   TEXT PRIMARY KEY,             -- instagram | facebook | tiktok | telegram
  url        TEXT NOT NULL DEFAULT '',
  sort       INTEGER NOT NULL DEFAULT 0,
  enabled    INTEGER NOT NULL DEFAULT 1,
  avatar_key TEXT NOT NULL DEFAULT '',     -- R2 key
  qr_key     TEXT NOT NULL DEFAULT ''      -- R2 key
);

-- Delivery price per wilaya (1..58).
CREATE TABLE IF NOT EXISTS shipping (
  wilaya_code INTEGER PRIMARY KEY CHECK (wilaya_code BETWEEN 1 AND 58),
  wilaya_name TEXT NOT NULL,
  home_price  INTEGER NOT NULL CHECK (home_price >= 0),
  desk_price  INTEGER NOT NULL CHECK (desk_price >= 0)
);

-- Multi-level categories (same ids as the current store, so nothing breaks).
CREATE TABLE IF NOT EXISTS categories (
  id        TEXT PRIMARY KEY,
  name      TEXT NOT NULL,
  name_en   TEXT NOT NULL DEFAULT '',
  parent_id TEXT REFERENCES categories(id) ON DELETE CASCADE,
  sort      INTEGER NOT NULL DEFAULT 0,
  img_key   TEXT NOT NULL DEFAULT '',
  hidden    INTEGER NOT NULL DEFAULT 0,
  is_needs  INTEGER NOT NULL DEFAULT 0,    -- the "shop by need" section
  facets    TEXT NOT NULL DEFAULT '[]'     -- JSON: filters of the section
);
CREATE INDEX IF NOT EXISTS idx_categories_parent ON categories(parent_id);

CREATE TABLE IF NOT EXISTS products (
  id          TEXT PRIMARY KEY,
  name        TEXT NOT NULL,
  brand       TEXT NOT NULL DEFAULT '',
  price       INTEGER NOT NULL CHECK (price >= 0),
  old_price   INTEGER NOT NULL DEFAULT 0,
  stock       INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),   -- used when the product has no variants
  size        TEXT NOT NULL DEFAULT '',
  description TEXT NOT NULL DEFAULT '',
  ingredients TEXT NOT NULL DEFAULT '',
  usage       TEXT NOT NULL DEFAULT '',
  colors      TEXT NOT NULL DEFAULT '[]',  -- JSON (colors without separate stock)
  sizes       TEXT NOT NULL DEFAULT '[]',  -- JSON (sizes without separate stock)
  attrs       TEXT NOT NULL DEFAULT '{}',  -- JSON: per-section attributes
  is_new      INTEGER NOT NULL DEFAULT 0,
  is_best     INTEGER NOT NULL DEFAULT 0,
  hidden      INTEGER NOT NULL DEFAULT 0,
  is_demo     INTEGER NOT NULL DEFAULT 0,
  created_at  INTEGER NOT NULL DEFAULT 0   -- same "ts" as today (used for "newest")
);
CREATE INDEX IF NOT EXISTS idx_products_brand ON products(brand);

-- One product in many categories, without duplicating the product.
CREATE TABLE IF NOT EXISTS product_categories (
  product_id  TEXT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  category_id TEXT NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
  PRIMARY KEY (product_id, category_id)
);
CREATE INDEX IF NOT EXISTS idx_pc_category ON product_categories(category_id);

-- Stock per size/colour.
CREATE TABLE IF NOT EXISTS product_variants (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  product_id TEXT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  size       TEXT NOT NULL DEFAULT '',
  color      TEXT NOT NULL DEFAULT '',
  stock      INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
  UNIQUE (product_id, size, color)
);

-- Images live in R2; the DB keeps only the key. position 0 = main image.
CREATE TABLE IF NOT EXISTS product_images (
  product_id TEXT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  position   INTEGER NOT NULL,
  image_key  TEXT NOT NULL,
  PRIMARY KEY (product_id, position)
);

-- Customer reviews. Nothing is public until approved = 1.
CREATE TABLE IF NOT EXISTS reviews (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  product_id TEXT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  name       TEXT NOT NULL,
  quality    INTEGER NOT NULL CHECK (quality BETWEEN 1 AND 5),
  service    INTEGER NOT NULL CHECK (service BETWEEN 1 AND 5),
  text       TEXT NOT NULL DEFAULT '',
  approved   INTEGER NOT NULL DEFAULT 0,
  created_at INTEGER NOT NULL DEFAULT (unixepoch())
);

-- Orders. See docs/ORDER-STATES.md: stock is NOT touched when an order is created
-- or when WhatsApp opens; it is deducted only when the owner moves the order to 'confirmed'.
CREATE TABLE IF NOT EXISTS orders (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  ref            TEXT NOT NULL UNIQUE,      -- public reference, e.g. NF-20261114-7K3Q
  customer_name  TEXT NOT NULL,
  phone          TEXT NOT NULL,
  wilaya_code    INTEGER NOT NULL,
  wilaya_name    TEXT NOT NULL,
  commune        TEXT NOT NULL DEFAULT '',
  address        TEXT NOT NULL DEFAULT '',
  delivery_mode  TEXT NOT NULL CHECK (delivery_mode IN ('home','desk')),
  subtotal       INTEGER NOT NULL,          -- computed on the server from DB prices
  shipping       INTEGER NOT NULL,
  total          INTEGER NOT NULL,
  status         TEXT NOT NULL DEFAULT 'new'
                 CHECK (status IN ('new','confirmed','shipped','delivered','cancelled','returned','no_answer')),
  stock_committed INTEGER NOT NULL DEFAULT 0, -- 1 once stock was deducted for this order
  note           TEXT NOT NULL DEFAULT '',
  created_at     INTEGER NOT NULL DEFAULT (unixepoch()),
  updated_at     INTEGER NOT NULL DEFAULT (unixepoch())
);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status, created_at);

CREATE TABLE IF NOT EXISTS order_items (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id     INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  product_id   TEXT NOT NULL,               -- no FK: history must survive product deletion
  variant_id   INTEGER,
  product_name TEXT NOT NULL,               -- snapshot at order time
  brand        TEXT NOT NULL DEFAULT '',
  size         TEXT NOT NULL DEFAULT '',
  color        TEXT NOT NULL DEFAULT '',
  unit_price   INTEGER NOT NULL,
  qty          INTEGER NOT NULL CHECK (qty > 0)
);
CREATE INDEX IF NOT EXISTS idx_items_order ON order_items(order_id);

-- Every status change (who/when), and every stock change (why).
CREATE TABLE IF NOT EXISTS order_status_log (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id    INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  from_status TEXT,
  to_status   TEXT NOT NULL,
  actor       TEXT NOT NULL DEFAULT 'system', -- 'customer' | 'owner:<email from Access>' | 'system'
  at          INTEGER NOT NULL DEFAULT (unixepoch())
);

CREATE TABLE IF NOT EXISTS stock_movements (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  product_id TEXT NOT NULL,
  variant_id INTEGER,
  delta      INTEGER NOT NULL,              -- negative = sold, positive = restored / manual
  reason     TEXT NOT NULL,                 -- 'order_confirmed' | 'order_cancelled' | 'manual' | 'seed'
  order_id   INTEGER,
  actor      TEXT NOT NULL DEFAULT 'system',
  at         INTEGER NOT NULL DEFAULT (unixepoch())
);
