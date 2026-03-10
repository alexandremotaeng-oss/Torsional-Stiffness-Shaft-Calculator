import math


class Calculator:
    """Torsional stiffness calculator for a multi-segment shaft."""

    def calculate_torsional_stiffness(self, segments):
        """
        Calculate the total torsional stiffness of a shaft with multiple segments
        in series (spring-in-series formula: 1/K_total = Σ 1/K_i).

        Args:
            segments: list of dicts with keys:
                'diameter'      – outer diameter in mm
                'length'        – length in mm
                'shear_modulus' – G in MPa

        Returns:
            float: total torsional stiffness in N·m/deg

        Raises:
            ZeroDivisionError: if any segment has length == 0 or diameter == 0.
        """
        inv_total = 0.0
        for seg in segments:
            G = seg["shear_modulus"] * 1e6          # MPa → Pa
            L = seg["length"] / 1000.0              # mm  → m
            D = seg["diameter"] / 1000.0            # mm  → m

            if L <= 0:
                raise ZeroDivisionError(
                    f"Comprimento inválido ({seg['length']} mm) em um segmento."
                )
            if D <= 0:
                raise ZeroDivisionError(
                    f"Diâmetro inválido ({seg['diameter']} mm) em um segmento."
                )

            J = (math.pi * D ** 4) / 32.0          # polar moment of area (m⁴)
            k_rad = (G * J) / L                     # N·m/rad

            inv_total += 1.0 / k_rad

        k_total_rad = 1.0 / inv_total                           # N·m/rad
        k_total_deg = k_total_rad * (math.pi / 180.0)          # N·m/deg  (K_deg = K_rad * π/180)
        return k_total_deg
