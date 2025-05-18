# ai_services/tasks.py

import requests
import json
import logging
import time 
import re

from celery import shared_task
from django.conf import settings
from django.utils import timezone # For potential future use

logger = logging.getLogger(__name__)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
AI_MODEL_FOR_QUOTES = "deepseek/deepseek-chat" # Or your preferred DeepSeek model

@shared_task(bind=True, max_retries=3, default_retry_delay=60 * 2, acks_late=True, name='ai_services.tasks.generate_quote_for_entry_task_explicit')
def generate_quote_for_entry_task(self, journal_entry_id):
    """
    Celery task to generate a quote for a journal entry and update its status.
    """
    from journal.models import JournalEntry # Import model inside the task
    logger.info(f"--- generate_quote_for_entry_task_explicit STARTED --- Entry ID: {journal_entry_id}")
    task_succeeded = False
    generated_quote_text = "Failed to generate quote." # Default error/fallback message

    try:
        entry = JournalEntry.objects.get(pk=journal_entry_id)
        logger.info(f"Fetched JournalEntry ID: {entry.id} for quote generation.")

        api_key = settings.OPENROUTER_API_KEY
        if not api_key:
            logger.error("OPENROUTER_API_KEY not found. Aborting quote generation for entry ID: %s", entry.id)
            generated_quote_text = "AI Quote generation failed: API key is missing."
            # No 'return' here, proceed to finally block to update status
        else:
            content_snippet = (entry.content[:750] + '...') if len(entry.content) > 750 else entry.content
            prompt_text = (
                f"Analyze the following journal entry snippet. Your task is to provide ONLY ONE single, short (1-2 sentences, maximum 3), "
                f"insightful, and inspiring quote that is highly relevant to the potential themes, emotions, or topics expressed in the snippet. "
                f"The quote MUST be from a well-known Persian (Iranian) OR English-speaking scientist, poet, philosopher, or other famous public figure. "
                f"You must choose the most fitting quote; do not offer alternatives or explanations about your choice. "
                f"Clearly attribute the quote to its author using the format: \"Quote text.\" - Author's Name. "
                f"If the snippet is too vague or short to derive a specific thematic quote, select a general inspiring quote about life, reflection, "
                f"or personal growth from such a figure (either Persian or English, whichever you deem more impactful in a general sense).\n\n"
                f"Journal Entry Snippet:\n\"\"\"\n{content_snippet}\n\"\"\"\n\n"
                f"Provide only the quote and its attribution below (do not add any other text before or after the quote itself):\nQuote:"
            )
            payload = {
                "model": AI_MODEL_FOR_QUOTES,
                "messages": [{"role": "user", "content": prompt_text}],
                "max_tokens": 120, "temperature": 0.7,
            }
            headers = {
                "Authorization": f"Bearer {api_key}", "Content-Type": "application/json",
                "HTTP-Referer": getattr(settings, 'YOUR_SITE_URL', ''), 
                "X-Title": getattr(settings, 'YOUR_SITE_NAME', ''),
            }
            
            logger.info(f"Requesting quote from OpenRouter for entry ID: {entry.id}. Model: {payload['model']}.")
            response = requests.post(OPENROUTER_API_URL, headers=headers, data=json.dumps(payload), timeout=60)
            logger.info(f"OpenRouter API response status: {response.status_code} for entry ID: {entry.id}")
            response.raise_for_status() 
            
            response_data = response.json()
            logger.debug(f"OpenRouter Raw Response for entry {entry.id}: {json.dumps(response_data, indent=2)}")

            if response_data.get("choices") and len(response_data["choices"]) > 0:
                message = response_data["choices"][0].get("message", {})
                generated_quote_content = message.get("content")
                if generated_quote_content:
                    processed_quote = generated_quote_content.strip()
                    preambles_to_check = ["quote:", "here's a quote:", "a fitting quote could be:", "certainly, here is a quote:", "here is a quote:"]
                    temp_lower_quote = processed_quote.lower()
                    for preamble in preambles_to_check:
                        if temp_lower_quote.startswith(preamble):
                            processed_quote = processed_quote[len(preamble):].strip()
                            break 
                    if processed_quote.startswith('"') and processed_quote.endswith('"'):
                        processed_quote = processed_quote[1:-1]
                    generated_quote_text = processed_quote.strip()
                    task_succeeded = True # Mark as succeeded if quote is processed
                    logger.info(f"Successfully generated and processed quote for entry {entry.id}: \"{generated_quote_text}\"")
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
        error_text = exc.response.text[:200] if hasattr(exc.response, 'text') else "Unknown HTTP Error"
        logger.error(f"OpenRouter API HTTPError for entry {entry.id}: {exc.response.status_code} - {error_text}")
        generated_quote_text = f"AI service error ({exc.response.status_code}). Quote not generated."
    except requests.exceptions.RequestException as exc: # Catch other network related errors
        logger.error(f"OpenRouter API request failed for entry {entry.id}: {exc}", exc_info=True)
        generated_quote_text = "Network error connecting to AI service."
    except Exception as exc: 
        logger.error(f"Unexpected error in quote generation for entry {entry.id}: {exc}", exc_info=True)
        generated_quote_text = "Unexpected error generating quote."
    finally:
        try:
            entry_to_update = JournalEntry.objects.get(pk=journal_entry_id) # Re-fetch to avoid stale instance
            entry_to_update.ai_quote = generated_quote_text 
            entry_to_update.ai_quote_processed = True # Mark as processed
            entry_to_update.save(update_fields=['ai_quote', 'ai_quote_processed'])
            logger.info(f"Final ai_quote and status for entry {entry_to_update.id} saved. Processed: True. Quote: '{entry_to_update.ai_quote}'.")
        except JournalEntry.DoesNotExist:
            logger.error(f"JournalEntry {journal_entry_id} not found in finally block. Cannot update status.")
        except Exception as e_save:
            logger.error(f"Error saving ai_quote/status for entry {journal_entry_id} in finally block: {e_save}", exc_info=True)


    logger.info(f"--- generate_quote_for_entry_task_explicit COMPLETED for entry ID: {journal_entry_id} ---")
    return f"Quote generation task processed for entry {journal_entry_id}. Success: {task_succeeded}"


@shared_task(bind=True, acks_late=True, name='ai_services.tasks.detect_mood_for_entry_task_explicit')
def detect_mood_for_entry_task(self, journal_entry_id):
    from journal.models import JournalEntry
    logger.info(f"--- detect_mood_for_entry_task_explicit STARTED --- Entry ID: {journal_entry_id}")
    task_succeeded = False
    try:
        entry = JournalEntry.objects.get(pk=journal_entry_id)
        if entry.mood: 
            logger.info(f"User already set mood ('{entry.mood}') for JournalEntry ID: {entry.id}. AI mood detection skipped.")
            # Still mark as processed if user set it, as no AI action is needed.
            task_succeeded = True 
        else:
            logger.info(f"Detecting mood for JournalEntry ID: {entry.id}")
            content_lower = entry.content.lower()
            detected_mood = 'neutral' 
            time.sleep(1) # Shorter simulation
            if any(keyword in content_lower for keyword in ["happy", "joy", "great", "wonderful", "excited", "love", "amazing", "fantastic", "delighted"]):
                detected_mood = 'happy'
            elif any(keyword in content_lower for keyword in ["sad", "unhappy", "cried", "depressed", "miserable", "gloomy", "tear", "sorrow"]):
                detected_mood = 'sad'
            elif any(keyword in content_lower for keyword in ["angry", "frustrated", "annoyed", "hate", "mad", "irritated", "furious"]):
                detected_mood = 'angry'
            elif any(keyword in content_lower for keyword in ["calm", "peaceful", "relaxed", "serene", "tranquil", "content"]):
                detected_mood = 'calm'
            elif any(keyword in content_lower for keyword in ["excited", "thrilled", "eager", "enthusiastic", "anticipating"]):
                detected_mood = 'excited'
            
            entry.mood = detected_mood
            entry.save(update_fields=['mood'])
            task_succeeded = True
            logger.info(f"AI detected and set mood to '{entry.mood}' for entry ID: {entry.id}")
        
    except JournalEntry.DoesNotExist:
        logger.error(f"JournalEntry ID {journal_entry_id} not found for mood detection.")
    except Exception as e:
        logger.error(f"Error in detect_mood_for_entry_task for entry {journal_entry_id}: {e}", exc_info=True)
    finally:
        try:
            entry_to_update_status = JournalEntry.objects.get(pk=journal_entry_id)
            entry_to_update_status.ai_mood_processed = True
            entry_to_update_status.save(update_fields=['ai_mood_processed'])
            logger.info(f"Mood task status for entry {journal_entry_id} set to processed.")
        except JournalEntry.DoesNotExist:
             pass # Already logged
        except Exception as e_save_status:
            logger.error(f"Error saving mood_processed status for entry {journal_entry_id}: {e_save_status}", exc_info=True)
            
    logger.info(f"--- detect_mood_for_entry_task_explicit COMPLETED for entry ID: {journal_entry_id} ---")
    return f"Mood detection processed for entry {journal_entry_id}. Success: {task_succeeded}"


@shared_task(bind=True, acks_late=True, name='ai_services.tasks.suggest_tags_for_entry_task_explicit')
def suggest_tags_for_entry_task(self, journal_entry_id):
    from journal.models import JournalEntry, Tag
    logger.info(f"--- suggest_tags_for_entry_task_explicit STARTED --- Entry ID: {journal_entry_id}")
    task_succeeded = False
    try:
        entry = JournalEntry.objects.get(pk=journal_entry_id)
        if entry.tags.exists(): 
            logger.info(f"User already set tags for JournalEntry ID: {entry.id}. AI tag suggestion skipped.")
            task_succeeded = True
        else:
            logger.info(f"Suggesting tags for JournalEntry ID: {entry.id}")
            content_lower = entry.content.lower()
            suggested_tags_names = []
            time.sleep(1) 

            if any(keyword in content_lower for keyword in ["work", "job", "office", "meeting", "project", "career"]):
                suggested_tags_names.append("Work")
            if any(keyword in content_lower for keyword in ["learn", "study", "course", "book", "research", "skill"]):
                suggested_tags_names.append("Learning")
            if any(keyword in content_lower for keyword in ["idea", "think", "brainstorm", "concept", "innovation"]):
                suggested_tags_names.append("Ideas")
            if any(keyword in content_lower for keyword in ["family", "home", "parents", "children", "love"]):
                suggested_tags_names.append("Family")
            if any(keyword in content_lower for keyword in ["friend", "friends", "social", "party"]):
                suggested_tags_names.append("Friends")
            if any(keyword in content_lower for keyword in ["goal", "plan", "achieve", "objective"]):
                suggested_tags_names.append("Goals")
            if not suggested_tags_names and len(entry.content) > 150:
                 suggested_tags_names.append("Reflection")
            elif not suggested_tags_names and len(entry.content) > 0:
                suggested_tags_names.append("Personal")

            if suggested_tags_names:
                tags_to_add = []
                for tag_name in list(set(suggested_tags_names)): 
                    tag, created = Tag.objects.get_or_create(
                        name__iexact=tag_name.strip(),
                        defaults={'name': tag_name.strip().capitalize()} 
                    )
                    tags_to_add.append(tag)
                    logger.info(f"AI suggesting tag '{tag.name}' for entry ID: {entry.id} (Created: {created})")
                if tags_to_add:
                    entry.tags.add(*tags_to_add)
                    logger.info(f"AI added suggested tags to entry ID: {entry.id}")
            task_succeeded = True
        
    except JournalEntry.DoesNotExist:
        logger.error(f"JournalEntry ID {journal_entry_id} not found for tag suggestion.")
    except Exception as e:
        logger.error(f"Error in suggest_tags_for_entry_task for entry {journal_entry_id}: {e}", exc_info=True)
    finally:
        try:
            entry_to_update_status = JournalEntry.objects.get(pk=journal_entry_id)
            entry_to_update_status.ai_tags_processed = True
            entry_to_update_status.save(update_fields=['ai_tags_processed'])
            logger.info(f"Tag suggestion task status for entry {journal_entry_id} set to processed.")
        except JournalEntry.DoesNotExist:
            pass # Already logged
        except Exception as e_save_status:
            logger.error(f"Error saving tags_processed status for entry {journal_entry_id}: {e_save_status}", exc_info=True)

    logger.info(f"--- suggest_tags_for_entry_task_explicit COMPLETED for entry ID: {journal_entry_id} ---")
    return f"Tag suggestion processed for entry {journal_entry_id}. Success: {task_succeeded}"

