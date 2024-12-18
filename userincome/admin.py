from django.contrib import admin
from .models import UserIncome, Source
# Register your models here.
class UserIncomeAdmin(admin.ModelAdmin):
    list_display = ('amount', 'description', 'owner', 'source', 'date',)
    search_fields = ('description', 'source__name', 'date',)
    list_filter = ('source', 'date')
    list_per_page = 10 

admin.site.register(UserIncome, UserIncomeAdmin)
admin.site.register(Source)