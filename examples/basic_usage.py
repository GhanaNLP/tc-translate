#!/usr/bin/env python3
"""
Basic usage examples for TC Translator
"""

from tc_translate import TCTranslator, Translator
from tc_translate.language_codes import convert_lang_code, get_language_mapping

# Show language code conversion
print("=== Language Code Conversion Examples ===")
languages = ['twi', 'fra', 'deu', 'spa', 'yor']
for lang in languages:
    google_code = convert_lang_code(lang, to_google=True)
    print(f"{lang} (3-letter) → {google_code} (Google)")
print()

# Example 1: Using TCTranslator for agriculture domain with 3-letter code
print("=== Example 1: Agriculture Translation (using 'twi') ===")
agric_translator = TCTranslator(domain='agric', target_lang='twi')

text = "The farmer uses an abattoir and manages his acreage efficiently."
result = agric_translator.translate(text)

print(f"Original: {result['original']}")
print(f"Translated: {result['text']}")
print(f"Source language (Google): {result['src_google']}")
print(f"Target language (Google): {result['dest_google']}")
print(f"Terms replaced: {result['replacements_count']}")
print()

# Example 2: Using TCTranslator with Google's 2-letter code
print("=== Example 2: Agriculture Translation (using 'ak') ===")
agric_translator_ak = TCTranslator(domain='agric', target_lang='ak')

result_ak = agric_translator_ak.translate(text)
print(f"Translated (using 'ak'): {result_ak['text']}")
print(f"Target language (Google): {result_ak['dest_google']}")
print()

# Example 3: Using the Google Translate-like API
print("=== Example 3: Google Translate-like API ===")
translator = Translator()

# With terminology control using 3-letter code
result_with_terms = translator.translate(
    "acaricide and adjuvant are important",
    src='en',
    dest='twi',  # Using 3-letter code
    domain='agric'
)
print(f"With terminology control (twi): {result_with_terms['text']}")

# With terminology control using 2-letter code
result_with_terms_ak = translator.translate(
    "acaricide and adjuvant are important",
    src='en',
    dest='ak',  # Using 2-letter Google code
    domain='agric'
)
print(f"With terminology control (ak): {result_with_terms_ak['text']}")

# Without terminology control (regular Google Translate)
result_without_terms = translator.translate(
    "acaricide and adjuvant are important",
    src='en',
    dest='ak'  # Must use Google's code for regular translation
)
print(f"Without terminology control: {result_without_terms['text']}")
print()

# Example 4: Language code information
print("=== Example 4: Language Code Information ===")
for lang_code in ['twi', 'yor', 'fra', 'deu']:
    info = get_language_mapping(lang_code)
    print(f"{lang_code}: Google code = {info['google_code']}, Supported = {info['supported_by_google']}")
