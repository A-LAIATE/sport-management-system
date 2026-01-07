#!/bin/bash
echo "checking required environment variables are set..."

if [[ -z "${SECRET_KEY}" ]]; then
    echo "Input value for SECRET_KEY:"
    read input
    export SECRET_KEY="$input"
fi

if [[ -z "${STRIPE_SECRET}" ]]; then
    echo "Input value for STRIPE_SECRET:"
    read input
    export STRIPE_SECRET="$input"
    export STRIPE_API_KEY="$input"
fi

FILE=./app/PROD_leisure_centre.db
if [ ! -f $FILE ]; then
    echo "$FILE does not exist. Creating..."
    touch $FILE
fi

FILE=./app/leisure_centre.db
if [ ! -f $FILE ]; then
    echo "$FILE does not exist. Creating..."
    touch $FILE
fi

echo "setting up stripe..."
stripe login -i
stripe listen --forward-to localhost:5000/auth/webhook &
echo "stripe listening on localhost:5000/auth/webhook"
echo "Running App"
python3 main.py
