from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView
from .models import Product, Cart, CartItem, Order, OrderItem, Category
from decimal import Decimal

def shop(request):
    category_id = request.GET.get('category')
    search_query = request.GET.get('search')
    
    products = Product.objects.filter(available=True)
    
    if category_id:
        products = products.filter(category_id=category_id)
    
    if search_query:
        products = products.filter(name__icontains=search_query)
    
    categories = Category.objects.all()
    
    return render(request, 'store/shop.html', {
        'products': products,
        'categories': categories,
        'current_category': category_id,
        'search_query': search_query
    })

def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    # Get related products from the same category, excluding the current product
    related_products = Product.objects.filter(
        category=product.category
    ).exclude(
        id=product.id
    )[:4]  # Limit to 4 related products
    
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
        total = sum(item.total_price for item in cart_items)
    except Cart.DoesNotExist:
        return redirect('cart')

    if request.method == 'POST':
        # Process the order
        order = Order.objects.create(
            user=request.user,
            address=request.POST['address'],
            phone=request.POST['phone'],
            total_amount=total
        )
        
        for cart_item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                quantity=cart_item.quantity,
                price=cart_item.product.price
            )
        
        cart_items.delete()
        return redirect('order_confirmation')
    
    return render(request, 'store/checkout.html', {
        'cart_items': cart_items,
        'total': total
    })

class RegisterView(CreateView):
    form_class = UserCreationForm
    template_name = 'registration/register.html'
    success_url = reverse_lazy('login')
    