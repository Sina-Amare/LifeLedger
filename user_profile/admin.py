from django.contrib import admin
from django.utils.html import format_html # For displaying HTML in admin, like image thumbnails
from .models import UserProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """
    Admin configuration for the UserProfile model.
    """
    list_display = (
        'user', 
        'get_user_email', # Custom method to display user's email
        'profile_picture_thumbnail', # Custom method for image thumbnail
        'bio_snippet', # Custom method for a short bio preview
        'updated_at'
    )
    list_select_related = ('user',) # Improves performance by fetching related user in one query
    search_fields = (
        'user__username', 
        'user__email', 
        'bio'
    )
    readonly_fields = (
        'user', # The user associated with the profile should not be changed here
        'profile_picture_thumbnail_display', # For displaying the image in the form
        'created_at', 
        'updated_at',
        'activation_key', # Usually, activation keys are not manually edited by admin
    )
    
    # fieldsets provide a way to organize the fields in the admin form
    fieldsets = (
        (None, { # Main section without a title, or you can put 'User Information'
            'fields': ('user', 'profile_picture_thumbnail_display', 'profile_picture', 'bio')
        }),
        ('Personal Details', {
            'fields': ('location', 'date_of_birth', 'website_url', 'linkedin_url', 'github_url')
        }),
        ('Privacy Settings', {
            'classes': ('collapse',), # Makes this section collapsible
            'fields': (
                'show_email_publicly', 
                'show_location_publicly', 
                'show_socials_publicly', 
                'show_dob_publicly'
            )
        }),
        ('AI Preferences', {
            'classes': ('collapse',),
            'fields': (
                'ai_enable_quotes', 
                'ai_enable_mood_detection', 
                'ai_enable_tag_suggestion'
            )
        }),
        ('Account Status & Timestamps', {
            'classes': ('collapse',),
            'fields': ('activation_key', 'created_at', 'updated_at')
        }),
    )

    def get_user_email(self, obj):
        """Returns the email of the associated user."""
        return obj.user.email
    get_user_email.short_description = 'User Email' # Column header in admin list
    get_user_email.admin_order_field = 'user__email' # Allows sorting by email

    def bio_snippet(self, obj):
        """Returns a short snippet of the bio."""
        if obj.bio:
            return obj.bio[:50] + '...' if len(obj.bio) > 50 else obj.bio
        return "-"
    bio_snippet.short_description = 'Bio Snippet'

    def profile_picture_thumbnail(self, obj):
        """Displays a small thumbnail of the profile picture in the list view."""
        if obj.profile_picture:
            return format_html('<img src="{}" style="width: 45px; height: 45px; border-radius: 50%; object-fit: cover;" />', obj.profile_picture.url)
        return "No Image"
    profile_picture_thumbnail.short_description = 'Pic'

    def profile_picture_thumbnail_display(self, obj):
        """Displays the profile picture thumbnail in the admin form (readonly)."""
        if obj.profile_picture:
            return format_html('<img src="{}" style="max-width: 200px; max-height: 200px; border-radius: 10px;" />', obj.profile_picture.url)
        return "No Image Uploaded"
    profile_picture_thumbnail_display.short_description = 'Current Picture Preview'

    # If you also want to manage UserProfile inline with CustomUser in accounts/admin.py:
    # This would be an alternative or addition to the standalone UserProfileAdmin.
    # You would define a UserProfileInline(admin.StackedInline) or TabularInline
    # and add it to the CustomUserAdmin's inlines list.
    # Example (you would put this in accounts/admin.py, not here):
    #
    # from user_profile.models import UserProfile
    # class UserProfileInline(admin.StackedInline):
    #     model = UserProfile
    #     can_delete = False
    #     verbose_name_plural = 'Profile'
    #     fk_name = 'user'
    #     readonly_fields = ('activation_key', 'created_at', 'updated_at') # And others as needed
    #
    # In CustomUserAdmin:
    # inlines = (UserProfileInline, )

