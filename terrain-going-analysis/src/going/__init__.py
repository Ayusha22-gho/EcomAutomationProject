"""Rapid terrain mapping and GOING (terrain trafficability) analysis toolkit.

Reference implementation used by the course demonstration. Every product is
generated from synthetic data so the full workflow can be run and repeated on a
laptop without flying a real UAS or holding protected data.
"""

LC = {
    "GRASS": 1,
    "CULTIVATED": 2,
    "SCRUB": 3,
    "FOREST_LIGHT": 4,
    "FOREST_DENSE": 5,
    "BUILT_UP": 6,
    "BUILDING": 7,
    "ROAD": 8,
    "TRACK": 9,
    "WATER": 10,
    "MARSH": 11,
    "QUARRY": 12,
}
LC_NAMES = {v: k for k, v in LC.items()}

GO, SLOW_GO, NO_GO, RECCE = 1, 2, 3, 4
CLASS_NAMES = {GO: "GO", SLOW_GO: "SLOW-GO", NO_GO: "NO-GO", RECCE: "REQUIRES RECCE"}
CLASS_COLOURS = {GO: "#2e9e44", SLOW_GO: "#f2c230", NO_GO: "#d7301f", RECCE: "#7b4fd6"}
