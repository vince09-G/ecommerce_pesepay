from .signals import order_created
from rest_framework import serializers
from django.db import transaction
from .models import Product,ProductImage, Collection, Review,Cart,CartItem,Customer,Order, Orderitem

class CollectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Collection
        fields = ['id', 'title']

class ProductImageSerializer(serializers.ModelSerializer):
    
    def create(self, validated_data):
        product_id= self.context['product_id']
        return ProductImage.objects.create(product_id=product_id, **validated_data)
    class Meta:
        model= ProductImage
        fields = ['id', 'image']

class ProductSerializer(serializers.ModelSerializer):
    images= ProductImageSerializer(many=True, read_only=True)
    class Meta:
        model = Product
        fields = ['id', 'title', 'slug', 'description', 'price','inventory', 'collection', 'images']

class SimpleProductSerializer(serializers.ModelSerializer):
    images= ProductImageSerializer(many=True, read_only=True)
    class Meta:
        model = Product
        fields = ['id', 'title','price', 'images']


class CustomerSerializer(serializers.ModelSerializer):
    user_id= serializers.IntegerField(read_only= True)
    class Meta:
        model= Customer
        fields=['id','user_id','phone', 'birth_date', 'membership']

class CartItemSerializer(serializers.ModelSerializer):
    product= SimpleProductSerializer()
    total_price= serializers.SerializerMethodField()
    
    def get_total_price(self, cart_item:CartItem):
        return cart_item.product.price* cart_item.quantity
    
    
    class Meta:
        model = CartItem
        fields = ['id','product', 'quantity','total_price']

class AddCartItemSerializer(serializers.ModelSerializer):
    product_id= serializers.IntegerField()

    def validate_product_id(self, value):
        if not Product.objects.filter(pk=value).exists():
            raise serializers.ValidationError('No product with given ID was found')
        
        return value

    def create(self, validated_data):
        cart_id = self.context['cart_id']  # from view
        product_id = validated_data['product_id']
        quantity = validated_data.get('quantity', 1)

        # check if product already in cart
        cart_item, created = CartItem.objects.get_or_create(
            cart_id=cart_id,
            product_id=product_id,
            defaults={'quantity': quantity}
        )

        if not created:
            # if it exists, increase quantity
            cart_item.quantity += quantity
            cart_item.save()

        return cart_item

    
    class Meta:
        model= CartItem
        fields=['id', 'product_id', 'quantity']

class CartItemQuantitySerializer(serializers.ModelSerializer):
    class Meta:
        model=CartItem
        fields=['quantity']

class CartSerializer(serializers.ModelSerializer):
    id=serializers.UUIDField(read_only=True)
    items= CartItemSerializer(many=True, read_only=True)
    total_price= serializers.SerializerMethodField()

    def get_total_price(self, cart:Cart):
        return sum([item.product.price* item.quantity for item in cart.items.all()])
    class Meta:
        model = Cart
        fields = ['id','items', 'total_price']

class OrderItemSerializer(serializers.ModelSerializer):
    product= SimpleProductSerializer()
    class Meta:
        model = Orderitem
        fields = ['id','product', 'quantity','unit_price']

class OrderSerializer(serializers.ModelSerializer):
    items= OrderItemSerializer(many=True, read_only=True)
    payment_status= serializers.CharField(read_only=True)
    customer= CustomerSerializer(read_only=True)
    class Meta:
        model = Order
        fields = ['id','placed_at', 'payment_status', 'items', 'customer']

class UpdateOrderSerializer(serializers.ModelSerializer):
   
    class Meta:
        model = Order
        fields = ['payment_status']

class CreateOrderSerializer(serializers.Serializer):
    cart_id = serializers.UUIDField()

    def validate_cart_id(self, cart_id):
        if not Cart.objects.filter(pk=cart_id).exists():
            raise serializers.ValidationError('No cart with the given ID was found.')
        if not CartItem.objects.filter(cart_id=cart_id).exists():
            raise serializers.ValidationError('The cart is empty.')
        return cart_id  
    def save(self, **kwargs):
        with transaction.atomic():
            cart_id=self.validated_data['cart_id']
            print(self.context['user_id'])

            customer= Customer.objects.get(user_id=self.context['user_id'])
            order=Order.objects.create(customer=customer)
            cart_items=CartItem.objects.select_related('product').filter(cart_id=cart_id)
            orderitems = [Orderitem(order=order,product=item.product,unit_price=item.product.price,quantity=item.quantity) 
            for item in cart_items]
            Orderitem.objects.bulk_create(orderitems)
            Cart.objects.filter(pk=cart_id).delete()
            order_created.send_robust(self.__class__, order=order)
            return order

class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ['id','name','description','date' ]
    
    def create(self, validated_data):
        product_id=self.context['product_id']
        return Review.objects.create(product_id= product_id, **validated_data)
        
