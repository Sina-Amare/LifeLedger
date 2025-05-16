# accounts/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin # Import UserAdmin
from .models import CustomUser, UserProfile # Import your models

# Register your models here.

# Optional: Customize the UserAdmin for your CustomUser if needed
# For example, to add custom fields to the admin form/list display
class CustomUserAdmin(UserAdmin):
    # Add your custom fields to the list_display, fieldsets, add_fieldsets, etc.
    # For example:
    # list_display = ('username', 'email', 'is_staff', 'is_active', 'date_joined', 'profile_picture') # Add custom fields here
    # fieldsets = UserAdmin.fieldsets + (
    #     (None, {'fields': ('profile_picture', 'bio')}), # Add custom fields to existing fieldsets
    # )
    # add_fieldsets = UserAdmin.add_fieldsets + (
    #     (None, {'fields': ('email',)}), # Add email to the add user form
    # )
    pass # Use default UserAdmin for now

# Register CustomUser with the custom admin class
admin.site.register(CustomUser, CustomUserAdmin)

# Register UserProfile
admin.site.register(UserProfile)

