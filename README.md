# Torsional Stiffness Shaft Calculator

A desktop engineering application for calculating the **torsional stiffness**, **torsional natural frequencies**, and **mass** of multi-segment driveline shafts. Built with Python and Tkinter, with multilingual support (pt\_BR / en / zh), project management, FRF chart, HTML report generation, and STEP 3D export.

---

## Table of Contents

1. [Engineering Background](#engineering-background)
2. [Shaft Model and Geometry](#shaft-model-and-geometry)
3. [Calculation Methodology](#calculation-methodology)
4. [Frequency Response Function (FRF) Chart](#frequency-response-function-frf-chart)
5. [Offset and Excluded Segments](#offset-and-excluded-segments)
6. [Compatibility Search](#compatibility-search)
7. [Report and Charts](#report-and-charts)
8. [Requirements and Installation](#requirements-and-installation)
9. [Running and Debugging](#running-and-debugging)
10. [Multilingual Support](#multilingual-support)

---

## Engineering Background

Torsional stiffness is a fundamental design parameter in driveline systems. It governs:

- **Natural frequencies** of the driveline torsional system — directly influencing NVH (Noise, Vibration and Harshness) targets.
- **Torque distribution** and angular compliance under load.
- **Durability** — shafts that are too compliant may amplify dynamic loads; shafts that are too stiff may transmit shock loads into adjacent components.

In automotive driveline engineering, a propshaft or halfshaft is modelled as a **series of cylindrical sections** connected to constant-velocity joints (OBJ and IBJ). Each segment contributes a finite stiffness $K_i$; the assembly behaves as springs in series.

---

## Shaft Model and Geometry

### Segment definition

Each segment is defined by three parameters:

| Parameter | Symbol | Unit |
| --- | --- | --- |
| Outer diameter | $D_i$ | mm |
| Axial length | $L_i$ | mm |
| Material shear modulus | $G_i$ | MPa |

Segments with $D_i = 0$ or $L_i = 0$ are automatically excluded from all calculations.

### Full shaft assembly

```markdown
+---------- OBJ Joint ----------+---- Central Shaft ----+---------- IBJ Joint ----------+
|  sec1 | sec2 | ... | sec10    |   O(D) x L_central    |  sec10 | ... | sec2 | sec1    |
+-------------------------------+-----------------------+-------------------------------+
        <-- obj_len -->                <-- L_bare -->           <-- ibj_len -->
   Pwc (obj_offset from left end)                    Ptl (ibj_offset from right end)
```

**OBJ joint** — sections defined inside-out (section 1 nearest the joint centre).
**IBJ joint** — sections reversed so section 1 is outermost right, preserving symmetry.
**Central segment** — a single bare shaft tube with the user-specified diameter and derived length.

### Pwc (Point of Wheel Center) / Ptl (Point of Transmission Line Center) reference planes

| Marker | Location |
| --- | --- |
| **Pwc** | `obj_offset` mm from the left end of the shaft |
| **Ptl** | `ibj_offset` mm from the right end of the shaft |

The user inputs the **Pwc to Ptl distance** (centre-to-centre). The application back-calculates the central bare length:

```
L_bare    = L(Pwc->Ptl) - L_OBJ - L_IBJ + delta_OBJ + delta_IBJ
L_central = L_bare - delta_OBJ - delta_IBJ
```

where `delta_OBJ` and `delta_IBJ` are the OBJ and IBJ offset values respectively.

---

## Calculation Methodology

### 1 — Polar moment of inertia

For a solid circular cross-section of diameter $D$:

$$J_i = \frac{\pi D_i^4}{32}$$

### 2 — Segment torsional stiffness

$$K_i = \frac{G_i \cdot J_i}{L_i} \quad \text{[N·m/rad]}$$

Converted to the engineering unit **N·m/degree**:

$$K_i^\circ = K_i \cdot \frac{\pi}{180}$$

### 3 — Total shaft stiffness (springs in series)

$$\frac{1}{K_\text{total}} = \sum_{i=1}^{n} \frac{1}{K_i}$$

$$K_\text{total}^\circ = K_\text{total} \cdot \frac{\pi}{180} \quad \text{[N·m/degree]}$$

> **Engineering implication:** In a series arrangement the weakest (most compliant) segment dominates. Improving the dominant segment yields far greater gains than improving a stiffer one.

### 4 — Shaft mass

Each segment is treated as a solid cylinder:

$$m_i = \rho \cdot \pi \cdot \left(\frac{D_i}{2}\right)^2 \cdot L_i \quad \text{[kg]}$$

Default density: $\rho = 7850\ \text{kg/m}^3$ (steel).

$$m_\text{total} = \sum_{i} m_i$$

Displayed alongside the 1st natural frequency in the Results bar.

### 5 — Torsional natural frequencies

The shaft is modelled as a **free-free lumped-parameter torsional chain** with $n$ springs and $n+1$ lumped polar inertia nodes.

**Polar mass moment of inertia** per segment (solid cylinder):

$$I_i = \frac{\rho \cdot \pi \cdot D_i^4 \cdot L_i}{32} \quad \text{[kg·m}^2\text{]}$$

**Lumped inertia nodes** — each node accumulates half of its two adjacent segment inertias:

$$I_0 = \tfrac{1}{2}I_\text{seg,0}, \quad I_j = \tfrac{1}{2}I_\text{seg,j-1} + \tfrac{1}{2}I_\text{seg,j} \; (j=1..n{-}1), \quad I_n = \tfrac{1}{2}I_\text{seg,n-1}$$

**Generalised eigenvalue problem:**

$$\mathbf{K}\,\boldsymbol{\theta} = \omega^2\,\mathbf{M}\,\boldsymbol{\theta}$$

Solved by normalising to a standard symmetric eigenproblem and applying the **Jacobi iteration** (exact for the small matrices, max 14 DOF, produced by real joint/shaft assemblies). The rigid-body mode ($\omega = 0$) is discarded; the first three non-zero eigenvalues give:

$$f_k = \frac{\omega_k}{2\pi} \quad \text{[Hz]}$$

### 6 — Maximum torsional shear stress

Shear stress at 1° of elastic twist in segment $i$ (geometric reference, not an operating load):

$$T_i = K_{i,\text{rad}} \cdot \frac{\pi}{180}, \qquad \tau_i = \frac{T_i \cdot (D_i/2)}{J_i} \quad \text{[MPa]}$$

$$\tau_\text{max} = \max_i(\tau_i)$$

### 7 — Shear yield criterion (von Mises)

$$\tau_\text{yield} = \frac{S_y}{\sqrt{3}} \approx 0.577 \cdot S_y$$

### 8 — Safety factor in shear

$$SF = \frac{\tau_\text{yield}}{\tau_\text{max}}$$

| SF range | Colour | Meaning |
| --- | --- | --- |
| $SF \geq 2.0$ | Green | Large shear margin — geometry is conservative |
| $1.0 \leq SF < 2.0$ | Amber | Moderate margin — within design range |
| $SF < 1.0$ | Grey | tau_max > tau_yield at 1° twist (informational only) |

---

## Frequency Response Function (FRF) Chart

The HTML report includes an **Amplitude vs Frequency** FRF chart generated from the three computed natural frequencies.

### Model

Single-DOF receptance superposition with constant damping ratio $\zeta = 0.02$:

$$H(f) = \sum_{k=1}^{3} \frac{1}{\sqrt{(1 - r_k^2)^2 + (2\,\zeta\,r_k)^2}}, \qquad r_k = \frac{f}{f_k}$$

Frequency sweep: $0$ to $1.4 \times f_\text{max}$, sampled at 900 equally-spaced points.

### Chart features

- **X axis:** frequency (Hz)
- **Y axis:** normalised amplitude $H(f)$, linear scale
- **Three resonance peaks** annotated with mode label and frequency value
- Vertical dashed guide lines at $f_1$, $f_2$, $f_3$
- Filled area under the FRF curve (semi-transparent blue)
- Damping ratio annotation ($\zeta = 0.02$) in the top-right corner

---

## Offset and Excluded Segments

Each joint carries an **offset** value (mm). Segments whose start position lies inside the offset zone are **excluded from the stiffness calculation** — they are structurally constrained inside the joint housing.

### Trimming rule

```
OBJ side (measured left -> right):
  segment start >= obj_offset  ->  INCLUDED
  segment start <  obj_offset  ->  EXCLUDED

IBJ side (measured right -> left, mirrored):
  segment start >= ibj_offset  ->  INCLUDED
  segment start <  ibj_offset  ->  EXCLUDED
```

Excluded segments are still drawn in the shaft schematic and listed in the report table, but their stiffness column shows **NAO APLICADO / Not Applied / 不适用** depending on the active language.

---

## Compatibility Search

**Buscar Compatibilidade / Search Compatibility** compares the current configuration against all saved projects and returns a ranked list with a 0–100% compatibility score.

### Scoring

| Component | Weight | Metric |
| --- | --- | --- |
| Joint geometry (OBJ + IBJ) | 40% | Mean segment-level diameter + length similarity |
| Shaft diameter | 20% | 1 - &#124;delta D&#124; / max(D) |
| Shaft length (Pwc–Ptl) | 20% | 1 - &#124;delta L&#124; / max(L) |
| Material | 20% | 50% name match + 50% shear modulus closeness |

$$\text{score} = 0.40 \cdot \frac{\text{sim}_\text{OBJ} + \text{sim}_\text{IBJ}}{2} + 0.20 \cdot \text{sim}_D + 0.20 \cdot \text{sim}_L + 0.20 \cdot \text{sim}_\text{mat}$$

Results are sorted descending by score. Selecting a result and clicking **Carregar / Load** opens that project directly.

---

## Report and Charts

Clicking **Gerar Relatorio / Generate Report** produces `report.html` (in the project root) and opens it in the default browser. All SVG graphics are inline; the company banner is base64-embedded, making the file fully self-contained.

### Report sections

| # | Section | Content |
| --- | --- | --- |
| 1 | Header | Company banner, project name, engineer, generation timestamp |
| 2 | Shaft Schematic (SVG) | Colour-banded cross-section profile, diameter/length labels, Pwc/Ptl markers |
| 3 | Segment Table | Diameter, length, G, individual stiffness (or Not Applied for excluded segments) |
| 4 | Total Stiffness KPI | K_total in N·m/degree — large highlighted block |
| 5 | Stiffness Chart (SVG) | Line chart of per-segment stiffness with weakest-segment callout |
| 6 | FRF Chart (SVG) | Amplitude vs Frequency with peaks at f1, f2, f3 and shaft mass in callout |
| 7 | Stress-Strain Curve (SVG) | Bilinear elastic-plastic material curve with operating zone overlay and SF |
| 8 | Operating Limits Analysis | tau_max, tau_yield, SF, full material properties table |

---

## Requirements and Installation

### Dependencies

| Dependency | Version | Purpose |
| --- | --- | --- |
| Python | >= 3.10 | Runtime |
| tkinter | bundled | GUI (included with the standard Python installer) |
| Jinja2 | >= 3.0 | HTML report templating |
| CadQuery | >= 2.7 | STEP 3D export (optional) |

### Installation

```powershell
pip install jinja2
```

CadQuery (optional, only for **Exportar .STP**):

```powershell
pip install cadquery
```

> CadQuery requires a 64-bit Python environment. All other features work without it.

---

## Running and Debugging

### Run directly

```powershell
python main.py
```

### Debug in VS Code

A `.vscode/launch.json` is included with a pre-configured debug profile. Open the project folder in VS Code, select **"Torsional Stiffness Shaft"** in the Run & Debug panel, and press **F5**.

### Workflow

1. **Projects** — type a name in the project combobox and click **Salvar** to save. Click **Carregar** to restore a saved project.
2. **Header** — enter Project Name and Engineer name.
3. **Shaft** — select OBJ and IBJ joints from the dropdowns. Enter shaft outer diameter (mm) and Pwc→Ptl distance (mm).
4. **Material** — select a material from the library; shear modulus G is auto-filled.
5. **Calcular** — computes torsional stiffness (N·m/degree), 1st natural frequency (Hz), and shaft mass (kg). Shaft drawing updates automatically.
6. **Tools menu:**
   - **Gerenciar Juntas** — add, edit, or delete joint definitions (up to 10 sections each with diameter, length, and offset).
   - **Gerenciar Materiais** — add, edit, or delete materials (name, G, E, Sy, Su).
   - **Gerar Relatorio** — generates `report.html` and opens it in the default browser.
   - **Exportar .STP** — exports a STEP 3D model of the active shaft geometry.
   - **Buscar Compatibilidade** — finds the most geometrically similar saved projects.

### Project save / load and DB reconciliation

When loading a project, the application compares joint and material data stored in the project JSON against the current libraries (`data/joints.json`, `data/materials.json`). If a discrepancy is detected, the user is prompted to:

- **Add** the missing entry to the library, or
- **Update** the library with the project values.

This ensures that loading a project always results in a consistent, reproducible calculation.

---

## Multilingual Support

Change the language at runtime using the **Idioma / Language** dropdown. The entire UI, all dialogs, report labels, and default names update immediately without restarting the application.

| Code | Language | Notes |
| --- | --- | --- |
| `pt_BR` | Portugues (Brasil) | Default |
| `en` | English | — |
| `zh` | Chinese Simplified (中文) | — |

Translation strings are stored in `locale/<code>/translation.json`. To add a new language, create the folder and JSON file with the same keys as an existing translation file.

---

## License

Internal engineering tool — for company use only.
