import unittest
import tempfile
import os
import pandas as pd
from tc_translate import TCTranslator, TerminologyManager

class TestTCTranslator(unittest.TestCase):
    
    def setUp(self):
        # Create a temporary directory for test terminology files
        self.temp_dir = tempfile.mkdtemp()
        
        # Create a test terminology file
        test_data = pd.DataFrame({
            'id': [1, 2, 3],
            'term': ['abattoir', 'acreage', 'acaricide'],
            'translation': ['test_trans1', 'test_trans2', 'test_trans3']
        })
        
        test_file = os.path.join(self.temp_dir, 'test_terms_twi.csv')
        test_data.to_csv(test_file, index=False)
    
    def test_terminology_loading(self):
        """Test that terminologies are loaded correctly."""
        manager = TerminologyManager(self.temp_dir)
        
        # Check that domain/language pair was detected
        self.assertIn(('test', 'twi'), manager.get_available_domains_languages())
        
        # Check terms were loaded
        terms = manager.get_terms_for_domain_lang('test', 'twi')
        self.assertEqual(len(terms), 3)
        self.assertIn('abattoir', terms)
    
    def test_preprocess_text(self):
        """Test text preprocessing with term replacement."""
        manager = TerminologyManager(self.temp_dir)
        
        text = "The abattoir and acreage are important."
        preprocessed, replacements = manager.preprocess_text(text, 'test', 'twi')
        
        # Check that placeholders were inserted
        self.assertIn('<1>', preprocessed)
        self.assertIn('<2>', preprocessed)
        
        # Check replacements mapping
        self.assertEqual(len(replacements), 2)
        self.assertIn('<1>', replacements)
        self.assertIn('<2>', replacements)
    
    def test_postprocess_text(self):
        """Test text postprocessing with translation insertion."""
        manager = TerminologyManager(self.temp_dir)
        
        # Simulate translated text with placeholders
        translated_text = "The <1> and <2> are important."
        replacements = {
            '<1>': type('obj', (object,), {'translation': 'test_trans1'})(),
            '<2>': type('obj', (object,), {'translation': 'test_trans2'})()
        }
        
        result = manager.postprocess_text(translated_text, replacements)
        self.assertEqual(result, "The test_trans1 and test_trans2 are important.")
    
    def tearDown(self):
        # Clean up temporary directory
        import shutil
        shutil.rmtree(self.temp_dir)

if __name__ == '__main__':
    unittest.main()
