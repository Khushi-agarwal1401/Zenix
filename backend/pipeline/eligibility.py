"""
Government Scheme Eligibility Checker for Zenix AI.
Checks if a user qualifies for PM-Kisan, Ayushman Bharat, etc.
"""

from typing import Dict, Any, List


class EligibilityChecker:
    """Check eligibility for major government schemes based on user inputs."""

    def check_all(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check eligibility for all schemes based on user profile.

        Profile fields:
            - occupation: str (farmer, student, employed, unemployed, etc.)
            - income_annual: float (annual family income in Rs)
            - age: int
            - gender: str (male, female, other)
            - state: str
            - is_sc_st: bool (SC/ST category)
            - is_obc: bool (OBC category)
            - has_aadhaar: bool
            - land_acres: float (for farmers)
            - is_bpl: bool (Below Poverty Line)
            - family_size: int
        """
        results = {
            "eligible_schemes": [],
            "not_eligible_schemes": [],
            "check_method": "rule_based",
        }

        schemes = [
            self._check_pmkisan(profile),
            self._check_ayushman_bharat(profile),
            self._check_pmujjwala(profile),
            self._check_pmsby(profile),
            self._check_pmjjby(profile),
            self._check_apy(profile),
            self._check_pmmvy(profile),
            self._check_scholarship(profile),
            self._check_mudra(profile),
            self._check_mgnrega(profile),
        ]

        for scheme in schemes:
            if scheme["eligible"]:
                results["eligible_schemes"].append(scheme)
            else:
                results["not_eligible_schemes"].append(scheme)

        return results

    def _check_pmkisan(self, p: Dict) -> Dict:
        """PM-KISAN: Rs 6,000/year for farmers."""
        eligible = False
        reasons = []

        if p.get("occupation") == "farmer" and p.get("land_acres", 0) > 0:
            eligible = True
            reasons.append("You are a farmer with cultivable land")
        else:
            reasons.append("PM-KISAN requires cultivable agricultural land")

        # Exclusion criteria
        if p.get("is_govt_employee"):
            eligible = False
            reasons.append("Government employees are excluded")
        if p.get("income_annual", 0) > 100000 and p.get("is_tax_payer"):
            eligible = False
            reasons.append("Income tax payers are excluded")

        return {
            "name": "PM-KISAN",
            "benefit": "Rs 6,000/year in 3 installments",
            "eligible": eligible,
            "reasons": reasons,
            "apply_at": "pmkisan.gov.in",
        }

    def _check_ayushman_bharat(self, p: Dict) -> Dict:
        """Ayushman Bharat: Rs 5 lakh health cover for poor families."""
        eligible = False
        reasons = []

        if p.get("is_bpl") or p.get("income_annual", 0) < 120000:
            eligible = True
            reasons.append("Annual income below Rs 1.2 lakh (BPL criteria)")
        elif p.get("is_sc_st") and p.get("income_annual", 0) < 200000:
            eligible = True
            reasons.append("SC/ST family with income below Rs 2 lakh")

        if not eligible:
            reasons.append("Ayushman Bharat is for families identified under SECC 2011")

        return {
            "name": "Ayushman Bharat (PM-JAY)",
            "benefit": "Rs 5 lakh health cover per family per year",
            "eligible": eligible,
            "reasons": reasons,
            "apply_at": "mera.pmjay.gov.in",
            "helpline": "14555",
        }

    def _check_pmujjwala(self, p: Dict) -> Dict:
        """PM Ujjwala Yojana: Free LPG connection for BPL families."""
        eligible = False
        reasons = []

        if p.get("is_bpl") and p.get("gender") == "female":
            eligible = True
            reasons.append("BPL family and female head of household")
        elif p.get("is_bpl"):
            reasons.append("Ujjwala 2.0 prioritizes women from BPL families")

        if not eligible:
            reasons.append("Must be a woman from BPL household without existing LPG connection")

        return {
            "name": "PM Ujjwala Yojana",
            "benefit": "Free LPG connection with deposit waiver",
            "eligible": eligible,
            "reasons": reasons,
            "apply_at": "ujjwala.pmuy.gov.in",
        }

    def _check_pmsby(self, p: Dict) -> Dict:
        """PMSBY: Rs 2 lakh accidental insurance for Rs 20/year."""
        age = p.get("age", 0)
        eligible = 18 <= age <= 70
        reasons = []

        if eligible:
            reasons.append(f"Age {age} is within 18-70 years range")
            reasons.append("Premium: Only Rs 20/year")
        else:
            reasons.append("PMSBY requires age between 18-70 years")

        return {
            "name": "PMSBY (Accidental Insurance)",
            "benefit": "Rs 2 lakh accidental death/disability cover",
            "eligible": eligible,
            "reasons": reasons,
            "apply_at": "Any bank branch",
            "premium": "Rs 20/year",
        }

    def _check_pmjjby(self, p: Dict) -> Dict:
        """PMJJBY: Rs 2 lakh life insurance for Rs 436/year."""
        age = p.get("age", 0)
        eligible = 18 <= age <= 50
        reasons = []

        if eligible:
            reasons.append(f"Age {age} is within 18-50 years range")
            reasons.append("Premium: Only Rs 436/year")
        else:
            reasons.append("PMJJBY requires age between 18-50 years")

        return {
            "name": "PMJJBY (Life Insurance)",
            "benefit": "Rs 2 lakh life cover",
            "eligible": eligible,
            "reasons": reasons,
            "apply_at": "Any bank branch",
            "premium": "Rs 436/year",
        }

    def _check_apy(self, p: Dict) -> Dict:
        """Atal Pension Yojana: Guaranteed pension after 60."""
        age = p.get("age", 0)
        eligible = 18 <= age <= 40
        reasons = []

        if eligible:
            reasons.append(f"Age {age} is within 18-40 years range")
            reasons.append("Government contributes 50% of your contribution for 5 years")
        else:
            reasons.append("APY requires age between 18-40 years")

        return {
            "name": "Atal Pension Yojana",
            "benefit": "Guaranteed Rs 1,000-5,000/month pension after 60",
            "eligible": eligible,
            "reasons": reasons,
            "apply_at": "Bank/Post Office or enatalpension.yojana.gov.in",
        }

    def _check_pmmvy(self, p: Dict) -> Dict:
        """PM Matru Vandana Yojana: Rs 5,000 for pregnant women."""
        eligible = False
        reasons = []

        if p.get("gender") == "female" and p.get("is_pregnant"):
            eligible = True
            reasons.append("Pregnant women are eligible for maternity benefit")
        elif p.get("gender") == "female":
            reasons.append("PMMVY is for pregnant and lactating mothers")
        else:
            reasons.append("PMMVY is only for women")

        return {
            "name": "PM Matru Vandana Yojana",
            "benefit": "Rs 5,000 for first pregnancy",
            "eligible": eligible,
            "reasons": reasons,
            "apply_at": "Common Service Centres",
        }

    def _check_scholarship(self, p: Dict) -> Dict:
        """Scholarships for students."""
        eligible = False
        reasons = []

        if p.get("occupation") == "student":
            if p.get("income_annual", 0) < 600000:
                eligible = True
                reasons.append("Student from family with income below Rs 6 lakh")
                if p.get("is_sc_st"):
                    reasons.append("SC/ST students get additional scholarships")
            elif p.get("is_obc"):
                eligible = True
                reasons.append("OBC students eligible for post-matric scholarships")

        if not eligible:
            reasons.append("Scholarships typically require family income below Rs 6-8 lakh")

        return {
            "name": "Government Scholarships",
            "benefit": "Tuition fees + maintenance allowance",
            "eligible": eligible,
            "reasons": reasons,
            "apply_at": "scholarships.gov.in",
        }

    def _check_mudra(self, p: Dict) -> Dict:
        """Mudra Loan: Up to Rs 10 lakh for micro enterprises."""
        eligible = False
        reasons = []

        if p.get("occupation") in ["self-employed", "business", "entrepreneur"]:
            eligible = True
            reasons.append("Available for non-farm micro enterprises")
            reasons.append("Shishu: Up to Rs 50,000 | Kishore: Up to Rs 5 lakh | Tarun: Up to Rs 10 lakh")
        elif p.get("occupation") in ["unemployed", "student"]:
            reasons.append("Mudra is for existing or aspiring micro enterprises")

        if not eligible:
            reasons.append("Must have a business plan for non-farm income activity")

        return {
            "name": "Mudra Yojana",
            "benefit": "Loans up to Rs 10 lakh",
            "eligible": eligible,
            "reasons": reasons,
            "apply_at": "Any bank, RRB, or NBFC",
        }

    def _check_mgnrega(self, p: Dict) -> Dict:
        """MGNREGA: 100 days guaranteed rural employment."""
        eligible = False
        reasons = []

        if p.get("occupation") in ["farmer", "unemployed", "rural_worker"]:
            eligible = True
            reasons.append("Guaranteed 100 days of wage employment per year")
            reasons.append(f"Minimum wage: Rs 349/day (varies by state)")

        if not eligible:
            reasons.append("MGNREGA is for rural households willing to do unskilled manual work")

        return {
            "name": "MGNREGA",
            "benefit": "100 days guaranteed rural employment",
            "eligible": eligible,
            "reasons": reasons,
            "apply_at": "Gram Panchayat",
        }


# Singleton
eligibility_checker = EligibilityChecker()
