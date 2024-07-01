from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('signup',views.signup,name='signup'),
    path('loginform',views.loginform,name='loginform'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('add_staff/', views.add_staff, name='add_staff'),
    path('patient_profile/', views.patient_profile, name='patient_profile'),
    path('create-password/<uidb64>/<token>/', views.create_password, name='create_password'),
    path('generate_pdf/<int:appointment_id>/', views.generate_pdf, name='generate_pdf'),
    path('add_room/', views.AddRoomView.as_view(), name='add_room'),
    path('book_room/<int:room_id>/', views.book_room, name='book_room'),
]
