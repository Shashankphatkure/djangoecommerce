from django.urls import path
from . import views
from .views import RegisterView

urlpatterns = [
    path('', views.shop, name='shop'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('cart/', views.cart, name='cart'),
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('order-confirmation/', views.order_confirmation, name='order_confirmation'),
    path('update-cart/<int:item_id>/', views.update_cart, name='update_cart'),
    path('accounts/register/', RegisterView.as_view(), name='register'),
] 