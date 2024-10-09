from django.shortcuts import render, redirect
from .forms import RegisterForm

def sign_up(request):
    if request.method == 'POST':
        form = RegisterForm(request.post)
        if form.is_valid():
            user = form.save()
            #login(request,user)
            return redirect('/')
    else:
        form = RegisterForm()
    return render(request, 'register.html', {'form': form})