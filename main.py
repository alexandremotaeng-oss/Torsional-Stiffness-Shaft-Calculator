import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from translator import Translator
from joint_management import JointManagementWindow
from material_management import MaterialManagementWindow
from calculator import Calculator
from report_generator import ReportGenerator
from stp_exporter import StpExporter
import json
import os

# Base directory is the project root (same folder as this file)
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
DATA_DIR     = os.path.join(BASE_DIR, "data")
LOCALE_DIR   = os.path.join(BASE_DIR, "locale")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
ASSETS_DIR   = os.path.join(BASE_DIR, "assets")


class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.translator = Translator(locale_dir=LOCALE_DIR)
        self.joints = []
        self.materials = []
        self.last_calculation_data = None
        self._last_drawn_segments = None   # keeps last segments for redraw on resize/expose

        self.title(self.translator.translate("main_window_title"))
        self.geometry("1280x720")
        self.resizable(True, True)

        # App icon
        icon_path = os.path.join(ASSETS_DIR, "icon.png")
        try:
            icon_img = tk.PhotoImage(file=icon_path)
            self.iconphoto(True, icon_img)
            self._icon_img = icon_img  # keep reference
        except Exception:
            pass  # icon is cosmetic – silently ignore if missing

        self._build_ui()
        self.update_ui()
        self.load_data()

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------
    def _build_ui(self):
        # ── HEADER ─────────────────────────────────────────────────────
        self.header_lf = ttk.LabelFrame(self, text="")
        self.header_lf.pack(fill="x", padx=8, pady=(8, 2))

        header_inner = ttk.Frame(self.header_lf)
        header_inner.pack(anchor="center", pady=4)

        self.project_name_label = ttk.Label(header_inner, text="Nome do Projeto:")
        self.project_name_entry = ttk.Entry(header_inner, width=25)
        self.engineer_label = ttk.Label(header_inner, text="Engenheiro:")
        self.engineer_entry = ttk.Entry(header_inner, width=20)
        self.language_label = ttk.Label(header_inner, text="Idioma:")
        self.language_combobox = ttk.Combobox(
            header_inner, values=["pt_BR", "en", "zh"], width=8, state="readonly"
        )
        self.language_combobox.set("pt_BR")
        self.language_combobox.bind("<<ComboboxSelected>>", self.change_language)

        for col, w in enumerate([
            self.project_name_label, self.project_name_entry,
            self.engineer_label, self.engineer_entry,
            self.language_label, self.language_combobox,
        ]):
            w.grid(row=0, column=col, padx=6, pady=4)

        # ── DRAWING ────────────────────────────────────────────────────
        self.drawing_lf = ttk.LabelFrame(self, text="Desenho")
        self.drawing_lf.pack(fill="both", expand=True, padx=8, pady=2)

        self.canvas = tk.Canvas(self.drawing_lf, bg="#0d1b2a", height=180)
        self.canvas.pack(fill="both", expand=True, padx=4, pady=4)

        # Redraw whenever the canvas is resized or re-exposed (window move/restore)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind("<Expose>",    self._on_canvas_configure)

        # ── SHAFT ──────────────────────────────────────────────────────
        self.shaft_lf = ttk.LabelFrame(self, text="Eixo")
        self.shaft_lf.pack(fill="x", padx=8, pady=2)

        shaft_inner = ttk.Frame(self.shaft_lf)
        shaft_inner.pack(anchor="center", pady=4)

        self.obj_type_label = ttk.Label(shaft_inner, text="OBJ:")
        self.obj_type_combobox = ttk.Combobox(shaft_inner, width=18, state="readonly")
        self.obj_type_combobox.bind("<<ComboboxSelected>>", lambda e: self.draw_shaft())

        self.shaft_diameter_label = ttk.Label(shaft_inner, text="Diâm. Eixo (mm):")
        self.shaft_diameter_var = tk.StringVar(value="0.00")
        self.shaft_diameter_entry = ttk.Entry(
            shaft_inner, textvariable=self.shaft_diameter_var, width=10, justify="center"
        )

        self.shaft_length_label = ttk.Label(shaft_inner, text="Comp. Eixo (mm):")
        self.shaft_length_var = tk.StringVar(value="0.00")
        self.shaft_length_entry = ttk.Entry(
            shaft_inner, textvariable=self.shaft_length_var, width=10, justify="center"
        )

        self.ibj_type_label = ttk.Label(shaft_inner, text="IBJ:")
        self.ibj_type_combobox = ttk.Combobox(shaft_inner, width=18, state="readonly")
        self.ibj_type_combobox.bind("<<ComboboxSelected>>", lambda e: self.draw_shaft())

        for col, w in enumerate([
            self.obj_type_label, self.obj_type_combobox,
            self.shaft_diameter_label, self.shaft_diameter_entry,
            self.shaft_length_label, self.shaft_length_entry,
            self.ibj_type_label, self.ibj_type_combobox,
        ]):
            w.grid(row=0, column=col, padx=6, pady=4)

        # ── MATERIAL ───────────────────────────────────────────────────
        self.material_lf = ttk.LabelFrame(self, text="Material")
        self.material_lf.pack(fill="x", padx=8, pady=2)

        mat_inner = ttk.Frame(self.material_lf)
        mat_inner.pack(anchor="center", pady=4)

        self.material_type_label = ttk.Label(mat_inner, text="Tipo:")
        self.material_type_combobox = ttk.Combobox(mat_inner, width=22, state="readonly")
        self.material_type_combobox.bind("<<ComboboxSelected>>", self.update_shear_modulus)

        self.shear_modulus_label = ttk.Label(mat_inner, text="Módulo de Cisalhamento (MPa):")
        self.shear_modulus_value_var = tk.StringVar(value="0.00")
        self.shear_modulus_value_label = ttk.Label(
            mat_inner, textvariable=self.shear_modulus_value_var,
            width=14, relief="sunken", anchor="center"
        )

        for col, w in enumerate([
            self.material_type_label, self.material_type_combobox,
            self.shear_modulus_label, self.shear_modulus_value_label,
        ]):
            w.grid(row=0, column=col, padx=6, pady=4)

        # ── STIFFNESS ──────────────────────────────────────────────────
        self.stiffness_lf = ttk.LabelFrame(self, text="Rigidez")
        self.stiffness_lf.pack(fill="x", padx=8, pady=2)

        stiff_inner = ttk.Frame(self.stiffness_lf)
        stiff_inner.pack(anchor="center", pady=4)

        self.calculate_button = ttk.Button(
            stiff_inner, text="Calcular", command=self.calculate_stiffness, width=14
        )
        self.stiffness_label = ttk.Label(stiff_inner, text="Rigidez Total (N.m/grau):")
        self.stiffness_value_var = tk.StringVar(value="0.00")
        self.stiffness_value_label = ttk.Label(
            stiff_inner, textvariable=self.stiffness_value_var,
            width=18, relief="sunken", anchor="center", font=("Arial", 11, "bold")
        )

        for col, w in enumerate([
            self.calculate_button,
            self.stiffness_label,
            self.stiffness_value_label,
        ]):
            w.grid(row=0, column=col, padx=10, pady=4)

        # ── TOOLS ──────────────────────────────────────────────────────
        self.tools_lf = ttk.LabelFrame(self, text="Ferramentas")
        self.tools_lf.pack(fill="x", padx=8, pady=(2, 8))

        tools_inner = ttk.Frame(self.tools_lf)
        tools_inner.pack(anchor="center", pady=4)

        self.manage_joints_button = ttk.Button(
            tools_inner, text="Gerenciar Juntas",
            command=self.open_joint_management, width=20
        )
        self.manage_materials_button = ttk.Button(
            tools_inner, text="Gerenciar Materiais",
            command=self.open_material_management, width=20
        )
        self.export_stp_button = ttk.Button(
            tools_inner, text="Exportar .STP",
            command=self.export_stp, width=16
        )
        self.generate_report_button = ttk.Button(
            tools_inner, text="Gerar Relatório",
            command=self.generate_report, width=16
        )

        for col, w in enumerate([
            self.manage_joints_button,
            self.manage_materials_button,
            self.export_stp_button,
            self.generate_report_button,
        ]):
            w.grid(row=0, column=col, padx=10, pady=4)

        # Status bar
        self.status_bar = ttk.Label(
            self, text="", relief="sunken", anchor="w",
            font=("Arial", 8), padding=(6, 2)
        )
        self.status_bar.pack(fill="x", side="bottom", padx=0, pady=0)

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------
    def load_data(self):
        self.load_joints()
        self.load_materials()

    def load_joints(self):
        path = os.path.join(DATA_DIR, "joints.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.joints = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.joints = []
        joint_names = [j["name"] for j in self.joints]
        self.obj_type_combobox["values"] = joint_names
        self.ibj_type_combobox["values"] = joint_names

    def load_materials(self):
        path = os.path.join(DATA_DIR, "materials.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.materials = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.materials = []
        material_names = [m["name"] for m in self.materials]
        self.material_type_combobox["values"] = material_names

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------
    def update_shear_modulus(self, event=None):
        selected = self.material_type_combobox.get()
        for mat in self.materials:
            if mat["name"] == selected:
                self.shear_modulus_value_var.set(f"{mat['shear_modulus']:.2f}")
                return
        self.shear_modulus_value_var.set("0.00")

    def calculate_stiffness(self):
        obj_joint_name = self.obj_type_combobox.get()
        ibj_joint_name = self.ibj_type_combobox.get()
        material_name = self.material_type_combobox.get()

        obj_joint = next((j for j in self.joints if j["name"] == obj_joint_name), None)
        ibj_joint = next((j for j in self.joints if j["name"] == ibj_joint_name), None)
        material = next((m for m in self.materials if m["name"] == material_name), None)

        diam_str = self.shaft_diameter_var.get().strip()
        length_str = self.shaft_length_var.get().strip()

        if not all([obj_joint, ibj_joint, material, diam_str, length_str]):
            messagebox.showerror(
                self.translator.translate("error"),
                self.translator.translate("fill_all_fields")
            )
            return

        try:
            shaft_diameter = float(diam_str)
            shaft_length = float(length_str)
        except ValueError:
            messagebox.showerror(
                self.translator.translate("error"),
                self.translator.translate("invalid_number")
            )
            return

        if shaft_diameter <= 0 or shaft_length <= 0:
            messagebox.showerror(
                self.translator.translate("error"),
                self.translator.translate("positive_values")
            )
            return

        shear_modulus = material["shear_modulus"]
        segments = []

        for sec in obj_joint["sections"]:
            segments.append({
                "diameter": float(sec["diameter"]),
                "length": float(sec["length"]),
                "shear_modulus": shear_modulus,
            })

        segments.append({
            "diameter": shaft_diameter,
            "length": shaft_length,
            "shear_modulus": shear_modulus,
        })

        # IBJ sections are stored from inner-end (sec 1) to outer-end (sec 6).
        # In the drawing the IBJ is mirrored: sec 6 is adjacent to the main shaft
        # and sec 1 is at the outermost right tip, so we reverse the order here.
        for sec in reversed(ibj_joint["sections"]):
            segments.append({
                "diameter": float(sec["diameter"]),
                "length": float(sec["length"]),
                "shear_modulus": shear_modulus,
            })

        try:
            calc = Calculator()
            total_stiffness = calc.calculate_torsional_stiffness(segments)
        except ZeroDivisionError:
            messagebox.showerror(
                self.translator.translate("error"),
                self.translator.translate("zero_length_segment")
            )
            return

        self.stiffness_value_var.set(f"{total_stiffness:.4f}")
        self.draw_shaft(segments)

        # Store a deep copy so mutations in report_generator don't corrupt it
        self.last_calculation_data = {
            "project_name":   self.project_name_entry.get(),
            "engineer":       self.engineer_entry.get(),
            "segments":       [dict(s) for s in segments],
            "total_stiffness": total_stiffness,
            "obj_joint_name": obj_joint_name,
            "ibj_joint_name": ibj_joint_name,
            "material_name":         material_name,
            "shear_modulus":         shear_modulus,
            "elastic_modulus_mpa":   material.get("elastic_modulus_mpa", 0.0),
            "yield_strength_mpa":    material.get("yield_strength_mpa", 0.0),
            "ultimate_strength_mpa": material.get("ultimate_strength_mpa", 0.0),
        }

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------
    def _on_canvas_configure(self, event=None):
        """Called when the canvas is resized or re-exposed. Redraws with last segments."""
        self.draw_shaft(self._last_drawn_segments)

    def draw_shaft(self, segments=None):
        # Persist segments so that resize/expose can redraw them
        if segments is not None:
            self._last_drawn_segments = segments
        else:
            segments = self._last_drawn_segments  # redraw with previously calculated segments

        self.canvas.update_idletasks()
        self.canvas.delete("all")
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w <= 1 or h <= 1:
            return

        pad_x = 60
        pad_y = 36          # vertical padding for labels above/below shaft
        mid_y  = h / 2

        if not segments:
            self._draw_shaft_shape(None, w, h, mid_y, pad_x, pad_y)
            return

        total_length = sum(s["length"] for s in segments)
        if total_length == 0:
            return

        self._draw_shaft_shape(segments, w, h, mid_y, pad_x, pad_y)

    # ------------------------------------------------------------------
    def _draw_shaft_shape(self, segments, w, h, mid_y, pad_x, pad_y):
        """
        Draws the shaft as a single continuous silhouette.

        Approach
        --------
        • One filled polygon per segment colour band (upper half), mirrored for lower half.
        • Thin internal dividers only at segment boundaries (no outer border on top/bottom).
        • scale_y uses half the available height so proportions feel slender/smooth.
        • Axis centre-line and dimensional markers drawn on top.
        """
        palette = [
            "#1a3a5c", "#1e4570", "#224f84", "#1a3a5c",
            "#1e4570", "#224f84", "#2a6090",
            "#224f84", "#1e4570", "#1a3a5c", "#224f84",
            "#1e4570", "#1a3a5c",
        ]

        avail_w = w - 2 * pad_x
        avail_h = (h - 2 * pad_y)   # full usable height

        if segments is None:
            # ── Placeholder ──────────────────────────────────────────
            n = 13
            block_w = avail_w / n
            half_h  = avail_h * 0.15   # half the block height
            seg_xs  = [pad_x + i * block_w for i in range(n + 1)]

            for i in range(n):
                x1, x2 = seg_xs[i], seg_xs[i + 1]
                y1 = mid_y - half_h
                y2 = mid_y + half_h
                fill = palette[i % len(palette)]
                # filled band
                self.canvas.create_polygon(
                    x1, y1, x2, y1, x2, y2, x1, y2,
                    fill=fill, outline=""
                )
                # internal vertical divider (skip first left edge, skip last right edge)
                if i > 0:
                    self.canvas.create_line(x1, y1, x1, y2, fill="#4a8ac4", width=1)

            # outer silhouette — top and bottom lines only
            self.canvas.create_line(
                seg_xs[0], mid_y - half_h, seg_xs[-1], mid_y - half_h,
                fill="#4a8ac4", width=1
            )
            self.canvas.create_line(
                seg_xs[0], mid_y + half_h, seg_xs[-1], mid_y + half_h,
                fill="#4a8ac4", width=1
            )
            # left and right caps
            self.canvas.create_line(
                seg_xs[0], mid_y - half_h, seg_xs[0], mid_y + half_h,
                fill="#4a8ac4", width=1
            )
            self.canvas.create_line(
                seg_xs[-1], mid_y - half_h, seg_xs[-1], mid_y + half_h,
                fill="#4a8ac4", width=1
            )
            p11_x = seg_xs[2] + block_w / 2
            p18_x = seg_xs[10] + block_w / 2
            self._draw_markers(p11_x, p18_x, mid_y, half_h, None, None)
            return

        # ── Real segments ─────────────────────────────────────────────
        max_diam   = max(s["diameter"] for s in segments)
        total_len  = sum(s["length"] for s in segments)
        scale_x    = avail_w / total_len
        # Use HALF of avail_h so the shaft looks slender
        scale_y    = (avail_h * 0.5 / max_diam) if max_diam > 0 else 1

        # Pre-compute x positions and half-heights
        xs = [pad_x]
        half_hs = []
        for seg in segments:
            xs.append(xs[-1] + seg["length"] * scale_x)
            half_hs.append(seg["diameter"] * scale_y / 2)

        # Draw filled colour bands
        for i, seg in enumerate(segments):
            x1, x2 = xs[i], xs[i + 1]
            hh = half_hs[i]
            fill = palette[i % len(palette)]
            self.canvas.create_polygon(
                x1, mid_y - hh,
                x2, mid_y - hh,
                x2, mid_y + hh,
                x1, mid_y + hh,
                fill=fill, outline=""
            )

        # Draw internal vertical dividers at segment junctions
        for i in range(1, len(segments)):
            x = xs[i]
            # divider spans from the taller of two adjacent segments
            top_y    = mid_y - max(half_hs[i - 1], half_hs[i])
            bottom_y = mid_y + max(half_hs[i - 1], half_hs[i])
            self.canvas.create_line(x, top_y, x, bottom_y, fill="#4a8ac4", width=1)

        # Draw outer silhouette: top profile, right cap, bottom profile (reversed), left cap
        top_pts    = []
        bottom_pts = []
        for i in range(len(segments)):
            top_pts   += [xs[i],     mid_y - half_hs[i],
                          xs[i + 1], mid_y - half_hs[i]]
            bottom_pts += [xs[i],     mid_y + half_hs[i],
                           xs[i + 1], mid_y + half_hs[i]]

        # Top edge
        self.canvas.create_line(*top_pts, fill="#4a8ac4", width=1)
        # Bottom edge
        self.canvas.create_line(*bottom_pts, fill="#4a8ac4", width=1)
        # Left cap
        self.canvas.create_line(
            xs[0],  mid_y - half_hs[0],
            xs[0],  mid_y + half_hs[0],
            fill="#4a8ac4", width=1
        )
        # Right cap
        self.canvas.create_line(
            xs[-1], mid_y - half_hs[-1],
            xs[-1], mid_y + half_hs[-1],
            fill="#4a8ac4", width=1
        )

        # Diameter labels below each segment
        for i, seg in enumerate(segments):
            cx = (xs[i] + xs[i + 1]) / 2
            by = mid_y + half_hs[i]
            self.canvas.create_text(
                cx, by + 10,
                text=f"Ø{seg['diameter']:.1f}",
                fill="#8ab4d4", font=("Arial", 7)
            )

        # Markers P11 / P18
        if len(segments) == 13:
            p11_x = (xs[2] + xs[3]) / 2
            p18_x = (xs[10] + xs[11]) / 2
            dist_mm = (
                sum(s["length"] for s in segments[3:10])
                + segments[2]["length"] / 2
                + segments[10]["length"] / 2
            )
            shaft_diam = segments[6]["diameter"]
            self._draw_markers(p11_x, p18_x, mid_y, half_hs[6], dist_mm, shaft_diam)

    # ------------------------------------------------------------------
    def _draw_markers(self, p11_x, p18_x, mid_y, shaft_half_h, dist_mm, shaft_diam):
        """Draw P11/P18 reference lines, distance arrow, and centre-shaft label."""
        marker_top    = mid_y - shaft_half_h - 18
        marker_bottom = mid_y + shaft_half_h + 18

        for x, label in [(p11_x, "P11"), (p18_x, "P18")]:
            self.canvas.create_line(
                x, marker_top, x, marker_bottom,
                fill="#ff6060", width=1, dash=(4, 3)
            )
            self.canvas.create_text(
                x, marker_top - 10,
                text=label, fill="#ff9090", font=("Arial", 8, "bold")
            )

        # Dimension arrow between P11 and P18 (above shaft)
        arrow_y = mid_y - shaft_half_h - 10
        self.canvas.create_line(
            p11_x, arrow_y, p18_x, arrow_y,
            arrow=tk.BOTH, fill="#ffcc00", width=1
        )
        dist_label = f"{dist_mm:.1f} mm" if dist_mm is not None else "__ mm"
        self.canvas.create_text(
            (p11_x + p18_x) / 2, arrow_y - 10,
            text=dist_label, fill="#ffcc00", font=("Arial", 8, "bold")
        )

        # Centre shaft diameter label (below shaft, between markers)
        if shaft_diam is not None:
            diam_y = mid_y + shaft_half_h + 22
            self.canvas.create_text(
                (p11_x + p18_x) / 2, diam_y,
                text=f"Ø {shaft_diam:.1f} mm",
                fill="#a8d8f0", font=("Arial", 8, "bold")
            )

    # ------------------------------------------------------------------
    # Export / Report
    # ------------------------------------------------------------------
    def export_stp(self):
        if not self.last_calculation_data:
            messagebox.showinfo("Info", self.translator.translate("calculate_first"))
            return
        file_path = filedialog.asksaveasfilename(
            defaultextension=".stp",
            filetypes=[("STEP files", "*.stp *.step"), ("All files", "*.*")],
        )
        if not file_path:
            return
        try:
            exporter = StpExporter(self.last_calculation_data["segments"])
            exporter.export(file_path)
            messagebox.showinfo("OK", f"Arquivo salvo em:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao exportar STP:\n{e}")

    def generate_report(self):
        if not self.last_calculation_data:
            messagebox.showinfo("Info", self.translator.translate("calculate_first"))
            return
        try:
            rg = ReportGenerator(
                template_dir=TEMPLATES_DIR,
                output_dir=BASE_DIR,
                translator=self.translator,
            )
            rg.generate_report(self.last_calculation_data)
        except Exception as e:
            messagebox.showerror(
                self.translator.translate("error"),
                f"{self.translator.translate('save_error')}:\n{e}"
            )

    # ------------------------------------------------------------------
    # i18n
    # ------------------------------------------------------------------
    def update_ui(self):
        t = self.translator.translate
        self.title(t("main_window_title"))
        self.drawing_lf.config(text=t("drawing"))
        self.shaft_lf.config(text=t("shaft"))
        self.material_lf.config(text=t("material"))
        self.stiffness_lf.config(text=t("stiffness"))
        self.tools_lf.config(text=t("tools"))
        self.project_name_label.config(text=t("project_name") + ":")
        self.engineer_label.config(text=t("engineer") + ":")
        self.language_label.config(text=t("language") + ":")
        self.obj_type_label.config(text=t("obj_type") + ":")
        self.shaft_diameter_label.config(text=t("shaft_diameter") + " (mm):")
        self.shaft_length_label.config(text=t("shaft_length") + " (mm):")
        self.ibj_type_label.config(text=t("ibj_type") + ":")
        self.material_type_label.config(text=t("material_type") + ":")
        self.shear_modulus_label.config(text=t("shear_modulus") + " (MPa):")
        self.calculate_button.config(text=t("calculate"))
        self.stiffness_label.config(text=t("stiffness") + " (N.m/grau):")
        self.manage_joints_button.config(text=t("manage_joints"))
        self.manage_materials_button.config(text=t("manage_materials"))
        self.export_stp_button.config(text=t("export_stp"))
        self.generate_report_button.config(text=t("generate_report"))
        self.status_bar.config(text=f"  {t('status_version')}")

    def change_language(self, event=None):
        self.translator.set_language(self.language_combobox.get())
        self.update_ui()

    # ------------------------------------------------------------------
    # Sub-windows
    # ------------------------------------------------------------------
    def open_joint_management(self):
        win = JointManagementWindow(self, data_dir=DATA_DIR, translator=self.translator)
        self.wait_window(win)
        self.load_joints()

    def open_material_management(self):
        win = MaterialManagementWindow(self, data_dir=DATA_DIR, translator=self.translator)
        self.wait_window(win)
        self.load_materials()


if __name__ == "__main__":
    app = MainWindow()
    app.mainloop()
