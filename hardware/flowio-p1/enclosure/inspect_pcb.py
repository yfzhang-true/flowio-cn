import Part
sh = Part.Shape()
sh.read("hardware/flowio-p1/fab/flowio-p1.step")
print("PCBSOLIDS", len(sh.Solids))
print("BBOX", sh.BoundBox)
