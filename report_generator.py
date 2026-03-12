import math
import copy
import os
import base64
import subprocess
import sys
from datetime import datetime

from jinja2 import Environment, FileSystemLoader


class ReportGenerator:
    """Generates an HTML torsional stiffness report using a Jinja2 template."""

    def __init__(self, template_dir: str | None = None,
                 output_dir: str | None = None,
                 translator=None):
        if template_dir is None:
            template_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "templates",
            )
        if output_dir is None:
            output_dir = os.path.dirname(os.path.abspath(__file__))

        self.template_dir = template_dir
        self.output_dir = output_dir
        self.translator = translator
        self.env = Environment(loader=FileSystemLoader(template_dir))
        # Resolve assets directory (same level as this file)
        self._assets_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "assets",
        )

    def _load_banner_b64(self) -> str:
        """Return the company banner as a base64-encoded PNG data URI string."""
        banner_path = os.path.join(self._assets_dir, "empresa.png")
        try:
            with open(banner_path, "rb") as f:
                return base64.b64encode(f.read()).decode("ascii")
        except FileNotFoundError:
            return ""

    def _t(self, key: str) -> str:
        if self.translator:
            return self.translator.translate(key)
        # Sensible English fallbacks
        _fallback = {
            "report_title":          "Structural Behaviour Report",
            "report_info":           "Project Information",
            "report_drawing":        "Shaft Schematic Drawing",
            "report_table":          "Segment Calculation Table",
            "report_seg_num":        "#",
            "report_diameter":       "Diameter (mm)",
            "report_length":         "Length (mm)",
            "report_shear_modulus":  "Shear Modulus (MPa)",
            "report_seg_stiffness":  "Segment Stiffness (N·m/deg)",
            "report_total_title":    "Total Torsional Stiffness of Shaft",
            "report_total_unit":     "N·m/deg",
            "report_project_name":   "Project Name",
            "report_engineer":       "Engineer",
            "report_date":           "Generated on",
            "report_joints_info":    "Joints & Material",
            "report_obj_joint":      "OBJ Joint",
            "report_ibj_joint":      "IBJ Joint",
            "report_material_name":  "Material",
            "report_material_shear":  "Material Shear Modulus (MPa)",
            "report_chart_title":     "Torsional Stiffness Chart by Segment",
            "report_stress_strain_title": "Material Stress-Strain Curve",
            "report_stress_lbl":      "Stress σ (MPa)",
            "report_strain_lbl":      "Strain ε (mm/mm)",
            "report_yield_point":     "Yield",
            "report_ultimate_point":  "Ultimate",
            "report_operating_zone":  "Shaft Operating Zone",
            "report_tau_max":         "τ max on shaft",
            "report_tau_yield":       "τ yield (Sy/2)",
            "report_shear_stress_lbl":"Shear Stress τ (MPa)",
            "report_analysis_title":  "Operating Limits Analysis",
            "report_analysis_intro":  "The stress-strain curve above represents the mechanical behaviour of the selected material. The actual operating limits of the calculated shaft are projected onto it, allowing structural safety to be assessed.",
            "report_values_title":    "Calculated Values",
            "report_val_tau_max":     "Maximum shear stress on shaft (τ_max)",
            "report_val_tau_yield":   "Shear yield limit (τ_yield = 0.577 · Sy)",
            "report_val_sf":          "Ratio τ_yield / τ_max (at 1° of deformation)",
            "report_val_sy":          "Material normal yield strength (Sy)",
            "report_val_su":          "Material ultimate tensile strength (Su)",
            "report_val_e":           "Elastic modulus (E)",
            "report_zone_title":      "Chart Zones",
            "report_zone_green":      "Green Zone (shaded band, 0 → τ_max): shear stress that would develop in the most-loaded segment if the shaft underwent exactly 1° of elastic twist.",
            "report_zone_yellow":     "Yellow Zone (shaded band, τ_max → τ_yield): difference between the 1°-twist shear stress and the material shear yield limit.",
            "report_zone_green_line": "Green dashed line (τ_max): shear stress corresponding to 1° of torsion in the critical segment.",
            "report_zone_orange_line":"Orange dashed line (τ_yield): shear yield limit by the von Mises criterion (τ = Sy / √3).",
            "report_zone_blue_curve": "Blue curve (σ–ε): bilinear elastic-plastic behaviour of the material, with yield point (A) and ultimate strength (B).",
            "report_analysis_note":   "Note: τ_max does not represent an actual operating load. It is the shear stress that would develop in the most-loaded segment if the shaft rotated exactly 1° in the elastic range — a geometric and material reference used to position the shaft on the curve. For a real strength assessment, enter the nominal design torque.",
            "report_chart_comment":   "Segment {idx} has the lowest stiffness ({val:.2f} N·m/deg) and is the dominant element in the total result ({total:.2f} N·m/deg). In a series connection, the most flexible segment controls the overall torsional stiffness — consider increasing its diameter or reducing its length to improve the total torsional stiffness.",
            "report_conclusion_safe": "",
            "report_conclusion_danger":"",
            "report_conclusion_title": "Conclusion",
            "report_conclusion_critical_seg": "Critical segment: Segment #{idx} (Ø {d:.1f} mm × {l:.1f} mm) — this segment will be the first to reach plastic deformation under torsional load, due to its lowest torsional capacity.",
            "report_conclusion_t_elastic": "Maximum torque without plastic deformation: {t:.1f} N·m. At this torque, the critical segment reaches the shear yield limit. The corresponding elastic twist angle of the critical segment is {theta:.3f}°.",
            "report_conclusion_safe_range": "Recommended safe operating range: 0 to {hi:.1f} N·m (60% of the elastic limit, safety factor ≈ 1.67). Within this range, all segments remain in the elastic regime with adequate margin.",
            "report_conclusion_rupture": "Estimated rupture torque (ultimate): ≈ {t:.1f} N·m — extrapolated from the Su/Sy ratio. Actual value depends on stress concentration, fatigue history, and temperature.",
            "report_conclusion_sf_info": "At 1° of reference twist: τ_max = {tau_max:.2f} MPa, τ_yield = {tau_yield:.2f} MPa, ratio τ_yield/τ_max = {sf:.2f}. This ratio indicates how far the shaft geometry is from yielding at 1° of elastic twist.",
            "report_conclusion_freq_info": "Torsional natural frequencies: f₁ = {f1:.2f} Hz, f₂ = {f2:.2f} Hz, f₃ = {f3:.2f} Hz. Verify that driveline excitation frequencies (engine orders, joint angles) do not coincide with these values to avoid resonance.",
            "report_conclusion_mass_info": "Estimated shaft mass: {mass:.3f} kg (solid cylinder model, ρ = 7850 kg/m³). Consider this value when evaluating unsprung mass, balance, and inertia targets.",
            "report_not_applied":     "NOT APPLIED",
            "report_freq_chart_title":"Torsional Natural Frequencies — FRF",
            "report_freq_chart_intro":"Frequency Response Function (FRF) showing normalised amplitude vs. excitation frequency. Resonance peaks correspond to the first three torsional natural frequencies of the shaft (damping ratio ζ = 0.02). The 1st mode governs the torsional dynamic response and should be verified against driveline excitations.",
            "report_freq_mode_1":     "1st Mode",
            "report_freq_mode_2":     "2nd Mode",
            "report_freq_mode_3":     "3rd Mode",
            "report_freq_unit":       "Hz",
            "report_freq_label":      "Frequency (Hz)",
            "report_freq_amplitude_label": "Amplitude",
            "mass_label":             "Mass",
        }
        return _fallback.get(key, key)

    # ------------------------------------------------------------------
    def _build_shaft_svg(self, segments: list, obj_offset: float = 0.0, ibj_offset: float = 0.0) -> str:
        """
        Build an inline SVG that mirrors the canvas drawing exactly:
          • Colour bands + silhouette edges.
          • Diameter labels alternating up/down inside each band.
          • Length labels alternating above/below the shaft with dashed ticks.
          • P11 / P18 dashed markers + dimension arrow + shaft diameter label.
        """
        SVG_W  = 1200
        SVG_H  = 260
        pad_x  = 80
        pad_y  = 60          # vertical padding — labels live in this space
        mid_y  = SVG_H / 2
        FONT   = "Arial"
        FS     = 11          # unified font size (matches canvas size=10 visually in SVG)
        FS_B   = f'font-family="{FONT}" font-size="{FS}" font-weight="bold"'
        FS_N   = f'font-family="{FONT}" font-size="{FS}"'

        total_len = sum(s["length"] for s in segments)
        max_diam  = max(s["diameter"] for s in segments)
        if total_len == 0 or max_diam == 0:
            return ""

        avail_w = SVG_W - 2 * pad_x
        avail_h = SVG_H - 2 * pad_y
        scale_x = avail_w / total_len
        # Use HALF of avail_h so the shaft looks slender (same as canvas)
        scale_y = avail_h * 0.5 / max_diam

        palette = [
            "#1a3a5c", "#1e4570", "#224f84", "#1a3a5c",
            "#1e4570", "#224f84", "#2a6090",
            "#224f84", "#1e4570", "#1a3a5c", "#224f84",
            "#1e4570", "#1a3a5c",
        ]

        # Pre-compute x positions and half-heights
        xs      = [pad_x]
        half_hs = []
        for seg in segments:
            xs.append(xs[-1] + seg["length"] * scale_x)
            half_hs.append(seg["diameter"] * scale_y / 2)

        max_hh = max(half_hs)

        parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {SVG_W} {SVG_H}" '
            f'width="100%" height="auto" '
            f'style="background:#0d1b2a;border-radius:6px;display:block;">'
        ]

        # ── Colour bands ──────────────────────────────────────────────
        for i, seg in enumerate(segments):
            x1, x2 = xs[i], xs[i + 1]
            hh      = half_hs[i]
            fill    = palette[i % len(palette)]
            parts.append(
                f'<rect x="{x1:.2f}" y="{mid_y - hh:.2f}" '
                f'width="{x2 - x1:.2f}" height="{hh * 2:.2f}" '
                f'fill="{fill}" stroke="none"/>'
            )

        # ── Internal dividers ─────────────────────────────────────────
        for i in range(1, len(segments)):
            x   = xs[i]
            top = mid_y - max(half_hs[i - 1], half_hs[i])
            bot = mid_y + max(half_hs[i - 1], half_hs[i])
            parts.append(
                f'<line x1="{x:.2f}" y1="{top:.2f}" x2="{x:.2f}" y2="{bot:.2f}" '
                f'stroke="#4a8ac4" stroke-width="1"/>'
            )

        # ── Silhouette edges ──────────────────────────────────────────
        top_d = "M " + " L ".join(
            f"{xs[i]:.2f},{mid_y - half_hs[i]:.2f} {xs[i+1]:.2f},{mid_y - half_hs[i]:.2f}"
            for i in range(len(segments))
        )
        bot_d = "M " + " L ".join(
            f"{xs[i]:.2f},{mid_y + half_hs[i]:.2f} {xs[i+1]:.2f},{mid_y + half_hs[i]:.2f}"
            for i in range(len(segments))
        )
        for d in (top_d, bot_d):
            parts.append(f'<path d="{d}" stroke="#4a8ac4" stroke-width="1" fill="none"/>')

        # End caps
        parts.append(
            f'<line x1="{xs[0]:.2f}" y1="{mid_y - half_hs[0]:.2f}" '
            f'x2="{xs[0]:.2f}" y2="{mid_y + half_hs[0]:.2f}" stroke="#4a8ac4" stroke-width="1"/>'
        )
        parts.append(
            f'<line x1="{xs[-1]:.2f}" y1="{mid_y - half_hs[-1]:.2f}" '
            f'x2="{xs[-1]:.2f}" y2="{mid_y + half_hs[-1]:.2f}" stroke="#4a8ac4" stroke-width="1"/>'
        )

        # ── Labels ────────────────────────────────────────────────────
        DIAM_HALF_H = 7
        lbl_above_y = mid_y - max_hh - 16
        lbl_below_y = mid_y + max_hh + 16

        for i, seg in enumerate(segments):
            cx  = (xs[i] + xs[i + 1]) / 2
            hh  = half_hs[i]
            # Diameter — alternating up/down inside band
            dy  = mid_y - DIAM_HALF_H if i % 2 == 0 else mid_y + DIAM_HALF_H
            parts.append(
                f'<text x="{cx:.2f}" y="{dy + 4:.2f}" text-anchor="middle" '
                f'fill="#c8ddf0" {FS_B}>'
                f'&#216;{seg["diameter"]:.1f}</text>'
            )
            # Length — alternating above / below
            if i % 2 == 0:
                parts.append(
                    f'<text x="{cx:.2f}" y="{lbl_above_y:.2f}" text-anchor="middle" '
                    f'fill="#a0c8e0" {FS_N}>{seg["length"]:.1f}</text>'
                )
                # dashed tick down to top of this segment
                parts.append(
                    f'<line x1="{cx:.2f}" y1="{lbl_above_y + 4:.2f}" '
                    f'x2="{cx:.2f}" y2="{mid_y - hh:.2f}" '
                    f'stroke="#4a6a7c" stroke-width="1" stroke-dasharray="2 2"/>'
                )
            else:
                parts.append(
                    f'<text x="{cx:.2f}" y="{lbl_below_y + FS:.2f}" text-anchor="middle" '
                    f'fill="#a0c8e0" {FS_N}>{seg["length"]:.1f}</text>'
                )
                # dashed tick up from bottom of this segment
                parts.append(
                    f'<line x1="{cx:.2f}" y1="{mid_y + hh:.2f}" '
                    f'x2="{cx:.2f}" y2="{lbl_below_y:.2f}" '
                    f'stroke="#4a6a7c" stroke-width="1" stroke-dasharray="2 2"/>'
                )

        # ── P11 / P18 markers ─────────────────────────────────────────
        if total_len > 0:
            p11_x   = pad_x + obj_offset * scale_x
            p18_x   = pad_x + (total_len - ibj_offset) * scale_x
            dist_mm = total_len - obj_offset - ibj_offset

            marker_top = mid_y - max_hh - 36
            marker_bot = mid_y + max_hh + 28
            arrow_y    = mid_y - max_hh - 24
            cx_mid     = (p11_x + p18_x) / 2

            # Arrowhead defs
            parts.insert(1,
                '<defs>'
                '<marker id="arr" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto">'
                '<path d="M0,0 L6,3 L0,6 Z" fill="#ffcc00"/>'
                '</marker>'
                '</defs>'
            )

            for px, lbl in [(p11_x, "Joint"), (p18_x, "Joint")]:
                parts.append(
                    f'<line x1="{px:.2f}" y1="{marker_top:.2f}" '
                    f'x2="{px:.2f}" y2="{marker_bot:.2f}" '
                    f'stroke="#ff6060" stroke-width="1" stroke-dasharray="4 3"/>'
                )
                parts.append(
                    f'<text x="{px:.2f}" y="{marker_top - 4:.2f}" '
                    f'text-anchor="middle" fill="#ff9090" {FS_B}>{lbl}</text>'
                )

            # Dimension arrow
            parts.append(
                f'<line x1="{p11_x:.2f}" y1="{arrow_y:.2f}" '
                f'x2="{p18_x:.2f}" y2="{arrow_y:.2f}" '
                f'stroke="#ffcc00" stroke-width="1" '
                f'marker-start="url(#arr)" marker-end="url(#arr)"/>'
            )
            parts.append(
                f'<text x="{cx_mid:.2f}" y="{arrow_y - 4:.2f}" '
                f'text-anchor="middle" fill="#ffcc00" {FS_B}>{dist_mm:.1f} mm</text>'
            )

            # Central shaft diameter label below shaft
            shaft_diam = segments[len(segments) // 2]["diameter"]
            diam_y     = mid_y + max_hh + 16
            parts.append(
                f'<text x="{cx_mid:.2f}" y="{diam_y + FS:.2f}" '
                f'text-anchor="middle" fill="#a8d8f0" {FS_B}>'
                f'&#216; {shaft_diam:.1f} mm</text>'
            )

        parts.append("</svg>")
        return "\n".join(parts)

    # ------------------------------------------------------------------
    def _build_freq_chart_svg(
        self,
        freqs: list,        # [f1, f2, f3] in Hz
        mode_labels: list,  # ["1ª Modo", "2º Modo", "3º Modo"]
        lbl_freq: str,      # x-axis label  (Frequência / Frequency / 频率)
        lbl_amp: str,       # y-axis label  (Amplitude / Amplitude / 幅值)
    ) -> str:
        """
        Frequency Response Function (FRF) chart — Amplitude vs Frequency.

        Model: linear superposition of single-DOF receptances with damping ζ=0.02.
        For each mode k with natural frequency f_k:

            H_k(f) = 1 / sqrt((1 - r²)² + (2·ζ·r)²)   where r = f / f_k

        Total amplitude: H(f) = Σ H_k(f)

        The sweep covers from 0 to 1.35 × f_max, sampled at 800 points.
        Y-axis is linear (not log) to keep the chart intuitive.
        The three resonance peaks are annotated with their frequency values.
        """
        import math as _m

        valid_freqs = [f for f in freqs if f and f > 0.0]
        if not valid_freqs:
            return ""

        zeta   = 0.02          # damping ratio
        f_max  = max(valid_freqs)
        f_end  = f_max * 1.40
        N_PTS  = 900           # sweep resolution

        # ── Compute FRF curve ─────────────────────────────────────────
        xs_data = [f_end * i / (N_PTS - 1) for i in range(N_PTS)]
        ys_data = []
        for f in xs_data:
            h = 0.0
            for fk in valid_freqs:
                r = f / fk if fk > 0 else 0.0
                denom = _m.sqrt((1.0 - r**2)**2 + (2.0 * zeta * r)**2)
                h += 1.0 / denom if denom > 1e-9 else 50.0
            ys_data.append(h)

        amp_max = max(ys_data)
        # Cap the Y display at 2× the baseline (out-of-resonance) amplitude
        # so the chart is readable — peaks clip at chart top
        n_valid = len(valid_freqs)
        amp_base = float(n_valid)           # amplitude far from resonance ≈ n modes × 1
        amp_display = min(amp_max, amp_base * 12.0)   # generous but bounded

        # ── SVG layout ────────────────────────────────────────────────
        W, H     = 900, 360
        pad_l    = 88
        pad_r    = 24
        pad_t    = 36
        pad_b    = 58
        chart_w  = W - pad_l - pad_r
        chart_h  = H - pad_t - pad_b
        baseline = pad_t + chart_h

        def sx(f):
            return pad_l + (f / f_end) * chart_w

        def sy(a):
            clamped = min(a, amp_display)
            return pad_t + chart_h * (1.0 - clamped / amp_display)

        parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
            f'width="100%" height="auto" '
            f'style="background:#f7f9fb;border:1px solid #c5d5e8;border-radius:6px;display:block;">'
        ]

        # ── Grid ──────────────────────────────────────────────────────
        N_GRID_Y = 5
        for k in range(N_GRID_Y + 1):
            gy = pad_t + chart_h * k / N_GRID_Y
            parts.append(
                f'<line x1="{pad_l}" y1="{gy:.1f}" x2="{W - pad_r}" y2="{gy:.1f}" '
                f'stroke="#c5d5e8" stroke-width="1" stroke-dasharray="4 3"/>'
            )

        N_GRID_X = 6
        for k in range(N_GRID_X + 1):
            f_tick = f_end * k / N_GRID_X
            gx = sx(f_tick)
            parts.append(
                f'<line x1="{gx:.1f}" y1="{pad_t}" x2="{gx:.1f}" y2="{baseline}" '
                f'stroke="#c5d5e8" stroke-width="1" stroke-dasharray="4 3"/>'
            )
            parts.append(
                f'<text x="{gx:.1f}" y="{baseline + 16:.1f}" text-anchor="middle" '
                f'font-family="Arial" font-size="10" fill="#555">{f_tick:.0f}</text>'
            )

        # ── Resonance peak vertical markers (behind curve) ────────────
        peak_colours = ["#1a4b8c", "#e8a020", "#cc3322"]
        for idx, fk in enumerate(valid_freqs):
            pkx = sx(fk)
            col = peak_colours[idx % len(peak_colours)]
            parts.append(
                f'<line x1="{pkx:.1f}" y1="{pad_t}" x2="{pkx:.1f}" y2="{baseline}" '
                f'stroke="{col}" stroke-width="1.2" stroke-dasharray="5 3" stroke-opacity="0.7"/>'
            )

        # ── Filled area under FRF curve ───────────────────────────────
        # Build polygon: left-baseline → all curve points (clamped) → right-baseline
        poly_pts = f"{sx(xs_data[0]):.1f},{baseline}"
        for i, (f, a) in enumerate(zip(xs_data, ys_data)):
            poly_pts += f" {sx(f):.1f},{sy(a):.1f}"
        poly_pts += f" {sx(xs_data[-1]):.1f},{baseline}"
        parts.append(
            f'<polygon points="{poly_pts}" fill="#2a6090" fill-opacity="0.12"/>'
        )

        # ── FRF line ──────────────────────────────────────────────────
        line_pts = " ".join(f"{sx(f):.1f},{sy(a):.1f}" for f, a in zip(xs_data, ys_data))
        parts.append(
            f'<polyline points="{line_pts}" fill="none" stroke="#1a3a5c" '
            f'stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>'
        )

        # ── Axes ──────────────────────────────────────────────────────
        parts.append(
            f'<line x1="{pad_l}" y1="{pad_t}" x2="{pad_l}" y2="{baseline}" '
            f'stroke="#1a3a5c" stroke-width="2"/>'
        )
        parts.append(
            f'<line x1="{pad_l}" y1="{baseline}" x2="{W - pad_r}" y2="{baseline}" '
            f'stroke="#1a3a5c" stroke-width="2"/>'
        )

        # ── Axis titles ───────────────────────────────────────────────
        cy_t = pad_t + chart_h / 2
        parts.append(
            f'<text transform="rotate(-90,14,{cy_t:.1f})" '
            f'x="14" y="{cy_t:.1f}" text-anchor="middle" '
            f'font-family="Arial" font-size="11" fill="#1a3a5c" font-weight="bold">'
            f'{lbl_amp}</text>'
        )
        cx_x = pad_l + chart_w / 2
        parts.append(
            f'<text x="{cx_x:.1f}" y="{H - 8}" text-anchor="middle" '
            f'font-family="Arial" font-size="11" fill="#1a3a5c" font-weight="bold">'
            f'{lbl_freq}</text>'
        )

        # ── Peak annotations ──────────────────────────────────────────
        lbl_offset_y = [pad_t + 20, pad_t + 36, pad_t + 52]   # stagger vertically
        for idx, fk in enumerate(valid_freqs):
            pkx = sx(fk)
            col = peak_colours[idx % len(peak_colours)]
            lbl_mode = mode_labels[idx] if idx < len(mode_labels) else f"f{idx+1}"
            lbl_text = f"{lbl_mode}: {fk:.2f} Hz"
            # Dot at chart-top where the peak clip starts
            peak_dot_y = sy(amp_display * 0.98)
            parts.append(
                f'<circle cx="{pkx:.1f}" cy="{peak_dot_y:.1f}" r="5" '
                f'fill="{col}" stroke="#fff" stroke-width="1.5"/>'
            )
            # Label box placed at staggered heights to avoid overlap
            lby = lbl_offset_y[idx % len(lbl_offset_y)]
            parts.append(
                f'<rect x="{pkx - 58:.1f}" y="{lby - 13:.1f}" width="116" height="18" '
                f'rx="4" fill="white" fill-opacity="0.85" stroke="{col}" stroke-width="1"/>'
            )
            parts.append(
                f'<text x="{pkx:.1f}" y="{lby:.1f}" text-anchor="middle" '
                f'font-family="Arial" font-size="11" font-weight="bold" fill="{col}">'
                f'{lbl_text}</text>'
            )

        # ── ζ annotation (top-right) ──────────────────────────────────
        parts.append(
            f'<text x="{W - pad_r - 6}" y="{pad_t + 14}" text-anchor="end" '
            f'font-family="Arial" font-size="10" fill="#888" font-style="italic">'
            f'&#950; = {zeta}</text>'
        )

        parts.append("</svg>")
        return "\n".join(parts)

    # ------------------------------------------------------------------
    def _build_chart_svg(self, segments: list, lbl_seg: str, lbl_unit: str) -> str:
        """
        Build an inline SVG line chart of torsional stiffness per segment.
        Segments must already have a 'stiffness' and 'index' key.
        """
        n = len(segments)
        if n == 0:
            return ""

        values = [s["stiffness"] for s in segments]
        # Guard against infinite stiffness (zero-length segments)
        finite = [v for v in values if v != float("inf")]
        if not finite:
            return ""
        max_val = max(finite) if finite else 1.0
        if max_val == 0:
            max_val = 1.0

        # Layout constants
        W       = 900
        H       = 320
        pad_l   = 88    # left  (y-axis labels)
        pad_r   = 20
        pad_t   = 30    # top
        pad_b   = 56    # bottom (x-axis labels)
        chart_w = W - pad_l - pad_r
        chart_h = H - pad_t - pad_b

        # Nice round grid max
        import math as _math
        magnitude = 10 ** _math.floor(_math.log10(max_val)) if max_val > 0 else 1
        grid_max  = _math.ceil(max_val / magnitude) * magnitude
        grid_step = grid_max / 5

        baseline = pad_t + chart_h

        def y_for(val):
            if val == float("inf"):
                val = grid_max
            return pad_t + chart_h * (1 - min(val, grid_max) / grid_max)

        # X center for each segment (evenly spaced)
        def cx_for(i):
            return pad_l + (i + 0.5) * (chart_w / n)

        parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
            f'width="100%" height="auto" '
            f'style="background:#f7f9fb;border:1px solid #c5d5e8;border-radius:6px;display:block;">'
        ]

        # ── Grid lines + Y-axis labels ──────────────────────────────────
        for i in range(6):
            gv  = grid_step * i
            gy  = y_for(gv)
            lbl = f"{gv:.4g}"
            parts.append(
                f'<line x1="{pad_l}" y1="{gy:.1f}" x2="{W - pad_r}" y2="{gy:.1f}" '
                f'stroke="#c5d5e8" stroke-width="1" stroke-dasharray="4 3"/>'
            )
            parts.append(
                f'<text x="{pad_l - 6}" y="{gy + 4:.1f}" text-anchor="end" '
                f'font-family="Arial" font-size="10" fill="#555">{lbl}</text>'
            )

        # ── Axes ───────────────────────────────────────────────────────
        # Y axis
        parts.append(
            f'<line x1="{pad_l}" y1="{pad_t}" x2="{pad_l}" y2="{baseline}" '
            f'stroke="#1a3a5c" stroke-width="2"/>'
        )
        # X axis
        parts.append(
            f'<line x1="{pad_l}" y1="{baseline}" '
            f'x2="{W - pad_r}" y2="{baseline}" '
            f'stroke="#1a3a5c" stroke-width="2"/>'
        )

        # ── Y-axis title (rotated) ──────────────────────────────────────
        cx_title = 14
        cy_title = pad_t + chart_h / 2
        parts.append(
            f'<text transform="rotate(-90,{cx_title},{cy_title:.1f})" '
            f'x="{cx_title}" y="{cy_title:.1f}" text-anchor="middle" '
            f'font-family="Arial" font-size="11" fill="#1a3a5c" font-weight="bold">'
            f'{lbl_unit}</text>'
        )

        # Collect (cx, cy) for each segment
        points = []
        for i, seg in enumerate(segments):
            val = seg["stiffness"] if seg["stiffness"] != float("inf") else grid_max
            points.append((cx_for(i), y_for(val), val))

        # ── Filled area under the line ──────────────────────────────────
        # Polygon: left baseline → all data points → right baseline → close
        poly_pts = (
            f"{pad_l},{baseline} "
            + " ".join(f"{cx:.1f},{cy:.1f}" for cx, cy, _ in points)
            + f" {W - pad_r},{baseline}"
        )
        parts.append(
            f'<polygon points="{poly_pts}" '
            f'fill="#2a6090" fill-opacity="0.18"/>'
        )

        # ── Polyline connecting all data points ─────────────────────────
        line_pts = " ".join(f"{cx:.1f},{cy:.1f}" for cx, cy, _ in points)
        parts.append(
            f'<polyline points="{line_pts}" '
            f'fill="none" stroke="#1a3a5c" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>'
        )

        # ── Dots, value labels, and X-axis segment labels ───────────────
        for i, (cx, cy, val) in enumerate(points):
            seg = segments[i]
            val_lbl = f"{val:.3g}"

            # Dot marker
            parts.append(
                f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="5" '
                f'fill="#224f84" stroke="#fff" stroke-width="1.5"/>'
            )
            # Value label above dot
            lbl_y = cy - 10
            if lbl_y < pad_t + 12:
                lbl_y = cy + 18   # push below dot if too close to top
            parts.append(
                f'<text x="{cx:.1f}" y="{lbl_y:.1f}" '
                f'text-anchor="middle" font-family="Arial" font-size="9" '
                f'fill="#1a3a5c" font-weight="bold">{val_lbl}</text>'
            )
            # X-axis segment label
            parts.append(
                f'<text x="{cx:.1f}" y="{baseline + 16:.1f}" '
                f'text-anchor="middle" font-family="Arial" font-size="10" fill="#333">'
                f'{lbl_seg} {seg["index"]}</text>'
            )

        parts.append("</svg>")
        return "\n".join(parts)

    # ------------------------------------------------------------------
    def _build_stress_strain_svg(
        self,
        elastic_modulus_mpa: float,
        yield_strength_mpa: float,
        ultimate_strength_mpa: float,
        material_name: str,
        tau_max_mpa: float,
        lbl_stress: str,
        lbl_strain: str,
        lbl_yield: str,
        lbl_ultimate: str,
        lbl_operating_zone: str,
        lbl_tau_max: str,
        lbl_tau_yield: str,
        lbl_shear_stress: str,
    ) -> str:
        """
        Build an inline SVG showing:
          • Bilinear elastic-plastic stress-strain curve (normal stress σ axis)
          • Overlaid shear stress axis (τ = σ/2 by von Mises) on the right
          • Operating zone of the shaft:
              - τ_yield = Sy / 2  (maximum safe shear stress)
              - τ_max   = maximum torsional shear stress in the shaft at rated load
          Both limits are projected as horizontal bands on the curve.
        """
        E   = elastic_modulus_mpa
        Sy  = yield_strength_mpa
        Su  = ultimate_strength_mpa

        if E <= 0 or Sy <= 0 or Su <= 0:
            return ""

        import math as _math

        # ── Key strain / stress points ─────────────────────────────────
        eps_y  = Sy / E
        # Strain hardening slope ≈ 5 % of E  →  eps_u
        eps_u  = eps_y + (Su - Sy) / (0.05 * E)
        eps_f  = eps_u * 1.25                   # fracture strain
        sig_f  = Su * 0.60                      # fracture stress

        pts = [
            (0.0,   0.0),
            (eps_y, Sy),
            (eps_u, Su),
            (eps_f, sig_f),
        ]

        # ── Shear limits (von Mises: τ_y = Sy/√3 ≈ 0.577·Sy) ────────
        tau_yield = Sy * 0.577          # MPa — shear yield strength
        # tau_max_mpa already passed in (computed outside)

        # ── Layout ────────────────────────────────────────────────────
        W, H    = 900, 380
        pad_l   = 90
        pad_r   = 90    # room for right τ axis labels
        pad_t   = 50
        pad_b   = 60
        chart_w = W - pad_l - pad_r
        chart_h = H - pad_t - pad_b

        max_eps = eps_f * 1.10
        max_sig = Su  * 1.20

        def px(eps): return pad_l + (eps / max_eps) * chart_w
        def py(sig): return pad_t + chart_h * (1 - sig / max_sig)

        parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
            f'width="100%" height="auto" '
            f'style="background:#f7f9fb;border:1px solid #c5d5e8;border-radius:6px;display:block;">'
        ]

        # ── Grid lines ────────────────────────────────────────────────
        n_x, n_y = 5, 5
        for i in range(n_y + 1):
            sv  = max_sig * i / n_y
            gy  = py(sv)
            parts.append(
                f'<line x1="{pad_l}" y1="{gy:.1f}" x2="{W-pad_r}" y2="{gy:.1f}" '
                f'stroke="#dce8f5" stroke-width="1" stroke-dasharray="4 3"/>'
            )
            parts.append(
                f'<text x="{pad_l-6}" y="{gy+4:.1f}" text-anchor="end" '
                f'font-family="Arial" font-size="10" fill="#555">{sv:.0f}</text>'
            )
            # Right axis: τ = σ * 0.577
            tau_lbl = sv * 0.577
            parts.append(
                f'<text x="{W-pad_r+6}" y="{gy+4:.1f}" text-anchor="start" '
                f'font-family="Arial" font-size="10" fill="#2a7a2a">{tau_lbl:.0f}</text>'
            )
        for i in range(n_x + 1):
            ev  = max_eps * i / n_x
            gx  = px(ev)
            parts.append(
                f'<line x1="{gx:.1f}" y1="{pad_t}" x2="{gx:.1f}" y2="{pad_t+chart_h}" '
                f'stroke="#dce8f5" stroke-width="1" stroke-dasharray="4 3"/>'
            )
            parts.append(
                f'<text x="{gx:.1f}" y="{pad_t+chart_h+18}" text-anchor="middle" '
                f'font-family="Arial" font-size="10" fill="#555">{ev:.4f}</text>'
            )

        # ── Axes ──────────────────────────────────────────────────────
        parts.append(
            f'<line x1="{pad_l}" y1="{pad_t}" x2="{pad_l}" y2="{pad_t+chart_h}" '
            f'stroke="#1a3a5c" stroke-width="2"/>'
        )
        parts.append(
            f'<line x1="{pad_l}" y1="{pad_t+chart_h}" x2="{W-pad_r}" y2="{pad_t+chart_h}" '
            f'stroke="#1a3a5c" stroke-width="2"/>'
        )
        # Right τ axis
        parts.append(
            f'<line x1="{W-pad_r}" y1="{pad_t}" x2="{W-pad_r}" y2="{pad_t+chart_h}" '
            f'stroke="#2a7a2a" stroke-width="1.5"/>'
        )

        # ── Axis titles ───────────────────────────────────────────────
        # Left Y: σ
        parts.append(
            f'<text transform="rotate(-90,14,{pad_t+chart_h/2:.0f})" '
            f'x="14" y="{pad_t+chart_h/2:.0f}" text-anchor="middle" '
            f'font-family="Arial" font-size="11" fill="#1a3a5c" font-weight="bold">'
            f'{lbl_stress}</text>'
        )
        # Right Y: τ
        parts.append(
            f'<text transform="rotate(90,{W-14},{pad_t+chart_h/2:.0f})" '
            f'x="{W-14}" y="{pad_t+chart_h/2:.0f}" text-anchor="middle" '
            f'font-family="Arial" font-size="11" fill="#2a7a2a" font-weight="bold">'
            f'{lbl_shear_stress}</text>'
        )
        # X
        parts.append(
            f'<text x="{pad_l+chart_w/2:.0f}" y="{H-8}" text-anchor="middle" '
            f'font-family="Arial" font-size="11" fill="#1a3a5c" font-weight="bold">'
            f'{lbl_strain}</text>'
        )

        # ── Operating zone overlay ────────────────────────────────────
        # τ_max = shear stress that would develop under 1° of elastic twist.
        # This is a material-position indicator, NOT a load simulation.
        # We always show both lines regardless of which is larger, clamping
        # tau_max to the chart area if it exceeds the visible scale.
        if tau_max_mpa > 0 and tau_yield > 0:
            sig_tau_max   = min(tau_max_mpa / 0.577, max_sig * 0.97)
            sig_tau_yield = tau_yield / 0.577        # = Sy (always visible)

            y_zone_bot = py(0)
            y_tm = py(sig_tau_max)
            y_ty = py(sig_tau_yield)

            # Green band: 0 → τ_max (shear stress range per 1° twist)
            parts.append(
                f'<rect x="{pad_l}" y="{y_tm:.1f}" '
                f'width="{chart_w}" height="{y_zone_bot - y_tm:.1f}" '
                f'fill="#22bb44" fill-opacity="0.10"/>'
            )
            # Yellow band: τ_max → τ_yield (reference margin)
            if y_ty < y_tm:   # τ_yield line is above τ_max line on SVG
                parts.append(
                    f'<rect x="{pad_l}" y="{y_ty:.1f}" '
                    f'width="{chart_w}" height="{y_tm - y_ty:.1f}" '
                    f'fill="#ffcc00" fill-opacity="0.13"/>'
                )

            # τ_max dashed line (green)
            parts.append(
                f'<line x1="{pad_l}" y1="{y_tm:.1f}" x2="{W-pad_r}" y2="{y_tm:.1f}" '
                f'stroke="#22aa44" stroke-width="1.8" stroke-dasharray="7 4"/>'
            )
            parts.append(
                f'<text x="{pad_l+chart_w-4}" y="{y_tm-5:.1f}" text-anchor="end" '
                f'font-family="Arial" font-size="10" fill="#1a7a30" font-weight="bold">'
                f'{lbl_tau_max}: {tau_max_mpa:.1f} MPa</text>'
            )

            # τ_yield dashed line (amber)
            parts.append(
                f'<line x1="{pad_l}" y1="{y_ty:.1f}" x2="{W-pad_r}" y2="{y_ty:.1f}" '
                f'stroke="#cc8800" stroke-width="1.8" stroke-dasharray="7 4"/>'
            )
            parts.append(
                f'<text x="{pad_l+chart_w-4}" y="{y_ty-5:.1f}" text-anchor="end" '
                f'font-family="Arial" font-size="10" fill="#996600" font-weight="bold">'
                f'{lbl_tau_yield}: {tau_yield:.1f} MPa</text>'
            )

            # Zone label (top-left)
            parts.append(
                f'<text x="{pad_l+8}" y="{pad_t+20}" '
                f'font-family="Arial" font-size="11" fill="#1a7a30" font-weight="bold">'
                f'{lbl_operating_zone}</text>'
            )

        # ── Stress-strain polyline ─────────────────────────────────────
        polyline = " ".join(f"{px(e):.1f},{py(s):.1f}" for e, s in pts)
        parts.append(
            f'<polyline points="{polyline}" '
            f'fill="none" stroke="#224f84" stroke-width="2.5" stroke-linejoin="round"/>'
        )

        # ── Elastic region shading ─────────────────────────────────────
        ax1 = px(0); ay1 = py(0)
        ax2 = px(eps_y); base_y = py(0)
        parts.append(
            f'<polygon points="{ax1:.1f},{base_y:.1f} {ax1:.1f},{ay1:.1f} '
            f'{ax2:.1f},{py(Sy):.1f} {ax2:.1f},{base_y:.1f}" '
            f'fill="#2a6090" fill-opacity="0.10"/>'
        )

        # ── Yield point annotation ─────────────────────────────────────
        xA, yA = px(eps_y), py(Sy)
        parts.append(f'<circle cx="{xA:.1f}" cy="{yA:.1f}" r="5" fill="#e08000" stroke="#fff" stroke-width="1.5"/>')
        parts.append(
            f'<line x1="{xA:.1f}" y1="{pad_t}" x2="{xA:.1f}" y2="{pad_t+chart_h}" '
            f'stroke="#e08000" stroke-width="1" stroke-dasharray="5 3"/>'
        )
        parts.append(
            f'<line x1="{pad_l}" y1="{yA:.1f}" x2="{W-pad_r}" y2="{yA:.1f}" '
            f'stroke="#e08000" stroke-width="1" stroke-dasharray="5 3"/>'
        )
        parts.append(
            f'<text x="{xA+8:.1f}" y="{yA-8:.1f}" font-family="Arial" font-size="10" '
            f'fill="#b05000" font-weight="bold">'
            f'{lbl_yield}: {Sy:.0f} MPa  ε={eps_y:.4f}</text>'
        )

        # ── Ultimate strength annotation ───────────────────────────────
        xB, yB = px(eps_u), py(Su)
        parts.append(f'<circle cx="{xB:.1f}" cy="{yB:.1f}" r="5" fill="#cc2222" stroke="#fff" stroke-width="1.5"/>')
        parts.append(
            f'<line x1="{pad_l}" y1="{yB:.1f}" x2="{W-pad_r}" y2="{yB:.1f}" '
            f'stroke="#cc2222" stroke-width="1" stroke-dasharray="5 3"/>'
        )
        parts.append(
            f'<text x="{xB+8:.1f}" y="{yB-8:.1f}" font-family="Arial" font-size="10" '
            f'fill="#991111" font-weight="bold">'
            f'{lbl_ultimate}: {Su:.0f} MPa  ε={eps_u:.4f}</text>'
        )

        # ── Material name ──────────────────────────────────────────────
        parts.append(
            f'<text x="{W-pad_r-4}" y="{pad_t+16}" text-anchor="end" '
            f'font-family="Arial" font-size="11" fill="#1a3a5c" font-style="italic">'
            f'{material_name}</text>'
        )

        parts.append("</svg>")
        return "\n".join(parts)

    # ------------------------------------------------------------------
    def generate_report(self, data: dict):
        """
        Generate the HTML report and open it in the default browser.

        Args:
            data: dict with keys 'project_name', 'engineer', 'segments', 'total_stiffness'.
                  'segments' is a list of dicts with 'diameter', 'length', 'shear_modulus'.
                  The original data is NOT modified.
        """
        # Deep-copy segments so we don't mutate shared state
        # Drawing uses ALL segments (full shaft); chart/τ use only the stiffness calc_segs
        draw_segments = copy.deepcopy(data.get("all_segments", data["segments"]))
        obj_offset    = data.get("obj_offset", 0.0)
        ibj_offset    = data.get("ibj_offset", 0.0)
        shaft_svg     = self._build_shaft_svg(draw_segments, obj_offset=obj_offset, ibj_offset=ibj_offset)

        # ── Stiffness-calc segments (used for chart / τ / total K) ───────
        segments = copy.deepcopy(data["segments"])

        def _compute_stiffness(seg: dict) -> float:
            G = seg["shear_modulus"] * 1e6
            L = seg["length"] / 1000.0
            D = seg["diameter"] / 1000.0
            J = (math.pi * D ** 4) / 32.0
            if L > 0 and D > 0:
                return (G * J) / L * (math.pi / 180.0)
            return float("inf")

        for i, seg in enumerate(segments, start=1):
            seg["stiffness"] = _compute_stiffness(seg)
            seg["index"] = i

        # ── All-segments table (full shaft — excluded → "NÃO APLICADO") ─
        # all_segments already carries excluded=True/False tags set in main.py.
        # We just walk through them in order, assigning sequential indices to
        # included segments and computing their stiffness.
        all_segs_table = []
        idx = 0
        for seg in copy.deepcopy(data.get("all_segments", data["segments"])):
            if not seg.get("excluded", False):
                idx += 1
                seg["stiffness"] = _compute_stiffness(seg)
                seg["index"] = idx
            else:
                seg["stiffness"] = None
                seg["index"] = "—"
            all_segs_table.append(seg)

        lbl_not_applied = self._t("report_not_applied")

        chart_svg   = self._build_chart_svg(
            segments,
            lbl_seg  = self._t("report_seg_num"),
            lbl_unit = self._t("report_seg_stiffness"),
        )

        # ── Natural frequency chart ────────────────────────────────────
        natural_freqs = data.get("natural_frequencies", [0.0, 0.0, 0.0])
        while len(natural_freqs) < 3:
            natural_freqs.append(0.0)
        freq_chart_svg = self._build_freq_chart_svg(
            freqs       = natural_freqs,
            mode_labels = [
                self._t("report_freq_mode_1"),
                self._t("report_freq_mode_2"),
                self._t("report_freq_mode_3"),
            ],
            lbl_freq    = self._t("report_freq_label"),
            lbl_amp     = self._t("report_freq_amplitude_label"),
        )

        # ── τ_max: highest torsional shear stress across all segments ──
        # Physics: τ = T·(D/2) / J  with T = K_rad × (π/180) at 1° twist
        #          K_rad = (G·J) / L  → τ = G·D/2 / L · (π/180)  [Pa → MPa: /1e6]
        tau_max_mpa = 0.0
        for seg in segments:
            G_pa  = seg["shear_modulus"] * 1e6        # Pa
            D_m   = seg.get("diameter", 0.0) / 1000.0 # m
            L_m   = seg.get("length",   0.0) / 1000.0 # m
            if D_m > 0 and L_m > 0:
                J_m4  = math.pi * D_m**4 / 32.0
                K_rad = (G_pa * J_m4) / L_m            # N·m/rad
                T_nm  = K_rad * (math.pi / 180.0)      # N·m at 1° twist
                tau   = (T_nm * (D_m / 2.0)) / J_m4 / 1e6  # MPa
                if tau > tau_max_mpa:
                    tau_max_mpa = tau

        stress_strain_svg = self._build_stress_strain_svg(
            elastic_modulus_mpa   = data.get("elastic_modulus_mpa",   0.0),
            yield_strength_mpa    = data.get("yield_strength_mpa",    0.0),
            ultimate_strength_mpa = data.get("ultimate_strength_mpa", 0.0),
            material_name         = data.get("material_name", ""),
            tau_max_mpa           = tau_max_mpa,
            lbl_stress            = self._t("report_stress_lbl"),
            lbl_strain            = self._t("report_strain_lbl"),
            lbl_yield             = self._t("report_yield_point"),
            lbl_ultimate          = self._t("report_ultimate_point"),
            lbl_operating_zone    = self._t("report_operating_zone"),
            lbl_tau_max           = self._t("report_tau_max"),
            lbl_tau_yield         = self._t("report_tau_yield"),
            lbl_shear_stress      = self._t("report_shear_stress_lbl"),
        )

        # ── Analysis card values ───────────────────────────────────────
        Sy   = data.get("yield_strength_mpa",    0.0)
        Su   = data.get("ultimate_strength_mpa", 0.0)
        E    = data.get("elastic_modulus_mpa",   0.0)
        tau_yield_mpa = Sy * 0.577
        # SF here is purely a geometric/material ratio for reference.
        # tau_max is NOT a load — it is the shear stress that would develop
        # in the most-loaded segment if the shaft twisted exactly 1°.
        # It positions the shaft geometry on the stress-strain curve, showing
        # how stiff (and therefore how stressed per degree) the shaft is.
        sf_val = (tau_yield_mpa / tau_max_mpa) if tau_max_mpa > 0 else 0.0

        # SF colour: purely informational gradient (no pass/fail meaning)
        if sf_val >= 2.0:
            sf_colour = "#1a7a30"   # green  — large margin
        elif sf_val >= 1.0:
            sf_colour = "#cc8800"   # amber  — moderate margin
        else:
            sf_colour = "#888888"   # grey   — ratio < 1 (not a failure indicator)

        analysis_note = self._t("report_analysis_note")

        # ── Chart comment: identify weakest segment ────────────────────
        total_stiffness = data.get("total_stiffness", 0.0)
        finite_segs = [
            (s["index"], s["stiffness"])
            for s in segments
            if s["stiffness"] != float("inf") and s["stiffness"] > 0
        ]
        if finite_segs:
            weakest = min(finite_segs, key=lambda x: x[1])
            chart_comment = self._t("report_chart_comment").format(
                idx=weakest[0],
                val=weakest[1],
                total=total_stiffness,
            )
        else:
            chart_comment = ""

        # ── Conclusion block ───────────────────────────────────────────
        # Identify the critical segment (lowest individual stiffness → first
        # to reach plastic deformation under torsion).
        # For each included segment compute the torque T_yield_i [N·m] that
        # would cause the segment's shear stress to reach τ_yield:
        #   τ_yield  = 0.577 · Sy
        #   τ_i(T)   = T · (D_i/2) / J_i  →  T_yield_i = τ_yield · J_i / (D_i/2)
        # The segment with the smallest T_yield_i is the first to fail.
        # T_elastic_max  = minimum T_yield_i across all included segments.
        # Recommended safe range = [0, 0.6 · T_elastic_max] (SF ≈ 1.67).

        T_yield_per_seg = []   # (seg_index, T_yield_Nm, diameter_mm, length_mm)
        for seg in segments:
            D_m = seg.get("diameter", 0.0) / 1000.0
            L_m = seg.get("length",   0.0) / 1000.0
            if D_m <= 0 or L_m <= 0:
                continue
            J_m4      = math.pi * D_m**4 / 32.0
            tau_y_pa  = Sy * 0.577 * 1e6           # Pa
            T_yield_i = tau_y_pa * J_m4 / (D_m / 2.0)  # N·m
            T_yield_per_seg.append((seg["index"], T_yield_i,
                                    seg.get("diameter", 0.0),
                                    seg.get("length",   0.0)))

        if T_yield_per_seg and Sy > 0:
            crit = min(T_yield_per_seg, key=lambda x: x[1])
            crit_idx, T_elastic_max, crit_D, crit_L = crit
            T_safe_lo = 0.0
            T_safe_hi = 0.60 * T_elastic_max    # 40 % safety margin
            T_rupture = (Su / Sy) * T_elastic_max if Sy > 0 else 0.0

            # Angle at yield for the critical segment (θ = T·L / (G·J))
            # Use G from the critical segment's data
            crit_seg_data = next(
                (s for s in segments if s["index"] == crit_idx), None
            )
            if crit_seg_data:
                G_pa     = crit_seg_data["shear_modulus"] * 1e6
                D_m_c    = crit_D / 1000.0
                L_m_c    = crit_L / 1000.0
                J_m4_c   = math.pi * D_m_c**4 / 32.0
                theta_yield_rad = (T_elastic_max * L_m_c) / (G_pa * J_m4_c)
                theta_yield_deg = math.degrees(theta_yield_rad)
            else:
                theta_yield_deg = 0.0

            conclusion_items = [
                {
                    "icon": "⚠️",
                    "colour": "#c0392b",
                    "label": self._t("report_conclusion_critical_seg").format(
                        idx=crit_idx,
                        d=crit_D,
                        l=crit_L,
                    ),
                },
                {
                    "icon": "🔩",
                    "colour": "#1a4b8c",
                    "label": self._t("report_conclusion_t_elastic").format(
                        t=T_elastic_max,
                        theta=theta_yield_deg,
                    ),
                },
                {
                    "icon": "✅",
                    "colour": "#1a7a30",
                    "label": self._t("report_conclusion_safe_range").format(
                        lo=T_safe_lo,
                        hi=T_safe_hi,
                    ),
                },
                {
                    "icon": "💥",
                    "colour": "#8B0000",
                    "label": self._t("report_conclusion_rupture").format(
                        t=T_rupture,
                    ),
                },
                {
                    "icon": "📐",
                    "colour": "#6d4c41",
                    "label": self._t("report_conclusion_sf_info").format(
                        sf=sf_val,
                        tau_max=tau_max_mpa,
                        tau_yield=tau_yield_mpa,
                    ),
                },
                {
                    "icon": "🎵",
                    "colour": "#4a235a",
                    "label": self._t("report_conclusion_freq_info").format(
                        f1=natural_freqs[0],
                        f2=natural_freqs[1],
                        f3=natural_freqs[2],
                    ),
                },
                {
                    "icon": "⚖️",
                    "colour": "#2c3e50",
                    "label": self._t("report_conclusion_mass_info").format(
                        mass=data.get("shaft_mass_kg", 0.0),
                    ),
                },
            ]
            conclusion_available = True
        else:
            conclusion_items     = []
            conclusion_available = False

        template_data = {
            "project_name":        data.get("project_name", ""),
            "engineer":            data.get("engineer", ""),
            "segments":            segments,
            "all_segs_table":      all_segs_table,
            "lbl_not_applied":     lbl_not_applied,
            "total_stiffness":     data.get("total_stiffness", 0.0),
            "shaft_svg":           shaft_svg,
            "chart_svg":           chart_svg,
            "chart_comment":       chart_comment,
            "freq_chart_svg":      freq_chart_svg,
            "natural_freqs":       natural_freqs,
            "shaft_mass_kg":       data.get("shaft_mass_kg", 0.0),
            "lbl_mass":            self._t("mass_label"),
            "stress_strain_svg":   stress_strain_svg,
            "company_banner_b64":  self._load_banner_b64(),
            "generated_on":        datetime.now().strftime("%d/%m/%Y  %H:%M"),
            # i18n strings for the template
            "lbl_title":           self._t("report_title"),
            "lbl_info":            self._t("report_info"),
            "lbl_drawing":         self._t("report_drawing"),
            "lbl_table":           self._t("report_table"),
            "lbl_seg_num":         self._t("report_seg_num"),
            "lbl_diameter":        self._t("report_diameter"),
            "lbl_length":          self._t("report_length"),
            "lbl_shear_modulus":   self._t("report_shear_modulus"),
            "lbl_seg_stiffness":   self._t("report_seg_stiffness"),
            "lbl_total_title":     self._t("report_total_title"),
            "lbl_total_unit":      self._t("report_total_unit"),
            "lbl_project_name":    self._t("report_project_name"),
            "lbl_engineer":        self._t("report_engineer"),
            "lbl_date":            self._t("report_date"),
            "lbl_joints_info":     self._t("report_joints_info"),
            "lbl_obj_joint":       self._t("report_obj_joint"),
            "lbl_ibj_joint":       self._t("report_ibj_joint"),
            "lbl_material_name":   self._t("report_material_name"),
            "lbl_material_shear":  self._t("report_material_shear"),
            "lbl_chart_title":     self._t("report_chart_title"),
            "lbl_freq_chart_title":self._t("report_freq_chart_title"),
            "lbl_freq_chart_intro":self._t("report_freq_chart_intro"),
            "lbl_freq_mode_1":     self._t("report_freq_mode_1"),
            "lbl_freq_mode_2":     self._t("report_freq_mode_2"),
            "lbl_freq_mode_3":     self._t("report_freq_mode_3"),
            "lbl_freq_unit":       self._t("report_freq_unit"),
            "lbl_stress_strain_title": self._t("report_stress_strain_title"),
            "obj_joint_name":      data.get("obj_joint_name", ""),
            "ibj_joint_name":      data.get("ibj_joint_name", ""),
            "material_name":       data.get("material_name", ""),
            "shear_modulus":       data.get("shear_modulus", 0.0),
            # Operating limits analysis card
            "tau_max_mpa":         tau_max_mpa,
            "tau_yield_mpa":       tau_yield_mpa,
            "sf":                  sf_val,
            "sf_colour":           sf_colour,
            "mat_sy":              Sy,
            "mat_su":              Su,
            "mat_e":               E,
            "lbl_analysis_title":  self._t("report_analysis_title"),
            "lbl_analysis_intro":  self._t("report_analysis_intro"),
            "lbl_values_title":    self._t("report_values_title"),
            "lbl_val_tau_max":     self._t("report_val_tau_max"),
            "lbl_val_tau_yield":   self._t("report_val_tau_yield"),
            "lbl_val_sf":          self._t("report_val_sf"),
            "lbl_val_sy":          self._t("report_val_sy"),
            "lbl_val_su":          self._t("report_val_su"),
            "lbl_val_e":           self._t("report_val_e"),
            "lbl_zone_title":      self._t("report_zone_title"),
            "lbl_zone_green":      self._t("report_zone_green"),
            "lbl_zone_yellow":     self._t("report_zone_yellow"),
            "lbl_zone_green_line": self._t("report_zone_green_line"),
            "lbl_zone_orange_line":self._t("report_zone_orange_line"),
            "lbl_zone_blue_curve": self._t("report_zone_blue_curve"),
            "lbl_analysis_note":   analysis_note,
            # Conclusion
            "conclusion_available":    conclusion_available,
            "conclusion_items":        conclusion_items,
            "lbl_conclusion_title":    self._t("report_conclusion_title"),
        }

        template = self.env.get_template("report_template.html")
        rendered = template.render(**template_data)

        report_path = os.path.join(self.output_dir, "report.html")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(rendered)

        # Open the report exactly once in the default browser.
        # subprocess + 'start' (Windows) / 'open' (macOS) / 'xdg-open' (Linux)
        # avoids the double-open that os.startfile and webbrowser.open can cause.
        if sys.platform == "win32":
            subprocess.Popen(
                ["cmd", "/c", "start", "", report_path],
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        elif sys.platform == "darwin":
            subprocess.Popen(["open", report_path])
        else:
            subprocess.Popen(["xdg-open", report_path])
