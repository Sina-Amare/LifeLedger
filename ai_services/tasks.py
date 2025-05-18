# ai_services/tasks.py

import requests
import json
import logging
import time 

from celery import shared_task
from django.conf import settings
# Importing models inside tasks is a good practice

logger = logging.getLogger(__name__)

# --- Constants for API Interaction ---
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
# Switched to a DeepSeek model as requested, which is often available on free tiers
AI_MODEL_FOR_QUOTES = "deepseek/deepseek-chat" 
# You can also try "deepseek/deepseek-coder" if you want a coding-focused model,
# or check OpenRouter's documentation for the exact free "v3-0324" variant if available.

@shared_task(bind=True, max_retries=3, default_retry_delay=60 * 2, acks_late=True, name='ai_services.tasks.generate_quote_for_entry_task_explicit')
def generate_quote_for_entry_task(self, journal_entry_id):
    """
    Celery task to generate an inspirational quote for a given journal entry
    using the OpenRouter API (with DeepSeek model) and update the journal entry.

    Args:
        journal_entry_id (int): The primary key of the JournalEntry object.
    """
    from journal.models import JournalEntry # Import model inside the task
    logger.info(f"--- generate_quote_for_entry_task_explicit STARTED --- Entry ID: {journal_entry_id}")

    try:
        entry = JournalEntry.objects.get(pk=journal_entry_id)
        logger.info(f"Fetched JournalEntry ID: {entry.id} for quote generation.")
    except JournalEntry.DoesNotExist:
        logger.error(f"JournalEntry with ID {journal_entry_id} not found. Aborting quote generation.")
        return f"Error: JournalEntry ID {journal_entry_id} not found."

    api_key = settings.OPENROUTER_API_KEY
    if not api_key:
        logger.error("OPENROUTER_API_KEY not found in Django settings. Aborting quote generation for entry ID: %s", entry.id)
        entry.ai_quote = "AI Quote generation failed: API key is missing in settings."
        entry.save(update_fields=['ai_quote'])
        return "Error: OpenRouter API key missing."

    content_snippet = (entry.content[:750] + '...') if len(entry.content) > 750 else entry.content
    
    prompt_text = (
        f"Based on the following journal entry snippet, provide a single, short (1-2 sentences, maximum 3), insightful, and inspiring quote. "
        f"The quote should be from a well-known Persian (Iranian) or English-speaking scientist, poet, philosopher, or other famous public figure. "
        f"Clearly attribute the quote to its author (e.g., \"Quote text.\" - Author's Name). "
        f"If the snippet is too vague, provide a general inspiring quote about life, reflection, or personal growth from such a figure. "
        f"Prioritize relevance and ensure the quote is genuinely attributable to the stated author.\n\n"
        f"Journal Entry Snippet:\n\"\"\"\n{content_snippet}\n\"\"\"\n\n"
        f"Quote:"
    )

    payload = {
        "model": AI_MODEL_FOR_QUOTES,
        "messages": [{"role": "user", "content": prompt_text}],
        "max_tokens": 150,  
        "temperature": 0.7, # DeepSeek models can sometimes benefit from slightly lower temperature for focused output
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": getattr(settings, 'YOUR_SITE_URL', ''), 
        "X-Title": getattr(settings, 'YOUR_SITE_NAME', ''),
    }
    
    logger.info(f"Requesting quote from OpenRouter for entry ID: {entry.id}. Model: {payload['model']}.")
    generated_quote_text = "Failed to generate quote." 

    try:
        response = requests.post(
            OPENROUTER_API_URL,
            headers=headers,
            data=json.dumps(payload),
            timeout=60 
        )
        logger.info(f"OpenRouter API response status: {response.status_code} for entry ID: {entry.id}")
        response.raise_for_status() 
        
        response_data = response.json()
        logger.debug(f"OpenRouter Raw Response for entry {entry.id}: {json.dumps(response_data, indent=2)}")

        if response_data.get("choices") and len(response_data["choices"]) > 0:
            message = response_data["choices"][0].get("message", {})
            generated_quote_content = message.get("content")
            
            if generated_quote_content:
                generated_quote_text = generated_quote_content.strip()
                logger.info(f"Successfully generated quote for entry {entry.id}: \"{generated_quote_text}\"")
            else:
                logger.warning(f"No 'content' found in OpenRouter response message for entry {entry.id}.")
                generated_quote_text = "AI service did not return a quote."
        else:
            error_detail = response_data.get("error", {}).get("message", "No 'choices' in API response.")
            logger.warning(f"Unexpected OpenRouter response for entry {entry.id}: {error_detail}. Full: {response_data}")
            generated_quote_text = f"AI service response error: {error_detail[:100]}"
        
    except requests.exceptions.Timeout as exc:
        logger.error(f"Timeout during OpenRouter API request for entry {entry.id}: {exc}")
        generated_quote_text = "AI service timed out. Quote not generated."
    except requests.exceptions.HTTPError as exc:
        logger.error(f"OpenRouter API HTTPError for entry {entry.id}: {exc.response.status_code} - {exc.response.text[:200]}")
        generated_quote_text = f"AI service error ({exc.response.status_code}). Quote not generated."
    except requests.exceptions.RequestException as exc:
        logger.error(f"OpenRouter API request failed for entry {entry.id}: {exc}", exc_info=True)
        generated_quote_text = "Network error connecting to AI service."
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        logger.error(f"Error parsing OpenRouter response for entry {entry.id}: {exc}", exc_info=True)
        generated_quote_text = "Error processing AI response for quote."
    except Exception as exc: 
        logger.error(f"Unexpected error in quote generation for entry {entry.id}: {exc}", exc_info=True)
        generated_quote_text = "Unexpected error generating quote."
    finally:
        entry.ai_quote = generated_quote_text # Save the generated quote or error message
        entry.save(update_fields=['ai_quote'])
        logger.info(f"Final ai_quote field for entry {entry.id} saved: '{entry.ai_quote}'.")

    logger.info(f"--- generate_quote_for_entry_task_explicit COMPLETED for entry ID: {journal_entry_id} ---")
    return f"Quote generation task processed for entry {entry.id}."


@shared_task(bind=True, acks_late=True, name='ai_services.tasks.detect_mood_for_entry_task_explicit')
def detect_mood_for_entry_task(self, journal_entry_id):
    """
    Celery task to detect mood for a given journal entry if not already set by the user.
    Placeholder: Current implementation uses simple keyword matching.
    """
    from journal.models import JournalEntry
    logger.info(f"--- detect_mood_for_entry_task_explicit STARTED --- Entry ID: {journal_entry_id}")
    try:
        entry = JournalEntry.objects.get(pk=journal_entry_id)
        if entry.mood: 
            logger.info(f"User already set mood ('{entry.mood}') for JournalEntry ID: {entry.id}. AI mood detection skipped.")
            return f"Mood already set by user for entry {entry.id}."
        
        logger.info(f"Detecting mood for JournalEntry ID: {entry.id}")
        content_lower = entry.content.lower()
        detected_mood = 'neutral' 

        time.sleep(2) 
        if any(keyword in content_lower for keyword in ["happy", "joy", "great", "wonderful", "excited", "love", "amazing", "fantastic"]):
            detected_mood = 'happy'
        elif any(keyword in content_lower for keyword in ["sad", "unhappy", "cried", "depressed", "miserable", "gloomy", "tear"]):
            detected_mood = 'sad'
        elif any(keyword in content_lower for keyword in ["angry", "frustrated", "annoyed", "hate", "mad", "irritated"]):
            detected_mood = 'angry'
        elif any(keyword in content_lower for keyword in ["calm", "peaceful", "relaxed", "serene", "tranquil"]):
            detected_mood = 'calm'
        elif any(keyword in content_lower for keyword in ["excited", "thrilled", "eager", "enthusiastic"]):
            detected_mood = 'excited'
        
        entry.mood = detected_mood
        entry.save(update_fields=['mood'])
        logger.info(f"AI detected and set mood to '{entry.mood}' for entry ID: {entry.id}")
        
    except JournalEntry.DoesNotExist:
        logger.error(f"JournalEntry ID {journal_entry_id} not found for mood detection.")
        return f"Error: JournalEntry ID {journal_entry_id} not found."
    except Exception as e:
        logger.error(f"Error in detect_mood_for_entry_task for entry {journal_entry_id}: {e}", exc_info=True)
        return f"Error processing mood for entry {journal_entry_id}."
    finally:
        logger.info(f"--- detect_mood_for_entry_task_explicit COMPLETED for entry ID: {journal_entry_id} ---")


@shared_task(bind=True, acks_late=True, name='ai_services.tasks.suggest_tags_for_entry_task_explicit')
def suggest_tags_for_entry_task(self, journal_entry_id):
    """
    Celery task to suggest or add tags for a given journal entry if none are set.
    Placeholder: Current implementation uses very simple logic.
    """
    from journal.models import JournalEntry, Tag
    logger.info(f"--- suggest_tags_for_entry_task_explicit STARTED --- Entry ID: {journal_entry_id}")
    try:
        entry = JournalEntry.objects.get(pk=journal_entry_id)
        if entry.tags.exists(): 
            logger.info(f"User already set tags for JournalEntry ID: {entry.id}. AI tag suggestion skipped.")
            return f"Tags already set by user for entry {entry.id}."

        logger.info(f"Suggesting tags for JournalEntry ID: {entry.id}")
        content_lower = entry.content.lower()
        suggested_tags_names = []

        time.sleep(1) 
        if "work" in content_lower or "job" in content_lower or "office" in content_lower or "meeting" in content_lower:
            suggested_tags_names.append("Work")
        if "learn" in content_lower or "study" in content_lower or "course" in content_lower or "book" in content_lower:
            suggested_tags_names.append("Learning")
        if "idea" in content_lower or "think" in content_lower or "brainstorm" in content_lower:
            suggested_tags_names.append("Ideas")
        if "family" in content_lower or "home" in content_lower:
            suggested_tags_names.append("Family")
        if not suggested_tags_names and len(entry.content) > 150:
             suggested_tags_names.append("Reflection")
        elif not suggested_tags_names and len(entry.content) > 0:
            suggested_tags_names.append("Personal")

        if suggested_tags_names:
            tags_to_add = []
            for tag_name in suggested_tags_names:
                tag, created = Tag.objects.get_or_create(
                    name__iexact=tag_name.strip(),
                    defaults={'name': tag_name.strip().capitalize()} 
                )
                tags_to_add.append(tag)
                logger.info(f"AI suggesting tag '{tag.name}' for entry ID: {entry.id} (Created: {created})")
            if tags_to_add:
                entry.tags.add(*tags_to_add)
                logger.info(f"AI added suggested tags to entry ID: {entry.id}")
        
    except JournalEntry.DoesNotExist:
        logger.error(f"JournalEntry ID {journal_entry_id} not found for tag suggestion.")
        return f"Error: JournalEntry ID {journal_entry_id} not found."
    except Exception as e:
        logger.error(f"Error in suggest_tags_for_entry_task for entry {journal_entry_id}: {e}", exc_info=True)
        return f"Error processing tags for entry {journal_entry_id}."
    finally:
        logger.info(f"--- suggest_tags_for_entry_task_explicit COMPLETED for entry ID: {journal_entry_id} ---")

