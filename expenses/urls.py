from django.urls import path
from . import views

urlpatterns = [
    # Existing URLs
    path('', views.index, name='expenses'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('add_expense/', views.add_expense, name='add-expenses'),
    path('edit-expense/<int:id>', views.expense_edit, name="expense-edit"),
    path('expense-delete/<int:id>', views.delete_expense, name="expense-delete"),
    path('search-expenses', views.search_expenses, name="search_expenses"),
    path('expense_category_summary', views.expense_category_summary, name="expense_category_summary"),
    path('stats', views.stats_view, name="stats"),
    path('all_expenses_summary/', views.all_expenses_summary, name='all_expenses_summary'),
    path('notification/', views.notification, name='notification'),
    path('delete-notification/<int:id>/', views.delete_notification, name='delete-notification'),
    path('export_csv', views.export_csv, name='export-csv'),
    path('export_pdf', views.export_pdf, name='export-pdf'),
]
