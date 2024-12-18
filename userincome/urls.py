from django.urls import path
from . import views
from django.views.decorators.csrf import csrf_exempt

urlpatterns = [
    path('', views.index, name="income"),
    path('add-income', views.add_income, name="add-income"),
    path('edit-income/<int:id>', views.income_edit, name="income-edit"),
    path('income-delete/<int:id>', views.delete_income, name="income-delete"),
    path('search-income', csrf_exempt(views.search_income), name="search_income"),
    path('income_category_summary', views.income_category_summary, name="income_category_summary"),
    path('all_income_summary', views.all_income_summary, name="all_income_summary"),
    path('income_stats', views.income_stats_view, name="income_stats"),
]
