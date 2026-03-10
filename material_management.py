import tkinter as tk
from tkinter import ttk, messagebox
import json
import os

COLUMNS = ("material_name", "shear_modulus_mpa",
           "elastic_modulus_mpa", "yield_strength_mpa", "ultimate_strength_mpa")
COLUMN_HEADERS = {
    "material_name":        "Nome do Material",
    "shear_modulus_mpa":    "Módulo Cisalh. G (MPa)",
    "elastic_modulus_mpa":  "Módulo Elástico E (MPa)",
    "yield_strength_mpa":   "Tensão Escoamento (MPa)",
    "ultimate_strength_mpa":"Tensão Ruptura (MPa)",
}
COLUMN_WIDTHS = {
    "material_name":        220,
    "shear_modulus_mpa":    160,
    "elastic_modulus_mpa":  170,
    "yield_strength_mpa":   170,
    "ultimate_strength_mpa":170,
}
DEFAULT_NEW_ROW = ("Novo Material", "0.00", "0.00", "0.00", "0.00")


class MaterialManagementWindow(tk.Toplevel):
    def __init__(self, parent, data_dir="data", translator=None):
        super().__init__(parent)
        self.data_dir = data_dir
        self.translator = translator
        self.title(self._t("material_management_window_title"))
        self.resizable(True, True)

        self._build_ui()
        self.load_materials()
        self.update_ui()

        # Auto-fit width: sum of all column widths + scrollbar + padding
        total_col_w = sum(COLUMN_WIDTHS.values())
        win_w = total_col_w + 20 + 20   # +scrollbar (~20) + left/right padding
        win_h = 400
        self.geometry(f"{win_w}x{win_h}")
        self.minsize(win_w, 200)

    def _t(self, key):
        if self.translator:
            return self.translator.translate(key)
        return COLUMN_HEADERS.get(key, key)

    def update_ui(self):
        """Refresh all translatable text."""
        self.title(self._t("material_management_window_title"))
        self.new_button.config(text=self._t("new"))
        self.edit_button.config(text=self._t("edit"))
        self.save_button.config(text=self._t("save"))
        self.delete_button.config(text=self._t("delete"))
        for col in COLUMNS:
            self.tree.heading(col, text=self._t(col))

    def _build_ui(self):
        # ── TOOLBAR ────────────────────────────────────────────────────
        toolbar = ttk.Frame(self)
        toolbar.pack(side="top", fill="x", padx=8, pady=6)

        btn_frame = ttk.Frame(toolbar)
        btn_frame.pack(anchor="center")

        self.new_button = ttk.Button(
            btn_frame, text=self._t("new"), command=self.new_material, width=12
        )
        self.edit_button = ttk.Button(
            btn_frame, text=self._t("edit"), command=self.edit_materials, width=12
        )
        self.save_button = ttk.Button(
            btn_frame, text=self._t("save"), command=self.save_materials, width=12
        )
        self.delete_button = ttk.Button(
            btn_frame, text=self._t("delete"), command=self.delete_material, width=12
        )

        for col, btn in enumerate([
            self.new_button, self.edit_button, self.save_button, self.delete_button
        ]):
            btn.grid(row=0, column=col, padx=8, pady=2)

        # ── TREEVIEW + SCROLLBARS ──────────────────────────────────────
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.tree = ttk.Treeview(tree_frame, columns=COLUMNS, show="headings",
                                  selectmode="browse")

        for col in COLUMNS:
            self.tree.heading(col, text=COLUMN_HEADERS[col], anchor="center")
            self.tree.column(col, width=COLUMN_WIDTHS[col], anchor="center",
                             minwidth=80, stretch=True)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        self.tree.bind("<Double-1>", self.on_double_click)

    # ------------------------------------------------------------------
    # Inline editing
    # ------------------------------------------------------------------
    def on_double_click(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region != "cell":
            return
        item = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        if not item or not col:
            return

        col_index = int(col.replace("#", "")) - 1
        bbox = self.tree.bbox(item, col)
        if not bbox:
            return
        x, y, width, height = bbox

        values = self.tree.item(item, "values")
        current_val = values[col_index] if col_index < len(values) else ""

        entry_var = tk.StringVar(value=current_val)
        entry = ttk.Entry(self.tree, textvariable=entry_var, justify="center")
        entry.place(x=x, y=y, width=width, height=height)
        entry.focus_set()
        entry.select_range(0, tk.END)

        def commit(e=None):
            new_val = entry_var.get()
            vals = list(self.tree.item(item, "values"))
            if col_index >= 1:   # all numeric columns
                try:
                    new_val = f"{float(new_val):.2f}"
                except ValueError:
                    new_val = "0.00"
            vals[col_index] = new_val
            self.tree.item(item, values=vals)
            entry.destroy()

        entry.bind("<Return>", commit)
        entry.bind("<Tab>", commit)
        entry.bind("<FocusOut>", commit)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    def new_material(self):
        iid = self.tree.insert("", "end", values=DEFAULT_NEW_ROW)
        self.tree.selection_set(iid)
        self.tree.see(iid)

    def edit_materials(self):
        messagebox.showinfo(
            self._t("edit"),
            self._t("edit_hint")
        )

    def save_materials(self):
        materials = []
        for child in self.tree.get_children():
            values = self.tree.item(child, "values")
            try:
                materials.append({
                    "name":                 values[0],
                    "shear_modulus":        float(values[1]) if len(values) > 1 else 0.0,
                    "elastic_modulus_mpa":  float(values[2]) if len(values) > 2 else 0.0,
                    "yield_strength_mpa":   float(values[3]) if len(values) > 3 else 0.0,
                    "ultimate_strength_mpa":float(values[4]) if len(values) > 4 else 0.0,
                })
            except (IndexError, ValueError) as exc:
                messagebox.showerror(self._t("error"), f"{self._t('invalid_data')}: {exc}")
                return

        path = os.path.join(self.data_dir, "materials.json")
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(materials, f, indent=4, ensure_ascii=False)
            messagebox.showinfo(self._t("save"), self._t("saved_materials_ok"))
        except Exception as exc:
            messagebox.showerror(self._t("error"), f"{self._t('save_error')}: {exc}")

    def delete_material(self):
        selected = self.tree.selection()
        if not selected:
            return
        if messagebox.askyesno(self._t("delete"), self._t("delete_confirm_material")):
            self.tree.delete(selected)

    def load_materials(self):
        path = os.path.join(self.data_dir, "materials.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                materials = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            materials = []
        except Exception as exc:
            messagebox.showerror(self._t("error"), f"{self._t('load_error')}: {exc}")
            return

        for mat in materials:
            name = mat.get("name", "")
            g    = mat.get("shear_modulus", 0.0)
            e    = mat.get("elastic_modulus_mpa", 0.0)
            sy   = mat.get("yield_strength_mpa", 0.0)
            su   = mat.get("ultimate_strength_mpa", 0.0)
            self.tree.insert("", "end", values=(
                name,
                f"{float(g):.2f}",
                f"{float(e):.2f}",
                f"{float(sy):.2f}",
                f"{float(su):.2f}",
            ))
