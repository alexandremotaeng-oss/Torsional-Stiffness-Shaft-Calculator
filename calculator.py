import math


class Calculator:
    """Torsional stiffness calculator for a multi-segment shaft."""

    def calculate_torsional_stiffness(self, segments):
        """
        Calculate the total torsional stiffness of a shaft with multiple segments
        in series (spring-in-series formula: 1/K_total = Σ 1/K_i).

        Segments with diameter == 0 or length == 0 are silently skipped.

        Args:
            segments: list of dicts with keys:
                'diameter'      – outer diameter in mm
                'length'        – length in mm
                'shear_modulus' – G in MPa

        Returns:
            float: total torsional stiffness in N·m/deg, or 0.0 if no valid segments.
        """
        inv_total = 0.0
        for seg in segments:
            D = seg["diameter"]
            L = seg["length"]
            if D <= 0 or L <= 0:
                continue   # skip zero/invalid segments

            G = seg["shear_modulus"] * 1e6     # MPa → Pa
            L_m = L / 1000.0                   # mm  → m
            D_m = D / 1000.0                   # mm  → m

            J = (math.pi * D_m ** 4) / 32.0   # polar moment of area (m⁴)
            k_rad = (G * J) / L_m              # N·m/rad

            inv_total += 1.0 / k_rad

        if inv_total == 0.0:
            return 0.0

        k_total_rad = 1.0 / inv_total
        k_total_deg = k_total_rad * (math.pi / 180.0)   # N·m/deg
        return k_total_deg

    def calculate_mass(self, segments, density_kg_m3=7850.0):
        """
        Calculate the total mass of the shaft (solid cylinders).

            m_i = ρ · π · (D_i/2)² · L_i   [kg]

        Args:
            segments:       list of dicts with 'diameter' (mm) and 'length' (mm).
            density_kg_m3:  material density (default: steel 7850 kg/m³).

        Returns:
            float: total mass in kg.
        """
        total = 0.0
        for seg in segments:
            D = float(seg.get("diameter", 0))
            L = float(seg.get("length",   0))
            if D <= 0 or L <= 0:
                continue
            r = (D / 1000.0) / 2.0          # radius in m
            L_m = L / 1000.0                # length in m
            total += density_kg_m3 * math.pi * r**2 * L_m
        return total

    def calculate_natural_frequencies(self, segments, density_kg_m3=7850.0):
        """
        Calculate the first three torsional natural frequencies of the shaft (Hz).

        Model: lumped-parameter torsional chain.
          - n valid segments → n torsional springs K_i [N·m/rad]
          - n+1 lumped polar inertias I_j [kg·m²] at segment boundaries,
            each accumulating half of its left and right segment mass inertia.
          - The two end nodes are kept free (free-free boundary conditions).

        Segment polar mass moment of inertia (solid cylinder):
            I_seg = (1/2) · m · r²  =  ρ · π · D⁴ · L / 32    [kg·m²]

        Free-free chain natural frequencies come from the eigenvalues of:
            K_eff · {θ} = ω² · M_eff · {θ}

        For free-free systems the rigid-body mode (ω=0) is removed; the first
        three non-zero eigenvalues give ω₁, ω₂, ω₃  →  f = ω/(2π).

        Args:
            segments:       list of dicts with 'diameter' (mm), 'length' (mm),
                            'shear_modulus' (MPa). Invalid segments are skipped.
            density_kg_m3:  material density for mass inertia (default: steel 7850 kg/m³).
                            Uses the same density for all segments as a first-order model.

        Returns:
            list of float: [f1, f2, f3] in Hz. Missing modes return 0.0.
        """
        rho = density_kg_m3

        # Filter valid segments only
        valid = [
            s for s in segments
            if float(s.get("diameter", 0)) > 0 and float(s.get("length", 0)) > 0
        ]
        n = len(valid)          # number of springs
        if n == 0:
            return [0.0, 0.0, 0.0]

        # ── Per-segment torsional spring stiffness [N·m/rad] ─────────────
        K = []
        for s in valid:
            G  = float(s["shear_modulus"]) * 1e6   # Pa
            D  = float(s["diameter"]) / 1000.0      # m
            L  = float(s["length"])  / 1000.0       # m
            J  = math.pi * D**4 / 32.0              # m⁴ (geometric polar moment)
            K.append(G * J / L)                     # N·m/rad

        # ── Per-segment polar mass moment of inertia [kg·m²] ─────────────
        # Solid cylinder: I_seg = ρ·π·D⁴·L / 32
        I_seg = []
        for s in valid:
            D = float(s["diameter"]) / 1000.0       # m
            L = float(s["length"])  / 1000.0        # m
            I_seg.append(rho * math.pi * D**4 * L / 32.0)

        # ── Assemble n+1 lumped inertia nodes ─────────────────────────────
        # Node 0     (left end)  : half of segment 0
        # Node j ∈ [1..n-1]     : half of segment j-1 + half of segment j
        # Node n     (right end) : half of segment n-1
        I_node = [0.0] * (n + 1)
        I_node[0]  = I_seg[0] / 2.0
        I_node[n]  = I_seg[n - 1] / 2.0
        for j in range(1, n):
            I_node[j] = I_seg[j - 1] / 2.0 + I_seg[j] / 2.0

        # ── Assemble stiffness matrix (n+1)×(n+1) — tri-diagonal ─────────
        ndof = n + 1
        Km = [[0.0] * ndof for _ in range(ndof)]
        for i in range(n):
            Km[i][i]         += K[i]
            Km[i][i + 1]     -= K[i]
            Km[i + 1][i]     -= K[i]
            Km[i + 1][i + 1] += K[i]

        # ── Assemble mass (inertia) matrix — diagonal ─────────────────────
        Mm = [I_node[i] for i in range(ndof)]

        # ── Solve generalised eigenvalue problem: K·θ = ω²·M·θ ───────────
        # For a diagonal M, transform to standard: K_eff · u = ω² · u
        # where K_eff[i][j] = K[i][j] / sqrt(M[i] * M[j])
        # Use iterative power / Jacobi for the small (≤ 14) tridiagonal matrix.
        # We implement a simple tridiagonal QR-like inverse-iteration for the
        # smallest eigenvalues.  For up to 14 DOF this is fast enough.

        # Guard against zero-inertia nodes (can arise if segments are very thin)
        for i in range(ndof):
            if Mm[i] <= 0.0:
                Mm[i] = 1e-30

        # Build symmetric normalised matrix A = M^{-1/2} K M^{-1/2}
        sqM = [math.sqrt(m) for m in Mm]
        A   = [[0.0] * ndof for _ in range(ndof)]
        for i in range(ndof):
            for j in range(ndof):
                A[i][j] = Km[i][j] / (sqM[i] * sqM[j])

        # ── Eigenvalues via Jacobi sweeps (symmetric dense, ndof ≤ 14) ───
        eigenvalues = self._jacobi_eigenvalues(A, ndof)

        # Sort ascending and remove zero/negative (rigid-body mode)
        eigenvalues.sort()
        positive = [ev for ev in eigenvalues if ev > 1e-3]

        result = []
        for k in range(3):
            if k < len(positive):
                omega_k = math.sqrt(positive[k])
                result.append(omega_k / (2.0 * math.pi))
            else:
                result.append(0.0)
        return result

    # ------------------------------------------------------------------
    @staticmethod
    def _jacobi_eigenvalues(A, n, max_sweeps=60, tol=1e-12):
        """
        Jacobi iterative method to find all eigenvalues of a real symmetric
        matrix A (n×n).  Returns eigenvalues as a flat list (unsorted).
        """
        # Work on a copy
        a = [row[:] for row in A]
        for _ in range(max_sweeps):
            # Find off-diagonal element with largest absolute value
            p, q = 0, 1
            max_off = 0.0
            for i in range(n - 1):
                for j in range(i + 1, n):
                    if abs(a[i][j]) > max_off:
                        max_off = abs(a[i][j])
                        p, q = i, j
            if max_off < tol:
                break
            # Jacobi rotation angle
            if abs(a[p][p] - a[q][q]) < 1e-30:
                theta = math.pi / 4.0
            else:
                theta = 0.5 * math.atan2(2.0 * a[p][q], a[p][p] - a[q][q])
            c, s = math.cos(theta), math.sin(theta)
            # Apply rotation
            new_a = [row[:] for row in a]
            for i in range(n):
                if i != p and i != q:
                    new_a[i][p] = c * a[i][p] + s * a[i][q]
                    new_a[p][i] = new_a[i][p]
                    new_a[i][q] = -s * a[i][p] + c * a[i][q]
                    new_a[q][i] = new_a[i][q]
            new_a[p][p] = (c**2) * a[p][p] + 2*c*s * a[p][q] + (s**2) * a[q][q]
            new_a[q][q] = (s**2) * a[p][p] - 2*c*s * a[p][q] + (c**2) * a[q][q]
            new_a[p][q] = 0.0
            new_a[q][p] = 0.0
            a = new_a
        return [a[i][i] for i in range(n)]
