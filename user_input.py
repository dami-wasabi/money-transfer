"""f_name = input("Enter your name: ")
age = input("Enter your age: ")
print(f"your name is {f_name} and your age is: {age}")"""

#Note: anything from input is considered a string 
# write a program that takes 2 numbers from user and displays the sum of both numbers
"""age = input("what is your age: ")
child_count = input("How many children do you have: ")
sum_total= int(age) + int(child_count)
print(f"Your total is {sum_total}")
 
 or 


num1 = (input("Enter your first number: ")
num2 = input("Enter your second number: ")
sum = int(num1) + int (num2)

or


num1 = int(input("Enter your first number: "))
num2 = int(input("Enter your second number: "))
sum = num1 + num2
print(sum)
"""

# write a code to help your client with money transfer
# it should ask for user total amount to send in USD
# then it should tell how muich the receiver will get in cameroon ==> CFA
# sending fees should be 0.02 added to the total amount 
# exchange rate should be 655
sending_fees = 0.02
exchange_rate = 655
user_amount = int(input("Enter the amount: "))
fee_amount = sending_fees * user_amount
amount_plus_fee = user_amount + fee_amount
receiving_amount = exchange_rate * user_amount 
print(f"The total amount plus sending fees is: ${amount_plus_fee:,} and your family will receive {receiving_amount:,} CFA")
user_answer = input("Do you want to proceed (yes/no) ? ")
if user_answer == 'yes':
    print("Proceed with the payment")
else: 
    print("Thank you for stopping by")
