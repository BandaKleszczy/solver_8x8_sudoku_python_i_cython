from PIL import Image, ImageTk
import subprocess
import multiprocessing
import sys
import threading
from tkinter import messagebox
import tkinter as tk
import os

CELL = 60
SIZE = 8
RADIUS = 6

COLORS = {
    "BLUE": "#4a90e2",
    "ORANGE": "#f5a623",
    "THERMO": "#d0021b"
}

ORDER = ["BLUE", "ORANGE", "THERMO"]


# =========================
# PARSER lines.txt
# =========================

def parse_lines_file(path):
    lines = {k: [] for k in ORDER}
    if not os.path.exists(path):
        return lines

    section = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith("["):
                section = line.strip("[]")
                continue

            _, rest = line.split(":")
            cells = []
            for t in rest.split():
                r = int(t[1]) - 1
                c = int(t[3]) - 1
                cells.append((r, c))
            lines[section].append(cells)

    return lines


# =========================
# GUI
# =========================

class LineEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Line Editor 8x8")

        self.canvas = tk.Canvas(
            root,
            width=SIZE * CELL,
            height=SIZE * CELL,
            bg="white"
        )
        self.canvas.pack(side="left")

        # =========================
        # TŁO PNG (8x8)
        # =========================
        self.bg_image = Image.open("grid_bg.png")
        self.bg_photo = ImageTk.PhotoImage(self.bg_image)

        self.bg_id = self.canvas.create_image(
            0, 0,
            anchor="nw",
            image=self.bg_photo
        )

        self.current_type = "BLUE"
        self.current_line = []

        self.lines = parse_lines_file("lines.txt")

        self.draw_grid()
        self.redraw_all_lines()

        self.canvas.bind("<Button-1>", self.on_click)
        self.build_controls()

    def same_line(self, a, b):
        return a == b or a == list(reversed(b))


    # -------------------------

    def draw_grid(self):
        for r in range(SIZE):
            for c in range(SIZE):
                x1 = c * CELL
                y1 = r * CELL
                x2 = x1 + CELL
                y2 = y1 + CELL

                self.canvas.create_rectangle(
                    x1, y1, x2, y2,
                    outline="black"
                )

                cx = x1 + CELL // 2
                cy = y1 + CELL // 2
                self.canvas.create_oval(
                    cx - RADIUS, cy - RADIUS,
                    cx + RADIUS, cy + RADIUS,
                    fill="black"
                )

    # -------------------------

    def cell_center(self, r, c):
        return (
            c * CELL + CELL // 2,
            r * CELL + CELL // 2
        )

    # -------------------------

    def on_click(self, event):
        c = event.x // CELL
        r = event.y // CELL
        if not (0 <= r < SIZE and 0 <= c < SIZE):
            return

        cell = (r, c)
        if self.current_line and cell == self.current_line[-1]:
            return

        self.current_line.append(cell)
        self.redraw()

    # -------------------------

    def redraw_all_lines(self):
        for t in ORDER:
            for line in self.lines[t]:
                self.draw_line(line, COLORS[t])

    # -------------------------

    def draw_line(self, line, color):
        if len(line) < 2:
            return
        points = []
        for r, c in line:
            points.extend(self.cell_center(r, c))

        self.canvas.create_line(
            *points,
            fill=color,
            width=4,
            capstyle=tk.ROUND,
            joinstyle=tk.ROUND
        )

    # -------------------------

    def redraw(self):
        self.canvas.delete("all")

        # tło ZAWSZE pierwsze
        self.bg_id = self.canvas.create_image(
            0, 0,
            anchor="nw",
            image=self.bg_photo
        )

        self.draw_grid()
        self.redraw_all_lines()
        self.draw_line(self.current_line, COLORS[self.current_type])


    # -------------------------

    def build_controls(self):
        panel = tk.Frame(self.root)
        panel.pack(side="right", fill="y", padx=10)

        tk.Label(panel, text="Typ linii").pack(pady=5)

        for t in ORDER:
            tk.Button(
                panel,
                text=t,
                command=lambda x=t: self.start_new_line(x)
            ).pack(fill="x", pady=2)

        tk.Button(
            panel,
            text="DELETE LINE",
            command=self.delete_line
        ).pack(fill="x", pady=10)

        tk.Button(
            panel,
            text="SAVE",
            command=self.save
        ).pack(fill="x")

        tk.Button(
            panel,
            text="SOLVE",
            bg="#4CAF50",
            fg="white",
            command=self.run_solver
        ).pack(fill="x", pady=10)


    # -------------------------

    # -------------------------

    def start_new_line(self, t):
        self.current_type = t
        self.current_line = []
        self.redraw()

    # -------------------------

    def delete_line(self):
        if self.current_line:
            self.current_line = []
        elif self.lines[self.current_type]:
            self.lines[self.current_type].pop()

        self.redraw()

    # -------------------------

    def save(self):
        self.commit_current_line()

        with open("lines.txt", "w", encoding="utf-8") as f:
            for section in ORDER:
                f.write(f"[{section}]\n")
                for i, line in enumerate(self.lines[section], 1):
                    cells = " ".join(
                        f"r{r+1}c{c+1}" for r, c in line
                    )
                    f.write(f"{section[0]}{i}: {cells}\n")
                f.write("\n")

        print("✔ Zapisano lines.txt")

    def run_solver(self):
        # najpierw zapisz aktualne linie
        self.save()

        # uruchom solver w osobnym wątku,
        # żeby GUI się nie zawiesiło
        threading.Thread(target=self._run_solver_bg, daemon=True).start()

    def _run_solver_bg(self):
        try:
            # uruchamiamy ten sam interpreter Pythona
            cmd = [sys.executable, "solver3.py"]

            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=os.getcwd()
            )

            if proc.returncode != 0:
                self.root.after(
                    0,
                    lambda: messagebox.showerror(
                        "Solver error",
                        proc.stderr
                    )
                )
                return

            output = proc.stdout.strip()

            self.root.after(
                0,
                lambda: messagebox.showinfo(
                    "Solver finished",
                    output
                )
            )

        except Exception as e:
            self.root.after(
                0,
                lambda: messagebox.showerror(
                    "Error",
                    str(e)
                )
            )


    def commit_current_line(self):
        if not self.current_line:
            return

        lines = self.lines[self.current_type]

        # toggle: usuń jeśli istnieje
        for i, line in enumerate(lines):
            if self.same_line(line, self.current_line):
                lines.pop(i)
                break
        else:
            lines.append(self.current_line)

        self.current_line = []

def delete_line(self):
    # jeśli coś aktualnie rysujemy – porzuć
    if self.current_line:
        self.current_line = []
    # w przeciwnym razie usuń ostatnią linię danego typu
    elif self.lines[self.current_type]:
        self.lines[self.current_type].pop()

    self.redraw()

# =========================
# START
# =========================

if __name__ == "__main__":
    multiprocessing.freeze_support()   # 🔑 KLUCZOWE NA WINDOWS

    root = tk.Tk()
    LineEditor(root)
    root.mainloop()