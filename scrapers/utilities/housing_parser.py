# scrapers/facebook/housing_parser.py

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

SIZE_PATTERN = re.compile(
    r'(?:(?P<size1>[1-9]\d{0,2}(?:[.,\s]\d{3})+|\d{1,5}(?:[.,]\d+)+|\d{1,5})\s*[-֊:]*\s*(?:քմ|ք\.մ\.|ք․մ․|ք\.\s*մ|քառակուսի\s+մետր|քառ\.\s*(?:մ\.|մետր)|sq\s*m|sq\.m\.|sqm|m2|m²|ք/մ|qm|q\.m\.|м²|кв\.?\s*м\.?|մ²|մ2|մետր))'
    r'|'
    r'(?:(?:քմ|ք\.մ\.|ք․մ․|ք\.\s*մ|քառակուսի\s+մետր|քառ\.\s*(?:մ\.|մետր)|sq\s*m|sq\.m\.|sqm|m2|m²|ք/մ|qm|q\.m\.|м²|кв\.?\s*м\.?|մ²|մ2|մետր)\s*[-֊:]*\s*(?P<size2>[1-9]\d{0,2}(?:[.,\s]\d{3})+|\d{1,5}(?:[.,]\d+)+|\d{1,5}))',
    re.IGNORECASE
)

ROOM_PATTERN = re.compile(
    r'(?:(?P<rooms1>\d{1,2})\s*[-֊:]*\s*(?:սենյակ|սենյականոց|սեն\.|room|rooms|bed|bd|bedrooms|комн(?:\.|аты|ат)?))'
    r'|'
    r'(?:(?:սենյակ|սենյականոց|սեն\.|room|rooms|bed|bd|bedrooms|комн(?:\.|аты|ат)?)\s*[-֊:]*\s*(?P<rooms2>\d{1,2}))',
    re.IGNORECASE
)

PRICE_CURRENCY_PATTERN = re.compile(
    r'(?:գինը[\s:`՝]*|price[\s:`՝]*|արժեքը[\s:`՝]*)?'
    r'(?P<pre_curr>\$|֏|€|USD|AMD|EUR|dram|դրամ|դոլար|dollar|տոլար|հհ\s*դրամ|ամն\s*դոլար|руб|рублей)?\s*'
    r'(?<![\d.])(?P<amount>[1-9]\d{0,2}(?:[,\s\.]\d{3})+(?!\d)|[1-9]\d{1,8})(?![\d.])\s*'
    r'(?P<post_curr>\$|֏|€|USD|AMD|EUR|dram|դրամ|դոլար|dollar|տոլար|հհ\s*դրամ|ամն\s*դոլար|руб|рублей)?',
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
    '$': 'USD', 'usd': 'USD', 'dollar': 'USD', 'դոլար': 'USD', 'տոլար': 'USD',
    'ամն դոլար': 'USD', 'ամն դոլարով': 'USD', 'usd dollar': 'USD',
    '֏': 'AMD', 'amd': 'AMD', 'dram': 'AMD', 'դրամ': 'AMD', 'հհ դրամ': 'AMD', 'հհդրամ': 'AMD',
    '€': 'EUR', 'eur': 'EUR', 'euro': 'EUR',
    'руб': 'RUB', 'рублей': 'RUB'
}


def normalize_price_amount(raw_str):
    if not raw_str:
        return None
    cleaned = re.sub(r'[,\s\.]', '', raw_str.strip())
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
    
    # 1. Apartment: explicit apartment/studio keywords or building floor ratio (e.g. 3/9 հարկ, 4/5 этаж)
    if re.search(r'\b(?:բնակարան|բնակարանի|բնակարանում|բնակարանը|nakaran|apartment|flat|ստուդիո|studio|квартира|квартиру|квартире|студия)\b', text_lower) or re.search(r'\b\d{1,2}\s*/\s*\d{1,2}\s*(?:-?րդ\s+)?(?:հարկ|этаж|эт)\b', text_lower):
        return "Apartment"
        
    # 2. House: explicit house/villa/cottage keywords with word boundaries to avoid matching inside street names (e.g. Բագրատունյանց)
    if re.search(r'\b(?:առանձնատուն|առանձնատան|առանձնատները|սեփական\s+տուն|տուն|տան|տներ|տները|arandznatun|tun|house|villa|ամառանոց|дом|дома|дач[ае]|коттедж|особняк)\b', text_lower):
        return "House"

    # 3. Land: explicit land/plot keywords
    if re.search(r'\b(?:հող|հողատարածք|հողատարածքի|հողամաս|հողամասի|հողակտոր|tnamerd|tnamerdz|hox|land|plot|участок|земля|земли)\b', text_lower):
        return "Land"

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
    """
    Classifies property purpose/zoning:
    - 'Housing': Intended for residential living/housing (apartments, residential houses, homestead land).
    - 'Agricultural': Intended for agricultural, farming, crops, orchards, greenhouses.
    Returns: ['Housing'], ['Agricultural'], or ['Housing', 'Agricultural'] (if dual-purpose), or [].
    """
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
    for canonical_name, patterns in LOCATION_DICTIONARY_REGEX.items():
        for pattern in patterns:
            if re.search(pattern, sanitized_text, re.IGNORECASE):
                found_locations.add(canonical_name)
                break
                
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

    listing_type = "Unknown"
    if any(w in text_lower for w in ["վարձով", "օրավարձով", "vardsov", "rent", "vardzov", "аренду", "сдам", "сдается", "аренда", "посуточно"]):
        listing_type = "Sale" if any(w in text_lower for w in ["վաճառք", "վաճառվում", "продажа", "продается"]) else "Rent"
    elif any(w in text_lower for w in ["վաճառվում է", "vacharvum e", "sale", "nakavachark", "վաճառք", "продается", "продам", "продажа"]):
        listing_type = "Sale"

    is_negotiable = extract_negotiation_status(text)

    floor_info = None
    floor_match = FLOOR_PATTERN.search(text)
    if floor_match:
        floor_info = {
            "floor": int(floor_match.group("floor")),
            "total_floors": int(floor_match.group("total_floors"))
        }

    phone_matches = list(PHONE_NUMBER_PATTERN.finditer(sanitized_text))
    found_phones = []
    for match in reversed(phone_matches):
        raw_phone = match.group(0)
        found_phones.append(normalize_phone_number(raw_phone))
        start, end = match.span()
        sanitized_text = sanitized_text[:start] + " [PHONE_REMOVED] " + sanitized_text[end:]
    found_phones.reverse()

    size_matches = list(SIZE_PATTERN.finditer(sanitized_text))
    found_sizes = []
    for match in reversed(size_matches):
        size_str = match.group('size1') or match.group('size2')
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

            found_sizes.append(size_num)
        start, end = match.span()
        sanitized_text = sanitized_text[:start] + " [SIZE_REMOVED] " + sanitized_text[end:]
    found_sizes.reverse()

    room_matches = list(ROOM_PATTERN.finditer(sanitized_text))
    found_rooms = []
    for match in reversed(room_matches):
        try: 
            rooms_str = match.group('rooms1') or match.group('rooms2')
            found_rooms.append(int(rooms_str))
        except ValueError: pass
        start, end = match.span()
        sanitized_text = sanitized_text[:start] + " [ROOM_REMOVED] " + sanitized_text[end:]
    found_rooms.reverse()

    sanitized_text = TREE_COUNT_PATTERN.sub(" [TREE_COUNT_REMOVED] ", sanitized_text)
    sanitized_text = DIMENSION_PATTERN.sub(" [DIMENSION_REMOVED] ", sanitized_text)
    sanitized_text = COUNT_ITEM_PATTERN.sub(" [COUNT_REMOVED] ", sanitized_text)
    sanitized_text = PROPERTY_CODE_PATTERN.sub(" [CODE_REMOVED] ", sanitized_text)
    sanitized_text = PERCENT_PATTERN.sub(" [PERCENT_REMOVED] ", sanitized_text)
    sanitized_text = COORDINATES_PATTERN.sub(" [COORDINATE_REMOVED] ", sanitized_text)

    parsed_prices = []
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
            if amount >= 50000:
                parsed_prices.append({"amount": amount, "currency": "AMD", "raw_text": match.group(0).strip()})
            elif 3000 <= amount < 50000:
                continue
            elif 50 <= amount < 3000:
                continue

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
    """Safely converts strings with regional separators (dots/commas) to float."""
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
            # Handle multiple dots like '1.363.6' -> treat previous dots as thousands separators
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