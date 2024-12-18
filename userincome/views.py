import datetime
from django.shortcuts import render, redirect
from .models import Source, UserIncome
from django.core.paginator import Paginator
from userpreferences.models import UserPreference
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
import json
from django.http import JsonResponse

def get_user_currency(user):
    """Helper function to get user's preferred currency."""
    try:
        return UserPreference.objects.get(user=user).currency
    except UserPreference.DoesNotExist:
        return 'DefaultCurrency'  

def search_income(request):
    """Search income records based on amount, date, description, or source."""
    if request.method == 'POST':
        search_str = json.loads(request.body).get('searchText')
        income = UserIncome.objects.filter(
            amount__istartswith=search_str, owner=request.user) | UserIncome.objects.filter(
            date__istartswith=search_str, owner=request.user) | UserIncome.objects.filter(
            description__icontains=search_str, owner=request.user) | UserIncome.objects.filter(
            source__icontains=search_str, owner=request.user)
        data = income.values()
        return JsonResponse(list(data), safe=False)


@login_required(login_url='/authentication/login')
def index(request):
    """Display all income records for the logged-in user."""
    sources = Source.objects.all()
    income = UserIncome.objects.filter(owner=request.user)
    paginator = Paginator(income, 5)  # Paginate income records
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    currency = get_user_currency(request.user)

    context = {
        'income': income,
        'page_obj': page_obj,
        'currency': currency,
        'sources': sources
    }
    return render(request, 'income/index.html', context)


@login_required(login_url='/authentication/login')
def add_income(request):
    """Add a new income record."""
    sources = Source.objects.all()
    context = {
        'sources': sources,
        'values': request.POST
    }
    
    if request.method == 'GET':
        return render(request, 'income/add_income.html', context)

    if request.method == 'POST':
        amount = request.POST.get('amount')
        description = request.POST.get('description')
        date = request.POST.get('income_date')
        source = request.POST.get('source')

        # Get today's date
        today = datetime.date.today()

        # Validate input fields
        if not amount:
            messages.error(request, 'Amount is required')
            return render(request, 'income/add_income.html', context)

        if not description:
            messages.error(request, 'Description is required')
            return render(request, 'income/add_income.html', context)
        
        if not date:
            messages.error(request, 'Date is required')
            return render(request, 'income/add_income.html', context)

        # Check if the date is in the future
        if datetime.datetime.strptime(date, '%Y-%m-%d').date() > today:
            messages.error(request, 'Date cannot be in the future')
            return render(request, 'income/add_income.html', context)

        UserIncome.objects.create(owner=request.user, amount=amount, date=date,
                                  source=source, description=description)
        messages.success(request, 'Record saved successfully')
        return redirect('income')



@login_required(login_url='/authentication/login')
def income_edit(request, id):
    """Edit an existing income record."""
    try:
        income = UserIncome.objects.get(pk=id)
    except UserIncome.DoesNotExist:
        messages.error(request, 'Income record not found.')
        return redirect('income')

    sources = Source.objects.all()
    context = {
        'income': income,
        'values': income,
        'sources': sources
    }
    
    if request.method == 'GET':
        return render(request, 'income/edit_income.html', context)

    if request.method == 'POST':
        amount = request.POST.get('amount')
        description = request.POST.get('description')
        date = request.POST.get('income_date')
        source = request.POST.get('source')

        # Get today's date
        today = datetime.date.today()

        # Validate input fields
        if not amount:
            messages.error(request, 'Amount is required')
            return render(request, 'income/edit_income.html', context)
        if not description:
            messages.error(request, 'Description is required')
            return render(request, 'income/edit_income.html', context)

        # Check if the date is in the future
        if datetime.datetime.strptime(date, '%Y-%m-%d').date() > today:
            messages.error(request, 'Date cannot be in the future')
            return render(request, 'income/edit_income.html', context)

        # Update income record
        income.amount = amount
        income.date = date
        income.source = source
        income.description = description
        income.save()
        messages.success(request, 'Record updated successfully')
        return redirect('income')



@login_required(login_url='/authentication/login')
def delete_income(request, id):
    """Delete an existing income record."""
    try:
        income = UserIncome.objects.get(pk=id)
        income.delete()
        messages.success(request, 'Record removed successfully')
    except UserIncome.DoesNotExist:
        messages.error(request, 'Income record not found.')
    
    return redirect('income')

@login_required(login_url='/authentication/login')
def income_category_summary(request):
    """Provide a summary of income by category for a selected month."""
    todays_date = datetime.date.today()
    six_months_ago = todays_date - datetime.timedelta(days=30 * 6)

    # Get the month from the request
    selected_month = request.GET.get('month')

    # If a month is selected, filter the income by that month
    if selected_month:
        income = UserIncome.objects.filter(owner=request.user, 
                                            date__year=todays_date.year, 
                                            date__month=selected_month)
    else:
        # Default to the last 6 months if no month is selected
        income = UserIncome.objects.filter(owner=request.user, date__gte=six_months_ago, date__lte=todays_date)

    # Calculate total income for the selected month
    total_income = income.aggregate(total=Sum('amount'))['total'] or 0

    # Group income by category and calculate total amounts
    income_by_category = income.values('source').annotate(total_amount=Sum('amount'))

    # Prepare the final report in dictionary format
    finalrep = {}
    for income_item in income_by_category:
        category_name = income_item['source']
        finalrep[category_name] = income_item['total_amount']

    # Prepare categories and total amounts for the response
    categories = list(finalrep.keys())
    total_amounts = list(finalrep.values())

    return JsonResponse({
        'categories': categories,
        'total_amounts': total_amounts,
        'total_income': total_income
    }, safe=False)



@login_required(login_url='/authentication/login')
def all_income_summary(request):
    """Provide a summary of all income records by category."""
    
    # Fetch all income records for the logged-in user
    income = UserIncome.objects.filter(owner=request.user)

    # Prepare data for response
    categories = []
    total_amounts = []
    total_income = sum(user_income.amount for user_income in income)

    for user_income in income:
        if user_income.source not in categories:
            categories.append(user_income.source)
            total_amounts.append(user_income.amount)
        else:
            index = categories.index(user_income.source)
            total_amounts[index] += user_income.amount

    data = {
        'total_income': total_income,
        'categories': categories,
        'total_amounts': total_amounts,
    }

    return JsonResponse(data)


@login_required(login_url='/authentication/login')
def income_stats_view(request):
    
    user_preferences = UserPreference.objects.filter(user=request.user).first()
    """Display the statistics page for income records."""
    currency = get_user_currency(request.user)

    # Calculate total income
    total_income = UserIncome.objects.filter(owner=request.user).aggregate(Sum('amount'))['amount__sum'] or 0

    context = {
        'currency': currency,
        'total_income': total_income, 
    }
    return render(request, 'income/income_stats.html', context)