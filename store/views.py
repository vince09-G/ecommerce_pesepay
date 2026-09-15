from urllib import response

from django.shortcuts import render, redirect
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter,OrderingFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.viewsets import ModelViewSet, GenericViewSet
from rest_framework.mixins import CreateModelMixin,RetrieveModelMixin,DestroyModelMixin, UpdateModelMixin
from .models import Product,ProductImage, Collection, Review, Cart,CartItem, Customer, Order, Orderitem, Payment
from .serializer import ProductSerializer,CollectionSerializer, ReviewSerializer, CartSerializer,CartItemSerializer,AddCartItemSerializer,CartItemQuantitySerializer,CustomerSerializer,OrderSerializer,CreateOrderSerializer, OrderItemSerializer,UpdateOrderSerializer, ProductImageSerializer
from .filters import ProductFilter
from .permissions import IsAdminOrReadOnly
from django.conf import settings
from django.http import HttpResponse
# Create your views here.
class ProductViewset(ModelViewSet):
    queryset= Product.objects.prefetch_related('images').all()
    serializer_class= ProductSerializer 
    permission_classes=[IsAdminOrReadOnly]
    filter_backends=[DjangoFilterBackend,SearchFilter,OrderingFilter]
    filterset_class=ProductFilter
    search_fields=['title','description']
    ordering_fields=['price', 'last_update']
    pagination_class= PageNumberPagination

class ProductImageViewset(ModelViewSet):
    
    serializer_class= ProductImageSerializer
    def get_serializer_context(self):
        return {'product_id': self.kwargs['product_pk']}
    def get_queryset(self):
        return ProductImage.objects.filter(product_id=self.kwargs['product_pk'])
   

class CollectionViewset(ModelViewSet):
    queryset= Collection.objects.all()
    serializer_class= CollectionSerializer 
    permission_classes=[IsAdminOrReadOnly]

class CartViewset(CreateModelMixin,RetrieveModelMixin,DestroyModelMixin, GenericViewSet, ):
    queryset= Cart.objects.prefetch_related('items__product').all()
    serializer_class= CartSerializer  


class CartItemViewset(ModelViewSet):
    http_method_names=['get','post','patch','delete']
 
    def get_serializer_class(self):
        if self.request.method== 'POST':
            return AddCartItemSerializer
        elif self.request.method=='PATCH':
            return CartItemQuantitySerializer
        return CartItemSerializer

    def get_queryset(self):
        return CartItem.objects.filter(cart=self.kwargs['cart_pk']).select_related('product')
    
    def get_serializer_context(self):
        return {'cart_id': self.kwargs['cart_pk']}  
    
class OrderViewset(ModelViewSet):
    # queryset= Order.objects.prefetch_related('items__product').all()
    #serializer_class= OrderSerializer
    def get_permissions(self):
        http_method_names= ['get','post','patch','delete','head','options']
        if self.request.method in ['PATCH','DELETE']:
            return  [IsAdminUser()]
        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        serializer= CreateOrderSerializer(data=request.data, context= {'user_id': self.request.user.id})
        serializer.is_valid(raise_exception=True)
        order= serializer.save()
        serializer= OrderSerializer(order)
        return Response(serializer.data)
    def get_serializer_class(self):
        if self.request.method== 'POST':
            return CreateOrderSerializer
        elif self.request.method== 'PATCH':
            return UpdateOrderSerializer
        return OrderSerializer

    def get_queryset(self):
        user= self.request.user
        if user.is_staff:
            return Order.objects.all()
        customer_id = Customer.objects.only('id').get(user_id=user.id)
        return Order.objects.filter(customer_id=customer_id)
    #permission_classes=[IsAdminUser]

    # @action(detail=False, methods=['GET', 'POST'], permission_classes=[IsAuthenticated])
    # def me(self, request):
    #     print(request.user)
    #     customer, created= Customer.objects.get_or_create(user_id=request.user.id)

    #     if request.method == 'GET':
    #         if request.user.id == None:
    #             return Response('Not logged in')
    #         orders= Order.objects.filter(customer=customer)
    #         serializer = OrderSerializer(orders, many=True)
    #         return Response(serializer.data)
           
    #     elif request.method == 'POST':
    #         serializer = OrderSerializer(data=request.data)
    #         serializer.is_valid(raise_exception='True')
    #         serializer.save(customer=customer)
    #         return Response(serializer.data)

class ReviewViewset(ModelViewSet):
    serializer_class= ReviewSerializer 

    def get_queryset(self):
        return Review.objects.filter(product=self.kwargs['product_pk'])
    
    def get_serializer_context(self):
        return {'product_id': self.kwargs['product_pk']}

class CustomerViewset(ModelViewSet):
    queryset= Customer.objects.all()
    serializer_class= CustomerSerializer
    permission_classes=[IsAdminUser]
    @action(detail=False, methods=['GET', 'PUT'], permission_classes=[IsAuthenticated])
    def me(self, request):
        print(request.user)
        customer= Customer.objects.get(user_id=request.user.id)

        if request.method == 'GET':
            if request.user.id == None:
                return Response('Not logged in')
            serializer = CustomerSerializer(customer)
            return Response(serializer.data)
           
        elif request.method == 'PUT':
            serializer = CustomerSerializer(customer, data=request.data)
            serializer.is_valid(raise_exception='True')
            serializer.save()
            return Response(serializer.data)


def products_page(request):
    return render(request, "products.html")

def cart_page(request):
    return render(request, "cart.html")

def product_detail_page(request, id): 
    return render(request, "product_detail.html", {"product_id": id})


def login_page(request):
    return render(request, "registration/login.html")


def register_page(request):
    return render(request, "registration/register.html")

from django.contrib.auth.decorators import login_required


def checkout_page(request):
    return render(request, "checkout.html")


import json
import base64
import requests

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

from django.shortcuts import redirect
from django.http import HttpResponse
from django.conf import settings

from .models import Order, Payment


# ---------------- ENCRYPT ---------------- #

def encrypt_payload(data, encryption_key):

    json_data = json.dumps(data)

    key = encryption_key.encode("utf-8")

    iv = encryption_key[:16].encode("utf-8")

    cipher = AES.new(key, AES.MODE_CBC, iv)

    encrypted_data = cipher.encrypt(
        pad(json_data.encode("utf-8"), AES.block_size)
    )

    return base64.b64encode(encrypted_data).decode("utf-8")


# ---------------- DECRYPT ---------------- #

def decrypt_payload(encrypted_payload, encryption_key):

    key = encryption_key.encode("utf-8")

    iv = encryption_key[:16].encode("utf-8")

    encrypted_bytes = base64.b64decode(encrypted_payload)

    cipher = AES.new(key, AES.MODE_CBC, iv)

    decrypted_data = unpad(
        cipher.decrypt(encrypted_bytes),
        AES.block_size
    )

    return json.loads(decrypted_data.decode("utf-8"))


# ---------------- PAYMENT ---------------- #

def start_payment(request, order_id):

    try:

        order = Order.objects.get(id=order_id)

        total = 0

        for item in order.items.all():
            total += item.quantity * item.unit_price

        # NORMAL JSON BODY (BEFORE ENCRYPTION)

        payment_body = {
            "amountDetails": {
                "amount": float(total),
                "currencyCode": "USD"
            },
            "merchantReference": str(order.id),
            "reasonForPayment": f"Order {order.id}",
            "resultUrl": settings.PESEPAY_RESULT_URL,
            "returnUrl": f"{settings.PESEPAY_RETURN_URL}?order_id={order.id}"
        }

        # ENCRYPT

        encrypted_payload = encrypt_payload(
            payment_body,
            settings.PESEPAY_ENCRYPTION_KEY
        )

        # FINAL API PAYLOAD

        payload = {
            "payload": encrypted_payload
        }

        # SANDBOX URL

        url = (
            "https://api.test.sandbox.pesepay.com/"
            "payments-engine/v1/payments/initiate"
        )

        headers = {
            "authorization": settings.PESEPAY_INTEGRATION_KEY,
            "Content-Type": "application/json"
        }

        response = requests.post(
            url,
            json=payload,
            headers=headers
        )

        print("STATUS CODE:", response.status_code)
        print("RAW RESPONSE:", response.text)

        response_data = response.json()

        encrypted_response = response_data.get("payload")

        if not encrypted_response:

            return HttpResponse(
                f"Payment Failed: {response.text}"
            )

        # DECRYPT RESPONSE

        decrypted_response = decrypt_payload(
            encrypted_response,
            settings.PESEPAY_ENCRYPTION_KEY
        )

        print("DECRYPTED RESPONSE:", decrypted_response)

        redirect_url = decrypted_response.get("redirectUrl")

        if redirect_url:

            Payment.objects.create(
                order=order,
                amount=total,
                status="PENDING",
                reference=decrypted_response.get(
                    "referenceNumber"
                ),
                poll_url=decrypted_response.get(
                    "pollUrl"
                )
            )

            return redirect(redirect_url)

        return HttpResponse(
            f"Payment Failed: {decrypted_response}"
        )

    except Exception as e:

        print("ERROR:", str(e))

        return HttpResponse(
            f"An error occurred: {str(e)}"
        )
    
from django.views.decorators.csrf import csrf_exempt


def check_payment_status(reference):

    url = (
        "https://api.test.sandbox.pesepay.com/"
        "payments-engine/v1/payments/check-payment"
    )

    headers = {
        "authorization": settings.PESEPAY_INTEGRATION_KEY,
        "Content-Type": "application/json"
    }

    params = {
        "referenceNumber": reference
    }

    response = requests.get(
        url,
        headers=headers,
        params=params
    )

    print("STATUS CHECK:", response.text)

    data = response.json()

    encrypted_payload = data.get("payload")

    if not encrypted_payload:
        return None

    decrypted_response = decrypt_payload(
        encrypted_payload,
        settings.PESEPAY_ENCRYPTION_KEY
    )

    print("DECRYPTED STATUS:", decrypted_response)

    return decrypted_response

from django.http import HttpResponse

def payment_return(request):
    try:
        order_id = request.GET.get("order_id")

        if not order_id:
            return HttpResponse("Order ID was not provided.")

        order = Order.objects.get(id=order_id)

        payment = Payment.objects.get(order=order)

        transaction = check_payment_status(payment.reference)

        print("TRANSACTION:", transaction)

        if not transaction:
            return HttpResponse(
                "Unable to retrieve transaction status."
            )

        status = transaction.get("transactionStatus")

        print("PAYMENT STATUS:", status)

        if status in ["SUCCESS", "PAID", "COMPLETED"]:

            payment.status = Payment.STATUS_PAID
            payment.save()

            order.payment_status = Order.PAYMENT_STATUS_COMPLETE
            order.save()

            return render(
                request,
                "payment_result.html",
                {
                    "success": True,
                    "order": order,
                    "payment": payment,
                }
            )

        elif status in ["INITIATED", "PENDING"]:

            return render(
                request,
                "payment_result.html",
                {
                    "success": False,
                    "pending": True,
                    "order": order,
                    "payment": payment,
                }
            )

        else:

            payment.status = Payment.STATUS_FAILED
            payment.save()

            order.payment_status = Order.PAYMENT_STATUS_FAILED
            order.save()

            return render(
                request,
                "payment_result.html",
                {
                    "success": False,
                    "failed": True,
                    "order": order,
                    "payment": payment,
                    "status": status,
                }
            )

    except Order.DoesNotExist:
        return HttpResponse("Order not found.")

    except Payment.DoesNotExist:
        return HttpResponse("Payment record not found.")

    except Exception as e:
        print("ERROR:", str(e))
        return HttpResponse(f"Error: {str(e)}")
    
@csrf_exempt
def payment_result(request):

    reference = request.GET.get("referenceNumber")

    if not reference:
        return HttpResponse("OK")

    transaction = check_payment_status(reference)

    if not transaction:
        return HttpResponse("OK")

    transaction_status = transaction.get("transactionStatus")

    try:

        payment = Payment.objects.get(
            reference=reference
        )

        order = payment.order

        if transaction_status in [
            "SUCCESS",
            "PAID",
            "COMPLETED"
        ]:

            payment.status = Payment.STATUS_PAID
            payment.save()

            order.payment_status = Order.PAYMENT_STATUS_COMPLETE
            order.save()

        elif transaction_status in [
            "INITIATED",
            "PENDING"
        ]:

            payment.status = Payment.STATUS_PENDING
            payment.save()

        else:

            payment.status = Payment.STATUS_FAILED
            payment.save()

            order.payment_status = Order.PAYMENT_STATUS_FAILED
            order.save()

    except Payment.DoesNotExist:
        pass

    return HttpResponse("OK")
# class ProductList(ListCreateAPIView):
#     queryset= Product.objects.all()
#     serializer_class= ProductSerializer

# class ProductDetails(RetrieveUpdateDestroyAPIView):
#     queryset= Product.objects.all()
#     serializer_class= ProductSerializer
  

# class CollectionList(ListCreateAPIView):
#     queryset= Collection.objects.all()
#     serializer_class= CollectionSerializer

# class CollectionDetails(RetrieveUpdateDestroyAPIView):
#     queryset= Collection.objects.all()
#     serializer_class= CollectionSerializer

# @api_view(['GET', 'POST'])
# def product_list(request):
#     if request.method == 'GET':
#         products=Product.objects.select_related('collection').all()
#         serializer= ProductSerializer(products, many=True)
#         return Response(serializer.data)
#     elif request.method == 'POST':
#         serializer= ProductSerializer(data= request.data)
#         serializer.is_valid(raise_exception=True)
#         serializer.save()

#         return Response(serializer.data)

# @api_view(['GET', 'PUT'])
# def product_detail(request, id):
#     product= get_object_or_404(Product, pk=id)
#     if request.method == 'GET':
#         serializer= ProductSerializer(product)
#         return Response(serializer.data)
    
#     elif request.method == 'PUT':
#         serializer= ProductSerializer(product, data= request.data)
#         serializer.is_valid(raise_exception=True)
#         serializer.save()
#         return Response(serializer.data)
