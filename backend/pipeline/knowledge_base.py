"""
Indian Knowledge Base for Zenix Agent.
Provides structured, factual information on Indian law, health, education,
constitution, and consumer rights that can be retrieved via the search tool.
"""


class IndianKnowledgeBase:
    """
    In-memory knowledge base with curated Indian content.
    Content is organized by domain and can be searched via keyword matching.
    """

    def __init__(self):
        self.knowledge = {}
        self._seed_all()

    def _seed_all(self):
        self._seed_constitution()
        self._seed_legal_rights()
        self._seed_health()
        self._seed_education()
        self._seed_consumer_rights()
        self._seed_labour_laws()
        self._seed_environment()

    def _add(self, domain: str, title: str, content: str, tags: list = None):
        if domain not in self.knowledge:
            self.knowledge[domain] = []
        self.knowledge[domain].append({
            "title": title,
            "content": content.strip(),
            "tags": [t.lower() for t in (tags or [])],
        })

    def search(self, query: str, domain: str = None, top_k: int = 5) -> list:
        """Search the knowledge base. Returns list of matching entries."""
        query_lower = query.lower()
        query_words = set(query_lower.split())
        results = []

        domains_to_search = [domain] if domain and domain in self.knowledge else self.knowledge.keys()

        for dom in domains_to_search:
            for entry in self.knowledge[dom]:
                # Score: title match > tag match > content match
                score = 0
                title_lower = entry["title"].lower()
                content_lower = entry["content"].lower()

                # Exact title substring match
                if query_lower in title_lower:
                    score += 10
                # Word overlap with title
                for w in query_words:
                    if w in title_lower:
                        score += 3
                # Tag match
                for tag in entry["tags"]:
                    if tag in query_lower or query_lower in tag:
                        score += 5
                    for w in query_words:
                        if w in tag:
                            score += 1
                # Content word overlap
                for w in query_words:
                    if len(w) > 2 and w in content_lower:
                        score += 1

                if score > 0:
                    results.append({**entry, "domain": dom, "score": score})

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def get_domains(self) -> list:
        return list(self.knowledge.keys())

    # ── Constitution ──────────────────────────────────────────────────────

    def _seed_constitution(self):
        d = "constitution"

        self._add(d, "Fundamental Rights (Part III, Articles 12-35)",
            """Fundamental Rights guaranteed by the Indian Constitution:

1. Right to Equality (Articles 14-18):
   - Art 14: Equality before law and equal protection of laws
   - Art 15: Prohibition of discrimination on grounds of religion, race, caste, sex, or place of birth
   - Art 16: Equality of opportunity in public employment
   - Art 17: Abolition of Untouchability (Offence punishable by law)
   - Art 18: Abolition of titles (except military and academic)

2. Right to Freedom (Articles 19-22):
   - Art 19: Six freedoms — speech, assembly, association, movement, residence, profession
   - Art 20: Protection in respect of conviction for offences (no ex-post-facto law, no double jeopardy, no self-incrimination)
   - Art 21: Protection of life and personal liberty (cannot be deprived except by procedure established by law)
   - Art 21A: Right to Education (6-14 years, free and compulsory)
   - Art 22: Protection against arrest and detention

3. Right against Exploitation (Articles 23-24):
   - Art 23: Prohibition of traffic in human beings and forced labour (begar)
   - Art 24: Prohibition of employment of children below 14 in factories

4. Right to Freedom of Religion (Articles 25-28):
   - Art 25: Freedom of conscience and free profession, practice, propagation of religion
   - Art 26: Freedom to manage religious affairs
   - Art 27: Freedom from payment of taxes for promotion of any particular religion
   - Art 28: Freedom from attendance at religious instruction in state-funded institutions

5. Cultural and Educational Rights (Articles 29-30):
   - Art 29: Protection of interests of minorities
   - Art 30: Right of minorities to establish and administer educational institutions

6. Right to Constitutional Remedies (Article 32):
   - Right to move Supreme Court for enforcement of Fundamental Rights
   - SC can issue writs: Habeas Corpus, Mandamus, Prohibition, Certiorari, Quo Warranto""",
            ["fundamental rights", "articles", "constitution", "equality", "freedom", "privacy", "article 21", "article 14"]
        )

        self._add(d, "Fundamental Duties (Article 51A)",
            """Fundamental Duties of Indian Citizens (Article 51A, added by 42nd Amendment 1976):

1. To abide by the Constitution and respect its ideals, institutions, National Flag, and National Anthem
2. To cherish and follow the noble ideals that inspired the national struggle for freedom
3. To uphold and protect the sovereignty, unity, and integrity of India
4. To defend the country and render national service when called upon
5. To promote harmony and the spirit of common brotherhood amongst all people of India
6. To value and preserve the rich heritage of composite culture
7. To protect and improve the natural environment (forests, lakes, rivers, wildlife)
8. To develop the scientific temper, humanism, and spirit of inquiry and reform
9. To safeguard public property and to abjure violence
10. To strive towards excellence in all spheres of individual and collective activity
11. To provide opportunities for education to children between 6-14 years (added by 86th Amendment, 2002)""",
            ["fundamental duties", "duties", "51a", "citizen", "constitution"]
        )

        self._add(d, "Directive Principles of State Policy",
            """Key Directive Principles (Part IV, Articles 36-51):

- Art 39: DPSPs are guidelines for the State while making laws
- Art 39A: Equal justice and free legal aid
- Art 40: Organisation of village panchayats
- Art 41: Right to work, education, and public assistance
- Art 42: Just and humane conditions of work and maternity relief
- Art 43: Living wage and standard of life for workers
- Art 43A: Participation of workers in management of industries
- Art 44: Uniform Civil Code for all citizens
- Art 45: Provision for early childhood care and education (below 6 years)
- Art 46: Promotion of educational and economic interests of SCs, STs, and weaker sections
- Art 47: Duty of the State to raise the level of nutrition and standard of living; improve public health
- Art 48: Organisation of agriculture and animal husbandry
- Art 48A: Protection and improvement of environment and safeguarding forests and wildlife
- Art 50: Separation of judiciary from executive
- Art 51: Promotion of international peace and security

Note: DPSPs are non-justiciable (cannot be enforced by courts) but are fundamental in governance.""",
            ["directive principles", "dpsp", "uniform civil code", "panchayat", "welfare state"]
        )

        self._add(d, "Constitutional Bodies",
            """Key Constitutional Bodies:

1. Election Commission of India (Art 324):
   - Conducts elections for Parliament, State Legislatures, President, Vice President
   - Chief Election Commissioner + Election Commissioners
   - Website: eci.gov.in

2. Comptroller and Auditor General (Art 148):
   - Audits all government accounts
   - Appointed by the President

3. Union Public Service Commission (Art 315):
   - Conducts Civil Services and other central recruitment exams
   - Chairman + members appointed by President

4. State Public Service Commissions (Art 315-323)
5. Finance Commission (Art 280): Recommends tax distribution between Centre and States
6. National Commission for SCs (Art 338)
7. National Commission for STs (Art 338A)
8. Special Officer for Linguistic Minorities (Art 350B)""",
            ["election commission", "upsc", "cag", "constitutional bodies", "government"]
        )

    # ── Legal Rights ─────────────────────────────────────────────────────

    def _seed_legal_rights(self):
        d = "legal_rights"

        self._add(d, "RTI Act — Right to Information",
            """Right to Information Act, 2005:

Purpose: To provide citizens access to information held by public authorities.

Key Provisions:
- Any citizen can request information from any public authority
- Response must be given within 30 days (48 hours if life/liberty at stake)
- First appeal to designated officer (within 30 days)
- Second appeal to State/Central Information Commission
- Fee: Rs 10 (ordinary), Rs 2 (BPL cards — no application fee)

Information Exempt (Section 8):
- National security, strategic interests
- Personal information (privacy)
- Trade secrets, intellectual property
- Cabinet papers (25-year rule)

Penalties:
- Rs 250/day for delay (max Rs 25,000)
- Officer can be disciplined for unreasonable delay

How to File RTI:
1. Write application in English/Hindi/local language
2. Address: Public Information Officer (PIO) of the department
3. Pay fee (IPO, demand draft, or online)
4. Get application number for tracking

Online RTI: rtionline.gov.in (for central government departments)""",
            ["rti", "right to information", "transparency", "government", "information commission"]
        )

        self._add(d, "Consumer Protection Act, 2019",
            """Consumer Protection Act, 2019 (replaced 1986 Act):

Who is a Consumer?
- Any person who buys goods or hires services for consideration
- Includes online purchases and e-commerce transactions
- Does not include goods obtained for resale or commercial purposes

Consumer Rights:
1. Right to Safety
2. Right to be Informed
3. Right to Choose
4. Right to be Heard
5. Right to Seek Redressal
6. Right to Consumer Education

Complaint Forums:
- District Commission: Claims up to Rs 1 crore
- State Commission: Claims Rs 1-10 crore
- National Commission: Claims above Rs 10 crore

How to File Complaint:
1. Write complaint with: name, address, date of purchase, amount paid, complaint details
2. File at: edaakhil.nic.in (online) or district commission office
3. No lawyer needed (consumer can self-represent)
4. Fee: Rs 100-200 depending on claim amount
5. Hearing: Within 90 days (3 months)

E-commerce Rules:
- Sellers must display country of origin
- No fake reviews allowed
- Easy return/refund within 14 days
- Grievance officer must respond within 48 hours""",
            ["consumer", "consumer protection", "complaint", "refund", "e-commerce", "product defect"]
        )

        self._add(d, "Criminal Laws — Bharatiya Nyaya Sanhita (BNS) 2023",
            """Key Provisions of Bharatiya Nyaya Sanhita (BNS) — effective 1 July 2024:
(Replaces Indian Penal Code, 1860)

Major Offences:
- Murder (Section 101): Life imprisonment or death
- Culpable Homicide not amounting to Murder (Section 103): Up to 10 years
- Rape (Section 63): 10 years to life imprisonment
- Theft (Section 303): Up to 3 years
- Robbery (Section 309): Up to 10 years
- Cheating (Section 318): Up to 3 years
- Cyber Crimes (Section 317): Up to 3 years + fine

New Provisions:
- Organised crime: Life imprisonment or death
- Terrorist acts: Up to death
- Mob lynching: Death or life imprisonment
- Community service as punishment for minor offences
- Reporting by women: No time limit for filing rape complaint

Your Rights if Arrested:
- Right to know grounds of arrest
- Right to legal counsel (Article 22)
- Right to inform family/friend
- Right to be produced before magistrate within 24 hours
- Right to medical examination
- Right against self-incrimination (Article 20)""",
            ["bns", "criminal law", "ipc", "arrest", "police", "murder", "theft", "cheating"]
        )

        self._add(d, "Domestic Violence — Protection of Women Act",
            """Protection of Women from Domestic Violence Act, 2005:

Definition of Domestic Violence:
- Physical abuse (hitting, slapping, kicking)
- Sexual abuse (forced sexual acts)
- Verbal abuse (insults, threats, name-calling)
- Emotional abuse (intimidation, isolation)
- Economic abuse (denying money, food, shelter)
- Digital abuse (monitoring phone, cyber-stalking)

Who Can File Complaint?
- Wife or live-in partner
- Mother, sister, daughter
- Any woman related by blood, marriage, or adoption

Available Remedies:
1. Protection Order: Abuser must stop violence
2. Residence Order: Woman cannot be evicted from shared household
3. Monetary Relief: Compensation for medical expenses, loss of earnings
4. Custody Order: Temporary custody of children
5. Compensation Order: Damages for mental agony

How to File:
1. Call **181** (Women Helpline) or **1091** (Police)
2. Visit nearest Magistrate court
3. File application (no court fee)
4. Get protection order within 60 days

Emergency: Dial **100** for Police, **181** for Women Helpline, **1091** for Police Control Room""",
            ["domestic violence", "women safety", "protection order", "dv", "abuse", "181", "women helpline"]
        )

        self._add(d, "Sexual Harassment — POSH Act",
            """Sexual Harassment of Women at Workplace (Prevention, Prohibition and Redressal) Act, 2013:

What is Sexual Harassment?
- Physical contact and advances
- Demand or request for sexual favours
- Making sexually coloured remarks
- Showing pornography
- Any other unwelcome physical, verbal, or non-verbal conduct of sexual nature

Who is Covered?
- All workplaces (organized and unorganized)
- Government, private, unorganized sectors
- Includes: domestic workers, daily wage workers
- Applies to: coworkers, clients, customers, supervisors

Internal Complaints Committee (ICC):
- Mandatory in every organization with 10+ employees
- Must have: Presiding Officer (senior woman), 2 members, 1 external member
- Complaint must be filed within 3 months of incident

Penalties for Employer:
- Rs 50,000 for not constituting ICC
- Rs 1,00,000 for non-compliance with orders
- Repeat offence: Double penalty

Helpline: 181 (Women Helpline), 1091 (Police)""",
            ["sexual harassment", "posh", "workplace", "women", "icc", "complaint"]
        )

        self._add(d, "FIR Filing — Criminal Procedure",
            """How to File an FIR (First Information Report):

What is FIR?
- Written record of information given to police about a cognizable offence
- First step in criminal justice process

Your Rights:
- Right to file FIR for cognizable offence (police MUST register it)
- Right to get a copy of FIR free of cost
- Right to file FIR in any police station (Zero FIR — can be transferred later)
- Right to file complaint electronically (e-FIR)

How to File:
1. Visit nearest police station
2. Tell the duty officer about the offence
3. Officer will record your statement
4. Read the FIR before signing
5. Get a copy with FIR number

If Police Refuse to File FIR:
1. Send written complaint to Superintendent of Police (SP)
2. File complaint at: court of Judicial Magistrate
3. Use: cpgrams.nic.in (Central Govt grievance)
4. Call: 100 (Police Control Room)

E-FIR: Many states allow online FIR filing at respective state police websites
- Delhi: delhipolice.gov.in
- Maharashtra: mahapolice.gov.in
- Karnataka: ksp.gov.in

Zero FIR: You can file FIR at ANY police station regardless of jurisdiction. It will be transferred to the correct station.""",
            ["fir", "police", "complaint", "criminal", "zero fir", "efir", "arrest"]
        )

    # ── Health ────────────────────────────────────────────────────────────

    def _seed_health(self):
        d = "health"

        self._add(d, "Ayushman Bharat — PM-JAY Health Insurance",
            """Ayushman Bharat — Pradhan Mantri Jan Arogya Yojana (PM-JAY):

Coverage: Rs 5 lakh per family per year for secondary and tertiary hospitalization
Beneficiaries: ~50 crore people from poor and vulnerable families

Eligibility:
- Families identified as per SECC 2011 database
- No enrollment required — check at hospital or call helpline
- Rural: BPL families, SC/ST, manual scavengers, freed bonded labourers
- Urban: Ragpickers, beggars, domestic workers, street vendors, construction workers

What is Covered:
- All pre and post-hospitalization expenses (3 days + 15 days)
- Day care procedures
- 1,929 medical packages covering surgery, medical, day care
- ICU, medicines, diagnostics, food during hospitalization

Not Covered:
- Outpatient department (OPD) expenses
- Drug and cosmetic treatments
- Organ transplants
- Infertility treatment
- Treatment abroad

Hospitals: All empanelled government and private hospitals (check at: beneficiary.nha.gov.in)

How to Use:
1. Visit empanelled hospital with Aadhaar card
2. Verify eligibility at hospital help desk
3. Get treatment — no cash payment needed
4. Call helpline: **14555** or **1800-111-565** (toll-free)

Check eligibility: pmjay.gov.in""",
            ["ayushman", "pmjay", "health insurance", "hospital", "medical", "bpl", "free treatment"]
        )

        self._add(d, "Jan Aushadhi — Affordable Generic Medicines",
            """Pradhan Mantri Bhartiya Janaushadhi Pariyojana (PMBJP):

Purpose: Quality generic medicines at affordable prices (50-90% cheaper than branded)

Key Facts:
- 10,000+ Jan Aushadhi Kendras across India
- 2,000+ medicines and 300+ surgical items available
- All medicines quality-tested by NABL-accredited labs
- Same salt composition as branded medicines

Price Comparison:
- Branded Paracetamol 500mg: Rs 25-30
- Jan Aushadhi Paracetamol 500mg: Rs 2-3
- Branded Omeprazole 20mg: Rs 90-120
- Jan Aushadhi Omeprazole 20mg: Rs 5-8

How to Find Store:
- App: Janaushadhi Sugam (available on Play Store)
- Website: janaushadhi.gov.in
- Call: 1800-180-8080 (toll-free)
- SMS: Type JANAUSHADHI and send to 9212240040

Available Medicines:
- Antibiotics, antacids, painkillers
- Diabetes, hypertension, cardiac medicines
- Vitamins and supplements
- Surgical items, dressings, disposables
- contraceptives""",
            ["janaushadhi", "generic medicine", "affordable medicine", "pharmacy", "medicine price"]
        )

        self._add(d, "COVID-19 Vaccination & Testing",
            """COVID-19 Vaccination in India:

Free Vaccination:
- Available at government hospitals and health centres
- All citizens eligible (age 5+)
- Booster dose (precautionary dose) for 18+

Vaccines Available:
- Covishield (AstraZeneca)
- Covaxin (Bharat Biotech)
- Corbevax (Biological E)
- mRNA vaccine (Gennova)

COVID Testing:
- RT-PCR: Rs 500 (govt), Rs 500-2000 (private)
- Rapid Antigen Test: Rs 50-200
- Free testing at govt centres

Emergency Numbers:
- COVID Helpline: **1075** (toll-free)
- National Helpline: **1800-112-545**
- Aarogya Setu App: For nearest testing centre

Helpline Numbers by State:
- Delhi: 011-22307145
- Maharashtra: 020-26127394
- Karnataka: 104
- Tamil Nadu: 044-24335050""",
            ["covid", "vaccination", "testing", "coronavirus", "covid helpline"]
        )

        self._add(d, "Emergency Numbers — Medical",
            """India Emergency Medical Numbers:

Ambulance: 108
Blood Bank Helpline: 104
Mental Health Helpline: 080-46110007 (Vandrevala Foundation)
COVID Helpline: 1075
AIDS Helpline: 1097
Poison Information Centre: 1066
National Ambulance Service: 102
Fire: 101
Police: 100
Disaster Management: 108
Women Helpline: 181
Child Helpline: 1098
Senior Citizen Helpline: 14567

Government Hospitals:
- AIIMS Delhi: 011-26588500, 011-26588700
- Safdarjung Hospital: 011-26707439
- CMR (Central Government):
  - cgisha.gov.in for hospital list

Health Portals:
- ABHA (Ayushman Bharat Health Account): abha.abdm.gov.in
- e-Sanjeevani (Telemedicine): esanjeevaniopd.in
- CoWIN (Vaccination): cowin.gov.in""",
            ["emergency number", "ambulance", "blood bank", "hospital number", "mental health"]
        )

    # ── Education ─────────────────────────────────────────────────────────

    def _seed_education(self):
        d = "education"

        self._add(d, "Right to Education Act (RTE)",
            """Right of Children to Free and Compulsory Education Act, 2009:

Key Provisions:
- Every child (6-14 years) has right to free and compulsory education
- No child shall be held back, expelled, or required to pass board exam till Class 8
- 25% seats reserved for economically weaker sections in private schools
- No donation or capitation fee allowed
- No admission test for entry-level classes
- Teachers must have minimum qualifications (D.Ed/B.Ed by 2015 deadline)

School Infrastructure:
- pupil-teacher ratio: 30:1 (primary), 35:1 (upper primary)
- At least one female teacher for primary schools
- Barrier-free access for disabled children
- Drinking water, toilets, kitchen mid-day meal facility
- No school shall function without RC (Recognition Certificate)

Parental Duties:
- Ensure child attends school (aged 6-14)
- Cooperation with school in education

Prohibited:
- Physical punishment or mental harassment
- Screening procedures for admission
- Private tutoring by teachers
- Capitation fee and donations

Grievance: File complaint with State Commission for Protection of Child Rights (SCPCR)""",
            ["rte", "right to education", "school", "admission", "child rights", "education act"]
        )

        self._add(d, "Scholarships for Indian Students",
            """Major Government Scholarships:

1. Post Matric Scholarship (SC/ST/OBC):
   - For Class 11 to PhD
   - Covers tuition, maintenance, book allowance
   - Apply: scholarships.gov.in

2. Pre Matric Scholarship (SC/ST):
   - For Class 5 to 10
   - Maintenance + book allowance

3. National Means Cum Merit Scholarship (NMMSS):
   - For Class 9-12 (family income < Rs 3.5 lakh)
   - Rs 12,000/year (Rs 1,000/month)
   - Selection via NSEJS/NTSE exam

4. Central Sector Scholarship (College students):
   - For students with family income < Rs 8 lakh
   - Rs 10,000/year (Graduation)
   - Rs 20,000/year (Post Graduation)
   - Rs 20,000/year (Professional courses)

5. AICTE Scholarship (Technical education):
   - Pragati: Rs 50,000/year for girls in technical education
   - Saksham: Rs 50,000/year for differently-abled students

6. Maulana Azad National Fellowship (Minorities):
   - For M.Phil and Ph.D
   - Rs 31,000/month (JRF) + Rs 35,000/month (SRF)

Apply at: scholarships.gov.in""",
            ["scholarship", "education", "student", "financial aid", "fellowship", "sc scholarship"]
        )

        self._add(d, "National Education Policy 2020",
            """National Education Policy (NEP) 2020 — Key Highlights:

School Education (5+3+3+4 Structure):
- Ages 3-8: Foundational Stage (3 years preschool + Class 1-2)
- Ages 8-11: Preparatory Stage (Class 3-5)
- Ages 11-14: Middle Stage (Class 6-8)
- Ages 14-18: Secondary Stage (Class 9-12)

Key Changes:
- Mother tongue/regional language as medium of instruction till Class 5
- No rigid stream separation (Science, Arts, Commerce — all subjects available)
- Board exams reduced — test core competency, not coaching/tutoring
- Internal assessment + semester system
- Coding and vocational exposure from Class 6
- AI, Data Science, Environmental Science in curriculum
- Grading system: NEP grading for schools

Higher Education:
- Multiple entry/exit system (certificate after 1 year, diploma after 2, degree after 3/4)
- Academic Bank of Credits (ABC) — transfer credits across universities
- Multidisciplinary education
- Top 100 global universities allowed to set up campuses in India
- GATE-like entrance for all streams
- NTA for all exams

Other Features:
- Special Education Zones for disadvantaged regions
- Gender Inclusion Fund
- Technology in education: DIKSHA, SWAYAM, National Digital Education Architecture""",
            ["nep", "national education policy", "education reform", "curriculum", "board exam", "5+3+3+4"]
        )

        self._add(d, "National Testing Agency (NTA) Exams",
            """Major NTA Exams and Key Information:

1. JEE Main (Engineering):
   - Eligibility: Class 12 pass (75% marks or top 20 percentile)
   - Sessions: January and April
   - Website: jeemain.nta.ac.in

2. NEET-UG (Medical/Dental):
   - Eligibility: Class 12 with Physics, Chemistry, Biology
   - Age: 17+ years
   - Website: neet.nta.nic.in

3. CUET-UG (Central University Admission):
   - For admission to Central Universities and participating institutions
   - Domain subjects + General Test + Language
   - Website: cuet.nta.nic.in

4. UGC-NET (Assistant Professor / JRF):
   - Eligibility: Master's degree with 55% marks
   - Website: ugcnet.nta.nic.in

5. CTET (Teacher Eligibility):
   - For teaching in government schools
   - Paper 1 (Class 1-5), Paper 2 (Class 6-8)
   - Website: ctet.nta.nic.in

General Information:
- All registration online at nta.ac.in
- Admit card: Download from respective exam website
- Results: Via roll number at exam website
- Helpline: 011-40759000, 011-69227700""",
            ["nta", "jee", "neet", "cuet", "ugc net", "ctet", "entrance exam", "exam"]
        )

    # ── Consumer Rights ───────────────────────────────────────────────────

    def _seed_consumer_rights(self):
        d = "consumer_rights"

        self._add(d, "Digital Personal Data Protection Act, 2023",
            """Digital Personal Data Protection (DPDP) Act, 2023:

Key Rights of Data Principals (Citizens):
1. Right to access information about data processing
2. Right to correction and erasure of personal data
3. Right to grievance redressal
4. Right to nominate (designate someone to exercise rights after death)

Obligations of Data Fiduciaries (Companies):
- Must obtain consent before processing personal data
- Purpose limitation — use data only for stated purpose
- Data minimization — collect only what's necessary
- Reasonable security safeguards
- Data breach notification to Data Protection Board and affected individuals
- Erase data when purpose is fulfilled or consent withdrawn

Significant Data Fiduciaries:
- Additional obligations: Data Protection Officer, independent audit, DPIA
- Government may notify based on: volume of data, sensitivity, risk

Exemptions:
- National security, sovereignty, public order
- Research, statistics, archiving
- Employment-related processing
- Compliance with law

Penalties:
- Failure to take reasonable security: Up to Rs 250 crore
- Failure to notify breach: Up to Rs 200 crore
- Non-compliance with Board directions: Up to Rs 50 crore

Data Protection Board of India:
- Adjudicates complaints and disputes
- Online mechanism for filing complaints
- Website: dpdpboard.in (expected)""",
            ["dpdp", "data protection", "privacy", "personal data", "consent", "gdpr", "digital"]
        )

        self._add(d, "Cybercrime — How to Report",
            """How to Report Cybercrime in India:

Cybercrime Portal: cybercrime.gov.in
- File complaint for: Financial fraud, online harassment, hacking, identity theft
- Register as citizen → File complaint → Track status

Types of Cybercrime:
1. Financial Fraud: UPI fraud, credit/debit card fraud, online banking fraud
   - Report to bank immediately
   - Call: 1930 (National Cybercrime Helpline)
   - File on: cybercrime.gov.in

2. Online Harassment: Cyberstalking, morphing, revenge porn
   - Call: 100 (Police) + 1930
   - Women: 181 (Women Helpline)
   - File FIR at local police station

3. Social Media Fraud: Fake profiles, impersonation, scams
   - Report to: platform (Facebook, Instagram, etc.)
   - File complaint at cybercrime.gov.in

4. Identity Theft:
   - Report to: RBI (for financial), police, cybercrime portal
   - Alert CIBIL: cibil.com
   - Freeze bank accounts if needed

Steps if You're a Victim:
1. Don't panic — preserve evidence (screenshots, messages)
2. Block the suspicious account/person
3. Change all passwords immediately
4. Report to: cybercrime.gov.in or call 1930
5. File FIR at local police station
6. Report to your bank (for financial fraud)
7. Check: Have I Been Pwned (haveibeenpwned.com) for data breach

Helplines:
- National Cybercrime: 1930 (toll-free)
- Women Cybercrime: 181
- Delhi Cybercrime: 011-27401011
- Maharashtra: 022-22621011""",
            ["cybercrime", "cyber", "online fraud", "hacking", "identity theft", "scam", "1930"]
        )

    # ── Labour Laws ───────────────────────────────────────────────────────

    def _seed_labour_laws(self):
        d = "labour_laws"

        self._add(d, "Minimum Wages & Worker Rights",
            """Minimum Wages & Worker Rights in India:

Minimum Wages (varies by state and skill level):
- Unskilled: Rs 8,000 - 14,000/month (state-dependent)
- Semi-skilled: Rs 10,000 - 18,000/month
- Skilled: Rs 12,000 - 25,000/month
- Check your state's minimum wages: labour.gov.in

Key Labour Laws:
1. Payment of Wages Act, 1936:
   - Salary must be paid by 7th (10,000+ employees) or 10th (others)
   - No unauthorized deductions
   - Bonus: 8.33% of wages (mandatory)

2. Factories Act, 1948:
   - Working hours: Max 8 hours/day, 48 hours/week
   - Overtime: Double wages
   - Weekly off: At least 1 day per week
   - Leave: 1 day earned leave per 20 days worked
   - Women not allowed night work (12 AM - 6 AM) in factories (relaxing)

3. Employees' Provident Fund (EPF):
   - Applicable: 20+ employees
   - Contribution: 12% of basic (employee) + 12% (employer)
   - Website: epfindia.gov.in
   - UAN: Universal Account Number (12-digit)

4. Employee State Insurance (ESI):
   - For employees earning up to Rs 21,000/month
   - Contribution: 0.75% (employee) + 3.25% (employer)
   - Benefits: Medical, sickness, maternity, disability
   - Website: esic.gov.in

5. Maternity Benefit Act:
   - 26 weeks paid leave (for first two children)
   - 12 weeks (for third child onwards)
   - Applies to: 10+ employees establishment
   - Work from home option available

6. Payment of Gratuity Act:
   - Gratuity: 15 days wages for each year of service
   - Eligible after 5 years of continuous service
   - Maximum: Rs 20 lakh (tax-free up to Rs 20 lakh)""",
            ["minimum wage", "labour", "worker", "epf", "esi", "gratuity", "maternity", "working hours"]
        )

    # ── Environment ───────────────────────────────────────────────────────

    def _seed_environment(self):
        d = "environment"

        self._add(d, "Environmental Laws & Pollution Control",
            """Key Environmental Laws in India:

1. Environment Protection Act, 1986:
   - Umbrella legislation for environmental protection
   - Central Government can take measures to protect environment
   - Environmental Impact Assessment (EIA) mandatory for projects

2. Air (Prevention and Control of Pollution) Act, 1981:
   - CPCB and SPCB regulate air pollution
   - Consent required for industrial operations
   - Vehicle emission norms (BS-VI from April 2020)

3. Water (Prevention and Control of Pollution) Act, 1974:
   - CPCB and SPCB regulate water pollution
   - Industries must treat effluent before discharge
   - Fine up to Rs 1 lakh for first offence

4. National Green Tribunal Act, 2010:
   - Specialized tribunal for environmental cases
   - Can hear cases related to water, air, forest, biodiversity
   - Camp: Principal bench in Delhi + zonal benches
   - Appeal: Supreme Court within 90 days

5. Plastic Waste Management Rules, 2016:
   - Single-use plastic banned from July 2022
   - Extended Producer Responsibility (EPR)
   - All plastic carry bags below 50 microns banned

How to Report Pollution:
- CPCB: cpcb.nic.in → file complaint online
- State Pollution Control Board: Contact state environment dept
- National Green Tribunal: oral/complaint before NGT
- CPCB Helpline: 1800-110-011
- Emergency: 100 (Police)""",
            ["pollution", "environment", "plastic ban", "green tribunal", "cpcb", "air pollution", "water pollution"]
        )

        self._add(d, "Forest Rights Act — Tribal Rights",
            """Forest Rights Act, 2006 (Scheduled Tribes and Other Traditional Forest Dwellers):

Purpose: Recognize and vest forest rights of tribal and traditional forest-dwelling communities.

Rights Recognized:
1. Individual Rights:
   - Right to hold and live in forest land for habitation
   - Right to self-cultivate and hold forest land for subsistence
   - Maximum: 4 hectares (irrigated) or 8 hectares (rain-fed)

2. Community Rights:
   - Right to use and manage community forest resources
   - Rights over minor forest produce (MFP): Tendu leaves, honey, herbs, etc.
   - Community forest resource rights over entire area

3. Right to Protect, Regenerate, and Conserve:
   - Community can protect community forest resources
   - Traditional and customary rights
   - Right to access, use, and dispose of MFP

4. Right to Development:
   - In-situ rehabilitation (housing on forest land)
   - Alternative land for those displaced

How to Claim Rights:
1. Apply to Gram Sabha (village assembly)
2. Gram Sabha examines and verifies claims
3. Gram Sabha forwards to Sub-Divisional Committee
4. SD Committee forwards to District Level Committee
5. Final approval by District Collector

Documents Required:
- Proof of residence in forest area
- Proof of forest rights (traditional/community proof)
- Aadhaar card
- Recommendation from Gram Sabha

Helpline: Ministry of Tribal Affairs — 011-23382650""",
            ["forest rights", "tribal", "forest act", "forest land", "mfp", "gram sabha"]
        )


# Singleton instance
_knowledge_base = None


def get_knowledge_base() -> IndianKnowledgeBase:
    global _knowledge_base
    if _knowledge_base is None:
        _knowledge_base = IndianKnowledgeBase()
    return _knowledge_base
