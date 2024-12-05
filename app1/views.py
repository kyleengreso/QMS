from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib import messages
from .models import userData, num_counters, Employee
import random
from django.contrib.auth.models import User, auth, Group

#----------------------------------------------------------FILL THE DETAILS BELOW--------------------------------------------------------------------

#email: input your email id and password as a string below
import smtplib
sender_email = "kenrogerdomingo@gmail.com"
password = "mpyw uhjy tedi iakc"

#uid is the token number, starts with 0, increments with 1 and so on...
uid = 0

#getting the admin info
u = User.objects.get(username='kyle')

#the employee model under application App1 has the data of admin, the counterNumber for admin means the total number of
#counters the admin want the employees to access. For others, it is zero by default and can be selected from selectCounter
#website by employee numbered between 1 and total_counters (admin's counter number)
#The admin can change the the total number of counters anytime but the system would have to restart for the changes to be applied
total_counters = u.employee.counterNumber

#counters is a dictionary which represents the counters and the number of people (queue size) of each available counter
#For eg, counters = {1:5, 2:4, 4:6} means 1st counter has 5 people, 2nd counter has 4 people and 4th counter has 6 people
#Empty by default, an employee would have to select a counter first for it to work
counters = {}

#naming convention w.r.t. employee (the counters available for the employees to choose)
#For eg, if the total_counters is 4, then the employees can choose counter from 1, 2, 3, 4
#No employee can select more than 1 counter
availableCounters = list(range(1, total_counters + 1))

#index (main) page
def index(request):
    return render(request, 'index.html')

#customer registration page
def register(request):
    # If no counters are available, customers cannot register
    if not counters:
        return HttpResponse('There is no counter available. Kindly, try again when an employee arrives at the counter')
    elif request.method == "POST":
        name = request.POST['name']
        email = request.POST['email']
        phoneNumber = request.POST['phoneNumber']

        # Validate email
        from django.core.validators import validate_email
        try:
            validate_email(email)
        except:
            messages.info(request, 'Enter a valid email address')
            return redirect('register')

        # Check for empty name
        if name == '':
            messages.info(request, 'Enter a name')
            return redirect('register')

        # Validate phone number (numeric and 10 digits long)
        elif not phoneNumber.isnumeric() or len(phoneNumber) != 10:
            messages.info(request, 'Enter a valid 10-digit phone number')
            return redirect('register')

        # Check for duplicate phone number
        phoneNumber = '+63' + phoneNumber  # Using '+63' as default country code
        if userData.objects.filter(phoneNumber=phoneNumber).exists():
            messages.info(request, 'This Phone Number is already registered')
            return redirect('register')

        # Generate OTP and send it
        otpNum = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        try:
            data = userData(name=name, email=email, phoneNumber=phoneNumber, otp=otpNum)
            data.save()

            # Send OTP via email
            rec_email = email
            message = f"Dear {name}, OTP to book your position in queue is {otpNum}. Do not share it with anyone."
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(sender_email, password)
            server.sendmail(sender_email, rec_email, message)

            return redirect('otp', phoneNumber)
        except Exception as e:
            messages.info(request, f"Error occurred: {e}")
            return redirect('register')
    else:
        return render(request, 'register.html')


#otp verification page
def otp(request, phoneNumber):
    d = userData.objects.get(phoneNumber = phoneNumber)
    if request.method == 'POST':
        input_otp = request.POST['input_otp']
        if input_otp == d.otp:
            #Assigning counter with smallest queue
            global counters
            global uid

            #incrementing token number
            uid += 1
            #smallest queue
            temp = min(counters.values())      
            #counter(s) of that queue (more than one queue have same number of people)                         
            res = [key for key in counters if counters[key] == temp]  
            #assigning one of the counters with smallest queue  
            d.counter = res[0]   
            #position of customer                                       
            d.pos = temp + 1
            #token number of customer
            d.token = uid
            #saving data
            d.save()
            #adding one customer to the counters dictionary
            counters[res[0]] += 1                                       

            #E-MAIL
            rec_email = d.email
            message = "Dear {}, your Token number is {}.".format(d.name, uid)
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(sender_email, password)
            server.sendmail(sender_email, rec_email, message)

            return redirect('queue details')
        else:
            messages.info(request, 'Invalid OTP')
            return redirect('otp', phoneNumber)
    else:
        return render(request, 'otp.html', {'phoneNumber' : phoneNumber})

#customer can check their counter number and position in queue using token number here
#Since the queue is dynamic, the counter number might change.
def view_queue(request):
    if request.method == "GET" and request.GET.get('token'):  # Check if token is provided
        token = request.GET['token']  # Retrieve token from request

        # **Enhancement: Validate token format**
        if not token.isdigit():  # Example: Ensure token is numeric
            messages.error(request, 'Token must be a valid number.')
            return redirect('queue details')

        try:
            # Retrieve user details based on token
            user = userData.objects.get(token=token)
            counter_num = user.counter  # Counter assigned to the user
            pos = user.pos  # Position in the queue

            # Get the total number of people in the queue for the assigned counter
            queue_size = counters.get(counter_num, 0)  # Default to 0 if counter number doesn't exist

            # Get the list of customers in the queue at the assigned counter
            queue = userData.objects.filter(counter=counter_num).order_by('pos')  # List customers sorted by position

            # Display the position and queue size
            return render(request, 'view_queue.html', {
                'counter_num': counter_num, 
                'pos': pos,
                'queue_size': queue_size,  # Show the current queue size
                'queue': queue  # Pass the current queue of customers at the counter
            })
        except userData.DoesNotExist:
            # Handle invalid token
            messages.error(request, 'Invalid token number. Please try again.')
            return redirect('queue details')
    else:
        # Render an empty form
        return render(request, 'view_queue.html', {
            'counter_num': None, 
            'pos': None,
            'queue_size': None,  # Default to None if no token provided
            'queue': []  # No queue if no token is provided
        })


#employee login
def login(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']

        user = auth.authenticate(username = username, password = password) 
        if user is not None:
            auth.login(request, user)
            return redirect('selectCounter')
        else:
            messages.info(request, 'Invalid credentials')
            return redirect('login')
    else:
        return render(request, 'login.html')

#employee logout
def logout(request):
    global counters
    user = request.user
    old_counter = user.employee.counterNumber
    if old_counter in counters:
        counters.pop(old_counter)
        availableCounters.append(old_counter)

    #if the queue is empty before logging out, it would cause an error because of the following query. That's why I used try-except here.
    try:
        current = userData.objects.get(counter = old_counter, pos = 0)
        current.delete()
    except:
        pass

    user.employee.counterNumber = 0
    user.employee.save()

    #In case the employee had customers at the counter before log out.
   
    #If every employee logs out, all the user(customer) data will be deleted.
    if counters == {}:
        userData.objects.all().delete()
    
    #Reassigning new counter (smallest queue) to customers who were assigned the old_counter (the counter which employee had before logging out).
    else:
        new = userData.objects.filter(counter = old_counter)
        for customer in new:
            temp = min(counters.values())                               #smallest queue
            res = [key for key in counters if counters[key] == temp]    #counter(s) of that queue
            customer.counter = res[0]
            customer.pos = temp + 1
            customer.save()
            counters[res[0]] += 1

    auth.logout(request)
    return redirect('login')

#Employee controls page
def employee(request):  #admin cannot access this website
    if request.user.is_authenticated and request.user.username != 'admin':
        global counters
        n = request.user.employee.counterNumber
        if n <= 0:
            return redirect('selectCounter')
        elif 'next' in request.POST:

            #Dynamic queue: whenever the 'next customer' button is clicked by an employee, the queues are rearranged accordingly
            #Consider there are 2 counters, one counter attended people faster than the other. Hence, 1st counter has 2 people and 2nd counter has 6 people in it.
            #So, we can transfer 2 people from 2nd counter to 1st counter to balance it out. But the question is which 2 out of those 6 people.
            #If we take the last 2, it would be easier to implement but unfair to the ones who came before them. So, the algorithm will work in the following way:
            #The 4th and 5th person of 2nd queue will be assigned 3rd and 4th position of 1st counter and the 6th person of counter 2 will naturally get the 4th position of counter 2.
            while max(counters.values()) > min(counters.values()) + 1:
                smallest_queue = min(counters.values())                                 #smallest queue
                largest_queue = max(counters.values())                                  #largest queue
                small = [key for key in counters if counters[key] == smallest_queue]    #counter(s) of smallest queue
                large = [key for key in counters if counters[key] == largest_queue]     #counter(s) of largest queue
                small_counter = small[0]                                                #counter of smallest queue
                large_counter = large[0]                                                #counter of largest queue
                customer = userData.objects.get(counter = large_counter, pos = smallest_queue + 2)
                customer.counter = small_counter
                customer.pos = smallest_queue + 1
                customer.save()
                counters[large_counter] -= 1
                counters[small_counter] += 1

                #if the person removed from large_counter was at last position
                try:    
                    data = userData.objects.filter(counter = large_counter, pos__gt = smallest_queue + 2)   #__gt means greater than
                    for i in data:
                        i.pos -= 1
                        i.save()
                except:
                    pass
            
            #next customer button is clicked, so decreasing the number of people in that queue by 1
            if counters[n] > 0:
                counters[n] -= 1

            #Decrement the positions of customers by 1, and delete their data if the position is -1.
            data = userData.objects.filter(counter = n)
            for i in data:
                i.pos -= 1
                i.save()
                if i.pos < 0:
                    i.delete()

        #calling the customer to counter when its their turn
        try:
            d = userData.objects.get(pos = 0, counter = n)

            #E-MAIL
            rec_email = d.email
            message = "Dear {}, it's your turn now. Kindly, arrive at counter number {}.".format(d.name, d.counter)
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(sender_email, password)
            server.sendmail(sender_email, rec_email, message)

            return render(request, 'employee.html', {'name': d.name, 'token': d.token, 'counter': n})
        except:
            messages.info(request, 'The queue is empty. Press "next customer" button when a customer arrives.')
            return render(request, 'employee.html', {'name': '', 'token': '', 'counter': n})
    else:
        return redirect('login')

availableCounters = []
counters = {}

def initialize_counters():
    """Initialize counters from the database."""
    global availableCounters, counters
    try:
        total_counters = num_counters.objects.first()
        if total_counters:
            # Create a list of available counters
            availableCounters = list(range(1, total_counters.num_counters + 1))
            counters = {counter: 0 for counter in availableCounters}  # All counters initially empty
        else:
            availableCounters = []
            counters = {}
    except Exception as e:
        print(f"Error initializing counters: {e}")
#Employee select counter page
def selectCounter(request):
    if request.user.is_authenticated and request.user.username != 'admin':
        global counters, availableCounters

        # Ensure counters are initialized
        if not availableCounters:
            initialize_counters()

        if request.method == 'POST':
            new_counter = int(request.POST['counter'])

            # Check if selected counter is still available
            if new_counter not in availableCounters:
                messages.error(request, "The selected counter is no longer available.")
                return render(request, 'selectCounter.html', {'availableCounters': availableCounters})

            # Update counters and user's assigned counter
            old_counter = request.user.employee.counterNumber
            if old_counter in counters:
                counters.pop(old_counter)  # Remove the old counter
                availableCounters.append(old_counter)

                # Reassign customers from old counter to other counters
                reassign_customers_from_counter(old_counter)

            availableCounters.remove(new_counter)
            counters[new_counter] = counters.get(new_counter, 0)  # Initialize counter if not present

            # Assign the new counter to the user
            request.user.employee.counterNumber = new_counter
            request.user.employee.save()
            availableCounters.sort()

            messages.success(request, f"Counter {new_counter} successfully selected.")
            return redirect('employee')

        return render(request, 'selectCounter.html', {'availableCounters': availableCounters})
    else:
        return redirect('login')



def reassign_customers_from_counter(old_counter):
    global counters
    try:
        # Reassign customers from the old counter to the smallest available queue
        customers = userData.objects.filter(counter=old_counter).order_by('pos')
        for customer in customers:
            smallest_queue_size = min(counters.values())
            smallest_queue_counter = next(key for key in counters if counters[key] == smallest_queue_size)
            customer.counter = smallest_queue_counter
            customer.pos = smallest_queue_size + 1
            customer.save()
            counters[smallest_queue_counter] += 1
    except Exception as e:
        print(f"Error while reassigning customers: {e}")
