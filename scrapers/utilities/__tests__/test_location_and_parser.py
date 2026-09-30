# scrapers/utilities/__tests__/test_location_and_parser.py
import os
import sys
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scrapers.utilities.housing_parser import (
    extract_housing_details,
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
