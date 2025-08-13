# -*- coding: utf-8 -*-
"""
Restaurant Manager — Flask (single-file)

Run:
  pip install flask==3.0.3 werkzeug==3.0.3
  # optional: pip install waitress==2.1.2
  python app.py
Login: admin / admin123
"""
from __future__ import annotations

import os, sqlite3, queue
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Optional

from flask import (
    Flask, request, redirect, url_for, jsonify, abort, make_response,
    render_template_string, g, session, Response, stream_with_context
)
from werkzeug.security import generate_password_hash, check_password_hash
from jinja2 import DictLoader

APP_TITLE = "Doman Restaurant"
DB_PATH = os.environ.get("RESTAURANT_DB", "restaurant.db")

app = Flask(__name__)
app.config.update(SECRET_KEY=os.environ.get("SECRET_KEY", "devkey"))

# ---------------------- DB helpers ----------------------
@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def _col_missing(conn, table: str, col: str) -> bool:
    cur = conn.execute(f"PRAGMA table_info({table})")
    return all(r[1] != col for r in cur.fetchall())

def init_db():
    with get_conn() as conn:
        c = conn.cursor()
        # tables (floor)
        c.execute("""
            CREATE TABLE IF NOT EXISTS tables(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                x REAL DEFAULT 10,
                y REAL DEFAULT 10,
                capacity INTEGER DEFAULT 2,
                status TEXT DEFAULT 'free' CHECK(status IN ('free','reserved','occupied')),
                size_px INTEGER DEFAULT 64,
                kind TEXT DEFAULT 'table',
                label TEXT
            )
        """)
        if _col_missing(conn, 'tables', 'size_px'):
            c.execute("ALTER TABLE tables ADD COLUMN size_px INTEGER DEFAULT 64")
        if _col_missing(conn, 'tables', 'kind'):
            c.execute("ALTER TABLE tables ADD COLUMN kind TEXT DEFAULT 'table'")
        if _col_missing(conn, 'tables', 'label'):
            c.execute("ALTER TABLE tables ADD COLUMN label TEXT")

        # menu
        c.execute("""
            CREATE TABLE IF NOT EXISTS menu(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price INTEGER NOT NULL,
                category TEXT
            )
        """)

        # orders
        c.execute("""
            CREATE TABLE IF NOT EXISTS orders(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_id INTEGER NOT NULL,
                opened_at TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('open','closed')),
                customer_name TEXT,
                FOREIGN KEY(table_id) REFERENCES tables(id)
            )
        """)
        if _col_missing(conn, 'orders', 'customer_name'):
            c.execute("ALTER TABLE orders ADD COLUMN customer_name TEXT")

        # order items
        c.execute("""
            CREATE TABLE IF NOT EXISTS order_items(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                menu_id INTEGER NOT NULL,
                qty INTEGER NOT NULL DEFAULT 1,
                price INTEGER NOT NULL,
                note TEXT,
                FOREIGN KEY(order_id) REFERENCES orders(id),
                FOREIGN KEY(menu_id) REFERENCES menu(id)
            )
        """)

        # invoices
        c.execute("""
            CREATE TABLE IF NOT EXISTS invoices(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                closed_at TEXT NOT NULL,
                subtotal INTEGER NOT NULL,
                discount INTEGER NOT NULL DEFAULT 0,
                tax INTEGER NOT NULL DEFAULT 0,
                total INTEGER NOT NULL,
                payment_method TEXT,
                customer_name TEXT,
                FOREIGN KEY(order_id) REFERENCES orders(id)
            )
        """)
        if _col_missing(conn, 'invoices', 'customer_name'):
            c.execute("ALTER TABLE invoices ADD COLUMN customer_name TEXT")

        # users
        c.execute("""
            CREATE TABLE IF NOT EXISTS users(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('admin','cashier'))
            )
        """)
        if c.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            c.execute(
                "INSERT INTO users(username, password_hash, role) VALUES(?,?,?)",
                ("admin", generate_password_hash("admin123"), "admin"),
            )

        # seeds
        if c.execute("SELECT COUNT(*) FROM menu").fetchone()[0] == 0:
            c.executemany(
                "INSERT INTO menu(name, price, category) VALUES(?,?,?)",
                [
                    ("پیتزا مارگاریتا", 850000, "پیتزا"),
                    ("کباب میکس", 650000, "کباب"),
                    ("سالاد سزار", 700000, "سالاد"),
                    ("کوکاکولا ۳۳۰ml", 50000, "نوشیدنی"),
                    ("آب معدنی", 30000, "نوشیدنی"),
                ],
            )
        if c.execute("SELECT COUNT(*) FROM tables").fetchone()[0] == 0:
            c.executemany(
                "INSERT INTO tables(name, x, y, capacity, status, size_px, kind, label) VALUES(?,?,?,?,?,?,?,?)",
                [
                    ("T1", 10, 20, 2, "free", 64, 'table', None),
                    ("T2", 40, 25, 4, "free", 64, 'table', None),
                    ("T3", 70, 50, 4, "reserved", 64, 'table', None),
                ],
            )

# ---------------------- Utils ----------------------
def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")

def fmt_rial(value) -> str:
    try:
        iv = int(round(float(value or 0)))
    except Exception:
        iv = 0
    return f"{iv:,}"
app.jinja_env.filters['rial'] = fmt_rial
def gregorian_to_jalali(gy, gm, gd):
    # الگوریتم استاندارد (jalaali)
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    gy2 = gy - (1 if gm < 3 else 0)
    days = 365*gy + (gy2+3)//4 - (gy2+99)//100 + (gy2+399)//400 + gd + g_d_m[gm-1] - 79
    j_np = days // 12053  # 33-year cycles
    days %= 12053
    jy = 979 + 33*j_np + 4*(days//1461)
    days %= 1461
    if days >= 366:
        jy += (days-1)//365
        days = (days-1) % 365
    if days < 186:
        jm = 1 + days//31
        jd = 1 + days%31
    else:
        days -= 186
        jm = 7 + days//30
        jd = 1 + days%30
    return jy, jm, jd

def today_jalali_str() -> str:
    dt = datetime.now()
    jy, jm, jd = gregorian_to_jalali(dt.year, dt.month, dt.day)
    return f"{jy:04d}/{jm:02d}/{jd:02d}"

def get_open_order(table_id: int) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM orders WHERE table_id=? AND status='open' ORDER BY id DESC LIMIT 1", (table_id,))
        return c.fetchone()

def ensure_open_order(table_id: int) -> int:
    ord_row = get_open_order(table_id)
    if ord_row:
        return ord_row["id"]
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("INSERT INTO orders(table_id, opened_at, status) VALUES(?,?, 'open')", (table_id, now_iso()))
        return c.lastrowid

# ---------------------- Real-time (SSE) ----------------------
class EventBroker:
    def __init__(self):
        self.subs = []
    def subscribe(self):
        q = queue.Queue()
        self.subs.append(q)
        return q
    def unsubscribe(self, q):
        try: self.subs.remove(q)
        except ValueError: pass
    def publish(self, typ='change'):
        # non-blocking fanout
        for q in list(self.subs):
            try: q.put_nowait(typ)
            except: pass

broker = EventBroker()

def notify_change():
    broker.publish('change')

@app.get('/events')
def sse_events():
    def gen():
        q = broker.subscribe()
        try:
            # initial ping so hx can bind
            yield 'event: change\ndata: init\n\n'
            while True:
                typ = q.get()
                yield f'event: {typ}\ndata: {now_iso()}\n\n'
        except GeneratorExit:
            broker.unsubscribe(q)
    return Response(stream_with_context(gen()), mimetype='text/event-stream')

# ---------------------- Templates ----------------------
BASE = r"""
<!doctype html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{{ title or app_title }}</title>
  <script src="https://unpkg.com/htmx.org@1.9.12"></script>
  <script src="https://unpkg.com/htmx.org@1.9.12/dist/ext/sse.js"></script>
  <script src="https://unpkg.com/hyperscript.org@0.9.12"></script>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    .table-dot { position:absolute; display:flex; align-items:center; justify-content:center; font-weight:700; box-shadow:0 4px 10px rgba(0,0,0,.12); border-radius:14px; user-select:none; }
    .status-free { background:#16a34a; color:white; }
    .status-reserved { background:#f59e0b; color:black; }
    .status-occupied { background:#ef4444; color:white; }
    .kind-cash { background:#8b5e3c; color:white; border:3px solid #5c3a23; }
    .chair { position:absolute; bottom:-10px; right:-10px; width:18px; height:18px; background:#374151; border-radius:4px; box-shadow:0 2px 6px rgba(0,0,0,.25); }
    .floor { position:relative; width:100%; height:70vh; background:repeating-linear-gradient(45deg,#f4f4f5,#f4f4f5 20px,#e4e4e7 20px,#e4e4e7 40px); border-radius:18px; }
    .badge { font-size:.75rem; padding:.125rem .375rem; border-radius:6px; background:#e5e7eb; }
    @keyframes blinky { 0%,100%{opacity:1; transform:scale(1);} 50%{opacity:.45; transform:scale(1.05);} }
    .blink { animation: blinky .6s ease-in-out 6; }
    .ctx { position:fixed; z-index:1000; background:#fff; border:1px solid #e5e7eb; box-shadow:0 10px 24px rgba(0,0,0,.12); border-radius:10px; padding:6px; min-width:180px; }
    .ctx-item { display:block; width:100%; text-align:right; padding:6px 10px; border-radius:8px; font-size:.9rem; }
    .ctx-item:hover { background:#f3f4f6; }
    .ctx-sep { height:1px; background:#e5e7eb; margin:6px 0; }
    .resize-h { position:absolute; bottom:-6px; left:-6px; width:16px; height:16px; border-radius:50%; background:#111827; opacity:.6; cursor:nwse-resize; }
    .table-dot:hover .resize-h{ opacity:.85; }
  </style>
</head>
<body class="min-h-screen bg-slate-50 text-slate-800"
      data-role="{{ session.get('role','') }}"
      data-page="{{ page|default('') }}">
  <header class="px-4 py-3 bg-white shadow sticky top-0 z-40">
    <div class="max-w-6xl mx-auto flex items-center gap-3">
      <div class="font-bold">{{ app_title }}</div>
      <nav class="ml-auto flex gap-2 text-sm">
        <a class="px-3 py-1 rounded hover:bg-slate-100" href="{{ url_for('index') }}">سالن</a>
        <a class="px-3 py-1 rounded hover:bg-slate-100" href="{{ url_for('menu_page') }}">منو</a>
        <a class="px-3 py-1 rounded hover:bg-slate-100" href="{{ url_for('reports') }}">گزارشات</a>
        {% if session.get('role')=='admin' %}
        <a class="px-3 py-1 rounded hover:bg-slate-100" href="{{ url_for('layout_editor') }}">چیدمان</a>
        <a class="px-3 py-1 rounded hover:bg-slate-100" href="{{ url_for('users') }}">کاربران</a>
        {% endif %}
      </nav>
      <div class="ml-4 flex items-center gap-2 text-sm">
        {% if session.get('uid') %}
          <span class="px-2 py-0.5 rounded bg-slate-100">{{ session['username'] }} · {{ 'ارشد' if session['role']=='admin' else 'صندوق' }}</span>
          <a class="px-3 py-1 rounded bg-slate-800 text-white" href="{{ url_for('logout') }}">خروج</a>
        {% else %}
          <a class="px-3 py-1 rounded bg-emerald-600 text-white" href="{{ url_for('login') }}">ورود</a>
        {% endif %}
      </div>
    </div>
  </header>

  <main class="max-w-6xl mx-auto p-4">
    {% block content %}{% endblock %}
  </main>

  <!-- Context menu (layout only) -->
  <div id="ctx" class="hidden ctx">
    <div id="ctx-title" class="px-2 py-1 text-xs text-slate-500"></div>
    <button class="ctx-item" data-act="status:free">علامت‌گذاری به «آزاد»</button>
    <button class="ctx-item" data-act="status:reserved">علامت‌گذاری به «رزرو»</button>
    <button class="ctx-item" data-act="status:occupied">علامت‌گذاری به «اشغال»</button>
    <button class="ctx-item" data-act="label">ثبت/ویرایش نام مشتری…</button>
    <button class="ctx-item" data-act="capacity" id="ctx-cap">تغییر ظرفیت…</button>
    <div class="ctx-sep"></div>
    <button class="ctx-item text-rose-600" data-act="delete" id="ctx-del">حذف</button>
  </div>

  <!-- Context menu (hall only) -->
  <div id="ctx-hall" class="hidden ctx">
    <div id="ctxh-title" class="px-2 py-1 text-xs text-slate-500"></div>
    <button class="ctx-item" data-act="open">ثبت/ویرایش سفارش…</button>
    <button class="ctx-item" data-act="checkout">تسویه / فاکتور…</button>
    <div class="ctx-sep"></div>
    <button class="ctx-item" data-act="menu">مدیریت منو…</button>
  </div>

  <!-- SSE source (global) -->
  <div id="evt-source" hx-ext="sse" sse-connect="{{ url_for('sse_events') }}"></div>

  <dialog id="dlg" class="p-0 rounded-2xl w-11/12 md:w-[640px]"></dialog>

  <script>
    function openDialog(html){ const dlg=document.getElementById('dlg'); dlg.innerHTML=html; dlg.showModal(); }
    function closeDialog(){ document.getElementById('dlg').close(); }

    // open dialog automatically when HTMX swaps into #dlg
    document.body.addEventListener('htmx:afterSwap', function(evt){
      if(evt.detail && evt.detail.target && evt.detail.target.id === 'dlg'){
        document.getElementById('dlg').showModal();
      }
    });

    // Blink occupied every minute (~3.6s pulse)
    function pulseOccupied(){ document.querySelectorAll('.status-occupied').forEach(el=>{ el.classList.add('blink'); setTimeout(()=>el.classList.remove('blink'), 3600); }); }
    setInterval(pulseOccupied, 60000);

    // Context menu events ONLY in layout page
    if (document.body.dataset.page === 'layout') {
      const ctx = document.getElementById('ctx');
      const ctxTitle = document.getElementById('ctx-title');
      let ctxTarget = null;

      document.addEventListener('contextmenu', (e)=>{
        const btn = e.target.closest('.table-dot');
        if(!btn) return;
        e.preventDefault();
        ctxTarget = btn;
        const id = btn.dataset.id || '?';
        const name = btn.textContent.trim();
        ctxTitle.textContent = `#${id} — ${name}`;
        const x = Math.min(e.clientX, window.innerWidth - 200);
        const y = Math.min(e.clientY, window.innerHeight - 200);
        ctx.style.left = x + 'px';
        ctx.style.top = y + 'px';
        ctx.classList.remove('hidden');
      });
      document.addEventListener('click', (e)=>{
        if(!ctx.classList.contains('hidden') && !e.target.closest('#ctx')){ ctx.classList.add('hidden'); }
      });

      ctx.addEventListener('click', (e)=>{
        const act = e.target.closest('.ctx-item')?.dataset.act; if(!act || !ctxTarget) return;
        const id = parseInt(ctxTarget.dataset.id);
        if(act.startsWith('status:')){
          const status = act.split(':')[1];
          fetch(`{{ url_for('layout_set_status') }}`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({id, status})})
            .then(r=>r.json()).then(js=>{ if(!js.ok){ alert(js.message||'خطا در تغییر وضعیت'); } location.reload(); });
        } else if(act==='delete'){
          const st = ctxTarget.dataset.status || (ctxTarget.className.includes('status-occupied') ? 'occupied' : '');
          if(st==='occupied'){ alert('میز اشغال‌شده قابل حذف نیست.'); ctx.classList.add('hidden'); return; }
          fetch(`{{ url_for('layout_remove') }}`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({id})})
            .then(r=>r.json()).then(js=>{ if(!js.ok){ alert(js.message||'حذف نشد'); } location.reload(); });
        } else if(act==='label'){
          const cur = ctxTarget.dataset.label || '';
          const val = prompt('نام مشتری برای نمایش روی میز:', cur);
          if(val===null) { ctx.classList.add('hidden'); return; }
          fetch(`{{ url_for('layout_set_label') }}`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({id, label: val})})
            .then(r=>r.json()).then(js=>{ if(!js.ok){ alert(js.message||'ثبت نام انجام نشد'); } location.reload(); });
        } else if(act==='capacity'){
          if(document.body.dataset.role !== 'admin'){ alert('فقط کاربر ارشد می‌تواند ظرفیت را تغییر دهد.'); ctx.classList.add('hidden'); return; }
          const cur = parseInt(ctxTarget.dataset.capacity||'2');
          const val = prompt('ظرفیت میز (عدد):', cur);
          if(val===null) { ctx.classList.add('hidden'); return; }
          const num = parseInt(val);
          if(!Number.isFinite(num) || num<1 || num>20){ alert('عدد معتبر وارد کنید (۱ تا ۲۰).'); ctx.classList.add('hidden'); return; }
          fetch(`{{ url_for('layout_set_capacity') }}`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({id, capacity: num})})
            .then(r=>r.json()).then(js=>{ if(!js.ok){ alert(js.message||'تغییر ظرفیت انجام نشد'); } location.reload(); });
        }
        ctx.classList.add('hidden');
      });

      // Hide admin-only items for non-admin
      document.addEventListener('DOMContentLoaded', ()=>{
        const role = document.body.dataset.role || '';
        if(role !== 'admin'){
          const cap = document.getElementById('ctx-cap'); if(cap) cap.style.display='none';
          const del = document.getElementById('ctx-del'); if(del) del.style.display='none';
        }
      });
    }

    // Context menu for HALL page (right click)
    if (document.body.dataset.page === 'hall') {
      const ctx = document.getElementById('ctx-hall');
      const title = document.getElementById('ctxh-title');
      let target = null;

      document.addEventListener('contextmenu', (e)=>{
        const btn = e.target.closest('.table-dot');
        if(!btn) return;
        if (btn.dataset.kind === 'cash') return; // ignore cashier desk
        e.preventDefault();
        target = btn;
        const id = btn.dataset.id || '?';
        const name = btn.textContent.trim();
        title.textContent = `#${id} — ${name}`;
        const x = Math.min(e.clientX, window.innerWidth - 200);
        const y = Math.min(e.clientY, window.innerHeight - 200);
        ctx.style.left = x + 'px';
        ctx.style.top = y + 'px';
        ctx.classList.remove('hidden');
      });

      document.addEventListener('click', (e)=>{
        if(!ctx.classList.contains('hidden') && !e.target.closest('#ctx-hall')){
          ctx.classList.add('hidden');
        }
      });

      ctx.addEventListener('click', (e)=>{
        const act = e.target.closest('.ctx-item')?.dataset.act;
        if(!act || !target) return;
        const id = parseInt(target.dataset.id);
        if (act === 'open') {
          fetch(`{{ url_for('table_modal', table_id=0) }}`.replace('0', id))
            .then(r=>r.text()).then(html=>openDialog(html));
        } else if (act === 'checkout') {
          const url = `{{ url_for('table_modal', table_id=0) }}`.replace('0', id) + '?show=checkout';
          fetch(url).then(r=>r.text()).then(html=>openDialog(html));
        } else if (act === 'menu') {
          fetch(`{{ url_for('menu_manage') }}`).then(r=>r.text()).then(html=>openDialog(html));
        }
        ctx.classList.add('hidden');
      });
    }
  </script>
</body>
</html>
"""

# ---- Hall floor (index + live fragment) ----
FLOOR = r"""
<div class="floor" id="floor"
     hx-get="{{ url_for('hall_floor') }}" hx-trigger="sse:change from:#evt-source" hx-swap="outerHTML">
  {% for t in tables %}
    {% set cls = 'kind-cash' if t['kind']=='cash' else 'status-' + t['status'] %}
    <button class="table-dot {{cls}}"
            style="left: {{t['x']}}%; top: {{t['y']}}%; width: {{t['size_px']}}px; height: {{t['size_px']}}px;"
            data-id="{{t['id']}}"
            data-kind="{{ t['kind'] }}"
            data-capacity="{{t['capacity']}}"
            data-label="{{t['cust'] or t['label'] or ''}}"
            data-status="{{t['status']}}"
            {% if t['kind']!='cash' %}
            hx-get="{{ url_for('table_modal', table_id=t['id']) }}" hx-target="#dlg" hx-swap="innerHTML"
            {% endif %}
            >
      <div class="flex flex-col items-center leading-tight">
        <div>{{ 'صندوق' if t['kind']=='cash' else t['name'] }}</div>
        {% set name_line = (t['cust'] or t['label']) %}
        {% if name_line %}
          <div class="text-[10px] font-normal opacity-90 mt-0.5">{{ name_line }} · ظرفیت {{ t['capacity'] }} نفر</div>
        {% else %}
          <div class="text-[10px] font-normal opacity-70 mt-0.5">ظرفیت {{ t['capacity'] }} نفر</div>
        {% endif %}
      </div>
      {% if t['kind']=='cash' %}<span class="chair" title="chair"></span>{% endif %}
    </button>
  {% endfor %}
</div>
"""

INDEX = r"""
{% extends 'base.html' %}
{% block content %}

  <!-- تاریخ شمسی و ساعت زنده -->
  <div class="mb-3 flex items-center gap-2">
    <div class="px-3 py-1 rounded bg-white border text-sm">
      تاریخ (شمسی): <span class="font-semibold">{{ jalali_today }}</span>
    </div>
    <div class="px-3 py-1 rounded bg-white border text-sm">
      ساعت: <span id="liveclock" class="font-semibold">--:--:--</span>
    </div>
  </div>

  <div class="mb-3 text-sm flex gap-2 items-center">
    <span class="badge">سبز=آزاد</span>
    <span class="badge">نارنجی=رزرو</span>
    <span class="badge">قرمز=اشغال</span>
    <span class="badge" style="background:#8b5e3c;color:#fff">قهوه‌ای=صندوق</span>
  </div>

  <div class="mb-2">
    <button class="px-3 py-2 rounded bg-emerald-600 text-white"
            hx-get="{{ url_for('menu_manage') }}" hx-target="#dlg" hx-swap="innerHTML">
      مدیریت منو
    </button>
  </div>

  {% include 'floor.html' %}

  <script>
    (function(){
      const el = document.getElementById('liveclock');
      function pad(n){ return (n<10?'0':'')+n; }
      function tick(){
        const d = new Date();
        el.textContent = pad(d.getHours()) + ':' + pad(d.getMinutes()) + ':' + pad(d.getSeconds());
      }
      tick();
      setInterval(tick, 1000);
    })();
  </script>
{% endblock %}
"""


TABLE_MODAL = r"""
<form class="bg-white rounded-2xl p-4 grid gap-3" hx-post="{{ url_for('table_action', table_id=table['id']) }}" hx-target="#dlg" hx-swap="innerHTML">
  <div class="flex items-center gap-2">
    <div class="text-lg font-bold">میز {{ table['name'] }}</div>
    <span class="badge">ظرفیت: {{ table['capacity'] }}</span>
    <span class="ml-auto"></span>
    <button type="button" class="px-3 py-1 rounded bg-slate-100" onclick="closeDialog()">بستن</button>
  </div>
  <div class="flex flex-wrap items-center gap-2">
    <label class="text-sm">وضعیت:</label>
    <select name="status" class="border rounded p-2">
      {% for s in ['free','reserved','occupied'] %}
      <option value="{{s}}" {% if s==table['status'] %}selected{% endif %}>{{ {'free':'آزاد','reserved':'رزرو','occupied':'اشغال'}[s] }}</option>
      {% endfor %}
    </select>
    <button name="_op" value="save_status" class="px-3 py-2 rounded bg-slate-800 text-white">ذخیره وضعیت</button>
  </div>
  <hr/>
  <div class="grid gap-2">
    <div class="font-semibold">سفارش فعال</div>
    {% if not order %}
      <div class="grid md:grid-cols-3 gap-2">
        <input class="border rounded p-2" name="customer_name" placeholder="نام مشتری (اختیاری)">
        <div class="md:col-span-2 flex items-center">
          <button name="_op" value="open_order" class="px-3 py-2 rounded bg-emerald-600 text-white">ایجاد سفارش</button>
        </div>
      </div>
    {% else %}
      <div class="flex items-center gap-2 text-sm">
        <div>کد سفارش: #{{ order['id'] }}</div>
        <div class="text-slate-500">از {{ order['opened_at'] }}</div>
      </div>
      <div class="flex items-center gap-2">
        <label class="text-sm">نام مشتری:</label>
        <input class="border rounded p-2 flex-1" name="customer_name" value="{{ order['customer_name'] or '' }}" placeholder="نام مشتری">
        <button name="_op" value="save_customer" class="px-3 py-2 rounded bg-slate-800 text-white">ذخیره نام</button>
      </div>
      <div class="grid gap-1">
        {% for it in items %}
          <div class="flex items-center gap-2 border rounded p-2">
            <div class="flex-1">{{ it['name'] }} × {{ it['qty'] }}</div>
            <div class="w-32 text-end">{{ (it['price'] * it['qty']) | rial }} <span class="text-slate-400 text-xs">ریال</span></div>
            <button name="_op" value="inc:{{it['id']}}" class="px-2 rounded bg-slate-100">+1</button>
            <button name="_op" value="dec:{{it['id']}}" class="px-2 rounded bg-slate-100">-1</button>
            <button name="_op" value="del:{{it['id']}}" class="px-2 rounded bg-rose-100">حذف</button>
          </div>
        {% else %}
          <div class="text-sm text-slate-500">آیتمی اضافه نشده است.</div>
        {% endfor %}
      </div>
      <div class="flex items-center justify-between font-semibold">
        <div>جمع جزء</div>
        <div>{{ subtotal | rial }} <span class="text-slate-400 text-xs">ریال</span></div>
      </div>
      <div class="grid md:grid-cols-3 gap-2">
        <select name="menu_id" class="border rounded p-2">
          {% for m in menu %}
            <option value="{{m['id']}}">{{ m['name'] }} — {{ m['price'] | rial }} ریال</option>
          {% endfor %}
        </select>
        <input class="border rounded p-2" type="number" name="qty" value="1" min="1" />
        <button name="_op" value="add_item" class="px-3 py-2 rounded bg-emerald-600 text-white">افزودن به میز</button>
      </div>
      <div class="text-xs">
        <button type="button" class="mt-1 px-2 py-1 rounded bg-slate-100"
                hx-get="{{ url_for('menu_manage') }}" hx-target="#dlg" hx-swap="innerHTML">
          مدیریت منو
        </button>
      </div>
      <details class="p-2 bg-slate-50 rounded" {% if show_checkout %}open{% endif %}>
        <summary class="cursor-pointer">تسویه / فاکتور</summary>
        <div class="grid md:grid-cols-4 gap-2 mt-2">
          <label class="text-sm">تخفیف (ریال)<input class="border rounded p-2 w-full" type="number" step="1" name="discount" value="0"></label>
          <label class="text-sm">مالیات (ریال)<input class="border rounded p-2 w-full" type="number" step="1" name="tax" value="0"></label>
          <label class="text-sm">روش پرداخت
            <select class="border rounded p-2 w-full" name="payment_method">
              <option>Cash</option><option>Card</option><option>Bizum</option>
            </select>
          </label>
          <div class="flex items-end">
            <button name="_op" value="checkout" class="px-3 py-2 rounded bg-indigo-600 text-white w-full">تسویه و صدور فاکتور</button>
          </div>
        </div>
      </details>
    {% endif %}
  </div>
</form>
"""

MENU_PAGE = r"""
{% extends 'base.html' %}
{% block content %}
  <div class="flex items-center gap-2 mb-2">
    <div class="text-xl font-bold">منو</div>
    <form class="ml-auto flex gap-2" method="post" action="{{ url_for('menu_page') }}">
      <input class="border rounded p-2" name="name" placeholder="نام غذا" required>
      <input class="border rounded p-2" name="price" placeholder="قیمت (ریال)" type="number" step="1" required>
      <input class="border rounded p-2" name="category" placeholder="دسته">
      <button class="px-3 py-2 rounded bg-emerald-600 text-white">افزودن</button>
    </form>
  </div>
  <div class="grid md:grid-cols-2 gap-2">
    {% for m in menu %}
      <div class="p-3 rounded-xl bg-white border flex items-center gap-2">
        <div class="font-semibold flex-1">{{ m['name'] }} <span class="text-slate-400 text-sm">{{ m['category'] or '' }}</span></div>
        <div class="w-32 text-end">{{ m['price'] | rial }} <span class="text-slate-400 text-xs">ریال</span></div>
        <form method="post" action="{{ url_for('menu_delete', id=m['id']) }}">
          <button class="px-2 py-1 rounded bg-rose-100">حذف</button>
        </form>
      </div>
    {% endfor %}
  </div>
{% endblock %}
"""

REPORTS = r"""
{% extends 'base.html' %}
{% block content %}
  <div class="text-xl font-bold mb-2">گزارشات</div>
  <div class="grid md:grid-cols-3 gap-3">
    {% for name, data in boxes %}
      <div class="p-4 bg-white rounded-2xl border">
        <div class="font-semibold mb-1">{{ name }}</div>
        <div class="text-2xl">{{ data['total'] | rial }} <span class="text-slate-400 text-base">ریال</span></div>
        <div class="text-sm text-slate-500">تعداد فاکتورها: {{ data['count'] }}</div>
      </div>
    {% endfor %}
  </div>
  <div class="mt-4 p-4 bg-white rounded-2xl border">
    <div class="font-semibold mb-2">پرفروش‌ها (۳۰ روز)</div>
    <div class="grid md:grid-cols-2 gap-2">
      {% for r in top_items %}
        <div class="flex items-center justify-between border rounded p-2">
          <div>{{ r['name'] }}</div>
          <div>× {{ r['qty'] }}</div>
          <div>{{ r['revenue'] | rial }} <span class="text-slate-400 text-xs">ریال</span></div>
        </div>
      {% else %}
        <div class="text-sm text-slate-500">داده‌ای نیست.</div>
      {% endfor %}
    </div>
  </div>
  <div class="mt-4 p-4 bg-white rounded-2xl border">
    <div class="font-semibold mb-2">آخرین فاکتورها</div>
    <div class="grid gap-2">
      {% for inv in last_invoices %}
        <div class="flex items-center gap-2 border rounded p-2">
          <div class="flex-1 text-sm">
            <div class="font-semibold">#{{ inv['id'] }} — {{ inv['table_name'] }}{% if inv['customer_name'] %} · {{ inv['customer_name'] }}{% endif %}</div>
            <div class="text-slate-500">{{ inv['closed_at'] }}</div>
          </div>
          <div class="w-32 text-end">{{ inv['total'] | rial }} <span class="text-slate-400 text-xs">ریال</span></div>
          <a class="px-3 py-1 rounded bg-indigo-600 text-white" href="{{ url_for('invoice_view', invoice_id=inv['id']) }}" target="_blank">چاپ مجدد</a>
        </div>
      {% else %}
        <div class="text-sm text-slate-500">فاکتوری ثبت نشده است.</div>
      {% endfor %}
    </div>
  </div>
{% endblock %}
"""

LAYOUT = r"""
{% extends 'base.html' %}
{% block content %}
  <div class="flex items-center gap-2 mb-2">
    <div class="text-xl font-bold">چیدمان سالن</div>
    <span class="text-sm text-slate-500">روی نقشه کلیک کنید تا میز اضافه شود؛ جابجایی با کشیدن؛ تغییر اندازه با Ctrl+اسکرول یا دستگیره گوشه.</span>
    <form class="ml-auto" method="post" action="{{ url_for('layout_add_cashier') }}">
      <button class="px-3 py-2 rounded bg-amber-800 text-white">➕ افزودن صندوق</button>
    </form>
    <button class="px-3 py-2 rounded bg-emerald-600 text-white"
            hx-get="{{ url_for('menu_manage') }}" hx-target="#dlg" hx-swap="innerHTML">
      مدیریت منو
    </button>
  </div>
  <div id="toast" class="hidden fixed top-16 left-1/2 -translate-x-1/2 bg-black text-white text-sm px-3 py-1 rounded">ذخیره شد</div>
  <div id="floor" class="floor" 
       onclick="addTable(event)"
       onwheel="maybeResize(event)"
       ondragover="event.preventDefault();"
       hx-post="{{ url_for('layout_save_positions') }}" hx-trigger="savePositions from:body" hx-include=".tblpos,.tblsize" hx-target="#toast" hx-swap="outerHTML">
    {% for t in tables %}
      {% set cls = 'kind-cash' if t['kind']=='cash' else 'status-' + t['status'] %}
      <button draggable="true" ondragstart="dragStart(event)" ondragend="dragEnd(event)"
              data-id="{{t['id']}}" data-kind="{{t['kind']}}" data-size="{{t['size_px']}}" data-capacity="{{t['capacity']}}" data-label="{{t['label'] or ''}}" data-status="{{t['status']}}"
              class="table-dot {{cls}}"
              style="left: {{t['x']}}%; top: {{t['y']}}%; width: {{t['size_px']}}px; height: {{t['size_px']}}px;">
        <div class="flex flex-col items-center leading-tight">
          <div>{{ 'صندوق' if t['kind']=='cash' else t['name'] }}</div>
          {% if t['label'] %}
            <div class="text-[10px] font-normal opacity-90 mt-0.5">{{ t['label'] }} · ظرفیت {{ t['capacity'] }} نفر</div>
          {% else %}
            <div class="text-[10px] font-normal opacity-70 mt-0.5">ظرفیت {{ t['capacity'] }} نفر</div>
          {% endif %}
        </div>
        {% if t['kind']=='cash' %}<span class="chair"></span>{% endif %}
        <span class="resize-h" title="Resize"></span>
      </button>
      <input type="hidden" class="tblpos" name="pos_{{t['id']}}" value="{{t['x']}},{{t['y']}}" />
      <input type="hidden" class="tblsize" name="size_{{t['id']}}" value="{{t['size_px']}}" />
    {% endfor %}
  </div>
  <form class="mt-3 flex gap-2" method="post" action="{{ url_for('layout_delete') }}">
    <input class="border rounded p-2" name="id" placeholder="ID میز برای حذف" type="number" min="1" required>
    <button class="px-3 py-2 rounded bg-rose-600 text-white">حذف میز</button>
  </form>
  <script>
    const floor = document.getElementById('floor');
    function pct(x, total){ return Math.min(99, Math.max(1, (x/total)*100)); }
    function addTable(e){
      if(e.target !== floor) return;
      const rect = floor.getBoundingClientRect();
      const x = pct(e.clientX - rect.left, rect.width).toFixed(2);
      const y = pct(e.clientY - rect.top, rect.height).toFixed(2);
      fetch("{{ url_for('layout_add') }}", {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({x, y})})
        .then(()=>location.reload());
    }
    let dragEl=null; let startX=0, startY=0;
    function dragStart(e){ dragEl = e.target; startX=e.clientX; startY=e.clientY; }
    function dragEnd(e){
      if(!dragEl) return; const rect = floor.getBoundingClientRect();
      const style = window.getComputedStyle(dragEl);
      const left = parseFloat(style.left); const top = parseFloat(style.top);
      const dx = e.clientX - startX; const dy = e.clientY - startY;
      const x = pct(left + dx, rect.width).toFixed(2);
      const y = pct(top + dy, rect.height).toFixed(2);
      dragEl.style.left = x + '%'; dragEl.style.top = y + '%';
      const id = dragEl.dataset.id; document.querySelector(`input[name="pos_${id}"]`).value = `${x},${y}`;
      document.body.dispatchEvent(new Event('savePositions'));
      dragEl=null;
    }
    function maybeResize(e){
      if(!e.ctrlKey) return;
      const target = e.target.closest('.table-dot');
      if(!target) return;
      e.preventDefault();
      let size = parseInt(target.dataset.size||'64');
      size += (e.deltaY < 0 ? 6 : -6);
      size = Math.max(40, Math.min(180, size));
      target.dataset.size = size;
      target.style.width = size + 'px';
      target.style.height = size + 'px';
      const id = target.dataset.id; const inp = document.querySelector(`input[name="size_${id}"]`);
      if(inp){ inp.value = String(size); document.body.dispatchEvent(new Event('savePositions')); }
    }
    // Resize via handle
    let rzEl=null, rzStart=0, rzX=0, rzY=0;
    document.addEventListener('mousedown', (e)=>{
      const h = e.target.closest('.resize-h'); if(!h) return;
      rzEl = h.closest('.table-dot'); rzStart = parseInt(rzEl.dataset.size||'64'); rzX=e.clientX; rzY=e.clientY;
      e.preventDefault();
    });
    document.addEventListener('mousemove', (e)=>{
      if(!rzEl) return;
      const delta = Math.max(e.clientX - rzX, e.clientY - rzY);
      let size = Math.max(40, Math.min(180, rzStart + delta));
      rzEl.dataset.size = size;
      rzEl.style.width = size + 'px';
      rzEl.style.height = size + 'px';
    });
    document.addEventListener('mouseup', ()=>{
      if(!rzEl) return;
      const id = rzEl.dataset.id; const inp = document.querySelector(`input[name="size_${id}"]`);
      if(inp){ inp.value = String(parseInt(rzEl.dataset.size||'64')); document.body.dispatchEvent(new Event('savePositions')); }
      rzEl=null;
    });
  </script>
{% endblock %}
"""

LOGIN_TPL = r"""
<!doctype html>
<html lang=fa dir=rtl>
<head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ورود</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="min-h-screen bg-slate-50 flex items-center justify-center p-4">
  <form method="post" class="bg-white p-6 rounded-2xl shadow max-w-sm w-full grid gap-3">
    <div class="text-xl font-bold">ورود به سیستم</div>
    {% if error %}<div class="text-rose-600 text-sm">{{ error }}</div>{% endif %}
    <input name="username" class="border rounded p-2" placeholder="نام کاربری" required>
    <input name="password" type="password" class="border rounded p-2" placeholder="کلمه عبور" required>
    <button class="px-3 py-2 rounded bg-emerald-600 text-white">ورود</button>
    <div class="text-xs text-slate-500">کاربر اولیه: <b>admin</b> / گذرواژه: <b>admin123</b> — پس از ورود تغییر دهید.</div>
  </form>
</body>
</html>
"""

USERS_TPL = r"""
{% extends 'base.html' %}
{% block content %}
  <div class="flex items-center gap-2 mb-3">
    <div class="text-xl font-bold">کاربران</div>
    <span class="text-sm text-slate-500">نقش‌ها: ارشد (admin) و صندوق (cashier)</span>
  </div>
  <form method="post" action="{{ url_for('users') }}" class="p-4 bg-white rounded-2xl border grid md:grid-cols-4 gap-2 mb-4">
    <input name="username" class="border rounded p-2" placeholder="نام کاربری" required>
    <input name="password" type="password" class="border rounded p-2" placeholder="کلمه عبور" required>
    <select name="role" class="border rounded p-2">
      <option value="cashier">صندوق</option>
      <option value="admin">ارشد</option>
    </select>
    <button class="px-3 py-2 rounded bg-emerald-600 text-white">ایجاد کاربر</button>
  </form>
  <div class="grid gap-2">
    {% for u in users %}
      <div class="p-3 bg-white rounded-xl border flex items-center gap-2">
        <div class="flex-1">{{ u['username'] }} · {{ 'ارشد' if u['role']=='admin' else 'صندوق' }}</div>
        <form method="post" action="{{ url_for('user_delete', id=u['id']) }}" onsubmit="return confirm('حذف کاربر؟')">
          <button class="px-2 py-1 rounded bg-rose-100">حذف</button>
        </form>
      </div>
    {% endfor %}
  </div>
{% endblock %}
"""

# ------- Menu management modal (used in hall & layout) -------
MENU_MANAGE = r"""
<form class="bg-white rounded-2xl p-4 grid gap-3"
      hx-post="{{ url_for('menu_add') }}" hx-target="#dlg" hx-swap="innerHTML">
  <div class="flex items-center gap-2">
    <div class="text-lg font-bold">مدیریت منو</div>
    <span class="ml-auto"></span>
    <button type="button" class="px-3 py-1 rounded bg-slate-100" onclick="closeDialog()">بستن</button>
  </div>

  {% if error %}
    <div class="text-rose-600 text-sm">{{ error }}</div>
  {% endif %}

  <div class="p-3 rounded-xl bg-slate-50 grid md:grid-cols-4 gap-2">
    <input class="border rounded p-2" name="name" placeholder="نام غذا" required>
    <input class="border rounded p-2" name="price" placeholder="قیمت (ریال)" type="number" step="1" min="0" required>
    <input class="border rounded p-2" name="category" placeholder="دسته (اختیاری)">
    <button class="px-3 py-2 rounded bg-emerald-600 text-white">افزودن</button>
  </div>

  <div class="grid gap-2">
    {% for m in menu %}
      <div class="p-3 bg-white rounded-xl border grid md:grid-cols-5 gap-2 items-center">
        <form class="contents"
              hx-post="{{ url_for('menu_update', id=m['id']) }}"
              hx-target="#dlg" hx-swap="innerHTML">
          <input class="border rounded p-2" name="name" value="{{ m['name'] }}" required>
          <input class="border rounded p-2" name="price" value="{{ m['price'] }}" type="number" step="1" min="0" required>
          <input class="border rounded p-2" name="category" value="{{ m['category'] or '' }}">
          <button class="px-3 py-2 rounded bg-slate-800 text-white">ذخیره</button>
        </form>
        <form hx-post="{{ url_for('menu_delete', id=m['id']) }}"
              hx-target="#dlg" hx-swap="innerHTML"
              onsubmit="return confirm('این مورد حذف شود؟')">
          <button class="px-3 py-2 rounded bg-rose-100" type="submit">حذف</button>
        </form>
      </div>
    {% else %}
      <div class="text-sm text-slate-500">هنوز آیتمی در منو ثبت نشده است.</div>
    {% endfor %}
  </div>
</form>
"""

# ---------------------- Jinja Loader ----------------------
app.jinja_loader = DictLoader({
    'base.html': BASE,
    'index.html': INDEX,
    'table_modal.html': TABLE_MODAL,
    'menu.html': MENU_PAGE,
    'reports.html': REPORTS,
    'layout.html': LAYOUT,
    'floor.html': FLOOR,
})

# ---------------------- Auth bootstrap ----------------------
@app.before_request
def _ensure_db():
    if not getattr(g, "_db_inited", False):
        init_db()
        g._db_inited = True
    # user
    g.user = None
    uid = session.get('uid')
    if uid:
        with get_conn() as conn:
            u = conn.execute("SELECT id, username, role FROM users WHERE id=?", (uid,)).fetchone()
            if u:
                g.user = dict(u)
    # protect (login required)
    open_endpoints = {'login', 'logout', 'health', 'static', 'sse_events'}
    if (request.endpoint not in open_endpoints) and (g.user is None):
        return redirect(url_for('login', next=request.path))

# ---------------------- Routes ----------------------
# Auth
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        with get_conn() as conn:
            u = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if u and check_password_hash(u['password_hash'], password):
            session['uid'] = u['id']
            session['username'] = u['username']
            session['role'] = u['role']
            nxt = request.args.get('next') or url_for('index')
            return redirect(nxt)
        else:
            return render_template_string(LOGIN_TPL, error='نام کاربری یا کلمه عبور نادرست است')
    return render_template_string(LOGIN_TPL, error=None)

@app.get('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Users (admin)
@app.route('/users', methods=['GET','POST'])
def users():
    if session.get('role') != 'admin':
        abort(403)
    with get_conn() as conn:
        if request.method == 'POST':
            username = request.form['username'].strip()
            password = request.form['password']
            role = request.form.get('role','cashier')
            conn.execute("INSERT INTO users(username, password_hash, role) VALUES(?,?,?)",
                         (username, generate_password_hash(password), role))
            return redirect(url_for('users'))
        users = conn.execute("SELECT id, username, role FROM users ORDER BY id").fetchall()
    return render_template_string(USERS_TPL, users=users, title='کاربران', app_title=APP_TITLE, page='users')

@app.post('/users/<int:id>/delete')
def user_delete(id):
    if session.get('role') != 'admin':
        abort(403)
    with get_conn() as conn:
        role = conn.execute("SELECT role FROM users WHERE id=?", (id,)).fetchone()
        if not role:
            return redirect(url_for('users'))
        if role['role']=='admin':
            cnt = conn.execute("SELECT COUNT(*) FROM users WHERE role='admin'").fetchone()[0]
            if cnt <= 1:
                return redirect(url_for('users'))
        conn.execute("DELETE FROM users WHERE id=?", (id,))
    return redirect(url_for('users'))

# Hall
@app.get('/')
def index():
    with get_conn() as conn:
        tables = conn.execute("""
            SELECT t.*, (
                SELECT customer_name FROM orders o
                WHERE o.table_id = t.id AND o.status='open'
                ORDER BY o.id DESC LIMIT 1
            ) AS cust
            FROM tables t
        """).fetchall()
    return render_template_string(
        INDEX,
        title="سالن",
        tables=tables,
        app_title=APP_TITLE,
        page='hall',
        jalali_today=today_jalali_str(),   # 👈 اضافه شد
    )

@app.get('/hall/floor')
def hall_floor():
    with get_conn() as conn:
        tables = conn.execute("""
            SELECT t.*, (
                SELECT customer_name FROM orders o
                WHERE o.table_id = t.id AND o.status='open'
                ORDER BY o.id DESC LIMIT 1
            ) AS cust
            FROM tables t
        """).fetchall()
    return render_template_string(FLOOR, tables=tables)

# Table modal & actions
@app.get('/table/<int:table_id>/modal')
def table_modal(table_id):
    show_checkout = (request.args.get('show') == 'checkout')
    with get_conn() as conn:
        t = conn.execute("SELECT * FROM tables WHERE id=?", (table_id,)).fetchone()
        if not t or t['kind']=='cash': abort(404)
        order = conn.execute(
            "SELECT * FROM orders WHERE table_id=? AND status='open' ORDER BY id DESC LIMIT 1",
            (table_id,),
        ).fetchone()
        items = []
        subtotal = 0
        if order:
            items = conn.execute("""
                SELECT oi.id, oi.qty, oi.price, m.name
                FROM order_items oi JOIN menu m ON m.id = oi.menu_id
                WHERE oi.order_id=? ORDER BY oi.id
            """, (order['id'],)).fetchall()
            subtotal = sum([row['qty']*row['price'] for row in items])
        menu = conn.execute("SELECT * FROM menu ORDER BY category, name").fetchall()
    return render_template_string(TABLE_MODAL, table=t, order=order, items=items, subtotal=subtotal, menu=menu, show_checkout=show_checkout)

@app.post('/table/<int:table_id>/action')
def table_action(table_id):
    op = request.form.get('_op')
    with get_conn() as conn:
        t = conn.execute("SELECT * FROM tables WHERE id=?", (table_id,)).fetchone()
        if not t or t['kind']=='cash': abort(404)
        if op == 'save_status':
            status = request.form.get('status', 'free')
            conn.execute("UPDATE tables SET status=? WHERE id=?", (status, table_id))
            notify_change()
            return table_modal(table_id)
        if op == 'open_order':
            order_id = ensure_open_order(table_id)
            cust = (request.form.get('customer_name') or '').strip()
            if cust:
                conn.execute("UPDATE orders SET customer_name=? WHERE id=?", (cust, order_id))
            conn.execute("UPDATE tables SET status='occupied' WHERE id=?", (table_id,))
            notify_change()
            return table_modal(table_id)
        order = conn.execute(
            "SELECT * FROM orders WHERE table_id=? AND status='open' ORDER BY id DESC LIMIT 1",
            (table_id,),
        ).fetchone()
        if not order:
            return table_modal(table_id)
        if op == 'save_customer':
            cust = (request.form.get('customer_name') or '').strip()
            conn.execute("UPDATE orders SET customer_name=? WHERE id=?", (cust, order['id']))
            notify_change()
            return table_modal(table_id)
        if op == 'add_item':
            menu_id = int(request.form.get('menu_id'))
            qty = max(1, int(request.form.get('qty', '1')))
            m = conn.execute("SELECT * FROM menu WHERE id=?", (menu_id,)).fetchone()
            conn.execute("INSERT INTO order_items(order_id, menu_id, qty, price) VALUES(?,?,?,?)", (order['id'], menu_id, qty, m['price']))
            notify_change()
            return table_modal(table_id)
        if op and op.startswith('inc:'):
            oi = int(op.split(':',1)[1])
            conn.execute("UPDATE order_items SET qty=qty+1 WHERE id=?", (oi,))
            notify_change()
            return table_modal(table_id)
        if op and op.startswith('dec:'):
            oi = int(op.split(':',1)[1])
            row = conn.execute("SELECT qty FROM order_items WHERE id=?", (oi,)).fetchone()
            if row and row['qty']<=1:
                conn.execute("DELETE FROM order_items WHERE id=?", (oi,))
            else:
                conn.execute("UPDATE order_items SET qty=qty-1 WHERE id=?", (oi,))
            notify_change()
            return table_modal(table_id)
        if op and op.startswith('del:'):
            oi = int(op.split(':',1)[1])
            conn.execute("DELETE FROM order_items WHERE id=?", (oi,))
            notify_change()
            return table_modal(table_id)
        if op == 'checkout':
            items = conn.execute("SELECT qty, price FROM order_items WHERE order_id=?", (order['id'],)).fetchall()
            subtotal = sum([r['qty']*r['price'] for r in items])
            discount = int(float(request.form.get('discount', '0') or 0))
            tax = int(float(request.form.get('tax', '0') or 0))
            total = max(0, subtotal - discount + tax)
            pay = request.form.get('payment_method', 'Cash')
            conn.execute("UPDATE orders SET status='closed' WHERE id=?", (order['id'],))
            cust = (order['customer_name'] or '')
            c = conn.cursor()
            c.execute(
                "INSERT INTO invoices(order_id, closed_at, subtotal, discount, tax, total, payment_method, customer_name) VALUES(?,?,?,?,?,?,?,?)",
                (order['id'], now_iso(), subtotal, discount, tax, total, pay, cust),
            )
            inv_id = c.lastrowid
            conn.execute("UPDATE tables SET status='free' WHERE id=?", (table_id,))
            notify_change()
            html = f"""
            <div class='p-6'>
              <div class='text-lg font-bold mb-2'>فاکتور صادر شد</div>
              <div class='mb-2'>مبلغ کل: {fmt_rial(total)} <span class='text-slate-400 text-xs'>ریال</span></div>
              <a class='px-4 py-2 rounded bg-indigo-600 text-white' href='{url_for('invoice_view', invoice_id=inv_id)}' target='_blank'>نمایش و چاپ فاکتور</a>
              <button class='ml-2 px-3 py-2 rounded bg-slate-100' onclick='closeDialog()'>بستن</button>
            </div>
            """
            return render_template_string(html)
    return table_modal(table_id)

# Menu page
@app.route('/menu', methods=['GET','POST'])
def menu_page():
    with get_conn() as conn:
        if request.method == 'POST':
            name = request.form['name'].strip()
            price = int(float(request.form['price']))
            cat = request.form.get('category')
            conn.execute("INSERT INTO menu(name, price, category) VALUES(?,?,?)", (name, price, cat))
            notify_change()
            return redirect(url_for('menu_page'))
        menu = conn.execute("SELECT * FROM menu ORDER BY category, name").fetchall()
    return render_template_string(MENU_PAGE, menu=menu, title='منو', app_title=APP_TITLE, page='menu')

# --- Menu management modal routes (from hall & layout) ---
def _render_menu_manage(error=None):
    with get_conn() as conn:
        menu = conn.execute("SELECT * FROM menu ORDER BY category, name").fetchall()
    return render_template_string(MENU_MANAGE, menu=menu, error=error)

@app.get('/menu/manage')
def menu_manage():
    return _render_menu_manage()

@app.post('/menu/add')
def menu_add():
    name = (request.form.get('name') or '').strip()
    price = request.form.get('price') or '0'
    cat = (request.form.get('category') or '').strip()
    try:
        price = int(float(price))
    except:
        return _render_menu_manage("قیمت نامعتبر است.")
    if not name:
        return _render_menu_manage("نام غذا الزامی است.")
    with get_conn() as conn:
        conn.execute("INSERT INTO menu(name, price, category) VALUES(?,?,?)", (name, price, cat))
    notify_change()
    return _render_menu_manage()

@app.post('/menu/<int:id>/update')
def menu_update(id):
    name = (request.form.get('name') or '').strip()
    price = request.form.get('price') or '0'
    cat = (request.form.get('category') or '').strip()
    try:
        price = int(float(price))
    except:
        return _render_menu_manage("قیمت نامعتبر است.")
    if not name:
        return _render_menu_manage("نام غذا الزامی است.")
    with get_conn() as conn:
        conn.execute("UPDATE menu SET name=?, price=?, category=? WHERE id=?", (name, price, cat, id))
    notify_change()
    return _render_menu_manage()

@app.post('/menu/<int:id>/delete')
def menu_delete(id):
    is_htmx = request.headers.get('HX-Request') == 'true'
    with get_conn() as conn:
        used = conn.execute("""
            SELECT COUNT(*) AS c
            FROM order_items oi
            JOIN orders o ON o.id = oi.order_id
            WHERE oi.menu_id=? AND o.status='open'
        """, (id,)).fetchone()['c']
        if used:
            if is_htmx:
                return _render_menu_manage("این آیتم در سفارشِ باز استفاده شده و قابل حذف نیست.")
            return redirect(url_for('menu_page'))
        conn.execute("DELETE FROM menu WHERE id=?", (id,))
    notify_change()
    if is_htmx:
        return _render_menu_manage()
    return redirect(url_for('menu_page'))

# Reports & invoice
@app.get('/reports')
def reports():
    now = datetime.now()
    start_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_week = start_day - timedelta(days=start_day.weekday())
    start_month = start_day.replace(day=1)

    def sum_from(start: datetime):
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT COUNT(*) as cnt, COALESCE(SUM(total),0) as tot FROM invoices WHERE closed_at >= ?",
                (start.isoformat(),),
            ).fetchone()
            return {"count": rows['cnt'], "total": rows['tot']}

    boxes = [
        ("امروز", sum_from(start_day)),
        ("این هفته", sum_from(start_week)),
        ("این ماه", sum_from(start_month)),
    ]

    last30 = (now - timedelta(days=30)).isoformat()
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT m.name, SUM(oi.qty) as qty, SUM(oi.qty*oi.price) as revenue
            FROM order_items oi JOIN orders o ON o.id = oi.order_id
            JOIN menu m ON m.id = oi.menu_id
            JOIN invoices inv ON inv.order_id = o.id
            WHERE inv.closed_at >= ?
            GROUP BY m.name ORDER BY revenue DESC LIMIT 20
        """, (last30,)).fetchall()
        last_invoices = conn.execute("""
            SELECT inv.id, inv.closed_at, inv.total, inv.payment_method, inv.customer_name,
                   t.name AS table_name
            FROM invoices inv
            JOIN orders o ON o.id = inv.order_id
            JOIN tables t ON t.id = o.table_id
            ORDER BY inv.id DESC LIMIT 20
        """).fetchall()
    return render_template_string(REPORTS, boxes=boxes, top_items=rows, last_invoices=last_invoices, title='گزارشات', app_title=APP_TITLE, page='reports')

@app.get('/invoice/<int:invoice_id>')
def invoice_view(invoice_id):
    INVOICE_TPL = r"""
<!doctype html>
<html lang=fa dir=rtl>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>فاکتور #{{ inv['id'] }}</title>
  <link rel="stylesheet" href="https://cdn.tailwindcss.com">
  <style>@media print { .noprint{display:none} body{background:white} }</style>
</head>
<body class="bg-slate-50 p-4">
  <div class="max-w-xl mx-auto bg-white p-6 rounded-2xl border">
    <div class="flex items-center justify-between mb-3">
      <div>
        <div class="text-xl font-bold">{{ app_title }}</div>
        <div class="text-slate-500 text-sm">فاکتور فروش</div>
      </div>
      <div class="text-sm text-slate-600">
        <div>شماره: #{{ inv['id'] }}</div>
        <div>تاریخ: {{ inv['closed_at'] }}</div>
      </div>
    </div>
    <div class="grid grid-cols-2 gap-3 text-sm py-2 border-y">
      <div>میز: {{ table['name'] }}</div>
      <div>نام مشتری: {{ inv['customer_name'] or '-' }}</div>
    </div>
    <div class="mt-3">
      <table class="w-full text-sm">
        <thead>
          <tr class="text-right border-b">
            <th class="py-1">ردیف</th>
            <th class="py-1">کالا</th>
            <th class="py-1">تعداد</th>
            <th class="py-1">فی (ریال)</th>
            <th class="py-1">مبلغ (ریال)</th>
          </tr>
        </thead>
        <tbody>
          {% for it in items %}
          <tr class="border-b">
            <td class="py-1">{{ loop.index }}</td>
            <td class="py-1">{{ it['name'] }}</td>
            <td class="py-1">{{ it['qty'] }}</td>
            <td class="py-1">{{ it['price'] | rial }}</td>
            <td class="py-1">{{ (it['qty']*it['price']) | rial }}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
    <div class="mt-3 grid gap-1 text-sm">
      <div class="flex justify-between"><span>جمع جزء</span><span>{{ inv['subtotal'] | rial }} ریال</span></div>
      <div class="flex justify_between"><span>تخفیف</span><span>{{ inv['discount'] | rial }} ریال</span></div>
      <div class="flex justify-between"><span>مالیات</span><span>{{ inv['tax'] | rial }} ریال</span></div>
      <div class="flex justify-between text-lg font-bold"><span>مبلغ کل</span><span>{{ inv['total'] | rial }} ریال</span></div>
      <div class="text-slate-500">روش پرداخت: {{ inv['payment_method'] }}</div>
    </div>
    <div class="mt-4 noprint">
      <button onclick="window.print()" class="px-4 py-2 rounded bg-indigo-600 text-white">چاپ</button>
    </div>
  </div>
</body>
</html>
"""
    with get_conn() as conn:
        inv = conn.execute("SELECT * FROM invoices WHERE id=?", (invoice_id,)).fetchone()
        if not inv:
            abort(404)
        order = conn.execute("SELECT * FROM orders WHERE id=?", (inv['order_id'],)).fetchone()
        table = conn.execute("SELECT * FROM tables WHERE id=?", (order['table_id'],)).fetchone()
        items = conn.execute("""
            SELECT m.name, oi.qty, oi.price
            FROM order_items oi JOIN menu m ON m.id = oi.menu_id
            WHERE oi.order_id=? ORDER BY oi.id
        """, (order['id'],)).fetchall()
    return render_template_string(INVOICE_TPL, inv=inv, table=table, items=items, app_title=APP_TITLE)

# Layout (admin only)
@app.get('/layout')
def layout_editor():
    if session.get('role') != 'admin':
        abort(403)
    with get_conn() as conn:
        tables = conn.execute("SELECT * FROM tables ORDER BY id").fetchall()
    return render_template_string(LAYOUT, title='چیدمان', tables=tables, app_title=APP_TITLE, page='layout')

@app.post('/layout/add')
def layout_add():
    if session.get('role') != 'admin':
        return jsonify(ok=False, message='فقط کاربر ارشد مجاز است'), 403
    data = request.get_json(force=True)
    x = float(data.get('x', 10)); y = float(data.get('y', 10))
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO tables(name, x, y, capacity, status, size_px, kind) VALUES(?,?,?,?,?,?,?)",
            (f"T{int(datetime.now().timestamp())%10000}", x, y, 2, 'free', 64, 'table'),
        )
    notify_change()
    return jsonify(ok=True)

@app.post('/layout/add_cashier')
def layout_add_cashier():
    if session.get('role') != 'admin':
        abort(403)
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO tables(name, x, y, capacity, status, size_px, kind) VALUES(?,?,?,?,?,?,?)",
            ('صندوق', 5.0, 85.0, 1, 'free', 80, 'cash'),
        )
    notify_change()
    return redirect(url_for('layout_editor'))

@app.post('/layout/delete')
def layout_delete():
    if session.get('role') != 'admin':
        abort(403)
    _id = int(request.form['id'])
    with get_conn() as conn:
        t = conn.execute("SELECT status FROM tables WHERE id=?", (_id,)).fetchone()
        if t and t['status']=='occupied':
            return redirect(url_for('layout_editor'))
        row = conn.execute("SELECT COUNT(*) AS c FROM orders WHERE table_id=? AND status='open'", (_id,)).fetchone()
        if row and row['c']>0:
            return redirect(url_for('layout_editor'))
        conn.execute("DELETE FROM tables WHERE id=?", (_id,))
    notify_change()
    return redirect(url_for('layout_editor'))

@app.post('/layout/remove')
def layout_remove():
    if session.get('role') != 'admin':
        return jsonify(ok=False, message='فقط کاربر ارشد مجاز است'), 403
    data = request.get_json(force=True)
    _id = int(data.get('id'))
    with get_conn() as conn:
        t = conn.execute("SELECT status FROM tables WHERE id=?", (_id,)).fetchone()
        if not t:
            return jsonify(ok=False, message='میز یافت نشد'), 404
        if t['status'] == 'occupied':
            return jsonify(ok=False, message='میز اشغال‌شده قابل حذف نیست.'), 400
        row = conn.execute("SELECT COUNT(*) AS c FROM orders WHERE table_id=? AND status='open'", (_id,)).fetchone()
        if row and row['c']>0:
            return jsonify(ok=False, message='برای این میز سفارشِ باز وجود دارد.'), 400
        conn.execute("DELETE FROM tables WHERE id=?", (_id,))
    notify_change()
    return jsonify(ok=True)

@app.post('/layout/save')
def layout_save_positions():
    if session.get('role') != 'admin':
        abort(403)
    with get_conn() as conn:
        for k, v in request.form.items():
            if k.startswith('pos_'):
                _id = int(k.split('_',1)[1]); x_str, y_str = v.split(',')
                conn.execute("UPDATE tables SET x=?, y=? WHERE id=?", (float(x_str), float(y_str), _id))
            elif k.startswith('size_'):
                _id = int(k.split('_',1)[1])
                conn.execute("UPDATE tables SET size_px=? WHERE id=?", (int(v), _id))
    notify_change()
    html = '<div id="toast" class="fixed top-16 left-1/2 -translate-x-1/2 bg-black text-white text-sm px-3 py-1 rounded">ذخیره شد</div>'
    resp = make_response(html)
    return resp

# layout helpers (admin)
@app.post('/layout/set_status')
def layout_set_status():
    if session.get('role') != 'admin':
        return jsonify(ok=False, message='فقط کاربر ارشد مجاز است'), 403
    data = request.get_json(force=True)
    _id = int(data.get('id'))
    status = (data.get('status') or 'free').strip()
    if status not in ('free','reserved','occupied'):
        return jsonify(ok=False, message='وضعیت نامعتبر است'), 400
    with get_conn() as conn:
        conn.execute("UPDATE tables SET status=? WHERE id=?", (status, _id))
    notify_change()
    return jsonify(ok=True)

@app.post('/layout/set_label')
def layout_set_label():
    if session.get('role') != 'admin':
        return jsonify(ok=False, message='فقط کاربر ارشد مجاز است'), 403
    data = request.get_json(force=True)
    _id = int(data.get('id')); label = (data.get('label') or '').strip()
    with get_conn() as conn:
        conn.execute("UPDATE tables SET label=? WHERE id=?", (label, _id))
    notify_change()
    return jsonify(ok=True)

@app.post('/layout/set_capacity')
def layout_set_capacity():
    if session.get('role') != 'admin':
        return jsonify(ok=False, message='فقط کاربر ارشد مجاز است'), 403
    data = request.get_json(force=True)
    _id = int(data.get('id')); capacity = int(data.get('capacity'))
    if capacity < 1 or capacity > 20:
        return jsonify(ok=False, message='عدد ظرفیت نامعتبر است'), 400
    with get_conn() as conn:
        conn.execute("UPDATE tables SET capacity=? WHERE id=?", (capacity, _id))
    notify_change()
    return jsonify(ok=True)

# Health
@app.get('/health')
def health():
    return {"ok": True, "time": now_iso()}

if __name__ == '__main__':
    app.run(debug=True)
    import os
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', '5000'))
    app.run(host=host, port=port, debug=True)