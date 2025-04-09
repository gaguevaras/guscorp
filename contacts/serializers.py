from rest_framework import serializers
from .models import Contact, ContactRequest
from accounts.models import CustomUser

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'first_name', 'last_name']

class ContactSerializer(serializers.ModelSerializer):
    contact = UserSerializer(read_only=True)
    contact_id = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(),
        write_only=True,
        source='contact'
    )
    user = UserSerializer(read_only=True)
    other_user = serializers.SerializerMethodField()

    class Meta:
        model = Contact
        fields = ['id', 'contact', 'contact_id', 'user', 'other_user', 'created_at']
        read_only_fields = ['user', 'created_at']

    def get_other_user(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            # If the requesting user is the contact, show the user
            if request.user == obj.contact:
                return UserSerializer(obj.user).data
            # If the requesting user is the user, show the contact
            elif request.user == obj.user:
                return UserSerializer(obj.contact).data
        return None

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class ContactRequestSerializer(serializers.ModelSerializer):
    from_user = UserSerializer(read_only=True)
    to_user = UserSerializer(read_only=True)
    to_user_id = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(),
        write_only=True,
        source='to_user'
    )

    class Meta:
        model = ContactRequest
        fields = ['id', 'from_user', 'to_user', 'to_user_id', 'status', 'created_at', 'updated_at']
        read_only_fields = ['from_user', 'status', 'created_at', 'updated_at']

    def create(self, validated_data):
        validated_data['from_user'] = self.context['request'].user
        return super().create(validated_data) 