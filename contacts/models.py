from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError

class Contact(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='contacts'
    )
    contact = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='contacted_by'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'contact']
        ordering = ['-created_at']

    def clean(self):
        if self.user == self.contact:
            raise ValidationError("A user cannot be their own contact.")
        if Contact.objects.filter(user=self.contact, contact=self.user).exists():
            raise ValidationError("This contact relationship already exists.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.email} - {self.contact.email}"

class ContactRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]

    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_contact_requests'
    )
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_contact_requests'
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['from_user', 'to_user']
        ordering = ['-created_at']

    def clean(self):
        if self.from_user == self.to_user:
            raise ValidationError("A user cannot send a contact request to themselves.")
        if Contact.objects.filter(user=self.from_user, contact=self.to_user).exists():
            raise ValidationError("These users are already contacts.")
        if self.status == 'pending' and ContactRequest.objects.filter(
            from_user=self.to_user,
            to_user=self.from_user,
            status='pending'
        ).exists():
            raise ValidationError("A pending request already exists between these users.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def accept(self):
        if self.status == 'pending':
            self.status = 'accepted'
            self.save()
            # Create the contact relationship if it doesn't exist
            # From user -> to user
            if not Contact.objects.filter(user=self.from_user, contact=self.to_user).exists():
                Contact.objects.create(user=self.from_user, contact=self.to_user)
            # To user -> from user
            if not Contact.objects.filter(user=self.to_user, contact=self.from_user).exists():
                Contact.objects.create(user=self.to_user, contact=self.from_user)

    def reject(self):
        if self.status == 'pending':
            self.status = 'rejected'
            self.save()

    def __str__(self):
        return f"{self.from_user.email} -> {self.to_user.email} ({self.status})"
