"""
Flask Web Application for Investment Pipeline

Serves the frontend UI and provides API endpoints for:
- Portfolio data
- Thesis insights  
- Deal recommendations from results.json
"""

import os
import json
import subprocess
import threading
from pathlib import Path
from flask import Flask, render_template, jsonify, request
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = Path(__file__).parent / 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Ensure upload folder exists
app.config['UPLOAD_FOLDER'].mkdir(exist_ok=True)

# Path to results file
RESULTS_PATH = Path(__file__).parent / 'results.json'
THESIS_PATH = Path(__file__).parent / 'thesis.pdf'

# Dummy portfolio data aligned with thesis sectors
DUMMY_PORTFOLIO = {
    "total_invested": 15000000,
    "average_roi": 14.29,
    "total_businesses": 20,
    "assets": [
        {"id": "AST001", "sector": "Financial", "location": "London", "loan_band": "250k-500k", "roi_band": "High (15%+)", "date": "2023-03-15", "risk_level": "Low Risk", "amount": 350000},
        {"id": "AST002", "sector": "Life_Science", "location": "Cambridge", "loan_band": "500k-750k", "roi_band": "High (15%+)", "date": "2023-01-20", "risk_level": "Low Risk", "amount": 620000},
        {"id": "AST003", "sector": "Financial", "location": "Edinburgh", "loan_band": "250k-500k", "roi_band": "Medium (10-15%)", "date": "2023-05-10", "risk_level": "Medium Risk", "amount": 400000},
        {"id": "AST004", "sector": "Life_Science", "location": "Oxford", "loan_band": "750k+", "roi_band": "High (15%+)", "date": "2023-02-28", "risk_level": "Low Risk", "amount": 850000},
        {"id": "AST005", "sector": "Financial", "location": "Manchester", "loan_band": "0-250k", "roi_band": "Medium (10-15%)", "date": "2023-04-05", "risk_level": "Medium Risk", "amount": 180000},
        {"id": "AST006", "sector": "Life_Science", "location": "London", "loan_band": "500k-750k", "roi_band": "High (15%+)", "date": "2023-06-12", "risk_level": "Low Risk", "amount": 550000},
        {"id": "AST007", "sector": "Financial", "location": "Birmingham", "loan_band": "250k-500k", "roi_band": "Medium (10-15%)", "date": "2023-03-22", "risk_level": "Medium Risk", "amount": 320000},
        {"id": "AST008", "sector": "Life_Science", "location": "Cambridge", "loan_band": "750k+", "roi_band": "High (15%+)", "date": "2023-07-01", "risk_level": "Low Risk", "amount": 920000},
        {"id": "AST009", "sector": "Financial", "location": "London", "loan_band": "250k-500k", "roi_band": "High (15%+)", "date": "2023-02-14", "risk_level": "Low Risk", "amount": 480000},
        {"id": "AST010", "sector": "Life_Science", "location": "Oxford", "loan_band": "500k-750k", "roi_band": "Medium (10-15%)", "date": "2023-04-18", "risk_level": "Medium Risk", "amount": 650000},
    ],
    "sector_breakdown": {
        "Financial": 0.70,
        "Life_Science": 0.30
    },
    "location_breakdown": {
        "London": 3500000,
        "Cambridge": 2800000,
        "Edinburgh": 1200000,
        "Oxford": 2100000,
        "Manchester": 1800000,
        "Birmingham": 1600000,
        "Leeds": 1000000,
        "Scotland": 1000000
    }
}


def load_results():
    """Load the latest results from results.json"""
    if RESULTS_PATH.exists():
        with open(RESULTS_PATH, 'r') as f:
            return json.load(f)
    return None


def run_pipeline_async(pdf_path):
    """Run the investment pipeline in background"""
    def run():
        subprocess.run([
            'python', 'main_pipeline.py', 
            str(pdf_path), 
            '-o', 'results.json'
        ], cwd=Path(__file__).parent)
    
    thread = threading.Thread(target=run)
    thread.start()


# ==================== PAGE ROUTES ====================

@app.route('/')
@app.route('/portfolio')
def portfolio():
    """Portfolio page with current holdings"""
    return render_template('portfolio.html', active='portfolio')


@app.route('/insights')
def insights():
    """Insights page with thesis upload and analysis"""
    results = load_results()
    thesis = results.get('thesis') if results else None
    return render_template('insights.html', active='insights', thesis=thesis)


@app.route('/marketplace')
def marketplace():
    """Marketplace page with deal recommendations"""
    results = load_results()
    return render_template('marketplace.html', active='marketplace', results=results)


@app.route('/exchange')
def exchange():
    """Exchange page with live transaction feed"""
    return render_template('exchange.html', active='exchange')


# ==================== API ROUTES ====================

@app.route('/api/portfolio')
def api_portfolio():
    """Return portfolio data"""
    return jsonify(DUMMY_PORTFOLIO)


@app.route('/api/thesis')
def api_thesis():
    """Return current thesis data"""
    results = load_results()
    if results and 'thesis' in results:
        return jsonify(results['thesis'])
    return jsonify(None)


@app.route('/api/deals')
def api_deals():
    """Return deal recommendations"""
    results = load_results()
    if results:
        return jsonify({
            'deals': results.get('deals_selected', []),
            'total_investment': results.get('total_investment_gbp', 0),
            'sector_allocation': results.get('sector_allocation', {}),
            'thesis': results.get('thesis', {})
        })
    return jsonify({'deals': [], 'total_investment': 0, 'sector_allocation': {}})


@app.route('/api/purchase-bundle', methods=['POST'])
def purchase_bundle():
    """Handle bundle purchase and update portfolio"""
    global DUMMY_PORTFOLIO
    
    results = load_results()
    if not results or not results.get('deals_selected'):
        return jsonify({'error': 'No deals to purchase'}), 400
    
    deals = results['deals_selected']
    total_new_investment = results.get('total_investment_gbp', 0)
    
    # Update total invested
    DUMMY_PORTFOLIO['total_invested'] += total_new_investment
    DUMMY_PORTFOLIO['total_businesses'] += len(deals)
    
    # Increase ROI slightly with each purchase (simulating portfolio improvement)
    import random
    roi_increase = random.uniform(0.5, 1.5)
    DUMMY_PORTFOLIO['average_roi'] = round(DUMMY_PORTFOLIO['average_roi'] + roi_increase, 2)
    
    # Add new assets to portfolio
    current_asset_count = len(DUMMY_PORTFOLIO['assets'])
    today = __import__('datetime').date.today().isoformat()
    
    for i, deal in enumerate(deals):
        new_asset = {
            'id': f'AST{current_asset_count + i + 1:03d}',
            'sector': deal.get('sector', 'Other').replace(' ', '_'),
            'location': 'London',  # Default location
            'loan_band': '250k-500k' if deal.get('amount_gbp', 0) < 500000 else '500k-750k' if deal.get('amount_gbp', 0) < 750000 else '750k+',
            'roi_band': 'High (15%+)',
            'date': today,
            'risk_level': 'Low Risk',
            'amount': deal.get('amount_gbp', 0)
        }
        DUMMY_PORTFOLIO['assets'].append(new_asset)
    
    # Recalculate sector breakdown from all assets
    sector_totals = {}
    total_amount = sum(a.get('amount', 0) for a in DUMMY_PORTFOLIO['assets'])
    
    for asset in DUMMY_PORTFOLIO['assets']:
        sector = asset.get('sector', 'Other')
        sector_totals[sector] = sector_totals.get(sector, 0) + asset.get('amount', 0)
    
    DUMMY_PORTFOLIO['sector_breakdown'] = {
        k: v / total_amount if total_amount > 0 else 0 
        for k, v in sector_totals.items()
    }
    
    # Update location breakdown
    for deal in deals:
        location = 'London'  # Default
        current = DUMMY_PORTFOLIO['location_breakdown'].get(location, 0)
        DUMMY_PORTFOLIO['location_breakdown'][location] = current + deal.get('amount_gbp', 0)
    
    return jsonify({
        'success': True,
        'message': f'Successfully purchased {len(deals)} deals for £{total_new_investment:,.2f}',
        'new_total_invested': DUMMY_PORTFOLIO['total_invested'],
        'new_total_businesses': DUMMY_PORTFOLIO['total_businesses'],
        'new_sector_breakdown': DUMMY_PORTFOLIO['sector_breakdown']
    })


@app.route('/api/upload-thesis', methods=['POST'])
def upload_thesis():
    """Handle thesis PDF upload and trigger pipeline"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and file.filename.lower().endswith('.pdf'):
        # Save the uploaded file
        filename = secure_filename(file.filename)
        filepath = app.config['UPLOAD_FOLDER'] / filename
        file.save(filepath)
        
        # Also copy as thesis.pdf for the pipeline
        import shutil
        shutil.copy(filepath, THESIS_PATH)
        
        # Run pipeline in background
        run_pipeline_async(THESIS_PATH)
        
        return jsonify({
            'success': True,
            'message': 'Thesis uploaded. Processing...',
            'filename': filename
        })
    
    return jsonify({'error': 'Invalid file type. Please upload a PDF.'}), 400


@app.route('/api/results-timestamp')
def results_timestamp():
    """Return timestamp of results file for polling"""
    if RESULTS_PATH.exists():
        return jsonify({
            'exists': True,
            'timestamp': RESULTS_PATH.stat().st_mtime
        })
    return jsonify({'exists': False, 'timestamp': 0})


if __name__ == '__main__':
    print("=" * 50)
    print("CIX Investment Platform")
    print("=" * 50)
    print("Starting server at http://localhost:5000")
    print("=" * 50)
    app.run(debug=True, port=5000)
