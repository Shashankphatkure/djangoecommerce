from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView
from django.contrib import messages
from .models import Product, Cart, CartItem, Order, OrderItem, Category
from decimal import Decimal

def get_base_context():
    context = {
        'categories': Category.objects.all()
    }
    
    # Add cart count if user is authenticated
    if hasattr(get_base_context, 'request') and get_base_context.request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=get_base_context.request.user)
            context['cart_count'] = sum(item.quantity for item in cart.cartitem_set.all())
        except Cart.DoesNotExist:
            context['cart_count'] = 0
            
    return context

def shop(request):
    category_id = request.GET.get('category')
    search_query = request.GET.get('search')
    
    products = Product.objects.filter(available=True)
    
    if category_id:
        products = products.filter(category_id=category_id)
    
    if search_query:
        products = products.filter(name__icontains=search_query)
    
    context = get_base_context()
    context.update({
        'products': products,
        'current_category': category_id,
        'search_query': search_query
    })
    
    return render(request, 'store/shop.html', context)

def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    # Get related products from the same category, excluding the current product
    # and prioritizing in-stock items
    related_products = Product.objects.filter(
        category=product.category,
        available=True
    ).exclude(
        id=product.id
    ).order_by(
        '-stock',  # Show in-stock items first
        '-id'      # Then show newer products
    )[:4]         # Limit to 4 related products
    
    context = {
        'product': product,
        'related_products': related_products,
    }
    return render(request, 'store/product_detail.html', context)

@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    
    if not created:
        cart_item.quantity += 1
        cart_item.save()
    
    return redirect('cart')

@login_required
def update_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    action = request.POST.get('action')
    
    if action == 'increment':
        cart_item.quantity += 1
    elif action == 'decrement':
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
        else:
            cart_item.delete()
            return redirect('cart')
    elif action == 'remove':
        cart_item.delete()
        return redirect('cart')
    
    cart_item.save()
    return redirect('cart')

@login_required
def cart(request):
    try:
        cart = Cart.objects.get(user=request.user)
        cart_items = CartItem.objects.filter(cart=cart)
        total = sum(item.total_price for item in cart_items)
        cart_count = sum(item.quantity for item in cart_items)
        remaining_amount = 50 - total if total < 50 else 0
    except Cart.DoesNotExist:
        cart_items = []
        total = 0
        cart_count = 0
        remaining_amount = 50
    
    return render(request, 'store/cart.html', {
        'cart_items': cart_items,
        'total': total,
        'cart_count': cart_count,
        'remaining_amount': remaining_amount
    })

@login_required
def order_confirmation(request):
    # Get the latest order for the user
    order = Order.objects.filter(user=request.user).latest('created')
    return render(request, 'store/order_confirmation.html', {'order': order})

@login_required
def checkout(request):
    try:
        cart = Cart.objects.get(user=request.user)
        cart_items = CartItem.objects.filter(cart=cart)
        
        if not cart_items.exists():
            messages.error(request, 'Your cart is empty')
            return redirect('cart')
            
        total = sum(item.total_price for item in cart_items)
        
    except Cart.DoesNotExist:
        messages.error(request, 'Your cart is empty')
        return redirect('cart')

    if request.method == 'POST':
        # Validate required fields
        required_fields = [
            'first_name', 'last_name', 'email', 'phone',
            'address', 'city', 'state', 'zip',
            'cc_name', 'cc_number', 'cc_expiration', 'cc_cvv'
        ]
        
        if all(request.POST.get(field) for field in required_fields):
            try:
                # Create the order
                order = Order.objects.create(
                    user=request.user,
                    first_name=request.POST['first_name'],
                    last_name=request.POST['last_name'],
                    email=request.POST['email'],
                    phone=request.POST['phone'],
                    address=request.POST['address'],
                    city=request.POST['city'],
                    state=request.POST['state'],
                    zip_code=request.POST['zip'],
                    total_amount=total
                )
                
                # Create order items
                for cart_item in cart_items:
                    OrderItem.objects.create(
                        order=order,
                        product=cart_item.product,
                        quantity=cart_item.quantity,
                        price=cart_item.product.price
                    )
                    
                    # Update product stock
                    product = cart_item.product
                    product.stock -= cart_item.quantity
                    product.save()
                
                # Clear the cart
                cart_items.delete()
                
                return redirect('order_confirmation')
            
            except Exception as e:
                messages.error(request, f'An error occurred: {e}')
                return redirect('checkout')
    
    return render(request, 'store/checkout.html', {
        'cart_items': cart_items,
        'total': total
    })

class RegisterView(CreateView):
    form_class = UserCreationForm
    template_name = 'registration/register.html'
    success_url = reverse_lazy('login')
    