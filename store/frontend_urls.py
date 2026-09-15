from django.urls import path
from store import views

urlpatterns = [
    path("", views.products_page, name="products_page"),
    path("cart/", views.cart_page, name="cart_page"),
    path("product/<int:id>/", views.product_detail_page, name="product_detail"),
    path("checkout/", views.checkout_page, name="checkout"),

    # PAYMENT ROUTES
    path("payment/start/<int:order_id>/", views.start_payment),
    path("payment/return/", views.payment_return),
    path("payment/result/", views.payment_result),
    
    path(
        "login/",
        views.login_page,
        name="login"
    ),

    path(
        "register/",
        views.register_page,
        name="register"
    ),
]