document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('quote-form');
    const amountInput = document.getElementById('amount');
    const errorBox = document.getElementById('error');
    const results = document.getElementById('results');
    const submitBtn = document.getElementById('calculate-btn');

    const usd = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' });
    const xaf = new Intl.NumberFormat('fr-CM', { style: 'currency', currency: 'XAF', maximumFractionDigits: 0 });

    function showError(message) {
        errorBox.textContent = message;
        errorBox.hidden = false;
        results.hidden = true;
    }

    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        errorBox.hidden = true;
        submitBtn.disabled = true;

        try {
            // The amount is sent as a string; the server does all money maths with Decimal.
            const response = await fetch('/api/quote', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ amount: amountInput.value }),
            });
            const data = await response.json();

            if (!response.ok) {
                showError(data.error || 'Could not get a quote. Please try again.');
                return;
            }

            document.getElementById('fee-amount').textContent = usd.format(Number(data.fee));
            document.getElementById('total-amount').textContent = usd.format(Number(data.total_to_pay));
            document.getElementById('exchange-rate').textContent = `1 USD = ${data.exchange_rate} XAF`;
            document.getElementById('receiving-amount').textContent = xaf.format(Number(data.receive_amount));
            results.hidden = false;
        } catch (err) {
            console.error(err);
            showError('Network error. Please check your connection and try again.');
        } finally {
            submitBtn.disabled = false;
        }
    });

    document.getElementById('reset-btn').addEventListener('click', () => {
        form.reset();
        results.hidden = true;
        errorBox.hidden = true;
        amountInput.focus();
    });
});
