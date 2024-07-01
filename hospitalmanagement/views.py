from datetime import datetime, timedelta
from decimal import Decimal
from io import BytesIO
from urllib import response
from django.http import HttpResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth import logout
from django.http import JsonResponse
from app2.models import Appointment, Notification,Patient,staff, Slot, Medicine, Medical, Room
from hospitalmanagement import settings
from django.core.mail import send_mail
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
import json, logging
from django.core.serializers.json import DjangoJSONEncoder
from app2.forms import MedicineForm,AssignMedicineForm
from app2.views import generate_pdf
import os

logger = logging.getLogger(__name__)

def view_image(request, image_name):
    try:
        image_path = os.path.join(settings.STATICFILES_DIRS[0], image_name)
        with open(image_path, 'rb') as f:
            return HttpResponse(f.read(), content_type='image/png')
    except FileNotFoundError:
        logger.error(f"Image '{image_name}' not found.")
        return HttpResponse('Image not found', status=404)

logger = logging.getLogger(__name__)

@login_required
def doctor_appointment_list(request):
    try:
        doctor = request.user.staff_set.first()
        if not doctor:
            return redirect('login')

        appointments = Appointment.objects.filter(doctor=doctor).order_by('date', 'time')
        return render(request, 'doctor_appointments_list.html', {'appointments': appointments})
    except Exception as e:
        logger.error(f"Error fetching appointments: {e}")
        return redirect('loginform')

@login_required
def medicine_list(request):
    medicines = Medicine.objects.all()
    return render(request, 'medicine_list.html', {'medicines': medicines})

def add_medicine(request):
    if request.method == 'POST':
        form = MedicineForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('medicine_list')
    else:
        form = MedicineForm()
    return render(request, 'add_medicine.html', {'form': form})

logger = logging.getLogger(__name__)
from django.db import transaction
import datetime
from django.contrib.auth.models import User

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from app2.models import Appointment, Medicine, Room, Medical, Notification, User

@login_required
def assign_medicine(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    medicines = Medicine.objects.all()
    rooms = Room.objects.filter(is_available=True)
    doctor = appointment.doctor

    # Fetch last submitted medicines for the current appointment
    last_medicines = Medical.objects.filter(appointment_id=appointment.id).order_by('-id')[:5]

    if request.method == 'POST':
        medicine_ids = request.POST.getlist('medicine_id[]')
        quantities = request.POST.getlist('quantity[]')
        prescription = request.POST.get('prescription')
        times = request.POST.getlist('time[]')
        need_admit = request.POST.get('need_admit')
        room_id = request.POST.get('room_type') if need_admit == 'yes' else None
        
        with transaction.atomic():
            # Check if a room is already assigned for this appointment
            existing_medical_records = Medical.objects.filter(appointment_id=appointment.id, room__isnull=False)
            if existing_medical_records.exists():
                room = existing_medical_records.first().room
            else:
                room = None
                if room_id:
                    room = get_object_or_404(Room, id=room_id)
                    # Check if room is available
                    if room.quantity < 1:
                        return JsonResponse({'error': 'Room is not available'}, status=400)
                    # Decrease the quantity of available rooms
                    room.quantity -= 1
                    if room.quantity < 1:
                        room.is_available = False
                    room.save()

            for i in range(len(medicine_ids)):
                medicine_id = medicine_ids[i]
                quantity = int(quantities[i])
                time = times[i]

                medicine = get_object_or_404(Medicine, id=medicine_id)
                quant = medicine.quantity  # Total available quantity
                price = medicine.price
                total_price = price * quantity

                if quant < quantity:
                    return JsonResponse({'error': 'Medicine is not available'}, status=400)

                medicine.quantity = quant - quantity
                medicine.save()
                
                import datetime
                # Create medical record
                medical_record = Medical.objects.create(
                    patient=appointment.patient_username,
                    doctor=doctor,
                    medicine=medicine,
                    quantity=quantity,
                    price=price,
                    total_price=total_price,
                    prescription=prescription,
                    medicine_time=time,
                    appointment_date=appointment.date,
                    appointment_id=appointment.id,
                    room=room if room_id else None,
                    admit_date=datetime.date.today() if room_id else None,
                )
                
                # Create a Notification (make sure Notification model and fields are defined properly)
                user = get_object_or_404(User, username=appointment.patient_username)
                
                # Check if a notification already exists for this appointment
                if not Notification.objects.filter(patient=user.id).exists():
                    Notification.objects.create(
                        patient=user,
                        message=f"Medicine '{medicine.name}' has been assigned by Dr. {doctor.last_name}",
                        is_read=False,
                        medical=medical_record,
                    )

        # Fetch last submitted medicines again after saving new ones
        last_medicines = Medical.objects.filter(appointment_id=appointment.id).order_by('-id')[:5]
        return redirect('doctor_appointment_list')
    context = {
        'appointment': appointment,
        'medicines': medicines,
        'rooms': rooms,
        'last_medicines': last_medicines,
    }

    return render(request, 'assign_medicine.html', context)

@login_required
def patient_notifications(request):
    unread_notifications_count = Notification.objects.filter(patient=request.user, is_read=False).count()
    notifications = Notification.objects.filter(patient=request.user, is_read=False)
    context = {
        'notifications': notifications,
        'unread_notifications_count': unread_notifications_count,
    }
    return render(request, 'patient_notifications.html', context)

from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect

@login_required
def select_room(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, patient=request.user)
    rooms = Room.objects.filter(is_available=True)

    if request.method == 'POST':
        room_id = request.POST.get('room_type')
        room = get_object_or_404(Room, id=room_id)

        # Check if room is available
        if room.quantity < 1:
            messages.error(request, 'Selected room is not available.')
            return redirect('patient_notifications')

        # Update room quantity and availability
        room.quantity -= 1
        if room.quantity < 1:
            room.is_available = False
        room.save()

        # Find the related medical record
        medical_record = Medical.objects.filter(notification=notification).first()
        if not medical_record:
            messages.error(request, 'No associated medical record found.')
            return redirect('patient_notifications')

        # Update the medical record with the selected room type and admit date
        medical_record.room = room
        import datetime
        medical_record.admit_date = datetime.date.today()
        medical_record.save()

        # Update the notification as read
        notification.is_read = True
        notification.save()

        messages.success(request, 'Room type selected successfully.')
        return redirect('patient_notifications')

    context = {
        'notification': notification,
        'rooms': rooms,
    }

    return render(request, 'select_room.html', context)



# @login_required
# def doctor_appointment_list(request):
#     try:
#         # Fetch the doctor record associated with the logged-in user
#         doctor = staff.objects.get(user=request.user)
#         appointments = Appointment.objects.filter(doctor=doctor).order_by('date', 'time')
#         print("try ")
#         return render(request, 'doctor_appointments_list.html', {'appointments': appointments})
#     except staff.DoesNotExist:
#         logger.error(f"User {request.user.id} is not associated with any staff record")
#         return redirect('loginform')  # Adjust this to your login URL or view name
#     except Exception as e:
#         logger.error(f"Error fetching appointments: {e}")
#         return redirect('loginform')  # Adjust this to your login URL or view name
    
# @login_required
# def assign_medicine(request, appointment_id):
#     appointment = get_object_or_404(Appointment, id=appointment_id)
#     medicines = Medicine.objects.all()

#     if request.method == 'POST':
#         selected_medicine_id = request.POST.get('medicine_id')
#         selected_medicine = Medicine.objects.get(id=selected_medicine_id)
#         # Here you can add logic to assign the medicine to the appointment or patient
#         # For example, you can create a new model for prescription and save it
#         return redirect('doctor_appointments_list')

#     return render(request, 'assign_medicine.html', {'appointment': appointment, 'medicines': medicines})
    
# @login_required
# def medicine_list(request):
#     medicines = Medicine.objects.all()
#     return render(request, 'medicine_list.html', {'medicines': medicines})

# @login_required
# def add_medicine(request):
#     if request.method == 'POST':
#         form = MedicineForm(request.POST)
#         if form.is_valid():
#             form.save()
#             return redirect('medicine_list')
#     else:
#         form = MedicineForm()
#     return render(request, 'add_medicine.html', {'form': form})

def appointment_list(request):
    appointments = Appointment.objects.all()
    return render(request, 'appointments_list.html', {'appointments': appointments})

from django.utils.dateparse import parse_time
import datetime
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from xhtml2pdf import pisa 

@login_required
def mark_as_done(request, appointment_id):
    print("START")
    appointment = get_object_or_404(Appointment, id=appointment_id)
    print("START=1")
    patient = get_object_or_404(Patient, user__username=appointment.patient_username)
    
    # Mark appointment as done
    appointment.status = 'Done'
    appointment.is_history = True
    appointment.save()

    # Retrieve the logged-in user's staff record (doctor)
    doctor = request.user.staff_set.first()
    print("MID-1")

    # Find all medical records associated with this appointment
    medical_records = Medical.objects.filter(appointment_id=appointment.id)

    # Iterate through each medical record and update release date and room quantity if room is not None
    for medical_record in medical_records:
        medical_record.release_date = timezone.now().date()
        medical_record.save()

        if medical_record.room:
            medical_record.room.quantity += 1
            if medical_record.room.quantity > 0:
                medical_record.room.is_available = True
            medical_record.room.save()
    
    # Calculate the billing details
    today_date = timezone.now().date()
    today_date_str = today_date.strftime('%Y-%m-%d')
    
    # Calculate totals
    subtotal = sum(record.total_price for record in medical_records)
    discount_rate = Decimal('0.05') 
    tax_rate = Decimal('0.18')  
    discount = subtotal * discount_rate
    sales_tax = subtotal * tax_rate
    
    amount_paid = Decimal('0.00') 
    print("MID-3")
    
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
        from_email = '11a11137smit2019@gmail.com' 
        to_email = patient.user.email
        
        email = EmailMessage(subject, message, from_email, [to_email])
        email.attach(f'appointment_{appointment.id}_bill.pdf', result.getvalue(), 'application/pdf')
        
        email.send()

        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="appointment_{appointment.id}_bill.pdf"'
        return response
    
    messages.success(request, 'Medication report sent successfully via email.')
    print("END")
    return redirect('doctor_appointment_list')

# @login_required
# def mark_as_done(request, appointment_id):
#     print("START")
#     appointment = Appointment.objects.get(id=appointment_id)
#     print("START=1")
#     patient = Patient.objects.get(user_id__username=appointment.patient_username)
#     # Mark appointment as done
#     appointment.status = 'Done'
#     appointment.is_history = True
#     appointment.save()

#     # Retrieve the logged-in user's staff record (doctor)
#     doctor = request.user.staff_set.first()
#     print("MID-1")

#     # Find all medical records associated with this appointment
#     medical_records = Medical.objects.filter(appointment_id=appointment.id)

#     # Iterate through each medical record and update release date
#     for medical_record in medical_records:
#         medical_record.release_date = timezone.now().date()
#         medical_record.save()
#         medical_record.room.quantity += 1
#         medical_record.room.save()    
    
#     # appointment = get_object_or_404(Appointment, id=appointment_id)
#     # patient = get_object_or_404(Patient, user=request.user)
#     medical_records = Medical.objects.filter(appointment_id=appointment_id)
    
#     today_date = timezone.now().date()
#     today_date_str = today_date.strftime('%Y-%m-%d')
    
#     # Calculate totals
#     subtotal = sum(record.total_price for record in medical_records)
#     discount_rate = Decimal('0.05') 
#     tax_rate = Decimal('0.18')  
#     discount = subtotal * discount_rate
#     sales_tax = subtotal * tax_rate
    
#     amount_paid = Decimal('0.00') 
#     print("MID-3")
    
    
#     # Calculate room cost if admit and release dates are the same
#     room_cost = Decimal('0.00')
#     admit_date = None
#     release_date = None

#     medical_record = medical_records.first()  # Assuming only one medical record per appointment for simplicity
#     if medical_record:
#         admit_date = medical_record.admit_date
#         release_date = medical_record.release_date

#         if admit_date and release_date:
#             if admit_date == release_date:
#                 # Case: Admit and release date are the same day
#                 room = medical_record.room
#                 if room:
#                     room_cost = room.price
#             else:
#                 # Case: Admit and release date are different days
#                 duration_days = (release_date - admit_date).days
#                 room = medical_record.room
#                 if room:
#                     room_cost = room.price * duration_days
                    
#     total = subtotal - discount + room_cost + sales_tax
#     balance_due = total - amount_paid
    
#     context = {
#         'appointment': appointment,
#         'patient': patient,
#         'medical_records': medical_records,
#         'subtotal': subtotal,
#         'discount': discount,
#         'sales_tax': sales_tax,
#         'total': total,
#         'amount_paid': amount_paid,
#         'balance_due': balance_due,
#         'today_date': today_date_str,
#         'room_cost': room_cost,
#     }

#     html_content = render_to_string('bill_template.html', context)
#     logger.debug(f'Rendered HTML content: {html_content}')
    
#     result = BytesIO()
#     pdf = pisa.pisaDocument(BytesIO(html_content.encode('UTF-8')), result)
    
#     if not pdf.err:
#         subject = f'Your Medical Invoice for Appointment #{appointment.id}'
#         message = f'Please find attached your medical invoice for appointment #{appointment.id}.'
#         from_email = '11a11137smit2019@gmail.comm' 
#         to_email = appointment.email
        
#         email = EmailMessage(subject, message, from_email, [to_email])
#         email.attach(f'appointment_{appointment.id}_bill.pdf', result.getvalue(), 'application/pdf')
        
#         email.send()

#         response = HttpResponse(result.getvalue(), content_type='application/pdf')
#         response['Content-Disposition'] = f'attachment; filename="appointment_{appointment.id}_bill.pdf"'
#         return response
    
#     messages.success(request, 'Medication report sent successfully via email.')
#     print("END")
#     return redirect('doctor_appointment_list')


def view_appointment_history(request):
    if request.user.is_authenticated:
        doctor_email = request.user.email
        
        try:
            doctor = staff.objects.get(email=doctor_email)
        except staff.DoesNotExist:
            return render(request, 'no_appointments.html', {'message': 'You are not registered as a doctor.'})
        
        done_appointments = Appointment.objects.filter(doctor=doctor, done=True)
        return render(request, 'view_appointment_history.html', {'appointments': done_appointments})
    else:
        return redirect('login')


# def assign_medicine(request, appointment_id):
#     if request.method == 'POST':
#         try:
#             doctor = request.user.staff_set.first()
#             appointment = Appointment.objects.get(id=appointment_id, doctor=doctor)
#             medicine_ids = request.POST.getlist('medicines')
#             medicines = Medicine.objects.filter(id__in=medicine_ids)
#             appointment.medicines.set(medicines)
#             appointment.save()
#             return redirect('doctor_appointments_list')
#         except Exception as e:
#             logger.error(f"Error assigning medicines: {e}")
#             return JsonResponse({'error': 'An error occurred'}, status=500)
#     else:
#         try:
#             doctor = request.user.staff_set.first()
#             appointment = Appointment.objects.get(id=appointment_id, doctor=doctor)
#             medicines = Medicine.objects.all()
#             return render(request, 'assign_medicine.html', {'appointment': appointment, 'medicines': medicines})
#         except Appointment.DoesNotExist:
#             return JsonResponse({'error': 'Appointment not found'}, status=404)
#         except Exception as e:
#             logger.error(f"Error fetching appointment details: {e}")
#             return JsonResponse({'error': 'An error occurred'}, status=500)

from django.contrib import messages

def patient_registration(request):
    if request.method == 'POST':
        first_name = request.POST.get('firstname')
        last_name = request.POST.get('lastname')
        gender = request.POST.get('gender')
        email = request.POST.get('email')
        phone_number = request.POST.get('phone')
        birth_date = request.POST.get('birthdate')
        blood_group = request.POST.get('blood')
        sugar = request.POST.get('sugar')
        concerns = request.POST.get('concern')
        
        print(first_name)
        print(request.method)
        auth_user = request.user
        print(auth_user.id)
        print(Patient.user_id)

        try:
            patient_record = Patient.objects.get(user_id=auth_user.id)
            print(patient_record)
        except Patient.DoesNotExist:
            messages.error(request, 'Patient record does not exist for this user.')
            return render(request, 'error.html', {'message': 'Patient record does not exist for this user.'})
        
        patient_record.first_name = first_name
        patient_record.last_name = last_name
        patient_record.gender = gender
        patient_record.email = email
        patient_record.phone_number = phone_number
        patient_record.birth_date = birth_date
        patient_record.blood_group = blood_group
        patient_record.sugar = sugar
        patient_record.concerns = concerns
        patient_record.save()
        
        messages.success(request, 'Patient details updated successfully.')
        return redirect('/')  
    else:
        auth_user = request.user
        patient_record = None
        try:
            patient_record = Patient.objects.get(user_id=auth_user.id)
        except Patient.DoesNotExist:
            messages.error(request, 'Patient record does not exist for this user.')
            return render(request, 'error.html', {'message': 'Patient record does not exist for this user.'})
        
    patient = get_object_or_404(Patient, user=request.user)
    print(patient)
    
    context = {
        'patient': patient,
    }
    
    return render(request, 'patient_form.html', context)


from datetime import datetime 

def doctor_registration(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        birth_date_str = request.POST.get('birth_date')
        birth_date = datetime.strptime(birth_date_str, '%d/%m/%Y').date()
       
        gender = request.POST.get('gender')
        phone_number = request.POST.get('phone_number')
        doctor_id = request.POST.get('doctor_id')
        specialization = request.POST.get('specialization')
        experience = request.POST.get('experience')
        medical_school = request.POST.get('medical_school')
        graduation_year = request.POST.get('graduation_year')
        languages = request.POST.get('languages')
        country = request.POST.get('country')
        city = request.POST.get('city')
        publications = request.POST.get('publications')
        awards = request.POST.get('awards')
        hobbies = request.POST.get('hobbies')
        capacity_per_hour = request.POST.get('capacity')
        submission_date_str = request.POST.get('submission_date')
        submission_date = datetime.strptime(submission_date_str, '%d/%m/%Y').date()
        auth_user = request.user
        print(capacity_per_hour)

        try:
            staff_record = staff.objects.get(name=auth_user.username)
        except staff.DoesNotExist:
            return render(request, 'error.html', {'message': 'Staff record does not exist for this username'}) 
        
        staff_record.first_name = first_name
        staff_record.last_name = last_name
        staff_record.birth_date = birth_date
        staff_record.gender = gender
        staff_record.phone_number = phone_number
        staff_record.medical_license = doctor_id
        staff_record.specialization = specialization
        staff_record.experience = experience
        staff_record.medical_school = medical_school
        staff_record.graduation_year = graduation_year
        staff_record.country = country
        staff_record.city = city
        staff_record.languages = languages
        staff_record.publications = publications
        staff_record.awards = awards
        staff_record.hobbies = hobbies
        staff_record.capacity_per_hour = capacity_per_hour
        staff_record.submission_date = submission_date
        staff_record.submitted_registration = True
        staff_record.save()
        
        
          # Handle schedules
        days = request.POST.getlist('day[]')
        start_times = request.POST.getlist('start_time[]')
        end_times = request.POST.getlist('end_time[]')

        # Clear existing slots for this staff
        Slot.objects.filter(staff=staff_record).delete()

        for day, start_time, end_time in zip(days, start_times, end_times):
            Slot.objects.create(
                staff=staff_record,
                day=day,
                start_time=start_time,
                end_time=end_time
            )
        
        return redirect('/')  
    else:
        staff_record = None
        auth_user = request.user
        try:
            staff_record = staff.objects.get(name=auth_user.username)
        except staff.DoesNotExist:
            pass
        
        return render(request, 'doctor_reg.html', {'staff': staff_record})


def staff_list(request):
    staff_members = staff.objects.all()
    return render(request, 'staff_list.html', {'staff_members': staff_members})


def get_doctors_by_department(request):
    department_name = request.GET.get('department_name')
    doctors = staff.objects.filter(department=department_name).values('id', 'name')
    doctor_list = [{'id': doctor['id'], 'name': doctor['name']} for doctor in doctors]
    return JsonResponse(doctor_list, safe=False)





logger = logging.getLogger(__name__)

def get_available_slots(request):
    date = request.GET.get('date')
    doctor_id = request.GET.get('doctor_id')
    
    if not date or not doctor_id:
        logger.error("Invalid parameters: date or doctor_id is missing")
        return JsonResponse({'error': 'Invalid parameters'}, status=400)

    try:
        date_obj = datetime.strptime(date, '%Y-%m-%d')
        day_of_week = date_obj.strftime('%A').lower()
    except ValueError as e:
        logger.error(f"Date conversion error: {e}")
        return JsonResponse({'error': 'Invalid date format'}, status=400)
    
    logger.info(f"Fetching slots for doctor {doctor_id} on day {day_of_week}")

    try:
        doctor = staff.objects.get(id=doctor_id)
        capacity_per_hour = doctor.capacity_per_hour
    except staff.DoesNotExist:
        logger.error(f"Doctor with ID {doctor_id} does not exist")
        return JsonResponse({'error': 'Doctor not found'}, status=404)
    
    try:
        booked_slots = Appointment.objects.filter(doctor_id=doctor_id, date=date).values_list('time', flat=True)
        slots = Slot.objects.filter(staff_id=doctor_id, day=day_of_week).values('start_time', 'end_time')
    except Slot.DoesNotExist:
        logger.info("No slots found")
        return JsonResponse({'availableSlots': []}) 

    available_slots = []

    for slot in slots:
        start_time = slot['start_time']
        end_time = slot['end_time']
        slot_duration = (datetime.combine(datetime.min, end_time) - datetime.combine(datetime.min, start_time)).seconds // 60
        sub_slot_duration = 60 // capacity_per_hour
        
        current_start_time = start_time
        while current_start_time < end_time:
            current_end_time = (datetime.combine(datetime.min, current_start_time) + timedelta(minutes=sub_slot_duration)).time()
            if current_end_time > end_time:
                break
            
            slot_time_str = f"{current_start_time.strftime('%H:%M')} - {current_end_time.strftime('%H:%M')}"
            
            if slot_time_str not in booked_slots:
                available_slots.append({
                    'time': slot_time_str
                })
            
            current_start_time = current_end_time

    logger.info(f"Available slots: {available_slots}")

    return JsonResponse({'availableSlots': available_slots}, encoder=DjangoJSONEncoder)

from django.http import HttpResponseNotFound

@csrf_exempt    
def book_appointment(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        mobile = request.POST.get('mobile')
        department_name = request.POST.get('department')
        doctor_id = request.POST.get('doctor')
        date = request.POST.get('date')
        time = request.POST.get('time')
        description = request.POST.get('description')
        patient_username = request.POST.get('patient_username')
        print(request.POST.get('patient_username'))
        

         # Fetch patient based on username (assuming first name matches)
        # patients = Patient.objects.filter(user__first_name=patient_username)
        # if patients.exists():
        #     print(patients)
        #     patient = patients.first()
        #     print("patirn")
        #     print(patient)# Select the first patient (you may want to refine this logic)
        # else:
        #     return HttpResponseNotFound("Patient not found")

        
        try:
            doctor = staff.objects.get(id=doctor_id)
        except staff.DoesNotExist:
            return JsonResponse({'error': 'Doctor not found'}, status=404)
        
         # Check if the selected slot is already full
        # appointments_in_slot = Appointment.objects.filter(date=date, time=time).count()
        # print(doctor_id)
        # print(doctor.capacity_per_hour)
        appointments_in_slot = Appointment.objects.filter(date=date, time=time, doctor_id=doctor_id).count()
        # return appointments_in_slot >= 4
        if appointments_in_slot >= doctor.capacity_per_hour:
            return JsonResponse({'error': 'Selected slot is already full'}, status=400)
        
        appointment = Appointment(
            name=name,
            email=email,
            mobile=mobile,
            department=department_name,
            doctor_id=doctor_id,
            date=date,
            time=time,
            description=description,
            patient_username=patient_username,
        )
        appointment.save()
        
        send_mail(
            'New Appointment Booking',
            f'Patient Name: {name}\nEmail: {email}\nMobile: {mobile}\nDepartment: {department_name}\nDate: {date}\nTime: {time}\nDescription: {description}',
            settings.EMAIL_HOST_USER,
            [doctor.email],
            fail_silently=False,
        
        )
        # print("Hello")
        send_mail(
            'Appointment Booking Successfully!❤️',
            f'Thank you for Appointment Booking!❤️ \nPatient Name: {name}\nEmail: {email}\nMobile: {mobile}\nDepartment: {department_name}\nDate: {date}\nTime: {time}\nDescription: {description}',
            settings.EMAIL_HOST_USER,
            [email],
            fail_silently=False,
        )
        

        return JsonResponse({'success': 'Appointment booked successfully'})
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=400)

def home(request):
    return render(request, 'index.html')

def about(request):
    return render(request, 'about.html')

def registration_form(request):
    return render(request, 'doctor_reg.html')

def contact(request):
    return render(request, 'contact.html')

def appointment(request):
    return render(request, 'appointment.html')

def blog(request):
    return render(request, 'blog.html')

def service(request):
    return render(request, 'service.html')

def search(request):
    return render(request, 'search.html')

def testimonial(request):
    return render(request, 'testimonial.html')

def team(request):
    return render(request, 'team.html')

def detail(request):
    return render(request, 'detail.html')

def price(request):
    return render(request, 'price.html')



# def profile(request):
#     if not request.user.is_authenticated:
#         return redirect('loginform')
#     return render(request, 'profile.html', {'user': request.user})

# def add_staff(request):
#     # Placeholder for add staff view
#     if not request.user.is_authenticated or not request.user.is_superuser:
#         return redirect('loginform')
#     if request.method == 'POST':
#         # Process the form to add staff
#         # For now, we can just redirect to the profile page
#         return redirect('profile')
#     return render(request, 'add_staff.html')

# def logout_view(request):
#     logout(request)
#     return redirect('/')  


# def get_doctors_by_department(request):   
#     department_name = request.GET.get('department_name')
#     doctors = staff.objects.filter(department=department_name)
#     doctor_list = [{'id': doctor.id, 'name': f"{doctor.first_name} {doctor.last_name}"} for doctor in doctors]
#     return JsonResponse(doctor_list, safe=False)


# from django.views.decorators.http import require_GET

# @require_GET
# def get_available_slots(request):
#     selected_date = request.GET.get('date')
#     doctor_id = request.GET.get('doctor_id')
#     print(selected_date)
#     print(doctor_id)

#     available_slots = [
#         {"time": "10:00 AM"},
#         {"time": "11:00 AM"},
#         {"time": "12:00 PM"},
#         {"time": "01:00 PM"},
#         {"time": "02:00 PM"},
#         {"time": "03:00 PM"},
#         {"time": "04:00 PM"}
#     ]

    
#     if selected_date and doctor_id:
        
#         pass

#     return JsonResponse({"availableSlots": available_slots})

# def get_available_slots(request):
#     date_str = request.GET.get('date')
#     doctor_id = request.GET.get('doctor_id')
    
#     try:
#         date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
#         doctor = get_object_or_404(staff, id=doctor_id)
        
#         day_of_week = date.strftime('%A').lower()
#         slots = Slot.objects.filter(staff=doctor, day=day_of_week, available=True)
#         print(slots)
        
#         available_slots = []
#         for slot in slots:
#             start_time = datetime.datetime.combine(date, slot.start_time)
#             end_time = datetime.datetime.combine(date, slot.end_time)
            
#             time_slots = []
#             capacity = doctor.capacity_per_hour
#             while start_time + datetime.timedelta(minutes=60/capacity) <= end_time:
#                 time_slots.append(start_time.time().strftime('%H:%M'))
#                 start_time += datetime.timedelta(minutes=60/capacity)
            
#             available_slots.extend(time_slots)
        
#         return JsonResponse({'availableSlots': available_slots})
    
#     except ValueError:
#         return JsonResponse({'error': 'Invalid date format'}, status=400)

# def get_doctors_by_department(request):
#     department_name = request.GET.get('department_name')
#     doctors = staff.objects.filter(department=department_name).values('id', 'name')
#     return JsonResponse(list(doctors), safe=False)
