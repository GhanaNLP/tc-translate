import json
from typing import Dict, List
from .terminology_manager import TerminologyManager
from .language_codes import convert_lang_code

def list_available_options(terminologies_dir: str = None, format: str = 'both') -> Dict:
    """List all available domains and languages.
    
    Args:
        terminologies_dir: Directory with terminology files
        format: 'original', 'google', or 'both'
    """
    manager = TerminologyManager(terminologies_dir)
    
    domains = manager.get_domains()
    original_languages = manager.get_languages(format='original')
    google_languages = manager.get_languages(format='google')
    
    # Group languages by domain
    domains_dict_original = {}
    domains_dict_google = {}
    
    for domain, lang in manager.get_available_domains_languages():
        google_lang = convert_lang_code(lang, to_google=True)
        
        if domain not in domains_dict_original:
            domains_dict_original[domain] = []
        domains_dict_original[domain].append(lang)
        
        if domain not in domains_dict_google:
            domains_dict_google[domain] = []
        domains_dict_google[domain].append(google_lang)
    
    if format == 'original':
        return {
            'domains': domains,
            'languages': original_languages,
            'domains_with_languages': domains_dict_original,
            'language_format': 'iso639-3 (3-letter)'
        }
    elif format == 'google':
        return {
            'domains': domains,
            'languages': google_languages,
            'domains_with_languages': domains_dict_google,
            'language_format': 'iso639-1 (2-letter, Google)'
        }
    else:  # both
        return {
            'domains': domains,
            'languages_original': original_languages,
            'languages_google': google_languages,
            'domains_with_languages_original': domains_dict_original,
            'domains_with_languages_google': domains_dict_google,
            'language_mapping': {
                lang: convert_lang_code(lang, to_google=True) 
                for lang in original_languages
            }
        }

def export_terminology(domain: str, language: str, output_format: str = 'json',
                      terminologies_dir: str = None):
    """Export terminology for a domain and language."""
    manager = TerminologyManager(terminologies_dir)
    terms_dict = manager.get_terms_for_domain_lang(domain, language)
    
    if not terms_dict:
        # Try with Google code
        google_lang = convert_lang_code(language, to_google=True)
        for (d, l), terms in manager.terms_by_domain_lang.items():
            if d == domain and convert_lang_code(l, to_google=True) == google_lang:
                terms_dict = terms
                break
    
    if not terms_dict:
        raise ValueError(f"No terminology found for {domain}/{language}")
    
    terms_list = [
        {
            'id': term.id,
            'term': term.term,
            'translation': term.translation,
            'domain': term.domain,
            'language': term.language,
            'google_language_code': term.google_lang_code
        }
        for term in terms_dict.values()
    ]
    
    if output_format == 'json':
        return json.dumps(terms_list, indent=2, ensure_ascii=False)
    elif output_format == 'csv':
        import csv
        import io
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=['id', 'term', 'translation', 'domain', 'language', 'google_language_code'])
        writer.writeheader()
        writer.writerows(terms_list)
        return output.getvalue()
    
    return terms_list

def get_language_mapping(language: str = None) -> Dict:
    """Get language code mapping information."""
    from .language_codes import LANGUAGE_CODE_MAPPING, convert_lang_code
    
    if language:
        original_format = 'iso639-3' if len(language) == 3 else 'iso639-1'
        google_code = convert_lang_code(language, to_google=True)
        
        return {
            'input': language,
            'input_format': original_format,
            'google_code': google_code,
            'supported_by_google': google_code in convert_lang_code(language, to_google=True)
        }
    else:
        return {
            'mapping': LANGUAGE_CODE_MAPPING,
            'note': 'Keys are 3-letter codes (ISO 639-3), values are Google Translate codes'
        }
