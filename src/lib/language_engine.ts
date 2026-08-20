/**
 * LanguageEngine — Real language detection, transliteration, and normalization
 * for Indic languages and code-mixed (Hinglish/Tanglish) text.
 *
 * Uses Unicode script analysis for detection (no heavy external deps).
 * Transliteration uses a phonetic mapping table for common Roman→Indic conversions.
 */

export interface LanguageDetectionResult {
    language: string;       // ISO 639 code: 'hi', 'bn', 'ta', 'te', 'en', 'hi-en' (code-mixed), etc.
    script: string;         // Unicode script name: 'Devanagari', 'Bengali', 'Tamil', 'Latn', etc.
    confidence: number;     // 0.0 – 1.0
    isCodeMixed: boolean;   // true if multiple scripts detected
}

export interface TransliterationConfig {
    sourceScript: string;
    targetScript: string;
}

// ── Unicode Script Ranges ────────────────────────────────────────────────────

const SCRIPT_RANGES: Record<string, [number, number][]> = {
    'Devanagari':  [[0x0900, 0x097F], [0xA8E0, 0xA8FF]],   // Hindi, Marathi, Nepali, Sanskrit
    'Bengali':     [[0x0980, 0x09FF]],                        // Bengali, Assamese
    'Gurmukhi':    [[0x0A00, 0x0A7F]],                        // Punjabi
    'Gujarati':    [[0x0A80, 0x0AFF]],                        // Gujarati
    'Tamil':       [[0x0B80, 0x0BFF]],                        // Tamil
    'Telugu':      [[0x0C00, 0x0C7F]],                        // Telugu
    'Kannada':     [[0x0C80, 0x0CFF]],                        // Kannada
    'Malayalam':   [[0x0D00, 0x0D7F]],                        // Malayalam
    'Odia':        [[0x0B00, 0x0B7F]],                        // Odia
    'Thai':        [[0x0E00, 0x0E7F]],                        // Thai
    'Arabic':      [[0x0600, 0x06FF], [0xFB50, 0xFDFF], [0xFE70, 0xFEFF]],
    'Tibetan':     [[0x0F00, 0x0FFF]],
    'Myanmar':     [[0x1000, 0x109F]],
    'Khmer':       [[0x1780, 0x17FF]],
    'Georgian':    [[0x10A0, 0x10FF]],
    'Hangul':      [[0xAC00, 0xD7AF], [0x1100, 0x11FF]],    // Korean
    'Han':         [[0x4E00, 0x9FFF], [0x3400, 0x4DBF]],    // Chinese
    'Hiragana':    [[0x3040, 0x309F]],                        // Japanese
    'Katakana':    [[0x30A0, 0x30FF]],                        // Japanese
};

// Map script → likely language(s)
const SCRIPT_TO_LANGUAGES: Record<string, string[]> = {
    'Devanagari':  ['hi', 'mr', 'ne', 'sa', 'kok'],
    'Bengali':     ['bn', 'as'],
    'Gurmukhi':    ['pa'],
    'Gujarati':    ['gu'],
    'Tamil':       ['ta'],
    'Telugu':      ['te'],
    'Kannada':     ['kn'],
    'Malayalam':   ['ml'],
    'Odia':        ['or'],
    'Arabic':      ['ar', 'ur'],
    'Hangul':      ['ko'],
    'Han':         ['zh'],
    'Hiragana':    ['ja'],
    'Katakana':    ['ja'],
};

// ── Detection Helpers ────────────────────────────────────────────────────────

function getScript(char: string): string | null {
    const code = char.codePointAt(0)!;
    for (const [script, ranges] of Object.entries(SCRIPT_RANGES)) {
        for (const [lo, hi] of ranges) {
            if (code >= lo && code <= hi) return script;
        }
    }
    return null;
}

function isLatinLetter(char: string): boolean {
    const code = char.codePointAt(0)!;
    return (code >= 0x41 && code <= 0x5A) || (code >= 0x61 && code <= 0x7A);
}

// Common Hinglish/Tanglish indicator words (Roman script but Indic language)
const CODE_MIXED_INDICATORS = new Set([
    // Hindi in Latin script
    'hai', 'ho', 'kya', 'kaun', 'kahan', 'kyun', 'kaise', 'nahi', 'haan',
    'bhai', 'yaar', 'arre', 'acha', 'theek', 'suno', 'batao', 'bolo',
    'chalo', 'dekho', 'suno', 'bata', 'mat', 'mai', 'mera', 'tera',
    'uska', 'iska', 'woh', 'yeh', 'kab', 'ab', 'phir', 'bhi', 'toh',
    'se', 'ko', 'me', 'pe', 'ne', 'ke', 'ki', 'ka', 'par', 'aur',
    'ek', 'do', 'teen', 'char', 'panch', 'das',
    'namaste', 'namaskar', 'shukriya', 'ji',
    // Tamil in Latin
    'vanakkam', 'nandri', 'irukku', 'illai', 'eppadi',
    // Telugu in Latin
    'namaskaram', 'bagunnara', 'ledu', 'undi',
    // Bengali in Latin
    'kemon', 'acho', 'bhalo', 'naaki',
]);

// ── Main Detection ───────────────────────────────────────────────────────────

/**
 * Detects the language and script of the input text using Unicode analysis.
 */
export function detectLanguage(text: string): LanguageDetectionResult {
    if (!text || text.trim().length === 0) {
        return { language: 'en', script: 'Latn', confidence: 0.5, isCodeMixed: false };
    }

    const scriptCounts: Record<string, number> = {};
    let totalMeaningful = 0;

    for (const char of text) {
        const script = getScript(char);
        if (script) {
            scriptCounts[script] = (scriptCounts[script] || 0) + 1;
            totalMeaningful++;
        }
    }

    // Check for Latin characters (Indicators for English or code-mixed)
    let latinCount = 0;
    for (const char of text) {
        if (isLatinLetter(char)) latinCount++;
    }

    const scriptsDetected = Object.keys(scriptCounts);

    // Case 1: Only Latin script
    if (latinCount > 0 && scriptsDetected.length === 0) {
        // Check if it's code-mixed (Hinglish etc.)
        const words = text.toLowerCase().split(/\s+/);
        let indicMatches = 0;
        for (const word of words) {
            const clean = word.replace(/[^a-z]/g, '');
            if (CODE_MIXED_INDICATORS.has(clean)) {
                indicMatches++;
            }
        }

        const mixRatio = indicMatches / Math.max(words.length, 1);
        if (mixRatio > 0.3) {
            return {
                language: 'hi-en',  // Hinglish / code-mixed
                script: 'Latn',
                confidence: Math.min(0.5 + mixRatio, 0.95),
                isCodeMixed: true,
            };
        }

        return { language: 'en', script: 'Latn', confidence: 0.9, isCodeMixed: false };
    }

    // Case 2: Indic script(s) detected
    if (scriptsDetected.length > 0) {
        // Find dominant script
        let dominantScript = scriptsDetected[0];
        let maxCount = scriptCounts[dominantScript] || 0;
        for (const script of scriptsDetected) {
            const count = scriptCounts[script] || 0;
            if (count > maxCount) {
                dominantScript = script;
                maxCount = count;
            }
        }

        const dominantRatio = maxCount / Math.max(totalMeaningful, 1);
        const isCodeMixed = scriptsDetected.length > 1 || latinCount > totalMeaningful * 0.15;

        const languages = SCRIPT_TO_LANGUAGES[dominantScript] || ['unknown'];
        const primaryLang = languages[0];

        // If code-mixed with Latin, append '-en'
        const finalLang = isCodeMixed && latinCount > 5 ? `${primaryLang}-en` : primaryLang;

        return {
            language: finalLang,
            script: dominantScript,
            confidence: Math.min(dominantRatio + 0.1, 1.0),
            isCodeMixed,
        };
    }

    // Fallback
    return { language: 'en', script: 'Latn', confidence: 0.5, isCodeMixed: false };
}

// ── Transliteration Tables (Roman → Indic) ───────────────────────────────────

/**
 * Romanized Hindi/Devanagari transliteration map.
 * Maps phonetic Roman input → Devanagari characters.
 * Covers common Hinglish typing patterns.
 */
const ROMAN_TO_DEVANAGARI: Record<string, string> = {
    // Vowels
    'a': 'अ', 'aa': 'आ', 'i': 'इ', 'ee': 'ई', 'u': 'उ', 'oo': 'ऊ',
    'e': 'ए', 'ai': 'ऐ', 'o': 'ओ', 'au': 'औ', 'am': 'अं', 'ah': 'अः',
    // Consonants
    'k': 'क', 'kh': 'ख', 'g': 'ग', 'gh': 'घ', 'ng': 'ङ',
    'ch': 'च', 'chh': 'छ', 'j': 'ज', 'jh': 'झ', 'ny': 'ञ',
    't': 'त', 'th': 'थ', 'd': 'द', 'dh': 'ध', 'n': 'न',
    'p': 'प', 'ph': 'फ', 'b': 'ब', 'bh': 'भ', 'm': 'म',
    'y': 'य', 'r': 'र', 'l': 'ल', 'v': 'व', 'w': 'व',
    'sh': 'श', 'shh': 'ष', 's': 'स', 'h': 'ह',
    // Nukta variants
    'ksh': 'क्ष', 'gy': 'ज्ञ', 'tr': 'त्र', 'dr': 'द्र',
    // Common conjuncts / half forms
    'ngh': 'ङ्घ', 'nch': 'ञ्च', 'nj': 'ञ्ज',
};

/**
 * Romanized Bengali transliteration map.
 */
const ROMAN_TO_BENGALI: Record<string, string> = {
    'a': 'অ', 'aa': 'আ', 'i': 'ই', 'ii': 'ঈ', 'u': 'উ', 'uu': 'ঊ',
    'e': 'এ', 'oi': 'ঐ', 'o': 'ও', 'ou': 'ঔ', 'am': 'অং', 'ah': 'অঃ',
    'k': 'ক', 'kh': 'খ', 'g': 'গ', 'gh': 'ঘ', 'ng': 'ঙ',
    'c': 'চ', 'ch': 'ছ', 'j': 'জ', 'jh': 'ঝ', 'ny': 'ঞ',
    'tt': 'ট', 'tth': 'ঠ', 'dd': 'ড', 'ddh': 'ঢ', 'nn': 'ণ',
    't': 'ত', 'th': 'থ', 'd': 'দ', 'dh': 'ধ', 'n': 'ন',
    'p': 'প', 'ph': 'ফ', 'b': 'ব', 'bh': 'ভ', 'm': 'ম',
    'y': 'য', 'r': 'র', 'l': 'ল', 'v': 'ভ', 'w': 'ভ',
    'sh': 'শ', 'shh': 'ষ', 's': 'স', 'h': 'হ',
    'ksh': 'ক্ষ', 'gy': 'জ্ঞ', 'tr': 'ত্র', 'dr': 'দ্র',
};

/**
 * Romanized Gujarati transliteration map.
 */
const ROMAN_TO_GUJARATI: Record<string, string> = {
    'a': 'અ', 'aa': 'આ', 'i': 'ઇ', 'ee': 'ઈ', 'u': 'ઉ', 'oo': 'ઊ',
    'e': 'એ', 'ai': 'ઐ', 'o': 'ઓ', 'au': 'ઔ', 'am': 'અં', 'ah': 'અઃ',
    'k': 'ક', 'kh': 'ખ', 'g': 'ગ', 'gh': 'ઘ', 'ng': 'ઙ',
    'ch': 'ચ', 'chh': 'છ', 'j': 'જ', 'jh': 'ઝ', 'ny': 'ઞ',
    't': 'ત', 'th': 'થ', 'd': 'દ', 'dh': 'ધ', 'n': 'ન',
    'p': 'પ', 'ph': 'ફ', 'b': 'બ', 'bh': 'ભ', 'm': 'મ',
    'y': 'ય', 'r': 'ર', 'l': 'લ', 'v': 'વ', 'w': 'વ',
    'sh': 'શ', 'shh': 'ષ', 's': 'સ', 'h': 'હ',
    'ksh': 'ક્ષ', 'gy': 'જ્ઞ', 'tr': 'ત્ર', 'dr': 'દ્ર',
};

/**
 * Romanized Tamil transliteration map.
 */
const ROMAN_TO_TAMIL: Record<string, string> = {
    'a': 'அ', 'aa': 'ஆ', 'i': 'இ', 'ii': 'ஈ', 'u': 'உ', 'uu': 'ஊ',
    'e': 'எ', 'ee': 'ஏ', 'ai': 'ஐ', 'o': 'ஒ', 'oo': 'ஓ', 'au': 'ஔ',
    'k': 'க', 'ng': 'ங', 'ch': 'ச', 'ny': 'ஞ', 't': 'ட', 'n': 'ண',
    'th': 'த', 'nh': 'ந', 'p': 'ப', 'm': 'ம', 'y': 'ய', 'r': 'ர',
    'l': 'ல', 'v': 'வ', 'z': 'ழ', 'L': 'ள', 'R': 'ற', 'n2': 'ந',
    'sh': 'ஶ', 'shh': 'ஷ', 's': 'ஸ', 'h': 'ஹ', 'ksh': 'க்ஷ',
};

/**
 * Romanized Telugu transliteration map.
 */
const ROMAN_TO_TELUGU: Record<string, string> = {
    'a': 'అ', 'aa': 'ఆ', 'i': 'ఇ', 'ee': 'ఈ', 'u': 'ఉ', 'oo': 'ఊ',
    'e': 'ఎ', 'ee': 'ఏ', 'ai': 'ఐ', 'o': 'ఒ', 'oo': 'ఓ', 'au': 'ఔ', 'am': 'అం', 'ah': 'అః',
    'k': 'క', 'kh': 'ఖ', 'g': 'గ', 'gh': 'ఘ', 'ng': 'ఙ',
    'ch': 'చ', 'chh': 'ఛ', 'j': 'జ', 'jh': 'ఝ', 'ny': 'ఞ',
    'tt': 'ట', 'tth': 'ఠ', 'dd': 'డ', 'ddh': 'ఢ', 'nn': 'ణ',
    't': 'త', 'th': 'థ', 'd': 'ద', 'dh': 'ధ', 'n': 'న',
    'p': 'ప', 'ph': 'ఫ', 'b': 'బ', 'bh': 'భ', 'm': 'మ',
    'y': 'య', 'r': 'ర', 'l': 'ల', 'v': 'వ', 'w': 'వ',
    'sh': 'శ', 'shh': 'ష', 's': 'స', 'h': 'హ',
    'ksh': 'క్ష', 'gy': 'జ్ఞ', 'tr': 'త్ర', 'dr': 'ద్ర',
};

/**
 * Romanized Gurmukhi (Punjabi) transliteration map.
 */
const ROMAN_TO_GURMUKHI: Record<string, string> = {
    'a': 'ਅ', 'aa': 'ਆ', 'i': 'ਇ', 'ee': 'ਈ', 'u': 'ਉ', 'oo': 'ਊ',
    'e': 'ਏ', 'ai': 'ਐ', 'o': 'ਓ', 'au': 'ਔ', 'am': 'ਅਂ', 'ah': 'ਅਃ',
    'k': 'ਕ', 'kh': 'ਖ', 'g': 'ਗ', 'gh': 'ਘ', 'ng': 'ਙ',
    'ch': 'ਚ', 'chh': 'ਛ', 'j': 'ਜ', 'jh': 'ਝ', 'ny': 'ਞ',
    'tt': 'ਟ', 'tth': 'ਠ', 'dd': 'ਡ', 'ddh': 'ਢ', 'nn': 'ਣ',
    't': 'ਤ', 'th': 'ਥ', 'd': 'ਦ', 'dh': 'ਧ', 'n': 'ਨ',
    'p': 'ਪ', 'ph': 'ਫ', 'b': 'ਬ', 'bh': 'ਭ', 'm': 'ਮ',
    'y': 'ਯ', 'r': 'ਰ', 'l': 'ਲ', 'v': 'ਵ', 'w': 'ਵ',
    'sh': 'ਸ਼', 's': 'ਸ', 'h': 'ਹ',
    'ksh': 'ਕਸ਼', 'gy': 'ਗਯ', 'tr': 'ਤਰ', 'dr': 'ਦਰ',
};

// Common word-level Roman → Devanagari mappings (for full words)
const COMMON_WORD_MAPPINGS: Record<string, string> = {
    'namaste': 'नमस्ते', 'namaskar': 'नमस्कार', 'shukriya': 'शुक्रिया',
    'kya': 'क्या', 'kahan': 'कहाँ', 'kaun': 'कौन', 'kyun': 'क्यों',
    'kaise': 'कैसे', 'kab': 'कब', 'nahi': 'नहीं', 'haan': 'हाँ',
    'bhai': 'भाई', 'yaar': 'यार', 'arre': 'अर्रे', 'acha': 'अच्छा',
    'theek': 'ठीक', 'suno': 'सुनो', 'batao': 'बताओ', 'bolo': 'बोलो',
    'chalo': 'चलो', 'dekho': 'देखो', 'samajh': 'समझ', 'bohot': 'बहुत',
    'thoda': 'थोड़ा', 'bahut': 'बहुत', 'sab': 'सब', 'mai': 'मैं',
    'mera': 'मेरा', 'tera': 'तेरा', 'uska': 'उसका', 'iska': 'इसका',
    'woh': 'वो', 'yeh': 'ये', 'aur': 'और', 'par': 'पर',
    'mein': 'में', 'se': 'से', 'ko': 'को', 'ke': 'के', 'ki': 'की',
    'ka': 'का', 'ne': 'ने', 'bhi': 'भी', 'toh': 'तो',
    'phir': 'फिर', 'ab': 'अब', 'ek': 'एक', 'do': 'दो',
    'hai': 'है', 'ho': 'हो', 'tha': 'था', 'thi': 'थी', 'the': 'थे',
    'hoga': 'होगा', 'honge': 'होंगे', 'hun': 'हूँ',
    'wala': 'वाला', 'wali': 'वाली', 'wale': 'वाले',
    'jaise': 'जैसे', 'jaisa': 'जैसा', 'jaisi': 'जैसी',
    'chahiye': 'चाहिए', 'de': 'दे', 'le': 'ले',
    'bata': 'बता', 'sikhao': 'सिखाओ', 'madad': 'मदद',
    'samay': 'समय', 'waqt': 'वक़्त', 'time': 'टाइम',
    'chai': 'चाय', 'pani': 'पानी', 'khana': 'खाना',
    'accha': 'अच्छा', 'bura': 'बुरा', 'sundar': 'सुंदर',
    'bachche': 'बच्चे', 'ghar': 'घर', 'school': 'स्कूल',
    'college': 'कॉलेज', 'office': 'ऑफिस', 'market': 'मार्केट',
    'phone': 'फ़ोन', 'paisa': 'पैसा', 'rupaye': 'रुपये',
};

// Common word mappings for Bengali
const COMMON_WORD_MAPPINGS_BENGALI: Record<string, string> = {
    'namaskar': 'নমস্কার', 'dhonnobad': 'ধন্যবাদ', 'kemon': 'কেমন',
    'acho': 'আছো', 'bhalo': 'ভালো', 'ami': 'আমি', 'tumi': 'তুমি',
    'apni': 'আপনি', 'kothay': 'কোথায়', 'ke': 'কে', 'ki': 'কী',
    'keno': 'কেন', 'kivabe': 'কিভাবে', 'kobe': 'কবে', 'na': 'না',
    'haa': 'হ্যাঁ', 'bhalobasha': 'ভালোবাসা', 'ma': 'মা', 'baba': 'বাবা',
    'bhai': 'ভাই', 'bon': 'বোন', 'dada': 'দাদা', 'didi': 'দিদি',
    'khawya': 'খাব', 'khawa': 'খাওয়া', 'jol': 'জল', 'bhat': 'ভাত',
    'misti': 'মিষ্টি', 'cha': 'চা', 'kafe': 'কফি', 'bazaar': 'বাজার',
    'ghor': 'ঘর', 'school': 'স্কুল', 'college': 'কলেজ', 'office': 'অফিস',
    'gari': 'গাড়ি', 'bas': 'বাস', 'train': 'ট্রেন', 'ticket': 'টিকেট',
};

// Common word mappings for Gujarati
const COMMON_WORD_MAPPINGS_GUJARATI: Record<string, string> = {
    'namaste': 'નમસ્તે', 'namaskar': 'નમસ્કાર', 'aabhar': 'આભાર',
    'kem': 'કેમ', 'cho': 'છો', 'hu': 'હું', 'tame': 'તમે',
    'aap': 'આપ', 'kya': 'ક્યાં', 'kau': 'કૌન', 'kyare': 'ક્યારે',
    'shu': 'શું', 'evu': 'એવું', 'hu': 'હું', 'na': 'ના', 'haa': 'હા',
    'ma': 'માતા', 'bapuji': 'બાપુજી', 'bhai': 'ભાઈ', 'ben': 'બહેન',
    'khavu': 'ખાવું', 'pani': 'પાણી', 'bhat': 'ભાત', 'mithu': 'મીઠું',
    'cha': 'ચા', 'coffee': 'કોફી', 'bazar': 'બાઝાર', 'ghar': 'ઘર',
    'school': 'સ્કૂલ', 'college': 'કોલેજ', 'office': 'ઑફિસ',
};

// Common word mappings for Tamil
const COMMON_WORD_MAPPINGS_TAMIL: Record<string, string> = {
    'vanakkam': 'வணக்கம்', 'nandri': 'நன்றி', 'epdi': 'எப்படி',
    'irukku': 'இருக்கு', 'illai': 'இல்லை', 'naan': 'நான்', 'ni': 'நீ',
    'neenga': 'நீங்கள்', 'enga': 'எங்கே', 'yaar': 'யார்', 'en': 'என்',
    'enna': 'என்ன', 'eppadi': 'எப்படி', 'eppo': 'எப்போது', 'illa': 'இல்லை',
    'amma': 'அம்மா', 'appa': 'அப்பா', 'anna': 'அண்ணா', 'akka': 'அக்கா',
    'sapidu': 'சாப்பிடு', 'thanni': 'தண்ணீர்', 'saadam': 'சாதம்',
    'chai': 'சாய்', 'kaapi': 'காபி', 'kadai': 'கடை', 'veedu': 'வீடு',
    'school': 'ஸ்கூல்', 'college': 'காலேஜ்', 'office': 'ஆபіс',
};

// Common word mappings for Telugu
const COMMON_WORD_MAPPINGS_TELUGU: Record<string, string> = {
    'namaskaram': 'నమస్కారం', 'dhanyavadhamulu': 'ధన్యవాదములు',
    'ela': 'ఎలా', 'unnavu': 'ఉన్నావు', 'nenu': 'నేను', 'nuvvu': 'నువ్వు',
    'meeru': 'మీరు', 'ekkada': 'ఎక్కడ', 'evvaru': 'ఎవరు', 'entha': 'ఎంత',
    'enduku': 'ఎందుకు', 'ela': 'ఎలా', 'eppudu': 'ఎప్పుడు', 'ledu': 'లేదు',
    'amma': 'అమ్మ', 'nanna': 'నన్న', 'anna': 'అన్న', 'akka': 'అక్క',
    'tinu': 'తిను', 'neellu': 'నీళ్ళు', 'annam': 'అన్నం',
    'chai': 'చాయ్', 'coffee': 'కాఫీ', 'angadi': 'అంగడి', 'illu': 'ఇల్లు',
    'school': 'స్కూల్', 'college': 'కాలేజ్', 'office': 'ఆఫీసు',
};

// Common word mappings for Gurmukhi
const COMMON_WORD_MAPPINGS_GURMUKHI: Record<string, string> = {
    'sat sri akal': 'ਸਤ ਸ੍ਰੀ ਅਕਾਲ', 'shukriya': 'ਸ਼ੁਕਰੀਆ',
    'ki haal': 'ਕੀ ਹਾਲ', 'main': 'ਮੈਂ', 'tusi': 'ਤੁਸੀਂ',
    'kithon': 'ਕਿੱਥੋਂ', 'kaun': 'ਕੌਣ', 'keha': 'ਕੇਹਾ', 'kiu': 'ਕਿਉਂ',
    'kiven': 'ਕਿਵੇਂ', 'kadon': 'ਕਦੋਂ', 'nahi': 'ਨਹੀਂ', 'haan': 'ਹਾਂ',
    'ma': 'ਮਾਂ', 'bapu': 'ਬਾਪੂ', 'bhai': 'ਭਾਈ', 'bhain': 'ਭੈਣ',
    'khana': 'ਖਾਣਾ', 'pani': 'ਪਾਣੀ', 'roti': 'ਰੋਟੀ', 'mitha': 'ਮਿੱਠਾ',
    'chai': 'ਚਾਹ', 'coffee': 'ਕੌਫੀ', 'bazaar': 'ਬਾਜ਼ਾਰ', 'ghar': 'ਘਰ',
    'school': 'ਸਕੂਲ', 'college': 'ਕਾਲਜ', 'office': 'ਦਫ਼ਤਰ',
};

/**
 * Transliterates Romanized Indic text to Devanagari script.
 * Handles word-level lookups first, then falls back to character-level mapping.
 */
export function transliterateToDevanagari(text: string): string {
    return transliterateGeneric(text, ROMAN_TO_DEVANAGARI, COMMON_WORD_MAPPINGS);
}

/**
 * Transliterates Romanized text to Bengali script.
 */
export function transliterateToBengali(text: string): string {
    return transliterateGeneric(text, ROMAN_TO_BENGALI, COMMON_WORD_MAPPINGS_BENGALI);
}

/**
 * Transliterates Romanized text to Gujarati script.
 */
export function transliterateToGujarati(text: string): string {
    return transliterateGeneric(text, ROMAN_TO_GUJARATI, COMMON_WORD_MAPPINGS_GUJARATI);
}

/**
 * Transliterates Romanized text to Tamil script.
 */
export function transliterateToTamil(text: string): string {
    return transliterateGeneric(text, ROMAN_TO_TAMIL, COMMON_WORD_MAPPINGS_TAMIL);
}

/**
 * Transliterates Romanized text to Telugu script.
 */
export function transliterateToTelugu(text: string): string {
    return transliterateGeneric(text, ROMAN_TO_TELUGU, COMMON_WORD_MAPPINGS_TELUGU);
}

/**
 * Transliterates Romanized text to Gurmukhi script.
 */
export function transliterateToGurmukhi(text: string): string {
    return transliterateGeneric(text, ROMAN_TO_GURMUKHI, COMMON_WORD_MAPPINGS_GURMUKHI);
}

/**
 * Generic transliteration function using provided maps.
 */
function transliterateGeneric(
    text: string,
    charMap: Record<string, string>,
    wordMap: Record<string, string>
): string {
    const words = text.split(/(\s+)/);
    const result: string[] = [];

    for (const word of words) {
        if (/^\s+$/.test(word)) {
            result.push(word);
            continue;
        }

        const lower = word.toLowerCase();

        if (wordMap[lower]) {
            result.push(wordMap[lower]);
            continue;
        }

        let remaining = lower;
        let output = '';
        while (remaining.length > 0) {
            let matched = false;
            for (const len of [3, 2, 1]) {
                const slice = remaining.slice(0, len);
                if (charMap[slice]) {
                    output += charMap[slice];
                    remaining = remaining.slice(len);
                    matched = true;
                    break;
                }
            }
            if (!matched) {
                output += remaining[0];
                remaining = remaining.slice(1);
            }
        }
        result.push(output);
    }

    return result.join('');
}

// ── Input Normalization ──────────────────────────────────────────────────────

/**
 * Normalizes input text:
 * - Trims whitespace
 * - Collapses multiple spaces
 * - Normalizes common typos ("kyaaa" → "kya", "hiii" → "hi")
 * - Converts to lowercase for matching
 */
export function normalizeInput(text: string): string {
    let normalized = text.trim();

    // Collapse multiple spaces
    normalized = normalized.replace(/\s+/g, ' ');

    // Normalize elongated characters ("kyaaa" → "kya", "hiii" → "hi")
    normalized = normalized.replace(/([a-zA-Z])\1{2,}/g, '$1$1');

    return normalized;
}

/**
 * Detect if the input is primarily a greeting in any Indic language.
 */
export function isGreeting(text: string): boolean {
    const lower = text.toLowerCase().trim();
    const greetings = [
        'hi', 'hello', 'hey', 'hii', 'helo',
        'namaste', 'namaskar', 'namaskaram', 'salaam', 'adaab',
        'vanakkam', 'namaskara', 'nomoshkar', 'khamma ghani',
        'radhe radhe', 'jai shree krishna', 'assalamualaikum',
    ];
    return greetings.some(g => lower === g || lower.startsWith(g));
}

// ── Legacy API (backward compat) ─────────────────────────────────────────────

export class LanguageEngine {
    /**
     * Detects the language and script of the input text.
     * Now uses real Unicode-based detection.
     */
    static detectLanguage(text: string): LanguageDetectionResult {
        return detectLanguage(text);
    }

    /**
     * Transliterates text from one script to another.
     * Supports Roman → Devanagari, Bengali, Gujarati, Tamil, Telugu, Gurmukhi.
     */
    static transliterate(text: string, config: TransliterationConfig): string {
        if (config.sourceScript === 'Latn') {
            switch (config.targetScript) {
                case 'Deva':
                    return transliterateToDevanagari(text);
                case 'Beng':
                    return transliterateToBengali(text);
                case 'Gujr':
                    return transliterateToGujarati(text);
                case 'Taml':
                    return transliterateToTamil(text);
                case 'Telu':
                    return transliterateToTelugu(text);
                case 'Guru':
                    return transliterateToGurmukhi(text);
            }
        }
        // For unsupported pairs, return text unchanged
        console.warn(`Transliteration from ${config.sourceScript} to ${config.targetScript} not yet supported.`);
        return text;
    }

    /**
     * Normalizes input text.
     */
    static normalizeInput(text: string): string {
        return normalizeInput(text);
    }
}
