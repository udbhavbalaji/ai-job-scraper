import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException

class LinkedinScraper: 
    def __init__(self, headless=True) -> None: 
        self.headless = headless
        self.driver = None
    
    def setup_driver(self):
        """Setup Chrome WebDriver with stealth options"""
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument('--headless=new')
        
        # Stealth options
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    def get_job_text(self, url):
        """Extract complete job posting text"""
        if not self.driver:
            self.setup_driver()
        
        print(f"🔍 Fetching job posting from: {url}")
        
        # Navigate to job page
        self.driver.get(url)
        time.sleep(3)
        
        # Click "Show more" buttons to expand all content
        self.expand_all_content()
        
        # Extract all job-related text
        job_text = self.extract_complete_text()
        
        return {
            'url': url,
            'job_id': self.extract_job_id(url),
            'raw_text': job_text,
            'word_count': len(job_text.split()),
            'char_count': len(job_text)
        }

    def expand_all_content(self):
        """Click all 'Show more' buttons to expand full content"""
        show_more_selectors = [
            '.show-more-less-html__button--more',
            'button[aria-label="Click to see more description"]',
            '.show-more-less-html__button[aria-expanded="false"]',
            '.jobs-description-content__footer button',
            'button:contains("Show more")',
            'button:contains("See more")'
        ]
        
        for selector in show_more_selectors:
            try:
                buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for button in buttons:
                    if button.is_displayed() and button.is_enabled():
                        print("🔽 Expanding content...")
                        self.driver.execute_script("arguments[0].click();", button)
                        time.sleep(1)
            except Exception:
                continue
        
        # Wait a bit for content to load after expansion
        time.sleep(3)
    
    def extract_complete_text(self):
        """Extract all job posting text"""
        job_text_parts = []
        
        # 1. Get job title
        title_selectors = [
            'h1.top-card-layout__title',
            'h1.topcard__title',
            '.job-details-jobs-unified-top-card__job-title h1',
            'h1'
        ]
        title = self.get_text_from_selectors(title_selectors)
        if title:
            job_text_parts.append(f"Job Title: {title}")
        
        # 2. Get company name
        company_selectors = [
            '.topcard__org-name-link',
            '.job-details-jobs-unified-top-card__company-name a',
            'a[data-tracking-control-name="public_jobs_topcard_org_name"]',
            '.topcard__flavor--black-link'
        ]
        company = self.get_text_from_selectors(company_selectors)
        if company:
            job_text_parts.append(f"Company: {company}")
        
        # 3. Get location
        location_selectors = [
            '.topcard__flavor--bullet',
            '.job-details-jobs-unified-top-card__primary-description-without-see-more'
        ]
        location = self.get_text_from_selectors(location_selectors)
        if location:
            job_text_parts.append(f"Location: {location}")
        
        # 4. Get job criteria/metadata (employment type, experience level, etc.)
        criteria_selectors = [
            '.job-details-jobs-unified-top-card__job-insight',
            '.job-criteria__text',
            '.jobs-unified-top-card__job-insight'
        ]
        
        criteria_texts = []
        for selector in criteria_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    text = element.text.strip()
                    if text and text not in criteria_texts:
                        criteria_texts.append(text)
            except:
                continue
        
        if criteria_texts:
            job_text_parts.append("Job Details: " + " | ".join(criteria_texts))
        
        # 5. Get the main job description (this is the most important part)
        description = self.get_full_job_description()
        if description:
            job_text_parts.append(f"Job Description:\n{description}")

        print(f"📝 Extracted job text: {job_text_parts}")
        
        # Combine all parts
        return "\n\n".join(job_text_parts)
    
    def get_full_job_description(self):
        """Get the complete job description text"""
        description_selectors = [
            '.show-more-less-html__markup',
            '.jobs-description__content',
            '.jobs-description-content__text',
            '.jobs-box__html-content',
            '.description__text'
        ]
        
        for selector in description_selectors:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                
                # Method 1: Get all text content preserving structure
                description_text = self.extract_structured_text(element)
                if description_text and len(description_text) > 100:
                    return description_text
                
                # Method 2: Fallback to simple text extraction
                text = element.text.strip()
                if text and len(text) > 100:
                    return text
                    
            except NoSuchElementException:
                continue
        
        return ""
    
    def extract_structured_text(self, element):
        """Extract text while preserving some structure"""
        try:
            # Get all text nodes, preserving line breaks for lists and paragraphs
            script = """
            function getTextWithStructure(element) {
                let text = '';
                let walker = document.createTreeWalker(
                    element,
                    NodeFilter.SHOW_TEXT,
                    null,
                    false
                );
                
                let node;
                let lastElement = null;
                
                while (node = walker.nextNode()) {
                    let parentElement = node.parentElement;
                    let nodeText = node.textContent.trim();
                    
                    if (nodeText) {
                        // Add spacing based on parent element type
                        if (lastElement && lastElement !== parentElement) {
                            let parentTag = parentElement.tagName.toLowerCase();
                            if (['p', 'div', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'].includes(parentTag)) {
                                text += '\\n';
                            }
                        }
                        
                        text += nodeText + ' ';
                        lastElement = parentElement;
                    }
                }
                
                return text.trim();
            }
            
            return getTextWithStructure(arguments[0]);
            """
            
            structured_text = self.driver.execute_script(script, element)
            
            # Clean up the text
            if structured_text:
                # Remove excessive whitespace while preserving paragraph breaks
                structured_text = re.sub(r' +', ' ', structured_text)
                structured_text = re.sub(r'\n +', '\n', structured_text)
                structured_text = re.sub(r'\n{3,}', '\n\n', structured_text)
                return structured_text.strip()
                
        except Exception:
            pass
        
        # Fallback to simple text extraction
        return element.text.strip()
    
    def get_text_from_selectors(self, selectors):
        """Try multiple selectors and return first found text"""
        for selector in selectors:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                text = element.text.strip()
                if text:
                    return text
            except NoSuchElementException:
                continue
        return ""
    
    def extract_job_id(self, url):
        """Extract job ID from LinkedIn URL"""
        match = re.search(r'/jobs/view/(\d+)', url)
        return match.group(1) if match else ""
    
    def close(self):
        """Close the webdriver"""
        if self.driver:
            self.driver.quit()

