from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from urllib import request
from django.views import View
from .models import Product, Customer, Cart, OrderPlaced
from django.db.models import Count
from .forms import CustomerRegistrationForm, CustomerProfileForm
from django.contrib import messages
from django.db import transaction
from django.contrib.auth.decorators import login_required 

# Create your views here.
def home(request):
    return render(request, "app/home.html")

def about(request):
    return render(request, "app/about.html")

def contact(request):
    return render(request, "app/contact.html")

class CategoryView(View):
    def get(self,request,val):
        product = Product.objects.filter(category=val)
        title = Product.objects.filter(category=val).values('title')
        return render(request, "app/category.html", locals())

class ProductDetail(View):
    def get(self, request, pk):
        product = Product.objects.get(pk=pk)
        return render(request, "app/productdetail.html", locals())

class CategoryTitle(View):
    def get(self, request, val):
        product = Product.objects.filter(title=val)
        title = Product.objects.filter(category=product[0].category).values('title')
        return render(request, "app/category.html", locals())

class CustomerRegistrationView(View):
    def get(self, request):
        form = CustomerRegistrationForm()
        return render(request, 'app/customerregistration.html', locals())

    def post(self, request):
        form = CustomerRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Congratulations! User Registered Successfully")
        else:
            messages.warning(request, "Invalid Input Data")
        return render(request, 'app/customerregistration.html', locals())

class ProfileView(View):
    def get(self, request):
        form = CustomerProfileForm()
        return render(request, 'app/profile.html', locals())

    def post(self, request):
        if request.user.is_authenticated:
            form = CustomerProfileForm(request.POST)
            if form.is_valid():
                user = request.user
                name = form.cleaned_data['name']
                locality = form.cleaned_data['locality']
                city = form.cleaned_data['city']
                mobile = form.cleaned_data['mobile']
                state = form.cleaned_data['state']
                zipcode = form.cleaned_data['zipcode']
                reg = Customer(user=user, name=name, locality=locality, mobile=mobile, city=city, state=state, zipcode=zipcode)
                reg.save()
                messages.success(request, "Tebrikler! Profil başarıyla kaydedildi.")
            else:
                messages.warning(request, "Geçersiz giriş verisi.")
        else:
            messages.warning(request, "Profilinizi kaydetmek için giriş yapmalısınız.")
            return redirect('login')  

        return render(request, 'app/profile.html', locals())

def address(request):
    add = Customer.objects.filter(user=request.user)
    return render(request, 'app/address.html', locals())

class updateAddress(View):
    def get(self,request,pk):
        add = Customer.objects.get(pk=pk)
        form = CustomerProfileForm(instance=add)
        return render(request, 'app/updateAddress.html', locals())
    def post(self,request,pk):
        form= CustomerProfileForm(request.POST)
        if form.is_valid():
            add = Customer.objects.get(pk=pk)
            add.name = form.cleaned_data['name']
            add.locality = form.cleaned_data['locality']
            add.city = form.cleaned_data['city']
            add.mobile = form.cleaned_data['mobile']
            add.state = form.cleaned_data['state']
            add.zipcode = form.cleaned_data['zipcode']
            add.save()
            messages.success(request, "Congratulations! Profile Update Successfully")
        else: 
            messages.warning(request, "Invalid Input Data")
        return redirect("address")

def add_to_cart(request):
    user = request.user
    product_id = request.GET.get('prod_id')

    try:
        product_instance = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return redirect('product_not_found')

    
    cart_item, created = Cart.objects.get_or_create(user=user, product=product_instance)

    if not created:
        cart_item.quantity += 1
        cart_item.save()

    return redirect("/cart")

def show_cart(request):
    
    cart = Cart.objects.filter(user=request.user)
    cart_items = {}
    total_amount = 0

    for item in cart:
        product_id = item.product.id
        if product_id in cart_items:
            cart_items[product_id]['quantity'] += item.quantity
            cart_items[product_id]['total_price'] += item.quantity * item.product.discounted_price
        else:
            cart_items[product_id] = {
                'item': item,
                'quantity': item.quantity,
                'total_price': item.quantity * item.product.discounted_price
            }
        total_amount += item.quantity * item.product.discounted_price

    shipping_cost = 40
    total_with_shipping = total_amount + shipping_cost

    
    context = {
        'cart_items': cart_items.values(),
        'total_amount': total_amount,
        'total_with_shipping': total_with_shipping,
        'shipping_cost': shipping_cost,
    }
    return render(request, 'app/addtocart.html', context)

class CheckoutView(View):
    def get(self, request, *args, **kwargs):
        addresses = Customer.objects.filter(user=request.user)
        cart_items = Cart.objects.filter(user=request.user)
        
        
        total_amount = 0
        for item in cart_items:
            total_amount += item.quantity * item.product.discounted_price
        
        shipping_cost = 40
        total_with_shipping = total_amount + shipping_cost

        
        context = {
            'addresses': addresses,
            'cart_items': cart_items,
            'totalamount': total_with_shipping,
        }
        return render(request, 'app/checkout.html', context)

    def post(self, request, *args, **kwargs):
        
        address_id = request.POST.get('custid')

        if not address_id:
            messages.error(request, "Please enter an address.")
            return redirect('checkout')

        try:
            address = Customer.objects.get(id=address_id)
        except Customer.DoesNotExist:
            messages.error(request, "Unvalid Address.")
            return redirect('checkout')

        cart_items = Cart.objects.filter(user=request.user)

        if not cart_items.exists():
            messages.error(request, "There is not any product in your box.")
            return redirect('cart')

        try:
            
            with transaction.atomic():
                for item in cart_items:
                    OrderPlaced.objects.create(
                        user=request.user,
                        product=item.product,
                        quantity=item.quantity,
                        price=item.product.discounted_price * item.quantity,
                        address=address,
                    )
                
                cart_items.delete()
                messages.success(request, "Your order has been successfully created..")
                return redirect('home')

        except Exception as e:
            messages.error(request, f"An error occurred while processing your order: {str(e)}")
            return redirect('checkout')

def update_cart_quantity(request):
    if request.method == "POST":
        cart_id = request.POST.get('cart_id')
        action = request.POST.get('action')
        
        try:
            cart_item = Cart.objects.get(id=cart_id)
            if action == 'increase':
                cart_item.quantity += 1
            elif action == 'decrease' and cart_item.quantity > 1:
                cart_item.quantity -= 1
            cart_item.save()
        except Cart.DoesNotExist:
            pass  
    
    return redirect('showcart')


def remove_from_cart(request, cart_id):
    try:
        cart_item = Cart.objects.get(id=cart_id, user=request.user)
        cart_item.delete()
        return redirect('showcart')
    except Cart.DoesNotExist:
        return redirect('showcart')


class PlaceOrderView(View):
    def get(self, request, *args, **kwargs):
        return render(request, 'app/placeorder.html')

    def post(self, request, *args, **kwargs):
        card_name = request.POST.get('card_name')
        card_number = request.POST.get('card_number')
        expiry_date = request.POST.get('expiry_date')
        cvv = request.POST.get('cvv')
        billing_address = request.POST.get('billing_address')
        
        
        messages.success(request, "Your payment was successful!")
        return redirect('home')

        messages.error(request, "There was an error with your payment. Please try again.")
        return redirect('placeorder')

