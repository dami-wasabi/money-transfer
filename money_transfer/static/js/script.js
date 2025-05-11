document.addEventListener('DOMContentLoaded', function() {
    const amountInput = document.getElementById('amount');
    const calculateBtn = document.getElementById('calculate-btn');
    const resultsDiv = document.getElementById('results');
    const proceedBtn = document.getElementById('proceed-btn');
    const cancelBtn = document.getElementById('cancel-btn');
    
    calculateBtn.addEventListener('click', calculateTransfer);
    proceedBtn.addEventListener('click', proceedPayment);
    cancelBtn.addEventListener('click', cancelTransfer);
    
    function calculateTransfer() {
        const amount = parseFloat(amountInput.value);
        
        if (isNaN(amount) || amount <= 0) {
            alert('Please enter a valid amount');
            return;
        }
        
        fetch('/calculate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `amount=${amount}`
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                document.getElementById('fee-amount').textContent = data.fee_amount;
                document.getElementById('total-amount').textContent = data.amount_plus_fees;
                document.getElementById('receiving-amount').textContent = data.receiving_amount;
                resultsDiv.style.display = 'block';
            } else {
                alert(data.message);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred. Please try again.');
        });
    }
    
    function proceedPayment() {
        alert('Redirecting to payment gateway...');
        // In a real app, you would redirect to a payment page
    }
    
    function cancelTransfer() {
        amountInput.value = '';
        resultsDiv.style.display = 'none';
    }
});