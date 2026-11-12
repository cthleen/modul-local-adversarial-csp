"""Eksperimen terukur untuk modul KKA; tanpa dependency selain standard library."""
from collections import deque
import math
import random

WIN_LINES = ((0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6),
             (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6))
ROW_ORDER = tuple(range(9))
CENTER_ORDER = (4, 0, 2, 6, 8, 1, 3, 5, 7)


def ttt_evaluation(board):
    """Skor cutoff dari sisi X: baris terbuka X dikurangi baris terbuka O.

    Rentang nonterminal kecil dibanding utility terminal +/-100.
    """
    score = 0
    for line in WIN_LINES:
        cells = [board[i] for i in line]
        if 'O' not in cells:
            score += cells.count('X') ** 2
        if 'X' not in cells:
            score -= cells.count('O') ** 2
    return score


def ttt_search(board=None, pruning=False, order=ROW_ORDER, cutoff=None):
    """Hitung semua pemanggilan rekursif, termasuk root dan terminal, tanpa cache.

    board valid, giliran X; order memuat indeks 0..8 tepat satu kali.
    """
    if sorted(order) != list(range(9)):
        raise ValueError('order harus permutasi 0..8')
    board = list(board) if board is not None else [' '] * 9
    if len(board) != 9 or any(c not in (' ', 'X', 'O') for c in board):
        raise ValueError('board harus berisi 9 sel: spasi, X, atau O')
    nodes = 0

    def visit(is_max, alpha, beta, depth):
        nonlocal nodes
        nodes += 1
        for a, b, c in WIN_LINES:
            if board[a] != ' ' and board[a] == board[b] == board[c]:
                return 100 if board[a] == 'X' else -100
        if ' ' not in board:
            return 0
        if cutoff is not None and depth >= cutoff:
            return ttt_evaluation(board)
        value = -math.inf if is_max else math.inf
        for move in order:
            if board[move] != ' ':
                continue
            board[move] = 'X' if is_max else 'O'
            child = visit(not is_max, alpha, beta, depth + 1)
            board[move] = ' '
            value = max(value, child) if is_max else min(value, child)
            if is_max:
                alpha = max(alpha, value)
            else:
                beta = min(beta, value)
            if pruning and beta <= alpha:
                break
        return value

    value = visit(True, -math.inf, math.inf, 0)
    return dict(value=value, nodes=nodes)


def ac3(domains, neighbors, compatible):
    """Mutasi domains hingga arc-consistent; False bila ada domain kosong.

    neighbors mencakup kedua arah setiap binary constraint.
    compatible(x, vx, y, vy) memeriksa constraint x-y.
    """
    if any(not domain for domain in domains.values()):
        return False
    queue = deque((x, y) for x in domains for y in neighbors[x])
    while queue:
        x, y = queue.popleft()
        remaining = [vx for vx in domains[x]
                     if any(compatible(x, vx, y, vy) for vy in domains[y])]
        if remaining != domains[x]:
            domains[x] = remaining
            if not remaining:
                return False
            queue.extend((z, x) for z in neighbors[x] if z != y)
    return True


def queens_compatible(row, col, other_row, other_col):
    return col != other_col and abs(row - other_row) != abs(col - other_col)


def valid_queens(solution, n):
    return (solution is not None and set(solution) == set(range(n))
            and all(0 <= col < n for col in solution.values())
            and all(queens_compatible(r, c, s, d)
                    for r, c in solution.items() for s, d in solution.items() if r < s))


def solve_queens(n=10, mode='BT'):
    """Solusi pertama. assignments = penempatan konsisten (termasuk yang dibatalkan).

    Baris dan nilai menaik; tie MRV: baris terkecil; tie LCV: kolom terkecil.
    """
    if n < 1 or mode not in ('BT', 'FC', 'FC+MRV', 'FC+MRV+LCV'):
        raise ValueError('n/mode tidak valid')
    assignments = 0
    use_fc = mode != 'BT'

    def search(assigned, domains):
        nonlocal assignments
        if len(assigned) == n:
            return assigned.copy()
        unassigned = [r for r in range(n) if r not in assigned]
        row = min(unassigned, key=lambda r: (len(domains[r]), r)) if 'MRV' in mode else unassigned[0]
        values = domains[row]
        if 'LCV' in mode:
            values = sorted(values, key=lambda c: (
                sum(not queens_compatible(row, c, r, d) for r in unassigned if r != row for d in domains[r]), c))
        for col in values:
            if not all(queens_compatible(row, col, r, c) for r, c in assigned.items()):
                continue
            assignments += 1
            assigned[row] = col
            reduced = {r: ds[:] for r, ds in domains.items()}
            if use_fc:
                for r in unassigned:
                    if r != row:
                        reduced[r] = [c for c in domains[r] if queens_compatible(row, col, r, c)]
            if all(reduced[r] for r in unassigned if r != row):
                found = search(assigned, reduced)
                if found is not None:
                    return found
            del assigned[row]
        return None

    solution = search({}, {r: list(range(n)) for r in range(n)})
    return dict(solution=solution, assignments=assignments)


def queen_fitness(state):
    return sum(queens_compatible(i, c, j, d)
               for i, c in enumerate(state) for j, d in enumerate(state) if i < j)


def local_queens(initial, method='HC', seed=0, max_iter=2000, T=10, alpha=0.995):
    """Kedua metode mulai dari state yang sama; SA menyimpan best-so-far.

    HC memilih tetangga terbaik tanpa sideways. SA memindah satu ratu acak.
    evaluations menghitung pemanggilan fitness (termasuk initial).
    """
    if method not in ('HC', 'SA'):
        raise ValueError(method)
    rng = random.Random(seed)
    state = tuple(initial)
    n = len(state)
    score = queen_fitness(state)
    best, best_score, evaluations = state, score, 1
    target = n * (n - 1) // 2
    steps = 0
    for _ in range(max_iter):
        if score == target:
            break
        steps += 1
        if method == 'HC':
            candidates = []
            for col in range(n):
                for row in range(n):
                    if row != state[col]:
                        candidate = state[:col] + (row,) + state[col + 1:]
                        candidates.append((queen_fitness(candidate), candidate))
            evaluations += len(candidates)
            new_score, new = max(candidates, key=lambda item: item[0])
            if new_score <= score:
                break
        else:
            col = rng.randrange(n)
            row = rng.choice([r for r in range(n) if r != state[col]])
            new = state[:col] + (row,) + state[col + 1:]
            new_score = queen_fitness(new)
            evaluations += 1
            delta = new_score - score
            accept = delta >= 0 or rng.random() < math.exp(delta / max(T, 1e-12))
            T *= alpha
            if not accept:
                continue
        state, score = new, new_score
        if score > best_score:
            best, best_score = state, score
    return dict(state=best, score=best_score, success=best_score == target,
                evaluations=evaluations, steps=steps)


def compare_local(runs=300, seed=42):
    """Paired starts; seed 42+i membangkitkan state dan proposal run ke-i."""
    rows = []
    for i in range(runs):
        rng = random.Random(seed + i)
        initial = tuple(rng.randrange(8) for _ in range(8))
        for method in ('HC', 'SA'):
            rows.append(dict(run=i, method=method, **local_queens(initial, method, seed + i)))
    return rows


def restart_hc(n=8, restarts=20, seed=42):
    rng = random.Random(seed)
    best = None
    for attempt in range(restarts):
        initial = tuple(rng.randrange(n) for _ in range(n))
        row = local_queens(initial, 'HC')
        if best is None or row['score'] > best['score']:
            best = row
        if row['success']:
            break
    return dict(best=best, attempts=attempt + 1)
