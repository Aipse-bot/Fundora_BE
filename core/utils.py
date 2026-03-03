import math
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _f(value, default=0.0):
    """Safely convert any field value to float."""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _has(value):
    """Return True if value is meaningfully present (non-zero, non-empty)."""
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (int, float, Decimal)):
        return float(value) != 0
    return bool(value)


def _log_scale(value, reference=1_000_000, max_pts=1.0):
    """
    Logarithmic scaling for large monetary fields (TAM, SAM, capital raised).
    Returns a 0–max_pts score so that small values aren't penalised
    and absurdly large values don't dominate.

    log10(1M)  → ~0.5 * max_pts
    log10(1B)  → ~0.75 * max_pts
    log10(10B) → ~1.0 * max_pts  (cap)
    """
    v = _f(value)
    if v <= 0:
        return 0.0
    # Normalise: log10(v) / log10(10_000_000_000) capped at 1
    ratio = math.log10(v + 1) / math.log10(10_000_000_000)
    return round(min(ratio, 1.0) * max_pts, 4)


# ---------------------------------------------------------------------------
# Main function
# ---------------------------------------------------------------------------

def calculate_confidence_percentage(startup):
    """
    Calculate data confidence for a Startup instance.

    Parameters
    ----------
    startup : Startup model instance

    Returns
    -------
    (int, str)  — (percentage 0-100, level: 'High'|'Medium'|'Low'|'Pending')
    """
    try:
        score = 0.0  # accumulates raw points; categories are normalised below

        # ===================================================================
        # 1. BASICS  (max 20 pts)
        # ===================================================================
        basics = 0.0

        if _has(startup.company_name):
            basics += 3.0
        if _has(startup.industry):
            basics += 3.0
        if _has(startup.company_description):
            basics += 3.0
        if _has(startup.company_stage):
            basics += 2.0
        if _has(startup.year_founded):
            basics += 1.5
        if _has(startup.headquarters):
            basics += 1.5
        if _has(startup.website_url) or _has(getattr(startup, 'linkedin_url', None)):
            basics += 2.0
        if _has(startup.problem_statement) and _has(startup.solution_description):
            basics += 2.0
        if _has(startup.contact_email) or _has(startup.contact_phone):
            basics += 1.0

        # Clamp and add (category max = 20)
        score += min(basics, 20.0)

        # ===================================================================
        # 2. FINANCIALS  (max 25 pts)
        # ===================================================================
        financials = 0.0

        cur_rev  = _f(startup.current_revenue or startup.revenue)
        prev_rev = _f(startup.previous_revenue)
        net_inc  = _f(startup.net_income)
        assets   = _f(startup.total_assets)
        liabs    = _f(startup.total_liabilities)
        eq       = _f(startup.shareholder_equity)
        cf       = _f(startup.cash_flow)
        cac      = _f(startup.cac)
        ltv      = _f(startup.ltv)
        gm       = _f(startup.gross_margin)
        runway   = _f(startup.expected_runway_months)

        # Revenue presence (4 pts)
        if cur_rev > 0:
            financials += 4.0

        # Revenue growth quality gate (3 pts)
        if cur_rev > 0 and prev_rev > 0:
            growth_rate = (cur_rev - prev_rev) / prev_rev
            if growth_rate > 0:
                financials += 3.0
            elif growth_rate == 0:
                financials += 1.0
            # negative growth → 0 pts (flag, no penalty beyond missing points)

        # Inconsistency quality gate: users=0 but revenue>0 → deduct 1 pt
        total_users = _f(startup.total_users)
        paid_users  = _f(startup.paid_users)
        if cur_rev > 0 and total_users == 0 and paid_users == 0:
            financials = max(financials - 1.0, 0)

        # Balance sheet (4 pts)
        if assets > 0:
            financials += 2.0
        if liabs > 0 or eq != 0:
            financials += 2.0

        # Cash flow (2 pts)
        if _has(startup.cash_flow):
            financials += 2.0

        # Unit economics (4 pts)
        if cac > 0:
            financials += 1.5
        if ltv > 0:
            financials += 1.5
        if gm != 0:
            financials += 1.0

        # Burn rate derived metric (2 pts)
        # burn_rate proxy = abs(net_income) when negative + abs(operating CF) when negative
        burn = 0.0
        if net_inc < 0:
            burn += abs(net_inc)
        if cf < 0:
            burn += abs(cf)
        if burn > 0 and runway > 0:
            financials += 2.0  # has burn + runway data

        # Current valuation (2 pts)
        if _has(startup.current_valuation):
            financials += 2.0

        # Retained earnings / EBIT (2 pts for Altman completeness)
        if _has(startup.retained_earnings):
            financials += 1.0
        if _has(startup.ebit):
            financials += 1.0

        score += min(financials, 25.0)

        # ===================================================================
        # 3. MARKET  (max 15 pts)
        # ===================================================================
        market = 0.0

        # TAM / SAM with log scaling to avoid bias from huge numbers (5 pts)
        market += _log_scale(startup.market_size_tam, max_pts=3.0)
        market += _log_scale(startup.market_size_sam, max_pts=2.0)

        # Market growth rate (3 pts)
        mgr = _f(startup.market_growth_rate)
        if mgr > 0:
            market += 3.0
        elif _has(startup.market_growth_rate):
            market += 1.0

        # Competitive positioning (4 pts)
        if _has(startup.competitive_advantage):
            market += 2.0
        if _has(startup.competitors):
            market += 1.0
        if _has(startup.go_to_market_strategy):
            market += 1.0

        # Target geography / customer segments (3 pts)
        if _has(startup.target_geography):
            market += 1.0
        if _has(startup.target_customer_segments):
            market += 1.0
        if _has(startup.primary_market):
            market += 1.0

        score += min(market, 15.0)

        # ===================================================================
        # 4. TRACTION  (max 15 pts)
        # ===================================================================
        traction = 0.0

        mrr = _f(startup.current_mrr_arr)

        # Users (4 pts)
        if total_users > 0:
            traction += 2.0
        if paid_users > 0:
            traction += 2.0

        # MRR/ARR (3 pts)
        if mrr > 0:
            traction += 3.0

        # MoM growth derived metric (3 pts)
        # Approximate: MRR growth if both MRR and revenue present
        if mrr > 0 and cur_rev > 0:
            implied_monthly = cur_rev / 12
            if mrr >= implied_monthly * 0.9:  # MRR roughly consistent with revenue
                traction += 2.0
            else:
                traction += 1.0  # Partial — inconsistency noted

        # Milestones / traction text (3 pts)
        if _has(startup.major_milestones):
            traction += 1.5
        if _has(startup.key_traction_metrics):
            traction += 1.5

        # Notable customers (2 pts)
        if _has(startup.notable_customers):
            traction += 2.0

        score += min(traction, 15.0)

        # ===================================================================
        # 5. TEAM & FUNDING  (max 15 pts)
        # ===================================================================
        team_funding = 0.0

        # Team (6 pts)
        if _has(startup.key_team_members):
            team_funding += 2.0
        if _has(startup.additional_founders):
            team_funding += 2.0
        if _has(startup.advisors):
            team_funding += 1.0
        if _has(startup.team_size) and _f(startup.team_size) > 0:
            team_funding += 1.0

        # Qualitative team fields (3 pts — legacy fields)
        if _has(startup.team_strength):
            team_funding += 1.5
        if _has(startup.market_position):
            team_funding += 1.5

        # Funding (6 pts)
        if _has(startup.capital_raised_to_date):
            team_funding += 2.0
        if _has(startup.funding_history):
            team_funding += 1.0
        if _has(startup.current_round_type):
            team_funding += 1.5
        if _has(startup.funding_ask):
            team_funding += 1.0
        if runway > 0:
            team_funding += 0.5

        score += min(team_funding, 15.0)

        # ===================================================================
        # 6. QUALITATIVE / BONUS  (max 10 pts)
        # ===================================================================
        qualitative = 0.0

        if _has(startup.brand_reputation):
            qualitative += 2.0
        if _has(startup.awards_and_recognition):
            qualitative += 2.0
        if _has(startup.key_partnerships):
            qualitative += 2.0
        if _has(startup.impact_statement):
            qualitative += 1.0
        if _has(startup.intellectual_property):
            qualitative += 1.5
        if _has(startup.pitch_deck_pdf) or _has(startup.one_pager_pdf):
            qualitative += 1.5

        score += min(qualitative, 10.0)

        # ===================================================================
        # Final percentage and level
        # ===================================================================
        percentage = int(round(max(0.0, min(score, 100.0))))

        if percentage >= 80:
            level = 'High'
        elif percentage >= 50:
            level = 'Medium'
        elif percentage >= 20:
            level = 'Low'
        else:
            level = 'Pending'

        return percentage, level

    except Exception as exc:
        logger.warning("calculate_confidence_percentage failed for startup %s: %s",
                       getattr(startup, 'id', '?'), exc)
        return 0, 'Pending'


# ---------------------------------------------------------------------------
# Unit tests  (run with: python manage.py shell < utils_tests.py  OR  pytest)
# ---------------------------------------------------------------------------

def _run_tests():
    """
    Quick self-contained tests using mock objects.
    Run from Django shell: from yourapp.utils import _run_tests; _run_tests()
    """
    from types import SimpleNamespace

    def make_startup(**kwargs):
        """Build a minimal mock Startup with all fields defaulting to None."""
        defaults = {f: None for f in [
            'id', 'company_name', 'industry', 'company_description', 'company_stage',
            'year_founded', 'headquarters', 'website_url', 'linkedin_url',
            'problem_statement', 'solution_description', 'contact_email', 'contact_phone',
            'current_revenue', 'revenue', 'previous_revenue', 'net_income',
            'total_assets', 'total_liabilities', 'shareholder_equity',
            'cash_flow', 'cac', 'ltv', 'gross_margin', 'expected_runway_months',
            'current_valuation', 'expected_future_valuation', 'retained_earnings', 'ebit',
            'market_size_tam', 'market_size_sam', 'market_growth_rate',
            'competitive_advantage', 'competitors', 'go_to_market_strategy',
            'target_geography', 'target_customer_segments', 'primary_market',
            'current_mrr_arr', 'total_users', 'paid_users',
            'major_milestones', 'key_traction_metrics', 'notable_customers',
            'key_team_members', 'additional_founders', 'advisors', 'team_size',
            'team_strength', 'market_position', 'brand_reputation',
            'capital_raised_to_date', 'funding_history', 'current_round_type',
            'funding_ask', 'awards_and_recognition', 'key_partnerships',
            'impact_statement', 'intellectual_property', 'pitch_deck_pdf', 'one_pager_pdf',
        ]}
        defaults.update(kwargs)
        return SimpleNamespace(**defaults)

    results = []

    # ------------------------------------------------------------------
    # Case 1: COMPLETE startup — should score High (>=80)
    # ------------------------------------------------------------------
    complete = make_startup(
        company_name='AcmeCorp',
        industry='FinTech',
        company_description='AI-powered payments.',
        company_stage='growth',
        year_founded=2020,
        headquarters='Manila, PH',
        website_url='https://acme.io',
        problem_statement='Payments are slow.',
        solution_description='Instant settlement via ML.',
        contact_email='hello@acme.io',
        current_revenue=5_000_000,
        previous_revenue=3_000_000,
        net_income=-200_000,
        total_assets=10_000_000,
        total_liabilities=4_000_000,
        shareholder_equity=6_000_000,
        cash_flow=-150_000,
        cac=50,
        ltv=500,
        gross_margin=65,
        expected_runway_months=18,
        current_valuation=20_000_000,
        retained_earnings=1_000_000,
        ebit=300_000,
        market_size_tam=50_000_000_000,
        market_size_sam=5_000_000_000,
        market_growth_rate=25,
        competitive_advantage='Proprietary model',
        competitors='Stripe, GCash',
        go_to_market_strategy='B2B SaaS via partnerships',
        target_geography='SEA',
        target_customer_segments='SMEs',
        primary_market='FinTech',
        current_mrr_arr=420_000,
        total_users=15_000,
        paid_users=3_000,
        major_milestones='$5M ARR, Series A closed',
        key_traction_metrics='MoM 12% growth',
        notable_customers='BDO, UnionBank',
        key_team_members='[{"name":"Jane","title":"CTO"}]',
        additional_founders='[{"name":"Bob","title":"COO"}]',
        advisors='[{"name":"Alice","title":"Advisor"}]',
        team_size=25,
        team_strength='Strong ML team',
        market_position='Top 3 in SEA',
        brand_reputation='Award-winning',
        capital_raised_to_date=3_000_000,
        funding_history='[{"round":"Seed","amount":500000}]',
        current_round_type='series_a',
        funding_ask=5_000_000,
        awards_and_recognition='Forbes 30 Under 30',
        key_partnerships='Visa, Mastercard',
        impact_statement='Financial inclusion',
        intellectual_property='2 patents pending',
        pitch_deck_pdf='decks/acme.pdf',
    )
    pct, lvl = calculate_confidence_percentage(complete)
    passed = pct >= 80 and lvl == 'High'
    results.append(('COMPLETE startup → High', passed, pct, lvl))

    # ------------------------------------------------------------------
    # Case 2: SPARSE startup — has basics + a little financial data → Low (20–49)
    # ------------------------------------------------------------------
    sparse = make_startup(
        company_name='StealthCo',
        industry='EdTech',
        company_description='Online learning platform.',
        company_stage='mvp',
        year_founded=2023,
        contact_email='hi@stealth.io',
        current_revenue=50_000,
        total_assets=200_000,
        total_liabilities=80_000,
        market_growth_rate=15,
        total_users=500,
    )
    pct, lvl = calculate_confidence_percentage(sparse)
    passed = 20 <= pct < 50 and lvl == 'Low'
    results.append(('SPARSE startup → Low', passed, pct, lvl))

    # ------------------------------------------------------------------
    # Case 3: INVALID / empty startup — should be Pending (<20)
    # ------------------------------------------------------------------
    empty = make_startup()
    pct, lvl = calculate_confidence_percentage(empty)
    passed = pct < 20 and lvl == 'Pending'
    results.append(('EMPTY startup → Pending', passed, pct, lvl))

    # ------------------------------------------------------------------
    # Print results
    # ------------------------------------------------------------------
    print("\n=== calculate_confidence_percentage unit tests ===")
    all_pass = True
    for name, ok, pct, lvl in results:
        status = '✅ PASS' if ok else '❌ FAIL'
        print(f"  {status}  {name}  →  {pct}% ({lvl})")
        if not ok:
            all_pass = False
    print(f"\n{'All tests passed!' if all_pass else 'Some tests FAILED — check thresholds.'}\n")
    return all_pass


if __name__ == '__main__':
    _run_tests()