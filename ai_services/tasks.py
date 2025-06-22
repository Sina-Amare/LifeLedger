# ai_services/tasks.py

import os
import requests
import json
import logging
import datetime
import re
from celery import shared_task
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext as _
from dotenv import load_dotenv

# --- FIX: Load environment variables for the Celery worker ---
# This ensures that the OPENROUTER_API_KEY is available when the task runs
# in a separate process from the main Django application.
# It assumes your .env file is in the project's root directory.
env_path = os.path.join(settings.BASE_DIR, '.env')
if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path)

# Models are imported directly inside tasks to prevent potential circular 
# dependency issues during application startup.
logger = logging.getLogger(__name__)

# Centralized API configuration for consistency and ease of maintenance.
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
AI_MODEL_FOR_ALL_TASKS = getattr(settings, 'AI_MODEL_FOR_JOURNAL_ANALYSIS', "openai/gpt-3.5-turbo")


def call_openrouter_api(prompt_text, task_name, max_tokens=250, temperature=0.6, response_format=None, entry_id=None):
    """
    A robust helper function to make API calls to the OpenRouter service.

    This function handles the construction of the request payload, headers,
    and comprehensive error handling, including network timeouts and HTTP errors.

    Args:
        prompt_text (str): The prompt to send to the AI model.
        task_name (str): A descriptive name for the task, used for logging purposes.
        max_tokens (int): The maximum number of tokens for the AI to generate.
        temperature (float): The sampling temperature for the generation (0.0 to 1.0).
        response_format (dict, optional): Specifies a required response format (e.g., {"type": "json_object"}).
        entry_id (int or str, optional): An identifier for logging context (e.g., user_id or entry_id).

    Returns:
        str: The content of the AI's response as a string, or None if an error occurs.
    """
    # The API key is now reliably loaded from the environment.
    api_key = os.getenv('OPENROUTER_API_KEY')
    if not api_key:
        logger.error(f"FATAL: OPENROUTER_API_KEY not found. Aborting {task_name}. Please check your .env file and restart the Celery worker.")
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
        response.raise_for_status()
        
        response_data = response.json()
        logger.debug(f"OpenRouter Raw Response for {task_name} ({log_identifier}): {json.dumps(response_data, indent=2)}")

        if response_data.get("choices") and len(response_data["choices"]) > 0:
            message = response_data["choices"][0].get("message", {})
            content = message.get("content")
            if content:
                return content.strip()
        
        error_detail = response_data.get("error", {}).get("message", "No 'choices' or 'content' in API response.")
        logger.warning(f"Unexpected OpenRouter response for {task_name} ({log_identifier}): {error_detail}")
        return None
        
    except requests.exceptions.Timeout:
        logger.error(f"Timeout during OpenRouter API request for {task_name} ({log_identifier}).")
    except requests.exceptions.HTTPError as http_err:
        error_text = http_err.response.text[:200] if hasattr(http_err.response, 'text') else "Unknown HTTP Error"
        logger.error(f"OpenRouter API HTTPError for {task_name} ({log_identifier}): {http_err.response.status_code} - {error_text}")
    except Exception as e:
        logger.error(f"Unexpected error calling OpenRouter API for {task_name} ({log_identifier}): {e}", exc_info=True)
    
    return None

@shared_task(bind=True, max_retries=3, default_retry_delay=60 * 2, acks_late=True)
def generate_quote_for_entry_task(self, journal_entry_id):
    """
    Celery task to generate an insightful and relevant quote for a specific journal entry.
    It fetches the entry, constructs a prompt, calls the AI, and updates the entry.
    """
    from journal.models import JournalEntry
    logger.info(f"Starting quote generation task for Entry ID: {journal_entry_id}")
    generated_quote_text = _("Could not generate a quote at this time.")
    
    try:
        entry = JournalEntry.objects.get(pk=journal_entry_id)
        content_snippet = (entry.content[:1000] + '...') if len(entry.content) > 1000 else entry.content
        
        prompt = (
            f"Analyze the following journal entry snippet. Provide ONE single, short (1-2 sentences), insightful quote from a well-known Persian (Iranian) "
            f"OR English-speaking figure that is highly relevant to the themes expressed. Format the response as: \"Quote text.\" - Author's Name. "
            f"If the snippet is too vague, select a general inspiring quote about life or growth.\n\n"
            f"Journal Entry Snippet:\n\"\"\"\n{content_snippet}\n\"\"\"\n\n"
            f"Provide only the quote and its attribution below:\n"
        )
        
        ai_response = call_openrouter_api(prompt, "quote_generation", max_tokens=120, temperature=0.7, entry_id=entry.id)
        
        if ai_response:
            generated_quote_text = ai_response.strip('" ')
            logger.info(f"Successfully generated quote for entry {entry.id}: \"{generated_quote_text}\"")
        else:
            logger.warning(f"AI service did not return valid content for quote generation (entry {entry.id}).")

    except JournalEntry.DoesNotExist:
        logger.error(f"JournalEntry {journal_entry_id} not found for quote generation task.")
    except Exception as exc: 
        logger.error(f"Retrying quote task for entry {journal_entry_id} due to unexpected error: {exc}", exc_info=True)
        self.retry(exc=exc)
    finally:
        JournalEntry.objects.filter(pk=journal_entry_id).update(
            ai_quote=generated_quote_text,
            ai_quote_processed=True
        )
        logger.info(f"Quote generation task completed and status saved for entry ID: {journal_entry_id}")


@shared_task(bind=True, max_retries=3, default_retry_delay=45, acks_late=True)
def detect_mood_for_entry_task(self, journal_entry_id):
    """
    Celery task to detect the primary mood of a journal entry using AI analysis.
    If a mood is already set by the user, this task will be skipped.
    """
    from journal.models import JournalEntry
    from journal.constants import MOOD_CHOICES
    
    logger.info(f"Starting mood detection task for Entry ID: {journal_entry_id}")
    
    try:
        entry = JournalEntry.objects.get(pk=journal_entry_id)
        if entry.mood: 
            logger.info(f"Mood ('{entry.mood}') was already set for entry {entry.id}. Skipping AI detection.")
        else:
            content_snippet = (entry.content[:1500] + '...') if len(entry.content) > 1500 else entry.content
            valid_moods = [choice[0] for choice in MOOD_CHOICES]
            mood_options_str = ", ".join(valid_moods)
            
            prompt = (
                f"Analyze the emotional tone of the journal entry below. "
                f"Choose exactly ONE primary mood from the list: {mood_options_str}. "
                f"Return only the single, lowercase mood word.\n\n"
                f"Journal Entry:\n\"\"\"\n{content_snippet}\n\"\"\"\n\n"
                f"Primary Mood:"
            )
            
            ai_response = call_openrouter_api(prompt, "mood_detection", max_tokens=10, temperature=0.2, entry_id=entry.id)
            
            detected_mood = 'neutral'  # Default fallback
            if ai_response:
                potential_mood = ai_response.lower().strip().split()[0].strip('".')
                if potential_mood in valid_moods:
                    detected_mood = potential_mood
                    logger.info(f"AI successfully detected mood as '{detected_mood}' for entry {entry.id}")
                else:
                    logger.warning(f"AI returned an invalid mood ('{ai_response}'). Falling back to neutral for entry {entry.id}.")
            else:
                logger.warning(f"AI did not return content for mood detection. Falling back to neutral for entry {entry.id}.")
            
            entry.mood = detected_mood
            entry.save(update_fields=['mood'])

    except JournalEntry.DoesNotExist:
        logger.error(f"JournalEntry ID {journal_entry_id} not found for mood detection.")
    except Exception as e:
        logger.error(f"Retrying mood task for entry {journal_entry_id} due to error: {e}", exc_info=True)
        self.retry(exc=e)
    finally:
        JournalEntry.objects.filter(pk=journal_entry_id).update(ai_mood_processed=True)
        logger.info(f"Mood detection task completed and status saved for entry ID: {journal_entry_id}")


@shared_task(bind=True, max_retries=3, default_retry_delay=50, acks_late=True)
def suggest_tags_for_entry_task(self, journal_entry_id):
    """
    Celery task to suggest and apply relevant, *pre-existing* tags for a journal entry.

    This task fetches all available tags from the database and instructs the AI
    to choose only from that list. This prevents the creation of new, unwanted tags.
    If no relevant tags are found, it applies a default 'General' tag.
    """
    from journal.models import JournalEntry, Tag
    logger.info(f"Starting tag suggestion task for Entry ID: {journal_entry_id}")
    
    try:
        entry = JournalEntry.objects.get(pk=journal_entry_id)
        if entry.tags.exists(): 
            logger.info(f"Tags already exist for entry {entry.id}. Skipping AI suggestion.")
        else:
            # Step 1: Get all predefined tag names to provide as context to the AI.
            available_tags = list(Tag.objects.values_list('name', flat=True))
            if not available_tags:
                logger.warning(f"No predefined tags found in the database. Cannot suggest tags for entry {entry.id}.")
                entry.ai_tags_processed = True
                entry.save(update_fields=['ai_tags_processed'])
                return

            tag_options_str = ", ".join(available_tags)
            content_snippet = (entry.content[:2000] + '...') if len(entry.content) > 2000 else entry.content
            
            # Step 2: Create a more precise prompt for the AI.
            prompt = (
                f"Analyze the following journal entry. From the list of available tags below, "
                f"select up to 3 that are the most relevant. Your response must be a single, "
                f"comma-separated list containing ONLY tags from the provided list.\n\n"
                f"AVAILABLE TAGS:\n[{tag_options_str}]\n\n"
                f"JOURNAL ENTRY:\n\"\"\"\n{content_snippet}\n\"\"\"\n\n"
                f"Relevant Tags from List:"
            )
            
            ai_response = call_openrouter_api(prompt, "tag_suggestion", max_tokens=50, temperature=0.3, entry_id=entry.id)
            
            if ai_response:
                # Step 3: Process the response and validate against existing tags.
                # Create a case-insensitive map for robust matching.
                available_tags_map = {name.lower(): name for name in available_tags}
                
                # Clean up the AI response.
                raw_tags = [tag.strip(' ".,').capitalize() for tag in ai_response.split(',') if tag.strip()]
                
                valid_tag_names = set()
                for tag_name in raw_tags:
                    if tag_name.lower() in available_tags_map:
                        # Use the original capitalization from the database.
                        valid_tag_names.add(available_tags_map[tag_name.lower()])

                logger.info(f"AI suggested: {raw_tags}. Validated against existing tags: {list(valid_tag_names)}")
                
                # Step 4: Apply the valid tags, or a fallback tag.
                tags_to_add = []
                if valid_tag_names:
                    tags_to_add = Tag.objects.filter(name__in=valid_tag_names)
                else:
                    logger.warning(f"No valid tags were identified from AI response for entry {entry.id}. Applying 'General' fallback.")
                    # Use get_or_create for the fallback to ensure it exists.
                    general_tag, _ = Tag.objects.get_or_create(name='General', defaults={'emoji': '🗒️'})
                    tags_to_add = [general_tag]
                
                if tags_to_add:
                    entry.tags.add(*tags_to_add)
                    logger.info(f"Successfully applied tags {[t.name for t in tags_to_add]} to entry {entry.id}")
            else:
                logger.warning(f"AI did not return content for tag suggestion for entry {entry.id}.")

    except JournalEntry.DoesNotExist:
        logger.error(f"JournalEntry ID {journal_entry_id} not found for tag suggestion.")
    except Exception as e:
        logger.error(f"Retrying tag task for entry {journal_entry_id} due to error: {e}", exc_info=True)
        self.retry(exc=e)
    finally:
        JournalEntry.objects.filter(pk=journal_entry_id).update(ai_tags_processed=True)
        logger.info(f"Tag suggestion task completed and status saved for entry ID: {journal_entry_id}")


@shared_task(bind=True, name='ai_services.tasks.generate_insights_for_period_task')
def generate_insights_for_period_task(self, user_id, time_period):
    """
    Analyzes a user's journal entries over a specified period to extract
    key highlights, challenges, and recurring themes.
    """
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
        logger.warning(f"No entries found for user {user.username} in period {time_period}.")
        return {'highlights': [], 'challenges': [], 'key_themes': []}

    combined_content = ""
    for entry in entries:
        combined_content += f"\n--- Entry from {entry.created_at.strftime('%Y-%m-%d')} ---\n{entry.content}\n"
    
    prompt = (
        "You are an insightful life coach. Analyze this collection of journal entries. "
        "Summarize the key points into three categories: 'highlights', 'challenges', and 'key_themes'. "
        "List 2-4 points for each. If a category is empty, return an empty list for it. "
        "Respond ONLY with a valid JSON object.\n\n"
        f"Journal Entries:\n\"\"\"\n{combined_content}\n\"\"\""
    )

    ai_response_str = call_openrouter_api(prompt, "collective_insights", max_tokens=1000, temperature=0.5, response_format={"type": "json_object"}, entry_id=user_id)

    if not ai_response_str:
        logger.error(f"Failed to get AI response for collective insights (User: {user.username}).")
        return {'error': 'AI service did not respond.'}

    try:
        json_match = re.search(r'\{.*\}', ai_response_str, re.DOTALL)
        if not json_match:
            raise ValueError("No valid JSON object found in AI response for insights.")
        
        insights_data = json.loads(json_match.group(0))
        
        if not all(k in insights_data for k in ['highlights', 'challenges', 'key_themes']):
            raise ValueError("AI response is missing required keys for insights.")
        
        logger.info(f"Successfully generated insights for user {user.username}.")
        return insights_data

    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Failed to parse insights JSON from AI (User: {user.username}): {e}", exc_info=True)
        return {'error': 'Failed to process AI response.'}


@shared_task(bind=True, name='ai_services.tasks.generate_life_suggestions_task')
def generate_life_suggestions_task(self, user_id, insights_data):
    """
    Takes a summary of insights and generates actionable, empathetic suggestions for the user.
    The prompt for this task is engineered to be more directive and provide better results.
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.error(f"User with ID {user_id} not found for suggestions task.")
        return {'error': 'User not found.'}

    logger.info(f"--- generate_life_suggestions_task STARTED --- User: {user.username}")

    highlights = insights_data.get('highlights', [])
    challenges = insights_data.get('challenges', [])
    
    if not highlights and not challenges:
        logger.warning(f"No specific highlights or challenges provided for user {user.username}. Returning a default suggestion.")
        return {'suggestions': [_("Keep reflecting on your days. Each entry is a valuable piece of your personal story.")]}

    highlights_str = "- " + "\n- ".join(highlights) if highlights else _("None provided.")
    challenges_str = "- " + "\n- ".join(challenges) if challenges else _("None provided.")

    # This improved prompt gives the AI a clear persona and structured instructions,
    # leading to more consistent and helpful suggestions.
    prompt_text = (
        "You are an empathetic and action-oriented AI life coach. Your client has shared the following summary from their journal. "
        "Your task is to provide 2-3 concrete, encouraging, and actionable suggestions based on this summary. "
        "Directly address the user's points.\n\n"
        "**User's Highlights (Things that went well):**\n"
        f"{highlights_str}\n\n"
        "**User's Challenges (Things that were difficult):**\n"
        f"{challenges_str}\n\n"
        "**Your Task:**\n"
        "1. **Acknowledge and Build:** Start with a suggestion that builds on a highlight (e.g., 'It's wonderful you felt [Highlight]. How can you plan a similar moment for next week?').\n"
        "2. **Offer a Small Step:** Provide a gentle, manageable suggestion for one of the challenges (e.g., 'Regarding [Challenge], perhaps you could try dedicating just 5 minutes to [small action] to make it feel less overwhelming.').\n"
        "3. **Provide an Insightful Question:** End with a thoughtful question that encourages deeper reflection.\n"
        "4. **Important:** Respond ONLY with a JSON object in the format: "
        '{"suggestions": ["Suggestion 1...", "Suggestion 2...", "Suggestion 3..."]}. '
        "Do NOT add any introductory text, markdown, or explanations outside of the JSON."
    )
    
    ai_response_str = call_openrouter_api(
        prompt_text, "life_suggestions_generation", max_tokens=500,
        temperature=0.7, response_format={"type": "json_object"}, entry_id=user_id
    )

    if not ai_response_str:
        logger.error(f"Failed to get a response from AI for life suggestions (User: {user.username}).")
        return {'error': _('AI service did not respond.')}

    try:
        json_match = re.search(r'\{.*\}', ai_response_str, re.DOTALL)
        if not json_match:
            raise ValueError("No valid JSON object found in the AI response for suggestions.")
        
        suggestions_data = json.loads(json_match.group(0))

        if 'suggestions' not in suggestions_data or not isinstance(suggestions_data.get('suggestions'), list) or not suggestions_data.get('suggestions'):
            raise ValueError("AI response for suggestions is not in the expected format or is empty.")

        logger.info(f"Successfully generated life suggestions for user {user.username}.")
        return suggestions_data

    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Failed to parse or validate JSON response from AI for suggestions (User: {user.username}): {e}", exc_info=True)
        logger.debug(f"Raw AI response for suggestions was: {ai_response_str}")
        return {'error': _('Failed to process AI suggestions.')}
