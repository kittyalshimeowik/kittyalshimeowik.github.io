# scrapers/utilities/__tests__/test_location_and_parser.py
import os
import sys
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scrapers.utilities.housing_parser import (
    extract_housing_details,
    extract_coordinates,
    extract_per_sqm_rates,
    extract_property_category,
    extract_property_zoning,
    extract_negotiation_status,
    normalize_phone_number,
    safe_to_float,
    extract_locations_from_text,
    CURRENCY_MAP
)
from scrapers.utilities.location_data import LOCATION_DICTIONARY_REGEX


class TestLocationAndHousingParser(unittest.TestCase):

    # -------------------------------------------------------------------------
    # 1. safe_to_float helper tests
    # -------------------------------------------------------------------------

    def test_safe_to_float_standard_numbers(self):
        self.assertEqual(safe_to_float(100), 100.0)
        self.assertEqual(safe_to_float(45.5), 45.5)
        self.assertEqual(safe_to_float("120"), 120.0)
        self.assertEqual(safe_to_float("120.75"), 120.75)

    def test_safe_to_float_thousands_and_decimals(self):
        # Comma thousands
        self.assertEqual(safe_to_float("1,500"), 1500.0)
        self.assertEqual(safe_to_float("1,500.50"), 1500.5)

        # European dot thousands and comma decimal
        self.assertEqual(safe_to_float("1.500,50"), 1500.5)

        # Multiple dots e.g. 1.363.6 -> keeps last dot as decimal
        self.assertEqual(safe_to_float("1.363.6"), 1363.6)

    def test_safe_to_float_invalid_inputs(self):
        self.assertEqual(safe_to_float(None), 0.0)
        self.assertIsNone(safe_to_float(None, default=None))
        self.assertEqual(safe_to_float(""), 0.0)
        self.assertIsNone(safe_to_float("", default=None))
        self.assertEqual(safe_to_float("not_a_number"), 0.0)
        self.assertEqual(safe_to_float("invalid", default=0.0), 0.0)

    # -------------------------------------------------------------------------
    # 2. Price and Currency parsing
    # -------------------------------------------------------------------------

    def test_currency_map_symbols(self):
        self.assertEqual(CURRENCY_MAP.get("$"), "USD")
        self.assertEqual(CURRENCY_MAP.get("usd"), "USD")
        self.assertEqual(CURRENCY_MAP.get("֏"), "AMD")
        self.assertEqual(CURRENCY_MAP.get("դրամ"), "AMD")
        self.assertEqual(CURRENCY_MAP.get("руб"), "RUB")
        self.assertEqual(CURRENCY_MAP.get("€"), "EUR")

    def test_price_filtering_and_retention(self):
        # USD and AMD are accepted in housing market extraction
        text_usd = "Rent luxury villa: 2500$ monthly"
        details_usd = extract_housing_details(text_usd)
        self.assertEqual(len(details_usd["prices"]), 1)
        self.assertEqual(details_usd["prices"][0]["amount"], 2500)
        self.assertEqual(details_usd["prices"][0]["currency"], "USD")

        text_amd = "Վարձով բնակարան: Գինը` 250,000 դրամ"
        details_amd = extract_housing_details(text_amd)
        self.assertEqual(len(details_amd["prices"]), 1)
        self.assertEqual(details_amd["prices"][0]["amount"], 250000)
        self.assertEqual(details_amd["prices"][0]["currency"], "AMD")

        # Armenian separator and dram symbol (250․000֏)
        text_arm_sep = "Վարձով 2 սենյակ: 250․000֏ ամսական"
        details_arm_sep = extract_housing_details(text_arm_sep)
        self.assertEqual(len(details_arm_sep["prices"]), 1)
        self.assertEqual(details_arm_sep["prices"][0]["amount"], 250000)
        self.assertEqual(details_arm_sep["prices"][0]["currency"], "AMD")

        # Armenian abbreviation 'դ' (180.000դ)
        text_arm_d = "Վարձով բնակարան 180.000դ"
        details_arm_d = extract_housing_details(text_arm_d)
        self.assertEqual(len(details_arm_d["prices"]), 1)
        self.assertEqual(details_arm_d["prices"][0]["amount"], 180000)
        self.assertEqual(details_arm_d["prices"][0]["currency"], "AMD")

        # Rental with unadorned price should never be classified as USD
        text_rent_unadorned = "Վարձով է տրվում 2 սենյականոց բնակարան Կենտրոնում, գինը` 300,000"
        details_rent_unadorned = extract_housing_details(text_rent_unadorned)
        self.assertEqual(len(details_rent_unadorned["prices"]), 1)
        self.assertEqual(details_rent_unadorned["prices"][0]["amount"], 300000)
        self.assertEqual(details_rent_unadorned["prices"][0]["currency"], "AMD")
        self.assertEqual(details_rent_unadorned["listing_type"], "Rent")

        # Sale with investor rental potential should remain Sale
        text_investor_sale = "Վաճառվում է առանձնատուն, 1-ին հարկը կարող եք տալ վարձով: Գինը` 185,000$"
        details_investor_sale = extract_housing_details(text_investor_sale)
        self.assertEqual(len(details_investor_sale["prices"]), 1)
        self.assertEqual(details_investor_sale["prices"][0]["amount"], 185000)
        self.assertEqual(details_investor_sale["prices"][0]["currency"], "USD")
        self.assertEqual(details_investor_sale["listing_type"], "Sale")

        # Monthly rental phrasing without explicit 'վարձով' word (e.g., 240.000դ Ամսեկան, Տրվում է Երկարաժամկետ)
        text_monthly_rent = "1-2 սենյականոց բնակարան\n240.000դ Ամսեկան\nՏրվում է Երկարաժամկետ"
        details_monthly_rent = extract_housing_details(text_monthly_rent)
        self.assertEqual(len(details_monthly_rent["prices"]), 1)
        self.assertEqual(details_monthly_rent["prices"][0]["amount"], 240000)
        self.assertEqual(details_monthly_rent["prices"][0]["currency"], "AMD")
        self.assertEqual(details_monthly_rent["listing_type"], "Rent")

    def test_multiple_prices_in_post(self):
        text = "Գինը` 120,000$ կամ 48,000,000 դրամ"
        details = extract_housing_details(text)
        self.assertEqual(len(details["prices"]), 2)
        currencies = set(p["currency"] for p in details["prices"])
        self.assertIn("USD", currencies)
        self.assertIn("AMD", currencies)

    def test_coordinates_sanitization_no_false_prices(self):
        text = (
            "Շտապ վաճառվում է հողատարածք:\n"
            "Կոորդինատներ` 40.187245, 44.515234\n"
            "Մակերեսը 800 քմ: Գինը 45,000$"
        )
        details = extract_housing_details(text)
        self.assertEqual(len(details["prices"]), 1)
        self.assertEqual(details["prices"][0]["amount"], 45000)
        self.assertEqual(details["prices"][0]["currency"], "USD")
        self.assertIn(800, details["sizes_sqm"])
        self.assertIsNotNone(details.get("coordinates"))
        self.assertAlmostEqual(details["coordinates"]["lat"], 40.187245)
        self.assertAlmostEqual(details["coordinates"]["lng"], 44.515234)

    def test_coordinates_extraction_methods(self):
        # 1. List.am header
        t1 = "Location: 40.521412, 44.71768, Կոտայքի մարզ\nPrice: $75,000"
        c1 = extract_coordinates(t1)
        self.assertIsNotNone(c1)
        self.assertAlmostEqual(c1["lat"], 40.521412)
        self.assertAlmostEqual(c1["lng"], 44.71768)

        # 2. Yandex Maps URL
        t2 = "Հողատարածք https://yandex.ru/navi?text=40.727950,44.686819&si=xyz Մարգահովիտ"
        c2 = extract_coordinates(t2)
        self.assertIsNotNone(c2)
        self.assertAlmostEqual(c2["lat"], 40.727950)
        self.assertAlmostEqual(c2["lng"], 44.686819)

        # 3. Google Maps URL
        t3 = "Գտնվելու վայրը https://maps.google.com/?q=40.187245,44.515234 Երևան"
        c3 = extract_coordinates(t3)
        self.assertIsNotNone(c3)
        self.assertAlmostEqual(c3["lat"], 40.187245)
        self.assertAlmostEqual(c3["lng"], 44.515234)

        # 4. Labeled GPS coordinates
        t4 = "📍 Coordinates: 40.312870, 44.311863 Փարպի"
        c4 = extract_coordinates(t4)
        self.assertIsNotNone(c4)
        self.assertAlmostEqual(c4["lat"], 40.312870)
        self.assertAlmostEqual(c4["lng"], 44.311863)

        # 5. Raw GPS coordinate pair
        t5 = "40.140146, 44.739168 ԿՈՐԴԻՆԱՏՆԵՐ Գառնի"
        c5 = extract_coordinates(t5)
        self.assertIsNotNone(c5)
        self.assertAlmostEqual(c5["lat"], 40.140146)
        self.assertAlmostEqual(c5["lng"], 44.739168)

        # 6. None when no coordinates are present
        t6 = "Վաճառվում է 2 սենյականոց բնակարան Կենտրոնում: Գինը 80,000$"
        self.assertIsNone(extract_coordinates(t6))

    def test_extract_per_sqm_rates_helper(self):
        # Prefix format
        rates_prefix = extract_per_sqm_rates("🏷️Արժեքը՝   1քմ - 70$")
        self.assertEqual(len(rates_prefix), 1)
        self.assertEqual(rates_prefix[0]["amount"], 70)
        self.assertEqual(rates_prefix[0]["currency"], "USD")
        self.assertEqual(rates_prefix[0]["rate_per_sqm"], 70.0)

        # Postfix format
        rates_postfix = extract_per_sqm_rates("Գինը՝ 35 ԱՄՆ դոլար / 1 քմ")
        self.assertEqual(len(rates_postfix), 1)
        self.assertEqual(rates_postfix[0]["amount"], 35)
        self.assertEqual(rates_postfix[0]["currency"], "USD")
        self.assertEqual(rates_postfix[0]["rate_per_sqm"], 35.0)

        # Sotka format (1 sotka = 100 sqm)
        rates_sot = extract_per_sqm_rates("1 սոտկան - 5000$")
        self.assertEqual(len(rates_sot), 1)
        self.assertEqual(rates_sot[0]["amount"], 5000)
        self.assertEqual(rates_sot[0]["unit"], "sot")
        self.assertEqual(rates_sot[0]["rate_per_sqm"], 50.0)

    def test_per_sqm_rate_total_price_calculation_usd(self):
        # Post 1 from user: 70$/sqm and 7066 sqm -> $494,620 total cost
        text_post1 = (
            "🌿 Վաճառվում է հողատարածք Ջրվեժ-Առինջ տանող ճանապարհին։\n"
            "🏷️Արժեքը՝   1քմ - 70$\n"
            "📐 Մակերես՝ 7066  քմ\n"
            "🏡 Նշանակություն՝ գյուղատնտեսական"
        )
        details1 = extract_housing_details(text_post1)
        self.assertEqual(len(details1["prices"]), 1)
        self.assertEqual(details1["prices"][0]["amount"], 494620)
        self.assertEqual(details1["prices"][0]["currency"], "USD")
        self.assertEqual(details1["sizes_sqm"], [7066])
        self.assertEqual(details1["property_category"], "Land")
        self.assertEqual(details1["listing_type"], "Sale")

        # Post 2 from user: 80$/sqm and 5770 sqm -> $461,600 total cost
        text_post2 = (
            "🌿 Վաճառվում է հողատարածք Ձորաղբյուրում՝ ձիարշավարանի մոտ։\n"
            "🏷️Արժեքը՝   1քմ - 80$\n"
            "📐 Մակերես՝ 5770  քմ\n"
            "🏡 Նշանակություն՝ գյուղատնտեսական"
        )
        details2 = extract_housing_details(text_post2)
        self.assertEqual(len(details2["prices"]), 1)
        self.assertEqual(details2["prices"][0]["amount"], 461600)
        self.assertEqual(details2["prices"][0]["currency"], "USD")
        self.assertEqual(details2["sizes_sqm"], [5770])
        self.assertEqual(details2["property_category"], "Land")
        self.assertEqual(details2["listing_type"], "Sale")

    def test_per_sqm_rate_total_price_calculation_amd(self):
        # Apartment complex with AMD rate: 630,000 AMD/sqm and 107.5 sqm -> 67,725,000 AMD
        text_amd_rate = "Բազիս բնակելի համալիր րաֆֆու 28։ 4 սենյակ 107.5քմ 1քմ=630000 սեփականատեր"
        details_amd = extract_housing_details(text_amd_rate)
        self.assertEqual(len(details_amd["prices"]), 1)
        self.assertEqual(details_amd["prices"][0]["amount"], 67725000)
        self.assertEqual(details_amd["prices"][0]["currency"], "AMD")
        self.assertEqual(details_amd["sizes_sqm"], [107.5])
        self.assertEqual(details_amd["property_category"], "Apartment")
        self.assertEqual(details_amd["listing_type"], "Sale")

    def test_explicit_price_not_overridden_by_sqm_rate(self):
        # When an explicit total price is provided alongside a rate, the explicit total price must be used
        text = "Վաճառվում է առանձնատուն: Գինը՝ 210,000$, 1քմ արժեքը 900$: Մակերեսը 235 քմ"
        details = extract_housing_details(text)
        self.assertEqual(len(details["prices"]), 1)
        self.assertEqual(details["prices"][0]["amount"], 210000)
        self.assertEqual(details["prices"][0]["currency"], "USD")

    def test_per_sqm_rate_without_size_does_not_become_sale_price(self):
        # A per-sqm price without a known property size must never be captured as the total property price
        text = "Վաճառվում է հողատարածք: 1քմ - 70$: Զանգահարել 098390839"
        details = extract_housing_details(text)
        self.assertEqual(details["prices"], [])

    # -------------------------------------------------------------------------
    # 3. Room count extraction
    # -------------------------------------------------------------------------


    def test_room_counts_various_phrasings(self):
        cases = [
            ("1 սենյականոց բնակարան", 1),
            ("2 սենյակ ունեցող տուն", 2),
            ("3-սենյականոց", 3),
            ("4 սեն.", 4),
            ("1 комн квартира", 1),
            ("2-комнатная квартира", 2),
            ("3 комн. студия", 3),
            ("2 bedrooms and living room", 2),
            ("5 room house", 5)
        ]
        for text, expected_room in cases:
            details = extract_housing_details(text)
            self.assertIn(expected_room, details["rooms"], f"Failed for text: '{text}'")

    # -------------------------------------------------------------------------
    # 4. Size and Area extraction
    # -------------------------------------------------------------------------

    def test_size_extraction_units(self):
        cases = [
            ("Մակերեսը 45 քմ", 45),
            ("Տարածքը` 85.5 ք.մ.", 85.5),
            ("Ընդհանուր մակերես 120 քառ. մետր", 120),
            ("Площадь 60 кв.м", 60),
            ("70 кв м жилая площадь", 70),
            ("95 m2 total area", 95),
            ("150 sqm modern apartment", 150)
        ]
        for text, expected_size in cases:
            details = extract_housing_details(text)
            self.assertIn(expected_size, details["sizes_sqm"], f"Failed for text: '{text}'")

    # -------------------------------------------------------------------------
    # 5. Listing Type and Property Category classification
    # -------------------------------------------------------------------------

    def test_listing_type_detection(self):
        # Sale
        self.assertEqual(extract_housing_details("Շտապ վաճառվում է բնակարան")["listing_type"], "Sale")
        self.assertEqual(extract_housing_details("Продается 2 комн квартира")["listing_type"], "Sale")
        self.assertEqual(extract_housing_details("Apartment for sale in Center")["listing_type"], "Sale")

        # Rent
        self.assertEqual(extract_housing_details("Տրվում է երկարաժամկետ վարձով")["listing_type"], "Rent")
        self.assertEqual(extract_housing_details("Сдается в аренду на длительный срок")["listing_type"], "Rent")
        self.assertEqual(extract_housing_details("Apartment for rent long term")["listing_type"], "Rent")

        # Conflict resolution (Sale takes precedence if both mentioned)
        self.assertEqual(extract_housing_details("Վաճառվում է կամ տրվում է վարձով")["listing_type"], "Sale")

    def test_property_category_detection(self):
        self.assertEqual(extract_property_category("3 սենյականոց բնակարան"), "Apartment")
        self.assertEqual(extract_property_category("Վաճառվում է սեփական տուն / առանձնատուն"), "House")
        self.assertEqual(extract_property_category("Վաճառվում է հողատարածք Դիլիջանում"), "Land")
        self.assertEqual(extract_property_category("Չնշված տեքստ"), "General / Unclassified")
        self.assertEqual(extract_property_category("", is_media_only=True), "Media-Only")

    def test_property_category_bagratunyants_fix(self):
        # Street names containing "տուն" root should not falsely classify apartments as houses
        self.assertEqual(extract_property_category("Բնակարան Բագրատունյանց պողոտայում"), "Apartment")
        self.assertEqual(extract_property_category("Բագրատունյաց պողոտա, 3 սենյականոց բնակարան"), "Apartment")

    def test_property_zoning_detection(self):
        # 1. Housing (apartments or houses inherit Housing zoning)
        self.assertIn("Housing", extract_property_zoning("3 սենյականոց բնակարան", property_category="Apartment"))
        self.assertIn("Housing", extract_property_zoning("Վաճառվում է առանձնատուն", property_category="House"))

        # 2. Residential / Homestead land
        res_land = "Վաճառվում է տնամերձ հողատարածք բնակելի կառուցապատման համար"
        self.assertEqual(extract_property_zoning(res_land, property_category="Land"), ["Housing"])

        # Russian residential building land (ИЖС)
        res_land_ru = "Участок под застройку дома, ИЖС"
        self.assertEqual(extract_property_zoning(res_land_ru, property_category="Land"), ["Housing"])

        # 3. Agricultural land / Orchards / Farming
        agri_text = "Վաճառվում է գյուղատնտեսական նշանակության հողամաս, պտղատու այգի"
        self.assertEqual(extract_property_zoning(agri_text, property_category="Land"), ["Agricultural"])

        agri_greenhouse = "Հողատարածք ջերմոցային տնտեսության համար"
        self.assertEqual(extract_property_zoning(agri_greenhouse, property_category="Land"), ["Agricultural"])

        agri_ru = "Продается участок сельхозназначения, виноградники"
        self.assertEqual(extract_property_zoning(agri_ru, property_category="Land"), ["Agricultural"])

        # 4. Dual-purpose: Homestead with fruit orchard / farming
        dual_text = "Վաճառվում է տնամերձ հողատարածք պտղատու այգով և ծիրանի ծառերով"
        dual_zonings = extract_property_zoning(dual_text, property_category="Land")
        self.assertIn("Housing", dual_zonings)
        self.assertIn("Agricultural", dual_zonings)

        # 5. Public park suppression (should not be tagged as agricultural)
        park_text = "Բնակարան Սիրահարների զբոսայգու հարևանությամբ"
        park_zonings = extract_property_zoning(park_text, property_category="Apartment")
        self.assertEqual(park_zonings, ["Housing"])
        self.assertNotIn("Agricultural", park_zonings)

    # -------------------------------------------------------------------------
    # 6. Location Dictionary and District Matching
    # -------------------------------------------------------------------------

    def test_yerevan_districts_recognition(self):
        districts_test = {
            "Kentron / Center": "Բնակարան Կենտրոնում, Ամիրյան փողոցում, կենտրոնական հատված",
            "Arabkir": "Կոմիտասի պողոտա, Արաբկիր վարչական շրջան, Վրացական փողոց, Ադոնց",
            "Davtashen": "Դավիթաշեն 2-րդ թաղամասում, Դավթաշենի կամուրջ",
            "Zeytun / Kanaker": "Զեյթունում, Պարույր Սևակի փողոց, Երազ թաղամաս",
            "Nor Nork / Massiv": "Նոր Նորքի 4-րդ զանգված, Մասիվ",
            "Avan": "Ավան Առինջ, Ավանում",
            "Malatia-Sebastia": "Մալաթիա-Սեբաստիա, Բանգլադեշ",
            "Shengavit": "Շենգավիթ, Չարբախ, Գարեգին Նժդեհ, Բագրատունյանց պողոտա, 3-րդ մաս",
            "Ajapnyak": "Աջափնյակում, 16-րդ թաղամաս, 15-րդ թաղ, Մարգարյան փողոց, Նազարբեկյան",
            "Erebuni": "Էրեբունի թաղամասում",
            "Nork-Marash": "Նորք-Մարաշ համայնքում",
            "Nubarashen": "Նուբարաշեն 11-րդ փողոց"
        }

        for district, text in districts_test.items():
            details = extract_housing_details(text)
            self.assertIn(district, details["locations"], f"Failed to match district: {district}")

    def test_suburb_and_regional_cities_recognition(self):
        regions_test = {
            "Abovyan": "Բնակարան Աբովյան քաղաքում",
            "Dilijan": "Առանձնատուն Դիլիջանում, գեղեցիկ բնություն",
            "Gyumri": "Շտապ վաճառք Գյումրիում",
            "Vanadzor": "Տուն Վանաձոր քաղաքում, Վանաձորի շրջակայքում",
            "Tsaghkadzor": "Քոթեջ Ծաղկաձորում",
            "Vagharshapat / Etchmiadzin": "Տուն Էջմիածնում",
            "Ashtarak": "Աշտարակ քաղաքում",
            "Sevan": "Հանգստի գոտի Սևանում"
        }

        for region, text in regions_test.items():
            details = extract_housing_details(text)
            self.assertIn(region, details["locations"], f"Failed to match region: {region}")

    def test_excluded_context_suppression(self):
        text = "Բնակարան բժշկական կենտրոնի մոտ"
        locs = extract_locations_from_text(text.lower())
        self.assertNotIn("Kentron / Center", locs)

    # -------------------------------------------------------------------------
    # 7. Phone Number normalization & multi-contact extraction
    # -------------------------------------------------------------------------

    def test_phone_number_formats(self):
        phones = [
            ("091123456", "+374 91 123 456"),
            ("077-88-99-00", "+374 77 889 900"),
            ("+37493112233", "+374 93 112 233"),
            ("041 55 66 77", "+374 41 556 677")
        ]
        for raw, expected in phones:
            self.assertEqual(normalize_phone_number(raw), expected)

    def test_phone_extraction_multiple(self):
        text = "Հարցերի համար զանգահարել 091-123-456 կամ 093 11 22 33:"
        details = extract_housing_details(text)
        self.assertIn("+374 91 123 456", details["phone_numbers"])
        self.assertIn("+374 93 112 233", details["phone_numbers"])

    def test_empty_or_media_only_details(self):
        empty_res = extract_housing_details("")
        self.assertFalse(empty_res["has_text"])
        self.assertEqual(empty_res["property_category"], "General / Unclassified")

        media_res = extract_housing_details("", is_media_only=True)
        self.assertTrue(media_res["is_media_only"])
        self.assertEqual(media_res["property_category"], "Media-Only")


if __name__ == "__main__":
    unittest.main()
