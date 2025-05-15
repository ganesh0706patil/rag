import os
import faiss
import numpy as np
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.conf import settings

from .retriever import DPRRetriever
from .generator import AnswerGenerator
from .models import UploadedFile
from .forms import UploadFileForm
from .utils import extract_text_from_file



def home(request):
    return render(request, 'ragApp/layout.html')


def login_view(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, "Login successful!")
            return redirect('profile')  # Redirect to profile
        else:
            messages.error(request, "Invalid username or password")

    return render(request, 'ragApp/login.html')


def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out successfully!")
    return redirect('login')


def register(request):
    if request.method == "POST":
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        if password1 != password2:
            messages.error(request, "Passwords do not match!")
            return redirect('register')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken!")
            return redirect('register')

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email is already in use!")
            return redirect('register')

        user = User.objects.create_user(
            username=username, 
            email=email, 
            password=password1, 
            first_name=first_name, 
            last_name=last_name
        )
        user.save()

        messages.success(request, "Account created successfully! You can now log in.")
        return redirect('login')

    return render(request, 'ragApp/register.html')

@login_required
def profile_view(request):
    return render(request, 'ragApp/profile.html')

@login_required
def upload_file(request):
    """Handles file upload"""
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = form.save(commit=False)
            uploaded_file.user = request.user  
            uploaded_file.save()

            # 🔹 Extract text from the file
            file_path = uploaded_file.file.path  # Get the actual file path
            extracted_text = extract_text_from_file(file_path)

            # 🔹 Save extracted text to a model (optional)
            uploaded_file.extracted_text = extracted_text
            uploaded_file.save()

            messages.success(request, "File uploaded and processed successfully!")
            return redirect('file_list')
    else:
        form = UploadFileForm()

    files = UploadedFile.objects.filter(user=request.user)
    return render(request, 'ragApp/upload.html', {'form': form, 'files': files})


@login_required
def file_list(request):
    """Displays all files uploaded by the logged-in user"""
    files = UploadedFile.objects.filter(user=request.user)  # Get user's uploaded files
    return render(request, 'ragApp/file_list.html', {'files': files})

# ✅ Delete File
@login_required
def delete_file(request, file_id):
    """Handles file deletion"""
    file = get_object_or_404(UploadedFile, id=file_id, user=request.user)
    
    file_path = os.path.join(settings.MEDIA_ROOT, str(file.file))  # Get file path
    if os.path.exists(file_path):
        os.remove(file_path)  # Delete file from storage
    
    file.delete()  # Remove file entry from database
    messages.success(request, "File deleted successfully!")
    
    return redirect('file_list')

@login_required
def search_query(request):
    response = None

    if request.method == "POST":
        query = request.POST.get("query")

        if query:
            try:
                retriever = DPRRetriever()  # Initialize retriever
                
                # 🔹 Retrieve all uploaded documents
                uploaded_files = UploadedFile.objects.all()
                contexts = [file.extracted_text for file in uploaded_files if file.extracted_text]  # Get extracted text

                if not contexts:
                    messages.error(request, "No documents available for retrieval.")
                    return render(request, "ragApp/search.html", {"response": None})

                retrieved_texts = retriever.retrieve(query, contexts)  # Pass both query & contexts

                generator = AnswerGenerator()  # Initialize answer generator
                response = generator.generate_answer(query, retrieved_texts)  # Generate answer
            except Exception as e:
                messages.error(request, f"Error processing query: {str(e)}")

    return render(request, "ragApp/search.html", {"response": response})
