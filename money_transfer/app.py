from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Configuration
SENDING_FEES = 0.02
EXCHANGE_RATE = 655

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/calculate', methods=['POST'])
def calculate():
    try:
        user_amount = float(request.form['amount'])

        # Calculations
        fee_amount = SENDING_FEES * user_amount
        amount_plus_fees = user_amount + fee_amount
        receiving_amount = EXCHANGE_RATE * user_amount

        return jsonify({
            'success': True,
            'amount_plus_fees': f"${amount_plus_fees:,.2f}",
            'receiving_amount': f"{receiving_amount:,.2f} CFA",
            'fee_amount': f"${fee_amount:,.2f}"
        })
    except:
        return jsonify({'success': False, 'message': 'Please enter a valid amount'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')  # host='0.0.0.0' is needed for Docker
