"""Exploratory submit-file fixture, also usable as a plain Python script."""
import sys

print("Exploratory Python stdout")
print("Exploratory Python stderr", file=sys.stderr)
if "GEOEXP_CONTEXT" in globals():
    GEOEXP_CONTEXT.tracker.log({"fixture": 1}, step=0)
