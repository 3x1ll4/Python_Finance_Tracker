
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import csv
import math
from pathlib import Path
from datetime import date, datetime

# ==================================
# COLORS AND SETTINGS
# ==================================

BG = "#101827"
CARD = "#1E293B"
WHITE = "#FFFFFF"
GRAY = "#94A3B8"
BLUE = "#38BDF8"
GREEN = "#4ADE80"
RED = "#FB7185"
PURPLE = "#C084FC"

DB_PATH = Path(__file__).resolve().parent / "finance_tracker.db"


def money(value):
    return f"${value:,.2f}"


def valid_amount(text, allow_zero=False):
    try:
        value = round(float(text), 2)

        if not math.isfinite(value):
            raise ValueError

        if allow_zero:
            if value < 0:
                raise ValueError
        elif value <= 0:
            raise ValueError

        return value

    except (ValueError, OverflowError):
        raise ValueError("Enter a valid dollar amount.")


def connect():
    return sqlite3.connect(DB_PATH)


# ==================================
# DATABASE SETUP
# ==================================

def setup_database():
    with connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_type TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                transaction_date TEXT
            )
        """)

        columns = {
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(transactions)"
            )
        }

        if "transaction_date" not in columns:
            conn.execute("""
                ALTER TABLE transactions
                ADD COLUMN transaction_date TEXT
            """)

        conn.execute("""
            UPDATE transactions
            SET transaction_date = ?
            WHERE transaction_date IS NULL
        """, (date.today().isoformat(),))

        conn.execute("""
            CREATE TABLE IF NOT EXISTS savings_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_name TEXT NOT NULL,
                target_amount REAL NOT NULL,
                current_amount REAL NOT NULL DEFAULT 0
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS budgets (
                category TEXT PRIMARY KEY,
                monthly_limit REAL NOT NULL
            )
        """)


setup_database()


# ==================================
# MAIN WINDOW
# ==================================

root = tk.Tk()
root.title("Personal Finance Tracker")
root.geometry("1100x780")
root.minsize(850, 600)
root.configure(bg=BG)

style = ttk.Style(root)
style.theme_use("clam")

style.configure(
    "Finance.Treeview",
    background=CARD,
    fieldbackground=CARD,
    foreground=WHITE,
    rowheight=30,
    font=("Arial", 10)
)

style.configure(
    "Finance.Treeview.Heading",
    background="#334155",
    foreground=WHITE,
    font=("Arial", 10, "bold")
)

style.map(
    "Finance.Treeview",
    background=[("selected", "#0369A1")],
    foreground=[("selected", WHITE)]
)

style.configure(
    "Goal.Horizontal.TProgressbar",
    troughcolor="#334155",
    background=PURPLE
)

main = tk.Frame(root, bg=BG)
main.pack(
    fill="both",
    expand=True,
    padx=24,
    pady=10
)


# ==================================
# HEADER
# ==================================

tk.Label(
    main,
    text="PERSONAL FINANCE TRACKER",
    font=("Arial", 23, "bold"),
    bg=BG,
    fg=WHITE
).pack(pady=(6, 3))

tk.Label(
    main,
    text="Manage your money. Track your goals.",
    font=("Arial", 12),
    bg=BG,
    fg=GRAY
).pack()

tk.Label(
    main,
    text="Financial Dashboard",
    font=("Arial", 18, "bold"),
    bg=BG,
    fg=BLUE
).pack(pady=(15, 12))


# ==================================
# DASHBOARD CARDS
# ==================================

cards = tk.Frame(main, bg=BG)
cards.pack(fill="x", pady=(0, 12))

for column in range(4):
    cards.columnconfigure(
        column,
        weight=1,
        uniform="cards"
    )


def create_card(label, color, column):
    box = tk.Frame(
        cards,
        bg=CARD,
        height=105,
        highlightthickness=1,
        highlightbackground="#334155"
    )

    box.grid(
        row=0,
        column=column,
        padx=5,
        sticky="ew"
    )

    box.grid_propagate(False)

    tk.Label(
        box,
        text=label,
        bg=CARD,
        fg=GRAY,
        font=("Arial", 12)
    ).pack(pady=(16, 8))

    value = tk.Label(
        box,
        text="$0.00",
        bg=CARD,
        fg=color,
        font=("Arial", 20, "bold")
    )
    value.pack()

    return value


balance_label = create_card(
    "Total Balance", BLUE, 0
)

income_label = create_card(
    "Total Income", GREEN, 1
)

expenses_label = create_card(
    "Total Expenses", RED, 2
)

savings_label = create_card(
    "Goal Savings", PURPLE, 3
)


# ==================================
# UPDATE DASHBOARD
# ==================================

def update_dashboard():
    with connect() as conn:
        income, expenses = conn.execute("""
            SELECT
                COALESCE(
                    SUM(
                        CASE
                            WHEN transaction_type = 'Income'
                            THEN amount ELSE 0
                        END
                    ), 0
                ),
                COALESCE(
                    SUM(
                        CASE
                            WHEN transaction_type = 'Expense'
                            THEN amount ELSE 0
                        END
                    ), 0
                )
            FROM transactions
        """).fetchone()

        savings = conn.execute("""
            SELECT COALESCE(SUM(current_amount), 0)
            FROM savings_goals
        """).fetchone()[0]

    balance_label.config(
        text=money(income - expenses)
    )

    income_label.config(
        text=money(income)
    )

    expenses_label.config(
        text=money(expenses)
    )

    savings_label.config(
        text=money(savings)
    )


# ==================================
# BUTTON CONTAINER
# ==================================

buttons = tk.Frame(main, bg=BG)
buttons.pack(pady=(0, 11))

for column in range(3):
    buttons.columnconfigure(column, weight=1)


# ==================================
# TRANSACTION HISTORY
# ==================================

history = tk.Frame(main, bg=BG)
history.pack(fill="both", expand=True)

tk.Label(
    history,
    text="Recent Transactions",
    font=("Arial", 17, "bold"),
    bg=BG,
    fg=WHITE
).pack(anchor="w", pady=(0, 8))

table_holder = tk.Frame(history, bg=BG)
table_holder.pack(fill="both", expand=True)

columns = (
    "ID",
    "Date",
    "Type",
    "Amount",
    "Category",
    "Description"
)

table = ttk.Treeview(
    table_holder,
    columns=columns,
    show="headings",
    style="Finance.Treeview",
    height=7
)

column_widths = [
    ("ID", 55),
    ("Date", 115),
    ("Type", 100),
    ("Amount", 115),
    ("Category", 150),
    ("Description", 300)
]

for name, width in column_widths:
    table.heading(name, text=name)

    table.column(
        name,
        width=width,
        minwidth=50,
        anchor="e" if name == "Amount" else "w"
    )

scroll = ttk.Scrollbar(
    table_holder,
    orient="vertical",
    command=table.yview
)

table.configure(
    yscrollcommand=scroll.set
)

scroll.pack(side="right", fill="y")

table.pack(
    side="left",
    fill="both",
    expand=True
)


def load_transactions():
    for item in table.get_children():
        table.delete(item)

    with connect() as conn:
        records = conn.execute("""
            SELECT
                id,
                transaction_date,
                transaction_type,
                amount,
                category,
                description
            FROM transactions
            ORDER BY transaction_date DESC, id DESC
            LIMIT 200
        """).fetchall()

    for record in records:
        (
            record_id,
            when,
            kind,
            amount,
            category,
            description
        ) = record

        table.insert(
            "",
            "end",
            values=(
                record_id,
                when or "",
                kind,
                money(amount),
                category,
                description or ""
            )
        )


# ==================================
# HELPER FUNCTIONS
# ==================================

def create_field(parent, label):
    tk.Label(
        parent,
        text=label,
        bg=BG,
        fg=GRAY
    ).pack(pady=(9, 3))

    entry = tk.Entry(
        parent,
        width=35
    )
    entry.pack()

    return entry


def popup_window(title, size):
    popup = tk.Toplevel(root)
    popup.title(title)
    popup.geometry(size)
    popup.configure(bg=BG)
    popup.transient(root)

    return popup


# ==================================
# ADD TRANSACTION
# ==================================

def add_transaction():
    popup = popup_window(
        "Add Transaction",
        "430x540"
    )

    tk.Label(
        popup,
        text="Add New Transaction",
        font=("Arial", 18, "bold"),
        bg=BG,
        fg=WHITE
    ).pack(pady=(18, 8))

    tk.Label(
        popup,
        text="Transaction Type",
        bg=BG,
        fg=GRAY
    ).pack(pady=(8, 3))

    kind = ttk.Combobox(
        popup,
        values=("Income", "Expense"),
        state="readonly",
        width=32
    )

    kind.pack()
    kind.set("Expense")

    amount = create_field(
        popup,
        "Amount ($)"
    )

    tk.Label(
        popup,
        text="Category",
        bg=BG,
        fg=GRAY
    ).pack(pady=(9, 3))

    category = ttk.Combobox(
        popup,
        values=(
            "Salary",
            "Groceries",
            "Housing",
            "Transportation",
            "Utilities",
            "Entertainment",
            "Shopping",
            "Savings",
            "Other"
        ),
        width=32
    )

    category.pack()
    category.set("Groceries")

    description = create_field(
        popup,
        "Description"
    )

    when = create_field(
        popup,
        "Date (YYYY-MM-DD)"
    )

    when.insert(
        0,
        date.today().isoformat()
    )

    def save():
        try:
            value = valid_amount(amount.get())

            date_str = datetime.strptime(
                when.get().strip(),
                "%Y-%m-%d"
            ).date().isoformat()

            category_name = category.get().strip()

            if not category_name:
                raise ValueError(
                    "Enter a category."
                )

        except ValueError as error:
            messagebox.showerror(
                "Invalid Transaction",
                str(error),
                parent=popup
            )
            return

        with connect() as conn:
            conn.execute("""
                INSERT INTO transactions (
                    transaction_type,
                    amount,
                    category,
                    description,
                    transaction_date
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                kind.get(),
                value,
                category_name,
                description.get().strip(),
                date_str
            ))

        update_dashboard()
        load_transactions()
        popup.destroy()

    tk.Button(
        popup,
        text="Save Transaction",
        command=save,
        bg=GREEN,
        fg=BG,
        font=("Arial", 11, "bold"),
        padx=14,
        pady=9
    ).pack(pady=20)


# ==================================
# DELETE TRANSACTION
# ==================================

def delete_transaction():
    selected = table.selection()

    if not selected:
        messagebox.showwarning(
            "No Selection",
            "Select a transaction first."
        )
        return

    record_id = table.item(
        selected[0],
        "values"
    )[0]

    confirmed = messagebox.askyesno(
        "Confirm Delete",
        "Delete this transaction permanently?"
    )

    if not confirmed:
        return

    with connect() as conn:
        conn.execute(
            "DELETE FROM transactions WHERE id = ?",
            (record_id,)
        )

    update_dashboard()
    load_transactions()


# ==================================
# SPENDING BY CATEGORY CHART
# ==================================

def spending_chart():
    window = popup_window(
        "Spending by Category",
        "850x590"
    )

    tk.Label(
        window,
        text="Spending by Category",
        font=("Arial", 21, "bold"),
        bg=BG,
        fg=WHITE
    ).pack(pady=17)

    with connect() as conn:
        spending = conn.execute("""
            SELECT category, SUM(amount)
            FROM transactions
            WHERE transaction_type = 'Expense'
              AND category != 'Savings'
            GROUP BY category
            ORDER BY SUM(amount) DESC
        """).fetchall()

    chart = tk.Canvas(
        window,
        bg=CARD,
        highlightthickness=0
    )

    chart.pack(
        fill="both",
        expand=True,
        padx=30,
        pady=(0, 25)
    )

    colors = (
        BLUE,
        PURPLE,
        RED,
        GREEN,
        "#FBBF24",
        "#F472B6"
    )

    def draw(event=None):
        chart.delete("all")

        width = chart.winfo_width()
        height = chart.winfo_height()

        if not spending:
            chart.create_text(
                width / 2,
                height / 2,
                text="No expenses recorded yet.",
                fill=GRAY,
                font=("Arial", 14)
            )
            return

        max_amount = max(
            value for _, value in spending
        )

        row_height = max(
            1,
            (height - 35) / len(spending)
        )

        available_width = max(
            10,
            width - 310
        )

        for index, (category_name, value) in enumerate(spending):
            y = 20 + row_height * (index + 0.5)

            bar_length = (
                available_width * value / max_amount
            )

            chart.create_text(
                165,
                y,
                text=category_name,
                anchor="e",
                fill=WHITE,
                font=("Arial", 11)
            )

            chart.create_rectangle(
                175,
                y - 11,
                175 + bar_length,
                y + 11,
                fill=colors[index % len(colors)],
                outline=""
            )

            chart.create_text(
                185 + bar_length,
                y,
                text=money(value),
                anchor="w",
                fill=WHITE
            )

    chart.bind("<Configure>", draw)


# ==================================
# MONTHLY INCOME VS EXPENSES CHART
# ==================================

def monthly_chart():
    window = popup_window(
        "Monthly Income vs Expenses",
        "950x620"
    )

    tk.Label(
        window,
        text="Monthly Income vs Expenses",
        font=("Arial", 21, "bold"),
        bg=BG,
        fg=WHITE
    ).pack(pady=18)

    with connect() as conn:
        records = conn.execute("""
            SELECT
                strftime('%Y-%m', transaction_date),
                SUM(
                    CASE
                        WHEN transaction_type = 'Income'
                        THEN amount ELSE 0
                    END
                ),
                SUM(
                    CASE
                        WHEN transaction_type = 'Expense'
                        THEN amount ELSE 0
                    END
                )
            FROM transactions
            WHERE transaction_date IS NOT NULL
            GROUP BY strftime('%Y-%m', transaction_date)
            ORDER BY 1
        """).fetchall()

    chart = tk.Canvas(
        window,
        bg=CARD,
        highlightthickness=0
    )

    chart.pack(
        fill="both",
        expand=True,
        padx=25,
        pady=(0, 22)
    )

    def draw(event=None):
        chart.delete("all")

        width = chart.winfo_width()
        height = chart.winfo_height()

        if not records:
            chart.create_text(
                width / 2,
                height / 2,
                text="No dated transactions yet.",
                fill=GRAY
            )
            return

        left = 95
        top = 60
        right = 30
        bottom = 80

        plot_width = width - left - right
        plot_height = height - top - bottom

        if plot_width < 30 or plot_height < 30:
            return

        maximum = max(
            1,
            *(
                max(income, expenses)
                for _, income, expenses in records
            )
        )

        for index in range(5):
            fraction = index / 4

            y = top + plot_height * (
                1 - fraction
            )

            chart.create_line(
                left,
                y,
                width - right,
                y,
                fill="#334155",
                dash=(3, 5)
            )

            chart.create_text(
                left - 8,
                y,
                text=f"${maximum * fraction:,.0f}",
                fill=GRAY,
                anchor="e"
            )

        for x, color, label in (
            (left, GREEN, "Income"),
            (left + 120, RED, "Expenses")
        ):
            chart.create_rectangle(
                x,
                15,
                x + 14,
                29,
                fill=color,
                outline=""
            )

            chart.create_text(
                x + 20,
                22,
                text=label,
                anchor="w",
                fill=WHITE
            )

        group_width = plot_width / len(records)
        bar_width = min(32, group_width * 0.25)

        for index, (month, income, expenses) in enumerate(records):
            x = left + group_width * (
                index + 0.5
            )

            baseline = top + plot_height

            chart.create_rectangle(
                x - bar_width - 3,
                baseline - income / maximum * plot_height,
                x - 3,
                baseline,
                fill=GREEN,
                outline=""
            )

            chart.create_rectangle(
                x + 3,
                baseline - expenses / maximum * plot_height,
                x + bar_width + 3,
                baseline,
                fill=RED,
                outline=""
            )

            chart.create_text(
                x,
                baseline + 20,
                text=month,
                fill=WHITE
            )

            net = income - expenses

            chart.create_text(
                x,
                baseline + 43,
                text=f"Net: ${net:,.0f}",
                fill=GREEN if net >= 0 else RED
            )

    chart.bind("<Configure>", draw)


# ==================================
# SAVINGS GOALS
# ==================================

def savings_goals():
    popup = popup_window(
        "Savings Goals",
        "680x650"
    )

    tk.Label(
        popup,
        text="My Savings Goals",
        font=("Arial", 21, "bold"),
        bg=BG,
        fg=WHITE
    ).pack(pady=(15, 5))

    tk.Label(
        popup,
        text="Track goal balances separately from spending",
        bg=BG,
        fg=GRAY
    ).pack()

    form = tk.Frame(popup, bg=CARD)
    form.pack(
        fill="x",
        padx=22,
        pady=12
    )

    fields = {}

    field_definitions = (
        ("name", "Goal name"),
        ("target", "Target ($)"),
        ("saved", "Already saved ($)")
    )

    for index, (key, label) in enumerate(field_definitions):
        tk.Label(
            form,
            text=label,
            bg=CARD,
            fg=WHITE
        ).grid(
            row=index,
            column=0,
            padx=12,
            pady=8,
            sticky="w"
        )

        entry = tk.Entry(
            form,
            width=31
        )

        entry.grid(
            row=index,
            column=1,
            padx=12,
            pady=8,
            sticky="ew"
        )

        fields[key] = entry

    fields["saved"].insert(0, "0")

    form.columnconfigure(1, weight=1)

    list_outer = tk.Frame(popup, bg=BG)

    list_outer.pack(
        fill="both",
        expand=True,
        padx=22,
        pady=(6, 15)
    )

    list_canvas = tk.Canvas(
        list_outer,
        bg=BG,
        highlightthickness=0
    )

    side_scroll = ttk.Scrollbar(
        list_outer,
        orient="vertical",
        command=list_canvas.yview
    )

    goal_list = tk.Frame(
        list_canvas,
        bg=BG
    )

    inner_window = list_canvas.create_window(
        (0, 0),
        window=goal_list,
        anchor="nw"
    )

    goal_list.bind(
        "<Configure>",
        lambda event: list_canvas.configure(
            scrollregion=list_canvas.bbox("all")
        )
    )

    list_canvas.bind(
        "<Configure>",
        lambda event: list_canvas.itemconfigure(
            inner_window,
            width=event.width
        )
    )

    list_canvas.configure(
        yscrollcommand=side_scroll.set
    )

    side_scroll.pack(
        side="right",
        fill="y"
    )

    list_canvas.pack(
        side="left",
        fill="both",
        expand=True
    )

    def refresh():
        for widget in goal_list.winfo_children():
            widget.destroy()

        with connect() as conn:
            goals = conn.execute("""
                SELECT
                    id,
                    goal_name,
                    target_amount,
                    current_amount
                FROM savings_goals
                ORDER BY id DESC
            """).fetchall()

        if not goals:
            tk.Label(
                goal_list,
                text="No savings goals yet.",
                bg=BG,
                fg=GRAY
            ).pack(pady=20)

        for goal_id, name, target, saved in goals:
            box = tk.Frame(
                goal_list,
                bg=CARD
            )

            box.pack(
                fill="x",
                pady=6
            )

            tk.Label(
                box,
                text=name,
                bg=CARD,
                fg=WHITE,
                font=("Arial", 12, "bold")
            ).pack(
                anchor="w",
                padx=12,
                pady=(9, 2)
            )

            percent = (
                min(saved / target * 100, 100)
                if target > 0 else 0
            )

            tk.Label(
                box,
                text=(
                    f"{money(saved)} / {money(target)}"
                    f"   ({percent:.1f}%)"
                ),
                bg=CARD,
                fg=GREEN
            ).pack(
                anchor="w",
                padx=12,
                pady=3
            )

            ttk.Progressbar(
                box,
                style="Goal.Horizontal.TProgressbar",
                maximum=100,
                value=percent
            ).pack(
                fill="x",
                padx=12,
                pady=6
            )

            controls = tk.Frame(
                box,
                bg=CARD
            )

            controls.pack(
                fill="x",
                padx=12,
                pady=(0, 9)
            )

            entry = tk.Entry(
                controls,
                width=12
            )

            entry.pack(side="left")
            entry.insert(0, "25")

            def add_savings(
                selected_goal=goal_id,
                amount_entry=entry
            ):
                try:
                    amount = valid_amount(
                        amount_entry.get()
                    )
                except ValueError as error:
                    messagebox.showerror(
                        "Invalid Amount",
                        str(error),
                        parent=popup
                    )
                    return

                with connect() as conn:
                    conn.execute("""
                        UPDATE savings_goals
                        SET current_amount = current_amount + ?
                        WHERE id = ?
                    """, (amount, selected_goal))

                refresh()
                update_dashboard()

            def remove_goal(selected_goal=goal_id):
                confirmed = messagebox.askyesno(
                    "Delete Goal",
                    "Delete this savings goal?",
                    parent=popup
                )

                if not confirmed:
                    return

                with connect() as conn:
                    conn.execute("""
                        DELETE FROM savings_goals
                        WHERE id = ?
                    """, (selected_goal,))

                refresh()
                update_dashboard()

            tk.Button(
                controls,
                text="Add Savings",
                command=add_savings,
                bg=GREEN,
                fg=BG
            ).pack(
                side="left",
                padx=7
            )

            tk.Button(
                controls,
                text="Delete Goal",
                command=remove_goal,
                bg=RED,
                fg=BG
            ).pack(side="right")

    def create_goal():
        try:
            name = fields["name"].get().strip()

            if not name:
                raise ValueError(
                    "Enter a goal name."
                )

            target = valid_amount(
                fields["target"].get()
            )

            saved = valid_amount(
                fields["saved"].get(),
                allow_zero=True
            )

        except ValueError as error:
            messagebox.showerror(
                "Invalid Goal",
                str(error),
                parent=popup
            )
            return

        with connect() as conn:
            conn.execute("""
                INSERT INTO savings_goals (
                    goal_name,
                    target_amount,
                    current_amount
                )
                VALUES (?, ?, ?)
            """, (name, target, saved))

        for key in fields:
            fields[key].delete(0, "end")

        fields["saved"].insert(0, "0")

        refresh()
        update_dashboard()

    tk.Button(
        popup,
        text="+ Create Savings Goal",
        command=create_goal,
        bg=PURPLE,
        fg=BG,
        font=("Arial", 11, "bold"),
        pady=9
    ).pack(pady=(0, 6))

    refresh()


# ==================================
# MONTHLY BUDGETS
# ==================================

def budgets_window():
    popup = popup_window(
        "Monthly Budgets",
        "620x580"
    )

    tk.Label(
        popup,
        text="Monthly Budgets",
        bg=BG,
        fg=WHITE,
        font=("Arial", 20, "bold")
    ).pack(pady=17)

    form = tk.Frame(
        popup,
        bg=BG
    )

    form.pack(pady=5)

    category = ttk.Combobox(
        form,
        values=(
            "Groceries",
            "Housing",
            "Transportation",
            "Utilities",
            "Entertainment",
            "Shopping",
            "Other"
        ),
        width=20
    )

    category.grid(
        row=0,
        column=0,
        padx=6
    )

    category.set("Groceries")

    amount = tk.Entry(
        form,
        width=17
    )

    amount.grid(
        row=0,
        column=1,
        padx=6
    )

    amount.insert(0, "300")

    content = tk.Frame(
        popup,
        bg=BG
    )

    content.pack(
        fill="both",
        expand=True,
        padx=25,
        pady=16
    )

    def refresh():
        for child in content.winfo_children():
            child.destroy()

        month = date.today().strftime("%Y-%m")

        with connect() as conn:
            budgets = conn.execute("""
                SELECT
                    b.category,
                    b.monthly_limit,
                    COALESCE(
                        (
                            SELECT SUM(t.amount)
                            FROM transactions t
                            WHERE t.transaction_type = 'Expense'
                              AND t.category = b.category
                              AND substr(t.transaction_date, 1, 7) = ?
                        ), 0
                    )
                FROM budgets b
                ORDER BY b.category
            """, (month,)).fetchall()

        if not budgets:
            tk.Label(
                content,
                text="No budgets set yet.",
                bg=BG,
                fg=GRAY
            ).pack(pady=20)

        for category_name, limit, spent in budgets:
            box = tk.Frame(
                content,
                bg=CARD
            )

            box.pack(
                fill="x",
                pady=6
            )

            tk.Label(
                box,
                text=(
                    f"{category_name}: "
                    f"{money(spent)} / {money(limit)}"
                    f" ({month})"
                ),
                bg=CARD,
                fg=RED if spent > limit else WHITE
            ).pack(
                anchor="w",
                padx=10,
                pady=8
            )

            progress = min(
                100,
                100 * spent / limit
            )

            ttk.Progressbar(
                box,
                style="Goal.Horizontal.TProgressbar",
                maximum=100,
                value=progress
            ).pack(
                fill="x",
                padx=10,
                pady=(0, 8)
            )

    def save_budget():
        try:
            limit = valid_amount(
                amount.get()
            )

            category_name = category.get().strip()

            if not category_name:
                raise ValueError(
                    "Choose a category."
                )

        except ValueError as error:
            messagebox.showerror(
                "Invalid Budget",
                str(error),
                parent=popup
            )
            return

        with connect() as conn:
            conn.execute("""
                INSERT INTO budgets (
                    category,
                    monthly_limit
                )
                VALUES (?, ?)
                ON CONFLICT(category)
                DO UPDATE SET
                    monthly_limit = excluded.monthly_limit
            """, (category_name, limit))

        refresh()

    tk.Button(
        form,
        text="Set Budget",
        bg=GREEN,
        fg=BG,
        command=save_budget
    ).grid(
        row=0,
        column=2,
        padx=6
    )

    refresh()


# ==================================
# EXPORT TRANSACTIONS TO CSV
# ==================================

def export_csv():
    file_path = filedialog.asksaveasfilename(
        defaultextension=".csv",
        filetypes=[
            ("CSV files", "*.csv")
        ],
        initialfile="finance_transactions.csv"
    )

    if not file_path:
        return

    with connect() as conn:
        records = conn.execute("""
            SELECT
                transaction_date,
                transaction_type,
                amount,
                category,
                description
            FROM transactions
            ORDER BY transaction_date, id
        """).fetchall()

    with open(
        file_path,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as file:
        writer = csv.writer(file)

        writer.writerow([
            "Date",
            "Type",
            "Amount",
            "Category",
            "Description"
        ])

        writer.writerows(records)

    messagebox.showinfo(
        "Export Complete",
        f"Exported {len(records)} transactions."
    )


# ==================================
# BUTTON LAYOUT
# ==================================

def make_button(
    text,
    command,
    color,
    row,
    column
):
    button = tk.Button(
        buttons,
        text=text,
        command=command,
        bg=color,
        fg=BG,
        font=("Arial", 10, "bold"),
        padx=10,
        pady=7,
        width=24,
        cursor="hand2"
    )

    button.grid(
        row=row,
        column=column,
        padx=5,
        pady=4
    )


make_button(
    "+ Add Transaction",
    add_transaction,
    BLUE,
    0,
    0
)

make_button(
    "Delete Selected Transaction",
    delete_transaction,
    RED,
    0,
    1
)

make_button(
    "View Spending Chart",
    spending_chart,
    PURPLE,
    0,
    2
)

make_button(
    "Monthly Trends",
    monthly_chart,
    GREEN,
    1,
    0
)

make_button(
    "Savings Goals",
    savings_goals,
    BLUE,
    1,
    1
)

make_button(
    "Monthly Budgets",
    budgets_window,
    PURPLE,
    1,
    2
)

make_button(
    "Export CSV",
    export_csv,
    GREEN,
    2,
    1
)


# ==================================
# LOAD SAVED DATA AND START APP
# ==================================

update_dashboard()
load_transactions()

root.mainloop()
