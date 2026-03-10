"""
STP (STEP) exporter for the torsional shaft geometry.

Each segment is modelled as a solid cylinder (right-circular) extruded along
the Z axis. Adjacent cylinders are fused into a single solid body using CadQuery.
"""

import cadquery as cq


class StpExporter:
    def __init__(self, segments: list[dict]):
        """
        Args:
            segments: list of dicts with 'diameter' (mm) and 'length' (mm).
        """
        self.segments = segments

    def export(self, file_path: str):
        """Build the solid and export to a STEP (.stp) file."""
        if not self.segments:
            raise ValueError("No segments provided for STP export.")

        result = None
        z_offset = 0.0

        for seg in self.segments:
            radius = seg["diameter"] / 2.0
            length = seg["length"]

            cylinder = (
                cq.Workplane("XY")
                .workplane(offset=z_offset)
                .circle(radius)
                .extrude(length)
            )

            result = cylinder if result is None else result.union(cylinder)
            z_offset += length

        # Export using the cadquery 2.x exporters API
        cq.exporters.export(result, file_path, cq.exporters.ExportTypes.STEP)
