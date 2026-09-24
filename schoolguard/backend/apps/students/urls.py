from rest_framework.routers import DefaultRouter

from .views import ParentViewSet, StudentParentViewSet, StudentViewSet

router = DefaultRouter()
router.register("students", StudentViewSet, basename="student")
router.register("parents", ParentViewSet, basename="parent")
router.register("student-parents", StudentParentViewSet, basename="student-parent")

urlpatterns = router.urls
