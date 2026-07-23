from rest_framework import serializers
from .models import SkillTag, CompanyClient, DeveloperCandidate

class SkillTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = SkillTag
        fields = '__all__'

class CompanyClientSerializer(serializers.ModelSerializer):
    required_tech_name = serializers.CharField(source='required_tech.name', read_only=True)

    class Meta:
        model = CompanyClient
        fields = '__all__'

class DeveloperCandidateSerializer(serializers.ModelSerializer):
    skills = SkillTagSerializer(many=True, read_only=True)

    class Meta:
        model = DeveloperCandidate
        fields = '__all__'