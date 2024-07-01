"""
URL configuration for hospitalmanagement project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('appointment/', views.appointment, name='appointment'),
    path('blog/', views.blog, name='blog'),  
    path('search/', views.search, name='search'),
    path('team/', views.team, name='team'),
    path('testimonial/', views.testimonial, name='testimonial'),
    path('detail/', views.detail, name='detail'),
    path('price/', views.price, name='price'),
    path('service/', views.service, name='service'),
    path('app2/',include('app2.urls')),
    path('get-doctors-by-department/', views.get_doctors_by_department, name='get_doctors_by_department'),
    path('book-appointment/', views.book_appointment, name='book_appointment'),
    path('staff/', views.staff_list, name='staff_list'),
    path('registration/', views.doctor_registration, name='doctor_registration'),
    path('Patientregistration/', views.patient_registration, name='patient_registration'),
    path('get-available-slots/', views.get_available_slots, name='get_available_slots'),
    path('appointments/', views.appointment_list, name='appointment_list'),
    path('appointments/<int:appointment_id>/mark-as-done/', views.mark_as_done, name='mark_as_done'),
    path('doctor/appointments/', views.doctor_appointment_list, name='doctor_appointment_list'),
    # path('doctor/appointments/assign_medicine/<int:appointment_id>/', views.assign_medicine, name='assign_medicine'),
    path('medicines/', views.medicine_list, name='medicine_list'),
    path('medicines/add/', views.add_medicine, name='add_medicine'),
    path('view-image/<str:image_name>/', views.view_image, name='view_image'),
    path('notifications/', views.patient_notifications, name='patient_notifications'),
    path('notifications/select-room/<int:notification_id>/', views.select_room, name='select_room'),
    path('assign-medicine/<int:appointment_id>/', views.assign_medicine, name='assign_medicine'),
    # path('notifications/', patient_notifications, name='patient_notifications'),
    # path('notifications/select-room/<int:notification_id>/', select_room, name='select_room'),
]

