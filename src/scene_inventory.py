"""Scene-level category inventory for BenchSeg (R3.6). Emits:
  results/scene_inventory.csv               partition,scene,category,n_frames
  results/tables/tab_scene_inventory.tex    appendix LaTeX table (per-partition, grouped by category)
Data taken from the GT mask inventory (scene = filename prefix, frame count = #masks).
"""
import csv
import os

# (partition, scene, n_frames) from data/<part>/masks inventory
INV = {
    "N5k": [(str(i), n) for i, n in
            [(1, 64), (2, 61), (3, 63), (4, 63), (5, 61), (6, 65), (7, 60), (8, 63), (9, 63), (10, 58)]],
    "MTF": [(str(i), n) for i, n in
            [(1, 199), (2, 200), (3, 200), (4, 200), (5, 200), (6, 200), (7, 200), (8, 200),
             (9, 30), (10, 30), (11, 30), (13, 30), (14, 30)]],
    "V\\&F": [("apple", 201), ("avocado", 172), ("banana", 232), ("blackberry", 157)],
    "FKit": [("aguacate", 1078), ("apple", 1005), ("apple\\_pie", 1201), ("banana", 1156),
             ("capsicum", 881), ("chocolate\\_bomb", 1111), ("chocolate\\_cake", 781),
             ("chocolate\\_croissant", 1122), ("donut", 780), ("durum", 1006),
             ("empanadilla", 926), ("falafel", 929), ("french\\_bread", 1139), ("lemon", 887),
             ("mini\\_chocolate\\_panettone", 1209), ("napolitanas", 1071), ("orange", 1001),
             ("paxoco\\_mini", 911), ("pear", 849), ("samosa", 848), ("yellow\\_cane", 715)],
}
# coarse food category per named scene; numbered scenes are multi-ingredient plated/tray meals
CAT = {
    "apple": "Fruit", "avocado": "Fruit", "banana": "Fruit", "blackberry": "Fruit",
    "aguacate": "Fruit", "capsicum": "Vegetable", "lemon": "Fruit", "orange": "Fruit",
    "pear": "Fruit", "yellow\\_cane": "Fruit",
    "donut": "Baked/Pastry", "apple\\_pie": "Baked/Pastry", "chocolate\\_bomb": "Baked/Pastry",
    "chocolate\\_cake": "Baked/Pastry", "chocolate\\_croissant": "Baked/Pastry",
    "french\\_bread": "Baked/Pastry", "mini\\_chocolate\\_panettone": "Baked/Pastry",
    "napolitanas": "Baked/Pastry", "paxoco\\_mini": "Baked/Pastry", "durum": "Baked/Pastry",
    "falafel": "Savory/Fried", "samosa": "Savory/Fried", "empanadilla": "Savory/Fried",
}
PART_DESC = {"N5k": "Plated multi-ingredient meal", "MTF": "Tray multi-ingredient meal",
             "V\\&F": "Single fruit/vegetable", "FKit": "Single dish/ingredient"}


def cat_of(part, scene):
    if part in ("N5k", "MTF"):
        return PART_DESC[part]
    return CAT.get(scene, "Other")


def main():
    os.makedirs("results/tables", exist_ok=True)
    rows = []
    for part, scenes in INV.items():
        for s, n in scenes:
            rows.append([part.replace("\\&", "&").replace("\\_", "_"),
                         s.replace("\\_", "_"), cat_of(part, s), n])
    with open("results/scene_inventory.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["partition", "scene", "category", "n_frames"]); w.writerows(rows)

    # LaTeX: one block per partition
    L = [r"\begin{table}[htb]", r"\centering", r"\footnotesize",
         r"\caption{\change{Scene-level category inventory of the $48$ evaluated dish scenes. "
         r"FKit and V\&F scenes are single named items; N5k and MTF scenes are multi-ingredient "
         r"meals identified by capture index. $n$ denotes the number of multi-view frames per scene.}}",
         r"\label{tab:scene_inventory}",
         r"\begin{tabular}{llr@{\hskip 2em}llr}", r"\toprule",
         r"\textbf{Scene} & \textbf{Category} & \textbf{$n$} & \textbf{Scene} & \textbf{Category} & \textbf{$n$} \\"]
    for part, scenes in INV.items():
        L.append(r"\midrule")
        L.append(r"\multicolumn{6}{l}{\textit{" + part + r" --- " + str(len(scenes)) +
                 r" scenes, " + str(sum(n for _, n in scenes)) + r" frames}} \\")
        half = (len(scenes) + 1) // 2
        left, right = scenes[:half], scenes[half:]
        for i in range(half):
            ls, ln = left[i]
            cells = [ls, cat_of(part, ls), str(ln)]
            if i < len(right):
                rs, rn = right[i]
                cells += [rs, cat_of(part, rs), str(rn)]
            else:
                cells += ["", "", ""]
            L.append(" & ".join(cells) + r" \\")
    L += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    with open("results/tables/tab_scene_inventory.tex", "w") as f:
        f.write("\n".join(L) + "\n")
    print(f"wrote results/scene_inventory.csv ({len(rows)} scenes) + results/tables/tab_scene_inventory.tex")
    print("totals:", {p: (len(s), sum(n for _, n in s)) for p, s in INV.items()},
          "=> 48 scenes,", sum(sum(n for _, n in s) for s in INV.values()), "frames")


if __name__ == "__main__":
    main()
