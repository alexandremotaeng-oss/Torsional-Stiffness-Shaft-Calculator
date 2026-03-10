import tkinter as tk
from tkinter import ttk, messagebox
import json
import os

COLUMNS = (
    "joint_name",
    "section_1", "length_1",
    "section_2", "length_2",
    "section_3", "length_3",
    "section_4", "length_4",
    "section_5", "length_5",
    "section_6", "length_6",
)

COLUMN_HEADERS = {
    "joint_name": "Nome da Junta",
    "section_1": "Seção 1 (mm)", "length_1": "Comp. 1 (mm)",
    "section_2": "Seção 2 (mm)", "length_2": "Comp. 2 (mm)",
    "section_3": "Seção 3 (mm)", "length_3": "Comp. 3 (mm)",
    "section_4": "Seção 4 (mm)", "length_4": "Comp. 4 (mm)",
    "section_5": "Seção 5 (mm)", "length_5": "Comp. 5 (mm)",
    "section_6": "Seção 6 (mm)", "length_6": "Comp. 6 (mm)",
}

COLUMN_WIDTHS = {
    "joint_name": 140,
    **{k: 90 for k in COLUMN_HEADERS if k != "joint_name"},
}

DEFAULT_NEW_ROW = ("Nova Junta",) + ("0.00",) * 12


class JointManagementWindow(tk.Toplevel):
    def __init__(self, parent, data_dir="data", translator=None):
        super().__init__(parent)
        self.data_dir = data_dir
        self.translator = translator
        self.title(self._t("joint_management_window_title"))
        self.resizable(True, True)

        self._build_ui()
        self.load_joints()
        self.update_ui()

        # Auto-fit width: sum of all column widths + scrollbar + padding
        total_col_w = sum(COLUMN_WIDTHS.values())
        win_w = total_col_w + 20 + 20   # +scrollbar (~20) + left/right padding
        win_h = 480
        self.geometry(f"{win_w}x{win_h}")
        self.minsize(win_w, 200)

    def _t(self, key):
        if self.translator:
            return self.translator.translate(key)
        return COLUMN_HEADERS.get(key, key)

    def update_ui(self):
        """Refresh all translatable text — called on creation and after language change."""
        self.title(self._t("joint_management_window_title"))
        self.new_button.config(text=self._t("new"))
        self.edit_button.config(text=self._t("edit"))
        self.save_button.config(text=self._t("save"))
        self.delete_button.config(text=self._t("delete"))
        # Refresh treeview column headers
        for col in COLUMNS:
            self.tree.heading(col, text=self._t(col))

    def _build_ui(self):
        # ── TOOLBAR ────────────────────────────────────────────────────
        toolbar = ttk.Frame(self)
        toolbar.pack(side="top", fill="x", padx=8, pady=6)

        btn_frame = ttk.Frame(toolbar)
        btn_frame.pack(anchor="center")

        self.new_button = ttk.Button(
            btn_frame, text=self._t("new"), command=self.new_joint, width=12
        )
        self.edit_button = ttk.Button(
            btn_frame, text=self._t("edit"), command=self.edit_joints, width=12
        )
        self.save_button = ttk.Button(
            btn_frame, text=self._t("save"), command=self.save_joints, width=12
        )
        self.delete_button = ttk.Button(
            btn_frame, text=self._t("delete"), command=self.delete_joint, width=12
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
                             minwidth=60, stretch=True)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
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
            # Validate numeric columns (all except first)
            if col_index > 0:
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
    def new_joint(self):
        iid = self.tree.insert("", "end", values=DEFAULT_NEW_ROW)
        self.tree.selection_set(iid)
        self.tree.see(iid)

    def edit_joints(self):
        messagebox.showinfo(
            self._t("edit"),
            self._t("edit_hint")
        )

    def save_joints(self):
        joints = []
        for child in self.tree.get_children():
            values = self.tree.item(child, "values")
            try:
                sections = []
                for i in range(1, 13, 2):
                    sections.append({
                        "diameter": float(values[i]) if values[i] else 0.0,
                        "length": float(values[i + 1]) if values[i + 1] else 0.0,
                    })
                joints.append({"name": values[0], "sections": sections})
            except (IndexError, ValueError) as exc:
                messagebox.showerror(self._t("error"), f"{self._t('invalid_data')}: {exc}")
                return

        path = os.path.join(self.data_dir, "joints.json")
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(joints, f, indent=4, ensure_ascii=False)
            messagebox.showinfo(self._t("save"), self._t("saved_joints_ok"))
        except Exception as exc:
            messagebox.showerror(self._t("error"), f"{self._t('save_error')}: {exc}")

    def delete_joint(self):
        selected = self.tree.selection()
        if not selected:
            return
        if messagebox.askyesno(self._t("delete"), self._t("delete_confirm_joint")):
            self.tree.delete(selected)

    def load_joints(self):
        path = os.path.join(self.data_dir, "joints.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                joints = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            joints = []
        except Exception as exc:
            messagebox.showerror(self._t("error"), f"{self._t('load_error')}: {exc}")
            return

        for joint in joints:
            values = [joint.get("name", "")]
            for sec in joint.get("sections", []):
                values.append(f"{float(sec.get('diameter', 0)):.2f}")
                values.append(f"{float(sec.get('length', 0)):.2f}")
            # Pad to 13 columns if needed
            while len(values) < len(COLUMNS):
                values.append("0.00")
            self.tree.insert("", "end", values=tuple(values[:len(COLUMNS)]))
