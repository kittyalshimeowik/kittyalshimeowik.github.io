# location_data.py

LOCATION_DICTIONARY_REGEX = {
    # --- Yerevan Districts ---
    "Kentron / Center": [
        r'\bկենտրոնում\b', r'\bկենտրոնի\b', r'\bв\s+центре\b', r'\bв\s+центр\b', 
        r'\bin\s+kentron\b', r'\bin\s+(?:the\s+)?center\b', r'\bnear\s+(?:the\s+)?center\b',
        r'\bcascade\b', r'\bкаскад\b', r'\bկասկադ\b', 
        r'\bhanrapetutyan\b', r'\bհանրապետության\b', r'\bamiryan\b', r'\bամիրյան\b'
    ],
    "Arabkir": [
        r'\bարաբկիր\b', r'\bարաբկիրում\b', r'\barabkir\b', r'\bарабкир\b', 
        r'\bкомитас\b', r'\bկոմիտաս\b', r'\bկոմիտասում\b', r'\bkomitas\b', 
        r'\bбарекамутюн\b', r'\bբարեկամություն\b', r'\bbarekamutyun\b'
    ],
    "Davtashen": [
        r'\bդավթաշեն\b', r'\bդավթաշենում\b', r'\bդավթաշենի\b', r'\bdavtashen\b', r'\bdavitashen\b', r'\bдавиташен\b'
    ],
    "Zeytun / Kanaker": [
        r'\bզեյթուն\b', r'\bզեյթունում\b', r'\bzeitun\b', r'\bzeytun\b', r'\bзейтун\b', 
        r'\bканакер\b', r'\bканакер-зейтун\b', r'\bքանաքեռ\b', r'\bkanaker\b', r'\bпаруйра\s+севака\b', r'\bераз\b'
    ],
    "Nor Nork / Massiv": [
        r'\bնոր\s+նորք\b', r'\bнор\s+норк\b', r'\bнорк\b', r'\bնորքի\b', 
        r'\bմասիվ\b', r'\bմասիվի\b', r'\bմասիվում\b', r'\bmassiv\b', r'\bnor\s+nork\b', r'\bмассив\b'
    ],
    "Avan": [
        r'\bավան\b', r'\bаван\b', r'\bավանում\b', r'\bավանի\b', r'\bavan\b'
    ],
    "Malatia-Sebastia": [
        r'\bմալաթիա\b', r'\bмалатия\b', r'\bсебастия\b', r'\bսեբաստիա\b', 
        r'\bմալաթիայում\b', r'\bmalatia\b', r'\bsebastia\b', r'\bбангладеш\b', r'\bբանգլադեշ\b'
    ],
    "Shengavit": [
        r'\bշենգավիթ\b', r'\bшенгавит\b', r'\bշենգավիթում\b', r'\bshengavit\b', 
        r'\bчарбах\b', r'\bչարբախ\b', r'\bcharbakh\b', r'\bгарегин\s+нжде\b', r'\bգարեգին\s+նժդեհ\b'
    ],
    "Ajapnyak": [
        r'\bաջափնյակ\b', r'\bачапняк\b', r'\bաջափնյակում\b', r'\bajapnyak\b', 
        r'\b16-րդ\b', r'\b16rd\b', r'\bназарбекян\b', r'\bնազարբեկյան\b', r'\bhaghtanak\b', r'\bհաղթանակ\b'
    ],
    "Erebuni": [
        r'\bէրեբունի\b', r'\bэребуни\b', r'\bէրեբունիում\b', r'\berebuni\b'
    ],
    "Nork-Marash": [
        r'\bնորք-մարաշ\b', r'\bнорк-мараш\b', r'\bնորք\s+մարաշ\b', r'\bnork\s+marash\b'
    ],
    "Nubarashen": [
        r'\bնուբարաշեն\b', r'\bнубарашен\b', r'\bnubarashen\b'
    ],

    # --- Kotayk Province & Suburbs ---
    "Abovyan": [
        r'\bաբովյան\b', r'\bաբովյանում\b', r'\bաբովյանի\b', r'\babovyan\b', r'\bабовян\b'
    ],
    "Nor Gyugh": [
        r'\bնոր\s+գյուղ\b', r'\bնոր\s+գյուղում\b', r'\bnor\s+gyugh\b', r'\bнор\s+гюх\b'
    ],
    "Yeghvard": [
        r'\bեղվարդ\b', r'\bեղվարդում\b', r'\byeghvard\b', r'\bегвард\b'
    ],
    "Jrvezh / Dzoraghbyur": [
        r'\bջրվեժ\b', r'\bջրվեժում\b', r'\bjrvezh\b', r'\bджрвеж\b', r'\bձորաղբյուր\b', r'\bdzoraghbyur\b'
    ],
    "Arinj": [
        r'\bառինջ\b', r'\bառինջում\b', r'\barinj\b', r'\bариндж\b'
    ],
    "Kasagh / Proshyan": [
        r'\bքասախ\b', r'\bkasagh\b', r'\bкасах\b', r'\bպրոշյան\b', r'\bproshyan\b', r'\bпрошян\b'
    ],
    "Tsaghkadzor": [
        r'\bծաղկաձոր\b', r'\bծաղկաձորում\b', r'\btsaghkadzor\b', r'\btsakhkadzor\b', r'\bцахкадзор\b'
    ],

    # --- Ararat & Armavir Suburbs ---
    "Vedi": [
        r'\bվեդի\b', r'\bվեդիում\b', r'\bvedi\b', r'\bведи\b'
    ],
    "Artashat": [
        r'\bարտաշատ\b', r'\bարտաշատում\b', r'\bartashat\b', r'\bарташат\b'
    ],
    "Vagharshapat / Etchmiadzin": [
        r'\bէջմիածին\b', r'\bէջմիածնում\b', r'\betchmiadzin\b', r'\bechmiadzin\b', r'\bэчмиадзин\b', r'\bվաղարշապատ\b'
    ],
    "Ashtarak": [
        r'\bաշտարակ\b', r'\bաշտարակում\b', r'\bashtarak\b', r'\bаштарак\b'
    ],

    # --- Extended Regions & Cities ---
    "Dilijan": [
        r'\bդիլիջան\b', r'\bդիլիջանում\b', r'\bdilijan\b', r'\bдилижан\b', r'\bաղավնավանք\b', r'\baghavnavank\b'
    ],
    "Goris": [
        r'\bգորիս\b', r'\bգորիսում\b', r'\bgoris\b', r'\bгорис\b'
    ],
    "Gyumri": [
        r'\bգյումրի\b', r'\bգյումրիում\b', r'\bgyumri\b', r'\bгюмри\b'
    ],
    "Vanadzor": [
        r'\bվանաձոր\b', r'\bվանաձորում\b', r'\bvanadzor\b', r'\bванадзор\b'
    ],
    "Sevan": [
        r'\bսևան\b', r'\bսևանում\b', r'\bsevan\b', r'\bсеван\b'
    ]
}