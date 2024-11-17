from django.urls import path
from . import views

urlpatterns = [
    path('adminview/', views.admin_view, name='admin_view'),
    path('documents/<int:user_id>/', views.get_user_documents, name='get_user_documents'),
    path('accept-document/<int:user_id>/<int:document_id>/', views.accept_document, name='accept_document'),
    path('reject-document/<int:user_id>/<int:document_id>/', views.reject_document, name='reject_document'),
    path('get-reported-users/', views.reported_users_list, name="reported_users"),
    path('get-user-reports/', views.get_user_reports, name='get_user_reports'),
    path('acknowledge-report/', views.acknowledge_report, name='acknowledge_report'),
    path('deactivate-account/', views.deactivate_account, name='deactivate_account'),
    path('get_admin_documents/', views.get_admin_document_list, name='get_admin_documents')
    # path("userlist/", views.authenticate_user_page, name="authenticate_user_tab_list"),
]
