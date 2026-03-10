# Torsional Stiffness Shaft Calculator

A desktop application for calculating the **torsional stiffness** of multi-segment shafts used in driveline and powertrain engineering. Built with Python and Tkinter, with multilingual support and HTML report generation.

---

## Features

- **Multi-segment shaft model** — define up to 13 individual shaft sections with different diameters, lengths, and materials
- **Torsional stiffness calculation** — series combination formula based on shear modulus, polar moment of inertia, and segment length
- **Graphical shaft preview** — live canvas drawing of the shaft cross-section profile with segment markers (P11/P18) and diameter labels
- **HTML report generation** — complete engineering report with inline SVG drawings, charts, and material analysis (see [Report and Charts](#report-and-charts))
- **STEP export** — exports a 3D shaft geometry via CadQuery (`.stp` file)
- **Joint management** — add, edit, and delete predefined joint types with configurable segment geometries
- **Material management** — library of 20 automotive metals with shear modulus G, elastic modulus E, yield strength Sy and ultimate strength Su
- **Multilingual UI** — Portuguese (pt_BR), English (en), and Chinese Simplified (zh)
- **Application icon and company banner** — embedded visual identity in app and report
- **Status bar** — displays app version in the currently selected language

---

## Calculation Formulas

### Segment stiffness

For each segment $i$, the torsional stiffness in N·m/degree is:

$$K_i = \frac{G_i \cdot J_i}{L_i} \cdot \frac{\pi}{180}$$

where:

| Symbol | Description | Unit |
| --- | --- | --- |
| $G_i$ | Shear modulus | Pa |
| $J_i = \pi D_i^4 / 32$ | Polar moment of inertia | m^4 |
| $L_i$ | Segment length | m |

### Total shaft stiffness (segments in series)

$$\frac{1}{K_\text{total}} = \sum_{i=1}^{n} \frac{1}{K_i}$$

Result expressed in **N·m/degree**.

### Torsional shear stress per segment

The maximum surface torsional shear stress at 1 degree of input twist is:

$$\tau_i = \frac{T_i \cdot (D_i / 2)}{J_i} \quad \text{where} \quad T_i = K_{i,\text{rad}} \cdot \frac{\pi}{180}$$

The critical (worst-case) segment is the one with the **highest** tau_i.

### Shear yield criterion (von Mises)

$$\tau_\text{yield} = \frac{S_y}{\sqrt{3}} \approx 0.577 \cdot S_y$$

### Safety factor in shear

$$SF = \frac{\tau_\text{yield}}{\tau_\text{max}}$$

---

## Requirements

| Dependency | Version |
| --- | --- |
| Python | >= 3.10 |
| tkinter | bundled with Python |
| Jinja2 | >= 3.0 |
| CadQuery | >= 2.7 |

---

## Installation

1. **Clone or copy** the project folder.

2. **Install dependencies** (Python 3.10+ must be on PATH):

   ```powershell
   pip install jinja2 cadquery
   ```

---

## Usage

Run the application directly from the project root:

```powershell
python main.py
```

### Workflow

1. Enter **Project Name** and **Engineer** in the top fields.
2. Select the **OBJ Joint** and **IBJ Joint** types from the dropdowns.
3. Enter the **shaft diameter** (mm) and **length** (mm) for the intermediate segment.
4. Select a **material** -- the shear modulus G is auto-filled from the library.
5. Click **Calcular / Calculate / 计算** to compute total torsional stiffness.
6. Optionally:
   - Click **Gerar Relatorio** to generate and open the HTML report.
   - Click **Exportar .STP** to export a STEP 3D model.
   - Use **Gerenciar Juntas / Manage Joints** to edit the joint library.
   - Use **Gerenciar Materiais / Manage Materials** to edit the material library.

---

## Report and Charts

Clicking **Gerar Relatorio** generates `report.html` and opens it in the default browser. The report is a self-contained HTML file -- all SVGs are inline, the company banner is base64-embedded -- divided into the sections below.

---

### 1 - Header and Project Information

| Field | Description |
| --- | --- |
| Company banner | `assets/empresa.png` embedded as a base64 PNG |
| Report title | Localised main heading |
| Project Name | As entered in the main window |
| Engineer | As entered in the main window |
| Generated on | Date and time of report generation (DD/MM/YYYY HH:MM) |

---

### 2 - Joints and Material

Summarises the configuration context:

| Field | Description |
| --- | --- |
| OBJ Joint | Name of the outer-body joint selected |
| IBJ Joint | Name of the inner-body joint selected |
| Material | Name of the selected material |
| Shear Modulus G | G value of the material (MPa) |

---

### 3 - Shaft Schematic Drawing (SVG)

An inline SVG (900 x 160 px, dark background) that shows the cross-section silhouette of the full shaft:

- Each segment is drawn as a **coloured rectangle** whose height is proportional to its diameter (half-scale relative to the tallest segment).
- Colour bands cycle through a palette of engineering blues (`#1a3a5c`, `#224f84`, `#2a6090`, ...).
- **Internal dividers** (light-blue vertical lines) separate adjacent segments.
- **Top and bottom silhouette edges** trace the exact stepped profile.
- **Left and right end caps** close the geometry.
- When exactly 13 segments are present, two additional annotations appear:
  - **P11 / P18 reference lines** -- dashed red vertical markers with labels identifying the standard measurement planes.
  - **Dimension arrow** -- a yellow horizontal arrow between P11 and P18 with the inter-plane distance in mm.
  - **Central diameter label** -- the diameter of the middle segment (segment 7) shown below the shaft in light blue.

---

### 4 - Segment Calculation Table

A table with one row per shaft segment:

| Column | Description |
| --- | --- |
| # | Segment index (1 to n) |
| Diameter (mm) | Cross-section diameter |
| Length (mm) | Axial length |
| Shear Modulus (MPa) | Material G for this segment |
| Segment Stiffness (N·m/deg) | Ki computed for this segment |

The **Total Torsional Stiffness** box below the table shows K_total in N·m/deg, calculated from the series formula.

---

### 5 - Torsional Stiffness Line Chart by Segment (SVG)

An inline SVG (900 × 320 px, light background) line chart comparing individual segment stiffness values:

- **Filled area** under the line (semi-transparent blue) gives immediate visual weight to the overall stiffness profile.
- **Polyline** (dark blue) connects all segment data points.
- **Circle dot markers** (r = 5, white border) sit at each data point.
- **Stiffness value** printed above each dot (or below if close to the top edge).
- One **X-axis label per segment** — "# 1", "# 2", ... evenly spaced.
- **Y axis** — stiffness in N·m/deg; scale rounded to a sensible magnitude automatically.
- **Grid lines** (light-blue dashed horizontals) at 6 evenly-spaced levels.
- Segments with zero length or zero diameter (Ki = ∞) are excluded from the scale and rendered at the grid ceiling.

Below the chart a **highlighted comment** identifies the weakest segment (lowest stiffness), its value, and the total shaft stiffness, explaining its dominant role in the series combination and suggesting design improvement actions. The text is shown in the currently selected language (pt_BR / en / zh).

> **Purpose:** Immediately shows which segment is the design bottleneck and by how much it dominates the total compliance.

---

### 6 - Material Stress-Strain Curve (SVG)

An inline SVG (900 x 380 px) showing the bilinear elastic-plastic model of the selected material, with the operating limits of the calculated shaft projected onto the curve.

#### 6.1 - Stress-strain curve (sigma-epsilon)

The curve uses a **bilinear elastic-plastic** model with four key points:

| Point | Strain epsilon | Stress sigma | Description |
| --- | --- | --- | --- |
| O | 0 | 0 | Origin |
| A | Sy / E | Sy | Yield point |
| B | epsilon_y + (Su - Sy) / (0.05 * E) | Su | Ultimate strength |
| C | epsilon_B x 1.25 | 0.60 * Su | Fracture (simplified necking drop) |

- **Blue polyline** (O to A to B to C) traces the stress-strain path.
- **Blue-shaded triangle** under the O-A segment represents the elastic strain energy density.
- **Orange dot + crosshairs** at point A annotate the yield point (Sy in MPa and epsilon_y value).
- **Red dot + horizontal line** at point B annotate the ultimate strength (Su in MPa and epsilon_u value).
- Material name printed in italic in the top-right corner of the chart.

#### 6.2 - Dual Y axes

| Axis | Side | Colour | Scale |
| --- | --- | --- | --- |
| Normal stress sigma (MPa) | Left | Dark blue | 0 to 1.20 * Su |
| Shear stress tau (MPa) | Right | Green | tau = sigma * 0.577 (von Mises) |

Both axes share the same grid lines. The right axis re-labels each gridline in shear stress units so the engineer can read tau directly.

#### 6.3 - Shaft operating zone overlay

The chart overlays the actual torsional shear stress of the shaft at 1 degree of input twist:

| Element | Colour | Meaning |
| --- | --- | --- |
| **Green band** (0 to tau_max) | #22bb44 at 10% opacity | Safe operating zone of the shaft |
| **Yellow band** (tau_max to tau_yield) | #ffcc00 at 13% opacity | Available safety margin before shear yield |
| **Green dashed line** at tau_max | #22aa44 | Maximum torsional shear stress on the most-loaded segment |
| **Orange dashed line** at tau_yield | #cc8800 | Shear yield limit: tau_yield = 0.577 * Sy |
| **SF label** (top-left) | Green text | Safety factor: SF = tau_yield / tau_max |

**If the shaft is overstressed** (tau_max >= tau_yield, i.e. SF < 1):

| Element | Colour | Meaning |
| --- | --- | --- |
| **SF label** displayed in grey | #888888 | Ratio shown as informational reference only (not a pass/fail indicator) |

> **Note:** τ_max is **not** an operating load — it is the shear stress that would develop at exactly 1° of elastic twist, used as a geometric/material reference to position the shaft on the curve. For a real strength assessment, enter the nominal design torque.

---

## Material Library

The library (`data/materials.json`) ships with **20 automotive metals**:

| Material | G (MPa) | E (MPa) | Sy (MPa) | Su (MPa) |
| --- | --- | --- | --- | --- |
| SAE 1020 Steel | 80 000 | 205 000 | 210 | 380 |
| SAE 1045 Steel | 80 000 | 210 000 | 310 | 565 |
| SAE 4130 Steel | 80 000 | 205 000 | 460 | 560 |
| SAE 4140 Steel | 80 000 | 207 000 | 655 | 1020 |
| SAE 4340 Steel | 77 000 | 205 000 | 470 | 745 |
| SAE 8620 Steel | 80 000 | 207 000 | 385 | 530 |
| AISI 304 Stainless | 75 000 | 193 000 | 215 | 505 |
| AISI 316 Stainless | 75 000 | 193 000 | 170 | 485 |
| AISI 52100 Bearing | 80 000 | 210 000 | 1520 | 1900 |
| 17-4 PH Stainless | 77 000 | 197 000 | 1170 | 1310 |
| AA 6061-T6 Aluminium | 26 000 | 68 900 | 276 | 310 |
| AA 7075-T6 Aluminium | 26 900 | 71 700 | 503 | 572 |
| AA 2024-T3 Aluminium | 27 600 | 73 100 | 345 | 483 |
| Ti-6Al-4V Titanium | 44 000 | 114 000 | 880 | 950 |
| Inconel 718 | 77 000 | 200 000 | 1034 | 1241 |
| Gray Cast Iron | 41 000 | 100 000 | -- | 200 |
| Ductile Cast Iron | 69 000 | 169 000 | 276 | 414 |
| Copper C110 | 44 000 | 117 000 | 70 | 220 |
| Bronze SAE 660 | 38 000 | 103 000 | 125 | 240 |
| Magnesium AZ31B | 17 000 | 45 000 | 220 | 290 |

All values can be edited, added, or removed at runtime through **Gerenciar Materiais / Manage Materials**.

---

## File Structure

```text
Torsional Stiffness Shaft/
├── main.py                   # Entry point — run directly with: python main.py
├── calculator.py             # Torsional stiffness calculation logic
├── report_generator.py       # HTML report builder (Jinja2 + inline SVG)
├── joint_management.py       # Joint CRUD window
├── material_management.py    # Material CRUD window (name, G, E, Sy, Su)
├── translator.py             # i18n / locale helper
├── stp_exporter.py           # STEP 3D export via CadQuery
├── README.md                 # This file
│
├── templates/
│   └── report_template.html  # Jinja2 HTML report template
│
├── data/
│   ├── joints.json           # Joint library data
│   └── materials.json        # Material library (20 automotive metals)
│
├── locale/
│   ├── pt_BR/translation.json  # Brazilian Portuguese strings
│   ├── en/translation.json     # English strings
│   └── zh/translation.json     # Chinese Simplified strings
│
└── assets/
    ├── icon.png              # Application icon (64×64)
    └── empresa.png           # Company banner for HTML report (900×120)
```

---

## Supported Languages

| Code | Language | Status bar text |
| --- | --- | --- |
| `pt_BR` | Portugues (Brasil) | Versao 1.0 |
| `en` | English | Version 1.0 |
| `zh` | Chinese (Simplified) | Version 1.0 |

Change the language at runtime using the **Idioma / Language** dropdown in the main window.

---

## License

Internal engineering tool -- for company use only.
