from rest_framework.routers import DefaultRouter

from .views import AcademicYearViewSet, ClassViewSet, DepartmentViewSet, TermViewSet

router = DefaultRouter()
router.register("departments", DepartmentViewSet, basename="department")
router.register("academic-years", AcademicYearViewSet, basename="academic-year")
router.register("terms", TermViewSet, basename="term")
router.register("classes", ClassViewSet, basename="class")

urlpatterns = router.urls
