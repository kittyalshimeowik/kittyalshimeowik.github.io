# scrapers/utilities/housing_parser.py

import re
from scrapers.utilities.location_data import LOCATION_DICTIONARY_REGEX

# --- Patterns ---
PHONE_NUMBER_PATTERN = re.compile(
    r'(?:'
    r'\+\d{1,3}[\s\./\-\u2010-\u2015\u2212\u00ad]*\(?\d{1,4}\)?[\s\./\-\u2010-\u2015\u2212\u00ad]*\d{2,4}[\s\./\-\u2010-\u2015\u2212\u00ad]*\d{2,4}[\s\./\-\u2010-\u2015\u2212\u00ad]*\d{2,4}'
    r'|'
    r'(?:\+?374[\s\./\-\u2010-\u2015\u2212\u00ad֊]*|0)(?:10|11|12|33|41|43|44|55|77|91|93|94|95|96|97|98|99)'
    r'(?:[\s\./\-\u2010-\u2015\u2212\u00ad֊]*\(?(?:0|\+?374)?(?:10|11|12|33|41|43|44|55|77|91|93|94|95|96|97|98|99)\)?)?'
    r'(?:[\s\./\-\u2010-\u2015\u2212\u00ad֊]*\d){6}\b'
    r')'
)

# Area / Size patterns
# Excluded bare 'մետր' / 'метр' so linear distances (e.g. 150 մետր հեռավորության վրա) are never captured as sizes
SIZE_PATTERN = re.compile(
    r'(?:(?P<size1>[1-9]\d{0,2}(?:[.,\s]\d{3})+|\d{1,5}(?:[.,]\d+)+|\d{1,5})\s*[-֊:.]*\s*(?:քմ|ք\.մ\.|ք․մ․|ք\.\s*մ|քառակուսի\s+մետր|քառ\.\s*(?:մ\.|մետր)|sq\s*m|sq\.m\.|sqm|m2|m²|ք/մ|qm|q\.m\.|м²|кв\.?\s*м\.?|մ²|մ2|մ\.))'
    r'|'
    r'(?:(?:քմ|ք\.մ\.|ք․մ․|ք\.\s*մ|քառակուսի\s+մետր|քառ\.\s*(?:մ\.|մետր)|sq\s*m|sq\.m\.|sqm|m2|m²|ք/մ|qm|q\.m\.|м²|кв\.?\s*м\.?|մ²|մ2|մ\.)\s*[-֊:.]*\s*(?P<size2>[1-9]\d{0,2}(?:[.,\s]\d{3})+|\d{1,5}(?:[.,]\d+)+|\d{1,5}))'
    r'|'
    r'(?:\b(?P<size3>[1-9]\d{1,3})\s*²\b)',
    re.IGNORECASE
)

SOT_PATTERN = re.compile(
    r'\b(?P<sot>[1-9]\d{0,3}(?:[.,]\d+)?)\s*[-֊:]*\s*(?:սոտ|սոտկա|սոտեկ|սոտկի|сотка|сотки|соток|sot)\b',
    re.IGNORECASE
)

HA_PATTERN = re.compile(
    r'\b(?P<ha>[1-9]\d{0,3}(?:[.,]\d+)?)\s*[-֊:]*\s*(?:հա|հեկտար|гектар|га|ha|hectare)\b',
    re.IGNORECASE
)

RATE_PER_SQM_HEADER_PATTERN = re.compile(
    r'\b1\s*(?:քմ|ք/մ|ք\.մ|մ2|sqm|sq\s*m|м²|кв\.?\s*м\.?)\s*(?:[-֊:]|\s)*(?:արժեքը?|գինը?|цена|price|արժե)',
    re.IGNORECASE
)

# Room count patterns
ROOM_PATTERN = re.compile(
    r'(?:(?P<rooms1>\d{1,2})\s*[-֊:]*\s*(?:սենյակ\w*|սեն\.|room|rooms|bed|bd|bedrooms|ննջասենյակ\w*|ննջարան\w*|комн(?:\.|аты|ատ|а)?|спальн\w*))'
    r'|'
    r'(?:(?:սենյակ\w*|սեն\.|room|rooms|bed|bd|bedrooms|ննջասենյակ\w*|ննջարան\w*|комн(?:\.|аты|ատ|а)?|спальн\w*)\s*[-֊:]*\s*(?P<rooms2>\d{1,2}))',
    re.IGNORECASE
)

CONVERTED_ROOMS_PATTERN = re.compile(
    r'\b(?P<r1>[1-9])\s*[-֊]\s*(?P<r2>[1-9])\s*սենյակ\w*',
    re.IGNORECASE
)

TRANSFORMED_ROOMS_PATTERN = re.compile(
    r'\b(?P<r1>[1-9])\s*(?:-?րդ\s+)?սենյակ\w*\s*(?:ձևափոխված|դարձրած|դարձած|վերափոխված|переделанная\s+в)\s*(?P<r2>[1-9])',
    re.IGNORECASE
)

WORD_ROOMS_PATTERN = re.compile(
    r'\b(?P<word>մեկ|երկու|երեք|չորս|հինգ)\s+սենյակ\w*',
    re.IGNORECASE
)

WORD_TO_NUM = {"մեկ": 1, "երկու": 2, "երեք": 3, "չորս": 4, "հինգ": 5}
STUDIO_PATTERN = re.compile(r'\b(?:ստուդիա|ստուդիո|studio|студия)\b', re.IGNORECASE)
LISTAM_ROOMS_PATTERN = re.compile(r'\b(?P<r>\d{1,2})\+?\s+Սենյակների\s+քանակ', re.IGNORECASE)

CURRENCY_SYMBOLS_REGEX = (
    r'\$|֏|€|₽|'
    r'USD|AMD|EUR|RUB|'
    r'dram(?:i|ov)?|amd|dollar(?:s)?|'
    r'հհ\s*դրամ|հհ\s*դր\.?|ամն\s*դոլար(?:ով)?|'
    r'դրամ(?:ի|ով)?|դր\.?|դ\b|'
    r'դոլար(?:ի|ով)?|տոլար(?:ի|ով)?|'
    r'амд|драм(?:а|ов)?|доллар(?:а|ов)?|у\.е\.?|ye|'
    r'руб(?:лей|ля)?'
)

PRICE_CURRENCY_PATTERN = re.compile(
    r'(?:գինը[\s:`՝]*|price[\s:`՝]*|արժեքը[\s:`՝]*)?'
    r'(?P<pre_curr>' + CURRENCY_SYMBOLS_REGEX + r')?\s*'
    r'(?<![\d.])(?P<amount>[1-9]\d{0,2}(?:[,\s\.․\u0589\u2024]\d{3})+(?!\d)|[1-9]\d{1,8})(?![\d.])\s*'
    r'(?P<post_curr>' + CURRENCY_SYMBOLS_REGEX + r')?',
    re.IGNORECASE
)

PER_SQM_PRICE_PATTERN = re.compile(
    r'(?:1\s*(?:քմ|ք/մ|ք\.մ|մ2|sqm|sq\s*m|кв\.?\s*м\.?)\s*[-֊:]?\s*(?P<p1>\$?\d[\d,\s.]*\$?)|'
    r'(?P<p2>\$?\d[\d,\s.]*\$?)\s*[-֊/]\s*(?:1\s*)?(?:քմ|ք/մ|ք\.մ|մ2|sqm|sq\s*m|кв\.?\s*м\.?)|'
    r'(?:արժեքը|գինը|цена)\s*1\s*(?:քմ|ք/մ|ք\.մ|մ2|sqm)\s*[-֊:]?\s*(?P<p3>\$?\d[\d,\s.]*\$?))',
    re.IGNORECASE
)

INVESTMENT_RENTAL_PATTERN = re.compile(
    r'\b(?:'
    r'հարմար\s+է(?:\s+շատ)?\s+(?:օրավարձով|վարձով)(?:\s+հանձնելու|\s+տալու)?(?:\s+համար)?|'
    r'օրավարձով\s+(?:հանձնելու|տալու)(?:\s+համար)?|'
    r'վարձով\s+(?:հանձնելու|տալու)(?:\s+համար)?|'
    r'կարող\s+եք\s+(?:տրվել\s+|տալ\s+)?(?:վարձով|օրավարձով)|'
    r'karox\s+eq\s+vardzov(?:\s+tal)?|'
    r'vardzov\s+talu(?:\s+hamar)?|'
    r'harmar\s+e\s+(?:shat\s+)?(?:vardzov|oravardzov)|'
    r'под\s+сдачу(?:\s+в\s+аренду)?|'
    r'для\s+сдачи(?:\s+в\s+аренду)?|'
    r'сдавать\s+в\s+аренду|'
    r'купи\s+и\s+сдавай(?:\s+в\s+аренду)?'
    r')\b',
    re.IGNORECASE
)

FLOOR_PATTERN = re.compile(
    r'\b(?P<floor>\d{1,2})\s*/\s*(?P<total_floors>\d{1,2})\b',
    re.IGNORECASE
)

DIMENSION_PATTERN = re.compile(r'\d+(?:[.,]\d+)?\s*(?:մ|մետր|կմ|սմ|м|метр|км|см)\b', re.IGNORECASE)
COUNT_ITEM_PATTERN = re.compile(r'\d+\s*(?:հարկ|հարկանի|տարի|սենյակ|բնակարան|этаж|комната|квартира)\b', re.IGNORECASE)
TREE_COUNT_PATTERN = re.compile(r'\b\d+\s+(?:[\wԱ-Ֆա-ֆА-Яа-я]+[\s\-]+){0,4}(?:ծառ|ծառեր|տնկի|տնկիներ|дерево|деревьев)\b', re.IGNORECASE)
PROPERTY_CODE_PATTERN = re.compile(r'(?:[A-Z]{1,4}\d*[_\\-]*)?(?:կոդ|id|լոտ|համար|код)[\s\./\-—–_,:;՝’\']*\d{3,7}\b|\b[A-Z]{2,4}\d+[_\\-]\d+\b', re.IGNORECASE)
PERCENT_PATTERN = re.compile(r'\d+(?:[.,]\d+)?\s*%', re.IGNORECASE)
COORDINATES_PATTERN = re.compile(r'\b\d{1,3}\.\d{4,8}\b')

EXCLUDED_CONTEXT_PATTERN = re.compile(
    r'\b(?:shopping|business|trade|commercial|fitness|medical|tech|service|call)\s+center\b|'
    r'\b(?:առևտրի|բիզնես|առևտրային|բժշկական)\s+կենտրոն(?:ի|ում)?\b|'
    r'\b(?:торговый|бизнес|медицинский)\s+центр(?:а|е)?\b',
    re.IGNORECASE
)

CURRENCY_MAP = {
    '$': 'USD', 'usd': 'USD', 'dollar': 'USD', 'dollars': 'USD',
    'դոլար': 'USD', 'դոլարի': 'USD', 'դոլարով': 'USD',
    'տոլար': 'USD', 'տոլարի': 'USD', 'տոլարով': 'USD',
    'ամն դոլար': 'USD', 'ամն դոլարով': 'USD', 'usd dollar': 'USD',
    'доллар': 'USD', 'доллара': 'USD', 'долларов': 'USD',
    'у.е.': 'USD', 'у.е': 'USD', 'ye': 'USD',

    '֏': 'AMD', 'amd': 'AMD', 'dram': 'AMD', 'drami': 'AMD', 'dramov': 'AMD',
    'դրամ': 'AMD', 'դրամի': 'AMD', 'դրամով': 'AMD', 'դր': 'AMD', 'դր.': 'AMD', 'դ': 'AMD', 'դ.': 'AMD',
    'հհ դրամ': 'AMD', 'հհդրամ': 'AMD', 'հհ դր': 'AMD', 'հհ դր.': 'AMD',
    'амд': 'AMD', 'драм': 'AMD', 'драма': 'AMD', 'драмов': 'AMD',

    '€': 'EUR', 'eur': 'EUR', 'euro': 'EUR', 'евро': 'EUR',
    '₽': 'RUB', 'руб': 'RUB', 'рублей': 'RUB', 'рубля': 'RUB'
}


def normalize_price_amount(raw_str):
    if not raw_str:
        return None
    cleaned = re.sub(r'[,\s\.․\u0589\u2024]', '', raw_str.strip())
    try:
        return int(cleaned)
    except ValueError:
        return None


def normalize_phone_number(raw_phone):
    if not raw_phone: return ""
    raw_stripped = raw_phone.strip()
    has_plus = raw_stripped.startswith('+')
    digits = re.sub(r'\D', '', raw_stripped)
    
    if not digits: return raw_stripped
        
    if digits.startswith('374') and len(digits) == 11:
        d = digits[3:]
        return f"+374 {d[:2]} {d[2:5]} {d[5:]}"
    elif digits.startswith('0') and len(digits) == 9:
        d = digits[1:]
        return f"+374 {d[:2]} {d[2:5]} {d[5:]}"
    elif len(digits) == 8:
        return f"+374 {digits[:2]} {digits[2:5]} {digits[5:]}"

    if has_plus or len(digits) > 10:
        if digits.startswith(('1', '7')) and len(digits) == 11:
            cc = digits[0]
            rest = digits[1:]
            if cc == '1':
                return f"+1 ({rest[:3]}) {rest[3:6]}-{rest[6:]}"
            return f"+{cc} {rest[:3]} {rest[3:6]}-{rest[6:]}"
            
        for cc_len in [3, 2, 1]:
            if len(digits) > cc_len + 6:
                cc = digits[:cc_len]
                rest = digits[cc_len:]
                chunks = []
                while rest:
                    chunk_size = 3 if len(rest) > 4 else 2
                    chunks.append(rest[:chunk_size])
                    rest = rest[chunk_size:]
                return f"+{cc} " + " ".join(chunks)

    return f"+{digits}" if has_plus else raw_stripped


def extract_property_category(text, is_media_only=False):
    if not text:
        return "Media-Only" if is_media_only else "General / Unclassified"
    text_lower = text.lower()
    
    # 0. Filter non-real-estate posts (vehicles, furniture, mines, accessories)
    if re.search(r'\b(?:ավտոմեքենա|մեքենա|ավտո|nissan|toyota|mercedes|bmw|kia|hyundai|ավազի\s+հանք|կահույք|պահոց\s+\+\s+քնելատեղ|սպորտային\s+հագուստ)\b', text_lower):
        if not re.search(r'\b(?:բնակարան|առանձնատուն|սեփական\s+տուն|հողատարածք)\b', text_lower):
            return "General / Unclassified"

    # 1. Commercial / Business premises (should not pollute Apartment / House)
    is_commercial = bool(re.search(
        r'\b(?:կոմերցիոն\s+տարածք|գրասենյակային\s+տարածք|գրասենյակ|բիզնես\s+տարածք|առևտրային\s+տարածք|արտադրական\s+տարածք|պահեստային\s+տարածք|խանութ|ավտոտնակ|garage|պահեստ|սրճարան|ռեստորան)\b',
        text_lower
    ))
    if is_commercial and not re.search(r'\b(?:բնակարան|առանձնատուն|սեփական\s+տուն)\b', text_lower):
        if re.search(r'\b(?:հող|հողատարածք|հողամաս)\b', text_lower):
            return "Land"
        return "General / Unclassified"

    # Clean out distracting footnotes before primary category matching:
    # A) "փոխանակում բնակարանի հետ" (exchange with apartment)
    cleaned_text = re.sub(r'(?:փոխանակ(?:վում|ում)?|обмен)\s+(?:նաև\s+)?[^\n.,;]+?\s+բնակարանի\s+հետ', ' [EXCHANGE_NOTE] ', text_lower)
    # B) "(տուն|առանձնատուն) կառուցելու համար" (to build a house)
    cleaned_text = re.sub(r'(?:տուն|առանձնատուն)\s+կառուցելու(?:\s+համար)?', ' [BUILDING_NOTE] ', cleaned_text)
    # C) Street names containing "տուն" root (e.g. Բագրատունյանց)
    cleaned_text = re.sub(r'բագրատունյա[նց]+', ' [STREET_NAME] ', cleaned_text)

    # 2. Inspect headline / first 2 lines (strongest signal of transaction item)
    lines = [line.strip() for line in cleaned_text.split('\n') if line.strip()]
    first_lines = " ".join(lines[:2]) if lines else cleaned_text

    # Title check for Land
    if re.search(r'\b(?:հող|հողատարածք|հողատարացք|հողամաս|հողակտոր|տնամերձ(?:\s+հողատարածք)?|գյուղատնտեսական\s+հող|պտղատու\s+այգի|land|plot|участок|земельный\s+участок)\b', first_lines):
        return "Land"

    # Title check for House
    if re.search(r'\b(?:առանձնատուն|առանձնատոին|առանձնատան|սեփական\s+տուն|սեփական\s+տոին|ամառանոց|թաունհաուզ|դուպլեքս|քոթեջ|տուն|տան|վիլլա|villa|cottage|townhouse|дом|дома|дач[ае]|коттедж|особняк|таунхаус)\b', first_lines):
        return "House"

    # Title check for Apartment
    if re.search(r'\b(?:բնակարան|բնակարանի|բնակարանում|բնակարանը|nakaran|apartment|flat|ստուդիո|ստուդիա|studio|квартира|квартиру|квартире|студия)\b', first_lines) or re.search(r'\b\d{1,2}\s*/\s*\d{1,2}\s*(?:-?րդ\s+)?(?:հարկ|этаж|эт)\b', first_lines):
        return "Apartment"

    # 3. Full text fallback checks
    if re.search(r'\b(?:հող|հողատարածք|հողատարացք|հողամաս|հողակտոր|տնամերձ|tnamerd|tnamerdz|hox|land|plot|участок|земля|земельный\s+участок)\b', cleaned_text):
        if not re.search(r'\b(?:առանձնատուն|սեփական\s+տուն|ամառանոց|թաունհաուզ|դուպլեքս|քոթեջ)\b', cleaned_text):
            return "Land"

    if re.search(r'\b(?:առանձնատուն|առանձնատոին|առանձնատան|առանձնատները|սեփական\s+տուն|սեփական\s+տոին|տուն|տան|տներ|տները|arandznatun|tun|house|villa|ամառանոց|дом|дома|дач[ае]|коттедж|особняк|թաունհաուզ|դուպլեքս|քոթեջ|таунхаус)\b', cleaned_text):
        if not re.search(r'\b(?:բնակարան|բնակարանի|բնակարանում|բնակարանը|квартира)\b', cleaned_text):
            return "House"

    if re.search(r'\b(?:բնակարան|բնակարանի|բնակարանում|բնակարանը|nakaran|apartment|flat|ստուդիո|ստուդիա|studio|квартира|квартиру|квартире|студия)\b', cleaned_text):
        return "Apartment"

    if re.search(r'\b\d{1,2}\s*/\s*\d{1,2}\s*(?:-?րդ\s+)?(?:հարկ|этаж|эт)\b', cleaned_text):
        return "Apartment"

    if re.search(r'\b(?:քարե|պանելային|մոնոլիտ|նորակառույց)\s+շենք(?:ի|ում|ը)?\b', cleaned_text) and re.search(r'\b\d{1,2}\s*[-֊:]*\s*սենյակ\w*', cleaned_text):
        return "Apartment"

    return "Media-Only" if is_media_only else "General / Unclassified"


# --- Zoning & Purpose Patterns ---
PARK_NEGATIVE_PATTERN = re.compile(
    r'\b(?:զբոսայգ(?:ի|ու|ում|ով|իներ)|մանկական\s+այգ(?:ի|ու|ում|ով|իներ)|սիրահարների\s+այգ(?:ի|ու|ում|ով|իներ)|օղակաձև\s+այգ(?:ի|ու|ում|ով|իներ)|պարկ|park)\b',
    re.IGNORECASE
)

AGRICULTURAL_PATTERN = re.compile(
    r'\b(?:գյուղատնտեսական|գյուղնշանակության|գյուղատնտեսության|գյուղատնտեսականի|գյուղ\s*նշանակության)\b|'
    r'\b(?:գյուղ\.\s*նշանակության)\b|'
    r'\b(?:պտղատու|խաղողի|ծիրանի|խնձորի|ընկույզի|բալի)\s+(?:այգ(?:ի|ու|ում|ով|իներ|իներով)?|ծառեր)\b|'
    r'\b(?:այգետարածք|այգեգործական|վարելահող|խոտհարք|արոտավայր|ջերմոց|ջերմոցային|ֆերմա|անասնագոմ|դաշտավայր)\b|'
    r'\b(?:сельхоз\w*|сельскохозяйственн\w*|пашն\w*|пашн\w*|ферм\w*|виноградник\w*|теплиц\w*)\b|'
    r'\b(?:agricultural|farmland|farming|orchard|vineyard|greenhouse)\b',
    re.IGNORECASE
)

RESIDENTIAL_HOUSING_PATTERN = re.compile(
    r'\b(?:տնամերձ|բնակելի|բնակավայրերի|բնակավայրի|բնակելի\s+կառուցապատման|տուն\s+կառուցելու|տան\s+համար|բնակարանաշինության|բնակելի\s+տարածք)\b|'
    r'\b(?:под\s+застройку|под\s+жилую\s+застройку|ижс|жилое|приусадебный|для\s+строительства\s+дома)\b|'
    r'\b(?:residential|homestead|housing|for\s+living|residential\s+building)\b',
    re.IGNORECASE
)


def extract_property_zoning(text, property_category=None):
    if not text and not property_category:
        return []

    text_str = text or ""
    text_clean = PARK_NEGATIVE_PATTERN.sub(" [PARK] ", text_str)

    zonings = []
    is_agri = bool(AGRICULTURAL_PATTERN.search(text_clean))
    is_housing = False

    if property_category in ["Apartment", "House"]:
        is_housing = True
    elif bool(RESIDENTIAL_HOUSING_PATTERN.search(text_clean)):
        is_housing = True

    if is_housing:
        zonings.append("Housing")
    if is_agri:
        zonings.append("Agricultural")

    return zonings


def extract_negotiation_status(text):
    if not text:
        return "Unknown"
    text_lower = text.lower()
    if any(w in text_lower for w in ["սակարկելի չէ", "սակարկման ենթակա չէ", "վերջնական գին", "not negotiable", "без торга", "торга нет"]):
        return False
    if any(w in text_lower for w in ["սակարկելի", "negotiable", "սակարկման ենթակա", "торг", "торгуемо"]):
        return True
    return "Unknown"


def extract_locations_from_text(text_lower):
    sanitized_text = EXCLUDED_CONTEXT_PATTERN.sub(" [EXCLUDED_CONTEXT] ", text_lower)
    found_locations = set()

    # Priority 1: Check explicit Location: or 📍 line for highest accuracy
    for line in sanitized_text.split('\n'):
        line_clean = line.strip()
        if line_clean.startswith('location:') or '📍' in line_clean or line_clean.startswith('տեղադրություն'):
            for canonical_name, patterns in LOCATION_DICTIONARY_REGEX.items():
                for pattern in patterns:
                    if re.search(pattern, line_clean, re.IGNORECASE):
                        found_locations.add(canonical_name)
                        break
            if found_locations:
                break

    # Priority 2: Full text inspection if none found yet or to add neighborhood details
    if not found_locations:
        for canonical_name, patterns in LOCATION_DICTIONARY_REGEX.items():
            for pattern in patterns:
                if re.search(pattern, sanitized_text, re.IGNORECASE):
                    found_locations.add(canonical_name)
                    break

    # Contextual conflict resolutions:
    # 1. Garun Avan (Spring Neighborhood) is in Nor Nork 2nd Massiv, not Avan district
    if "Nor Nork / Massiv" in found_locations and "Avan" in found_locations and "գարուն ավան" in sanitized_text:
        found_locations.remove("Avan")
    # 2. Azatutyan street in Dzoraghbyur should not be tagged as Arabkir
    if "Jrvezh / Dzoraghbyur" in found_locations and "Arabkir" in found_locations and "ազատության" in sanitized_text:
        if not re.search(r'\bկոմիտաս\b|\bարաբկիր\b', sanitized_text):
            found_locations.remove("Arabkir")
    # 3. Abovyan street/avenue in Kentron should not be tagged as Abovyan city
    if "Abovyan" in found_locations and "Kentron / Center" in found_locations:
        if re.search(r'\bաբովյան\s+(?:փողոց|պողոտա|նրբ)\b', sanitized_text):
            found_locations.remove("Abovyan")

    return list(found_locations)


def extract_housing_details(text, is_media_only=False):
    has_text = bool(text and text.strip())
    if not has_text:
        return {
            "has_text": False,
            "is_media_only": is_media_only,
            "property_category": "Media-Only" if is_media_only else "General / Unclassified",
            "listing_type": "Unknown",
            "is_negotiable": "Unknown",
            "floor_info": None,
            "prices": [],
            "locations": [],
            "phone_numbers": [],
            "sizes_sqm": [],
            "rooms": [],
            "zoning": []
        }

    sanitized_text = text
    text_lower = text.lower()

    property_category = extract_property_category(text, is_media_only=is_media_only)

    # 1. Extract phone numbers and mask them to avoid false price/code matches
    phone_matches = list(PHONE_NUMBER_PATTERN.finditer(sanitized_text))
    found_phones = []
    for match in reversed(phone_matches):
        raw_phone = match.group(0)
        found_phones.append(normalize_phone_number(raw_phone))
        start, end = match.span()
        sanitized_text = sanitized_text[:start] + " [PHONE_REMOVED] " + sanitized_text[end:]
    found_phones.reverse()

    # 2. Extract sizes
    found_sizes = []
    clean_for_size = RATE_PER_SQM_HEADER_PATTERN.sub(" [RATE_HEADER] ", sanitized_text)
    
    # Hectare sizes (1 ha = 10,000 sqm)
    for m in HA_PATTERN.finditer(clean_for_size):
        try:
            val = float(m.group('ha').replace(',', '.'))
            found_sizes.append(int(val * 10000))
        except ValueError:
            pass

    # Sotka sizes (1 sot = 100 sqm)
    for m in SOT_PATTERN.finditer(clean_for_size):
        try:
            val = float(m.group('sot').replace(',', '.'))
            found_sizes.append(int(val * 100))
        except ValueError:
            pass

    # Standard sqm sizes
    size_matches = list(SIZE_PATTERN.finditer(clean_for_size))
    for match in reversed(size_matches):
        size_str = match.group('size1') or match.group('size2') or match.group('size3')
        if size_str:
            size_str = size_str.strip()
            if re.search(r'[.,\s]\d{3}$', size_str):
                cleaned = re.sub(r'[.,\s]', '', size_str)
                size_num = int(cleaned)
            else:
                size_val = size_str.replace(',', '.')
                size_num = float(size_val)
                if size_num.is_integer():
                    size_num = int(size_num)

            # Avoid 1 sqm false matches resulting from 1 քմ rate mentions
            if size_num > 1 and size_num <= 500000:
                found_sizes.append(size_num)
        start, end = match.span()
        sanitized_text = sanitized_text[:start] + " [SIZE_REMOVED] " + sanitized_text[end:]
    found_sizes.reverse()

    # 3. Extract rooms
    found_rooms = []
    # Converted room formats (e.g. 2-3 սենյակ, 1 ձևափոխված 2)
    for m in CONVERTED_ROOMS_PATTERN.finditer(sanitized_text):
        found_rooms.extend([int(m.group('r1')), int(m.group('r2'))])
    for m in TRANSFORMED_ROOMS_PATTERN.finditer(sanitized_text):
        found_rooms.extend([int(m.group('r1')), int(m.group('r2'))])

    # List.am attributes (e.g. 5 Սենյակների քանակ)
    for m in LISTAM_ROOMS_PATTERN.finditer(sanitized_text):
        found_rooms.append(int(m.group('r')))

    # Word numbers (e.g. երկու սենյակ)
    for m in WORD_ROOMS_PATTERN.finditer(sanitized_text):
        w = m.group('word').lower()
        if w in WORD_TO_NUM:
            found_rooms.append(WORD_TO_NUM[w])

    room_matches = list(ROOM_PATTERN.finditer(sanitized_text))
    for match in reversed(room_matches):
        try:
            rooms_str = match.group('rooms1') or match.group('rooms2')
            if rooms_str:
                found_rooms.append(int(rooms_str))
        except ValueError:
            pass
        start, end = match.span()
        sanitized_text = sanitized_text[:start] + " [ROOM_REMOVED] " + sanitized_text[end:]
    found_rooms.reverse()

    # Studio default room count
    if not found_rooms and STUDIO_PATTERN.search(sanitized_text):
        found_rooms.append(1)

    # Discard rooms for pure Land listings
    if property_category == "Land":
        found_rooms = []

    # Clean other distractors
    sanitized_text = TREE_COUNT_PATTERN.sub(" [TREE_COUNT_REMOVED] ", sanitized_text)
    sanitized_text = DIMENSION_PATTERN.sub(" [DIMENSION_REMOVED] ", sanitized_text)
    sanitized_text = COUNT_ITEM_PATTERN.sub(" [COUNT_REMOVED] ", sanitized_text)
    sanitized_text = PROPERTY_CODE_PATTERN.sub(" [CODE_REMOVED] ", sanitized_text)
    sanitized_text = PERCENT_PATTERN.sub(" [PERCENT_REMOVED] ", sanitized_text)
    sanitized_text = COORDINATES_PATTERN.sub(" [COORDINATE_REMOVED] ", sanitized_text)

    # 4. Determine initial sale/rent signals
    rent_check_text = INVESTMENT_RENTAL_PATTERN.sub(" ", text_lower)
    is_rent = any(w in rent_check_text for w in [
        "վարձով", "վարձակալություն", "վարձակալության", "վարձակալությամբ", "տրվում է վարձով",
        "օրավարձով", "օրավարձ", "vardsov", "rent", "for rent", "vardzov", "аренду", "в аренду",
        "сдам", "сдается", "аренда", "посуточно",
        "տրվում է", "տերվում է", "երկարաժամկետ", "ամսական", "ամսեկան", "ամսավճար",
        "կվարձակալեմ", "կվարձեմ", "դեպոզիտ", "դեպոզիտային", "depozit", "amsakan", "erkarajamket"
    ])
    
    is_sale = any(w in text_lower for w in [
        "վաճառվում է", "վաճառվում են", "վաճառվում", "վաճառում եմ", "վաճառում ենք", "վաճառում",
        "վաճառք", "շտապ վաճառք", "վաճառքի է", "վաճառքի", "կգնեմ", "կգնենք", "գնում եմ", "առնում եմ",
        "vacharvum e", "vacharvum", "vacharum em", "vacharum", "sale", "for sale", "vachark", "nakavachark",
        "продается", "продам", "продажа", "продаю", "куплю"
    ])

    has_text_amd = bool(re.search(
        r'\b(?:amd|dram|drami|dramov|դրամ|դրամի|դրամով|դր|դ|հհ\s*դրամ|ամդ|драм|драма|драмов)\b|[֏]',
        text, re.IGNORECASE
    ))
    has_text_usd = bool(re.search(
        r'\b(?:usd|dollar|dollars|դոլար|դոլարի|դոլարով|տոլար|ամն\s*դոլար|доллар|доллара|долларов|у\.е)\b|[\$]',
        text, re.IGNORECASE
    ))

    # Mask per-sqm price mentions so rate numbers don't get captured as total property prices
    sanitized_text = PER_SQM_PRICE_PATTERN.sub(" [PER_SQM_PRICE_REMOVED] ", sanitized_text)

    # 5. Extract prices
    parsed_prices = []
    # Priority 1: Check explicit Price header line (List.am or FB format)
    explicit_price_match = re.search(r'(?:Price:|Գինը[^\n:]*:|Արժեքը[^\n:]*:)\s*([^\n]+)', text, re.IGNORECASE)
    if explicit_price_match:
        price_header_line = explicit_price_match.group(1)
        header_has_amd = bool(re.search(r'\b(?:amd|dram|drami|dramov|դրամ|դրամի|դրամով|դր|դ|ամդ|драм)\b|[֏]', price_header_line, re.IGNORECASE))
        header_has_usd = bool(re.search(r'\b(?:usd|dollar|dollars|դոլար|տոլար|ամն\s*դոլար|доллар|у\.е)\b|[\$]', price_header_line, re.IGNORECASE))
        for match in PRICE_CURRENCY_PATTERN.finditer(price_header_line):
            amount_raw = match.group('amount')
            pre_curr = match.group('pre_curr')
            post_curr = match.group('post_curr')
            amount = normalize_price_amount(amount_raw)
            if not amount or (2020 <= amount <= 2030 and not pre_curr and not post_curr):
                continue
            symbol = (pre_curr or post_curr or '').strip().lower()
            symbol_clean = re.sub(r'\s+', ' ', symbol)
            currency = CURRENCY_MAP.get(
                symbol_clean,
                'AMD' if header_has_amd and not header_has_usd else ('USD' if header_has_usd and not header_has_amd else None)
            )
            if not currency:
                if has_text_amd and not has_text_usd:
                    currency = 'AMD'
                elif is_rent and not is_sale and amount >= 30000:
                    currency = 'AMD'
                elif amount >= 10000000:
                    currency = 'AMD'
                elif 20000 <= amount < 1000000 and (is_sale or not is_rent):
                    currency = 'USD'
            if currency in ['AMD', 'USD']:
                parsed_prices.append({
                    "amount": amount,
                    "currency": currency,
                    "raw_text": match.group(0).strip()
                })

    # Priority 2: General text prices
    if not parsed_prices:
        for match in PRICE_CURRENCY_PATTERN.finditer(sanitized_text):
            amount_raw = match.group('amount')
            pre_curr = match.group('pre_curr')
            post_curr = match.group('post_curr')
            amount = normalize_price_amount(amount_raw)
            
            if not amount:
                continue
                
            if 2020 <= amount <= 2030 and not pre_curr and not post_curr:
                continue
                
            symbol = (pre_curr or post_curr or '').strip().lower()
            symbol_clean = re.sub(r'\s+', ' ', symbol)
            currency = CURRENCY_MAP.get(symbol_clean)
            
            if currency in ['AMD', 'USD']:
                if currency == 'USD' and amount < 50:
                    continue
                if currency == 'AMD' and amount < 5000:
                    continue
                parsed_prices.append({
                    "amount": amount,
                    "currency": currency,
                    "raw_text": match.group(0).strip()
                })
            elif not symbol_clean:
                # Text with explicit AMD keywords and no USD keywords defaults unadorned prices to AMD
                if has_text_amd and not has_text_usd:
                    if amount >= 10000:
                        parsed_prices.append({"amount": amount, "currency": "AMD", "raw_text": match.group(0).strip()})
                # Rentals (without explicit sale signals) in Armenia are quoted in AMD (e.g. 150,000 - 800,000 AMD/month)
                elif is_rent and not is_sale and 30000 <= amount <= 5000000:
                    parsed_prices.append({"amount": amount, "currency": "AMD", "raw_text": match.group(0).strip()})
                elif amount >= 10000000:
                    parsed_prices.append({"amount": amount, "currency": "AMD", "raw_text": match.group(0).strip()})
                # Real estate sales quoted as 20k-999k without symbol (and without AMD indicators) are USD
                elif 20000 <= amount < 1000000 and (is_sale or (not is_rent and property_category in ["Apartment", "House", "Land"])):
                    parsed_prices.append({"amount": amount, "currency": "USD", "raw_text": match.group(0).strip()})

    # Filter out false per-sqm price rates (< 1,000 USD or < 400,000 AMD) for sales
    if is_sale:
        valid_prices = []
        for p in parsed_prices:
            amt = p.get("amount")
            curr = p.get("currency")
            if (curr == "USD" and amt and amt < 1000) or (curr == "AMD" and amt and amt < 400000):
                continue
            valid_prices.append(p)
        if valid_prices:
            parsed_prices = valid_prices

    # 6. Determine listing type (Sale vs Rent)
    first_price_val = parsed_prices[0]['amount'] if parsed_prices else None
    first_price_curr = parsed_prices[0]['currency'] if parsed_prices else None
    listing_type = "Unknown"

    is_sale_priced = bool(
        first_price_val and property_category in ["Apartment", "House", "Land"] and
        ((first_price_curr == "USD" and first_price_val >= 15000) or
         (first_price_curr == "AMD" and first_price_val >= 8000000))
    )

    if is_sale_priced:
        listing_type = "Sale"
    elif is_rent and is_sale:
        listing_type = "Sale"
    elif is_rent:
        listing_type = "Rent"
    elif is_sale:
        listing_type = "Sale"
    elif first_price_val and first_price_val >= 15000 and property_category in ["Apartment", "House", "Land"]:
        listing_type = "Sale"

    is_negotiable = extract_negotiation_status(text)

    floor_info = None
    floor_match = FLOOR_PATTERN.search(text)
    if floor_match:
        floor_info = {
            "floor": int(floor_match.group("floor")),
            "total_floors": int(floor_match.group("total_floors"))
        }

    found_locations = extract_locations_from_text(text_lower)
    zoning = extract_property_zoning(text, property_category)

    return {
        "has_text": True,
        "is_media_only": is_media_only,
        "property_category": property_category,
        "listing_type": listing_type,
        "is_negotiable": is_negotiable,
        "floor_info": floor_info,
        "prices": parsed_prices,
        "locations": found_locations,
        "phone_numbers": list(dict.fromkeys(found_phones)),
        "sizes_sqm": list(dict.fromkeys(found_sizes)),
        "rooms": list(dict.fromkeys(found_rooms)),
        "zoning": zoning
    }


def safe_to_float(val_str, default=0.0):
    if not val_str:
        return default
    val_str = str(val_str).strip()
    try:
        if ',' in val_str and '.' in val_str:
            if val_str.rfind(',') > val_str.rfind('.'):
                val_str = val_str.replace('.', '').replace(',', '.')
            else:
                val_str = val_str.replace(',', '')
        elif val_str.count('.') > 1:
            parts = val_str.split('.')
            val_str = "".join(parts[:-1]) + "." + parts[-1]
        elif ',' in val_str and val_str.count(',') > 1:
            parts = val_str.split(',')
            val_str = "".join(parts[:-1]) + "." + parts[-1]
        elif ',' in val_str and val_str.count(',') == 1:
            parts = val_str.split(',')
            if len(parts[1]) == 3 and len(parts[0]) <= 3:
                val_str = val_str.replace(',', '')
            else:
                val_str = val_str.replace(',', '.')
        return float(val_str)
    except Exception:
        return default