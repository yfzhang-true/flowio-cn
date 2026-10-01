import Mesh, Part
import os
here = os.path.dirname(os.path.abspath(__file__))
for name in ("case-bottom", "case-top"):
    m = Mesh.Mesh()
    m.read(os.path.join(here, name + ".stl"))
    print("CHK", name, "STLfaces", len(m.Facets), "watertight", m.isSolid())
    sh = Part.Shape()
    sh.read(os.path.join(here, name + ".step"))
    print("CHK", name, "STEPsolids", len(sh.Solids), "vol_cm3", round(sh.Volume/1000, 1), "valid", sh.isValid())
