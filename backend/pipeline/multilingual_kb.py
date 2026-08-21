"""
Multi-Language Knowledge Base for Zenix AI.
Provides knowledge base content in Hindi, Bengali, Tamil, and other Indian languages.
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class MultilingualKnowledgeBase:
    """
    Knowledge base with multi-language support.
    Contains key legal, health, and education content in Indian languages.
    """

    def __init__(self):
        self.content = {}
        self._seed_content()

    def _seed_content(self):
        """Seed knowledge base with multi-language content."""

        # Hindi content
        self.content["hindi"] = {
            "fundamental_rights": {
                "title": "मौलिक अधिकार",
                "content": """भारतीय संविधान के भाग III (अनुच्छेद 12-35) में मौलिक अधिकार:

1. समानता का अधिकार (अनुच्छेद 14-18):
   - अनुच्छेद 14: कानून के समक्ष समानता
   - अनुच्छेद 15: धर्म, जाति, लिंग, स्थान के आधार पर भेदभाव निषिद्ध
   - अनुच्छेद 16: सार्वजनिक रोजगार में समान अवसर
   - अनुच्छेद 17: छुआछूत का अंत
   - अनुच्छेद 18: उपाधियों का अंत

2. स्वतंत्रता का अधिकार (अनुच्छेद 19-22):
   - अनुच्छेद 19: 6 स्वतंत्रताएं - भाषण, सभा, संघ, आवागमन, निवास, व्यवसाय
   - अनुच्छेद 21: जीवन और व्यक्तिगत स्वतंत्रता की रक्षा
   - अनुच्छेद 21A: शिक्षा का अधिकार (6-14 वर्ष)

3. शोषण के विरुद्ध अधिकार (अनुच्छेद 23-24):
   - अनुच्छेद 23: मानव व्यापार और जबरन श्रम निषिद्ध
   - अनुच्छेद 24: 14 वर्ष से कम आयु के बच्चों का कारखानों में काम निषिद्ध

4. धार्मिक स्वतंत्रता का अधिकार (अनुच्छेद 25-28)

5. सांस्कृतिक और शैक्षिक अधिकार (अनुच्छेद 29-30)

6. संवैधानिक उपचारों का अधिकार (अनुच्छेद 32)""",
                "tags": ["मौलिक अधिकार", "संविधान", "अनुच्छेद", "कानून"]
            },
            "rti": {
                "title": "सूचना का अधिकार (आरटीआई)",
                "content": """सूचना का अधिकार अधिनियम, 2005:

उद्देश्य: नागरिकों को सरकारी जानकारी तक पहुंच प्रदान करना।

मुख्य प्रावधान:
- कोई भी नागरिक किसी भी सार्वजनिक प्राधिकरण से जानकारी मांग सकता है
- 30 दिनों के भीतर जवाब देना अनिवार्य
- जीवन और स्वतंत्रता के मामले में 48 घंटे
- अपील: सूचना आयोग में

शुल्क: ₹10 (सामान्य), ₹2 (बीपीएल कार्ड)

कैसे दायर करें:
1. अंग्रेजी या हिंदी में आवेदन लिखें
2. संबंधित विभाग के सूचना अधिकारी को भेजें
3. शुल्क का भुगतान करें
4. आवेदन संख्या प्राप्त करें

ऑनलाइन: rtionline.gov.in""",
                "tags": ["आरटीआई", "सूचना का अधिकार", "पारदर्शिता", "सरकार"]
            },
            "consumer_rights": {
                "title": "उपभोक्ता अधिकार",
                "content": """उपभोक्ता संरक्षण अधिनियम, 2019:

उपभोक्ता कौन है?
- कोई भी व्यक्ति जो विचार के बदले माल या सेवाएं खरीदता है
- ऑनलाइन खरीदारी भी शामिल

उपभोक्ता अधिकार:
1. सुरक्षा का अधिकार
2. सूचना का अधिकार
3. चयन का अधिकार
4. सुनवाई का अधिकार
5. निवारण का अधिकार
6. उपभोक्ता शिक्षा का अधिकार

शिकायत दायर करना:
1. शिकायत लिखें: नाम, पता, खरीद की तारीख, राशि
2. edaakhil.nic.in पर ऑनलाइन दायर करें
3. वकील की आवश्यकता नहीं
4. शुल्क: ₹100-200

ई-कॉमर्स नियम:
- विक्रेताओं को मूल देश दिखाना अनिवार्य
- नकली समीक्षाएं निषिद्ध
- 14 दिनों में आसान वापसी/रिफंड""",
                "tags": ["उपभोक्ता", "उपभोक्ता संरक्षण", "शिकायत", "ई-कॉमर्स"]
            },
            "emergency_numbers": {
                "title": "आपातकालीन नंबर",
                "content": """भारत में आपातकालीन नंबर:

🚨 पुलिस: 100
🚒 दमकल: 101
🚑 एम्बुलेंस: 108
👩 महिला हेल्पलाइन: 181
👶 बाल हेल्पलाइन: 1098
🆘 आपदा: 112
🏥 रक्त बैंक: 104
📱 साइबर अपराध: 1930
👴 वरिष्ठ नागरिक: 14567

स्वास्थ्य आपातकाल:
- AIIMS दिल्ली: 011-26588500
- COVID हेल्पलाइन: 1075
- मानसिक स्वास्थ्य: 080-46110007""",
                "tags": ["आपातकाल", "नंबर", "पुलिस", "एम्बुलेंस"]
            },
            "health_tips": {
                "title": "स्वास्थ्य सुझाव",
                "content": """महत्वपूर्ण स्वास्थ्य सुझाव:

🌡️ बुखार:
- पानी पीते रहें
- पैरासिटामोल लें (500mg हर 6 घंटे)
- आराम करें
- डॉक्टर से सलाह लें

💊 दवाइयां:
- डॉक्टर की सलाह के बिना दवा न लें
- एक्सपायरी डेट जांचें
- पानी के साथ लें
- खाली पेट न लें (जब तक डॉक्टर न कहे)

🍎 पोषण:
- रोजाना 5 सब्जियां और 2 फल खाएं
- दूध पिएं
- जंक फूड से बचें
- पर्याप्त पानी पिएं (8-10 गिलास)

🏃 व्यायाम:
- रोजाना 30 मिनट व्यायाम करें
- टहलें या योग करें""",
                "tags": ["स्वास्थ्य", "बुखार", "दवाइयां", "पोषण"]
            },
        }

        # Bengali content
        self.content["bengali"] = {
            "fundamental_rights": {
                "title": "মৌলিক অধিকার",
                "content": """ভারতীয় সংবিধানের মৌলিক অধিকার (অনুচ্ছেদ ১২-৩৫):

১. সমতার অধিকার (অনুচ্ছেদ ১৪-১৮):
   - আইনের সম্মুখে সমতা
   - ধর্ম, জাতি, লিঙ্গের ভিত্তিতে বৈষম্য নিষিদ্ধ
   - সরকারি চাকরিতে সমান সুযোগ

২. স্বাধীনতার অধিকার (অনুচ্ছেদ ১৯-২২):
   - বাক্ স্বাধীনতা
   - সমাবেশের স্বাধীনতা
   - জীবন ও ব্যক্তিগত স্বাধীনতার রক্ষা

৩. শোষণের বিরুদ্ধে অধিকার (অনুচ্ছেদ ২৩-২৪)

৪. ধর্মীয় স্বাধীনতার অধিকার (অনুচ্ছেদ ২৫-২৮)

৫. সাংস্কৃতিক ও শিক্ষাগত অধিকার (অনুচ্ছেদ ২৯-৩০)

৬. সাংবিধানিক প্রতিকারের অধিকার (অনুচ্ছেদ ৩২)""",
                "tags": ["মৌলিক অধিকার", "সংবিধান", "অনুচ্ছেদ"]
            },
            "emergency_numbers": {
                "title": "জরুরি নম্বর",
                "content": """ভারতে জরুরি নম্বর:

🚨 পুলিশ: ১০০
🚒 অগ্নিনির্বাপক: ১০১
🚑 অ্যাম্বুলেন্স: ১০৮
👩 মহিলা হেল্পলাইন: ১৮১
👶 শিশু হেল্পলাইন: ১০৯৮
🆘 দুর্যোগ: ১১২
📱 সাইবার অপরাধ: ১৯৩০""",
                "tags": ["জরুরি", "নম্বর", "পুলিশ"]
            },
        }

        # Tamil content
        self.content["tamil"] = {
            "fundamental_rights": {
                "title": "அடிப்படை உரிமைகள்",
                "content": """இந்திய அரசியலமைப்பின் அடிப்படை உரிமைகள் (பிரிவு 12-35):

1. சமத்துவ உரிமை (பிரிவு 14-18):
   - சட்டத்தின் முன் சமத்துவம்
   - மதம், ஜாதி, பாலினம், இடம் ஆகியவற்றின் அடிப்படையில் பாகுபாடு தடை
   - அரசு வேலையில் சம வாய்ப்பு

2. சுதந்திர உரிமை (பிரிவு 19-22):
   - பேச்சு சுதந்திரம்
   - கூட்டம் கூடும் உரிமை
   - வாழ்க்கை மற்றும் தனிப்பட்ட சுதந்திரம்

3. சுரண்டலுக்கு எதிரான உரிமை (பிரிவு 23-24)

4. மத சுதந்திர உரிமை (பிரிவு 25-28)

5. கலாச்சார மற்றும் கல்வி உரிமை (பிரிவு 29-30)

6. அரசியலமைப்பு தீர்வு உரிமை (பிரிவு 32)""",
                "tags": ["அடிப்படை உரிமைகள்", "அரசியலமைப்பு", "பிரிவு"]
            },
            "emergency_numbers": {
                "title": "அவசர எண்கள்",
                "content": """இந்தியாவில் அவசர எண்கள்:

🚨 காவல்துறை: 100
🚒 தீயணைப்பு: 101
🚑 ஆம்புலன்ஸ்: 108
👩 பெண்கள் உதவி எண்: 181
👶 குழந்தை உதவி எண்: 1098
🆘 பேரிடர்: 112
📱 சைபர் குற்றம்: 1930""",
                "tags": ["அவசர", "எண்", "காவல்துறை"]
            },
        }

        # Common content in all languages
        self.content["common"] = {
            "government_schemes": {
                "title": "Government Schemes / सरकारी योजनाएं / সরকারি প্রকল্প / அரசு திட்டங்கள்",
                "content": """Key Government Schemes / मुख्य सरकारी योजनाएं:

1. PM-KISAN: ₹6,000/year for farmers
   किसानों के लिए ₹6,000/वर्ष
   pmkisan.gov.in

2. Ayushman Bharat: ₹5 lakh health cover
   ₹5 लाख स्वास्थ्य बीमा
   pmjay.gov.in

3. PM Ujjwala: Free LPG connection
   मुफ्त LPG कनेक्शन
   pmujjwala.gov.in

4. PMKVY: Free skill training
   मुफ्त कौशल प्रशिक्षण
   pmkvyofficial.org

5. MUDRA Loan: Up to ₹10 lakh
   ₹10 लाख तक ऋण
   mudra.org.in

6. Sukanya Samriddhi: Girl child savings
   बालिका बचत योजना

7. PM Awas: Housing for all
   सबके लिए आवास""",
                "tags": ["सरकारी योजना", "स्कीम", "government scheme"]
            },
            "digital_india": {
                "title": "Digital India / डिजिटल इंडिया",
                "content": """Digital India Services:

💳 UPI: Send money instantly
   तुरंत पैसे भेजें
   Format: name@bank

🆔 Aadhaar: Identity proof
   पहचान प्रमाण
   uidai.gov.in

📱 DigiLocker: Digital documents
   डिजिटल दस्तावेज
   digilocker.gov.in

🛒 ONDC: Shop from local sellers
   स्थानीय विक्रेताओं से खरीदारी

📄 e-Help: Government services
   सरकारी सेवाएं
   egov.gov.in""",
                "tags": ["डिजिटल इंडिया", "UPI", "आधार", "digital india"]
            },
        }

    def search(self, query: str, language: str = None, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Search the multilingual knowledge base.

        Args:
            query: Search query
            language: Specific language to search in (None for all)
            top_k: Number of results

        Returns:
            List of matching entries
        """
        query_lower = query.lower()
        results = []

        # Search in specified language or all languages
        languages = [language] if language and language in self.content else self.content.keys()

        for lang in languages:
            for key, entry in self.content[lang].items():
                score = 0
                title = entry.get("title", "").lower()
                content = entry.get("content", "").lower()
                tags = [t.lower() for t in entry.get("tags", [])]

                # Score calculation
                if query_lower in title:
                    score += 10
                for word in query_lower.split():
                    if word in title:
                        score += 5
                    if word in content:
                        score += 1
                    for tag in tags:
                        if word in tag:
                            score += 3

                if score > 0:
                    results.append({
                        "language": lang,
                        "key": key,
                        "title": entry.get("title", ""),
                        "content": entry.get("content", ""),
                        "tags": entry.get("tags", []),
                        "score": score,
                    })

        # Sort by score
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def get_available_languages(self) -> List[str]:
        """Get list of available languages."""
        return list(self.content.keys())

    def get_content(self, language: str, key: str) -> Optional[Dict[str, Any]]:
        """Get specific content by language and key."""
        if language in self.content and key in self.content[language]:
            return self.content[language][key]
        return None


# Singleton instance
_multilingual_kb = None


def get_multilingual_kb() -> MultilingualKnowledgeBase:
    """Get or create the multilingual knowledge base singleton."""
    global _multilingual_kb
    if _multilingual_kb is None:
        _multilingual_kb = MultilingualKnowledgeBase()
    return _multilingual_kb
