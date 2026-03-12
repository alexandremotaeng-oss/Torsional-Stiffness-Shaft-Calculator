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
import math

# Base directory is the project root (same folder as this file)
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
DATA_DIR      = os.path.join(BASE_DIR, "data")
LOCALE_DIR    = os.path.join(BASE_DIR, "locale")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
ASSETS_DIR    = os.path.join(BASE_DIR, "assets")
PROJECTS_DIR  = os.path.join(BASE_DIR, "projects")

# Ensure projects folder exists
os.makedirs(PROJECTS_DIR, exist_ok=True)

DEFAULT_PROJECT = "New_Shaft"


class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.translator = Translator(locale_dir=LOCALE_DIR)
        self.joints = []
        self.materials = []
        self.last_calculation_data = None
        self._last_drawn_segments = None   # keeps last segments for redraw on resize/expose

        self.title(self.translator.translate("main_window_title"))
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

        # Set initial window size based on actual content, then allow free resize.
        # minsize ensures the window never becomes unusably small.
        self.update_idletasks()
        w = max(self.winfo_reqwidth(), 900)
        h = self.winfo_reqheight()
        self.geometry(f"{w}x{h}")
        self.minsize(900, 700)

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
        self.project_name_entry = ttk.Entry(header_inner, width=50)
        self.engineer_label = ttk.Label(header_inner, text="Engenheiro:")
        self.engineer_entry = ttk.Entry(header_inner, width=50)
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

        # ── PROJECTS ───────────────────────────────────────────────────
        self.projects_lf = ttk.LabelFrame(self, text="Projetos")
        self.projects_lf.pack(fill="x", padx=8, pady=2)

        projects_inner = ttk.Frame(self.projects_lf)
        projects_inner.pack(anchor="center", pady=4)

        self.project_file_label = ttk.Label(projects_inner, text="Arquivo:")
        self.project_file_var = tk.StringVar(value=DEFAULT_PROJECT)
        self.project_file_combobox = ttk.Combobox(
            projects_inner, textvariable=self.project_file_var, width=40
        )
        self.load_project_button = ttk.Button(
            projects_inner, text="Carregar", command=self.load_project, width=12
        )
        self.save_project_button = ttk.Button(
            projects_inner, text="Salvar", command=self.save_project, width=12
        )

        for col, w in enumerate([
            self.project_file_label,
            self.project_file_combobox,
            self.load_project_button,
            self.save_project_button,
        ]):
            w.grid(row=0, column=col, padx=6, pady=4)

        self._refresh_project_list()

        # ── DRAWING ────────────────────────────────────────────────────
        self.drawing_lf = ttk.LabelFrame(self, text="Desenho")
        self.drawing_lf.pack(fill="both", expand=True, padx=8, pady=2)

        self.canvas = tk.Canvas(self.drawing_lf, bg="#0d1b2a", height=45)
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
        self.obj_type_combobox = ttk.Combobox(shaft_inner, width=25, state="readonly")
        self.obj_type_combobox.bind("<<ComboboxSelected>>", lambda e: self.draw_shaft())

        self.shaft_diameter_label = ttk.Label(shaft_inner, text="Diâm. Eixo (mm):")
        self.shaft_diameter_var = tk.StringVar(value="0.00")
        self.shaft_diameter_entry = ttk.Entry(
            shaft_inner, textvariable=self.shaft_diameter_var, width=10, justify="center"
        )

        # P11–P18 distance (user input)
        self.shaft_length_label = ttk.Label(shaft_inner, text="Junta [Centro-Centro] (mm):")
        self.shaft_length_var = tk.StringVar(value="0.00")
        self.shaft_length_entry = ttk.Entry(
            shaft_inner, textvariable=self.shaft_length_var, width=10, justify="center"
        )

        self.ibj_type_label = ttk.Label(shaft_inner, text="IBJ:")
        self.ibj_type_combobox = ttk.Combobox(shaft_inner, width=25, state="readonly")
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
        self.material_type_combobox = ttk.Combobox(mat_inner, width=50, state="readonly")
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
        self.stiffness_lf = ttk.LabelFrame(self, text="Resultados")
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

        self.freq_label = ttk.Label(stiff_inner, text="1ª Freq. Natural (Hz):")
        self.freq_value_var = tk.StringVar(value="0.00")
        self.freq_value_label = ttk.Label(
            stiff_inner, textvariable=self.freq_value_var,
            width=14, relief="sunken", anchor="center", font=("Arial", 11, "bold")
        )

        self.mass_label = ttk.Label(stiff_inner, text="Massa (kg):")
        self.mass_value_var = tk.StringVar(value="0.000")
        self.mass_value_label = ttk.Label(
            stiff_inner, textvariable=self.mass_value_var,
            width=12, relief="sunken", anchor="center", font=("Arial", 11, "bold")
        )

        for col, w in enumerate([
            self.calculate_button,
            self.stiffness_label,
            self.stiffness_value_label,
            self.freq_label,
            self.freq_value_label,
            self.mass_label,
            self.mass_value_label,
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
        self.compatibility_button = ttk.Button(
            tools_inner, text="Buscar Compatibilidade",
            command=self.open_compatibility_search, width=22
        )

        for col, w in enumerate([
            self.manage_joints_button,
            self.manage_materials_button,
            self.export_stp_button,
            self.generate_report_button,
            self.compatibility_button,
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
        material_name  = self.material_type_combobox.get()

        obj_joint = next((j for j in self.joints if j["name"] == obj_joint_name), None)
        ibj_joint = next((j for j in self.joints if j["name"] == ibj_joint_name), None)
        material  = next((m for m in self.materials if m["name"] == material_name), None)

        diam_str   = self.shaft_diameter_var.get().strip()
        length_str = self.shaft_length_var.get().strip()   # P11–P18 distance

        if not all([obj_joint, ibj_joint, material, diam_str, length_str]):
            messagebox.showerror(
                self.translator.translate("error"),
                self.translator.translate("fill_all_fields")
            )
            return

        try:
            shaft_diameter = float(diam_str)
            p11_p18_length = float(length_str)
        except ValueError:
            messagebox.showerror(
                self.translator.translate("error"),
                self.translator.translate("invalid_number")
            )
            return

        if shaft_diameter <= 0 or p11_p18_length <= 0:
            messagebox.showerror(
                self.translator.translate("error"),
                self.translator.translate("positive_values")
            )
            return

        shear_modulus = material["shear_modulus"]

        # ── Helper: build list of valid (D>0, L>0) segments from a joint ──
        def valid_sections(joint):
            return [
                {"diameter": float(s["diameter"]), "length": float(s["length"]),
                 "shear_modulus": shear_modulus}
                for s in joint.get("sections", [])
                if float(s.get("diameter", 0)) > 0 and float(s.get("length", 0)) > 0
            ]

        obj_segs = valid_sections(obj_joint)          # OBJ: inside-out order (sec1 first)
        ibj_segs = valid_sections(ibj_joint)[::-1]    # IBJ: reversed so sec1 is outermost right

        obj_offset = float(obj_joint.get("offset", 0.0))
        ibj_offset = float(ibj_joint.get("offset", 0.0))

        obj_len = sum(s["length"] for s in obj_segs)
        ibj_len = sum(s["length"] for s in ibj_segs)

        # ── Length breakdown ────────────────────────────────────────────
        # The user types the P11–P18 distance (distance between the two markers).
        # P11 is at obj_offset from the LEFT shaft end.
        # P18 is at ibj_offset from the RIGHT shaft end.
        # Total shaft = obj_len + central_bare + ibj_len
        # P11–P18 span = total - obj_offset - ibj_offset
        #              = obj_len + central_bare + ibj_len - obj_offset - ibj_offset
        # => central_bare = p11_p18_length - obj_len - ibj_len + obj_offset + ibj_offset
        p11_p18_length = float(length_str)   # user-typed P11→P18 distance
        central_bare   = p11_p18_length - obj_len - ibj_len + obj_offset + ibj_offset
        # central_length for stiffness calc = bare shaft minus the offset zones
        central_length = central_bare - obj_offset - ibj_offset
        if central_length <= 0:
            messagebox.showerror(
                self.translator.translate("error"),
                self.translator.translate("positive_values")
            )
            return

        # ── Build full segment list for drawing ────────────────────────
        # central_seg spans central_bare so that P11–P18 in the drawing equals
        # the value the user typed.
        central_seg = {
            "diameter": shaft_diameter,
            "length":   central_bare,
            "shear_modulus": shear_modulus,
        }
        all_segments = obj_segs + [central_seg] + ibj_segs

        # ── Determine which segments to include in stiffness calc ──────
        # A segment is excluded if its START position is before the offset.
        # i.e. we skip every segment whose leading edge < offset (even if it
        # crosses the offset boundary — it still lives partly inside the joint).
        def trim_from_left(segs, offset):
            """Exclude segments whose start position is before 'offset' mm."""
            acc = 0.0
            result = []
            for seg in segs:
                start = acc
                acc += seg["length"]
                if start >= offset:   # segment starts at or beyond the joint boundary
                    result.append(seg)
            return result

        def trim_from_right(segs, offset):
            """Exclude segments whose start-from-right is before 'offset' mm."""
            return list(reversed(trim_from_left(list(reversed(segs)), offset)))

        # The calc central seg uses only the pure central length (offsets excluded).
        calc_central_seg = {
            "diameter": shaft_diameter,
            "length":   central_length,
            "shear_modulus": shear_modulus,
        }
        calc_segs = (
            trim_from_left(obj_segs, obj_offset)
            + [calc_central_seg]
            + trim_from_right(ibj_segs, ibj_offset)
        )

        if not calc_segs:
            messagebox.showerror(
                self.translator.translate("error"),
                self.translator.translate("zero_length_segment")
            )
            return

        # ── Tag every segment in all_segments with excluded=True/False ──
        # OBJ excluded = those NOT in calc_segs (start position < obj_offset)
        obj_excluded_count = len(obj_segs) - len(trim_from_left(obj_segs, obj_offset))
        ibj_excluded_count = len(ibj_segs) - len(trim_from_right(ibj_segs, ibj_offset))

        tagged_all = []
        for i, seg in enumerate(obj_segs):
            s = dict(seg)
            s["excluded"] = (i < obj_excluded_count)
            tagged_all.append(s)

        central_tagged = dict(central_seg)
        central_tagged["excluded"] = False   # central bare segment always drawn, never excluded
        tagged_all.append(central_tagged)

        for i, seg in enumerate(ibj_segs):
            s = dict(seg)
            # IBJ excluded segments are the ones at the END of the list (outermost right)
            s["excluded"] = (i >= len(ibj_segs) - ibj_excluded_count)
            tagged_all.append(s)

        calc = Calculator()
        total_stiffness = calc.calculate_torsional_stiffness(calc_segs)
        natural_freqs   = calc.calculate_natural_frequencies(calc_segs)
        shaft_mass_kg   = calc.calculate_mass(calc_segs)

        self.stiffness_value_var.set(f"{total_stiffness:.4f}")
        self.freq_value_var.set(f"{natural_freqs[0]:.2f}")
        self.mass_value_var.set(f"{shaft_mass_kg:.3f}")
        self.draw_shaft(all_segments, obj_offset=obj_offset, ibj_offset=ibj_offset)

        self.last_calculation_data = {
            "project_name":          self.project_name_entry.get(),
            "engineer":              self.engineer_entry.get(),
            "segments":              [dict(s) for s in calc_segs],
            "all_segments":          tagged_all,
            "obj_offset":            obj_offset,
            "ibj_offset":            ibj_offset,
            "total_stiffness":       total_stiffness,
            "natural_frequencies":   natural_freqs,
            "shaft_mass_kg":         shaft_mass_kg,
            "obj_joint_name":        obj_joint_name,
            "ibj_joint_name":        ibj_joint_name,
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
        if self._last_drawn_segments is not None:
            segs, kw = self._last_drawn_segments
            self.draw_shaft(segs, **kw)
        else:
            self.draw_shaft(None)

    def draw_shaft(self, segments=None, obj_offset=0.0, ibj_offset=0.0):
        # Persist segments so that resize/expose can redraw them
        if segments is not None:
            self._last_drawn_segments = (segments, {
                "obj_offset": obj_offset,
                "ibj_offset": ibj_offset,
            })
        elif self._last_drawn_segments is not None:
            segments, kw = self._last_drawn_segments
            obj_offset = kw.get("obj_offset", 0.0)
            ibj_offset = kw.get("ibj_offset", 0.0)

        self.canvas.update_idletasks()
        self.canvas.delete("all")
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w <= 1 or h <= 1:
            return

        pad_x = 60
        pad_y = 20
        mid_y  = h / 2

        if not segments:
            self._draw_shaft_shape(None, w, h, mid_y, pad_x, pad_y, 0.0, 0.0)
            return

        total_length = sum(s["length"] for s in segments)
        if total_length == 0:
            return

        self._draw_shaft_shape(segments, w, h, mid_y, pad_x, pad_y, obj_offset, ibj_offset)

    # ------------------------------------------------------------------
    def _draw_shaft_shape(self, segments, w, h, mid_y, pad_x, pad_y,
                          obj_offset=0.0, ibj_offset=0.0):
        """
        Draws the shaft as a single continuous silhouette.
        P11 is at obj_offset mm from the LEFT end of the shaft.
        P18 is at ibj_offset mm from the RIGHT end of the shaft.
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
            p11_x = seg_xs[0] + (avail_w * 0.15)   # placeholder: ~15% from left
            p18_x = seg_xs[-1] - (avail_w * 0.15)  # placeholder: ~15% from right
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

        # ── Labels: diameters centred inside each band; lengths alternating above/below ──
        # Find the tallest half-height for top/bottom bounds
        max_hh = max(half_hs) if half_hs else 1
        lbl_above_y = mid_y - max_hh - 14   # fixed row above the tallest bar
        lbl_below_y = mid_y + max_hh + 14   # fixed row below the tallest bar

        # Half-height of a font-10 character (~7 px) used to offset diameter labels
        DIAM_HALF_H = 7

        for i, seg in enumerate(segments):
            cx = (xs[i] + xs[i + 1]) / 2
            hh = half_hs[i]
            seg_w_px = xs[i + 1] - xs[i]

            # Diameter — centred inside the band, alternating slightly up/down
            diam_y = mid_y - DIAM_HALF_H if i % 2 == 0 else mid_y + DIAM_HALF_H
            self.canvas.create_text(
                cx, diam_y,
                text=f"Ø{seg['diameter']:.1f}",
                fill="#c8ddf0", font=("Arial", 10, "bold"),
                angle=0
            )

            # Length — alternating above / below the whole shaft silhouette
            if i % 2 == 0:
                self.canvas.create_text(
                    cx, lbl_above_y,
                    text=f"{seg['length']:.1f}",
                    fill="#a0c8e0", font=("Arial", 10)
                )
                # short tick from label down to top edge of THIS segment
                self.canvas.create_line(
                    cx, lbl_above_y + 7, cx, mid_y - hh,
                    fill="#4a6a7c", width=1, dash=(2, 2)
                )
            else:
                self.canvas.create_text(
                    cx, lbl_below_y,
                    text=f"{seg['length']:.1f}",
                    fill="#a0c8e0", font=("Arial", 10)
                )
                self.canvas.create_line(
                    cx, mid_y + hh, cx, lbl_below_y - 7,
                    fill="#4a6a7c", width=1, dash=(2, 2)
                )

        # ── Markers P11 / P18 ───────────────────────────────────────────
        # P11 at obj_offset mm from the LEFT end of the shaft.
        # P18 at ibj_offset mm from the RIGHT end of the shaft.
        total_len_draw = sum(s["length"] for s in segments)
        if total_len_draw > 0:
            p11_x   = pad_x + obj_offset * scale_x
            p18_x   = pad_x + (total_len_draw - ibj_offset) * scale_x
            dist_mm = total_len_draw - obj_offset - ibj_offset  # = P11→P18 span
            central_bare_draw = dist_mm - obj_offset - ibj_offset  # pure shaft (no offsets)
            # Shaft diameter at the central segment (the one near the midpoint)
            mid_acc = 0.0
            shaft_diam = segments[len(segments) // 2]["diameter"]
            for seg in segments:
                mid_acc += seg["length"]
                if mid_acc >= total_len_draw / 2:
                    shaft_diam = seg["diameter"]
                    break
            centre_hh = half_hs[len(half_hs) // 2]
            self._draw_markers(p11_x, p18_x, mid_y, centre_hh, dist_mm,
                               shaft_diam, max_hh, central_bare_draw)

    # ------------------------------------------------------------------
    def _draw_markers(self, p11_x, p18_x, mid_y, shaft_half_h, dist_mm, shaft_diam,
                      max_hh=None, central_bare=None):
        """Draw P11/P18 reference lines, distance arrow, and centre-shaft label."""
        # Use max_hh (tallest segment) so markers always clear all labels
        ref_h = max_hh if max_hh is not None else shaft_half_h
        marker_top    = mid_y - ref_h - 36
        marker_bottom = mid_y + ref_h + 28

        for x, label in [(p11_x, "Joint"), (p18_x, "Joint")]:
            self.canvas.create_line(
                x, marker_top, x, marker_bottom,
                fill="#ff6060", width=1, dash=(4, 3)
            )
            self.canvas.create_text(
                x, marker_top - 9,
                text=label, fill="#ff9090", font=("Arial", 10, "bold")
            )

        # Dimension arrow between P11 and P18 — sits above the length labels row
        cx_mid  = (p11_x + p18_x) / 2
        arrow_y = mid_y - ref_h - 24
        self.canvas.create_line(
            p11_x, arrow_y, p18_x, arrow_y,
            arrow=tk.BOTH, fill="#ffcc00", width=1
        )
        dist_label = f"{dist_mm:.1f} mm" if dist_mm is not None else "__ mm"
        self.canvas.create_text(
            cx_mid, arrow_y - 9,
            text=dist_label, fill="#ffcc00", font=("Arial", 10, "bold")
        )

        # Below shaft: diameter only
        if shaft_diam is not None:
            diam_y = mid_y + ref_h + 14
            self.canvas.create_text(
                cx_mid, diam_y,
                text=f"Ø {shaft_diam:.1f} mm",
                fill="#a8d8f0", font=("Arial", 10, "bold")
            )

    # ------------------------------------------------------------------
    # Project management
    # ------------------------------------------------------------------
    def _refresh_project_list(self):
        """Populate the project combobox with all *.json files in PROJECTS_DIR."""
        names = [DEFAULT_PROJECT]
        if os.path.isdir(PROJECTS_DIR):
            for f in sorted(os.listdir(PROJECTS_DIR)):
                if f.lower().endswith(".json"):
                    stem = f[:-5]   # strip .json
                    if stem != DEFAULT_PROJECT:
                        names.append(stem)
        self.project_file_combobox["values"] = names

    def _project_path(self, name: str) -> str:
        stem = name.strip()
        if not stem:
            stem = DEFAULT_PROJECT
        if not stem.lower().endswith(".json"):
            stem = stem + ".json"
        return os.path.join(PROJECTS_DIR, stem)

    def _collect_current_state(self) -> dict:
        """Return a dict representing the current window state for saving."""
        obj_name = self.obj_type_combobox.get()
        ibj_name = self.ibj_type_combobox.get()
        mat_name = self.material_type_combobox.get()
        obj_joint = next((j for j in self.joints if j["name"] == obj_name), None)
        ibj_joint = next((j for j in self.joints if j["name"] == ibj_name), None)
        material  = next((m for m in self.materials if m["name"] == mat_name), None)
        return {
            "project_name":    self.project_name_entry.get(),
            "engineer":        self.engineer_entry.get(),
            "shaft_diameter":  self.shaft_diameter_var.get(),
            "shaft_length":    self.shaft_length_var.get(),
            "obj_joint_name":  obj_name,
            "ibj_joint_name":  ibj_name,
            "material_name":   mat_name,
            "obj_joint":       obj_joint,
            "ibj_joint":       ibj_joint,
            "material":        material,
        }

    def save_project(self):
        name = self.project_file_var.get().strip()
        if not name or name == DEFAULT_PROJECT:
            # Allow saving as New_Shaft explicitly
            pass
        path = self._project_path(name)
        data = self._collect_current_state()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self._refresh_project_list()
            messagebox.showinfo(
                self.translator.translate("project_saved_title"),
                self.translator.translate("project_saved_msg").format(name=os.path.basename(path))
            )
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao salvar projeto:\n{e}")

    def load_project(self):
        name = self.project_file_var.get().strip()
        path = self._project_path(name)
        if not os.path.isfile(path):
            messagebox.showwarning(
                self.translator.translate("project_not_found_title"),
                self.translator.translate("project_not_found_msg").format(name=name)
            )
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao ler projeto:\n{e}")
            return

        # ── Verify / reconcile OBJ joint ──────────────────────────────
        self._reconcile_joint(data.get("obj_joint"), data.get("obj_joint_name", ""))
        # ── Verify / reconcile IBJ joint ──────────────────────────────
        self._reconcile_joint(data.get("ibj_joint"), data.get("ibj_joint_name", ""))
        # ── Verify / reconcile material ───────────────────────────────
        self._reconcile_material(data.get("material"), data.get("material_name", ""))

        # Reload DB lists (may have been updated above)
        self.load_joints()
        self.load_materials()

        # ── Populate UI fields ────────────────────────────────────────
        self.project_name_entry.delete(0, "end")
        self.project_name_entry.insert(0, data.get("project_name", ""))
        self.engineer_entry.delete(0, "end")
        self.engineer_entry.insert(0, data.get("engineer", ""))
        self.shaft_diameter_var.set(data.get("shaft_diameter", "0.00"))
        self.shaft_length_var.set(data.get("shaft_length", "0.00"))

        obj_name = data.get("obj_joint_name", "")
        ibj_name = data.get("ibj_joint_name", "")
        mat_name = data.get("material_name", "")

        if obj_name in self.obj_type_combobox["values"]:
            self.obj_type_combobox.set(obj_name)
        if ibj_name in self.ibj_type_combobox["values"]:
            self.ibj_type_combobox.set(ibj_name)
        if mat_name in self.material_type_combobox["values"]:
            self.material_type_combobox.set(mat_name)
            self.update_shear_modulus()

        self.draw_shaft()

    def _reconcile_joint(self, saved_joint: dict | None, name: str):
        """Compare saved joint data against current DB; prompt to update if different."""
        if not saved_joint or not name:
            return
        db_joint = next((j for j in self.joints if j["name"] == name), None)
        if db_joint is None:
            # Joint not in DB at all — ask to add it
            ans = messagebox.askyesno(
                self.translator.translate("project_joint_missing_title"),
                self.translator.translate("project_joint_missing_msg").format(name=name)
            )
            if ans:
                self.joints.append(saved_joint)
                self._save_joints_db()
            return
        # Check for differences
        if db_joint != saved_joint:
            ans = messagebox.askyesno(
                self.translator.translate("project_joint_diff_title"),
                self.translator.translate("project_joint_diff_msg").format(name=name)
            )
            if ans:
                idx = next(i for i, j in enumerate(self.joints) if j["name"] == name)
                self.joints[idx] = saved_joint
                self._save_joints_db()

    def _reconcile_material(self, saved_mat: dict | None, name: str):
        """Compare saved material data against current DB; prompt to update if different."""
        if not saved_mat or not name:
            return
        db_mat = next((m for m in self.materials if m["name"] == name), None)
        if db_mat is None:
            ans = messagebox.askyesno(
                self.translator.translate("project_mat_missing_title"),
                self.translator.translate("project_mat_missing_msg").format(name=name)
            )
            if ans:
                self.materials.append(saved_mat)
                self._save_materials_db()
            return
        if db_mat != saved_mat:
            ans = messagebox.askyesno(
                self.translator.translate("project_mat_diff_title"),
                self.translator.translate("project_mat_diff_msg").format(name=name)
            )
            if ans:
                idx = next(i for i, m in enumerate(self.materials) if m["name"] == name)
                self.materials[idx] = saved_mat
                self._save_materials_db()

    def _save_joints_db(self):
        path = os.path.join(DATA_DIR, "joints.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.joints, f, ensure_ascii=False, indent=2)

    def _save_materials_db(self):
        path = os.path.join(DATA_DIR, "materials.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.materials, f, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------
    # Compatibility search
    # ------------------------------------------------------------------
    @staticmethod
    def _project_compatibility(current: dict, candidate: dict) -> float:
        """
        Compute a 0–100% compatibility score between two project dicts.

        Methodology (weighted average of 4 components):
          40% — joint geometry similarity  (OBJ + IBJ sections, diameter & length)
          20% — shaft diameter match
          20% — shaft length (centre-to-centre) match
          20% — material match (name + shear modulus)
        """
        def sections_similarity(a_joint: dict | None, b_joint: dict | None) -> float:
            """Mean segment-level similarity over the longer section list."""
            if a_joint is None or b_joint is None:
                return 0.0
            a_secs = [s for s in a_joint.get("sections", [])
                      if float(s.get("diameter", 0)) > 0 and float(s.get("length", 0)) > 0]
            b_secs = [s for s in b_joint.get("sections", [])
                      if float(s.get("diameter", 0)) > 0 and float(s.get("length", 0)) > 0]
            if not a_secs and not b_secs:
                return 1.0
            n = max(len(a_secs), len(b_secs))
            score = 0.0
            for i in range(n):
                if i >= len(a_secs) or i >= len(b_secs):
                    continue        # missing segment → 0 contribution
                a_d = float(a_secs[i].get("diameter", 0))
                a_l = float(a_secs[i].get("length",   0))
                b_d = float(b_secs[i].get("diameter", 0))
                b_l = float(b_secs[i].get("length",   0))
                # Diameter similarity: 1 - |Δd|/max(d)
                d_sim = 1.0 - abs(a_d - b_d) / max(a_d, b_d, 1e-9)
                # Length similarity: 1 - |Δl|/max(l)
                l_sim = 1.0 - abs(a_l - b_l) / max(a_l, b_l, 1e-9)
                score += (d_sim + l_sim) / 2.0
            return score / n

        def num_similarity(a, b) -> float:
            """Numeric closeness clamped to [0, 1]."""
            try:
                a, b = float(a), float(b)
            except (TypeError, ValueError):
                return 0.0
            if a == 0 and b == 0:
                return 1.0
            return max(0.0, 1.0 - abs(a - b) / max(abs(a), abs(b), 1e-9))

        # Joint geometry (40%)
        obj_sim = sections_similarity(
            current.get("obj_joint"), candidate.get("obj_joint")
        )
        ibj_sim = sections_similarity(
            current.get("ibj_joint"), candidate.get("ibj_joint")
        )
        joint_score = (obj_sim + ibj_sim) / 2.0

        # Shaft diameter (20%)
        diam_score = num_similarity(
            current.get("shaft_diameter", 0), candidate.get("shaft_diameter", 0)
        )

        # Shaft length (20%)
        len_score = num_similarity(
            current.get("shaft_length", 0), candidate.get("shaft_length", 0)
        )

        # Material (20%): 50% name match + 50% shear modulus match
        c_mat = current.get("material") or {}
        k_mat = candidate.get("material") or {}
        name_match  = 1.0 if c_mat.get("name") == k_mat.get("name") else 0.0
        shear_match = num_similarity(
            c_mat.get("shear_modulus", 0), k_mat.get("shear_modulus", 0)
        )
        mat_score = (name_match + shear_match) / 2.0

        total = 0.40 * joint_score + 0.20 * diam_score + 0.20 * len_score + 0.20 * mat_score
        return round(total * 100, 1)

    def open_compatibility_search(self):
        current = self._collect_current_state()

        # Scan all saved projects
        results = []
        if os.path.isdir(PROJECTS_DIR):
            for fname in sorted(os.listdir(PROJECTS_DIR)):
                if not fname.lower().endswith(".json"):
                    continue
                fpath = os.path.join(PROJECTS_DIR, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        candidate = json.load(f)
                    pct = self._project_compatibility(current, candidate)
                    results.append((pct, fname[:-5], fpath, candidate))
                except Exception:
                    continue

        if not results:
            messagebox.showinfo(
                self.translator.translate("compat_no_projects_title"),
                self.translator.translate("compat_no_projects_msg")
            )
            return

        # Sort descending
        results.sort(key=lambda x: x[0], reverse=True)

        # ── Popup window ───────────────────────────────────────────────
        popup = tk.Toplevel(self)
        popup.title(self.translator.translate("compat_title"))
        popup.resizable(True, True)
        popup.transient(self)
        popup.grab_set()

        ttk.Label(
            popup,
            text=self.translator.translate("compat_instruction"),
            font=("Arial", 10)
        ).pack(padx=12, pady=(12, 4), anchor="w")

        frame = ttk.Frame(popup)
        frame.pack(fill="both", expand=True, padx=12, pady=4)

        cols = ("pct", "name")
        tree = ttk.Treeview(frame, columns=cols, show="headings", selectmode="browse")
        tree.heading("pct",  text=self.translator.translate("compat_col_pct"))
        tree.heading("name", text=self.translator.translate("compat_col_name"))
        tree.column("pct",  width=100, anchor="center", minwidth=80)
        tree.column("name", width=480, anchor="w",      minwidth=120)

        vsb = ttk.Scrollbar(frame, orient="vertical",   command=tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        # Map iid → (fpath, candidate_data)
        item_data: dict[str, tuple] = {}
        for pct, stem, fpath, candidate in results:
            iid = tree.insert("", "end", values=(f"{pct:.1f}%", stem))
            item_data[iid] = (fpath, candidate)

        # Select first row
        if tree.get_children():
            tree.selection_set(tree.get_children()[0])

        btn_frame = ttk.Frame(popup)
        btn_frame.pack(fill="x", padx=12, pady=8)

        def do_load():
            sel = tree.selection()
            if not sel:
                return
            fpath, candidate = item_data[sel[0]]
            popup.destroy()
            # Load the selected project into the UI
            stem = os.path.basename(fpath)[:-5]
            self.project_file_var.set(stem)
            self.load_project()

        def do_cancel():
            popup.destroy()

        ttk.Button(btn_frame, text=self.translator.translate("compat_load"),
                   command=do_load, width=14).pack(side="left", padx=8)
        ttk.Button(btn_frame, text=self.translator.translate("compat_cancel"),
                   command=do_cancel, width=14).pack(side="left", padx=4)

        # Auto-fit to content; keep user able to resize freely.
        popup.update_idletasks()
        w = max(popup.winfo_reqwidth(), 500)
        h = max(popup.winfo_reqheight(), 380)
        popup.geometry(f"{w}x{h}")
        popup.minsize(400, 280)

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
        self.projects_lf.config(text=t("projects"))
        self.project_file_label.config(text=t("project_file") + ":")
        self.load_project_button.config(text=t("project_load"))
        self.save_project_button.config(text=t("project_save"))
        self.drawing_lf.config(text=t("drawing"))
        self.shaft_lf.config(text=t("shaft"))
        self.material_lf.config(text=t("material"))
        self.stiffness_lf.config(text=t("results"))
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
        self.freq_label.config(text=t("natural_frequency") + ":")
        self.mass_label.config(text=t("mass_label") + ":")
        self.manage_joints_button.config(text=t("manage_joints"))
        self.manage_materials_button.config(text=t("manage_materials"))
        self.export_stp_button.config(text=t("export_stp"))
        self.generate_report_button.config(text=t("generate_report"))
        self.compatibility_button.config(text=t("compat_button"))
        self.status_bar.config(text=f"  {t('status_version')}")

    def change_language(self, event=None):
        self.translator.set_language(self.language_combobox.get())
        self.update_ui()

    # ------------------------------------------------------------------
    # Sub-windows
    # ------------------------------------------------------------------
    def open_joint_management(self):
        win = JointManagementWindow(self, data_dir=DATA_DIR, translator=self.translator)
        win.transient(self)
        win.grab_set()
        self.wait_window(win)
        self.load_joints()

    def open_material_management(self):
        win = MaterialManagementWindow(self, data_dir=DATA_DIR, translator=self.translator)
        win.transient(self)
        win.grab_set()
        self.wait_window(win)
        self.load_materials()


if __name__ == "__main__":
    app = MainWindow()
    app.mainloop()
