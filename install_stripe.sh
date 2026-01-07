#!/bin/bash
curl -s https://packages.stripe.dev/api/security/keypair/stripe-cli-gpg/public | gpg --dearmor | sudo tee /usr/share/keyrings/stripe.gpg
echo "deb [signed-by=/usr/share/keyrings/stripe.gpg] https://packages.stripe.dev/stripe-cli-debian-local stable main" | sudo tee -a /etc/apt/sources.list.d/stripe.list
sudo apt update
sudo apt install stripe

echo "---------"
echo "Remember to set the STRIPE_SECRET and SECRET_KEY environment variables."
echo "Stripe CLI installed, please login with 'stripe login'"
echo "To run the app, please run 'stripe listen --forward-to localhost:5000/auth/webhook' and 'python3 main.py' - both in seperate terminals"