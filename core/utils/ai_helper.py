# core/utils/ai_helper.py
import google.genai as genai
from google.genai import types
from django.conf import settings
from django.core.cache import cache
import json
import hashlib
import logging

logger = logging.getLogger(__name__)

# Configure Gemini with new SDK
client = genai.Client(api_key=settings.GEMINI_API_KEY)

# Model configuration for Gemini 2.0 Flash
MODEL_NAME = 'gemini-2.0-flash-exp'

# Generation config for fast responses
GENERATION_CONFIG = types.GenerateContentConfig(
    temperature=0.3,
    max_output_tokens=150,
    response_modalities=["TEXT"],
)


def generate_smart_hint(exercise, user_profile=None):
    """
    Generate a contextual hint for the exercise using Gemini 2.0 Flash.
    Cached for 7 days since hints don't change per exercise.
    """
    
    # Create cache key based on exercise
    cache_key = f"hint:v2:{exercise.id}"
    
    # Check cache first
    cached_hint = cache.get(cache_key)
    if cached_hint:
        logger.info(f"Hint cache hit for exercise {exercise.id}")
        return cached_hint
    
    try:
        # Build context-aware prompt
        learning_level = "beginner"  # Could be based on user_profile data
        
        prompt = f"""You are a helpful language tutor. Generate a brief hint for this exercise.

Exercise Type: {exercise.get_type_display()}
Question: {exercise.prompt}
Correct Answer: {exercise.answer_text}
Student Level: {learning_level}

Provide a helpful hint that:
1. Doesn't give away the full answer
2. Guides the student's thinking
3. Is encouraging and brief (2-3 sentences max)

Hint:"""

        # Use new SDK with Gemini 2.0 Flash
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=GENERATION_CONFIG,
        )
        
        hint = response.text.strip()
        
        # Cache for 7 days
        cache.set(cache_key, hint, 60*60*24*7)
        logger.info(f"Generated and cached hint for exercise {exercise.id}")
        
        return hint
        
    except Exception as e:
        logger.error(f"Error generating hint: {e}")
        # Fallback to static hint if available
        return exercise.hint if exercise.hint else "Think about the context and try again!"


def explain_mistake(user_answer, correct_answer, exercise_prompt, exercise_type):
    """
    Generate a detailed explanation of why the answer was wrong using Gemini 2.0 Flash.
    Cached based on the specific mistake.
    """
    
    # Create cache key based on the mistake pattern
    cache_key = hashlib.md5(
        f"{user_answer}:{correct_answer}:{exercise_prompt}".lower().encode()
    ).hexdigest()
    cache_key = f"explanation:v2:{cache_key}"
    
    # Check cache first
    cached_explanation = cache.get(cache_key)
    if cached_explanation:
        logger.info(f"Explanation cache hit")
        return cached_explanation
    
    try:
        prompt = f"""You are a patient language teacher. A student made a mistake.

Exercise Type: {exercise_type}
Question: {exercise_prompt}
Student's Answer: {user_answer}
Correct Answer: {correct_answer}

Provide a brief, encouraging explanation that:
1. Identifies what went wrong
2. Explains the correct answer
3. Gives a helpful tip to remember
4. Stays under 4 sentences
5. Is supportive and constructive

Explanation:"""

        # Use new SDK with Gemini 2.0 Flash
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=GENERATION_CONFIG,
        )
        
        explanation = response.text.strip()
        
        # Cache for 30 days (mistakes are consistent)
        cache.set(cache_key, explanation, 60*60*24*30)
        logger.info(f"Generated and cached mistake explanation")
        
        return explanation
        
    except Exception as e:
        logger.error(f"Error generating explanation: {e}")
        # Fallback explanation
        return f"The correct answer is '{correct_answer}'. Keep practicing!"


def check_translation_with_ai(user_answer, correct_answer, original_phrase):
    """
    Check if translation is semantically correct using Gemini 2.0 Flash.
    Returns dict with 'correct' (bool) and 'feedback' (str).
    """
    
    # Create cache key
    cache_key = hashlib.md5(
        f"{user_answer}:{correct_answer}:{original_phrase}".lower().encode()
    ).hexdigest()
    cache_key = f"trans_check:v2:{cache_key}"
    
    # Check cache
    cached = cache.get(cache_key)
    if cached:
        logger.info(f"Translation check cache hit")
        return cached
    
    try:
        prompt = f"""Check this translation:

Original: {original_phrase}
Expected: {correct_answer}
Student: {user_answer}

Is the student's translation acceptable? Consider:
- Semantic meaning (most important)
- Common alternative translations
- Minor grammar/spelling differences

Respond in JSON format only:
{{"correct": true/false, "feedback": "brief reason in 1 sentence"}}"""

        # Use new SDK with Gemini 2.0 Flash - optimized for JSON
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,  # Lower temp for more consistent JSON
                max_output_tokens=100,
                response_modalities=["TEXT"],
                response_mime_type="application/json",  # Request JSON response
            ),
        )
        
        # Parse JSON response
        result = json.loads(response.text.strip())
        
        # Validate response structure
        if not isinstance(result, dict) or 'correct' not in result:
            raise ValueError("Invalid response structure")
        
        # Ensure correct is boolean
        result['correct'] = bool(result.get('correct', False))
        
        # Ensure feedback exists
        if 'feedback' not in result:
            result['feedback'] = "Checked against expected answer."
        
        # Cache for 30 days
        cache.set(cache_key, result, 60*60*24*30)
        logger.info(f"Generated and cached translation check")
        
        return result
        
    except Exception as e:
        logger.error(f"Error checking translation: {e}")
        # Fallback to exact match
        is_correct = user_answer.lower().strip() == correct_answer.lower().strip()
        return {
            "correct": is_correct,
            "feedback": "Checked against expected answer."
        }


def generate_batch_hints(exercises, user_profile=None):
    """
    Generate hints for multiple exercises in a single batch request.
    More efficient for pre-generating hints.
    """
    
    uncached_exercises = []
    results = {}
    
    # Check cache first
    for exercise in exercises:
        cache_key = f"hint:v2:{exercise.id}"
        cached = cache.get(cache_key)
        if cached:
            results[exercise.id] = cached
        else:
            uncached_exercises.append(exercise)
    
    if not uncached_exercises:
        return results
    
    try:
        # Build batch prompts
        batch_prompts = []
        for exercise in uncached_exercises:
            prompt = f"""Exercise {exercise.id}:
Type: {exercise.get_type_display()}
Question: {exercise.prompt}
Answer: {exercise.answer_text}

Generate a brief helpful hint (2-3 sentences, don't give away answer):"""
            batch_prompts.append(prompt)
        
        # Combine prompts
        combined_prompt = "\n\n---\n\n".join(batch_prompts)
        
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=combined_prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=500,
                response_modalities=["TEXT"],
            ),
        )
        
        # Parse response (split by exercise)
        hints = response.text.split("---")
        
        for i, exercise in enumerate(uncached_exercises):
            if i < len(hints):
                hint = hints[i].strip()
                results[exercise.id] = hint
                cache_key = f"hint:v2:{exercise.id}"
                cache.set(cache_key, hint, 60*60*24*7)
        
        return results
        
    except Exception as e:
        logger.error(f"Error in batch hint generation: {e}")
        # Fallback to individual hints
        for exercise in uncached_exercises:
            results[exercise.id] = generate_smart_hint(exercise, user_profile)
        return results


def get_conversation_practice_response(user_message, conversation_history, target_language):
    """
    Generate conversational responses for practice mode.
    Uses streaming for better UX.
    """
    
    try:
        # Build conversation context
        messages = []
        for msg in conversation_history[-10:]:  # Last 10 messages
            messages.append(f"{msg['role']}: {msg['content']}")
        
        context = "\n".join(messages)
        
        prompt = f"""You are a friendly language tutor having a conversation in {target_language}.

Conversation so far:
{context}

Student: {user_message}

Respond naturally in {target_language}. Keep responses short (2-3 sentences). If the student makes a mistake, gently correct it in your response. Be encouraging!

Your response:"""

        # Use streaming for better UX
        response = client.models.generate_content_stream(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,  # Higher temp for more natural conversation
                max_output_tokens=200,
                response_modalities=["TEXT"],
            ),
        )
        
        # Stream response
        for chunk in response:
            if chunk.text:
                yield chunk.text
        
    except Exception as e:
        logger.error(f"Error in conversation practice: {e}")
        yield "I'm having trouble responding right now. Could you try again?"