[![Open in Codespaces](https://classroom.github.com/assets/launch-codespace-f4981d0f882b2a3f0472912d15f9806d57e124e0fc890972558857b51b24a6f9.svg)](https://classroom.github.com/open-in-codespaces?assignment_repo_id=10164186)

# Set up the environment

## Using dev containers (Recommended)
This is an easy way of setting up the environment using containers:
- Open vscode
- Install the Dev Containers extension
- Open the command palette
- Run "Dev Container: Clone Repository in Container Volume"
- Paste in the link to the repo `https://github.com/uol-feps-soc-comp2913-2223s2-classroom/project-squad46.git`
- It should set everything up for you.

## Without dev containers
- Get python 3.8, can use an installer, chocolatey, apt
- Create a new python 3.8 environment using venv
- Activate the environment
- Clone the repo
- `pip install -r requirements.txt`

# Setting up pre-commit

We will be using pre-commit to make sure all commits are working python code that is consistently formatted using black and flake8. Unit tests are configured to run on every push.

If you used the devcontainer method then this has been done for you.


Run `pre-commit install && pre-commit install --hook-type pre-push` in the same directory as the .pre-commit-config.yaml file.

## Notes

Now when you make a commit, a few checks will run first.

flake8 - this checks the syntax and formatting of your python files. When it fails it will tell you what the issues are and where they are.

black - this also checks the formatting. It will fail if it has to reformat any files. It will not save any changes it makes to staged files so you must run `black .` to make the changes.

When you push, all unit tests will be run first. If the tests fail the push will be aborted. You may notice that your push takes a bit longer.
If you get an error along the lines of `failed to push some refs` and you can't see why, check that all of the tests pass `python -m pytest`

## flake8 and black in your IDE

I recommend setting them up in your IDE so that you get warnings in your editor and code is reformatted on save. Note that flake8 needs some extra args to be compatible with black. These are in the .pre-commit-config.yaml file


The devcontainer method will have installed the flake8 extension for vscode. You still need to set these extra args in the extension settings

```
--extend-ignore=E203,E501
--select=C,E,F,W,B,B950
--max-line-length=88
```

# Running the app

The app requires an environment variable `SECRET_KEY` to be set. On windows this is `set SECRET_KEY=something` on linux `export SECRET_KEY=something`
Run the app by doing `python main.py` in the terminal - DO NOT use `flask run`

## Stripe CLI
We use Stripe webhooks to track various user actions. In order for these to work properly please install the stripe CLI from here:[https://stripe.com/docs/stripe-cli]
If you are using the devcontainer then this will be done for you. Please follow the instructions in the terminal. They are repeated here for clarity:
- Remember to set the `STRIPE_SECRET` and `SECRET_KEY` environment variables.
- Stripe CLI installed, please login with `stripe login`
- To run the app, please run `stripe listen --forward-to localhost:5000/auth/webhook` and `python3 main.py` - both in seperate terminals"
