import os
import pandas as pd
import re
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
from collections import defaultdict
import json

from .language_codes import convert_lang_code, detect_lang_code_format, is_google_supported

@dataclass
class Term:
    id: int
    term: str
    translation: str
    domain: str
    language: str
    google_lang_code: str  # Add Google-compatible language code

class TerminologyManager:
    def __init__(self, terminologies_dir: str = None):
        """Initialize terminology manager.
        
        Args:
            terminologies_dir: Directory containing terminology CSV files.
                               Defaults to package's terminologies directory.
        """
        if terminologies_dir is None:
            # Default to package directory
            current_dir = os.path.dirname(os.path.abspath(__file__))
            self.terminologies_dir = os.path.join(current_dir, 'terminologies')
        else:
            self.terminologies_dir = terminologies_dir
            
        self.terms_by_domain_lang = defaultdict(dict)
        self.domains_languages = set()
        self.available_google_languages = set()
        self._load_terminologies()
    
    def _load_terminologies(self):
        """Load all terminology files from the terminologies directory."""
        if not os.path.exists(self.terminologies_dir):
            raise FileNotFoundError(
                f"Terminologies directory not found: {self.terminologies_dir}"
            )
        
        # Pattern for terminology files: {domain}_terms_{language}.csv
        pattern = re.compile(r'(.+)_terms_(.+)\.csv$')
        
        for filename in os.listdir(self.terminologies_dir):
            match = pattern.match(filename)
            if match:
                domain, language = match.groups()
                
                # Convert language code to Google format
                google_lang_code = convert_lang_code(language, to_google=True)
                
                # Check if Google Translate supports this language
                if not is_google_supported(language):
                    print(f"Warning: Language '{language}' may not be fully supported by Google Translate")
                    print(f"  Using code: '{google_lang_code}' for Google Translate")
                
                self.domains_languages.add((domain, language))
                self.available_google_languages.add(google_lang_code)
                
                filepath = os.path.join(self.terminologies_dir, filename)
                df = pd.read_csv(filepath)
                
                # Create a dictionary of terms for quick lookup
                terms_dict = {}
                for _, row in df.iterrows():
                    term_id = int(row['id'])
                    term = Term(
                        id=term_id,
                        term=str(row['term']).lower().strip(),
                        translation=str(row['translation']),
                        domain=domain,
                        language=language,
                        google_lang_code=google_lang_code
                    )
                    terms_dict[term.term] = term
                
                self.terms_by_domain_lang[(domain, language)] = terms_dict
    
    def get_available_domains_languages(self) -> List[Tuple[str, str]]:
        """Get list of available (domain, language) pairs."""
        return sorted(self.domains_languages)
    
    def get_available_domains_languages_google(self) -> List[Tuple[str, str]]:
        """Get list of available (domain, language) pairs with Google language codes."""
        result = []
        for domain, lang in self.domains_languages:
            google_lang = convert_lang_code(lang, to_google=True)
            result.append((domain, google_lang))
        return sorted(result)
    
    def get_domains(self) -> List[str]:
        """Get list of available domains."""
        return sorted({d for d, _ in self.domains_languages})
    
    def get_languages(self, format: str = 'original') -> List[str]:
        """Get list of available languages.
        
        Args:
            format: 'original' for original codes, 'google' for Google codes
        """
        languages = {l for _, l in self.domains_languages}
        
        if format == 'google':
            return sorted({convert_lang_code(l, to_google=True) for l in languages})
        else:
            return sorted(languages)
    
    def get_terms_for_domain_lang(self, domain: str, language: str) -> Dict[str, Term]:
        """Get all terms for a specific domain and language.
        
        Args:
            domain: Domain name
            language: Language code (can be 2-letter or 3-letter)
        """
        # Try exact match first
        if (domain, language) in self.terms_by_domain_lang:
            return self.terms_by_domain_lang[(domain, language)]
        
        # If language is 2-letter, try to find matching 3-letter code
        if len(language) == 2:
            for (d, l), terms in self.terms_by_domain_lang.items():
                if d == domain and convert_lang_code(l, to_google=True) == language:
                    return terms
        
        # If language is 3-letter, try to convert to Google code and find
        if len(language) == 3:
            google_code = convert_lang_code(language, to_google=True)
            for (d, l), terms in self.terms_by_domain_lang.items():
                if d == domain and convert_lang_code(l, to_google=True) == google_code:
                    return terms
        
        return {}
    
    def get_google_lang_code(self, language: str) -> str:
        """Get Google-compatible language code for a given language code."""
        return convert_lang_code(language, to_google=True)
    
    def preprocess_text(self, text: str, domain: str, language: str) -> Tuple[str, Dict[str, Term]]:
        """Replace terms in text with their IDs.
        
        Args:
            text: Input text
            domain: Domain name
            language: Target language (2-letter or 3-letter code)
            
        Returns:
            Tuple of (preprocessed_text, id_to_term_mapping)
        """
        terms_dict = self.get_terms_for_domain_lang(domain, language)
        if not terms_dict:
            # Try to find if domain exists with different language code
            available_domains = self.get_domains()
            if domain in available_domains:
                available_langs = [l for d, l in self.domains_languages if d == domain]
                raise ValueError(
                    f"No terminology found for domain '{domain}' and language '{language}'. "
                    f"Available languages for '{domain}': {available_langs}"
                )
            else:
                raise ValueError(
                    f"Domain '{domain}' not found. Available domains: {available_domains}"
                )
        
        # Sort terms by length (longest first) to handle compound terms
        sorted_terms = sorted(terms_dict.values(), key=lambda x: len(x.term), reverse=True)
        
        preprocessed_text = text
        replacements = {}  # Map of placeholder to term
        
        for term_obj in sorted_terms:
            # Case-insensitive replacement with word boundaries
            pattern = re.compile(r'\b' + re.escape(term_obj.term) + r'\b', re.IGNORECASE)
            
            def replace_with_placeholder(match):
                placeholder = f"<{term_obj.id}>"
                replacements[placeholder] = term_obj
                return placeholder
            
            preprocessed_text = pattern.sub(replace_with_placeholder, preprocessed_text)
        
        return preprocessed_text, replacements
    
    def postprocess_text(self, text: str, replacements: Dict[str, Term]) -> str:
        """Replace IDs in translated text with their translations.
        
        Args:
            text: Translated text with placeholders
            replacements: Mapping from placeholders to Term objects
            
        Returns:
            Postprocessed text with actual translations
        """
        for placeholder, term_obj in replacements.items():
            text = text.replace(placeholder, term_obj.translation)
        return text
