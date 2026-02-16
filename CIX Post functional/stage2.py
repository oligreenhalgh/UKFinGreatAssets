"""
LP for portfolio sector rebalancing (additions-only) with a risk-penalty term.

"""

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple
from pathlib import Path
import math

import pulp

try:
    import pandas as pd
except ImportError:
    pd = None  # Will raise clear error in load_deals_from_csv


# Default CSV path
DEFAULT_CSV_PATH = Path(__file__).parent / "UKFIN_combined_dataset_FINAL (1).csv"


@dataclass(frozen=True)
class Deal:
    deal_id: str
    sector: str
    a: float   # deal size in GBP
    r1: float
    r2: float
    r3: float


def load_deals_from_csv(
    csv_path: Optional[str] = None,
    sectors: Optional[Sequence[str]] = None,
    deal_size_column: str = "Turnover",
) -> List[Deal]:
    """
    Load deals from the UKFIN dataset CSV file.
    
    Args:
        csv_path: Path to CSV file (defaults to bundled dataset)
        sectors: Optional list of sectors to filter by. If None, loads all sectors.
        deal_size_column: Column to use as deal size 'a' (default: "Turnover")
        
    Returns:
        List of Deal objects
        
    Risk metrics mapping:
        r1: Current Ratio (liquidity risk - higher is better)
        r2: ICR - Interest Coverage Ratio (debt service risk - higher is better)  
        r3: EBITDA / Turnover ratio (profitability risk - higher is better)
    """
    if pd is None:
        raise ImportError("pandas is required: pip install pandas")
    
    if csv_path is None:
        csv_path = DEFAULT_CSV_PATH
    
    df = pd.read_csv(csv_path)
    
    # Filter by sectors if specified
    if sectors:
        df = df[df["Sector"].isin(sectors)]
    
    deals = []
    for _, row in df.iterrows():
        try:
            # Extract deal size - use a fraction of turnover as investable amount
            # Typically an investment deal would be a portion of company value
            turnover = float(row.get(deal_size_column, 0) or 0)
            if turnover <= 0:
                # Fallback to Total Assets or Net Assets
                turnover = float(row.get("Total Assets", 0) or 0)
            if turnover <= 0:
                continue  # Skip deals with no valid size
            
            # Deal size is 10% of turnover (realistic debt/equity allocation)
            deal_size = turnover * 0.10
            
            # Extract risk metrics (handle #DIV/0! and missing values)
            def safe_float(val, default=1.0):
                if pd.isna(val) or val == "#DIV/0!" or val == "":
                    return default
                try:
                    result = float(val)
                    return result if result > 0 and not math.isinf(result) else default
                except (ValueError, TypeError):
                    return default
            
            r1 = safe_float(row.get("Currrent Ratio", 1.0), 1.0)  # Note: CSV has typo "Currrent"
            r2 = safe_float(row.get("ICR", 1.0), 1.0)
            
            # Calculate r3 as EBITDA margin (profitability indicator)
            ebitda = safe_float(row.get("EBITDA", 0), 0)
            turnover = safe_float(row.get("Turnover", 1), 1)
            r3 = (ebitda / turnover) if turnover > 0 else 0.1
            r3 = max(0.1, min(r3, 10.0))  # Clamp to reasonable range
            
            # Ensure all risk scores are positive
            r1 = max(0.1, r1)
            r2 = max(0.1, r2)
            
            deal = Deal(
                deal_id=str(row.get("Company Name", f"Unknown_{_}")),
                sector=str(row.get("Sector", "Unknown")),
                a=deal_size,
                r1=r1,
                r2=r2,
                r3=r3,
            )
            deals.append(deal)
            
        except Exception:
            # Skip malformed rows
            continue
    
    return deals


def solve_investment_bundle_lp(
    *,
    sectors: Sequence[str],
    current_gbp_by_sector: Dict[str, float],    # C_i
    desired_weight_by_sector: Dict[str, float], # d_i
    deals: Sequence[Deal],
    budget_gbp: float,                          # B
    solver: Optional[pulp.LpSolver] = None,
    msg: bool = False,
) -> Dict[str, float]:
    """
    Solves the LP and returns only y_j (fraction of each deal to take), as requested.

    Returns:
        y_by_deal_id: mapping deal_id -> y_j in [0,1]
    """
    # ----------------------------
    # Minimal validation
    # ----------------------------
    sectors = list(sectors)
    sector_set = set(sectors)

    # Ensure all sectors have C_i and d_i
    for s in sectors:
        if s not in current_gbp_by_sector:
            raise ValueError(f"Missing current capital C_i for sector '{s}'.")
        if s not in desired_weight_by_sector:
            raise ValueError(f"Missing desired weight d_i for sector '{s}'.")

    # Ensure desired weights sum to 1 (within tolerance)
    d_sum = sum(float(desired_weight_by_sector[s]) for s in sectors)
    if abs(d_sum - 1.0) > 1e-8:
        raise ValueError(f"Desired weights must sum to 1. Got {d_sum}.")

    # Deals sanity checks
    for d in deals:
        if d.sector not in sector_set:
            raise ValueError(f"Deal '{d.deal_id}' references unknown sector '{d.sector}'.")
        if d.a <= 0:
            raise ValueError(f"Deal '{d.deal_id}' has non-positive size a={d.a}.")
        R = d.r1 + d.r2 + d.r3
        if R <= 0:
            raise ValueError(
                f"Deal '{d.deal_id}' has non-positive risk score r1+r2+r3={R}."
            )

    # Total current portfolio size C
    C_total = sum(float(current_gbp_by_sector[s]) for s in sectors)

    # ----------------------------
    # Build LP
    # ----------------------------
    model = pulp.LpProblem("investment_bundle_rebalance_lp", pulp.LpMinimize)

    # Decision variables: y_j in [0,1]
    y = {
        d.deal_id: pulp.LpVariable(f"y_{d.deal_id}", lowBound=0, upBound=1, cat=pulp.LpContinuous)
        for d in deals
    }

    # Helper variables
    x = {s: pulp.LpVariable(f"x_{s}", lowBound=0, cat=pulp.LpContinuous) for s in sectors}  # x_i
    X = pulp.LpVariable("X_total_new_gbp", lowBound=0, cat=pulp.LpContinuous)              # X
    t = pulp.LpVariable("t_total_portfolio_gbp", lowBound=0, cat=pulp.LpContinuous)        # t
    u = {s: pulp.LpVariable(f"u_abs_dev_{s}", lowBound=0, cat=pulp.LpContinuous) for s in sectors}  # u_i

    # Index deals by sector for convenience
    deals_by_sector: Dict[str, List[Deal]] = {s: [] for s in sectors}
    for d in deals:
        deals_by_sector[d.sector].append(d)

    # x_i = sum_{j: s(j)=i} a_j y_j
    for s in sectors:
        model += (
            x[s] == pulp.lpSum(d.a * y[d.deal_id] for d in deals_by_sector[s]),
            f"sector_topup_{s}",
        )

    # X = sum_j a_j y_j
    model += (
        X == pulp.lpSum(d.a * y[d.deal_id] for d in deals),
        "total_new_investment",
    )

    # t = C + X
    model += (t == float(C_total) + X, "total_portfolio_after")

    # Budget option A: X <= B
    model += (X <= float(budget_gbp), "budget_option_A")

    # Absolute deviation constraints:
    # g_i = (C_i + x_i) - d_i t
    # g_i <= u_i and -g_i <= u_i
    for s in sectors:
        C_i = float(current_gbp_by_sector[s])
        d_i = float(desired_weight_by_sector[s])
        g = (C_i + x[s]) - (d_i * t)
        model += (g <= u[s], f"abs_pos_{s}")
        model += (-g <= u[s], f"abs_neg_{s}")

    # Objective: sum_i u_i + sum_j (a_j y_j / (r1+r2+r3))
    model += (
        pulp.lpSum(u[s] for s in sectors)
        + pulp.lpSum(
            (d.a * y[d.deal_id]) / (d.r1 + d.r2 + d.r3)
            for d in deals
        ),
        "objective",
    )

    # ----------------------------
    # Solve
    # ----------------------------
    if solver is None:
        solver = pulp.PULP_CBC_CMD(msg=msg)

    status = model.solve(solver)
    status_str = pulp.LpStatus.get(status, str(status))
    if status_str not in ("Optimal", "Feasible"):
        raise RuntimeError(f"Solver status: {status_str}")

    # Return only y_j
    y_out = {deal_id: float(pulp.value(var)) for deal_id, var in y.items()}
    return y_out


# ----------------------------
# Example usage (replace with your data)
# ----------------------------
if __name__ == "__main__":
    sectors = ["Retail", "Defence", "Finance"]

    current = {"Retail": 7_000_000, "Defence": 0, "Finance": 2_000_000}
    desired = {"Retail": 0.50, "Defence": 0.30, "Finance": 0.20}

    deals = [
        Deal("D1", "Retail", 5_000_000, 2.0, 3.0, 4.0),
        Deal("D2", "Defence", 4_000_000, 5.0, 5.0, 5.0),
        Deal("D3", "Finance", 3_000_000, 1.0, 2.0, 2.0),
    ]

    y = solve_investment_bundle_lp(
        sectors=sectors,
        current_gbp_by_sector=current,
        desired_weight_by_sector=desired,
        deals=deals,
        budget_gbp=6_000_000,
        msg=False,
    )

    for k, v in y.items():
        print(k, v)