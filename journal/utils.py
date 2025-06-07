# journal/utils.py

"""
Shared utilities and constants for the journal application.
"""

# Visual configurations for different moods to be used across views and templates.
# This centralized dictionary ensures consistency in UI representation of moods.
MOOD_VISUALS = {
    'happy': {
        'emoji': "😊", 
        'text_color': "text-green-700 dark:text-green-400", 
        'bg_color': "bg-green-100 dark:bg-green-800", 
        'border_color': "border-green-500"
    },
    'sad': {
        'emoji': "😢", 
        'text_color': "text-blue-700 dark:text-blue-400", 
        'bg_color': "bg-blue-100 dark:bg-blue-800", 
        'border_color': "border-blue-500"
    },
    'angry': {
        'emoji': "😠", 
        'text_color': "text-red-700 dark:text-red-400", 
        'bg_color': "bg-red-100 dark:bg-red-800", 
        'border_color': "border-red-500"
    },
    'calm': {
        'emoji': "😌", 
        'text_color': "text-sky-700 dark:text-sky-400", 
        'bg_color': "bg-sky-100 dark:bg-sky-800", 
        'border_color': "border-sky-500"
    },
    'neutral': {
        'emoji': "😐", 
        'text_color': "text-gray-700 dark:text-gray-400", 
        'bg_color': "bg-gray-100 dark:bg-gray-700", 
        'border_color': "border-gray-500"
    },
    'excited': {
        'emoji': "🎉", 
        'text_color': "text-yellow-700 dark:text-yellow-400", 
        'bg_color': "bg-yellow-100 dark:bg-yellow-800", 
        'border_color': "border-yellow-500"
    },
}

# Color palette for Chart.js, providing a consistent theme for visualizations.
# Keys correspond to mood values.
CHART_JS_COLOR_PALETTE = {
    'happy': {'bg': 'rgba(75, 192, 192, 0.6)', 'border': 'rgb(75, 192, 192)'},
    'sad': {'bg': 'rgba(54, 162, 235, 0.6)', 'border': 'rgb(54, 162, 235)'},
    'angry': {'bg': 'rgba(255, 99, 132, 0.6)', 'border': 'rgb(255, 99, 132)'},
    'calm': {'bg': 'rgba(153, 102, 255, 0.6)', 'border': 'rgb(153, 102, 255)'},
    'neutral': {'bg': 'rgba(201, 203, 207, 0.6)', 'border': 'rgb(201, 203, 207)'},
    'excited': {'bg': 'rgba(255, 205, 86, 0.6)', 'border': 'rgb(255, 205, 86)'},
    'default': {'bg': 'rgba(100, 100, 100, 0.6)', 'border': 'rgb(100, 100, 100)'}
}

