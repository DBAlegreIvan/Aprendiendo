import sqlite3
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk

DB_PATH = Path(__file__).with_name("stock.db")

class Database:
    def __init__(self, path=DB_PATH):
        self.con = sqlite3.connect(path)
        self.con.execute("PRAGMA foreign_keys = ON")
        self.con.executescript(
            """
            CREATE TABLE IF NOT EXISTS productos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo TEXT UNIQUE NOT NULL,
                nombre TEXT NOT NULL,
                precio REAL NOT NULL DEFAULT 0,
                cantidad INTEGER NOT NULL DEFAULT 0,
                minimo INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS movimientos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                producto_id INTEGER NOT NULL
                    REFERENCES productos(id) ON DELETE CASCADE,
                tipo TEXT NOT NULL,
                cantidad INTEGER NOT NULL,
                fecha TEXT NOT NULL
            );
            """
        )
        self.con.commit()

    def listar(self, filtro=""):
        like = f"%{filtro}%"
        return self.con.execute(
            "SELECT id, codigo, nombre, precio, cantidad, minimo FROM productos "
            "WHERE codigo LIKE ? OR nombre LIKE ? ORDER BY nombre",
            (like, like),
        ).fetchall()

    def agregar(self, codigo, nombre, precio, cantidad, minimo):
        cur = self.con.execute(
            "INSERT INTO productos (codigo, nombre, precio, cantidad, minimo) "
            "VALUES (?, ?, ?, ?, ?)",
            (codigo, nombre, precio, cantidad, minimo),
        )
        if cantidad:
            self._movimiento(cur.lastrowid, "ENTRADA", cantidad)
        self.con.commit()

    def editar(self, pid, codigo, nombre, precio, minimo):
        self.con.execute(
            "UPDATE productos SET codigo=?, nombre=?, precio=?, minimo=? WHERE id=?",
            (codigo, nombre, precio, minimo, pid),
        )
        self.con.commit()

    def eliminar(self, pid):
        self.con.execute("DELETE FROM productos WHERE id=?", (pid,))
        self.con.commit()

    def mover(self, pid, tipo, cantidad):
        """Registra una ENTRADA o SALIDA. Devuelve False si no hay stock suficiente."""
        actual = self.con.execute(
            "SELECT cantidad FROM productos WHERE id=?", (pid,)
        ).fetchone()[0]
        if tipo == "SALIDA" and cantidad > actual:
            return False
        delta = cantidad if tipo == "ENTRADA" else -cantidad
        self.con.execute(
            "UPDATE productos SET cantidad = cantidad + ? WHERE id=?", (delta, pid)
        )
        self._movimiento(pid, tipo, cantidad)
        self.con.commit()
        return True

    def _movimiento(self, pid, tipo, cantidad):
        self.con.execute(
            "INSERT INTO movimientos (producto_id, tipo, cantidad, fecha) "
            "VALUES (?, ?, ?, ?)",
            (pid, tipo, cantidad, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )

    def historial(self):
        return self.con.execute(
            "SELECT m.fecha, p.codigo, p.nombre, m.tipo, m.cantidad "
            "FROM movimientos m JOIN productos p ON p.id = m.producto_id "
            "ORDER BY m.id DESC LIMIT 500"
        ).fetchall()

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Control de Stock")
        self.geometry("900x560")
        self.minsize(820, 500)
        self.db = Database()
        self.seleccion = None 

        self.v_codigo = tk.StringVar()
        self.v_nombre = tk.StringVar()
        self.v_precio = tk.StringVar()
        self.v_cantidad = tk.StringVar(value="0")
        self.v_minimo = tk.StringVar(value="0")
        self.v_mov = tk.StringVar(value="1")
        self.v_buscar = tk.StringVar()
        self.v_buscar.trace_add("write", lambda *_: self.refrescar())

        self._crear_formulario()
        self._crear_tabla()
        self._crear_barra_estado()
        self.refrescar()

    def _crear_formulario(self):
        marco = ttk.LabelFrame(self, text="Producto")
        marco.pack(fill="x", padx=10, pady=(10, 5))

        campos = [
            ("Código", self.v_codigo, 12),
            ("Nombre", self.v_nombre, 28),
            ("Precio", self.v_precio, 10),
            ("Cantidad inicial", self.v_cantidad, 10),
            ("Stock mínimo", self.v_minimo, 10),
        ]
        for i, (texto, var, ancho) in enumerate(campos):
            ttk.Label(marco, text=texto).grid(row=0, column=i, sticky="w", padx=6)
            ttk.Entry(marco, textvariable=var, width=ancho).grid(
                row=1, column=i, padx=6, pady=(0, 6)
            )
        self.entry_cantidad = marco.grid_slaves(row=1, column=3)[0]

        botones = ttk.Frame(marco)
        botones.grid(row=2, column=0, columnspan=5, sticky="w", padx=6, pady=(0, 6))
        ttk.Button(botones, text="Agregar", command=self.agregar).pack(side="left")
        ttk.Button(botones, text="Guardar cambios", command=self.guardar).pack(
            side="left", padx=5
        )
        ttk.Button(botones, text="Eliminar", command=self.eliminar).pack(side="left")
        ttk.Button(botones, text="Limpiar", command=self.limpiar).pack(
            side="left", padx=5
        )

        mov = ttk.LabelFrame(self, text="Movimiento de stock (producto seleccionado)")
        mov.pack(fill="x", padx=10, pady=5)
        ttk.Label(mov, text="Cantidad:").pack(side="left", padx=6, pady=6)
        ttk.Entry(mov, textvariable=self.v_mov, width=8).pack(side="left")
        ttk.Button(
            mov, text="➕ Entrada", command=lambda: self.mover("ENTRADA")
        ).pack(side="left", padx=6)
        ttk.Button(
            mov, text="➖ Salida", command=lambda: self.mover("SALIDA")
        ).pack(side="left")
        ttk.Button(mov, text="Ver historial", command=self.ver_historial).pack(
            side="right", padx=6
        )

    def _crear_tabla(self):
        barra = ttk.Frame(self)
        barra.pack(fill="x", padx=10)
        ttk.Label(barra, text="Buscar:").pack(side="left")
        ttk.Entry(barra, textvariable=self.v_buscar, width=30).pack(
            side="left", padx=6, pady=4
        )

        marco = ttk.Frame(self)
        marco.pack(fill="both", expand=True, padx=10, pady=5)
        cols = ("codigo", "nombre", "precio", "cantidad", "minimo", "valor")
        self.tabla = ttk.Treeview(marco, columns=cols, show="headings")
        encabezados = {
            "codigo": ("Código", 90),
            "nombre": ("Nombre", 280),
            "precio": ("Precio", 90),
            "cantidad": ("Stock", 80),
            "minimo": ("Mínimo", 80),
            "valor": ("Valor total", 110),
        }
        for c, (texto, ancho) in encabezados.items():
            self.tabla.heading(c, text=texto)
            self.tabla.column(
                c, width=ancho, anchor="w" if c in ("codigo", "nombre") else "e"
            )
        self.tabla.tag_configure("bajo", background="#ffd6d6")
        sb = ttk.Scrollbar(marco, orient="vertical", command=self.tabla.yview)
        self.tabla.configure(yscrollcommand=sb.set)
        self.tabla.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.tabla.bind("<<TreeviewSelect>>", self.al_seleccionar)

    def _crear_barra_estado(self):
        self.estado = ttk.Label(self, anchor="w")
        self.estado.pack(fill="x", padx=10, pady=(0, 8))

    def _leer_formulario(self, con_cantidad=True):
        codigo = self.v_codigo.get().strip()
        nombre = self.v_nombre.get().strip()
        if not codigo or not nombre:
            messagebox.showwarning("Datos incompletos", "Código y nombre son obligatorios.")
            return None
        try:
            precio = float(self.v_precio.get().replace(",", ".") or 0)
            minimo = int(self.v_minimo.get() or 0)
            cantidad = int(self.v_cantidad.get() or 0) if con_cantidad else 0
        except ValueError:
            messagebox.showwarning("Dato inválido", "Precio y cantidades deben ser números.")
            return None
        if precio < 0 or minimo < 0 or cantidad < 0:
            messagebox.showwarning("Dato inválido", "No se permiten valores negativos.")
            return None
        return codigo, nombre, precio, cantidad, minimo

    def refrescar(self):
        self.tabla.delete(*self.tabla.get_children())
        total_valor, bajos = 0.0, 0
        for pid, cod, nom, precio, cant, minimo in self.db.listar(self.v_buscar.get().strip()):
            valor = precio * cant
            total_valor += valor
            bajo = cant <= minimo
            bajos += bajo
            self.tabla.insert(
                "", "end", iid=str(pid),
                values=(cod, nom, f"{precio:.2f}", cant, minimo, f"{valor:.2f}"),
                tags=("bajo",) if bajo else (),
            )
        self.estado.config(
            text=f"Productos: {len(self.tabla.get_children())}   |   "
                 f"Con stock bajo: {bajos}   |   Valor del inventario: {total_valor:,.2f}"
        )

    def limpiar(self):
        self.seleccion = None
        self.tabla.selection_remove(self.tabla.selection())
        for var, val in ((self.v_codigo, ""), (self.v_nombre, ""), (self.v_precio, ""),
                         (self.v_cantidad, "0"), (self.v_minimo, "0")):
            var.set(val)
        self.entry_cantidad.config(state="normal")


    def al_seleccionar(self, _evento=None):
        sel = self.tabla.selection()
        if not sel:
            return
        self.seleccion = int(sel[0])
        cod, nom, precio, cant, minimo, _ = self.tabla.item(sel[0], "values")
        self.v_codigo.set(cod)
        self.v_nombre.set(nom)
        self.v_precio.set(precio)
        self.v_cantidad.set(cant)
        self.v_minimo.set(minimo)
        self.entry_cantidad.config(state="disabled")

    def agregar(self):
        datos = self._leer_formulario()
        if not datos:
            return
        try:
            self.db.agregar(*datos)
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Ya existe un producto con ese código.")
            return
        self.limpiar()
        self.refrescar()

    def guardar(self):
        if self.seleccion is None:
            messagebox.showinfo("Selecciona un producto", "Elige un producto de la tabla.")
            return
        datos = self._leer_formulario(con_cantidad=False)
        if not datos:
            return
        codigo, nombre, precio, _, minimo = datos
        try:
            self.db.editar(self.seleccion, codigo, nombre, precio, minimo)
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Ya existe un producto con ese código.")
            return
        self.refrescar()

    def eliminar(self):
        if self.seleccion is None:
            messagebox.showinfo("Selecciona un producto", "Elige un producto de la tabla.")
            return
        if messagebox.askyesno("Confirmar", "¿Eliminar el producto y su historial?"):
            self.db.eliminar(self.seleccion)
            self.limpiar()
            self.refrescar()

    def mover(self, tipo):
        if self.seleccion is None:
            messagebox.showinfo("Selecciona un producto", "Elige un producto de la tabla.")
            return
        try:
            cantidad = int(self.v_mov.get())
            if cantidad <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Dato inválido", "La cantidad debe ser un entero mayor que 0.")
            return
        pid = self.seleccion
        if not self.db.mover(pid, tipo, cantidad):
            messagebox.showerror("Stock insuficiente", "La salida supera el stock disponible.")
            return
        self.refrescar()
        if self.tabla.exists(str(pid)):
            self.tabla.selection_set(str(pid))

    def ver_historial(self):
        ventana = tk.Toplevel(self)
        ventana.title("Historial de movimientos")
        ventana.geometry("640x400")
        cols = ("fecha", "codigo", "nombre", "tipo", "cantidad")
        tabla = ttk.Treeview(ventana, columns=cols, show="headings")
        for c, texto, ancho in (("fecha", "Fecha", 150), ("codigo", "Código", 90),
                                ("nombre", "Nombre", 220), ("tipo", "Tipo", 80),
                                ("cantidad", "Cantidad", 80)):
            tabla.heading(c, text=texto)
            tabla.column(c, width=ancho)
        for fila in self.db.historial():
            tabla.insert("", "end", values=fila)
        tabla.pack(fill="both", expand=True, padx=8, pady=8)


if __name__ == "__main__":
    App().mainloop()
