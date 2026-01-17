"""
AI Service for MATRXe Platform
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime
import json

from app.core.config import settings
from app.ai_engine.llm_provider import LLMProvider
from app.ai_engine.voice_cloner import VoiceCloner
from app.ai_engine.face_processor import FaceProcessor
from app.ai_engine.emotion_detector import EmotionDetector

logger = logging.getLogger(__name__)

class AIService:
    """
    Main AI service coordinating all AI operations
    """
    
    def __init__(self):
        self.llm_provider = LLMProvider()
        self.voice_cloner = VoiceCloner()
        self.face_processor = FaceProcessor()
        self.emotion_detector = EmotionDetector()
        
        # Initialize components
        self._initialize()
    
    def _initialize(self):
        """Initialize AI components"""
        try:
            # Load models in background
            asyncio.create_task(self._load_models_async())
            logger.info("AI Service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize AI Service: {e}")
    
    async def _load_models_async(self):
        """Load AI models asynchronously"""
        try:
            await self.llm_provider.load_models()
            await self.voice_cloner.load_models()
            await self.face_processor.load_models()
            await self.emotion_detector.load_models()
            logger.info("All AI models loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load AI models: {e}")
    
    async def train_personality_model(
        self,
        twin_id: uuid.UUID,
        personality_traits: Optional[Dict] = None,
        twin_name: str = "Digital Twin"
    ) -> Dict[str, Any]:
        """
        Train personality model for digital twin
        """
        try:
            logger.info(f"Training personality model for twin: {twin_id}")
            
            # Default personality traits
            default_traits = {
                "communication_style": "friendly",
                "formality_level": "medium",
                "humor_level": 5,
                "empathy_level": 7,
                "creativity_level": 6,
                "detail_oriented": 8,
                "knowledge_domains": ["general"],
                "conversation_topics": ["personal", "professional", "casual"]
            }
            
            # Merge with provided traits
            traits = {**default_traits, **(personality_traits or {})}
            
            # Create personality profile
            personality_profile = {
                "twin_id": str(twin_id),
                "twin_name": twin_name,
                "traits": traits,
                "created_at": datetime.utcnow().isoformat(),
                "training_status": "completed",
                "model_id": f"personality_{twin_id}",
                "chat_model_id": f"chat_{twin_id}"
            }
            
            # Train LLM with personality
            llm_result = await self.llm_provider.train_personality(
                twin_id=twin_id,
                personality_profile=personality_profile
            )
            
            personality_profile.update(llm_result)
            
            logger.info(f"Personality model trained for twin: {twin_id}")
            return personality_profile
            
        except Exception as e:
            logger.error(f"Failed to train personality model: {e}")
            return {
                "error": str(e),
                "training_status": "failed"
            }
    
    async def generate_response(
        self,
        twin_id: uuid.UUID,
        user_message: str,
        conversation_history: List[Dict] = None,
        context: Optional[str] = None,
        emotion: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate AI response for digital twin
        """
        try:
            logger.info(f"Generating response for twin: {twin_id}")
            
            # Detect emotion in user message if not provided
            if not emotion:
                emotion_result = await self.emotion_detector.detect_text_emotion(user_message)
                emotion = emotion_result.get("primary_emotion", "neutral")
            
            # Generate response using LLM
            response = await self.llm_provider.generate_response(
                twin_id=twin_id,
                user_message=user_message,
                conversation_history=conversation_history or [],
                context=context,
                emotion=emotion
            )
            
            # Enhance response with emotions
            enhanced_response = await self._enhance_response_with_emotion(
                response=response["text"],
                emotion=emotion,
                twin_id=twin_id
            )
            
            result = {
                "text": enhanced_response,
                "emotion": emotion,
                "confidence": response.get("confidence", 0.8),
                "tokens_used": response.get("tokens_used", 0),
                "response_time": response.get("response_time", 0),
                "suggested_follow_up": response.get("suggested_follow_up", [])
            }
            
            logger.info(f"Response generated for twin: {twin_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            return {
                "text": "I apologize, but I'm having trouble processing your request. Please try again.",
                "emotion": "neutral",
                "error": str(e)
            }
    
    async def _enhance_response_with_emotion(
        self,
        response: str,
        emotion: str,
        twin_id: uuid.UUID
    ) -> str:
        """
        Enhance response with emotional expressions
        """
        try:
            if emotion in ["happy", "excited", "joyful"]:
                # Add positive expressions
                enhancements = ["Great!", "Wonderful!", "I'm glad to hear that!"]
                import random
                if random.random() > 0.7:
                    response = f"{random.choice(enhancements)} {response}"
            
            elif emotion in ["sad", "disappointed", "frustrated"]:
                # Add empathetic expressions
                enhancements = ["I understand.", "That sounds difficult.", "I'm here for you."]
                import random
                if random.random() > 0.7:
                    response = f"{random.choice(enhancements)} {response}"
            
            elif emotion in ["angry", "annoyed"]:
                # Add calming expressions
                enhancements = ["I hear you.", "Let's work through this.", "I understand your frustration."]
                import random
                if random.random() > 0.7:
                    response = f"{random.choice(enhancements)} {response}"
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to enhance response with emotion: {e}")
            return response
    
    async def generate_voice_response(
        self,
        twin_id: uuid.UUID,
        text: str,
        emotion: str = "neutral"
    ) -> Dict[str, Any]:
        """
        Generate voice response for digital twin
        """
        try:
            logger.info(f"Generating voice response for twin: {twin_id}")
            
            # Get voice model for twin
            voice_model = await self._get_voice_model(twin_id)
            
            if not voice_model:
                return {
                    "success": False,
                    "error": "Voice model not found",
                    "audio_url": None
                }
            
            # Adjust voice parameters based on emotion
            voice_params = self._get_voice_params_for_emotion(emotion)
            
            # Generate voice
            voice_result = await self.voice_cloner.synthesize_speech(
                text=text,
                voice_model=voice_model,
                emotion=emotion,
                parameters=voice_params
            )
            
            if voice_result["success"]:
                logger.info(f"Voice response generated for twin: {twin_id}")
                return {
                    "success": True,
                    "audio_url": voice_result["audio_url"],
                    "duration": voice_result["duration"],
                    "emotion": emotion,
                    "format": "mp3"
                }
            else:
                logger.error(f"Voice generation failed: {voice_result.get('error')}")
                return {
                    "success": False,
                    "error": voice_result.get("error"),
                    "audio_url": None
                }
            
        except Exception as e:
            logger.error(f"Failed to generate voice response: {e}")
            return {
                "success": False,
                "error": str(e),
                "audio_url": None
            }
    
    async def _get_voice_model(self, twin_id: uuid.UUID) -> Optional[Dict]:
        """
        Get voice model for digital twin
        """
        # In production, this would fetch from database
        # For now, return a default model
        return {
            "model_id": f"voice_{twin_id}",
            "voice_name": "Digital Twin",
            "provider": "elevenlabs",
            "voice_id": "pNInz6obpgDQGcFmaJgB"  # Default voice ID
        }
    
    def _get_voice_params_for_emotion(self, emotion: str) -> Dict[str, Any]:
        """
        Get voice parameters based on emotion
        """
        params = {
            "stability": 0.5,
            "similarity_boost": 0.5,
            "style": 0.0,
            "use_speaker_boost": True
        }
        
        emotion_params = {
            "happy": {"stability": 0.3, "style": 0.8},
            "sad": {"stability": 0.7, "style": 0.2},
            "angry": {"stability": 0.4, "style": 0.9},
            "excited": {"stability": 0.2, "style": 0.9},
            "calm": {"stability": 0.8, "style": 0.1},
            "neutral": {"stability": 0.5, "style": 0.5}
        }
        
        if emotion in emotion_params:
            params.update(emotion_params[emotion])
        
        return params
    
    async def process_face_images(
        self,
        twin_id: uuid.UUID,
        image_paths: List[str]
    ) -> Dict[str, Any]:
        """
        Process face images for digital twin
        """
        try:
            logger.info(f"Processing face images for twin: {twin_id}")
            
            # Process images
            face_result = await self.face_processor.process_images(
                image_paths=image_paths,
                twin_id=twin_id
            )
            
            if face_result["success"]:
                # Create face model
                model_result = await self.face_processor.create_face_model(
                    features=face_result["features"],
                    twin_id=twin_id
                )
                
                result = {
                    "success": True,
                    "model_id": model_result.get("model_id"),
                    "features": face_result["features"],
                    "similarity_score": face_result.get("similarity_score", 0.0),
                    "avatar_url": model_result.get("avatar_url"),
                    "processing_time": face_result.get("processing_time", 0)
                }
                
                logger.info(f"Face processing completed for twin: {twin_id}")
                return result
            else:
                logger.error(f"Face processing failed: {face_result.get('error')}")
                return {
                    "success": False,
                    "error": face_result.get("error")
                }
            
        except Exception as e:
            logger.error(f"Failed to process face images: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def generate_face_animation(
        self,
        twin_id: uuid.UUID,
        text: str,
        emotion: str = "neutral"
    ) -> Dict[str, Any]:
        """
        Generate face animation for digital twin
        """
        try:
            logger.info(f"Generating face animation for twin: {twin_id}")
            
            # Get facial expressions based on text and emotion
            expressions = await self.emotion_detector.generate_facial_expressions(
                text=text,
                emotion=emotion
            )
            
            # Generate animation
            animation_result = await self.face_processor.generate_animation(
                twin_id=twin_id,
                expressions=expressions,
                duration=len(text.split()) * 0.3  # Approximate duration
            )
            
            if animation_result["success"]:
                logger.info(f"Face animation generated for twin: {twin_id}")
                return {
                    "success": True,
                    "animation_url": animation_result.get("animation_url"),
                    "expressions": expressions,
                    "duration": animation_result.get("duration", 0),
                    "format": "mp4"
                }
            else:
                logger.error(f"Face animation failed: {animation_result.get('error')}")
                return {
                    "success": False,
                    "error": animation_result.get("error")
                }
            
        except Exception as e:
            logger.error(f"Failed to generate face animation: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def analyze_conversation(
        self,
        twin_id: uuid.UUID,
        conversation_history: List[Dict]
    ) -> Dict[str, Any]:
        """
        Analyze conversation for insights
        """
        try:
            logger.info(f"Analyzing conversation for twin: {twin_id}")
            
            analysis = await self.llm_provider.analyze_conversation(
                twin_id=twin_id,
                conversation_history=conversation_history
            )
            
            # Add emotion analysis
            emotions = []
            for message in conversation_history:
                if message.get("sender_type") == "user":
                    emotion = await self.emotion_detector.detect_text_emotion(
                        message.get("text_content", "")
                    )
                    emotions.append(emotion.get("primary_emotion", "neutral"))
            
            # Calculate emotion distribution
            emotion_dist = {}
            for emotion in emotions:
                emotion_dist[emotion] = emotion_dist.get(emotion, 0) + 1
            
            if emotions:
                for emotion in emotion_dist:
                    emotion_dist[emotion] = emotion_dist[emotion] / len(emotions)
            
            analysis["emotion_analysis"] = {
                "emotion_distribution": emotion_dist,
                "primary_emotion": max(emotion_dist, key=emotion_dist.get) if emotion_dist else "neutral",
                "emotional_variability": len(set(emotions)) / len(emotions) if emotions else 0
            }
            
            logger.info(f"Conversation analysis completed for twin: {twin_id}")
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze conversation: {e}")
            return {
                "error": str(e),
                "summary": "Analysis failed",
                "key_topics": [],
                "sentiment": "neutral"
            }
    
    async def generate_chat_suggestions(
        self,
        twin_id: uuid.UUID,
        context: Optional[str] = None,
        user_interests: Optional[List[str]] = None
    ) -> List[str]:
        """
        Generate chat suggestions for digital twin
        """
        try:
            logger.info(f"Generating chat suggestions for twin: {twin_id}")
            
            suggestions = await self.llm_provider.generate_suggestions(
                twin_id=twin_id,
                context=context,
                user_interests=user_interests or []
            )
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Failed to generate chat suggestions: {e}")
            return [
                "Tell me about your day.",
                "What are your thoughts on technology?",
                "Can you share an interesting fact?",
                "How are you feeling today?"
            ]
    
    async def generate_greeting(
        self,
        twin_id: uuid.UUID,
        user_name: str,
        context: str = "general",
        mood: str = "friendly"
    ) -> str:
        """
        Generate personalized greeting
        """
        try:
            logger.info(f"Generating greeting for twin: {twin_id}")
            
            greeting = await self.llm_provider.generate_greeting(
                twin_id=twin_id,
                user_name=user_name,
                context=context,
                mood=mood
            )
            
            return greeting
            
        except Exception as e:
            logger.error(f"Failed to generate greeting: {e}")
            return f"Hello {user_name}! How can I help you today?"
    
    async def translate_text(
        self,
        text: str,
        source_lang: str = "auto",
        target_lang: str = "en"
    ) -> Dict[str, Any]:
        """
        Translate text between languages
        """
        try:
            logger.info(f"Translating text from {source_lang} to {target_lang}")
            
            translation = await self.llm_provider.translate_text(
                text=text,
                source_lang=source_lang,
                target_lang=target_lang
            )
            
            return {
                "success": True,
                "original_text": text,
                "translated_text": translation,
                "source_lang": source_lang,
                "target_lang": target_lang,
                "detected_lang": source_lang if source_lang != "auto" else "detected"
            }
            
        except Exception as e:
            logger.error(f"Failed to translate text: {e}")
            return {
                "success": False,
                "error": str(e),
                "original_text": text,
                "translated_text": text
            }
    
    async def summarize_text(
        self,
        text: str,
        max_length: int = 100
    ) -> Dict[str, Any]:
        """
        Summarize text
        """
        try:
            logger.info("Summarizing text")
            
            summary = await self.llm_provider.summarize_text(
                text=text,
                max_length=max_length
            )
            
            return {
                "success": True,
                "original_text": text,
                "summary": summary,
                "original_length": len(text),
                "summary_length": len(summary),
                "compression_ratio": len(summary) / len(text) if text else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to summarize text: {e}")
            return {
                "success": False,
                "error": str(e),
                "original_text": text,
                "summary": text[:max_length] + "..." if len(text) > max_length else text
            }
    
    async def extract_keywords(
        self,
        text: str,
        max_keywords: int = 10
    ) -> List[str]:
        """
        Extract keywords from text
        """
        try:
            logger.info("Extracting keywords from text")
            
            keywords = await self.llm_provider.extract_keywords(
                text=text,
                max_keywords=max_keywords
            )
            
            return keywords
            
        except Exception as e:
            logger.error(f"Failed to extract keywords: {e}")
            return []
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check health of all AI components
        """
        try:
            health_status = {
                "timestamp": datetime.utcnow().isoformat(),
                "overall": "healthy",
                "components": {}
            }
            
            # Check LLM provider
            llm_health = await self.llm_provider.health_check()
            health_status["components"]["llm_provider"] = llm_health
            
            # Check voice cloner
            voice_health = await self.voice_cloner.health_check()
            health_status["components"]["voice_cloner"] = voice_health
            
            # Check face processor
            face_health = await self.face_processor.health_check()
            health_status["components"]["face_processor"] = face_health
            
            # Check emotion detector
            emotion_health = await self.emotion_detector.health_check()
            health_status["components"]["emotion_detector"] = emotion_health
            
            # Determine overall health
            all_healthy = all(
                comp.get("status") == "healthy" 
                for comp in health_status["components"].values()
            )
            
            health_status["overall"] = "healthy" if all_healthy else "degraded"
            
            return health_status
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "overall": "unhealthy",
                "error": str(e)
            }

# Singleton instance
_ai_service = None

def get_ai_service() -> AIService:
    """Get AI service instance (singleton)"""
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service