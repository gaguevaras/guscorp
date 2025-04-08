from django.shortcuts import render
from rest_framework import viewsets, permissions, status, views
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from .models import Contact, ContactRequest
from .serializers import ContactSerializer, ContactRequestSerializer
from django.db import models
from accounts.models import CustomUser

# Create your views here.

class ContactViewSet(viewsets.ModelViewSet):
    serializer_class = ContactSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'delete', 'head', 'options']

    def get_queryset(self):
        # Return contacts where the current user is either the 'user' or the 'contact'
        return Contact.objects.filter(
            models.Q(user=self.request.user) |
            models.Q(contact=self.request.user)
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['delete'])
    def remove(self, request, pk=None):
        contact = self.get_object()
        # Also remove the reverse contact relationship
        Contact.objects.filter(
            user=contact.contact,
            contact=contact.user
        ).delete()
        contact.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(['POST'])
def create_contact_request(request):
    """
    Create a new contact request using email instead of user ID.
    """
    print(f"DEBUG: Processing POST request to create contact request with data: {request.data}")
    
    # Check if email is provided
    to_email = request.data.get('email')
    if not to_email:
        return Response(
            {"error": "Email is required"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Look up the user by email
    try:
        to_user = CustomUser.objects.get(email=to_email)
    except CustomUser.DoesNotExist:
        return Response(
            {"error": f"User with email {to_email} not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Create the data for the serializer with the found user
    data = {'to_user_id': to_user.id}
    
    # Check if this is a request to yourself
    if to_user.id == request.user.id:
        return Response(
            {"error": "You cannot send a contact request to yourself"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check if a contact already exists
    existing_contact = Contact.objects.filter(
        user=request.user,
        contact=to_user
    ).exists()
    
    if existing_contact:
        return Response(
            {"error": "This user is already in your contacts"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check if there's a pending request already
    existing_request = ContactRequest.objects.filter(
        from_user=request.user,
        to_user=to_user,
        status='pending'
    ).exists()
    
    if existing_request:
        return Response(
            {"error": "A pending request already exists for this user"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Create the serializer with the user ID we found
    serializer = ContactRequestSerializer(
        data=data,
        context={'request': request}
    )
    
    if not serializer.is_valid():
        print(f"DEBUG: Serializer errors: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        serializer.save(from_user=request.user)
        print(f"DEBUG: Successfully created contact request: {serializer.data}")
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    except Exception as e:
        print(f"DEBUG: Exception during contact request creation: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ContactRequestList(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        contact_requests = ContactRequest.objects.filter(
            models.Q(from_user=request.user) |
            models.Q(to_user=request.user)
        )
        serializer = ContactRequestSerializer(contact_requests, many=True)
        return Response(serializer.data)

class ContactRequestViewSet(viewsets.ModelViewSet):
    serializer_class = ContactRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'put', 'patch', 'delete', 'head', 'options', 'post']

    def get_queryset(self):
        return ContactRequest.objects.filter(
            models.Q(from_user=self.request.user) |
            models.Q(to_user=self.request.user)
        )

    def perform_create(self, serializer):
        serializer.save(from_user=self.request.user)

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        contact_request = self.get_object()
        if contact_request.to_user != request.user:
            return Response(
                {'error': 'You can only accept requests sent to you'},
                status=status.HTTP_403_FORBIDDEN
            )
        contact_request.accept()
        return Response({'status': 'contact request accepted'})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        contact_request = self.get_object()
        if contact_request.to_user != request.user:
            return Response(
                {'error': 'You can only reject requests sent to you'},
                status=status.HTTP_403_FORBIDDEN
            )
        contact_request.reject()
        return Response({'status': 'contact request rejected'})

    @action(detail=False, methods=['get'])
    def received(self, request):
        received_requests = ContactRequest.objects.filter(
            to_user=request.user,
            status='pending'
        )
        serializer = self.get_serializer(received_requests, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def sent(self, request):
        sent_requests = ContactRequest.objects.filter(
            from_user=request.user,
            status='pending'
        )
        serializer = self.get_serializer(sent_requests, many=True)
        return Response(serializer.data)

@api_view(['POST'])
def accept_contact_request(request, pk):
    """
    Accept a contact request.
    """
    print(f"DEBUG: Processing accept request for contact request {pk}")
    try:
        contact_request = ContactRequest.objects.get(pk=pk)
    except ContactRequest.DoesNotExist:
        return Response(
            {"error": f"Contact request with ID {pk} not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check permissions
    if contact_request.to_user != request.user:
        return Response(
            {'error': 'You can only accept requests sent to you'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Check if already accepted
    if contact_request.status == 'accepted':
        return Response({'status': 'contact request was already accepted'})
    
    # Check if already rejected
    if contact_request.status == 'rejected':
        return Response(
            {'error': 'This contact request was already rejected'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Update the status
        contact_request.status = 'accepted'
        contact_request.save(update_fields=['status', 'updated_at'])
        
        # Create bidirectional contacts - handle each direction individually
        try:
            # From user -> to user
            if not Contact.objects.filter(user=contact_request.from_user, contact=contact_request.to_user).exists():
                Contact.objects.create(user=contact_request.from_user, contact=contact_request.to_user)
        except Exception as e:
            print(f"DEBUG: Exception creating from_user->to_user contact: {str(e)}")
            
        try:
            # To user -> from user
            if not Contact.objects.filter(user=contact_request.to_user, contact=contact_request.from_user).exists():
                Contact.objects.create(user=contact_request.to_user, contact=contact_request.from_user)
        except Exception as e:
            print(f"DEBUG: Exception creating to_user->from_user contact: {str(e)}")
            
        return Response({'status': 'contact request accepted'})
    except Exception as e:
        print(f"DEBUG: Exception during contact request acceptance: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def reject_contact_request(request, pk):
    """
    Reject a contact request.
    """
    print(f"DEBUG: Processing reject request for contact request {pk}")
    try:
        contact_request = ContactRequest.objects.get(pk=pk)
    except ContactRequest.DoesNotExist:
        return Response(
            {"error": f"Contact request with ID {pk} not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check permissions
    if contact_request.to_user != request.user:
        return Response(
            {'error': 'You can only reject requests sent to you'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Check if already accepted
    if contact_request.status == 'accepted':
        return Response(
            {'error': 'This contact request was already accepted and cannot be rejected'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check if already rejected
    if contact_request.status == 'rejected':
        return Response({'status': 'contact request was already rejected'})
    
    try:
        # Update the status
        contact_request.status = 'rejected'
        contact_request.save(update_fields=['status', 'updated_at'])
        return Response({'status': 'contact request rejected'})
    except Exception as e:
        print(f"DEBUG: Exception during contact request rejection: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
