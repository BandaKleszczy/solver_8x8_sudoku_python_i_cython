import time
from concurrent.futures import ProcessPoolExecutor
import os


# =========================
# KANONIZACJA (KLUCZOWE)
# =========================

def canonicalize(values):
    """
    Zamienia listę liczb (np. sum regionów)
    na postać kanoniczną niezależną od etykiet cyfr.
    """
    mapping = {}
    next_id = 1
    out = []

    for v in values:
        if v not in mapping:
            mapping[v] = next_id
            next_id += 1
        out.append(mapping[v])

    return tuple(out)


# =========================
# PARSERY (BEZ ZMIAN)
# =========================

def parse_cells(tokens):
    out = []
    for t in tokens:
        r = int(t[1]) - 1
        c = int(t[3]) - 1
        out.append(r * 8 + c)
    return out


def parse_geometry(path):
    regions = {}
    region_to_island = {}

    section = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith("["):
                section = line
                continue

            key, rest = line.split(":")
            tokens = rest.split()

            if section == "[REGIONS]":
                cells = []
                for t in tokens:
                    r = int(t[1]) - 1
                    c = int(t[3]) - 1
                    cells.append(r * 8 + c)
                regions[key] = cells

            elif section == "[ISLANDS]":
                for r in tokens:
                    region_to_island[r] = key

    region_ids = {r: i for i, r in enumerate(regions)}
    region_cells = [regions[r] for r in regions]

    cell_to_region = {}
    for rname, cells in regions.items():
        rid = region_ids[rname]
        for idx in cells:
            cell_to_region[idx] = rid

    island_ids = {i: idx for idx, i in enumerate(set(region_to_island.values()))}
    region_to_island_list = [
        island_ids[region_to_island[r]] for r in regions
    ]

    return region_cells, cell_to_region, region_ids, region_to_island_list


def parse_lines(path, cell_to_region):
    blue, orange, thermo = [], [], []
    section = None

    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith("["):
                section = line
                continue

            _, rest = line.split(":")
            tokens = rest.split()

            idxs = []
            regs = []

            for t in tokens:
                r = int(t[1]) - 1
                c = int(t[3]) - 1
                idx = r * 8 + c
                idxs.append(idx)
                regs.append(cell_to_region[idx])

            if section == "[THERMO]":
                thermo.append(idxs)
            elif section == "[BLUE]":
                blue.append(regs)
            elif section == "[ORANGE]":
                orange.append(regs)

    return blue, orange, thermo


def parse_matrices(path):
    matrices = []
    current = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.lower().startswith("macierz"):
                if current:
                    matrices.append(current)
                current = []
            else:
                current.extend([ord(c) - 65 for c in line.split()])
    if current:
        matrices.append(current)
    return matrices


# =========================
# ROZWIĄZYWANIE 1 MACIERZY
# =========================

def solve_one_matrix(args):
    (
        matrix,
        thermo,
        region_cells,
        active_regions,
        blue,
        orange,
        region_to_island,
    ) = args

    letters = sorted(set(matrix))
    L = len(letters)

    letter_index = {l: i for i, l in enumerate(letters)}
    matrix = [letter_index[x] for x in matrix]

    # 🔑 Cython: zwraca LISTĘ sum regionów dla każdego rozwiązania
    from solver_cy import get_solutions_sums

    raw_solutions = get_solutions_sums(
        matrix,
        thermo,
        region_cells,
        active_regions,
        blue,
        orange,
        region_to_island,
        L
    )

    uniq = set()
    for sums in raw_solutions:
        uniq.add(canonicalize(sums))

    return uniq


# =========================
# MAIN
# =========================

def solve_partial():
    region_cells, cell_to_region, region_ids, region_to_island = parse_geometry("geometry.txt")
    blue, orange, thermo = parse_lines("lines.txt", cell_to_region)
    matrices = parse_matrices("matrices.txt")

    active_regions = sorted(set(r for line in blue + orange for r in line))

    args = [
        (
            matrix,
            thermo,
            region_cells,
            active_regions,
            blue,
            orange,
            region_to_island,
        )
        for matrix in matrices
    ]

    workers = os.cpu_count()

    all_unique = set()

    with ProcessPoolExecutor(max_workers=workers) as exe:
        results = exe.map(solve_one_matrix, args)

        for s in results:
            all_unique |= s

    return len(all_unique)


if __name__ == "__main__":
    t0 = time.perf_counter()
    result = solve_partial()
    t1 = time.perf_counter()

    print("Unikalne rozwiązania (bez permutacji cyfr):", result)
    print(f"Czas: {t1 - t0:.3f} s")
