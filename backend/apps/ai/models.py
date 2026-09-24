"""
ai/models.py

Every AI-assistant answer produces one of these rows -- the blueprint's
`ai_analysis_records` entity. This is what makes an AI answer auditable:
given a row, you can see exactly which tool was called, with what
parameters, what data came back, and what Claude was told to summarize --
so a wrong-looking answer can be traced to either bad input data (a real
bug elsewhere) or a language-generation issue, not left as a mystery.
"""

from django.db import models


class AIAnalysisRecord(models.Model):
    school = models.ForeignKey("schools.School", on_delete=models.CASCADE, related_name="+")
    asked_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, related_name="ai_queries")

    question = models.TextField()
    tool_called = models.CharField(max_length=100, blank=True)
    tool_params = models.JSONField(null=True, blank=True)
    data_retrieved = models.JSONField(null=True, blank=True)
    answer = models.TextField(blank=True)
    error = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.question[:60]} -> {self.tool_called or 'no tool'}"
