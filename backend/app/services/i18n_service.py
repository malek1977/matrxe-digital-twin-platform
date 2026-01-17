"""
Internationalization Service for MATRXe
"""

import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json
import os
from babel import Locale
from deep_translator import GoogleTranslator

from app.models.i18n import Language, Translation, MultilingualContent
from app.core.config import settings

logger = logging.getLogger(__name__)

class I18nService:
    """
    Internationalization service for multi-language support
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.supported_languages = settings.SUPPORTED_LANGUAGES
        self.default_language = settings.DEFAULT_LANGUAGE
        
        # Load translations cache
        self.translations_cache = {}
        
    async def initialize(self):
        """Initialize i18n service"""
        await self.load_translations()
        logger.info(f"I18n service initialized with languages: {self.supported_languages}")
    
    async def load_translations(self):
        """Load all translations into cache"""
        try:
            stmt = select(Translation)
            result = await self.db.execute(stmt)
            translations = result.scalars().all()
            
            for trans in translations:
                lang = trans.language_code
                if lang not in self.translations_cache:
                    self.translations_cache[lang] = {}
                self.translations_cache[lang][trans.key] = trans.value
            
            logger.info(f"Loaded {len(translations)} translations")
            
        except Exception as e:
            logger.error(f"Failed to load translations: {e}")
    
    async def get_translation(
        self, 
        key: str, 
        language_code: str = None,
        default: str = None,
        variables: Dict[str, Any] = None
    ) -> str:
        """
        Get translation for a key
        """
        try:
            lang = language_code or self.default_language
            
            # Check cache
            if lang in self.translations_cache and key in self.translations_cache[lang]:
                translation = self.translations_cache[lang][key]
            else:
                # Try to get from database
                stmt = select(Translation).where(
                    Translation.key == key,
                    Translation.language_code == lang
                )
                result = await self.db.execute(stmt)
                translation_obj = result.scalar_one_or_none()
                
                if translation_obj:
                    translation = translation_obj.value
                    # Update cache
                    if lang not in self.translations_cache:
                        self.translations_cache[lang] = {}
                    self.translations_cache[lang][key] = translation
                else:
                    # Fallback to default language
                    if lang != self.default_language:
                        return await self.get_translation(key, self.default_language, default, variables)
                    
                    # Return default or key
                    translation = default or key
            
            # Replace variables if provided
            if variables and translation:
                for var_name, var_value in variables.items():
                    translation = translation.replace(f"{{{var_name}}}", str(var_value))
            
            return translation
            
        except Exception as e:
            logger.error(f"Failed to get translation: {e}")
            return default or key
    
    async def translate_text(
        self,
        text: str,
        source_lang: str = "auto",
        target_lang: str = None,
        use_cache: bool = True
    ) -> str:
        """
        Translate text using Google Translate
        """
        try:
            if not target_lang:
                target_lang = self.default_language
            
            if source_lang == target_lang:
                return text
            
            # Check cache first
            cache_key = f"{source_lang}:{target_lang}:{hash(text)}"
            if use_cache and cache_key in self.translations_cache.get('_translations', {}):
                return self.translations_cache['_translations'][cache_key]
            
            # Use Google Translate
            translator = GoogleTranslator(source=source_lang, target=target_lang)
            translated = translator.translate(text)
            
            # Update cache
            if '_translations' not in self.translations_cache:
                self.translations_cache['_translations'] = {}
            self.translations_cache['_translations'][cache_key] = translated
            
            return translated
            
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return text
    
    async def get_supported_languages(self) -> List[Dict[str, Any]]:
        """Get list of supported languages"""
        try:
            stmt = select(Language).where(Language.is_active == True)
            result = await self.db.execute(stmt)
            languages = result.scalars().all()
            
            return [
                {
                    "code": lang.code,
                    "name": lang.name,
                    "native_name": lang.native_name,
                    "direction": lang.direction,
                    "flag_emoji": lang.flag_emoji,
                    "is_active": lang.is_active
                }
                for lang in languages
            ]
            
        except Exception as e:
            logger.error(f"Failed to get supported languages: {e}")
            return []
    
    async def set_user_language(self, user_id: str, language_code: str) -> bool:
        """Set user's preferred language"""
        try:
            # Update user's language preference in database
            from app.models.user import User
            stmt = select(User).where(User.id == user_id)
            result = await self.db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if user:
                user.language_code = language_code
                await self.db.commit()
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to set user language: {e}")
            await self.db.rollback()
            return False
    
    async def get_user_language(self, user_id: str) -> str:
        """Get user's preferred language"""
        try:
            from app.models.user import User
            stmt = select(User).where(User.id == user_id)
            result = await self.db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if user and user.language_code:
                return user.language_code
            
            return self.default_language
            
        except Exception as e:
            logger.error(f"Failed to get user language: {e}")
            return self.default_language
    
    async def detect_language(self, text: str) -> Dict[str, Any]:
        """Detect language of text"""
        try:
            from langdetect import detect, detect_langs, LangDetectException
            
            try:
                detected_lang = detect(text)
                probabilities = detect_langs(text)
                
                return {
                    "detected_language": detected_lang,
                    "confidence": max([p.prob for p in probabilities]) if probabilities else 0.0,
                    "probabilities": [
                        {"language": p.lang, "probability": p.prob}
                        for p in probabilities
                    ]
                }
            except LangDetectException:
                return {
                    "detected_language": "unknown",
                    "confidence": 0.0,
                    "probabilities": []
                }
                
        except ImportError:
            logger.warning("langdetect not installed")
            return {
                "detected_language": "unknown",
                "confidence": 0.0,
                "probabilities": []
            }
        except Exception as e:
            logger.error(f"Language detection failed: {e}")
            return {
                "detected_language": "unknown",
                "confidence": 0.0,
                "probabilities": []
            }
    
    async def get_multilingual_content(
        self,
        content_key: str,
        language_code: str = None
    ) -> Dict[str, Any]:
        """Get multilingual content by key"""
        try:
            stmt = select(MultilingualContent).where(
                MultilingualContent.content_key == content_key
            )
            result = await self.db.execute(stmt)
            content = result.scalar_one_or_none()
            
            if not content:
                return {}
            
            lang = language_code or self.default_language
            
            # Get content in requested language
            content_field = f"content_{lang}"
            if hasattr(content, content_field):
                text = getattr(content, content_field)
            else:
                # Fallback to default language
                content_field = f"content_{self.default_language}"
                text = getattr(content, content_field, "")
            
            return {
                "content_key": content.content_key,
                "content_type": content.content_type,
                "text": text,
                "language": lang,
                "context": content.context,
                "page": content.page,
                "is_active": content.is_active
            }
            
        except Exception as e:
            logger.error(f"Failed to get multilingual content: {e}")
            return {}
    
    async def update_translation(
        self,
        key: str,
        language_code: str,
        value: str,
        context: str = None
    ) -> bool:
        """Update or create translation"""
        try:
            # Check if translation exists
            stmt = select(Translation).where(
                Translation.key == key,
                Translation.language_code == language_code
            )
            result = await self.db.execute(stmt)
            translation = result.scalar_one_or_none()
            
            if translation:
                translation.value = value
                if context:
                    translation.context = context
            else:
                translation = Translation(
                    key=key,
                    language_code=language_code,
                    value=value,
                    context=context
                )
                self.db.add(translation)
            
            await self.db.commit()
            
            # Update cache
            if language_code not in self.translations_cache:
                self.translations_cache[language_code] = {}
            self.translations_cache[language_code][key] = value
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update translation: {e}")
            await self.db.rollback()
            return False
    
    async def bulk_translate(
        self,
        texts: List[str],
        source_lang: str = "auto",
        target_lang: str = None
    ) -> List[str]:
        """Translate multiple texts at once"""
        try:
            if not target_lang:
                target_lang = self.default_language
            
            if source_lang == target_lang:
                return texts
            
            # Group texts for batch translation
            batch_size = 50  # Google Translate batch limit
            results = []
            
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                batch_results = []
                
                for text in batch:
                    translated = await self.translate_text(
                        text=text,
                        source_lang=source_lang,
                        target_lang=target_lang
                    )
                    batch_results.append(translated)
                
                results.extend(batch_results)
            
            return results
            
        except Exception as e:
            logger.error(f"Bulk translation failed: {e}")
            return texts
    
    async def get_language_info(self, language_code: str) -> Dict[str, Any]:
        """Get detailed language information"""
        try:
            stmt = select(Language).where(Language.code == language_code)
            result = await self.db.execute(stmt)
            language = result.scalar_one_or_none()
            
            if not language:
                # Try to get info from Babel
                try:
                    locale = Locale.parse(language_code)
                    return {
                        "code": language_code,
                        "name": locale.display_name,
                        "native_name": locale.get_display_name(language_code),
                        "direction": "rtl" if language_code in ["ar", "he", "fa", "ur"] else "ltr",
                        "flag_emoji": self._get_flag_emoji(language_code),
                        "is_active": language_code in self.supported_languages
                    }
                except:
                    return {
                        "code": language_code,
                        "name": language_code.upper(),
                        "native_name": language_code.upper(),
                        "direction": "ltr",
                        "flag_emoji": "🌐",
                        "is_active": False
                    }
            
            return {
                "code": language.code,
                "name": language.name,
                "native_name": language.native_name,
                "direction": language.direction,
                "flag_emoji": language.flag_emoji,
                "is_active": language.is_active
            }
            
        except Exception as e:
            logger.error(f"Failed to get language info: {e}")
            return {
                "code": language_code,
                "name": language_code.upper(),
                "native_name": language_code.upper(),
                "direction": "ltr",
                "flag_emoji": "🌐",
                "is_active": False
            }
    
    def _get_flag_emoji(self, language_code: str) -> str:
        """Get flag emoji for language code"""
        flag_map = {
            'ar': '🇸🇦',  # Saudi Arabia
            'en': '🇺🇸',  # United States
            'fr': '🇫🇷',  # France
            'es': '🇪🇸',  # Spain
            'de': '🇩🇪',  # Germany
            'ru': '🇷🇺',  # Russia
            'tr': '🇹🇷',  # Turkey
            'ur': '🇵🇰',  # Pakistan
            'zh': '🇨🇳',  # China
            'ja': '🇯🇵',  # Japan
            'ko': '🇰🇷',  # Korea
            'hi': '🇮🇳',  # India
            'pt': '🇵🇹',  # Portugal
            'it': '🇮🇹',  # Italy
        }
        
        return flag_map.get(language_code, '🌐')
    
    async def export_translations(self, language_code: str = None) -> Dict[str, Any]:
        """Export translations for a language"""
        try:
            if language_code:
                stmt = select(Translation).where(Translation.language_code == language_code)
            else:
                stmt = select(Translation)
            
            result = await self.db.execute(stmt)
            translations = result.scalars().all()
            
            # Group by language
            export_data = {}
            for trans in translations:
                lang = trans.language_code
                if lang not in export_data:
                    export_data[lang] = {}
                export_data[lang][trans.key] = {
                    "value": trans.value,
                    "context": trans.context
                }
            
            return export_data
            
        except Exception as e:
            logger.error(f"Failed to export translations: {e}")
            return {}
    
    async def import_translations(self, import_data: Dict[str, Any]) -> Dict[str, int]:
        """Import translations from data"""
        try:
            stats = {
                "added": 0,
                "updated": 0,
                "skipped": 0,
                "errors": 0
            }
            
            for language_code, translations in import_data.items():
                # Check if language is supported
                if language_code not in self.supported_languages:
                    stats["skipped"] += len(translations)
                    continue
                
                for key, data in translations.items():
                    try:
                        value = data.get("value", "")
                        context = data.get("context")
                        
                        success = await self.update_translation(
                            key=key,
                            language_code=language_code,
                            value=value,
                            context=context
                        )
                        
                        if success:
                            stats["updated"] += 1
                        else:
                            stats["errors"] += 1
                            
                    except Exception as e:
                        logger.error(f"Failed to import translation {key}: {e}")
                        stats["errors"] += 1
            
            await self.db.commit()
            await self.load_translations()  # Reload cache
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to import translations: {e}")
            await self.db.rollback()
            return {
                "added": 0,
                "updated": 0,
                "skipped": 0,
                "errors": 1
            }
    
    async def generate_translation_keys(self, content: str) -> List[str]:
        """Generate translation keys from content"""
        try:
            # Extract text that needs translation
            # This is a simplified version - in production, use proper parsing
            import re
            
            # Look for text patterns that might need translation
            patterns = [
                r'"([^"\\]*(?:\\.[^"\\]*)*)"',  # Double quoted strings
                r"'([^'\\]*(?:\\.[^'\\]*)*)'",  # Single quoted strings
                r'<trans>([^<]+)</trans>',      # Custom tags
            ]
            
            keys = []
            for pattern in patterns:
                matches = re.findall(pattern, content)
                keys.extend(matches)
            
            # Clean and deduplicate keys
            cleaned_keys = []
            seen = set()
            for key in keys:
                key = key.strip()
                if key and key not in seen and len(key) > 3:  # Minimum length
                    cleaned_keys.append(key)
                    seen.add(key)
            
            return cleaned_keys
            
        except Exception as e:
            logger.error(f"Failed to generate translation keys: {e}")
            return []
    
    async def health_check(self) -> Dict[str, Any]:
        """Check i18n service health"""
        try:
            # Check database connection
            stmt = select(Language).limit(1)
            result = await self.db.execute(stmt)
            languages = result.scalars().all()
            
            # Check translation cache
            cache_status = {
                "cached_languages": len(self.translations_cache),
                "total_translations": sum(len(v) for v in self.translations_cache.values())
            }
            
            return {
                "status": "healthy",
                "supported_languages": self.supported_languages,
                "default_language": self.default_language,
                "database_connected": len(languages) >= 0,
                "cache_status": cache_status,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"I18n health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }