from django.urls import path
from . import views
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers
from pprint import pprint


router= routers.DefaultRouter()
router.register('products', views.ProductViewset, basename='products')
router.register('carts', views.CartViewset)
router.register('collections', views.CollectionViewset)
router.register('customers', views.CustomerViewset)
router.register('orders', views.OrderViewset, basename='orders')
products_router=routers.NestedDefaultRouter(router, 'products', lookup= 'product')
products_router.register('reviews', views.ReviewViewset, basename='product-reviews')
products_router.register('images', views.ProductImageViewset, basename='product-images')
carts_router=routers.NestedDefaultRouter(router, 'carts', lookup= 'cart')
carts_router.register('cart-items', views.CartItemViewset, basename='cart-items')

urlpatterns = router.urls + products_router.urls + carts_router.urls