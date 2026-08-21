"""
Insurance Calculator Module for Zenix AI.
Provides premium calculations for term life insurance and health insurance.
"""

import math
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class InsuranceQuote:
    """Insurance quote result."""
    insurance_type: str
    sum_insured: float
    premium_monthly: float
    premium_annual: float
    tenure_years: int
    details: Dict[str, Any]


class InsuranceCalculator:
    """
    Calculate insurance premiums for term life and health insurance.
    Uses approximate Indian market rates.
    """

    # Term life insurance rates (per Rs 1 lakh sum assured, annual)
    TERM_LIFE_RATES = {
        # age_group: rate_per_lakh_per_year
        (18, 25): 350,
        (26, 30): 450,
        (31, 35): 600,
        (36, 40): 900,
        (41, 45): 1400,
        (46, 50): 2200,
        (51, 55): 3500,
        (56, 60): 5500,
        (61, 65): 8500,
    }

    # Health insurance rates (annual premium per Rs 1 lakh sum insured)
    HEALTH_INSURANCE_RATES = {
        # age_group: rate_per_lakh_per_year
        (18, 25): 2500,
        (26, 30): 3500,
        (31, 35): 4500,
        (36, 40): 5500,
        (41, 45): 7000,
        (46, 50): 9000,
        (51, 55): 12000,
        (56, 60): 16000,
        (61, 65): 22000,
        (66, 70): 30000,
        (71, 75): 45000,
    }

    # Family floater rates (for family health insurance)
    FAMILY_FLOATER_MULTIPLIER = 1.8  # 80% more than individual for 2 members

    def calculate_term_life(self, age: int, sum_insured: float,
                           tenure_years: int = 10, smoker: bool = False) -> InsuranceQuote:
        """
        Calculate term life insurance premium.

        Args:
            age: Age of the insured person
            sum_insured: Sum assured in Rs (e.g., 5000000 for 50 lakh)
            tenure_years: Policy tenure in years
            smoker: Whether the person is a smoker

        Returns:
            InsuranceQuote with premium details
        """
        # Find rate for age group
        rate_per_lakh = self._get_rate(age, self.TERM_LIFE_RATES)

        # Calculate base premium
        sum_in_lakhs = sum_insured / 100000
        base_premium = rate_per_lakh * sum_in_lakhs

        # Smoker loading (50% extra)
        if smoker:
            base_premium *= 1.5

        # GST (18% on premium)
        gst = base_premium * 0.18
        total_annual = base_premium + gst

        # Monthly premium
        monthly = total_annual / 12

        details = {
            "age": age,
            "smoker": smoker,
            "base_premium": round(base_premium, 2),
            "gst": round(gst, 2),
            "rate_per_lakh": rate_per_lakh,
            "sum_assured_words": self._amount_in_words(sum_insured),
        }

        return InsuranceQuote(
            insurance_type="Term Life Insurance",
            sum_insured=sum_insured,
            premium_monthly=round(monthly, 2),
            premium_annual=round(total_annual, 2),
            tenure_years=tenure_years,
            details=details,
        )

    def calculate_health(self, age: int, sum_insured: float,
                        members: int = 1, city_tier: str = "tier1") -> InsuranceQuote:
        """
        Calculate health insurance premium.

        Args:
            age: Age of the eldest member
            sum_insured: Sum insured in Rs (e.g., 500000 for 5 lakh)
            members: Number of members (1 for individual, 2+ for family)
            city_tier: "tier1" for metro, "tier2" for non-metro

        Returns:
            InsuranceQuote with premium details
        """
        # Find rate for age group
        rate_per_lakh = self._get_rate(age, self.HEALTH_INSURANCE_RATES)

        # Calculate base premium
        sum_in_lakhs = sum_insured / 100000
        base_premium = rate_per_lakh * sum_in_lakhs

        # Family floater loading
        if members > 1:
            # Additional members add 50% each (approximate)
            for i in range(1, members):
                base_premium += rate_per_lakh * sum_in_lakhs * 0.5

        # City tier loading
        if city_tier == "tier2":
            base_premium *= 0.9  # 10% discount for non-metro

        # No claim discount (assume 10% for illustration)
        no_claim_discount = base_premium * 0.1

        # Pre-final premium
        premium_after_discount = base_premium - no_claim_discount

        # GST (18%)
        gst = premium_after_discount * 0.18
        total_annual = premium_after_discount + gst

        # Monthly premium
        monthly = total_annual / 12

        details = {
            "age": age,
            "members": members,
            "city_tier": city_tier,
            "base_premium": round(base_premium, 2),
            "no_claim_discount": round(no_claim_discount, 2),
            "premium_after_discount": round(premium_after_discount, 2),
            "gst": round(gst, 2),
            "rate_per_lakh": rate_per_lakh,
            "sum_assured_words": self._amount_in_words(sum_insured),
        }

        return InsuranceQuote(
            insurance_type="Health Insurance",
            sum_insured=sum_insured,
            premium_monthly=round(monthly, 2),
            premium_annual=round(total_annual, 2),
            tenure_years=1,
            details=details,
        )

    def compare_plans(self, age: int, sum_insured: float,
                     insurance_type: str = "term") -> list:
        """
        Compare insurance plans from different perspectives.

        Args:
            age: Age of the insured
            sum_insured: Sum insured in Rs
            insurance_type: "term" or "health"

        Returns:
            List of InsuranceQuote objects
        """
        results = []

        if insurance_type == "term":
            # Compare different tenures
            for tenure in [10, 15, 20, 25, 30]:
                quote = self.calculate_term_life(age, sum_insured, tenure)
                results.append(quote)

        elif insurance_type == "health":
            # Compare different sum insured amounts
            for amount in [300000, 500000, 1000000, 2000000, 5000000]:
                quote = self.calculate_health(age, amount)
                results.append(quote)

        return results

    def get_recommendation(self, age: int, income: float,
                          dependents: int = 0) -> Dict[str, Any]:
        """
        Get insurance recommendation based on profile.

        Args:
            age: Age of the person
            income: Annual income in Rs
            dependents: Number of dependents

        Returns:
            Recommendation dictionary
        """
        # Term life recommendation (10-15x annual income)
        term_amount = income * 10
        if dependents > 2:
            term_amount = income * 15

        # Health insurance recommendation
        health_amount = 500000  # Minimum 5 lakh
        if dependents > 0:
            health_amount = 1000000  # 10 lakh for families

        # Calculate premiums
        term_quote = self.calculate_term_life(age, term_amount, 20)
        health_quote = self.calculate_health(age, health_amount, dependents + 1)

        recommendation = {
            "term_life": {
                "recommended_amount": term_amount,
                "amount_words": self._amount_in_words(term_amount),
                "monthly_premium": term_quote.premium_monthly,
                "annual_premium": term_quote.premium_annual,
            },
            "health_insurance": {
                "recommended_amount": health_amount,
                "amount_words": self._amount_in_words(health_amount),
                "monthly_premium": health_quote.premium_monthly,
                "annual_premium": health_quote.premium_annual,
            },
            "total_monthly": round(term_quote.premium_monthly + health_quote.premium_monthly, 2),
            "total_annual": round(term_quote.premium_annual + health_quote.premium_annual, 2),
            "percentage_of_income": round(
                (term_quote.premium_annual + health_quote.premium_annual) / income * 100, 2
            ) if income > 0 else 0,
        }

        return recommendation

    def _get_rate(self, age: int, rate_table: Dict) -> float:
        """Get rate from table based on age."""
        for (min_age, max_age), rate in rate_table.items():
            if min_age <= age <= max_age:
                return rate
        # Default to highest bracket
        return list(rate_table.values())[-1]

    def _amount_in_words(self, amount: float) -> str:
        """Convert amount to Indian words."""
        if amount >= 10000000:
            return f"Rs {amount/10000000:.2f} Crore"
        elif amount >= 100000:
            return f"Rs {amount/100000:.2f} Lakh"
        else:
            return f"Rs {amount:,.0f}"


# Singleton instance
_insurance_calculator = None


def get_insurance_calculator() -> InsuranceCalculator:
    """Get or create the insurance calculator singleton."""
    global _insurance_calculator
    if _insurance_calculator is None:
        _insurance_calculator = InsuranceCalculator()
    return _insurance_calculator
