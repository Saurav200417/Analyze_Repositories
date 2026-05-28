# serializers/authentication.py
from rest_framework import serializers
from django.contrib.auth import authenticate
from gitinterface.models import User


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            'first_name',
            'last_name',
            'email',
            'password',
            'password2',
        ]

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError("Passwords do not match")
        return data

    def validate_email(self, email):
        email = email.lower()
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError("Email already registered")
        return email

    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')
        email = validated_data.pop('email')

        # Auto-generate username from email if not provided,
        # since User model requires it
        username = email.split('@')[0]
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        user = User.objects.create_user(
            email=email,
            username=username,
            password=password,
            **validated_data
        )
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate_email(self, email):
        return email.lower()

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')

        user = authenticate(
            request=self.context.get('request'),
            email=email,
            password=password
        )
        if not user:
            raise serializers.ValidationError("Invalid email or password")

        if not user.is_active:
            raise serializers.ValidationError("This account has been deactivated")

        data['user'] = user
        return data