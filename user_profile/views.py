from django.shortcuts import render, redirect
from django.views import View 
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.contrib.auth import update_session_auth_hash # Important for keeping user logged in
from django.utils.translation import gettext_lazy as _ # For translation

# Forms from user_profile.forms
from .forms import UserUpdateForm, UserProfileUpdateForm, CurrentPasswordConfirmForm, NewPasswordSetForm
# UserProfile model from the current app's models
from .models import UserProfile 

class ProfileUpdateView(LoginRequiredMixin, View):
    """
    View for users to update their profile information.
    Handles both CustomUser data (first_name, last_name) and
    UserProfile data (bio, profile_picture, etc.).
    """
    template_name = 'user_profile/profile_update_form.html'
    success_url = reverse_lazy('user_profile:profile_update') 

    def get(self, request, *args, **kwargs):
        """
        Handles GET requests.
        Initializes and displays the user update form and profile update form
        populated with the current user's data.
        """
        user_form = UserUpdateForm(instance=request.user)
        # Ensure profile exists. The signal should create it for new users.
        # For existing users, if it somehow doesn't exist, get_or_create handles it.
        profile_instance, created = UserProfile.objects.get_or_create(user=request.user)
        if created:
            # This log helps identify if a profile was missing and created on-the-fly.
            print(f"ProfileUpdateView: Created a new UserProfile for {request.user.username} during GET request because it was missing.")
            
        profile_form = UserProfileUpdateForm(instance=profile_instance)
        
        context = {
            'user_form': user_form,
            'profile_form': profile_form,
            'page_title': _('Update Your Profile') # Translated page title
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests.
        Validates and saves the submitted data for both forms.
        """
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_instance, _ = UserProfile.objects.get_or_create(user=request.user)
        profile_form = UserProfileUpdateForm(request.POST, request.FILES, instance=profile_instance)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save() 
            profile_form.save() 
            messages.success(request, _('Your profile has been updated successfully!'))
            return redirect(self.success_url)
        else:
            messages.error(request, _('Please correct the errors below.'))
            context = {
                'user_form': user_form,
                'profile_form': profile_form,
                'page_title': _('Update Your Profile') # Translated page title
            }
            return render(request, self.template_name, context)

class CustomPasswordChangeView(LoginRequiredMixin, View):
    """
    Handles a two-stage password change process for authenticated users.
    Stage 1: Confirm current password.
    Stage 2: Set new password.
    """
    template_name = 'user_profile/change_password.html' 
    current_password_form_class = CurrentPasswordConfirmForm
    new_password_form_class = NewPasswordSetForm
    success_url = reverse_lazy('user_profile:profile_update') 

    SESSION_KEY_PASSWORD_CONFIRMED = 'current_password_confirmed_for_change'

    def get_context_data(self, **kwargs):
        """Prepares context data for the template based on the current stage."""
        context = {}
        if self.request.session.get(self.SESSION_KEY_PASSWORD_CONFIRMED, False):
            context['stage'] = 2
            context['new_password_form'] = self.new_password_form_class(user=self.request.user)
            context['page_title'] = _('Set New Password')
        else:
            context['stage'] = 1
            context['current_password_form'] = self.current_password_form_class(user=self.request.user)
            context['page_title'] = _('Confirm Current Password')
        return context

    def get(self, request, *args, **kwargs):
        """Handles GET requests to display the appropriate form based on stage."""
        return render(request, self.template_name, self.get_context_data())

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests for both stages of password change.
        Determines which form (stage 1 or stage 2) is being submitted.
        """
        if 'current_password' in request.POST: 
            form = self.current_password_form_class(request.POST, user=request.user)
            if form.is_valid():
                request.session[self.SESSION_KEY_PASSWORD_CONFIRMED] = True
                return redirect(request.path) 
            else:
                # Form's clean_current_password will add specific error.
                # We add a general info message here.
                messages.info(request, _("If you've forgotten your current password, you may need to log out and use the 'Forgot Password' link on the login page."))
                context = self.get_context_data() 
                context['current_password_form'] = form 
                return render(request, self.template_name, context)

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
                context = self.get_context_data() 
                context['new_password_form'] = form 
                messages.error(request, _('Please correct the errors below to set your new password.'))
                return render(request, self.template_name, context)
        
        messages.error(request, _("Invalid form submission. Please try again."))
        return redirect(request.path)

