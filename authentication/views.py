from django.shortcuts import render, redirect
from django.views import View
import json
from django.http import JsonResponse
from django.contrib.auth.models import User
from validate_email_address import validate_email
from django.contrib import messages
from django.core.mail import EmailMessage
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes, force_str, DjangoUnicodeDecodeError
from django.core.mail import send_mail
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.template.loader import render_to_string
from .utils import account_activation_token
from django.urls import reverse
from django.contrib import auth
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.auth.mixins import LoginRequiredMixin

# Create your views here.

class EmailValidationView(View):
    def post(self, request):
        data = json.loads(request.body)
        email = data['email']
        if not validate_email(email):
            return JsonResponse({'email_error': 'Email is invalid'}, status=400)
        if User.objects.filter(email=email).exists():
            return JsonResponse({'email_error': 'Email already in use'}, status=409)
        return JsonResponse({'email_valid': True})

class UsernameValidationView(View):
    def post(self, request):
        data = json.loads(request.body)
        username = data['username']

        if not str(username).isalnum():
            return JsonResponse({'username_error': 'Username can only contain alphabets or numerical characters'}, status=400)
        if User.objects.filter(username=username).exists():
            return JsonResponse({'username_error': 'Username already exists'}, status=409)
        return JsonResponse({'username_valid': True})

class RegistrationView(View):
    def get(self, request):
        return render(request, 'authentication/register.html')
    
    def post(self, request):
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']

        context = {
            'fieldValues': request.POST
        }

        if not User.objects.filter(username=username).exists():
            if not User.objects.filter(email=email).exists():
                if len(password) < 6:
                    messages.error(request, 'Password too short')
                    return render(request, 'authentication/register.html', context)

                user = User.objects.create_user(username=username, email=email)
                user.set_password(password)
                user.is_active = False
                user.save()
                current_site = get_current_site(request)
                email_body = {
                    'user': user,
                    'domain': current_site.domain,
                    'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                    'token': account_activation_token.make_token(user),
                }

                link = reverse('activate', kwargs={
                               'uidb64': email_body['uid'], 'token': email_body['token']})

                email_subject = 'Activate your account'

                activate_url = 'http://' + current_site.domain + link

                email = EmailMessage(
                    email_subject,
                    'Hi ' + user.username + ', please click the link below to activate your account: \n' + activate_url,
                    'noreply@semycolon.com',
                    [email],
                )
                email.send(fail_silently=False)
                messages.success(request, 'Account successfully created')
                return render(request, 'authentication/register.html')

        return render(request, 'authentication/register.html')

class VerificationView(View):
    def get(self, request, uidb64, token):
        try:
            id = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=id)

            if not account_activation_token.check_token(user, token):
                return redirect('login' + '?message=' + 'User already activated')

            if user.is_active:
                return redirect('login')
            user.is_active = True
            user.save()

            messages.success(request, 'Account activated successfully')
            return redirect('login')

        except Exception as ex:
            pass

        return redirect('login')

class LoginView(View):
    def get(self, request):
        return render(request, 'authentication/login.html')

    def post(self, request):
        username = request.POST['username']
        password = request.POST['password']

        if username and password:
            user = auth.authenticate(username=username, password=password)

            if user:
                if user.is_active:
                    auth.login(request, user)
                    messages.success(request, 'Welcome, ' + user.username + ', you are now logged in')
                    return redirect('dashboard')
                messages.error(request, 'Account is not active, please check your email')
                return render(request, 'authentication/login.html')
            messages.error(request, 'Invalid credentials, try again')
            return render(request, 'authentication/login.html')

        messages.error(request, 'Please fill all fields')
        return render(request, 'authentication/login.html')

class LogoutView(View):
    def post(self, request):
        auth.logout(request)
        messages.success(request, 'You have been logged out')
        return redirect('login')

class RequestPasswordResetEmail(View):
    def get(self, request):
        return render(request, 'authentication/reset-password.html')

    def post(self, request):
        email = request.POST['email']
        context = {'values': request.POST}

        if not validate_email(email):
            messages.error(request, 'Please enter a valid email')
            return render(request, 'authentication/reset-password.html', context)

        current_site = get_current_site(request)
        user = User.objects.filter(email=email)

        if user.exists():
            email_context = {
                'user': user[0],
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(user[0].pk)),
                'token': PasswordResetTokenGenerator().make_token(user[0]),
            }

            link = reverse('reset-user-password', kwargs={
                           'uidb64': email_context['uid'], 'token': email_context['token']})

            reset_url = f'http://{current_site.domain}{link}'
            email_subject = 'Password Reset'

            email = EmailMessage(
                email_subject,
                f'Hi {user[0].username},\nPlease click the link below to reset your password: {reset_url}',
                'noreply@domain.com',
                [email],
            )
            email.send(fail_silently=False)

            messages.success(request, 'Password reset link has been sent to your email')
            return render(request, 'authentication/reset-password.html', context)

        messages.error(request, 'Email does not exist')
        return render(request, 'authentication/reset-password.html', context)

class CompletePasswordReset(View):
    def get(self, request, uidb64, token):
        context = {
            'uidb64': uidb64,
            'token': token
        }
        return render(request, 'authentication/set-new-password.html', context)

    def post(self, request, uidb64, token):
        password = request.POST['password']
        password2 = request.POST['password2']

        if password != password2:
            messages.error(request, 'Passwords do not match')
            return redirect(f'/authentication/set-new-password/{uidb64}/{token}/')

        if len(password) < 6:
            messages.error(request, 'Password too short')
            return redirect(f'/authentication/set-new-password/{uidb64}/{token}/')

        try:
            user_id = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=user_id)

            if PasswordResetTokenGenerator().check_token(user, token):
                user.set_password(password)
                user.save()

                messages.success(request, 'Password reset successfully')
                return redirect('login')

        except Exception as e:
            messages.error(request, 'Something went wrong, please try again')
            return redirect('login')

        return render(request, 'authentication/set-new-password.html')

class UpdateAccountView(LoginRequiredMixin, View):
    def get(self, request):
        context = {
            'username': request.user.username,
            'email': request.user.email
        }
        return render(request, 'authentication/account.html', context)

    def post(self, request):
        username = request.POST['username']
        old_password = request.POST['old_password']
        new_password = request.POST['password']
        confirm_password = request.POST['confirm_password']

        context = {
            'username': username,
            'email': request.user.email,
            'values': request.POST 
        }

        if old_password and not request.user.check_password(old_password):
            messages.error(request, 'Old password is incorrect.')
            return render(request, 'authentication/account.html', context)

        if new_password and new_password != confirm_password:
            messages.error(request, 'New passwords do not match.')
            return render(request, 'authentication/account.html', context)

        if new_password and len(new_password) < 6:
            messages.error(request, 'New password must be at least 6 characters long.')
            return render(request, 'authentication/account.html', context)

        if username and username != request.user.username and User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return render(request, 'authentication/account.html', context)

        if username and username != request.user.username:
            request.user.username = username

        if new_password:
            request.user.set_password(new_password)

        request.user.save()
        messages.success(request, 'Account updated successfully')
        return redirect('dashboard')
