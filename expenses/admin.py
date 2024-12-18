from django.contrib import admin
from .models import Expense, Category
# Register your models here.


class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('amount', 'descriptions', 'owner', 'category', 'date',)
    search_fields = ('descriptions', 'category', 'date',)

    list_per_page = 5


admin.site.register(Expense, ExpenseAdmin)
admin.site.register(Category)