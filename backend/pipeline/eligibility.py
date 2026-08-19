"""
Government Scheme Eligibility Checker for Zenix AI.
Checks if a user qualifies for 30+ Indian government schemes.
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
            - is_pregnant: bool
            - is_govt_employee: bool
            - is_tax_payer: bool
        """
        results = {
            "eligible_schemes": [],
            "not_eligible_schemes": [],
            "check_method": "rule_based",
        }

        schemes = [
            # ── Core Welfare ───────────────────────────────────────────────
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
            # ── Housing & Infrastructure ───────────────────────────────────
            self._check_pmawas(profile),
            self._check_swachh_bharat(profile),
            # ── Women & Child ──────────────────────────────────────────────
            self._check_sukanya(profile),
            self._check_beti_bachao(profile),
            self._check_cbse_udyamita(profile),
            # ── Agriculture ────────────────────────────────────────────────
            self._check_kisan_credit(profile),
            self._check_soil_health(profile),
            self._check_pm_fasal_bima(profile),
            self._check_enam(profile),
            # ── Education & Skill ──────────────────────────────────────────
            self._check_pyramid_mission(profile),
            self._check_iskm(profile),
            # ── Employment & Entrepreneurship ──────────────────────────────
            self._check_standup_india(profile),
            self._check_pmrevamp(profile),
            # ── Pension & Insurance ────────────────────────────────────────
            self._check_nps(profile),
            self._check_jandhan(profile),
            self._check_senior_citizen_savings(profile),
            # ── Digital & Startup ──────────────────────────────────────────
            self._check_digital_india(profile),
            self._check_startup_india(profile),
            # ── State-specific ─────────────────────────────────────────────
            self._check_state_schemes(profile),
        ]

        for scheme in schemes:
            if scheme["eligible"]:
                results["eligible_schemes"].append(scheme)
            else:
                results["not_eligible_schemes"].append(scheme)

        return results

    # ── Original 10 Schemes ───────────────────────────────────────────────────

    def _check_pmkisan(self, p: Dict) -> Dict:
        """PM-KISAN: Rs 6,000/year for farmers."""
        eligible = False
        reasons = []

        if p.get("occupation") == "farmer" and p.get("land_acres", 0) > 0:
            eligible = True
            reasons.append("You are a farmer with cultivable land")
        else:
            reasons.append("PM-KISAN requires cultivable agricultural land")

        if p.get("is_govt_employee"):
            eligible = False
            reasons.append("Government employees are excluded")
        if p.get("income_annual", 0) > 100000 and p.get("is_tax_payer"):
            eligible = False
            reasons.append("Income tax payers are excluded")

        return {
            "name": "PM-KISAN",
            "benefit": "Rs 6,000/year in 3 installments of Rs 2,000",
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
            reasons.append("Minimum wage: Rs 349/day (varies by state)")

        if not eligible:
            reasons.append("MGNREGA is for rural households willing to do unskilled manual work")

        return {
            "name": "MGNREGA",
            "benefit": "100 days guaranteed rural employment",
            "eligible": eligible,
            "reasons": reasons,
            "apply_at": "Gram Panchayat",
        }

    # ── Housing & Infrastructure ───────────────────────────────────────────────

    def _check_pmawas(self, p: Dict) -> Dict:
        """PM Awas Yojana (Urban): Housing for All — subsidy on home loan."""
        eligible = False
        reasons = []
        income = p.get("income_annual", 0)

        if income <= 300000:
            eligible = True
            reasons.append("EWS category (income up to Rs 3 lakh) — Rs 2.67 lakh subsidy")
        elif income <= 600000:
            eligible = True
            reasons.append("LIG category (income Rs 3-6 lakh) — Rs 2.35 lakh subsidy")
        elif income <= 1200000:
            eligible = True
            reasons.append("MIG-I category (income Rs 6-12 lakh) — Rs 2.35 lakh subsidy")
        elif income <= 1800000:
            eligible = True
            reasons.append("MIG-II category (income Rs 12-18 lakh) — Rs 2.30 lakh subsidy")

        if not eligible:
            reasons.append("PM Awas is for families without a pucca house")

        return {
            "name": "PM Awas Yojana (Urban)",
            "benefit": "Interest subsidy up to Rs 2.67 lakh on home loan",
            "eligible": eligible,
            "reasons": reasons,
            "apply_at": "pmaymis.gov.in",
        }

    def _check_swachh_bharat(self, p: Dict) -> Dict:
        """Swachh Bharat Mission: Toilet construction subsidy."""
        eligible = False
        reasons = []

        if p.get("is_bpl") or p.get("income_annual", 0) < 120000:
            eligible = True
            reasons.append("BPL family eligible for toilet construction subsidy")
            reasons.append("Rs 12,000 for individual household latrine")

        if not eligible:
            reasons.append("Swachh Bharat subsidy is primarily for BPL households")

        return {
            "name": "Swachh Bharat Mission",
            "benefit": "Rs 12,000 subsidy for toilet construction",
            "eligible": eligible,
            "reasons": reasons,
            "apply_at": "swachhbharat.mygov.in",
        }

    # ── Women & Child ──────────────────────────────────────────────────────────

    def _check_sukanya(self, p: Dict) -> Dict:
        """Sukanya Samriddhi Yojana: Savings scheme for girl child."""
        eligible = False
        reasons = []

        if p.get("gender") == "female" and p.get("age", 0) <= 10:
            eligible = True
            reasons.append("Girl child below 10 years is eligible")
            reasons.append("Higher interest rate (8.2%) + tax benefits under 80C")
        elif p.get("has_daughter_below_10"):
            eligible = True
            reasons.append("Parent can open account for daughter below 10 years")

        if not eligible:
            reasons.append("Sukanya Samriddhi is for girl child below 10 years")

        return {
            "name": "Sukanya Samriddhi Yojana",
            "benefit": "8.2% interest + tax benefits under 80C",
            "eligible": eligible,
            "reasons": reasons,
            "apply_at": "Any post office or authorized bank",
        }

    def _check_beti_bachao(self, p: Dict) -> Dict:
        """Beti Bachao Beti Padhao: Awareness + savings for girl child."""
        eligible = False
        reasons = []

        if p.get("has_daughter_below_10") or (p.get("gender") == "female" and p.get("age", 0) <= 10):
            eligible = True
            reasons.append("Girl child benefits from awareness and savings programs")
            reasons.append("Linked with Sukanya Samriddhi for savings")

        if not eligible:
            reasons.append("BBBP focuses on girl child welfare and education")

        return {
            "name": "Beti Bachao Beti Padhao",
            "benefit": "Girl child welfare + linked savings benefits",
            "eligible": eligible,
            "reasons": reasons,
            "apply_at": "wcd.nic.in",
        }

    def _check_cbse_udyamita(self, p: Dict) -> Dict:
        """CBSE Udaan: Mentorship for girl students in engineering."""
        eligible = False
        reasons = []

        if p.get("occupation") == "student" and p.get("gender") == "female":
            eligible = True
            reasons.append("Girl students in Class XI/XII can apply")
            reasons.append("Mentorship, online resources, and test prep support")

        if not eligible:
            reasons.append("CBSE Udaan is for girl students in Class XI-XII")

        return {
            "name": "CBSE Udaan",
            "benefit": "Mentorship + resources for girl students in engineering",
            "eligible": eligible,
            "reasons": reasons,
            "apply_at": "cbse.gov.in",
        }

    # ── Agriculture ────────────────────────────────────────────────────────────

    def _check_kisan_credit(self, p: Dict) -> Dict:
        """Kisan Credit Card: Short-term credit for farmers at 4% interest."""
        eligible = False
        reasons = []

        if p.get("occupation") == "farmer" and p.get("land_acres", 0) > 0:
            eligible = True
            reasons.append("Farmers with cultivable land are eligible")
            reasons.append("Interest rate: 4% (after subsidy) vs 7-9% regular loans")
            reasons.append("Covers crop cultivation + animal husbandry + fishery")

        if not eligible:
            reasons.append("KCC is for farmers with cultivable agricultural land")

        return {
            "name": "Kisan Credit Card (KCC)",
            "benefit": "Crop loan at 4% interest (after govt subsidy)",
            "eligible": eligible,
            "reasons": reasons,
            "apply_at": "Any bank, cooperative society, or NABARD",
        }

    def _check_soil_health(self, p: Dict) -> Dict:
        """Soil Health Card: Free soil testing for farmers."""
        eligible = False
        reasons = []

        if p.get("occupation") == "farmer":
            eligible = True
            reasons.append("All farmers can get free soil testing")
            reasons.append("Get Soil Health Card with nutrient recommendations")

        if not eligible:
            reasons.append("Soil Health Card is for farmers")

        return {
            "name": "Soil Health Card Scheme",
            "benefit": "Free soil testing + nutrient recommendations",
            "eligible": eligible,
            "reasons": reasons,
            "apply_at": "Soil Health Card portal or nearest Krishi Vigyan Kendra",
        }

    def _check_pm_fasal_bima(self, p: Dict) -> Dict:
        """PM Fasal Bima Yojana: Crop insurance at low premiums."""
        eligible = False
        reasons = []

        if p.get("occupation") == "farmer" and p.get("land_acres", 0) > 0:
            eligible = True
            reasons.append("All farmers (sharecroppers + tenant farmers) eligible")
            reasons.append("Premium: Kharif 2%, Rabi 1.5%, Commercial 5% of sum insured")
            reasons.append("Covers crop loss due to natural calamites, pests, diseases")

        if not eligible:
            reasons.append("PMFBY is for farmers growing notified crops")

        return {
            "name": "PM Fasal Bima Yojana",
            "benefit": "Crop insurance at 1.5-5% premium (govt pays rest)",
            "eligible": eligible,
            "reasons": reasons,
            "apply_at": "pmfby.gov.in or bank/insurance company",
        }

    def _check_enam(self, p: Dict) -> Dict:
        """e-NAM: Electronic National Agriculture Market — online trading."""
        eligible = False
        reasons = []

        if p.get("occupation") == "farmer":
            eligible = True
            reasons.append("All farmers can sell produce on e-NAM platform")
            reasons.append("Better prices through competitive bidding across markets")

        if not eligible:
            reasons.append("e-NAM is for farmers and traders in agriculture")

        return {
            "name": "e-NAM (National Agriculture Market)",
            "benefit": "Online trading of agriculture produce across 1,000+ mandis",
            "eligible": eligible,
            "reasons": reasons,
            "apply_at": "enam.gov.in",
        }

    # ── Education & Skill ──────────────────────────────────────────────────────

    def _check_pyramid_mission(self, p: Dict) -> Dict:
        """National Skill Development Mission / Skill India."""
        eligible = False
        reasons = []

        if p.get("occupation") in ["student", "unemployed", "rural_worker"]:
            eligible = True
            reasons.append("Free skill training under Skill India")
            reasons.append("Covers 40+ sectors — IT, healthcare, retail, etc.")
            reasons.append("Certification recognized by NSDC")

        if not eligible:
            reasons.append("Skill India is available for youth seeking employment")

        return {
            "name": "Skill India (PMKVY)",
            "benefit": "Free skill training + certification in 40+ sectors",
            "eligible": eligible,
            "reasons": reasons,
            "apply_at": "skillindia.gov.in or nearest Skill India centre",
        }

    def _check_iskm(self, p: Dict) -> Dict:
        """Impact linkage of Education with Skills and Knowledge for Market."""
        eligible = False
        reasons = []

        if p.get("occupation") in ["student", "unemployed"] and p.get("income_annual", 0) < 600000:
            eligible = True
            reasons.append("Scholarship for economically weaker students")
            reasons.append("Covers tuition, books, and living expenses")

        if not eligible:
            reasons.append("Requires family income below Rs 6 lakh")

        return {
            "name": "National Scholarship Portal Schemes",
            "benefit": "Scholarship for tuition + maintenance",
            "eligible": eligible,
            "reasons": reasons,
            "apply_at": "scholarships.gov.in",
        }

    # ── Employment & Entrepreneurship ──────────────────────────────────────────

    def _check_standup_india(self, p: Dict) -> Dict:
        """Stand-Up India: Loans Rs 10 lakh - 1 crore for SC/ST/Women."""
        eligible = False
        reasons = []

        if p.get("occupation") in ["self-employed", "business", "entrepreneur"]:
            if p.get("is_sc_st") or p.get("gender") == "female":
                eligible = True
                reasons.append("SC/ST or Woman entrepreneur eligible")
                reasons.append("Loan: Rs 10 lakh to Rs 1 crore")
                reasons.append("For greenfield enterprises in manufacturing, services, or trading")

        if not eligible:
            reasons.append("Stand-Up India is for SC/ST or Women entrepreneurs")

        return {
            "name": "Stand-Up India",
            "benefit": "Loans Rs 10 lakh to Rs 1 crore for SC/ST/Women entrepreneurs",
            "eligible": eligible,
            "reasons": reasons,
            "apply_at": "standupmitra.india.gov.in",
        }

    def _check_pmrevamp(self, p: Dict) -> Dict:
        """PM Rozgar Yojana: Employment generation for educated youth."""
        eligible = False
        reasons = []

        if p.get("occupation") in ["unemployed", "student"] and 18 <= p.get("age", 0) <= 35:
            eligible = True
            reasons.append("Educated unemployed youth (18-35 years) eligible")
            reasons.append("Interest subsidy on loans for self-employment")

        if not eligible:
            reasons.append("PM Rozgar is for educated unemployed youth 18-35 years")

        return {
            "name": "PM Rozgar Yojana",
            "benefit": "Interest subsidy on self-employment loans",
            "eligible": eligible,
            "reasons": reasons,
            "apply_at": "pmry.gov.in",
        }

    # ── Pension & Insurance ────────────────────────────────────────────────────

    def _check_nps(self, p: Dict) -> Dict:
        """National Pension System: Voluntary pension with tax benefits."""
        age = p.get("age", 0)
        eligible = 18 <= age <= 65
        reasons = []

        if eligible:
            reasons.append(f"Age {age} is within 18-65 years range")
            reasons.append("Additional Rs 50,000 tax deduction under 80CCD(1B)")
            reasons.append("Market-linked returns with govt backing")

        if not eligible:
            reasons.append("NPS requires age between 18-65 years")

        return {
            "name": "National Pension System (NPS)",
            "benefit": "Additional Rs 50,000 tax deduction + pension corpus",
            "eligible": eligible,
            "reasons": reasons,
            "apply_at": "npscra.nsdl.co.in or any bank",
        }

    def _check_jandhan(self, p: Dict) -> Dict:
        """Jan Dhan Yojana: Zero-balance bank account for all."""
        eligible = False
        reasons = []

        if p.get("has_aadhaar") or not p.get("has_bank_account"):
            eligible = True
            reasons.append("All Indian citizens can open Jan Dhan account")
            reasons.append("Zero balance required + RuPay debit card")
            reasons.append("Rs 2 lakh accident insurance + Rs 30,000 life cover")

        if not eligible:
            reasons.append("Jan Dhan is available for all Indian citizens")

        return {
            "name": "Pradhan Mantri Jan Dhan Yojana",
            "benefit": "Zero-balance account + Rs 2 lakh insurance + overdraft facility",
            "eligible": eligible,
            "reasons": reasons,
            "apply_at": "Any bank branch with Aadhaar + identity proof",
        }

    def _check_senior_citizen_savings(self, p: Dict) -> Dict:
        """Senior Citizens Savings Scheme: 8.2% interest for 60+."""
        age = p.get("age", 0)
        eligible = age >= 60
        reasons = []

        if eligible:
            reasons.append(f"Age {age} — senior citizen eligible")
            reasons.append("8.2% interest, 5-year tenure, Rs 30 lakh max deposit")
            reasons.append("Tax benefit under Section 80C")

        if not eligible:
            reasons.append("SCSS requires age 60+ (or 55+ on retirement)")

        return {
            "name": "Senior Citizens Savings Scheme (SCSS)",
            "benefit": "8.2% guaranteed interest on Rs 30 lakh",
            "eligible": eligible,
            "reasons": reasons,
            "apply_at": "Post office or authorized bank",
        }

    # ── Digital & Startup ──────────────────────────────────────────────────────

    def _check_digital_india(self, p: Dict) -> Dict:
        """Digital India: Digital literacy and internet access programs."""
        eligible = False
        reasons = []

        if p.get("occupation") in ["student", "unemployed", "rural_worker"]:
            eligible = True
            reasons.append("Free digital literacy training available")
            reasons.append("PMGDISHA: Certificate in digital skills")

        if not eligible:
            reasons.append("Digital India programs are available for all citizens")

        return {
            "name": "Digital India (PMGDISHA)",
            "benefit": "Free digital literacy training + certificate",
            "eligible": eligible,
            "reasons": reasons,
            "apply_at": "Common Service Centres",
        }

    def _check_startup_india(self, p: Dict) -> Dict:
        """Startup India: Tax holidays, funding, and easier compliance."""
        eligible = False
        reasons = []

        if p.get("occupation") in ["self-employed", "business", "entrepreneur"]:
            eligible = True
            reasons.append("Startups can register on Startup India portal")
            reasons.append("3-year tax holiday + self-certification for compliance")
            reasons.append("Fund of Funds (Rs 10,000 crore) access")

        if not eligible:
            reasons.append("Startup India is for recognized startups")

        return {
            "name": "Startup India",
            "benefit": "3-year tax holiday + Fund of Funds + easier compliance",
            "eligible": eligible,
            "reasons": reasons,
            "apply_at": "startupindia.gov.in",
        }

    # ── State-specific ─────────────────────────────────────────────────────────

    def _check_state_schemes(self, p: Dict) -> Dict:
        """State-specific schemes based on user's state."""
        state = (p.get("state") or "").lower().strip()
        eligible = False
        reasons = []
        state_benefits = []

        state_map = {
            "delhi": [
                "Ladli Yojana — Rs 5,000-11,000 for girl child",
                "Free water (20,000 litres/month) + electricity subsidy",
                "Odd-even scheme benefits",
            ],
            "maharashtra": [
                "Mahatma Jyotiba Phule Jan Arogya Yojana — Rs 2.5 lakh health cover",
                "Majhi Ladki Bahin — Rs 1,500/month to eligible women",
                "Shasan Apli Didi — Women empowerment programs",
            ],
            "uttar pradesh": [
                "Kanya Sumangala Yojana — Rs 15,000-20,000 for girl child",
                "Mukhyamantri Kisan Sampada Yojana — Agricultural support",
                "UP Free Laptop Yojana — For meritorious students",
            ],
            "tamil nadu": [
                "Amma Two-Wheeler Scheme — Subsidy on scooty for women",
                "UDAN — Free education for poor students",
                "Kalyanam Kamayagam — Marriage assistance",
            ],
            "rajasthan": [
                "Chiranjeevi Yojana — Rs 25 lakh health cover",
                "Indira Gandhi Free Smartphone — For women students",
                "Lado Laxmi Yojana — Financial assistance to women",
            ],
            "madhya pradesh": [
                "Ladli Laxmi Yojana — Rs 1.18 lakh for girl child education",
                "Mukhyamantri Kisan Kalyan Yojana — Rs 4,000/year to farmers",
                "Jankalyan — 100+ welfare schemes",
            ],
            "karnataka": [
                "Gruha Lakshmi — Rs 2,000/month to women heads of family",
                "Yuva Nidhi — Unemployment allowance for graduates",
                "Shakti — Free bus travel for women",
            ],
            "west bengal": [
                "Lakshmir Bhandar — Rs 1,000-1,200/month to women",
                "Swasthya Sathi — Rs 5 lakh health cover",
                "Kanyashree — Scholarships for girl students",
            ],
            "gujarat": [
                "Mukhyamantri Mahila Utkarsh Yojana — 2% interest on loans",
                "Smart City Mission — Urban development",
                "Mukhyamantri Drashti Yojana — Eye care for students",
            ],
            "andhra pradesh": [
                "Amma Vodi — Rs 15,000 to mothers for child's education",
                "YSR Rythu Bharosa — Rs 13,500/year to farmers",
                "Jagananna Vidya Deevena — Free education",
            ],
            "telangana": [
                "Rythu Bandhu — Rs 10,000/year to farmers",
                "KCR Kit — Rs 12,000 for pregnant women",
                "Kalyana Lakshmi — Rs 1.01 lakh for SC/ST/BC girls' marriage",
            ],
            "bihar": [
                "Mukhyamantri Kanya Utthan Yojana — Rs 50,000 for graduation",
                "Jeevika — Self-help group support",
                "Saat Nischay — 7 resolution development programs",
            ],
            "punjab": [
                "Mukhyamantri Kamyab Kisan Yojana — Interest-free farm loans",
                "Maa Bhagwati Bike Yojana — Free bike for meritorious girls",
                "Smart Phone Yojana — Subsidized smartphones",
            ],
        }

        for state_key, benefits in state_map.items():
            if state_key in state:
                eligible = True
                state_benefits = benefits
                reasons.append(f"You are in {state.title()} — {len(benefits)} state schemes available")
                break

        if not eligible and state:
            reasons.append(f"No state-specific schemes mapped for {state.title()} yet")
        elif not state:
            reasons.append("Tell me your state for state-specific scheme info")

        return {
            "name": f"State Schemes ({state.title() if state else 'Unknown'})",
            "benefit": "State-specific welfare schemes",
            "eligible": eligible,
            "reasons": reasons,
            "state_benefits": state_benefits,
            "apply_at": "State government portal",
        }


# Singleton
eligibility_checker = EligibilityChecker()
