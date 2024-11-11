from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q, Count, BooleanField, Case, When
from accounts.models import UserReports
import logging

logger = logging.getLogger(__name__)

@login_required
def admin_view(request):
    users = User.objects.all()

    users_with_unacknowledged_reports = User.objects.filter(
        reports_received__is_acknowledged=False
    ).annotate(
        report_count=Count('reports_received')
    ).distinct()

    users_with_only_acknowledged_reports = User.objects.annotate(
        unacknowledged_count=Count(
            Case(
                When(reports_received__is_acknowledged=False, then=1),
                output_field=BooleanField()
            )
        ),
        total_report_count=Count('reports_received')
    ).filter(
        unacknowledged_count=0,
        total_report_count__gt=0
    )

    # Example: Printing annotated field for debugging
    if users_with_unacknowledged_reports.exists():
        print("User with unacknowledged reports - Total reports count:", users_with_unacknowledged_reports[0].report_count)

    if users_with_only_acknowledged_reports.exists():
        print("User with only acknowledged reports - Total reports count:", users_with_only_acknowledged_reports[0].total_report_count)

    context = {
        'users_with_unacknowledged_reports': users_with_unacknowledged_reports,
        'users_with_only_acknowledged_reports': users_with_only_acknowledged_reports,
    }

    return render(request, "admin/admin_tabs.html", {"users": users, "reports": context})


#
# def authenticate_user_page(request):
#     return render(request, "admin/authenticate_users_list.html")

def reported_users_list(request):
    return
