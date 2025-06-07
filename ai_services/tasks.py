# ai_services/tasks.py

import requests
import json
import logging
import datetime
import re
from celery import shared_task
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext as _

# Import models inside tasks to avoid circular dependencies
# from journal.models import JournalEntry, Tag 

logger = logging.getLogger(__name__)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
# Using a capable model for all tasks. Can be changed in settings.py.
AI_MODEL_FOR_ALL_TASKS = getattr(settings, 'AI_MODEL_FOR_JOURNAL_ANALYSIS', "openai/gpt-3.5-turbo")


def call_openrouter_api(prompt_text, task_name, max_tokens=250, temperature=0.6, response_format=None, entry_id=None):
    """
    Helper function to call the OpenRouter API, now with response_format support.

    Args:
        prompt_text (str): The prompt to send to the AI model.
        task_name (str): A descriptive name for the task, used for logging.
        max_tokens (int): The maximum number of tokens to generate.
        temperature (float): The sampling temperature.
        response_format (dict, optional): The desired response format (e.g., {"type": "json_object"}).
        entry_id (int or str, optional): An identifier for the log (e.g., user_id or entry_id).

    Returns:
        str: The content of the AI's response, or None on failure.
    """
    api_key = settings.OPENROUTER_API_KEY
    if not api_key:
        logger.error(f"OPENROUTER_API_KEY not found. Aborting {task_name}.")
        return None

    payload = {
        "model": AI_MODEL_FOR_ALL_TASKS,
        "messages": [{"role": "user", "content": prompt_text}],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if response_format:
        payload["response_format"] = response_format

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": getattr(settings, 'YOUR_SITE_URL', 'http://localhost:8000'),
        "X-Title": getattr(settings, 'YOUR_SITE_NAME', 'LifeLedger'),
    }

    log_identifier = f"entry/user {entry_id}" if entry_id else "a general request"
    try:
        logger.info(f"Requesting {task_name} from OpenRouter for {log_identifier}. Model: {payload['model']}.")
        response = requests.post(OPENROUTER_API_URL, headers=headers, data=json.dumps(payload), timeout=90)
        logger.info(f"OpenRouter API response status for {task_name} ({log_identifier}): {response.status_code}")
        response.raise_for_status()
        
        response_data = response.json()
        logger.debug(f"OpenRouter Raw Response for {task_name} ({log_identifier}): {json.dumps(response_data, indent=2)}")

        if response_data.get("choices") and len(response_data["choices"]) > 0:
            message = response_data["choices"][0].get("message", {})
            content = message.get("content")
            if content:
                return content.strip()
        
        error_detail = response_data.get("error", {}).get("message", f"No 'choices' or 'content' in API response for {task_name}.")
        logger.warning(f"Unexpected OpenRouter response for {task_name} ({log_identifier}): {error_detail}")
        return None
            
    except requests.exceptions.Timeout:
        logger.error(f"Timeout during OpenRouter API request for {task_name} ({log_identifier}).")
    except requests.exceptions.HTTPError as http_err:
        error_text = http_err.response.text[:200] if hasattr(http_err.response, 'text') else "Unknown HTTP Error"
        logger.error(f"OpenRouter API HTTPError for {task_name} ({log_identifier}): {http_err.response.status_code} - {error_text}")
    except requests.exceptions.RequestException as req_err:
        logger.error(f"OpenRouter API request failed for {task_name} ({log_identifier}): {req_err}", exc_info=True)
    except Exception as e:
        logger.error(f"Unexpected error calling OpenRouter API for {task_name} ({log_identifier}): {e}", exc_info=True)
    
    return None


@shared_task(bind=True, max_retries=3, default_retry_delay=60 * 2, acks_late=True, name='ai_services.tasks.generate_quote_for_entry_task_explicit')
def generate_quote_for_entry_task(self, journal_entry_id):
    # ... (code is unchanged) ...
    from journal.models import JournalEntry
    logger.info(f"--- generate_quote_for_entry_task_explicit STARTED --- Entry ID: {journal_entry_id}")
    task_succeeded = False
    generated_quote_text = "Failed to generate quote." 
    try:
        entry = JournalEntry.objects.get(pk=journal_entry_id)
        content_snippet = (entry.content[:1000] + '...') if len(entry.content) > 1000 else entry.content
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
        ai_response_content = call_openrouter_api(prompt_text, "quote_generation", max_tokens=120, temperature=0.7, entry_id=entry.id)
        if ai_response_content:
            processed_quote = ai_response_content
            preambles_to_check = ["quote:", "here's a quote:", "a fitting quote could be:", "certainly, here is a quote:", "here is a quote:"]
            temp_lower_quote = processed_quote.lower()
            for preamble in preambles_to_check:
                if temp_lower_quote.startswith(preamble):
                    processed_quote = processed_quote[len(preamble):].strip()
                    break 
            if processed_quote.startswith('"') and processed_quote.endswith('"'):
                processed_quote = processed_quote[1:-1]
            generated_quote_text = processed_quote.strip()
            if generated_quote_text:
                task_succeeded = True
                logger.info(f"Successfully generated and processed quote for entry {entry.id}: \"{generated_quote_text}\"")
            else:
                generated_quote_text = "AI quote was empty after processing."
        else:
            logger.warning(f"Failed to get valid content from AI for quote generation (entry {entry.id}).")
    except JournalEntry.DoesNotExist:
        logger.error(f"JournalEntry {journal_entry_id} not found for quote generation.")
        generated_quote_text = "Entry not found for quote."
    except Exception as exc: 
        logger.error(f"Unexpected error in quote generation task for entry {journal_entry_id}: {exc}", exc_info=True)
        generated_quote_text = "Unexpected error generating quote."
    finally:
        try:
            entry_to_update = JournalEntry.objects.get(pk=journal_entry_id) 
            entry_to_update.ai_quote = generated_quote_text 
            entry_to_update.ai_quote_processed = True 
            entry_to_update.save(update_fields=['ai_quote', 'ai_quote_processed'])
            logger.info(f"Final ai_quote and status for entry {entry_to_update.id} saved.")
        except JournalEntry.DoesNotExist:
            logger.error(f"JournalEntry {journal_entry_id} not found in finally block for quote task.")
        except Exception as e_save:
            logger.error(f"Error saving ai_quote/status for entry {journal_entry_id} in quote task finally: {e_save}", exc_info=True)
    logger.info(f"--- generate_quote_for_entry_task_explicit COMPLETED for entry ID: {journal_entry_id} ---")
    return f"Quote generation task processed for entry {journal_entry_id}. Success: {task_succeeded}"


@shared_task(bind=True, max_retries=3, default_retry_delay=45, acks_late=True, name='ai_services.tasks.detect_mood_for_entry_task_explicit')
def detect_mood_for_entry_task(self, journal_entry_id):
    # ... (code is unchanged) ...
    from journal.models import JournalEntry
    logger.info(f"--- detect_mood_for_entry_task_explicit STARTED --- Entry ID: {journal_entry_id}")
    task_succeeded = False
    detected_mood_value = None 
    try:
        entry = JournalEntry.objects.get(pk=journal_entry_id)
        if entry.mood: 
            logger.info(f"User already set mood ('{entry.mood}') for JournalEntry ID: {entry.id}. AI mood detection skipped.")
            task_succeeded = True 
        else:
            logger.info(f"Detecting mood for JournalEntry ID: {entry.id} using AI.")
            content_snippet = (entry.content[:1500] + '...') if len(entry.content) > 1500 else entry.content
            valid_moods = [choice[0] for choice in JournalEntry.MOOD_CHOICES]
            mood_options_str = ", ".join(valid_moods)
            prompt_text = (
                f"Analyze the sentiment and emotional tone of the following journal entry, which can be in any language. "
                f"Based on your analysis, determine the primary mood. "
                f"You MUST choose exactly ONE mood from the following predefined list: {mood_options_str}. "
                f"Do not provide any explanation or other text, only the single mood word.\n\n"
                f"Journal Entry Content:\n\"\"\"\n{content_snippet}\n\"\"\"\n\n"
                f"Primary Mood (choose one from list above):"
            )
            ai_response_content = call_openrouter_api(prompt_text, "mood_detection", max_tokens=10, temperature=0.3, entry_id=entry.id)
            if ai_response_content:
                potential_mood = ai_response_content.split()[0].lower().strip().replace("\"", "").replace(".", "")
                if potential_mood in valid_moods:
                    detected_mood_value = potential_mood
                    entry.mood = detected_mood_value
                    task_succeeded = True
                    logger.info(f"AI successfully detected mood as '{detected_mood_value}' for entry ID: {entry.id}")
                else:
                    logger.warning(f"AI returned an invalid mood ('{ai_response_content}') for entry {entry.id}. Falling back to neutral.")
                    detected_mood_value = 'neutral'
                    entry.mood = detected_mood_value
            else:
                logger.warning(f"AI did not return content for mood detection for entry {entry.id}. Falling back to neutral.")
                detected_mood_value = 'neutral'
                entry.mood = detected_mood_value
    except JournalEntry.DoesNotExist:
        logger.error(f"JournalEntry ID {journal_entry_id} not found for mood detection.")
    except Exception as e:
        logger.error(f"Error in detect_mood_for_entry_task for entry {journal_entry_id}: {e}", exc_info=True)
        if 'entry' in locals() and not entry.mood:
            detected_mood_value = 'neutral'
            entry.mood = detected_mood_value
    finally:
        try:
            entry_to_update_status = JournalEntry.objects.get(pk=journal_entry_id)
            if detected_mood_value and not entry_to_update_status.mood:
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
    # ... (code is unchanged) ...
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
            content_snippet = (entry.content[:2000] + '...') if len(entry.content) > 2000 else entry.content
            existing_tag_names = list(Tag.objects.values_list('name', flat=True).distinct().order_by('?')[:20])
            existing_tags_hint = ""
            if existing_tag_names:
                existing_tags_hint = f"You can also consider if any of these existing tags are relevant: {', '.join(existing_tag_names)}. "
            prompt_text = (
                f"Analyze the following journal entry, which can be in any language. "
                f"Based on its content, themes, and topics, suggest 1 to 3 relevant tags. "
                f"Each tag should be a single word or a short 2-3 word phrase. "
                f"{existing_tags_hint}"
                f"Return the suggested tags as a comma-separated list (e.g., Tag1, Another Tag, Example). "
                f"Do not provide any explanation or other text, only the comma-separated list of tags.\n\n"
                f"Journal Entry Content:\n\"\"\"\n{content_snippet}\n\"\"\"\n\n"
                f"Suggested Tags (comma-separated):"
            )
            ai_response_content = call_openrouter_api(prompt_text, "tag_suggestion", max_tokens=50, temperature=0.5, entry_id=entry.id)
            if ai_response_content:
                raw_tags = [tag.strip() for tag in ai_response_content.split(',')]
                for raw_tag in raw_tags:
                    if not raw_tag: continue
                    capitalized_tag = ' '.join(word.capitalize() for word in raw_tag.split())
                    if capitalized_tag and len(capitalized_tag) <= 50:
                         ai_suggested_tag_names.append(capitalized_tag)
                ai_suggested_tag_names = list(set(ai_suggested_tag_names)) 
                if ai_suggested_tag_names:
                    logger.info(f"AI suggested tags for entry {entry.id}: {ai_suggested_tag_names}")
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
            if ai_suggested_tag_names and not entry_to_update_status.tags.exists():
                tags_to_add_instances = []
                for tag_name in ai_suggested_tag_names:
                    tag_instance, created = Tag.objects.get_or_create(
                        name__iexact=tag_name, 
                        defaults={'name': tag_name} 
                    )
                    tags_to_add_instances.append(tag_instance)
                    logger.info(f"AI Tag: Adding/found '{tag_instance.name}' for entry {entry_to_update_status.id} (Created: {created})")
                if tags_to_add_instances:
                    entry_to_update_status.tags.add(*tags_to_add_instances)
                    logger.info(f"AI successfully added {len(tags_to_add_instances)} tags to entry {entry_to_update_status.id}.")
            
            entry_to_update_status.ai_tags_processed = True
            entry_to_update_status.save(update_fields=['ai_tags_processed']) 
            logger.info(f"Tag suggestion task status for entry {journal_entry_id} set to processed.")
        except JournalEntry.DoesNotExist:
            pass 
        except Exception as e_save_status:
            logger.error(f"Error saving tags/status for entry {journal_entry_id} in tag task finally: {e_save_status}", exc_info=True)
    logger.info(f"--- suggest_tags_for_entry_task_explicit COMPLETED for entry ID: {journal_entry_id} ---")
    return f"Tag suggestion processed for entry {journal_entry_id}. Success: {task_succeeded}"


@shared_task(bind=True, name='ai_services.tasks.generate_insights_for_period_task')
def generate_insights_for_period_task(self, user_id, time_period):
    # ... (code is unchanged) ...
    from django.contrib.auth import get_user_model
    from journal.models import JournalEntry

    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.error(f"User with ID {user_id} not found for insights task.")
        return {'error': 'User not found.'}

    logger.info(f"--- generate_insights_for_period_task STARTED --- User: {user.username}, Period: {time_period}")

    end_date = timezone.now()
    start_date = None
    if time_period == 'last_7_days':
        start_date = end_date - datetime.timedelta(days=7)
    elif time_period == 'last_30_days':
        start_date = end_date - datetime.timedelta(days=30)
    elif time_period == 'last_90_days':
        start_date = end_date - datetime.timedelta(days=90)
    
    entries_query = JournalEntry.objects.filter(user=user)
    if start_date:
        entries_query = entries_query.filter(created_at__gte=start_date)
    
    entries = entries_query.order_by('created_at').only('created_at', 'content')
    
    if not entries.exists():
        logger.warning(f"No entries found for user {user.username} in period {time_period}. Aborting insights task.")
        return {'error': 'No entries found for this period.', 'highlights': [], 'challenges': [], 'key_themes': []}

    combined_content = ""
    word_limit = 4000 
    for entry in entries:
        entry_text = f"\n--- Entry from {entry.created_at.strftime('%Y-%m-%d')} ---\n{entry.content}\n"
        if len(combined_content.split()) + len(entry_text.split()) > word_limit:
            break
        combined_content += entry_text

    prompt_text = (
        f"You are an insightful and empathetic life coach. Analyze the following collection of journal entries from a user. "
        f"Your task is to identify and summarize the key points into three categories: Highlights, Challenges, and Key Themes. "
        f"The entries can be in any language, so analyze them accordingly.\n\n"
        f"1.  **Highlights**: Identify and list 2-4 key positive moments, achievements, sources of joy, or significant progress mentioned. "
        f"2.  **Challenges**: Identify and list 2-4 main difficulties, struggles, or sources of frustration the user faced. "
        f"3.  **Key Themes**: Identify 2-4 overarching themes or recurring topics that appear throughout the entries (e.g., 'Work-life balance', 'Exploring a new hobby', 'Family relationships').\n\n"
        f"Please provide your response strictly in the following JSON format, with no introductory text or markdown formatting:\n"
        f'{{"highlights": ["Point 1", "Point 2", ...], "challenges": ["Point 1", "Point 2", ...], "key_themes": ["Theme 1", "Theme 2", ...]}}\n\n'
        f"Journal Entries Collection:\n\"\"\"\n{combined_content}\n\"\"\""
    )

    ai_response_str = call_openrouter_api(
        prompt_text, "collective_insights_generation", max_tokens=1000, 
        temperature=0.5, response_format={"type": "json_object"}, entry_id=user_id
    )

    if not ai_response_str:
        logger.error(f"Failed to get a response from AI for collective insights (User: {user.username}).")
        return {'error': 'AI service did not respond.'}

    try:
        # Attempt to find a JSON object within the response string if it's not a clean JSON
        json_match = re.search(r'\{.*\}', ai_response_str, re.DOTALL)
        if not json_match:
            raise ValueError("No valid JSON object found in the AI response.")
        
        insights_data = json.loads(json_match.group(0))
        
        if not all(k in insights_data for k in ['highlights', 'challenges', 'key_themes']):
            raise ValueError("AI response is missing one of the required keys.")
        
        logger.info(f"Successfully generated insights for user {user.username}.")
        return insights_data

    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Failed to parse or validate JSON response from AI for collective insights (User: {user.username}): {e}")
        logger.debug(f"Raw AI response was: {ai_response_str}")
        return {'error': 'Failed to process AI response.'}


# --- NEW TASK FOR LIFE SUGGESTIONS ---

@shared_task(bind=True, name='ai_services.tasks.generate_life_suggestions_task')
def generate_life_suggestions_task(self, user_id, insights_data):
    """
    Takes a summary of insights (highlights, challenges) and generates
    actionable, empathetic suggestions for the user.

    Args:
        user_id (int): The ID of the user for whom to generate suggestions.
        insights_data (dict): A dictionary containing 'highlights' and 'challenges' lists.

    Returns:
        dict: A dictionary containing a list of suggestions or an error message.
    """
    from django.contrib.auth import get_user_model

    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.error(f"User with ID {user_id} not found for suggestions task.")
        return {'error': 'User not found.'}

    logger.info(f"--- generate_life_suggestions_task STARTED --- User: {user.username}")

    # Prepare the context from the previous analysis task
    highlights = insights_data.get('highlights', [])
    challenges = insights_data.get('challenges', [])
    
    if not highlights and not challenges:
        logger.warning(f"No highlights or challenges provided for user {user.username}. Cannot generate suggestions.")
        return {'suggestions': [_("No specific insights were found to generate suggestions from.")]}

    # Format the context for the prompt
    highlights_str = "\n- ".join(highlights) if highlights else "None"
    challenges_str = "\n- ".join(challenges) if challenges else "None"

    prompt_text = (
        f"You are a supportive and insightful life coach. Your client has shared the following summary from their journal. "
        f"Your task is to provide 2-3 actionable, empathetic, and encouraging suggestions based on this summary. "
        f"Avoid generic advice. Focus on building on the highlights and providing constructive ways to approach the challenges.\n\n"
        f"**User's Highlights:**\n- {highlights_str}\n\n"
        f"**User's Challenges:**\n- {challenges_str}\n\n"
        f"Based on this, generate your suggestions. "
        f"Return your response strictly in the following JSON format, with no other text:\n"
        f'{{"suggestions": ["Suggestion 1...", "Suggestion 2...", "Suggestion 3..."]}}'
    )
    
    ai_response_str = call_openrouter_api(
        prompt_text,
        "life_suggestions_generation",
        max_tokens=500,
        temperature=0.7,
        response_format={"type": "json_object"},
        entry_id=user_id
    )

    if not ai_response_str:
        logger.error(f"Failed to get a response from AI for life suggestions (User: {user.username}).")
        return {'error': _('AI service did not respond.')}

    try:
        # Attempt to find a JSON object within the response string
        json_match = re.search(r'\{.*\}', ai_response_str, re.DOTALL)
        if not json_match:
            raise ValueError("No valid JSON object found in the AI response for suggestions.")
        
        suggestions_data = json.loads(json_match.group(0))

        if 'suggestions' not in suggestions_data or not isinstance(suggestions_data['suggestions'], list):
             raise ValueError("AI response for suggestions is not in the expected format.")

        logger.info(f"Successfully generated life suggestions for user {user.username}.")
        return suggestions_data

    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Failed to parse or validate JSON response from AI for suggestions (User: {user.username}): {e}")
        logger.debug(f"Raw AI response was: {ai_response_str}")
        return {'error': _('Failed to process AI suggestions.')}
