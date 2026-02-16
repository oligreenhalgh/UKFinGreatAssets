"""
Stage 1: Investment Thesis Interpreter

Parses PDF investment thesis documents using Google's Gemini API to extract:
1. Investment amount in GBP millions
2. Desired sector allocations (weights summing to 1.0)
3. Topline overview with KPIs and timeline
"""

import os
import json
import re
from dataclasses import dataclass, field
from typing import Dict, Optional
from pathlib import Path

try:
    import google.generativeai as genai
except ImportError:
    raise ImportError("Please install google-generativeai: pip install google-generativeai")

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None  # Will work without .env file if env var is set


# Valid sectors matching the CSV dataset
VALID_SECTORS = [
    "Advanced_Manufacturing",
    "Clean_Energy",
    "Creative_Industries",
    "Defence",
    "Digital&Technologies",
    "Financial",
    "Life_Science",
    "Professional_Business",
    "Real_Estate",
    "Retail",
]


@dataclass
class ThesisOutput:
    """Parsed investment thesis data."""
    amount_millions: float
    desired_sectors: Dict[str, float]  # sector -> weight (must sum to 1.0)
    overview: str
    kpis: list = field(default_factory=list)
    timeline: Optional[str] = None


def _configure_genai() -> None:
    """Configure Gemini API with environment key or .env file."""
    # Load .env file if dotenv is available
    if load_dotenv is not None:
        env_path = Path(__file__).parent / ".env"
        load_dotenv(env_path)
    
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError(
            "GOOGLE_API_KEY environment variable not set. "
            "Please set it with your Gemini API key."
        )
    genai.configure(api_key=api_key)


def _build_extraction_prompt() -> str:
    """Build the prompt for thesis extraction."""
    sectors_list = ", ".join(VALID_SECTORS)
    return f"""You are an investment analyst assistant. Analyze this investment thesis document and extract the following information in JSON format:

1. "amount_millions": The total investment amount in GBP millions (as a number)
2. "desired_sectors": A dictionary mapping sector names to their target allocation weights. 
   - Valid sectors are: {sectors_list}
   - Weights must sum to 1.0
   - Map any mentioned industries/sectors to the closest matching valid sector name
3. "overview": A concise topline summary of the investment thesis (2-3 sentences)
4. "kpis": A list of key performance indicators mentioned (if any)
5. "timeline": The investment timeline or horizon mentioned (if any, otherwise null)

Return ONLY valid JSON with these exact keys. Example:
{{
    "amount_millions": 10.5,
    "desired_sectors": {{"Defence": 0.4, "Advanced_Manufacturing": 0.35, "Digital&Technologies": 0.25}},
    "overview": "Focus on UK defence and manufacturing sectors with emphasis on export potential.",
    "kpis": ["ROI > 15%", "3-year payback"],
    "timeline": "5-year investment horizon"
}}

If sector weights are not explicitly stated, infer reasonable weights based on the thesis focus areas.
If amount is not specified, look for budget, allocation, or fund size mentions.
"""


def parse_investment_thesis(pdf_path: str) -> ThesisOutput:
    """
    Parse a PDF investment thesis and extract structured investment parameters.
    
    Args:
        pdf_path: Path to the PDF investment thesis file
        
    Returns:
        ThesisOutput with extracted parameters
        
    Raises:
        FileNotFoundError: If PDF file doesn't exist
        ValueError: If API key not configured or extraction fails
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    _configure_genai()
    
    # Upload the PDF file to Gemini
    uploaded_file = genai.upload_file(str(pdf_path))
    
    # Use Gemini to extract thesis information
    model = genai.GenerativeModel("gemini-2.5-flash")  # Available model
    
    prompt = _build_extraction_prompt()
    
    # Retry with exponential backoff for rate limits
    import time
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = model.generate_content([uploaded_file, prompt])
            break
        except Exception as e:
            if "quota" in str(e).lower() or "rate" in str(e).lower() or "429" in str(e):
                wait_time = (attempt + 1) * 30  # 30s, 60s, 90s
                print(f"      Rate limited, waiting {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait_time)
                if attempt == max_retries - 1:
                    raise
            else:
                raise
    
    # Parse the JSON response
    response_text = response.text.strip()
    
    # Extract JSON from response (handle markdown code blocks)
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_text)
    if json_match:
        response_text = json_match.group(1)
    
    try:
        data = json.loads(response_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse Gemini response as JSON: {e}\nResponse: {response_text}")
    
    # Validate and normalize sector weights
    desired_sectors = data.get("desired_sectors", {})
    
    # Filter to valid sectors only
    valid_sector_weights = {
        k: v for k, v in desired_sectors.items() 
        if k in VALID_SECTORS
    }
    
    # Normalize weights to sum to 1.0
    total_weight = sum(valid_sector_weights.values())
    if total_weight > 0:
        valid_sector_weights = {
            k: v / total_weight 
            for k, v in valid_sector_weights.items()
        }
    else:
        raise ValueError("No valid sectors extracted from thesis")
    
    return ThesisOutput(
        amount_millions=float(data.get("amount_millions", 0)),
        desired_sectors=valid_sector_weights,
        overview=data.get("overview", ""),
        kpis=data.get("kpis", []),
        timeline=data.get("timeline"),
    )


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python stage1.py <path_to_thesis.pdf>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    try:
        result = parse_investment_thesis(pdf_path)
        print(f"\n=== Investment Thesis Analysis ===\n")
        print(f"Investment Amount: £{result.amount_millions}M")
        print(f"\nSector Allocations:")
        for sector, weight in result.desired_sectors.items():
            print(f"  {sector}: {weight:.1%}")
        print(f"\nOverview: {result.overview}")
        if result.kpis:
            print(f"\nKPIs: {', '.join(result.kpis)}")
        if result.timeline:
            print(f"\nTimeline: {result.timeline}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)