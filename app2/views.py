from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.contrib import auth
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth import logout
from .models import staff
from hospitalmanagement import settings
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.urls import reverse
from django.template.loader import render_to_string
from .forms import SetPasswordForm
from django.utils.html import strip_tags
from app2.models import Patient,Medical, Appointment, Room
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from xhtml2pdf import pisa 
from io import BytesIO
from decimal import Decimal
from django.utils import timezone
from datetime import datetime
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
import logging
from .forms import RoomForm
import os

from django.views.generic.edit import CreateView
from django.urls import reverse_lazy

class AddRoomView(CreateView):
    model = Room
    form_class = RoomForm
    template_name = 'add_room.html'

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('profile')

def book_room(request):
    if request.method == 'POST':
        form = RoomForm(request.POST)
        if form.is_valid():
            form.save()
            # Handle success or redirect
            return redirect('success_url')
    else:
        form = RoomForm()
    
    context = {'form': form}
    return render(request, 'book_room.html', context)

logger = logging.getLogger(__name__)

def generate_pdf(request, appointment_id):

    appointment = get_object_or_404(Appointment, id=appointment_id)
    patient = get_object_or_404(Patient, user=request.user)
    medical_records = Medical.objects.filter(appointment_id=appointment_id)
    
    today_date = timezone.now().date()
    today_date_str = today_date.strftime('%Y-%m-%d')
    
    # Calculate totals
    subtotal = sum(record.total_price for record in medical_records)
    discount_rate = Decimal('0.05') 
    tax_rate = Decimal('0.18')  
    discount = subtotal * discount_rate
    sales_tax = subtotal * tax_rate
    
    amount_paid = Decimal('0.00') 
    
    
    # Calculate room cost if admit and release dates are the same
    room_cost = Decimal('0.00')
    admit_date = None
    release_date = None

    medical_record = medical_records.first()  # Assuming only one medical record per appointment for simplicity
    if medical_record:
        admit_date = medical_record.admit_date
        release_date = medical_record.release_date

        if admit_date and release_date:
            if admit_date == release_date:
                # Case: Admit and release date are the same day
                room = medical_record.room
                if room:
                    room_cost = room.price
            else:
                # Case: Admit and release date are different days
                duration_days = (release_date - admit_date).days
                room = medical_record.room
                if room:
                    room_cost = room.price * duration_days
                    
    total = subtotal - discount + room_cost + sales_tax
    balance_due = total - amount_paid
    
    context = {
        'appointment': appointment,
        'patient': patient,
        'medical_records': medical_records,
        'subtotal': subtotal,
        'discount': discount,
        'sales_tax': sales_tax,
        'total': total,
        'amount_paid': amount_paid,
        'balance_due': balance_due,
        'today_date': today_date_str,
        'room_cost': room_cost,
    }

    html_content = render_to_string('bill_template.html', context)
    logger.debug(f'Rendered HTML content: {html_content}')
    
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html_content.encode('UTF-8')), result)
    
    if not pdf.err:
        subject = f'Your Medical Invoice for Appointment #{appointment.id}'
        message = f'Please find attached your medical invoice for appointment #{appointment.id}.'
        from_email = '11a11137smit2019@gmail.comm' 
        to_email = appointment.email
        
        email = EmailMessage(subject, message, from_email, [to_email])
        email.attach(f'appointment_{appointment.id}_bill.pdf', result.getvalue(), 'application/pdf')
        
        email.send()

        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="appointment_{appointment.id}_bill.pdf"'
        return response
    
    return HttpResponse('Error rendering PDF', status=500)


@login_required
def patient_profile(request):
    patient = get_object_or_404(Patient, user=request.user)
    appointments = Appointment.objects.filter(patient_username=request.user.username).order_by('date')
    medical_records = Medical.objects.filter(patient=request.user.username).order_by('appointment_date')
    context = {
        'patient': patient,
        'appointments': appointments,
        'medical_records': medical_records,
    }
    return render(request, 'patient_profile.html', context)

def add_staff(request):
    if request.method == 'POST':
        username = request.POST.get('name')
        email = request.POST.get('email')
        department = request.POST.get('department')
        staff_type = request.POST.get('staff_type')
        status = request.POST.get('status')
        first_name = request.POST.get('firstname')
        last_name = request.POST.get('lastname')
        staff_ty = True
        user = User.objects.create_user(username=username, is_staff= staff_ty, email=email, password='defaultpassword', first_name=first_name, last_name=last_name)
        useridt = user.id 
        print(useridt)
        user.save()

        Satff = staff(user=user)
        Satff.save()
        print("Staff created successfully")

        try:
            staff_record = staff.objects.get(user_id=useridt)
            print(staff_record)
        except staff.DoesNotExist:
            return render(request, 'error.html', {'message': 'Staff record does not exist for this username'}) 
        
        staff_record.name=username
        staff_record.email=email
        staff_record.department=department
        staff_record.staff_type=staff_type, 
        staff_record.status=status
        staff_record.save()
        

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        password_creation_link = request.build_absolute_uri(reverse('create_password', kwargs={'uidb64': uid, 'token': token}))

        subject = "Welcome to Hospital"
        message = render_to_string('welcome_email.html', {
            'user': user,
            'password_creation_link': password_creation_link,
        })
        
        plain_message = strip_tags(message)

        from_email = settings.EMAIL_HOST_USER
        to_list = [user.email]
        send_mail(subject, plain_message, from_email, to_list, fail_silently=True, html_message=message)
            
        return redirect('/')  
    
    return render(request, 'add_staff.html')

from django.utils.http import urlsafe_base64_decode

def create_password(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            form = SetPasswordForm(request.POST)
            if form.is_valid():
                user.set_password(form.cleaned_data['new_password1'])
                user.save()
                return redirect('/')
        else:
            form = SetPasswordForm()
        return render(request, 'create_password.html', {'form': form})
    else:
        return render(request, 'invalid_link.html')

def signup(request):
    if request.method == 'POST':
        username = request.POST['username']
        firstname = request.POST['firstname']
        lastname = request.POST['lastname']
        email = request.POST['email']
        password = request.POST['password']
        # user_type = "Patient"
        # if User.objects.filter(username=username):
        #     messages.error(request, "USER EXIST")
        #     return redirect('/')
        
        # if User.objects.filter(email=email):
        #     messages.error(request, "Email EXIST")
        # return redirect('/')
        x = User.objects.create_user(username=username, first_name=firstname, last_name=lastname, email=email, password=password)
        x.save()
        print("user created successfully")
        
        # Create the Patient instance
        patient = Patient(user=x)
        patient.save()
        print("Patient created successfully")
        
        subject = "welcome to Hospital"
        message = "Hello " + x.first_name + "!\n" + "Thank You!"
        from_email = settings.EMAIL_HOST_USER
        to_list = [x.email]
        send_mail(subject, message, from_email, to_list, fail_silently=True)
        
        return redirect('/')
    else:
        return render(request, 'login.html')

def loginform(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        print(request.method)
        print(username)
        print(password)
        
        user = authenticate(request, username=username, password=password)
        print(user)
        if user is not None:
            login(request, user)
            return redirect('/')  
        else:
            messages.error(request, 'Invalid email or password')
            return render(request, 'login.html')
    else:
        return render(request, 'login.html')
    
def profile(request):
    if not request.user.is_authenticated:
        return redirect('loginform')
    return render(request, 'profile.html', {'user': request.user})



def logout_view(request):
    logout(request)
    return redirect('/')
