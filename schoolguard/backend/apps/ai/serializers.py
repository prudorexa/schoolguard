from rest_framework import serializers


class AskAssistantInputSerializer(serializers.Serializer):
    question = serializers.CharField(min_length=3, max_length=1000)


class AskAssistantResponseSerializer(serializers.Serializer):
    answer = serializers.CharField()
    tool_called = serializers.CharField()
    data = serializers.JSONField()
