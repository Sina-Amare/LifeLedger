# ai_services/tasks.py

import requests
import json
import logging
import time
import re # Keep re for potential future use or simple pre-processing

from celery import shared_task
from django.conf import settings
from django.utils import timezone 

logger = logging.getLogger(__name__)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
# Using a capable model for all tasks for now.
# Consider using different models based on complexity/cost in the future.
AI_MODEL_FOR_ALL_TASKS = getattr(settings, 'AI_MODEL_FOR_JOURNAL_ANALYSIS', "deepseek/deepseek-chat")


def call_openrouter_api(prompt_text, entry_id, task_name, max_tokens=80, temperature=0.6):
    """
    Helper function to call the OpenRouter API.
    Returns the content of the AI's response or None on failure.
    """
    api_key = settings.OPENROUTER_API_KEY
    if not api_key:
        logger.error(f"OPENROUTER_API_KEY not found. Aborting {task_name} for entry ID: {entry_id}")
        return None

    payload = {
        "model": AI_MODEL_FOR_ALL_TASKS,
        "messages": [{"role": "user", "content": prompt_text}],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": getattr(settings, 'YOUR_SITE_URL', 'http://localhost:8000'), # Default for local dev
        "X-Title": getattr(settings, 'YOUR_SITE_NAME', 'LifeLedger'), # Default site name
    }

    try:
        logger.info(f"Requesting {task_name} from OpenRouter for entry ID: {entry_id}. Model: {payload['model']}.")
        response = requests.post(OPENROUTER_API_URL, headers=headers, data=json.dumps(payload), timeout=60) # 60s timeout
        logger.info(f"OpenRouter API response status for {task_name} (entry {entry_id}): {response.status_code}")
        response.raise_for_status()  # Raises HTTPError for bad responses (4XX or 5XX)
        
        response_data = response.json()
        logger.debug(f"OpenRouter Raw Response for {task_name} (entry {entry_id}): {json.dumps(response_data, indent=2)}")

        if response_data.get("choices") and len(response_data["choices"]) > 0:
            message = response_data["choices"][0].get("message", {})
            content = message.get("content")
            if content:
                return content.strip()
            else:
                logger.warning(f"No 'content' in OpenRouter response message for {task_name} (entry {entry_id}).")
                return None
        else:
            error_detail = response_data.get("error", {}).get("message", f"No 'choices' in API response for {task_name}.")
            logger.warning(f"Unexpected OpenRouter response for {task_name} (entry {entry_id}): {error_detail}. Full: {response_data}")
            return None
            
    except requests.exceptions.Timeout:
        logger.error(f"Timeout during OpenRouter API request for {task_name} (entry {entry_id}).")
    except requests.exceptions.HTTPError as http_err:
        error_text = http_err.response.text[:200] if hasattr(http_err.response, 'text') else "Unknown HTTP Error"
        logger.error(f"OpenRouter API HTTPError for {task_name} (entry {entry_id}): {http_err.response.status_code} - {error_text}")
    except requests.exceptions.RequestException as req_err:
        logger.error(f"OpenRouter API request failed for {task_name} (entry {entry_id}): {req_err}", exc_info=True)
    except Exception as e:
        logger.error(f"Unexpected error calling OpenRouter API for {task_name} (entry {entry_id}): {e}", exc_info=True)
    
    return None


@shared_task(bind=True, max_retries=3, default_retry_delay=60 * 2, acks_late=True, name='ai_services.tasks.generate_quote_for_entry_task_explicit')
def generate_quote_for_entry_task(self, journal_entry_id):
    from journal.models import JournalEntry
    logger.info(f"--- generate_quote_for_entry_task_explicit STARTED --- Entry ID: {journal_entry_id}")
    task_succeeded = False
    generated_quote_text = "Failed to generate quote." 

    try:
        entry = JournalEntry.objects.get(pk=journal_entry_id)
        logger.info(f"Fetched JournalEntry ID: {entry.id} for quote generation.")

        content_snippet = (entry.content[:1000] + '...') if len(entry.content) > 1000 else entry.content # Increased snippet size
        
        prompt_text = (
            f"Analyze the following journal entry snippet, which could be in any language. Your task is to provide ONLY ONE single, short (1-2 sentences, maximum 3), "
            f"insightful, and inspiring quote that is highly relevant to the potential themes, emotions, or topics expressed in the snippet. "
            f"The quote MUST be from a well-known Persian (Iranian) OR English-speaking scientist, poet, philosopher, or other famous public figure. "
            f"You must choose the most fitting quote; do not offer alternatives or explanations about your choice. "
            f"Clearly attribute the quote to its author using the format: \"Quote text.\" - Author's Name. "
            f"If the snippet is too vague or short to derive a specific thematic quote, select a general inspiring quote about life, reflection, "
            f"or personal growth from such a figure (either Persian or English, whichever you deem more impactful in a general sense).\n\n"
            f"Journal Entry Snippet:\n\"\"\"\n{content_snippet}\n\"\"\"\n\n"
            f"Provide only the quote and its attribution below (do not add any other text before or after the quote itself):\nQuote:"
        )
        
        ai_response_content = call_openrouter_api(prompt_text, entry.id, "quote_generation", max_tokens=120, temperature=0.7)

        if ai_response_content:
            processed_quote = ai_response_content
            # Clean up potential preambles from the AI, more robustly
            preambles_to_check = ["quote:", "here's a quote:", "a fitting quote could be:", "certainly, here is a quote:", "here is a quote:"]
            temp_lower_quote = processed_quote.lower()
            for preamble in preambles_to_check:
                if temp_lower_quote.startswith(preamble):
                    processed_quote = processed_quote[len(preamble):].strip()
                    break 
            # Remove surrounding quotes if present
            if processed_quote.startswith('"') and processed_quote.endswith('"'):
                processed_quote = processed_quote[1:-1]
            
            generated_quote_text = processed_quote.strip()
            if generated_quote_text: # Ensure it's not empty after stripping
                task_succeeded = True
                logger.info(f"Successfully generated and processed quote for entry {entry.id}: \"{generated_quote_text}\"")
            else:
                logger.warning(f"AI response for quote was empty after processing for entry {entry.id}.")
                generated_quote_text = "AI quote was empty after processing."
        else:
            logger.warning(f"Failed to get valid content from AI for quote generation (entry {entry.id}).")
            # generated_quote_text remains "Failed to generate quote."
            
    except JournalEntry.DoesNotExist:
        logger.error(f"JournalEntry {journal_entry_id} not found for quote generation.")
        generated_quote_text = "Entry not found for quote." # More specific error
    except Exception as exc: 
        logger.error(f"Unexpected error in quote generation task for entry {journal_entry_id}: {exc}", exc_info=True)
        generated_quote_text = "Unexpected error generating quote."
    finally:
        try:
            entry_to_update = JournalEntry.objects.get(pk=journal_entry_id) 
            entry_to_update.ai_quote = generated_quote_text 
            entry_to_update.ai_quote_processed = True 
            entry_to_update.save(update_fields=['ai_quote', 'ai_quote_processed'])
            logger.info(f"Final ai_quote and status for entry {entry_to_update.id} saved. Processed: True. Quote: '{entry_to_update.ai_quote}'.")
        except JournalEntry.DoesNotExist:
            logger.error(f"JournalEntry {journal_entry_id} not found in finally block for quote task. Cannot update status.")
        except Exception as e_save:
            logger.error(f"Error saving ai_quote/status for entry {journal_entry_id} in quote task finally block: {e_save}", exc_info=True)

    logger.info(f"--- generate_quote_for_entry_task_explicit COMPLETED for entry ID: {journal_entry_id} ---")
    return f"Quote generation task processed for entry {journal_entry_id}. Success: {task_succeeded}"


@shared_task(bind=True, max_retries=3, default_retry_delay=45, acks_late=True, name='ai_services.tasks.detect_mood_for_entry_task_explicit')
def detect_mood_for_entry_task(self, journal_entry_id):
    from journal.models import JournalEntry
    logger.info(f"--- detect_mood_for_entry_task_explicit STARTED --- Entry ID: {journal_entry_id}")
    task_succeeded = False
    detected_mood_value = None # Store the mood value from AI

    try:
        entry = JournalEntry.objects.get(pk=journal_entry_id)
        if entry.mood: 
            logger.info(f"User already set mood ('{entry.mood}') for JournalEntry ID: {entry.id}. AI mood detection skipped.")
            task_succeeded = True 
        else:
            logger.info(f"Detecting mood for JournalEntry ID: {entry.id} using AI.")
            content_snippet = (entry.content[:1500] + '...') if len(entry.content) > 1500 else entry.content # Use a good chunk of content

            valid_moods = [choice[0] for choice in JournalEntry.MOOD_CHOICES]
            mood_options_str = ", ".join(valid_moods) # "happy, sad, angry, calm, neutral, excited"

            prompt_text = (
                f"Analyze the sentiment and emotional tone of the following journal entry, which can be in any language. "
                f"Based on your analysis, determine the primary mood. "
                f"You MUST choose exactly ONE mood from the following predefined list: {mood_options_str}. "
                f"Do not provide any explanation or other text, only the single mood word.\n\n"
                f"Journal Entry Content:\n\"\"\"\n{content_snippet}\n\"\"\"\n\n"
                f"Primary Mood (choose one from list above):"
            )

            ai_response_content = call_openrouter_api(prompt_text, entry.id, "mood_detection", max_tokens=10, temperature=0.3)

            if ai_response_content:
                # Clean the response: take the first word, lowercase it.
                potential_mood = ai_response_content.split()[0].lower().strip().replace("\"", "").replace(".", "")
                if potential_mood in valid_moods:
                    detected_mood_value = potential_mood
                    entry.mood = detected_mood_value
                    # entry.save(update_fields=['mood']) # Save will be done in finally block
                    task_succeeded = True
                    logger.info(f"AI successfully detected mood as '{detected_mood_value}' for entry ID: {entry.id}")
                else:
                    logger.warning(f"AI returned an invalid mood ('{ai_response_content}') for entry {entry.id}. Not in {valid_moods}. Falling back to neutral.")
                    detected_mood_value = 'neutral' # Fallback
                    entry.mood = detected_mood_value # Set fallback
            else:
                logger.warning(f"AI did not return content for mood detection for entry {entry.id}. Falling back to neutral.")
                detected_mood_value = 'neutral' # Fallback
                entry.mood = detected_mood_value # Set fallback
        
    except JournalEntry.DoesNotExist:
        logger.error(f"JournalEntry ID {journal_entry_id} not found for mood detection.")
    except Exception as e:
        logger.error(f"Error in detect_mood_for_entry_task for entry {journal_entry_id}: {e}", exc_info=True)
        if 'entry' in locals() and not entry.mood: # If entry exists and mood wasn't set by user
            detected_mood_value = 'neutral' # Fallback on unexpected error
            entry.mood = detected_mood_value
    finally:
        try:
            entry_to_update_status = JournalEntry.objects.get(pk=journal_entry_id)
            if detected_mood_value and not entry_to_update_status.mood: # If AI determined a mood and user hadn't set one
                 entry_to_update_status.mood = detected_mood_value
            entry_to_update_status.ai_mood_processed = True
            entry_to_update_status.save(update_fields=['mood', 'ai_mood_processed'])
            logger.info(f"Mood task status for entry {journal_entry_id} set to processed. Final mood: {entry_to_update_status.mood}")
        except JournalEntry.DoesNotExist:
            pass 
        except Exception as e_save_status:
            logger.error(f"Error saving mood/status for entry {journal_entry_id} in mood task finally: {e_save_status}", exc_info=True)
            
    logger.info(f"--- detect_mood_for_entry_task_explicit COMPLETED for entry ID: {journal_entry_id} ---")
    return f"Mood detection processed for entry {journal_entry_id}. Success: {task_succeeded}"


@shared_task(bind=True, max_retries=3, default_retry_delay=50, acks_late=True, name='ai_services.tasks.suggest_tags_for_entry_task_explicit')
def suggest_tags_for_entry_task(self, journal_entry_id):
    from journal.models import JournalEntry, Tag
    logger.info(f"--- suggest_tags_for_entry_task_explicit STARTED --- Entry ID: {journal_entry_id}")
    task_succeeded = False
    ai_suggested_tag_names = []

    try:
        entry = JournalEntry.objects.get(pk=journal_entry_id)
        if entry.tags.exists(): 
            logger.info(f"User already set tags for JournalEntry ID: {entry.id}. AI tag suggestion skipped.")
            task_succeeded = True 
        else:
            logger.info(f"Suggesting tags for JournalEntry ID: {entry.id} using AI, as no user tags were found.")
            content_snippet = (entry.content[:2000] + '...') if len(entry.content) > 2000 else entry.content # Larger snippet for tags

            # Get some existing tag names to potentially guide the AI, but not strictly enforce them
            existing_tag_names = list(Tag.objects.values_list('name', flat=True).distinct().order_by('?')[:20]) # Get 20 random existing tags
            existing_tags_hint = ""
            if existing_tag_names:
                existing_tags_hint = f"You can also consider if any of these existing tags are relevant: {', '.join(existing_tag_names)}. "


            prompt_text = (
                f"Analyze the following journal entry, which can be in any language. "
                f"Based on its content, themes, and topics, suggest 1 to 3 relevant tags. "
                f"Each tag should be a single word or a short 2-3 word phrase. "
                f"{existing_tags_hint}" # Add hint about existing tags
                f"Return the suggested tags as a comma-separated list (e.g., Tag1, Another Tag, Example). "
                f"Do not provide any explanation or other text, only the comma-separated list of tags.\n\n"
                f"Journal Entry Content:\n\"\"\"\n{content_snippet}\n\"\"\"\n\n"
                f"Suggested Tags (comma-separated):"
            )

            ai_response_content = call_openrouter_api(prompt_text, entry.id, "tag_suggestion", max_tokens=50, temperature=0.5)

            if ai_response_content:
                # Split by comma, strip whitespace, capitalize, and filter empty strings
                raw_tags = [tag.strip() for tag in ai_response_content.split(',')]
                for raw_tag in raw_tags:
                    if not raw_tag: continue
                    # Capitalize each word in the tag
                    capitalized_tag = ' '.join(word.capitalize() for word in raw_tag.split())
                    if capitalized_tag and len(capitalized_tag) <= 50: # Max length from Tag model
                         ai_suggested_tag_names.append(capitalized_tag)
                
                ai_suggested_tag_names = list(set(ai_suggested_tag_names)) # Remove duplicates

                if ai_suggested_tag_names:
                    logger.info(f"AI suggested tags for entry {entry.id}: {ai_suggested_tag_names}")
                    # The actual adding of tags will happen in the finally block
                    task_succeeded = True
                else:
                    logger.warning(f"AI response for tags was empty or invalid after processing for entry {entry.id}: '{ai_response_content}'")
            else:
                logger.warning(f"AI did not return content for tag suggestion for entry {entry.id}.")
        
    except JournalEntry.DoesNotExist:
        logger.error(f"JournalEntry ID {journal_entry_id} not found for tag suggestion.")
    except Exception as e:
        logger.error(f"Error in suggest_tags_for_entry_task for entry {journal_entry_id}: {e}", exc_info=True)
    finally:
        try:
            entry_to_update_status = JournalEntry.objects.get(pk=journal_entry_id)
            if ai_suggested_tag_names and not entry_to_update_status.tags.exists(): # Only add if AI suggested and user hasn't set any
                tags_to_add_instances = []
                for tag_name in ai_suggested_tag_names:
                    tag_instance, created = Tag.objects.get_or_create(
                        name__iexact=tag_name, # Case-insensitive check
                        defaults={'name': tag_name} # Save with the AI's capitalization
                    )
                    tags_to_add_instances.append(tag_instance)
                    logger.info(f"AI Tag: Adding/found '{tag_instance.name}' for entry {entry_to_update_status.id} (Created: {created})")
                if tags_to_add_instances:
                    entry_to_update_status.tags.add(*tags_to_add_instances)
                    logger.info(f"AI successfully added {len(tags_to_add_instances)} tags to entry {entry_to_update_status.id}.")
            
            entry_to_update_status.ai_tags_processed = True
            entry_to_update_status.save(update_fields=['ai_tags_processed']) # Also save tags implicitly if add() was called
            logger.info(f"Tag suggestion task status for entry {journal_entry_id} set to processed.")
        except JournalEntry.DoesNotExist:
            pass 
        except Exception as e_save_status:
            logger.error(f"Error saving tags/status for entry {journal_entry_id} in tag task finally: {e_save_status}", exc_info=True)

    logger.info(f"--- suggest_tags_for_entry_task_explicit COMPLETED for entry ID: {journal_entry_id} ---")
    return f"Tag suggestion processed for entry {journal_entry_id}. Success: {task_succeeded}"

