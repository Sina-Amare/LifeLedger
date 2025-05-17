# journal/tests.py

import os
import shutil
import uuid 
import logging

from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from django.utils.html import escape

from .models import JournalEntry, JournalAttachment, Tag, user_directory_path
from .forms import JournalEntryForm, JournalAttachmentForm, MOOD_CHOICES_FORM_DISPLAY

User = get_user_model()
logger = logging.getLogger('journal.tests') 

TEST_MEDIA_ROOT_JOURNAL = os.path.join(settings.BASE_DIR, f'test_media_root_journal_app_{uuid.uuid4().hex[:8]}')

@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT_JOURNAL)
class JournalModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user1_username = f'model_user1_journal_{uuid.uuid4().hex[:6]}'
        cls.user1 = User.objects.create_user(username=cls.user1_username, email=f'{cls.user1_username}@example.com', password='password123')
        
        cls.entry1 = JournalEntry.objects.create(
            user=cls.user1, title="Model Test Entry Alpha", content="Content for model test alpha.", mood="happy"
        )
        
        # Use get_or_create for predefined tags to avoid IntegrityError
        cls.tag_work, _ = Tag.objects.get_or_create(name="Work", defaults={'emoji': '💼'})
        cls.tag_personal, _ = Tag.objects.get_or_create(name="Personal", defaults={'emoji': '🏠'})
        # If you need a tag that is definitely not predefined for some test:
        # cls.tag_custom_model_test = Tag.objects.create(name=f"CustomModelTest_{uuid.uuid4().hex[:4]}", emoji="🧪")

        cls.entry1.tags.add(cls.tag_work)

        cls.test_file_content_model = b"Alpha model test file content."
        cls.uploaded_file_model = SimpleUploadedFile(
            name=f"model_test_img_alpha_{uuid.uuid4().hex}.jpg", content=cls.test_file_content_model, content_type="image/jpeg"
        )
        cls.attachment1 = JournalAttachment.objects.create(journal_entry=cls.entry1, file=cls.uploaded_file_model, file_type='image')


    @classmethod
    def tearDownClass(cls):
        if os.path.exists(TEST_MEDIA_ROOT_JOURNAL):
            shutil.rmtree(TEST_MEDIA_ROOT_JOURNAL)
        super().tearDownClass()

    def test_tag_creation_and_str(self):
        self.assertEqual(str(self.tag_work), "💼 Work")
        self.assertEqual(str(self.tag_personal), "🏠 Personal")

    def test_journal_entry_creation_with_tags(self):
        self.assertEqual(self.entry1.title, "Model Test Entry Alpha")
        self.assertIn(self.tag_work, self.entry1.tags.all())

    def test_journal_entry_str(self):
        self.assertEqual(str(self.entry1), f"Entry for {self.user1.username}: {self.entry1.title}")

    def test_journal_entry_get_absolute_url(self):
        self.assertEqual(self.entry1.get_absolute_url(), reverse('journal:journal_detail', kwargs={'pk': self.entry1.pk}))

    def test_journal_attachment_creation(self):
        self.assertTrue(self.attachment1.file.name.startswith(f'user_{self.user1.id}/journal_attachments/'))
        self.assertEqual(self.attachment1.file_type, 'image')


    def test_journal_attachment_str(self):
        expected_str_start = f"Attachment for Entry {self.entry1.id}:"
        self.assertTrue(str(self.attachment1).startswith(expected_str_start))

    def test_user_directory_path_function(self):
        mock_attachment_instance = JournalAttachment(journal_entry=self.entry1)
        filename = "original_filename_beta.png"
        path = user_directory_path(mock_attachment_instance, filename)
        now = timezone.now()
        expected_prefix = f'user_{self.user1.id}/journal_attachments/{now.strftime("%Y/%m/%d")}/'
        self.assertTrue(path.startswith(expected_prefix))
        self.assertTrue(path.endswith('.png'))

    def test_journal_attachment_file_deletion_on_model_delete(self):
        entry = JournalEntry.objects.create(user=self.user1, title="Test Del Attach Final", content="...")
        uf = SimpleUploadedFile(f"del_file_final_{uuid.uuid4().hex}.txt", b"del_final", content_type="text/plain")
        att = JournalAttachment.objects.create(journal_entry=entry, file=uf, file_type='other')
        fp = att.file.path
        self.assertTrue(os.path.exists(fp), f"File {fp} should exist before delete.")
        att.delete()
        self.assertFalse(os.path.exists(fp), f"File {fp} should NOT exist after delete.")

    def test_journal_entry_cascade_delete_attachments_and_files(self):
        entry_title = f"Test Cascade Del Final {uuid.uuid4().hex[:4]}"
        entry = JournalEntry.objects.create(user=self.user1, title=entry_title, content="...")
        paths = []
        for i in range(2):
            uf = SimpleUploadedFile(f"cas_del_final_{i}_{uuid.uuid4().hex}.txt", f"cf{i}".encode(), content_type="text/plain")
            att = JournalAttachment.objects.create(journal_entry=entry, file=uf, file_type='other')
            paths.append(att.file.path)
        
        for p in paths: self.assertTrue(os.path.exists(p))
        entry.delete()
        for p in paths: self.assertFalse(os.path.exists(p))

@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT_JOURNAL)
class JournalFormTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_form_test = User.objects.create_user(username=f'form_user_{uuid.uuid4().hex[:6]}', email=f'form_user_{uuid.uuid4().hex[:6]}@example.com', password='password123')
        # Tags are populated by post_migrate signal, ensure they exist for tests
        Tag.objects.get_or_create(name="Work", defaults={'emoji': '💼'})
        Tag.objects.get_or_create(name="Personal", defaults={'emoji': '🏠'})


    @classmethod
    def tearDownClass(cls):
        if os.path.exists(TEST_MEDIA_ROOT_JOURNAL):
            shutil.rmtree(TEST_MEDIA_ROOT_JOURNAL)
        super().tearDownClass()

    def test_journal_entry_form_valid(self):
        valid_mood_key = ''
        if MOOD_CHOICES_FORM_DISPLAY and len(MOOD_CHOICES_FORM_DISPLAY) > 1:
            for val, _label in MOOD_CHOICES_FORM_DISPLAY:
                if val: 
                    valid_mood_key = val
                    break
        
        form_data = {
            'title': 'Valid Title Form Final', 
            'content': 'Valid content.', 
            'mood': valid_mood_key, 
            'location': 'Test Location Form Final', 
            'privacy_level': 'private', 
            'is_favorite': True,
            'tags': 'Work, New Custom Tag' 
        }
        form = JournalEntryForm(data=form_data)
        self.assertTrue(form.is_valid(), msg=f"Form errors: {form.errors.as_json()}")
        self.assertIn('Work', form.cleaned_data['tags'])
        self.assertIn('New Custom Tag', form.cleaned_data['tags'])


    def test_journal_entry_form_invalid_missing_content(self):
        form = JournalEntryForm(data={'title': 'Incomplete Form Final', 'mood': 'happy', 'privacy_level': 'private'})
        self.assertFalse(form.is_valid())
        self.assertIn('content', form.errors)

    def test_journal_attachment_form_valid(self):
        f = SimpleUploadedFile(f"form_attach_final_{uuid.uuid4().hex}.txt", b"content", content_type="text/plain")
        form = JournalAttachmentForm(data={}, files={'file': f})
        self.assertTrue(form.is_valid(), msg=f"AttachmentForm errors: {form.errors.as_json()}")
        instance = form.save(commit=False)
        self.assertEqual(instance.file_type, 'other') 

    def test_journal_attachment_form_valid_image(self):
        img_content = b"GIF89a\x01\x00\x01\x00\x00\x00\x00\xff\xff\xff,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
        f = SimpleUploadedFile(f"form_attach_img_final_{uuid.uuid4().hex}.gif", img_content, content_type="image/gif")
        form = JournalAttachmentForm(data={}, files={'file': f})
        self.assertTrue(form.is_valid(), msg=f"AttachmentForm errors: {form.errors.as_json()}")
        instance = form.save(commit=False)
        self.assertEqual(instance.file_type, 'image')


    def test_journal_attachment_form_no_file(self):
        form = JournalAttachmentForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn('file', form.errors)

@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT_JOURNAL)
class JournalViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_username = f'view_user_main_final_{uuid.uuid4().hex[:6]}'
        cls.other_user_username = f'view_user_other_final_{uuid.uuid4().hex[:6]}'
        cls.user = User.objects.create_user(username=cls.user_username, email=f'{cls.user_username}@example.com', password='password123')
        cls.other_user = User.objects.create_user(username=cls.other_user_username, email=f'{cls.other_user_username}@example.com', password='password123')
        
        # Use get_or_create for predefined tags
        cls.tag_test_view, _ = Tag.objects.get_or_create(name="ViewTestTag", defaults={'emoji':"🧪"})


        cls.entry_user = JournalEntry.objects.create(
            user=cls.user, title="User's Main Entry For View Test Final", content="Content by main user final.", mood="happy"
        )
        cls.entry_user.tags.add(cls.tag_test_view)

        cls.entry_other_user = JournalEntry.objects.create(
            user=cls.other_user, title="Other User's Entry For View Test Final", content="Content by other user final."
        )
        cls.test_file_content_view = b"View test file content final."

    def setUp(self):
        self.client = Client()
        self.client.login(username=self.user.username, password='password123')

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(TEST_MEDIA_ROOT_JOURNAL):
            shutil.rmtree(TEST_MEDIA_ROOT_JOURNAL)
        super().tearDownClass()

    def test_journal_list_view_authenticated(self):
        response = self.client.get(reverse('journal:journal_list'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.entry_user, response.context['entries'])
        self.assertContains(response, escape(self.entry_user.title))
        self.assertContains(response, self.tag_test_view.name) 

    def test_journal_detail_view_owner_access(self):
        response = self.client.get(reverse('journal:journal_detail', kwargs={'pk': self.entry_user.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['entry'], self.entry_user)
        self.assertContains(response, self.tag_test_view.name)

    def test_journal_create_view_post_valid_no_attachments(self):
        entry_count = JournalEntry.objects.count()
        form_data = {
            'title': 'New Entry No Attach Final', 'content': 'Content final.', 'mood': 'happy',
            'privacy_level': 'private', 'is_favorite': False, 'tags': 'CustomTag1, ViewTestTag'
        }
        formset_data = {'attachments-TOTAL_FORMS': '0', 'attachments-INITIAL_FORMS': '0', 'attachments-MAX_NUM_FORMS': ''}
        
        response = self.client.post(reverse('journal:journal_create'), {**form_data, **formset_data})
        
        self.assertEqual(response.status_code, 302, msg=f"Form errors: {response.context.get('form', {}).errors if response.context else 'No context'}")
        self.assertEqual(JournalEntry.objects.count(), entry_count + 1)
        new_entry = JournalEntry.objects.get(title='New Entry No Attach Final')
        self.assertIn(self.tag_test_view, new_entry.tags.all())
        self.assertTrue(Tag.objects.filter(name="Customtag1").exists())


    def test_journal_create_view_post_valid_with_attachment(self):
        entry_count_before = JournalEntry.objects.count()
        valid_mood = 'happy' 
        Tag.objects.get_or_create(name="Work", defaults={'emoji': '💼'})
        Tag.objects.get_or_create(name="Personal", defaults={'emoji': '🏠'})

        form_data = {
            'title': 'Entry With Attachment Test Final', 'content': 'File here final.', 'mood': valid_mood,
            'privacy_level': 'ai_only', 'is_favorite': False, 'tags': 'Work, Personal'
        }
        formset_management_data = {
            'attachments-TOTAL_FORMS': '1', 
            'attachments-INITIAL_FORMS': '0', 
            'attachments-MAX_NUM_FORMS': '',
            'attachments-0-DELETE': '', 
        }
        
        fresh_uploaded_file = SimpleUploadedFile(
            name=f"create_test_attach_final_{uuid.uuid4().hex}.png", 
            content=self.test_file_content_view,
            content_type="image/png"
        )
        post_data = {**form_data, **formset_management_data, 'attachments-0-file': fresh_uploaded_file}
        
        response = self.client.post(reverse('journal:journal_create'), post_data)
        
        msg = ""
        if response.status_code != 302 and response.context:
            form_errors = response.context.get('form', {}).errors if response.context.get('form') else "N/A"
            formset_errors = response.context.get('attachment_formset', {}).errors if response.context.get('attachment_formset') else "N/A"
            msg = f"Expected 302, got {response.status_code}. Form: {form_errors}, Formset: {formset_errors}"

        self.assertEqual(response.status_code, 302, msg=msg)
        self.assertEqual(JournalEntry.objects.count(), entry_count_before + 1)
        new_entry = JournalEntry.objects.get(title='Entry With Attachment Test Final')
        self.assertEqual(new_entry.attachments.count(), 1, "Attachment was not created.")
        self.assertTrue(new_entry.attachments.first().file.name.endswith('.png'))
        self.assertEqual(new_entry.attachments.first().file_type, 'image')
        self.assertIn(Tag.objects.get(name="Work"), new_entry.tags.all())


    def test_journal_update_view_post_owner(self):
        updated_title = "Updated Title Test Final"
        original_is_favorite = self.entry_user.is_favorite
        Tag.objects.get_or_create(name="Personal", defaults={'emoji': '🏠'}) 

        form_data = {
            'title': updated_title, 'content': self.entry_user.content,
            'mood': self.entry_user.mood if self.entry_user.mood else '',
            'privacy_level': self.entry_user.privacy_level, 
            'is_favorite': not original_is_favorite,
            'tags': 'Personal, UpdatedTag' 
        }
        
        initial_forms = self.entry_user.attachments.count()
        total_forms = initial_forms 
        formset_data = {
            f'attachments-TOTAL_FORMS': str(total_forms if total_forms > 0 else 0),
            f'attachments-INITIAL_FORMS': str(initial_forms),
            f'attachments-MAX_NUM_FORMS': '',
        }
        for i, att in enumerate(self.entry_user.attachments.all()):
            formset_data[f'attachments-{i}-id'] = att.id

        response = self.client.post(reverse('journal:journal_update', kwargs={'pk': self.entry_user.pk}), {**form_data, **formset_data})
        
        msg = ""
        if response.status_code != 302 and response.context:
            form_errors = response.context.get('form', {}).errors if response.context.get('form') else "N/A"
            formset_errors = response.context.get('attachment_formset', {}).errors if response.context.get('attachment_formset') else "N/A"
            msg = f"Update failed. Form: {form_errors}, Formset: {formset_errors}"

        self.assertEqual(response.status_code, 302, msg=msg)
        self.entry_user.refresh_from_db()
        self.assertEqual(self.entry_user.title, updated_title)
        self.assertEqual(self.entry_user.is_favorite, not original_is_favorite)
        self.assertNotIn(self.tag_test_view, self.entry_user.tags.all()) 
        self.assertIn(Tag.objects.get(name="Personal"), self.entry_user.tags.all())
        self.assertTrue(Tag.objects.filter(name="Updatedtag").exists()) 

    def test_journal_list_view_login_required(self):
        self.client.logout()
        response = self.client.get(reverse('journal:journal_list'))
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={reverse('journal:journal_list')}")

    def test_journal_detail_view_other_user_no_access(self):
        response = self.client.get(reverse('journal:journal_detail', kwargs={'pk': self.entry_other_user.pk}))
        self.assertEqual(response.status_code, 404)

    def test_journal_create_view_get(self):
        response = self.client.get(reverse('journal:journal_create'))
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context['form'], JournalEntryForm)
        self.assertIn('predefined_tags', response.context) 

    def test_journal_update_view_get_owner(self):
        response = self.client.get(reverse('journal:journal_update', kwargs={'pk': self.entry_user.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'value="{escape(self.entry_user.title)}"')
        self.assertIn('predefined_tags', response.context)
        self.assertIn(self.tag_test_view.name, response.context['form']['tags'].initial)


    def test_journal_delete_view_get_owner_method_not_allowed(self):
        response = self.client.get(reverse('journal:journal_delete', kwargs={'pk': self.entry_user.pk}))
        self.assertEqual(response.status_code, 405) 

    def test_journal_ajax_delete_view_post_owner(self):
        entry_to_delete_title = f"Ajax Delete Owner Final {uuid.uuid4().hex[:4]}"
        entry_to_delete = JournalEntry.objects.create(user=self.user, title=entry_to_delete_title, content="...")
        pk_to_delete = entry_to_delete.pk
        response = self.client.post(reverse('journal:journal_delete', kwargs={'pk': pk_to_delete}), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        with self.assertRaises(JournalEntry.DoesNotExist):
            JournalEntry.objects.get(pk=pk_to_delete)
