from django.shortcuts import render, redirect
from django.views import View 
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.contrib.auth import update_session_auth_hash 
from django.utils.translation import gettext_lazy as _
from django.conf import settings 
from django.contrib.auth.password_validation import get_password_validators

from .forms import UserUpdateForm, UserProfileUpdateForm, CurrentPasswordConfirmForm, NewPasswordSetForm
from .models import UserProfile 

class ProfileUpdateView(LoginRequiredMixin, View):
    template_name = 'user_profile/profile_update_form.html'
    success_url = reverse_lazy('user_profile:profile_update') 

    def get(self, request, *args, **kwargs):
        user_form = UserUpdateForm(instance=request.user)
        profile_instance, profile_created = UserProfile.objects.get_or_create(user=request.user)
        if profile_created:
            print(f"ProfileUpdateView: Created UserProfile for {request.user.username} in GET.")
            
        profile_form = UserProfileUpdateForm(instance=profile_instance)
        
        context = {
            'user_form': user_form,
            'profile_form': profile_form,
            'page_title': _('Edit Profile'),
            'active_section': 'profile_update' 
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_instance, profile_created_on_post = UserProfile.objects.get_or_create(user=request.user)
        if profile_created_on_post:
            print(f"ProfileUpdateView: Created UserProfile for {request.user.username} in POST.")

        profile_form = UserProfileUpdateForm(request.POST, request.FILES, instance=profile_instance)

        if user_form.is_valid() and profile_form.is_valid():
            try:
                # Save user form first
                user = user_form.save(commit=True)
                
                # Then save profile form with explicit commit
                profile = profile_form.save(commit=True)
                
                # Log the update for debugging
                print(f"Profile updated for {user.username}. Profile ID: {profile.id}")
                
                messages.success(request, _('Your profile has been updated successfully!'))
                return redirect(self.success_url)
            except Exception as e:
                messages.error(request, _(f"An error occurred while saving: {str(e)}"))
                context = {
                    'user_form': user_form,
                    'profile_form': profile_form,
                    'page_title': _('Edit Profile'),
                    'active_section': 'profile_update'
                }
                return render(request, self.template_name, context)
        else:
            messages.error(request, _('Please correct the errors below.'))
            context = {
                'user_form': user_form,
                'profile_form': profile_form,
                'page_title': _('Edit Profile'),
                'active_section': 'profile_update'
            }
            return render(request, self.template_name, context)

class CustomPasswordChangeView(LoginRequiredMixin, View):
    template_name = 'user_profile/change_password.html' 
    current_password_form_class = CurrentPasswordConfirmForm
    new_password_form_class = NewPasswordSetForm
    success_url = reverse_lazy('user_profile:change_password') 

    SESSION_KEY_PASSWORD_CONFIRMED = 'current_password_confirmed_for_change'

    def get_context_data(self, **kwargs):
        context = {'active_section': 'change_password'} 
        if self.request.session.get(self.SESSION_KEY_PASSWORD_CONFIRMED, False):
            context['stage'] = 2
            context['new_password_form'] = self.new_password_form_class(user=self.request.user)
            context['page_title'] = _('Set New Password')
            
            # --- FIXED PASSWORD VALIDATORS HELP TEXT ---
            try:
                # Get the actual validator instances instead of just the validator settings
                validators = get_password_validators(settings.AUTH_PASSWORD_VALIDATORS)
                help_texts = []
                for validator in validators:
                    help_texts.append(validator.get_help_text())
                context['password_validators_help_texts'] = help_texts
                print("DEBUG: Successfully called get_password_validators and got help texts.")
            except Exception as e:
                print(f"ERROR getting password validators help texts: {e}")
                import traceback
                traceback.print_exc()
                context['password_validators_help_texts'] = [] # Provide an empty list on error
            # --- END OF FIXED BLOCK ---

        else: # Stage 1
            if not self.request.user.is_authenticated:
                messages.error(self.request, _("You must be logged in to change your password."))
                return redirect(reverse_lazy('accounts:login'))
            context['stage'] = 1
            context['current_password_form'] = self.current_password_form_class(user=self.request.user)
            context['page_title'] = _('Confirm Current Password')
        return context

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, self.get_context_data())

    def post(self, request, *args, **kwargs):
        # Get base context which includes 'active_section' and potentially initial form for stage 1 or 2
        # This ensures that if a POST fails and re-renders, the context is correctly set for the current stage.
        current_stage_context = self.get_context_data()

        if 'current_password' in request.POST: 
            form = self.current_password_form_class(request.POST, user=request.user)
            if form.is_valid():
                request.session[self.SESSION_KEY_PASSWORD_CONFIRMED] = True
                return redirect(request.path) 
            else:
                messages.info(request, _("If you've forgotten your current password, you may need to log out and use the 'Forgot Password' link on the login page."))
                current_stage_context['current_password_form'] = form # Add the form with errors
                # Ensure stage is correctly set for re-rendering stage 1 with errors
                current_stage_context['stage'] = 1
                current_stage_context['page_title'] = _('Confirm Current Password')
                return render(request, self.template_name, current_stage_context)

        elif 'new_password1' in request.POST:
            if not request.session.get(self.SESSION_KEY_PASSWORD_CONFIRMED, False):
                messages.error(request, _("Please confirm your current password first."))
                if self.SESSION_KEY_PASSWORD_CONFIRMED in request.session:
                     del request.session[self.SESSION_KEY_PASSWORD_CONFIRMED]
                return redirect(request.path)

            form = self.new_password_form_class(request.user, request.POST)
            if form.is_valid():
                user = form.save()
                update_session_auth_hash(request, user)
                
                if self.SESSION_KEY_PASSWORD_CONFIRMED in request.session:
                    del request.session[self.SESSION_KEY_PASSWORD_CONFIRMED]
                
                messages.success(request, _('Your password has been changed successfully!'))
                return redirect(self.success_url) 
            else:
                current_stage_context['new_password_form'] = form # Add the form with errors
                # Ensure stage and title are correctly set for re-rendering stage 2 with errors
                current_stage_context['stage'] = 2 
                current_stage_context['page_title'] = _('Set New Password')
                # Ensure password_validators_help_texts is available on error re-render for stage 2
                try:
                    validators = get_password_validators(settings.AUTH_PASSWORD_VALIDATORS)
                    help_texts = []
                    for validator in validators:
                        help_texts.append(validator.get_help_text())
                    current_stage_context['password_validators_help_texts'] = help_texts
                except Exception as e: # Fallback in case of error
                    print(f"ERROR getting password validators help texts during POST error handling: {e}")
                    current_stage_context['password_validators_help_texts'] = []
                messages.error(request, _('Please correct the errors below to set your new password.'))
                return render(request, self.template_name, current_stage_context)
        
        messages.error(request, _("Invalid form submission. Please try again."))
        return redirect(request.path)