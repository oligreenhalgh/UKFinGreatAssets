"""
Main Investment Pipeline

Orchestrates the end-to-end investment thesis processing:
1. Parse PDF investment thesis (stage1)
2. Load deals from CSV dataset (stage2)
3. Run portfolio optimization LP (stage2)
4. Output recommended deal allocations
"""

import sys
import argparse
from pathlib import Path
from typing import Dict, List, Optional

from stage1 import parse_investment_thesis, ThesisOutput, VALID_SECTORS
from stage2 import (
    load_deals_from_csv,
    solve_investment_bundle_lp,
    Deal,
    DEFAULT_CSV_PATH,
)


def run_pipeline(
    pdf_path: str,
    csv_path: Optional[str] = None,
    current_portfolio: Optional[Dict[str, float]] = None,
    verbose: bool = True,
) -> Dict:
    """
    Run the complete investment pipeline.
    
    Args:
        pdf_path: Path to the investment thesis PDF
        csv_path: Path to deals CSV (defaults to bundled dataset)
        current_portfolio: Optional dict of current GBP holdings by sector
        verbose: Whether to print progress messages
        
    Returns:
        Dictionary containing:
            - thesis: Parsed thesis data
            - deals_selected: List of (deal_id, fraction, amount) tuples
            - total_investment: Total GBP to be invested
            - sector_allocation: Final sector allocation breakdown
    """
    if verbose:
        print("=" * 60)
        print("INVESTMENT THESIS PIPELINE")
        print("=" * 60)
    
    # Step 1: Parse the investment thesis
    if verbose:
        print(f"\n[1/4] Parsing investment thesis: {pdf_path}")
    
    thesis = parse_investment_thesis(pdf_path)
    
    if verbose:
        print(f"      Investment Amount: £{thesis.amount_millions}M")
        print(f"      Focus Sectors (to dilute): {list(thesis.desired_sectors.keys())}")
    
    # Step 2: Load deals from ALL sectors (we buy in non-focus sectors to dilute focus)
    # Focus sectors = sectors the thesis says are overweight and need diluting
    focus_sectors = set(thesis.desired_sectors.keys())
    all_sectors = set(VALID_SECTORS)
    non_focus_sectors = list(all_sectors - focus_sectors)
    
    if verbose:
        print(f"\n[2/4] Loading deals from non-focus sectors: {non_focus_sectors}")
    
    deals = load_deals_from_csv(
        csv_path=csv_path,
        sectors=non_focus_sectors,  # Buy in OTHER sectors to dilute focus
    )
    
    if not deals:
        raise ValueError(f"No deals found for sectors: {non_focus_sectors}")
    
    if verbose:
        print(f"      Found {len(deals)} deals")
    
    # Step 3: Prepare inputs for LP solver
    if verbose:
        print(f"\n[3/4] Running portfolio optimization...")
    
    # All sectors involved in the optimization
    all_involved_sectors = list(focus_sectors | set(non_focus_sectors))
    
    # Build current portfolio:
    # - Focus sectors have high current exposure (simulated based on thesis weights)
    # - Non-focus sectors have zero current exposure
    total_current = thesis.amount_millions * 1_000_000 * 2  # Assume current portfolio is 2x budget
    
    if current_portfolio is None:
        current_portfolio = {}
        # Focus sectors get proportional current holdings based on thesis weights
        focus_weight_sum = sum(thesis.desired_sectors.values())
        for sector in all_involved_sectors:
            if sector in focus_sectors:
                # Current weight is proportional to thesis weight (overweight)
                sector_weight = thesis.desired_sectors.get(sector, 0) / focus_weight_sum
                current_portfolio[sector] = total_current * sector_weight
            else:
                # Non-focus sectors have minimal current holdings
                current_portfolio[sector] = 0.0
    
    # Build desired weights: 
    # - Dilute focus sectors to lower weights
    # - Increase non-focus sectors
    num_non_focus = len(non_focus_sectors)
    focus_dilution_target = 0.3  # Target: focus sectors should be 30% total after rebalancing
    
    desired_weights = {}
    focus_weight_sum = sum(thesis.desired_sectors.values())
    for sector in all_involved_sectors:
        if sector in focus_sectors:
            # Focus sectors get reduced weight (dilution)
            relative_weight = thesis.desired_sectors.get(sector, 0) / focus_weight_sum
            desired_weights[sector] = focus_dilution_target * relative_weight
        else:
            # Non-focus sectors share the remaining weight equally
            desired_weights[sector] = (1 - focus_dilution_target) / num_non_focus if num_non_focus > 0 else 0
    
    if verbose:
        print(f"      Current portfolio (focus sectors): {sum(v for k, v in current_portfolio.items() if k in focus_sectors):,.0f} GBP")
        print(f"      Target: dilute focus sectors to {focus_dilution_target:.0%} of portfolio")
    
    # Convert budget to GBP
    budget_gbp = thesis.amount_millions * 1_000_000
    
    # Run the LP solver
    y_results = solve_investment_bundle_lp(
        sectors=all_involved_sectors,
        current_gbp_by_sector=current_portfolio,
        desired_weight_by_sector=desired_weights,
        deals=deals,
        budget_gbp=budget_gbp,
        msg=False,
    )
    
    # Step 4: Process results
    if verbose:
        print(f"\n[4/4] Processing results...")
    
    # Build deal lookup
    deal_by_id = {d.deal_id: d for d in deals}
    
    # Filter to deals with non-zero allocation
    deals_selected = []
    total_investment = 0.0
    sector_investment = {s: 0.0 for s in all_involved_sectors}
    
    for deal_id, fraction in y_results.items():
        if fraction > 0.001:  # Threshold for meaningful allocation
            deal = deal_by_id[deal_id]
            amount = fraction * deal.a
            deals_selected.append({
                "deal_id": deal_id,
                "sector": deal.sector,
                "fraction": round(fraction, 4),
                "amount_gbp": round(amount, 2),
                "deal_size_gbp": deal.a,
            })
            total_investment += amount
            if deal.sector in sector_investment:
                sector_investment[deal.sector] += amount
    
    # Sort by amount descending
    deals_selected.sort(key=lambda x: x["amount_gbp"], reverse=True)
    
    # Calculate final sector allocation percentages
    sector_allocation = {}
    if total_investment > 0:
        for sector, amount in sector_investment.items():
            sector_allocation[sector] = round(amount / total_investment, 4)
    
    result = {
        "thesis": {
            "amount_millions": thesis.amount_millions,
            "desired_sectors": thesis.desired_sectors,
            "overview": thesis.overview,
            "kpis": thesis.kpis,
            "timeline": thesis.timeline,
        },
        "deals_selected": deals_selected,
        "total_investment_gbp": round(total_investment, 2),
        "sector_allocation": sector_allocation,
    }
    
    if verbose:
        _print_results(result)
    
    return result


def _print_results(result: Dict) -> None:
    """Pretty print pipeline results."""
    print("\n" + "=" * 60)
    print("INVESTMENT RECOMMENDATIONS")
    print("=" * 60)
    
    thesis = result["thesis"]
    print(f"\n[THESIS SUMMARY]")
    print(f"   Budget: GBP {thesis['amount_millions']}M")
    print(f"   Overview: {thesis['overview']}")
    if thesis.get("timeline"):
        print(f"   Timeline: {thesis['timeline']}")
    if thesis.get("kpis"):
        print(f"   KPIs: {', '.join(thesis['kpis'])}")
    
    print(f"\n[TARGET SECTOR WEIGHTS]")
    for sector, weight in thesis["desired_sectors"].items():
        print(f"   {sector}: {weight:.1%}")
    
    print(f"\n[RECOMMENDED DEALS] ({len(result['deals_selected'])} total)")
    print("-" * 60)
    
    for deal in result["deals_selected"][:20]:  # Show top 20
        fraction_pct = deal["fraction"] * 100
        print(f"   {deal['deal_id'][:40]:<40}")
        print(f"      Sector: {deal['sector']}")
        print(f"      Invest: GBP {deal['amount_gbp']:,.2f} ({fraction_pct:.1f}% of GBP {deal['deal_size_gbp']:,.0f} deal)")
        print()
    
    if len(result["deals_selected"]) > 20:
        print(f"   ... and {len(result['deals_selected']) - 20} more deals")
    
    print(f"\n[FINAL SECTOR ALLOCATION]")
    for sector, weight in result["sector_allocation"].items():
        print(f"   {sector}: {weight:.1%}")
    
    print(f"\n[TOTAL INVESTMENT]: GBP {result['total_investment_gbp']:,.2f}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Investment Thesis Pipeline - Parse PDF and recommend deals"
    )
    parser.add_argument(
        "pdf_path",
        help="Path to investment thesis PDF file",
    )
    parser.add_argument(
        "--csv",
        default=None,
        help="Path to deals CSV file (defaults to bundled UKFIN dataset)",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Output JSON file path (optional)",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress verbose output",
    )
    
    args = parser.parse_args()
    
    try:
        result = run_pipeline(
            pdf_path=args.pdf_path,
            csv_path=args.csv,
            verbose=not args.quiet,
        )
        
        if args.output:
            import json
            with open(args.output, "w") as f:
                json.dump(result, f, indent=2)
            print(f"\nResults saved to: {args.output}")
            
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise


if __name__ == "__main__":
    main()
