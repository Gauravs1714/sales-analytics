"""Sample datasets so you can try the dashboard immediately."""
import numpy as np
import pandas as pd


def sales_df():
    rng = np.random.default_rng(2026)
    prods = [("Laptop", "Electronics", 52000, 41000, 3), ("Smartphone", "Electronics", 24000, 19000, 4),
             ("Headphones", "Electronics", 3500, 2200, 6), ("Office Chair", "Furniture", 8500, 5600, 4),
             ("Standing Desk", "Furniture", 18000, 12500, 2), ("Notebook Pack", "Stationery", 350, 180, 12),
             ("Printer", "Electronics", 11000, 8300, 2), ("Water Bottle", "Home", 600, 320, 8)]
    rows = []
    for i in range(1, 401):
        name, cat, price, cost, qmax = prods[min(int(rng.random() * rng.random() * len(prods) * 1.3), len(prods) - 1)]
        month = int(rng.integers(1, 13))
        qty = int(1 + rng.integers(0, max(1, int(qmax * (1 + month * 0.04)))))
        unit_cost = round(cost * (0.96 + rng.random() * 0.08))
        rows.append({"Order ID": f"ORD{1000 + i}", "Date": f"2025-{month:02d}-{int(rng.integers(1, 29)):02d}",
                     "Region": str(rng.choice(["North", "South", "East", "West"])), "Product": name,
                     "Category": cat, "Quantity": qty, "Unit Price": price, "Cost": unit_cost,
                     "Revenue": qty * price, "Profit": qty * (price - unit_cost)})
    df = pd.DataFrame(rows)
    dirty = pd.concat([df, df.sample(10, random_state=1), pd.DataFrame([{}, {}])], ignore_index=True)
    return dirty


def staff_df():
    rng = np.random.default_rng(7)
    depts = {"Engineering": 90000, "Sales": 60000, "HR": 50000, "Finance": 65000, "Support": 40000}
    rows = []
    for i in range(1, 161):
        d = str(rng.choice(list(depts)))
        exp = int(rng.integers(0, 12))
        rows.append({"Emp ID": f"E{100 + i}", "Department": d, "City": str(rng.choice(["Pune", "Hyderabad", "Nashik", "Delhi"])),
                     "Joined": f"{int(rng.integers(1, 29)):02d}/{int(rng.integers(1, 13)):02d}/{int(rng.integers(2018, 2026))}",
                     "Experience (yrs)": exp, "Salary": round(depts[d] * (1 + exp * 0.05) * (0.9 + rng.random() * 0.25)),
                     "Rating": round(2.5 + rng.random() * 2.5, 1)})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    sales_df().to_csv("sample_sales.csv", index=False)
    staff_df().to_excel("sample_staff.xlsx", index=False)
    print("Wrote sample_sales.csv and sample_staff.xlsx")
