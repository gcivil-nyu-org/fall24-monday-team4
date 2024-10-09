from django.contrib.auth.forms import *

def sign_up(request):
    if request.method == 'POST':
        form = RegistrationForm(request.post)
        if form.is_valid():
            user = form.save()
            login(request,user)
            return redirect('/')
    else:
        form = RegistrationForm()
    return render(request, 'register.html', {'form': form})