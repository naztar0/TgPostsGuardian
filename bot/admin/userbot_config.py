from django.contrib import admin
from django.utils.translation import gettext_lazy as _


class UserBotConfigAdmin(admin.ModelAdmin):
    list_display = ['created', 'phone_number', 'password', 'worker_instances', 'is_active']
    search_fields = ['phone_number']
    list_editable = ['is_active']
    date_hierarchy = 'created'
    list_per_page = 25

    fieldsets = [
        (_('parameters'), {'fields': ['phone_number', 'password', 'worker_instances', 'is_active']}),
    ]

    def has_add_permission(self, *args, **kwargs):
        return True

    def has_change_permission(self, *args, **kwargs):
        return True

    def has_delete_permission(self, *args, **kwargs):
        return True
