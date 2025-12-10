import asyncio
import logging
from typing import Optional, Dict, Any

from googletrans import Translator as GoogleTranslator
from .terminology_manager import TerminologyManager
from .language_codes import convert_lang_code, is_google_supported

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TCTranslator:
    def __init__(self, domain: str, target_lang: str, 
                 src_lang: str = 'en', terminologies_dir: str = None):
        """
        Initialize Terminology-Controlled Translator.
        
        Args:
            domain: Domain name (e.g., 'agric', 'science')
            target_lang: Target language code (e.g., 'twi' or 'ak')
            src_lang: Source language code (default: 'en')
            terminologies_dir: Custom directory for terminology files
        """
        self.domain = domain
        self.target_lang = target_lang
        self.src_lang = src_lang
        
        # Initialize terminology manager
        self.terminology_manager = TerminologyManager(terminologies_dir)
        
        # Convert language codes to Google format
        self.src_lang_google = convert_lang_code(src_lang, to_google=True)
        self.target_lang_google = self.terminology_manager.get_google_lang_code(target_lang)
        
        # Check if Google Translate supports these languages
        if not is_google_supported(src_lang):
            logger.warning(f"Source language '{src_lang}' may not be supported by Google Translate")
        
        if not is_google_supported(target_lang):
            logger.warning(f"Target language '{target_lang}' may not be supported by Google Translate")
        
        # Verify domain and language are available
        available = self.terminology_manager.get_available_domains_languages()
        
        # Check if the requested domain/language combination exists
        domain_lang_exists = False
        original_target_lang = None
        
        for d, l in available:
            if d == domain:
                # Check if target_lang matches either original or Google code
                google_l = convert_lang_code(l, to_google=True)
                if target_lang == l or target_lang == google_l:
                    domain_lang_exists = True
                    original_target_lang = l
                    break
        
        if not domain_lang_exists:
            # Find what's actually available
            available_for_domain = [l for d, l in available if d == domain]
            raise ValueError(
                f"Domain '{domain}' with language '{target_lang}' not found.\n"
                f"Available languages for '{domain}': {available_for_domain}\n"
                f"Note: You can use either 2-letter (Google) or 3-letter codes"
            )
        
        # Store the original language code from terminology file
        self.original_target_lang = original_target_lang
    
    async def _translate_async(self, text: str, **kwargs) -> Dict[str, Any]:
        """
        Internal async translation method.
        
        Args:
            text: Text to translate
            **kwargs: Additional arguments for Google Translate
            
        Returns:
            Dictionary with translation results
        """
        # Step 1: Preprocess - replace terms with IDs
        preprocessed_text, replacements = self.terminology_manager.preprocess_text(
            text, self.domain, self.original_target_lang
        )
        
        logger.debug(f"Preprocessed text: {preprocessed_text}")
        logger.debug(f"Replacements: {list(replacements.keys())}")
        logger.debug(f"Source language (Google): {self.src_lang_google}")
        logger.debug(f"Target language (Google): {self.target_lang_google}")
        
        # Step 2: Translate with Google Translate (async)
        try:
            # Create translator instance INSIDE the async context
            async with GoogleTranslator() as translator:
                google_result = await translator.translate(
                    preprocessed_text,
                    src=self.src_lang_google,
                    dest=self.target_lang_google,
                    **kwargs
                )
                
                translated_with_placeholders = google_result.text
                
                # Step 3: Postprocess - replace IDs with translations
                final_text = self.terminology_manager.postprocess_text(
                    translated_with_placeholders,
                    replacements
                )
                
                return {
                    'text': final_text,
                    'src': self.src_lang,
                    'dest': self.target_lang,
                    'original_dest': self.original_target_lang,
                    'domain': self.domain,
                    'original': text,
                    'preprocessed': preprocessed_text,
                    'google_translation': google_result.text,
                    'replacements_count': len(replacements),
                    'src_google': self.src_lang_google,
                    'dest_google': self.target_lang_google
                }
                
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            raise
    
    def translate(self, text: str, **kwargs) -> Dict[str, Any]:
        """
        Translate text with terminology control.
        
        Args:
            text: Text to translate
            **kwargs: Additional arguments for Google Translate
            
        Returns:
            Dictionary with translation results
        """
        # Use the same pattern as your working example
        try:
            # Try to get the existing event loop
            loop = asyncio.get_event_loop()
            
            # If we're in Jupyter/Colab with a running loop
            if loop.is_running():
                # Create a new task in the existing loop
                future = asyncio.run_coroutine_threadsafe(
                    self._translate_async(text, **kwargs), 
                    loop
                )
                return future.result(timeout=30)  # 30 second timeout
            else:
                # We're in a regular Python environment
                return asyncio.run(self._translate_async(text, **kwargs))
                
        except RuntimeError:
            # No event loop, create one
            return asyncio.run(self._translate_async(text, **kwargs))
        except TimeoutError:
            logger.error("Translation timed out after 30 seconds")
            raise
    
    async def batch_translate(self, texts: list, **kwargs) -> list:
        """Translate multiple texts asynchronously."""
        # Process one at a time to avoid rate limiting
        results = []
        for text in texts:
            result = await self._translate_async(text, **kwargs)
            results.append(result)
            # Small delay between requests
            await asyncio.sleep(0.1)
        return results
    
    def batch_translate_sync(self, texts: list, **kwargs) -> list:
        """Synchronous wrapper for batch translation."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                future = asyncio.run_coroutine_threadsafe(
                    self.batch_translate(texts, **kwargs), 
                    loop
                )
                return future.result(timeout=300)  # 5 minute timeout for batch
            else:
                return asyncio.run(self.batch_translate(texts, **kwargs))
        except RuntimeError:
            return asyncio.run(self.batch_translate(texts, **kwargs))
        except TimeoutError:
            logger.error("Batch translation timed out after 5 minutes")
            raise

# Google Translate-like API wrapper
class Translator:
    """Google Translate-like API with terminology control."""
    
    def __init__(self, terminologies_dir: str = None):
        self.terminology_manager = TerminologyManager(terminologies_dir)
        self.terminologies_dir = terminologies_dir
    
    async def _translate_async(self, text: str, src: str = 'en', dest: str = 'twi', 
                              domain: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Internal async translation method.
        """
        if domain:
            # Use terminology-controlled translation
            tc_translator = TCTranslator(
                domain=domain,
                target_lang=dest,
                src_lang=src,
                terminologies_dir=self.terminologies_dir
            )
            return await tc_translator._translate_async(text, **kwargs)
        else:
            # Use regular Google Translate (async)
            async with GoogleTranslator() as translator:
                src_google = convert_lang_code(src, to_google=True)
                dest_google = convert_lang_code(dest, to_google=True)
                
                result = await translator.translate(
                    text, 
                    src=src_google, 
                    dest=dest_google, 
                    **kwargs
                )
                return {
                    'text': result.text,
                    'src': src,
                    'dest': dest,
                    'src_google': src_google,
                    'dest_google': dest_google,
                    'original': text
                }
    
    def translate(self, text: str, src: str = 'en', dest: str = 'twi', 
                 domain: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Translate text with optional terminology control.
        
        Args:
            text: Text to translate
            src: Source language (2-letter or 3-letter)
            dest: Destination language (2-letter or 3-letter)
            domain: Domain for terminology control (optional)
            **kwargs: Additional arguments
            
        Returns:
            Dictionary with translation results
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                future = asyncio.run_coroutine_threadsafe(
                    self._translate_async(text, src, dest, domain, **kwargs), 
                    loop
                )
                return future.result(timeout=30)
            else:
                return asyncio.run(self._translate_async(text, src, dest, domain, **kwargs))
        except RuntimeError:
            return asyncio.run(self._translate_async(text, src, dest, domain, **kwargs))
        except TimeoutError:
            logger.error("Translation timed out after 30 seconds")
            raise
    
    async def detect_async(self, text: str):
        """Detect language of text."""
        async with GoogleTranslator() as translator:
            return await translator.detect(text)
    
    def detect(self, text: str):
        """Synchronous language detection."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                future = asyncio.run_coroutine_threadsafe(
                    self.detect_async(text), 
                    loop
                )
                return future.result(timeout=10)
            else:
                return asyncio.run(self.detect_async(text))
        except RuntimeError:
            return asyncio.run(self.detect_async(text))
        except TimeoutError:
            logger.error("Language detection timed out")
            raise
