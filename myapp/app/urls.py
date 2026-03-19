from django.urls import path
from .views import upload_pdf, ask_pdf, summary_pdf

urlpatterns = [
    path('upload/', upload_pdf),
    path('ask/', ask_pdf),
    path('summary/', summary_pdf),
]