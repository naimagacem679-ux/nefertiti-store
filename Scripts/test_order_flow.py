#!/usr/bin/env python3
"""Executable specification of the order/stock rules (docs/ORDER-STATES.md), tested on SQLite
   with the real schema. Phase 2 functions must run the same SQL inside one D1 batch (transaction)."""
import os, sqlite3, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db = sqlite3.connect(":memory:", isolation_level=None); db.row_factory = sqlite3.Row
db.executescript(open(os.path.join(ROOT, "db/schema.sql"), encoding="utf8").read())
db.execute("insert into categories(id,name) values('c','c')")
db.execute("insert into products(id,name,price,stock) values('p1','Serum',3000,5)")
db.execute("insert into products(id,name,price,stock) values('p2','Shirt',2000,0)")
db.execute("insert into product_variants(product_id,size,color,stock) values('p2','M','Red',2)")
vid = db.execute("select id from product_variants").fetchone()[0]
stock = lambda: (db.execute("select stock from products where id='p1'").fetchone()[0], db.execute("select stock from product_variants where id=?", (vid,)).fetchone()[0])
fails = []
def ok(name, cond):
    print(("PASS " if cond else "FAIL ") + name); cond or fails.append(name)

def create_order():
    c = db.execute("insert into orders(ref,customer_name,phone,wilaya_code,wilaya_name,delivery_mode,subtotal,shipping,total) values(?,?,?,?,?,?,?,?,?)",
                   ("NF-T%d" % db.execute("select count(*) from orders").fetchone()[0], "A", "0550000000", 16, "الجزائر", "home", 8000, 500, 8500))
    oid = c.lastrowid
    db.execute("insert into order_items(order_id,product_id,product_name,unit_price,qty) values(?,?,?,?,?)", (oid, "p1", "Serum", 3000, 2))
    db.execute("insert into order_items(order_id,product_id,variant_id,product_name,size,color,unit_price,qty) values(?,?,?,?,?,?,?,?)", (oid, "p2", vid, "Shirt", "M", "Red", 2000, 1))
    db.execute("insert into order_status_log(order_id,from_status,to_status,actor) values(?,NULL,'new','customer')", (oid,))
    return oid

def set_status(oid, new, actor="owner:test@example.com"):
    """The only allowed way to change a status. One transaction; returns False if refused."""
    db.execute("begin")
    try:
        o = db.execute("select status, stock_committed from orders where id=?", (oid,)).fetchone()
        allowed = {"new": {"confirmed", "cancelled", "no_answer"}, "no_answer": {"confirmed", "cancelled"}, "confirmed": {"shipped", "cancelled"},
                   "shipped": {"delivered", "returned"}, "delivered": {"returned"}, "cancelled": set(), "returned": set()}
        if new not in allowed[o["status"]]: raise ValueError("transition not allowed")
        if new == "confirmed" and not o["stock_committed"]:
            for it in db.execute("select * from order_items where order_id=?", (oid,)).fetchall():
                if it["variant_id"]: db.execute("update product_variants set stock = stock - ? where id=?", (it["qty"], it["variant_id"]))
                else: db.execute("update products set stock = stock - ? where id=?", (it["qty"], it["product_id"]))   # CHECK(stock>=0) aborts if short
                db.execute("insert into stock_movements(product_id,variant_id,delta,reason,order_id,actor) values(?,?,?,?,?,?)", (it["product_id"], it["variant_id"], -it["qty"], "order_confirmed", oid, actor))
            db.execute("update orders set stock_committed=1 where id=?", (oid,))
        if new in ("cancelled", "returned") and o["stock_committed"]:
            for it in db.execute("select * from order_items where order_id=?", (oid,)).fetchall():
                if it["variant_id"]: db.execute("update product_variants set stock = stock + ? where id=?", (it["qty"], it["variant_id"]))
                else: db.execute("update products set stock = stock + ? where id=?", (it["qty"], it["product_id"]))
                db.execute("insert into stock_movements(product_id,variant_id,delta,reason,order_id,actor) values(?,?,?,?,?,?)", (it["product_id"], it["variant_id"], it["qty"], "order_" + new, oid, actor))
            db.execute("update orders set stock_committed=0 where id=?", (oid,))
        db.execute("update orders set status=?, updated_at=unixepoch() where id=?", (new, oid))
        db.execute("insert into order_status_log(order_id,from_status,to_status,actor) values(?,?,?,?)", (oid, o["status"], new, actor))
        db.execute("commit"); return True
    except Exception as e:
        db.execute("rollback"); return False

ok("start stock", stock() == (5, 2))
a = create_order()
ok("creating an order does NOT touch stock", stock() == (5, 2))
ok("opening WhatsApp = nothing in the DB changes (order stays 'new')", db.execute("select status from orders where id=?", (a,)).fetchone()[0] == "new")
ok("new -> shipped is refused", set_status(a, "shipped") is False)
ok("confirm succeeds", set_status(a, "confirmed") is True)
ok("confirm deducted stock exactly once", stock() == (3, 1))
ok("confirming again is refused (no double deduction)", set_status(a, "confirmed") is False and stock() == (3, 1))
ok("cancel after confirm restores stock", set_status(a, "cancelled") and stock() == (5, 2))
ok("cancelled order cannot be re-opened", set_status(a, "confirmed") is False)
b = create_order(); c = create_order()
ok("order B confirmed", set_status(b, "confirmed") and stock() == (3, 1))
ok("order C needs 2 of p1 (3 left) + 1 variant (1 left): confirmed", set_status(c, "confirmed") and stock() == (1, 0))
d = create_order()
ok("order D cannot be confirmed: not enough stock, whole transaction rolled back", set_status(d, "confirmed") is False and stock() == (1, 0)
   and db.execute("select status,stock_committed from orders where id=?", (d,)).fetchone()[:] == ("new", 0))
ok("shipped -> delivered", set_status(b, "shipped") and set_status(b, "delivered"))
ok("return after delivery restores stock", set_status(b, "returned") and stock() == (3, 1))
ok("audit trail exists", db.execute("select count(*) from stock_movements").fetchone()[0] >= 6 and db.execute("select count(*) from order_status_log").fetchone()[0] >= 8)
print("RESULT:", "FAIL" if fails else "OK - all order/stock rules behave as specified"); sys.exit(1 if fails else 0)
