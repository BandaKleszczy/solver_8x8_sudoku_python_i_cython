# solver_cy.pyx
# cython: boundscheck=False, wraparound=False, language_level=3

cdef bint check_one_perm(
    list matrix,
    list thermo,
    list region_cells,
    list active_regions,
    list blue,
    list orange,
    list region_to_island,
    list letter_to_digit
):
    cdef int i, j, rid, idx
    cdef int first, val, s

    # 🌡️ THERMO
    for line in thermo:
        first = letter_to_digit[matrix[line[0]]]
        inc = True
        dec = True
        for i in range(1, len(line)):
            val = letter_to_digit[matrix[line[i]]]
            if val <= first:
                inc = False
            if val >= first:
                dec = False
            first = val
        if not (inc or dec):
            return False

    # 🧮 SUMY REGIONÓW
    sums = [0] * len(region_cells)
    for rid in active_regions:
        s = 0
        for idx in region_cells[rid]:
            s += letter_to_digit[matrix[idx]]
        sums[rid] = s

    # 🔵 BLUE
    for regs in blue:
        first = sums[regs[0]]
        for i in range(1, len(regs)):
            if sums[regs[i]] != first:
                return False

    # 🟠 ORANGE (BEZ dict — SZYBKO)
    cdef int island_sum[4]
    cdef int seen[4]
    cdef int isl

    for regs in orange:
        # reset
        for i in range(4):
            seen[i] = 0

        for rid in regs:
            isl = region_to_island[rid]
            if not seen[isl]:
                island_sum[isl] = sums[rid]
                seen[isl] = 1
            elif island_sum[isl] != sums[rid]:
                return False

        # wszystkie wyspy muszą mieć tę samą sumę
        first = -1
        for i in range(4):
            if seen[i]:
                if first == -1:
                    first = island_sum[i]
                elif island_sum[i] != first:
                    return False


    return True


def solve_matrix_all_permutations(
    list matrix,
    list thermo,
    list region_cells,
    list active_regions,
    list blue,
    list orange,
    list region_to_island,
    int L
):
    """
    Generuje wszystkie permutacje cyfr 1..8 długości L
    i liczy poprawne.
    """
    cdef int total = 0
    cdef list letter_to_digit = [0] * 8
    cdef list used = [0] * 9   # index 1..8

    def dfs(int pos):
        nonlocal total
        cdef int d

        if pos == L:
            if check_one_perm(
                matrix, thermo, region_cells,
                active_regions, blue, orange,
                region_to_island, letter_to_digit
            ):
                total += 1
            return

        for d in range(1, 9):
            if not used[d]:
                used[d] = 1
                letter_to_digit[pos] = d
                dfs(pos + 1)
                used[d] = 0

    dfs(0)
    return total

def get_solutions_sums(
    list matrix,
    list thermo,
    list region_cells,
    list active_regions,
    list blue,
    list orange,
    list region_to_island,
    int L
):
    cdef list results = []

    cdef list letter_to_digit = [0] * 8
    cdef list used = [0] * 9

    def dfs(int pos):
        cdef int d, rid, idx, s

        if pos == L:
            if check_one_perm(
                matrix, thermo, region_cells,
                active_regions, blue, orange,
                region_to_island, letter_to_digit
            ):
                # policz sumy regionów
                sums = [0] * len(region_cells)
                for rid in active_regions:
                    s = 0
                    for idx in region_cells[rid]:
                        s += letter_to_digit[matrix[idx]]
                    sums[rid] = s

                results.append(sums)
            return

        for d in range(1, 9):
            if not used[d]:
                used[d] = 1
                letter_to_digit[pos] = d
                dfs(pos + 1)
                used[d] = 0

    dfs(0)
    return results