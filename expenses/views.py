from django.shortcuts import render, redirect,  get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Category, Expense
from django.contrib import messages
from django.core.paginator import Paginator
import json
from django.db.models import Sum
from django.http import JsonResponse,HttpResponse
from userpreferences.models import UserPreference
import datetime
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from django.utils import timezone
import csv
import os
from django.template.loader import render_to_string
from weasyprint import HTML
import tempfile


def search_expenses(request):
    if request.method == 'POST':
        search_str = json.loads(request.body).get('searchText')
        expenses = Expense.objects.filter(
            amount__istartswith=search_str, owner=request.user
        ) | Expense.objects.filter(
            date__istartswith=search_str, owner=request.user
        ) | Expense.objects.filter(
            descriptions__icontains=search_str, owner=request.user
        ) | Expense.objects.filter(
            category__icontains=search_str, owner=request.user
        )
        data = expenses.values()
        return JsonResponse(list(data), safe=False)


@login_required(login_url='/authentication/login')
def index(request):
    categories = Category.objects.all()
    expenses = Expense.objects.filter(owner=request.user)
    paginator = Paginator(expenses, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    try:
        currency = UserPreference.objects.get(user=request.user).currency
    except UserPreference.DoesNotExist:
        currency = 'DefaultCurrency'  
    context = {
        'expenses': expenses,
        'page_obj': page_obj,
        'currency': currency,
        'categories': categories
    }
    return render(request, 'expenses/index.html', context)

@login_required(login_url='/authentication/login')
def dashboard(request):
    
    recent_expenses = Expense.objects.filter(owner=request.user).order_by('-date')[:5]

    expense_descriptions = [expense.descriptions for expense in recent_expenses]
    expense_amounts = [expense.amount for expense in recent_expenses]

    try:
        currency = UserPreference.objects.get(user=request.user).currency
    except UserPreference.DoesNotExist:
        currency = 'DefaultCurrency'  

    context = {
        'recent_expenses': recent_expenses,
        'currency': currency,
        'expense_descriptions': expense_descriptions,
        'expense_amounts': expense_amounts,
    }
    return render(request, 'expenses/dashboard.html', context)

@login_required(login_url='/authentication/login')
def add_expense(request):
    categories = Category.objects.all()
    context = {
        'categories': categories,
        'values': request.POST
    }
    if request.method == 'GET':
        return render(request, 'expenses/add_expense.html', context)

    if request.method == 'POST':
        amount = request.POST.get('amount')
        descriptions = request.POST.get('description')
        date = request.POST.get('expense_date')
        category = request.POST.get('category')

        today = datetime.date.today()

        if not amount:
            messages.error(request, 'Amount is required')
            return render(request, 'expenses/add_expense.html', context)

        if not descriptions:
            messages.error(request, 'Description is required')
            return render(request, 'expenses/add_expense.html', context)

        if not date:
            messages.error(request, 'Date is required')
            return render(request, 'expenses/add_expense.html', context)

        if datetime.datetime.strptime(date, '%Y-%m-%d').date() > today:
            messages.error(request, 'Date cannot be in the future')
            return render(request, 'expenses/add_expense.html', context)

        Expense.objects.create(owner=request.user, amount=amount, date=date,
                               category=category, descriptions=descriptions)
        messages.success(request, 'Expense saved successfully')

        return redirect('expenses')


@login_required(login_url='/authentication/login')
def expense_edit(request, id):
    try:
        expense = Expense.objects.get(pk=id)
    except Expense.DoesNotExist:
        messages.error(request, 'Expense record not found.')
        return redirect('expenses')

    categories = Category.objects.all()
    context = {
        'expense': expense,
        'values': expense,
        'categories': categories
    }

    if request.method == 'GET':
        return render(request, 'expenses/edit-expense.html', context)

    if request.method == 'POST':
        amount = request.POST.get('amount')
        descriptions = request.POST.get('description')
        date = request.POST.get('expense_date')
        category = request.POST.get('category')

        today = datetime.date.today()

        if not amount:
            messages.error(request, 'Amount is required')
            return render(request, 'expenses/edit-expense.html', context)

        if not descriptions:
            messages.error(request, 'Description is required')
            return render(request, 'expenses/edit-expense.html', context)

        if datetime.datetime.strptime(date, '%Y-%m-%d').date() > today:
            messages.error(request, 'Date cannot be in the future')
            return render(request, 'expenses/edit-expense.html', context)

        expense.amount = amount
        expense.date = date
        expense.category = category
        expense.descriptions = descriptions
        expense.save()
        messages.success(request, 'Expense updated successfully')

        return redirect('expenses')


@login_required(login_url='/authentication/login')
def delete_expense(request, id):
    try:
        expense = Expense.objects.get(pk=id)
        expense.delete()
        messages.success(request, 'Expense removed successfully')
    except Expense.DoesNotExist:
        messages.error(request, 'Expense record not found.')
    
    return redirect('expenses')


@login_required(login_url='/authentication/login')
def expense_category_summary(request):
    todays_date = datetime.date.today()
    six_months_ago = todays_date - datetime.timedelta(days=30 * 6)

    selected_month = request.GET.get('month')

    if selected_month:
        selected_month = int(selected_month)

        if selected_month > todays_date.month:
            expenses = Expense.objects.none()
            prediction = 0
        else:
            expenses = Expense.objects.filter(
                owner=request.user,
                date__year=todays_date.year,
                date__month=selected_month
            )
    else:
        expenses = Expense.objects.filter(owner=request.user, date__gte=six_months_ago, date__lte=todays_date)

    total_expenses = expenses.aggregate(total=Sum('amount'))['total'] or 0
    category_summary = expenses.values('category').annotate(total_amount=Sum('amount'))

    finalrep = {}
    for expense in category_summary:
        category_name = expense['category']
        finalrep[category_name] = expense['total_amount']

    categories = list(finalrep.keys())
    total_amounts = list(finalrep.values())

    if selected_month and selected_month <= todays_date.month:
        last_three_months_expenses = Expense.objects.filter(
            owner=request.user,
            date__gte=todays_date - pd.DateOffset(months=3)
        ).values('date', 'amount')

        df = pd.DataFrame(list(last_three_months_expenses))

        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            df['month'] = df['date'].dt.month
            monthly_totals = df.groupby('month')['amount'].sum().reset_index()

            if len(monthly_totals) >= 3:
                df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
                df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)

                X = df[['month_sin', 'month_cos']].values
                y = monthly_totals['amount'].values

                try:
                    model = LinearRegression()
                    model.fit(X, y)

                    next_month = (todays_date.month % 12) + 1
                    next_month_sin = np.sin(2 * np.pi * next_month / 12)
                    next_month_cos = np.cos(2 * np.pi * next_month / 12)

                    predicted_expense = model.predict([[next_month_sin, next_month_cos]])

                    prediction = predicted_expense[0]
                except Exception as e:
                    print(f"Error in model prediction: {e}")
                    prediction = 0
            else:
                prediction = 0
        else:
            prediction = 0

        return JsonResponse({
            'categories': categories,
            'total_amounts': total_amounts,
            'total_expenses': total_expenses,
            'predicted_expense': prediction
        }, safe=False)

    return JsonResponse({
        'categories': categories,
        'total_amounts': total_amounts,
        'total_expenses': total_expenses
    }, safe=False)



@login_required(login_url='/authentication/login')
def all_expenses_summary(request):
    expenses = Expense.objects.all()
    
    categories = []
    total_amounts = []
    total_expenses = sum(expense.amount for expense in expenses)

    for expense in expenses:
        if expense.category not in categories:
            categories.append(expense.category)
            total_amounts.append(expense.amount)
        else:
            index = categories.index(expense.category)
            total_amounts[index] += expense.amount

    data = {
        'categories': categories,
        'total_amounts': total_amounts,
        'total_expenses': total_expenses,
    }

    return JsonResponse(data)


@login_required(login_url='/authentication/login')
def stats_view(request):
    user_preferences = UserPreference.objects.filter(user=request.user).first()
    currency = user_preferences.currency if user_preferences else 'DefaultCurrency'

    expense_summary = Expense.objects.filter(owner=request.user) \
        .values('category') \
        .annotate(total_amount=Sum('amount'))

    expense_summary_dict = {item['category']: item['total_amount'] for item in expense_summary}

    total_expenses = sum(expense_summary_dict.values())

    context = {
        'expense_summary': expense_summary_dict,
        'total_expenses': total_expenses,
        'currency': currency,
    }

    return render(request, 'expenses/stats.html', context)



@login_required(login_url='/authentication/login')
def notification(request):
    today = datetime.date.today()
    upcoming_notifications = []
    previous_notifications = []

    expenses = Expense.objects.filter(
        owner=request.user,
        category__in=['Bills', 'Education', 'Subscription']
    )

    for expense in expenses:
        expiry_date = expense.date + datetime.timedelta(days=30)
        
        if expense.category == 'Bills':
            message_prefix = "Your bill is going to be due soon"
        elif expense.category == 'Subscription':
            message_prefix = "Your subscription is going to expire soon"
        elif expense.category == 'Education':
            message_prefix = "Your education-related expense is about to come soon"
        else:
            message_prefix = "Your expense is going to expire soon"
        
        if today < expiry_date:
            if today >= expiry_date - datetime.timedelta(days=1):
                message = f"{message_prefix}: {expense.descriptions}"
                upcoming_notifications.append({
                    'category': expense.category,
                    'message': message,
                    'expiry_date': expiry_date,
                    'expense_id': expense.id 
                })

        elif today >= expiry_date:
            message = f"Your {expense.category.lower()} related expense has expired: {expense.descriptions}"
            previous_notifications.append({
                'category': expense.category,
                'message': message,
                'expiry_date': expiry_date,
                'expense_id': expense.id  
            })

    context = {
        'upcoming_notifications': upcoming_notifications,
        'previous_notifications': previous_notifications,
    }

    return render(request, 'expenses/notification.html', context)

def delete_notification(request, id):
    expense = get_object_or_404(Expense, id=id, owner=request.user)
    expense.delete()
    messages.success(request, 'Expense notification deleted successfully!')
    return redirect('notification')

def export_csv(request):
    response = HttpResponse(content_type='text/csv')

    current_time = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    response['Content-Disposition'] = f'attachment; filename=Expenses_{current_time}.csv'

    writer = csv.writer(response)
    writer.writerow(['Amount', 'Description', 'Category', 'Date'])

    expenses = Expense.objects.filter(owner=request.user)

    for expense in expenses:
        formatted_date = expense.date.strftime('%Y-%m-%d') 
        writer.writerow([expense.amount, expense.descriptions, expense.category, formatted_date])

    return response

def export_pdf(request):
    response = HttpResponse(content_type='application/pdf')

    current_time = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    response['Content-Disposition'] = f'attachment; filename=Expenses_{current_time}.pdf'
    response['Content-Transfer-Encoding'] = 'binary'

    expenses = Expense.objects.filter(owner=request.user)
    sum_result = expenses.aggregate(total=Sum('amount'))  
    total_sum = sum_result['total'] if sum_result['total'] else 0  

    html_string = render_to_string('expenses/pdf_op.html', {'expenses': expenses, 'total': total_sum})
    html = HTML(string=html_string)

    result = html.write_pdf()

    with tempfile.NamedTemporaryFile(delete=False) as output:
        output.write(result)
        output.flush()
        output_path = output.name

    with open(output_path, 'rb') as pdf_file:
        response.write(pdf_file.read())

    os.remove(output_path)

    return response
        