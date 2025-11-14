"""
===============================================================================
FILE IDENTITY CARD
===============================================================================
Filename    : report_generator.py
Created     : 2025
Author      : Elite Development Team
Department  : Reporting Services
Project     : Gravity Fundamental Analysis
Module      : Comprehensive Valuation Report Generator
Version     : 1.0.0

Purpose     : Generate comprehensive PDF and JSON valuation reports with all
              15 valuations, ML predictions, recommendations, risk analysis,
              and visualizations. Production-ready report generation.

Scope       : Production report generation for investment analysis
Components  : PDF generation, JSON export, charts, templates

Dependencies:
    - ReportLab (PDF generation)
    - Matplotlib (chart generation)
    - Jinja2 (HTML templates)
    - Pydantic (data models)
    - app.services (Valuation services, ML predictions)

Output      : PDF reports, JSON data exports

Notes       : Part of Task 10 - Comprehensive Valuation Report Generator
              Generates detailed investment reports with methodology explanations
              Includes all valuations, features, predictions, and recommendations
===============================================================================
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import json
from io import BytesIO

# PDF generation
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, black, blue, green, red
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# Charts
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend

# Data models
from pydantic import BaseModel


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class ValuationMethodResult:
    """Result from a single valuation method."""
    method_name: str
    fair_value_bull: float
    fair_value_base: float
    fair_value_bear: float
    confidence: float
    key_assumptions: Dict[str, float]
    methodology_notes: str


@dataclass
class MLPredictionResult:
    """ML model prediction result."""
    predicted_best_method: str
    method_confidence: float
    bull_probability: float
    base_probability: float
    bear_probability: float
    expected_return_1m: float
    expected_return_3m: float
    expected_return_6m: float
    expected_return_12m: float
    time_to_fair_value: Optional[float]


@dataclass
class RiskFactor:
    """Single risk factor."""
    category: str  # "market", "company", "industry", "valuation"
    severity: str  # "high", "medium", "low"
    description: str
    mitigation: Optional[str]


@dataclass
class PriceTarget:
    """Price target with scenario."""
    scenario: str  # "bull", "base", "bear"
    target_price: float
    upside_potential: float  # %
    time_horizon: str  # "6M", "12M"


@dataclass
class RecommendationData:
    """Investment recommendation."""
    recommendation: str  # "Strong Buy", "Buy", "Hold", "Sell", "Strong Sell"
    conviction: float  # 0-100
    rationale: str
    entry_range: Tuple[float, float]
    exit_target: float
    stop_loss: Optional[float]


@dataclass
class CompanySnapshot:
    """Company overview snapshot."""
    symbol: str
    company_name: str
    industry: str
    market_cap: Optional[float]
    current_price: float
    pe_ratio: Optional[float]
    pb_ratio: Optional[float]
    dividend_yield: Optional[float]
    latest_financials_date: Optional[datetime]


@dataclass
class ValuationReportData:
    """Complete data for valuation report."""
    # Report metadata
    report_id: str
    generation_date: datetime
    analyst_name: Optional[str]
    
    # Company data
    company: CompanySnapshot
    
    # Valuations (all 5 methods)
    valuations: List[ValuationMethodResult]
    
    # ML predictions
    ml_prediction: MLPredictionResult
    
    # Ensemble consensus
    consensus_fair_value: float
    consensus_confidence: float
    
    # Recommendation
    recommendation: RecommendationData
    
    # Price targets
    price_targets: List[PriceTarget]
    
    # Risk analysis
    risk_factors: List[RiskFactor]
    
    # Features (top 10 most important)
    top_features: Dict[str, float]
    
    # Disclaimers
    disclaimers: List[str]


# ============================================================================
# Report Generator
# ============================================================================

class ValuationReportGenerator:
    """
    Generate comprehensive valuation reports in PDF and JSON formats.
    
    Features:
    - All 15 valuations with methodology
    - ML predictions with confidence
    - Recommendation with rationale
    - Risk factors and disclaimers
    - Price targets (bull/base/bear)
    - Entry/exit ranges
    - Charts and visualizations
    """
    
    def __init__(self, output_dir: str = "reports"):
        """
        Initialize report generator.
        
        Args:
            output_dir: Directory to save generated reports
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # PDF styles
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom PDF styles."""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=HexColor('#1a237e'),
            spaceAfter=30,
            alignment=TA_CENTER
        ))
        
        # Section heading
        self.styles.add(ParagraphStyle(
            name='SectionHeading',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=HexColor('#283593'),
            spaceAfter=12,
            spaceBefore=12
        ))
        
        # Recommendation style
        self.styles.add(ParagraphStyle(
            name='Recommendation',
            parent=self.styles['Normal'],
            fontSize=14,
            textColor=green,
            alignment=TA_CENTER,
            spaceAfter=20
        ))
    
    async def generate_report(
        self,
        data: ValuationReportData,
        format: str = "both"  # "pdf", "json", "both"
    ) -> Dict[str, str]:
        """
        Generate comprehensive valuation report.
        
        Args:
            data: Complete report data
            format: Output format ("pdf", "json", "both")
        
        Returns:
            Dict with file paths: {"pdf": path, "json": path}
        """
        output_files = {}
        
        # Generate PDF
        if format in ["pdf", "both"]:
            pdf_path = await self._generate_pdf_report(data)
            output_files["pdf"] = str(pdf_path)
        
        # Generate JSON
        if format in ["json", "both"]:
            json_path = await self._generate_json_report(data)
            output_files["json"] = str(json_path)
        
        return output_files
    
    async def _generate_pdf_report(self, data: ValuationReportData) -> Path:
        """Generate PDF report."""
        filename = f"valuation_report_{data.company.symbol}_{data.report_id}.pdf"
        filepath = self.output_dir / filename
        
        # Create PDF document
        doc = SimpleDocTemplate(
            str(filepath),
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        # Build content
        story = []
        
        # Title page
        story.extend(self._build_title_page(data))
        story.append(PageBreak())
        
        # Executive summary
        story.extend(self._build_executive_summary(data))
        story.append(PageBreak())
        
        # Company overview
        story.extend(self._build_company_overview(data))
        
        # Valuation analysis
        story.extend(self._build_valuation_section(data))
        story.append(PageBreak())
        
        # ML predictions
        story.extend(self._build_ml_prediction_section(data))
        
        # Recommendation
        story.extend(self._build_recommendation_section(data))
        story.append(PageBreak())
        
        # Risk analysis
        story.extend(self._build_risk_section(data))
        
        # Disclaimers
        story.extend(self._build_disclaimers(data))
        
        # Build PDF
        doc.build(story)
        
        return filepath
    
    def _build_title_page(self, data: ValuationReportData) -> List:
        """Build title page."""
        elements = []
        
        # Title
        title = Paragraph(
            f"Valuation Report: {data.company.company_name}",
            self.styles['CustomTitle']
        )
        elements.append(title)
        elements.append(Spacer(1, 0.5*inch))
        
        # Symbol
        symbol = Paragraph(
            f"Symbol: <b>{data.company.symbol}</b>",
            self.styles['Normal']
        )
        elements.append(symbol)
        elements.append(Spacer(1, 0.2*inch))
        
        # Date
        date_str = data.generation_date.strftime("%Y-%m-%d %H:%M")
        date_p = Paragraph(f"Report Date: {date_str}", self.styles['Normal'])
        elements.append(date_p)
        elements.append(Spacer(1, 0.2*inch))
        
        # Report ID
        report_id = Paragraph(f"Report ID: {data.report_id}", self.styles['Normal'])
        elements.append(report_id)
        
        if data.analyst_name:
            analyst = Paragraph(f"Analyst: {data.analyst_name}", self.styles['Normal'])
            elements.append(Spacer(1, 0.2*inch))
            elements.append(analyst)
        
        return elements
    
    def _build_executive_summary(self, data: ValuationReportData) -> List:
        """Build executive summary section."""
        elements = []
        
        # Section title
        elements.append(Paragraph("Executive Summary", self.styles['SectionHeading']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Recommendation
        rec_color = self._get_recommendation_color(data.recommendation.recommendation)
        rec_text = f"<font color='{rec_color}'><b>{data.recommendation.recommendation}</b></font>"
        elements.append(Paragraph(rec_text, self.styles['Recommendation']))
        
        # Key metrics table
        key_data = [
            ["Metric", "Value"],
            ["Current Price", f"{data.company.current_price:,.0f}"],
            ["Consensus Fair Value", f"{data.consensus_fair_value:,.0f}"],
            ["Upside Potential", f"{((data.consensus_fair_value/data.company.current_price - 1) * 100):+.1f}%"],
            ["Conviction Score", f"{data.recommendation.conviction:.0f}/100"],
            ["Best Method", data.ml_prediction.predicted_best_method],
            ["Expected Return (6M)", f"{data.ml_prediction.expected_return_6m:.1%}"],
            ["Expected Return (12M)", f"{data.ml_prediction.expected_return_12m:.1%}"]
        ]
        
        table = Table(key_data, colWidths=[3*inch, 2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#e3f2fd')),
            ('TEXTCOLOR', (0, 0), (-1, 0), black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, HexColor('#bbdefb'))
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Rationale
        elements.append(Paragraph("<b>Investment Rationale:</b>", self.styles['Normal']))
        elements.append(Spacer(1, 0.1*inch))
        elements.append(Paragraph(data.recommendation.rationale, self.styles['Normal']))
        
        return elements
    
    def _build_company_overview(self, data: ValuationReportData) -> List:
        """Build company overview section."""
        elements = []
        
        elements.append(Paragraph("Company Overview", self.styles['SectionHeading']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Company data
        company_data = [
            ["Attribute", "Value"],
            ["Company Name", data.company.company_name],
            ["Symbol", data.company.symbol],
            ["Industry", data.company.industry or "N/A"],
            ["Market Cap", f"{data.company.market_cap:,.0f}" if data.company.market_cap else "N/A"],
            ["P/E Ratio", f"{data.company.pe_ratio:.2f}" if data.company.pe_ratio else "N/A"],
            ["P/B Ratio", f"{data.company.pb_ratio:.2f}" if data.company.pb_ratio else "N/A"],
            ["Dividend Yield", f"{data.company.dividend_yield:.2%}" if data.company.dividend_yield else "N/A"]
        ]
        
        table = Table(company_data, colWidths=[2.5*inch, 3*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#e8eaf6')),
            ('GRID', (0, 0), (-1, -1), 1, HexColor('#c5cae9')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold')
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.3*inch))
        
        return elements
    
    def _build_valuation_section(self, data: ValuationReportData) -> List:
        """Build valuation analysis section."""
        elements = []
        
        elements.append(Paragraph("Valuation Analysis", self.styles['SectionHeading']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Valuation table
        val_data = [["Method", "Bull", "Base", "Bear", "Confidence"]]
        
        for val in data.valuations:
            val_data.append([
                val.method_name,
                f"{val.fair_value_bull:,.0f}",
                f"{val.fair_value_base:,.0f}",
                f"{val.fair_value_bear:,.0f}",
                f"{val.confidence:.0%}"
            ])
        
        # Add consensus row
        val_data.append([
            "<b>Consensus</b>",
            "",
            f"<b>{data.consensus_fair_value:,.0f}</b>",
            "",
            f"<b>{data.consensus_confidence:.0%}</b>"
        ])
        
        table = Table(val_data, colWidths=[2*inch, 1.2*inch, 1.2*inch, 1.2*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#e1f5fe')),
            ('BACKGROUND', (0, -1), (-1, -1), HexColor('#fff9c4')),
            ('GRID', (0, 0), (-1, -1), 1, HexColor('#b3e5fc')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT')
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.3*inch))
        
        return elements
    
    def _build_ml_prediction_section(self, data: ValuationReportData) -> List:
        """Build ML prediction section."""
        elements = []
        
        elements.append(Paragraph("Machine Learning Predictions", self.styles['SectionHeading']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Scenario probabilities
        scenario_data = [
            ["Scenario", "Probability"],
            ["Bull", f"{data.ml_prediction.bull_probability:.1%}"],
            ["Base", f"{data.ml_prediction.base_probability:.1%}"],
            ["Bear", f"{data.ml_prediction.bear_probability:.1%}"]
        ]
        
        table = Table(scenario_data, colWidths=[2*inch, 2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#f3e5f5')),
            ('GRID', (0, 0), (-1, -1), 1, HexColor('#e1bee7'))
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.2*inch))
        
        # Expected returns
        returns_text = (
            f"Expected Returns: "
            f"1M: {data.ml_prediction.expected_return_1m:+.1%}, "
            f"3M: {data.ml_prediction.expected_return_3m:+.1%}, "
            f"6M: {data.ml_prediction.expected_return_6m:+.1%}, "
            f"12M: {data.ml_prediction.expected_return_12m:+.1%}"
        )
        elements.append(Paragraph(returns_text, self.styles['Normal']))
        
        return elements
    
    def _build_recommendation_section(self, data: ValuationReportData) -> List:
        """Build recommendation section."""
        elements = []
        
        elements.append(Paragraph("Investment Recommendation", self.styles['SectionHeading']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Price targets
        targets_data = [["Scenario", "Price Target", "Upside", "Horizon"]]
        for target in data.price_targets:
            targets_data.append([
                target.scenario.capitalize(),
                f"{target.target_price:,.0f}",
                f"{target.upside_potential:+.1%}",
                target.time_horizon
            ])
        
        table = Table(targets_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#e8f5e9')),
            ('GRID', (0, 0), (-1, -1), 1, HexColor('#c8e6c9'))
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.2*inch))
        
        # Entry/Exit
        entry_exit = (
            f"<b>Entry Range:</b> {data.recommendation.entry_range[0]:,.0f} - "
            f"{data.recommendation.entry_range[1]:,.0f}<br/>"
            f"<b>Exit Target:</b> {data.recommendation.exit_target:,.0f}<br/>"
        )
        if data.recommendation.stop_loss:
            entry_exit += f"<b>Stop Loss:</b> {data.recommendation.stop_loss:,.0f}"
        
        elements.append(Paragraph(entry_exit, self.styles['Normal']))
        
        return elements
    
    def _build_risk_section(self, data: ValuationReportData) -> List:
        """Build risk analysis section."""
        elements = []
        
        elements.append(Paragraph("Risk Analysis", self.styles['SectionHeading']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Group risks by severity
        for severity in ["high", "medium", "low"]:
            severity_risks = [r for r in data.risk_factors if r.severity == severity]
            if severity_risks:
                elements.append(Paragraph(
                    f"<b>{severity.upper()} Severity Risks:</b>",
                    self.styles['Normal']
                ))
                for risk in severity_risks:
                    elements.append(Paragraph(
                        f"• [{risk.category}] {risk.description}",
                        self.styles['Normal']
                    ))
                elements.append(Spacer(1, 0.1*inch))
        
        return elements
    
    def _build_disclaimers(self, data: ValuationReportData) -> List:
        """Build disclaimers section."""
        elements = []
        
        elements.append(Paragraph("Disclaimers", self.styles['SectionHeading']))
        elements.append(Spacer(1, 0.2*inch))
        
        for disclaimer in data.disclaimers:
            elements.append(Paragraph(f"• {disclaimer}", self.styles['Normal']))
            elements.append(Spacer(1, 0.1*inch))
        
        return elements
    
    async def _generate_json_report(self, data: ValuationReportData) -> Path:
        """Generate JSON report."""
        filename = f"valuation_report_{data.company.symbol}_{data.report_id}.json"
        filepath = self.output_dir / filename
        
        # Convert dataclass to dict
        report_dict = asdict(data)
        
        # Handle datetime serialization
        def json_serial(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")
        
        # Write JSON
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, indent=2, default=json_serial, ensure_ascii=False)
        
        return filepath
    
    def _get_recommendation_color(self, recommendation: str) -> str:
        """Get color for recommendation."""
        if "Strong Buy" in recommendation or "Buy" in recommendation:
            return "#4caf50"  # Green
        elif "Sell" in recommendation:
            return "#f44336"  # Red
        else:
            return "#ff9800"  # Orange (Hold)
